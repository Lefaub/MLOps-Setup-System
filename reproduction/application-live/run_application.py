#!/usr/bin/env python3
"""Generate both profiles and execute a GUI-free application path on a dedicated kind cluster."""
import argparse
import ast
import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
sys.dont_write_bytecode = True
import tempfile
import time

import yaml

BASE = Path(__file__).resolve().parent
KUBERNETES_LIVE = BASE.parent / "kubernetes-live"
sys.path.insert(0, str(KUBERNETES_LIVE))
from supplement.replay import COMMIT, rules

PROFILES = ("time_series", "visual_inspection")
KINDS = {"time_series": "Time-Series", "visual_inspection": "Image"}
SCOPE = ("headless application-path live smoke test using deterministic synthetic fixtures; "
         "the browser GUI, external production datasets and production-scale model quality are not exercised")
SERVER = "minio"
REGISTRY = "mlflow"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def check(flag, reason):
    if not flag:
        raise ValueError(reason)


def verified_source(repo):
    hashes = json.loads((KUBERNETES_LIVE / "supplement/input_sha256.json").read_text())
    for name, expected in hashes.items():
        check(sha((repo / name).read_bytes()) == expected, f"pinned source mismatch: {name}")
    result = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    check(result == COMMIT, "checkout does not match the paper commit")
    spec = importlib.util.spec_from_file_location("pinned_generator", repo / "script_generation.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def generation(gen, directory, template, fields, profile):
    here = Path.cwd()
    try:
        os.chdir(directory)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            gen.script_generation(template, fields, json.dumps(profile))
    finally:
        os.chdir(here)


def preparation(repo, gen, folder, profile_id):
    path = KUBERNETES_LIVE / "supplement/profiles" / f"{profile_id}.json"
    profile_bytes = path.read_bytes()
    profile = json.loads(profile_bytes)
    fields = json.loads((repo / "feature_model.fm").read_text())
    problems = rules(fields, profile)
    check(not problems, f"invalid feature profile: {problems}")
    check(profile["data_type"] == KINDS[profile_id], "wrong data modality")
    for name in ("code_templates.json", "ml_pipeline_templates.json"):
        (folder / name).write_bytes((repo / name).read_bytes())
    (folder / "kubernetes_resources.txt").write_text("=== Services ===\n\n=== Pods ===\n")
    generation(gen, folder, "code_templates.json", fields, profile)
    platform = dict(sorted({p.relative_to(folder).as_posix(): sha(p.read_bytes())
                            for dr in ("src", "build_scripts", "deployment")
                            for p in (folder / dr).rglob("*") if p.is_file()}.items()))
    manifest = folder / "src/kubernetes/data_repository/deployment.yml"
    docs = list(yaml.safe_load_all(manifest.read_text()))
    deploys = [doc for doc in docs if doc and doc.get("kind") == "Deployment"
               and doc["metadata"]["name"] == SERVER]
    check(len(deploys) == 1, "unexpected generated storage deployment")
    return fields, profile, sha(profile_bytes), platform, deploys[0]


def storage_resources(deploy, server_image):
    pod = deploy["spec"]["template"]["spec"]
    containers = pod["containers"]
    check(len(containers) == 1 and containers[0]["name"] == SERVER, "unexpected storage containers")
    labels = deploy["spec"]["selector"]["matchLabels"]
    check(labels == {"app": SERVER}, "unexpected storage selector")
    pod["automountServiceAccountToken"] = False
    cfg = containers[0]
    cfg["image"] = server_image
    cfg["ports"] = [{"name": "s3", "containerPort": 9000}]
    cfg["readinessProbe"] = {"httpGet": {"path": "/minio/health/ready", "port": "s3"},
                             "periodSeconds": 2, "failureThreshold": 15}
    cfg["envFrom"] = [{"secretRef": {"name": "paper-storage-auth"}}]
    service = {"apiVersion": "v1", "kind": "Service", "metadata": {"name": SERVER},
               "spec": {"selector": labels, "ports": [{"name": "s3", "port": 9000,
                                                          "targetPort": "s3"}]}}
    return deploy, service


def registry_resources(client_image):
    labels = {"app": REGISTRY}
    command = ("python -m pip install --no-input --retries 2 --timeout 30 'mlflow==2.16.2' && "
               "exec mlflow server --host 0.0.0.0 --port 5000 "
               "--backend-store-uri sqlite:////tmp/mlflow.db --serve-artifacts "
               "--artifacts-destination /tmp/mlartifacts")
    deployment = {
        "apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": REGISTRY},
        "spec": {"replicas": 1, "selector": {"matchLabels": labels},
                 "template": {"metadata": {"labels": labels}, "spec": {
                     "automountServiceAccountToken": False,
                     "containers": [{"name": REGISTRY, "image": client_image,
                                     "ports": [{"name": "http", "containerPort": 5000}],
                                     "command": ["sh", "-ec"], "args": [command],
                                     "startupProbe": {"tcpSocket": {"port": "http"},
                                                      "periodSeconds": 5, "failureThreshold": 60},
                                     "readinessProbe": {"tcpSocket": {"port": "http"},
                                                        "periodSeconds": 2, "failureThreshold": 10}}]}}}}
    service = {"apiVersion": "v1", "kind": "Service", "metadata": {"name": REGISTRY},
               "spec": {"selector": labels, "ports": [{"name": "http", "port": 5000,
                                                          "targetPort": "http"}]}}
    return deployment, service


