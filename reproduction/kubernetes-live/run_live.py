#!/usr/bin/env python3
"""Generate both paper profiles and, on an explicitly selected kind cluster, test the storage path."""
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
from supplement.replay import COMMIT, rules
from fixtures import expected

BASE = Path(__file__).resolve().parent
PROFILES = ("time_series", "visual_inspection")
KINDS = {"time_series": "Time-Series", "visual_inspection": "Image"}
SCOPE = "live storage smoke test only; full platform/XAI/explanation/training not exercised"
SERVER = "minio"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

def check(flag, reason):
    if not flag:
        raise ValueError(reason)

def verified_source(repo, snapshot_mode):
    hashes = json.loads((BASE / "supplement/input_sha256.json").read_text())
    for name, expected in hashes.items():
        check(sha((repo / name).read_bytes()) == expected, f"pinned source mismatch: {name}")
    if not snapshot_mode:
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
    path = BASE / "supplement/profiles" / f"{profile_id}.json"
    profile_bytes = path.read_bytes()
    profile = json.loads(profile_bytes)
    fields = json.loads((repo / "feature_model.fm").read_text())
    problems = rules(fields, profile)
    check(not problems, f"invalid feature profile: {problems}")
    check(profile["data_type"] == KINDS[profile_id], "wrong data modality")
    for name in ("code_templates.json", "ml_pipeline_templates.json"):
        (folder / name).write_bytes((repo / name).read_bytes())
    # Stage 1 only: there is no live inventory before deployment.
    (folder / "kubernetes_resources.txt").write_text("=== Services ===\n\n=== Pods ===\n")
    generation(gen, folder, "code_templates.json", fields, profile)
    platform = sorted({p.relative_to(folder).as_posix(): sha(p.read_bytes())
                       for dr in ("src", "build_scripts", "deployment") for p in (folder / dr).rglob("*")
                       if p.is_file()}.items())
    manifest = folder / "src/kubernetes/data_repository/deployment.yml"
    docs = list(yaml.safe_load_all(manifest.read_text()))
    deploys = [d for d in docs if d and d.get("kind") == "Deployment" and d["metadata"]["name"] == SERVER]
    check(len(deploys) == 1, "unexpected generated storage deployment")
    return fields, profile, sha(profile_bytes), platform, deploys[0], sha(manifest.read_bytes())

def resources(deploy, server_image):
    """Minimal documented overlay; keeps the actual generated MinIO Deployment."""
    pod = deploy["spec"]["template"]["spec"]
    containers = pod["containers"]
    check(len(containers) == 1 and containers[0]["name"] == SERVER, "unexpected containers in storage deployment")
    labels = deploy["spec"]["selector"]["matchLabels"]
    check(labels == {"app": SERVER}, "unexpected storage selector")
    pod["automountServiceAccountToken"] = False
    cfg = containers[0]
    cfg["image"] = server_image
    cfg["ports"] = [{"name": "s3", "containerPort": 9000}]
    cfg["readinessProbe"] = {"httpGet": {"path": "/minio/health/ready", "port": "s3"},
                             "periodSeconds": 2, "failureThreshold": 6}
    cfg["envFrom"] = [{"secretRef": {"name": "paper-storage-auth"}}]
    svc = {"apiVersion": "v1", "kind": "Service", "metadata": {"name": SERVER},
           "spec": {"type": "ClusterIP", "selector": labels, "ports": [{"name": "s3", "port": 9000,
                                                                       "targetPort": "s3"}]}}
    return deploy, svc

class Cluster:
    def __init__(self, kubeconfig, context, namespace):
        self.base = ["kubectl", "--kubeconfig", str(kubeconfig), "--context", context]
        self.ns = namespace

    def call(self, *args, data=None, namespaced=True, timeout=360):
        argv = self.base + (["-n", self.ns] if namespaced else []) + list(args)
        proc = subprocess.run(argv, input=data, text=True, capture_output=True, timeout=timeout)
        if proc.returncode:
            # Never include manifests, credentials or verbose kubectl stderr in public evidence.
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
        port = next(p["port"] for p in service["spec"]["ports"] if p["name"] == "s3")
        pieces = cluster.get("endpointslices", "-l", "kubernetes.io/service-name=minio")["items"]
        ready = len({addr for p in pieces for e in p.get("endpoints", [])
                     if e.get("conditions", {}).get("ready") is True for addr in e.get("addresses", [])})
        if ready:
            # Same text format the pinned generator reads; constructed from the live API
            # in the dedicated namespace instead of the historical inventory.
            pods = cluster.get("pods", "-l", "app=minio")["items"]
            lines = ["=== Services ===", "", "Service Name: minio", f"  Namespace: {cluster.ns}",
                     f"  Cluster IP: {fresh_ip}", f"  Ports: {port}/TCP", "", "=== Pods ===", ""]
            for p in pods:
                lines += [f"Pod Name: {p['metadata']['name']}", f"  Namespace: {cluster.ns}",
                          f"  Node: {p['spec']['nodeName']}", f"  Status: {p['status']['phase']}", ""]
            return f"{fresh_ip}:{port}", "\n".join(lines) + "\n", ready
        time.sleep(2)
    raise RuntimeError("no ready EndpointSlice address before timeout")

def check_binding(src, endpoint, profile):
    tree = ast.parse(src)
    def assignments(name):
        return [node.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in node.targets)]
    ip, bind = assignments("minio_service_1_ip"), assignments("MINIO_ENDPOINT")
    check(len(ip) == len(bind) == 1 and isinstance(ip[0], ast.Constant) and
          ip[0].value == endpoint and isinstance(bind[0], ast.Name) and bind[0].id == "minio_service_1_ip",
          "fresh endpoint was not bound into the generated client")
    marker = ("monthly_hourly_load_values_2022_DE.csv" if profile == "time_series" else "image-data")
    check(marker in src, "generated repository client does not match profile")

def job(client_image, profile, endpoint, timeout):
    return {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": "storage-probe"},
            "spec": {"backoffLimit": 0, "activeDeadlineSeconds": timeout,
                     "template": {"spec": {"restartPolicy": "Never", "automountServiceAccountToken": False,
                       "containers": [{"name": "probe", "image": client_image,
                         "envFrom": [{"secretRef": {"name": "paper-storage-auth"}}],
                         "env": [{"name": "PROFILE", "value": profile},
                                 {"name": "EXPECTED_ENDPOINT", "value": endpoint},
                                 {"name": "PIP_DISABLE_PIP_VERSION_CHECK", "value": "1"}],
                         "command": ["sh", "-ec"], "args": [
                             "python -m pip install --no-input --retries 2 --timeout 20 "
                             "'minio==7.2.15' 'pandas==2.2.3' 'urllib3==2.3.0' && "
                             "python /probe/storage_probe.py"],
                         "volumeMounts": [{"name": "script", "mountPath": "/probe", "readOnly": True}]}],
                       "volumes": [{"name": "script", "configMap": {"name": "paper-probe"}}]}}}}