class Cluster:
    def __init__(self, kubeconfig, context, namespace):
        self.base = ["kubectl", "--kubeconfig", str(kubeconfig), "--context", context]
        self.ns = namespace

    def call(self, *args, data=None, namespaced=True, timeout=360):
        argv = self.base + (["-n", self.ns] if namespaced else []) + list(args)
        proc = subprocess.run(argv, input=data, text=True, capture_output=True, timeout=timeout)
        if proc.returncode:
            raise RuntimeError(f"kubectl {' '.join(args)} exited {proc.returncode}")
        return proc.stdout

    def get(self, *args, namespaced=True):
        return json.loads(self.call("get", *args, "-o", "json", namespaced=namespaced, timeout=45))

    def apply(self, obj):
        self.call("apply", "-f", "-", data=json.dumps(obj))


def discovered(cluster, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        service = cluster.get("service", SERVER)
        fresh_ip = ipaddress.IPv4Address(service["spec"]["clusterIP"])
        port = next(item["port"] for item in service["spec"]["ports"] if item["name"] == "s3")
        slices = cluster.get("endpointslices", "-l", "kubernetes.io/service-name=minio")["items"]
        ready = len({address for piece in slices for endpoint in piece.get("endpoints", [])
                     if endpoint.get("conditions", {}).get("ready") is True
                     for address in endpoint.get("addresses", [])})
        if ready:
            pods = cluster.get("pods", "-l", "app=minio")["items"]
            inventory = ["=== Services ===", "", "Service Name: minio",
                         f"  Namespace: {cluster.ns}", f"  Cluster IP: {fresh_ip}",
                         f"  Ports: {port}/TCP", "", "=== Pods ===", ""]
            for pod in pods:
                inventory.extend([f"Pod Name: {pod['metadata']['name']}",
                                  f"  Namespace: {cluster.ns}",
                                  f"  Node: {pod['spec']['nodeName']}",
                                  f"  Status: {pod['status']['phase']}", ""])
            return f"{fresh_ip}:{port}", "\n".join(inventory) + "\n", ready
        time.sleep(2)
    raise RuntimeError("no ready storage endpoint before timeout")


def check_binding(source, endpoint, profile):
    tree = ast.parse(source)

    def assignments(name):
        return [node.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]

    ip, binding = assignments("minio_service_1_ip"), assignments("MINIO_ENDPOINT")
    check(len(ip) == len(binding) == 1 and isinstance(ip[0], ast.Constant)
          and ip[0].value == endpoint and isinstance(binding[0], ast.Name)
          and binding[0].id == "minio_service_1_ip", "fresh endpoint was not bound into generated client")
    marker = "monthly_hourly_load_values_2022_DE.csv" if profile == "time_series" else "image-data"
    check(marker in source, "generated storage client does not match profile")


def application_job(client_image, profile, endpoint, timeout):
    install = ("python -m pip install --no-input --retries 2 --timeout 30 "
               "'numpy==1.26.4' 'pandas==2.2.3' 'scikit-learn==1.5.2' "
               "'pillow==11.0.0' 'joblib==1.4.2' 'minio==7.2.15' "
               "'urllib3==2.3.0' 'mlflow==2.16.2'")
    return {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": "application-probe"},
            "spec": {"backoffLimit": 0, "activeDeadlineSeconds": timeout,
                     "template": {"spec": {"restartPolicy": "Never", "automountServiceAccountToken": False,
                         "containers": [{"name": "probe", "image": client_image,
                             "envFrom": [{"secretRef": {"name": "paper-storage-auth"}}],
                             "env": [{"name": "PROFILE", "value": profile},
                                     {"name": "EXPECTED_ENDPOINT", "value": endpoint},
                                     {"name": "MLFLOW_TRACKING_URI", "value": "http://mlflow:5000"},
                                     {"name": "PIP_DISABLE_PIP_VERSION_CHECK", "value": "1"}],
                             "command": ["sh", "-ec"],
                             "args": [install + " && python /probe/application_probe.py"],
                             "volumeMounts": [{"name": "script", "mountPath": "/probe", "readOnly": True}]}],
                         "volumes": [{"name": "script", "configMap": {"name": "application-probe"}}]}}}}


def wait_job(cluster, timeout):
    cutoff = time.monotonic() + timeout
    while time.monotonic() < cutoff:
        state = cluster.get("job", "application-probe").get("status", {})
        conditions = {item["type"]: item.get("status") for item in state.get("conditions", [])}
        if conditions.get("Failed") == "True":
            logs = cluster.call("logs", "job/application-probe", timeout=90)
            tail = "\n".join(logs.splitlines()[-40:])
            raise RuntimeError(f"application-probe Job failed; final log lines:\n{tail}")
        if conditions.get("Complete") == "True":
            lines = cluster.call("logs", "job/application-probe", timeout=90).splitlines()
            matches = []
            for line in lines:
                try:
                    value = json.loads(line)
                    if isinstance(value, dict) and isinstance(value.get("application_result"), dict):
                        matches.append(value["application_result"])
                except json.JSONDecodeError:
                    continue
            check(len(matches) == 1, "missing or ambiguous application proof")
            return matches[0]
        time.sleep(3)
    raise RuntimeError("application-probe Job timed out")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--context")
    parser.add_argument("--kubeconfig", type=Path)
    parser.add_argument("--server-image")
    parser.add_argument("--client-image")
    parser.add_argument("--profile", choices=("both",) + PROFILES, default="both")
    parser.add_argument("--timeout", type=int, default=720)
    args = parser.parse_args()
    check(args.execute, "the application live test requires explicit execute mode")
    check(120 <= args.timeout <= 1800, "timeout must be 120-1800 seconds")
    check(args.kubeconfig and args.kubeconfig.is_file(), "a dedicated kubeconfig is required")
    check(re.fullmatch(r"kind-application-live(?:-[a-z0-9-]+)?", args.context or ""),
          "a dedicated kind-application-live context is required")
    for value in (args.server_image, args.client_image):
        check(value and re.fullmatch(r"[-./a-zA-Z0-9_:]+@sha256:[0-9a-f]{64}", value),
              "both images must be full references pinned by digest")

    repo, out = args.repo.resolve(), args.out.resolve()
    gen = verified_source(repo)
    out.mkdir(parents=True, exist_ok=False)
    evidence = {"schema": 1, "commit": COMMIT, "started_utc": now(), "scope": SCOPE,
                "mode": "execute", "configuration_mode": "direct generator call; GUI bypassed",
                "fixture_scope": "deterministic synthetic fixtures", "cases": {},
                "source": "git and sha256 verified",
                "images": {"server": args.server_image, "client": args.client_image},
                "dependency_pins": {"mlflow": "2.16.2", "scikit-learn": "1.5.2",
                                    "numpy": "1.26.4", "pandas": "2.2.3", "pillow": "11.0.0",
                                    "minio": "7.2.15", "urllib3": "2.3.0", "joblib": "1.4.2"}}
    exit_code = 0
    try:
        preliminary = Cluster(args.kubeconfig, args.context, "default")
        current = preliminary.call("config", "current-context", namespaced=False).strip()
        check(current == args.context, "dedicated kubeconfig context does not match")
        nodes = preliminary.get("nodes", namespaced=False)["items"]
        cluster_name = args.context.removeprefix("kind-")
        roles = ("node-role.kubernetes.io/control-plane", "node-role.kubernetes.io/worker")
        check(nodes and all(node["metadata"]["name"].startswith(cluster_name + "-")
                            and any(role in node["metadata"].get("labels", {}) for role in roles)
                            for node in nodes), "target nodes are not the dedicated kind cluster")
        evidence["kubernetes_version"] = json.loads(
            preliminary.call("version", "-o", "json", namespaced=False, timeout=45))
        for profile_id in (PROFILES if args.profile == "both" else (args.profile,)):
            row = {"started_utc": now(), "status": "incomplete", "stage": "generate", "checks": {}}
            evidence["cases"][profile_id] = row
            try:
                with tempfile.TemporaryDirectory(prefix="application-live-") as temp:
                    folder = Path(temp)
                    fields, profile, profile_hash, platform_hashes, deploy = preparation(
                        repo, gen, folder, profile_id)
                    row.update(profile_sha256=profile_hash,
                               generated_platform_paths_and_hashes=platform_hashes)
                    row["checks"]["profile_validation_and_generation"] = True
                    suffix = secrets.token_hex(4)
                    namespace = f"application-{'ts' if profile_id == 'time_series' else 'img'}-{suffix}"
                    row["namespace"] = namespace
                    cluster = Cluster(args.kubeconfig, args.context, namespace)
                    cluster.call("create", "namespace", namespace, namespaced=False)
                    cluster.call("create", "-f", "-", data=json.dumps({
                        "kind": "Secret", "apiVersion": "v1", "metadata": {"name": "paper-storage-auth"},
                        "stringData": {"MINIO_ROOT_USER": "paper-" + secrets.token_hex(6),
                                       "MINIO_ROOT_PASSWORD": secrets.token_urlsafe(28)}}))
                    row["stage"] = "deploy_services"
                    storage, storage_service = storage_resources(deploy, args.server_image)
                    registry, registry_service = registry_resources(args.client_image)
                    for resource in (storage, storage_service, registry, registry_service):
                        cluster.apply(resource)
                    cluster.call("rollout", "status", "deployment/minio", f"--timeout={args.timeout}s",
                                 timeout=args.timeout + 30)
                    cluster.call("rollout", "status", "deployment/mlflow", f"--timeout={args.timeout}s",
                                 timeout=args.timeout + 30)
                    row["checks"]["kubernetes_service_rollout"] = True
                    endpoint, inventory, ready = discovered(cluster, args.timeout)
                    (folder / "kubernetes_resources.txt").write_text(inventory)
                    row.update(ready_storage_endpoints=ready, fresh_inventory_sha256=sha(inventory.encode()))
                    generation(gen, folder, "ml_pipeline_templates.json", fields, profile)
                    source = (folder / "python/data_repository/main.py").read_text()
                    check_binding(source, endpoint, profile_id)
                    row["generated_storage_client_sha256"] = sha(source.encode())
                    row["checks"]["fresh_endpoint_binding"] = True
                    row["stage"] = "headless_application"
                    cluster.apply({"apiVersion": "v1", "kind": "ConfigMap",
                                   "metadata": {"name": "application-probe"},
                                   "data": {"generated.py": source,
                                            "application_probe.py": (BASE / "application_probe.py").read_text()}})
                    cluster.apply(application_job(args.client_image, profile_id, endpoint, args.timeout))
                    proof = wait_job(cluster, args.timeout)
                    check(proof.get("status") == "application_smoke_pass"
                          and proof.get("profile") == profile_id
                          and proof.get("fixture_scope") == "deterministic synthetic fixture"
                          and proof.get("live_endpoint_used") is True
                          and proof.get("checks") and all(proof["checks"].values()),
                          "application proof is incomplete")
                    row["application"] = proof
                    row["checks"]["headless_application_path"] = True
                    row["status"] = "application_smoke_pass"
            except (RuntimeError, ValueError, subprocess.SubprocessError, OSError) as exc:
                row["status"] = "failed"
                row["failure_class"] = type(exc).__name__
                print(f"{profile_id}: {row['stage']}: {exc}", file=sys.stderr)
                exit_code = 1
            finally:
                row["ended_utc"] = now()
    except (RuntimeError, ValueError, subprocess.SubprocessError, OSError) as exc:
        evidence["preflight_failure"] = type(exc).__name__
        print(f"preflight: {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        evidence["ended_utc"] = now()
        (out / "evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        print(out / "evidence.json")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