def wait_job(cluster, timeout):
    cutoff = time.monotonic() + timeout
    while time.monotonic() < cutoff:
        state = cluster.get("job", "storage-probe").get("status", {})
        conditions = {e["type"]:e.get("status") for e in state.get("conditions", [])}
        if conditions.get("Failed") == "True":
            raise RuntimeError("storage-probe Job failed; use local kubectl logs for diagnosis")
        if conditions.get("Complete") == "True":
            lines = cluster.call("logs", "job/storage-probe", timeout=45).splitlines()
            matches = []
            for line in lines:
                try:
                    parsed = json.loads(line)
                    if isinstance(parsed, dict) and parsed.get("round_trip") == "pass":
                        matches.append(parsed)
                except json.JSONDecodeError:
                    continue
            check(len(matches) == 1, "missing or ambiguous round-trip proof")
            return matches[0]
        time.sleep(2)
    raise RuntimeError("storage-probe Job timed out")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new output directory")
    parser.add_argument("--execute", action="store_true", help="opt in to a real kind-cluster deployment")
    parser.add_argument("--context")
    parser.add_argument("--kubeconfig", type=Path)
    parser.add_argument("--server-image")
    parser.add_argument("--client-image")
    parser.add_argument("--profile", choices=("both",) + PROFILES, default="both")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--snapshot-plan", action="store_true", help="plan only, SHA256-verified files without Git metadata")
    args = parser.parse_args()
    check(30 <= args.timeout <= 1800, "timeout must be 30–1800 seconds")
    if args.execute:
        check(not args.snapshot_plan and args.kubeconfig and args.kubeconfig.is_file(),
              "live mode needs the explicit dedicated kubeconfig and a real pinned git checkout")
        check(re.fullmatch(r"kind-paper-live(?:-[a-z0-9-]+)?", args.context or ""),
              "live mode requires a dedicated kind-paper-live[-suffix] context")
        for value in (args.server_image, args.client_image):
            check(value and re.fullmatch(r"[-./a-zA-Z0-9_:]+@sha256:[0-9a-f]{64}", value),
                  "both images must be full image references pinned by digest")
    repo, out = args.repo.resolve(), args.out.resolve()
    gen = verified_source(repo, args.snapshot_plan)
    out.mkdir(parents=True, exist_ok=False)
    evidence = {"schema": 1, "commit": COMMIT, "started_utc": now(), "scope": SCOPE,
                "mode": "execute" if args.execute else "plan", "cases": {},
                "source": "sha256-matched snapshot" if args.snapshot_plan else "git and sha256 verified",
                "images": {"server": args.server_image, "client": args.client_image},
                "direct_client_pins": ["minio==7.2.15", "pandas==2.2.3", "urllib3==2.3.0"]}
    exit_code = 0
    try:
        cases = PROFILES if args.profile == "both" else (args.profile,)
        if args.execute:
            preliminary = Cluster(args.kubeconfig, args.context, "default")
            current = preliminary.call("config", "current-context", namespaced=False).strip()
            check(current == args.context, "dedicated kubeconfig current context does not match")
            nodes = preliminary.get("nodes", namespaced=False)["items"]
            cluster_name = args.context.removeprefix("kind-")
            role_labels = ("node-role.kubernetes.io/control-plane", "node-role.kubernetes.io/worker")
            check(nodes and all(n["metadata"]["name"].startswith(cluster_name + "-") and
                                any(role in n["metadata"].get("labels", {}) for role in role_labels)
                                for n in nodes),
                  "target nodes are not recognized as the dedicated kind cluster")
            evidence["kubernetes_version"] = json.loads(preliminary.call("version", "-o", "json",
                                                                         namespaced=False, timeout=45))
            evidence["nodes"] = [{"architecture": n["status"]["nodeInfo"]["architecture"],
                                   "os": n["status"]["nodeInfo"]["osImage"],
                                   "runtime": n["status"]["nodeInfo"]["containerRuntimeVersion"],
                                   "cpu_capacity": n["status"]["capacity"]["cpu"],
                                   "memory_capacity": n["status"]["capacity"]["memory"]} for n in nodes]
        for name in cases:
            row = {"started_utc": now(), "status": "incomplete", "stage": "validate_and_generate", "checks": {}}
            evidence["cases"][name] = row
            try:
                with tempfile.TemporaryDirectory(prefix="paper-live-") as tmp:
                    folder = Path(tmp)
                    fields, profile, profile_hash, exported, deploy, declared = preparation(repo, gen, folder, name)
                    row.update(profile_sha256=profile_hash, generated_platform_paths_and_hashes=dict(exported),
                               generated_storage_manifest_sha256=declared)
                    row["checks"]["profile_and_artifact_generation"] = True
                    if not args.execute:
                        row["status"] = "plan_only"
                        continue
                    suffix = secrets.token_hex(4)
                    ns = f"paper-live-{'ts' if name == 'time_series' else 'img'}-{suffix}"
                    row["namespace"] = ns
                    cluster = Cluster(args.kubeconfig, args.context, ns)
                    row["stage"] = "deploy_and_wait"
                    cluster.call("create", "namespace", ns, namespaced=False)
                    # Create directly (no last-applied annotation on the Secret).
                    cluster.call("create", "-f", "-", data=json.dumps(
                        {"kind":"Secret", "apiVersion":"v1", "metadata":{"name":"paper-storage-auth"},
                         "stringData":{"MINIO_ROOT_USER":"paper-"+secrets.token_hex(6),
                                       "MINIO_ROOT_PASSWORD":secrets.token_urlsafe(28)}}))
                    deployment, service = resources(deploy, args.server_image)
                    cluster.apply(deployment)
                    cluster.apply(service)
                    cluster.call("rollout", "status", "deployment/minio", f"--timeout={args.timeout}s",
                                 timeout=args.timeout + 30)
                    status = cluster.get("deployment", SERVER)["status"]
                    row["ready_replicas"] = status.get("readyReplicas", 0)
                    check(row["ready_replicas"] >= 1, "no ready storage replica")
                    row["checks"]["storage_rollout"] = True
                    row["stage"] = "discover_and_bind"
                    endpoint, inventory, ready = discovered(cluster, args.timeout)
                    (folder / "kubernetes_resources.txt").write_text(inventory)
                    row.update(ready_endpoints=ready, fresh_inventory_sha256=sha(inventory.encode()))
                    row["checks"]["live_endpoint_discovery"] = True
                    generation(gen, folder, "ml_pipeline_templates.json", fields, profile)
                    source = (folder / "python/data_repository/main.py").read_text()
                    check_binding(source, endpoint, name)
                    row.update(generated_repository_client_sha256=sha(source.encode()))
                    row["checks"]["fresh_endpoint_binding"] = True
                    row["stage"] = "storage_pipeline_smoke"
                    config = {"apiVersion": "v1", "kind": "ConfigMap", "metadata":{"name":"paper-probe"},
                              "data":{"generated.py":source, "storage_probe.py":(BASE/"storage_probe.py").read_text(),
                                      "fixtures.py":(BASE/"fixtures.py").read_text()}}
                    cluster.apply(config)
                    cluster.apply(job(args.client_image, name, endpoint, args.timeout))
                    result = wait_job(cluster, args.timeout + 15)
                    check(result.get("profile") == name and result.get("live_endpoint_used") is True
                          and all(result.get(k) == v for k, v in expected(name).items()),
                          "storage proof is missing identity, binding or digest")
                    row["round_trip"] = expected(name)
                    row["client_versions"] = result.get("client_versions", {})
                    row["checks"]["generated_client_object_round_trip"] = True
                    row["status"] = "storage_smoke_pass"
            except (RuntimeError, ValueError, subprocess.SubprocessError, OSError) as exc:
                row["status"] = "failed"
                row["failure_class"] = type(exc).__name__
                # Fixed stages, booleans and failure class only in evidence.
                print(f"{name}: {row['stage']}: {exc}", file=sys.stderr)
                exit_code = 1
            finally:
                row["ended_utc"] = now()
    except (RuntimeError, ValueError, subprocess.SubprocessError, OSError) as exc:
        evidence["preflight_failure"] = type(exc).__name__
        print(f"preflight: {exc}", file=sys.stderr)
        exit_code = 1
    finally:
        evidence["ended_utc"] = now()
        (out / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print(out / "evidence.json")
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
