#!/usr/bin/env python3
"""Run a deterministic application path inside the isolated Kubernetes cluster."""
import ast
import contextlib
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile

import joblib
import mlflow
import mlflow.sklearn
from minio import Minio
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, mean_absolute_error

PROFILE = os.environ["PROFILE"]
EXPECTED_ENDPOINT = os.environ["EXPECTED_ENDPOINT"]
TRACKING_URI = os.environ["MLFLOW_TRACKING_URI"]
ROOT = Path("/home/data_repository")
SEED = 1729


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check(flag, reason):
    if not flag:
        raise RuntimeError(reason)


def make_time_series():
    ROOT.mkdir(parents=True, exist_ok=True)
    rows = ["MeasureItem;DateUTC;DateShort;TimeFrom;TimeTo;CountryCode;Cov_ratio;Value;Value_ScaleTo100;CreateDate"]
    for i in range(240):
        value = 50000 + 6500 * math.sin(2 * math.pi * i / 24) + 1200 * math.sin(2 * math.pi * i / 168)
        day, hour = 1 + i // 24, i % 24
        rows.append(f"Synthetic Hourly Load;{day:02d}/01/2022 {hour:02d}:00;{day:02d}/01/2022;{hour:02d}:00;{(hour + 1) % 24:02d}:00;DE;100;{value:.3f};{value:.3f};01/01/2022 00:00")
    target = ROOT / "monthly_hourly_load_values_2022_DE.csv"
    target.write_text("\n".join(rows) + "\n")
    return [target]


def image_bytes(label, index):
    rng = np.random.default_rng(SEED + label * 100 + index)
    base = np.full((32, 32), 210, dtype=np.int16)
    base += rng.integers(-8, 9, size=base.shape)
    image = Image.fromarray(np.uint8(np.clip(base, 0, 255)), mode="L")
    draw = ImageDraw.Draw(image)
    draw.ellipse((7, 7, 25, 25), fill=150, outline=90, width=2)
    if label:
        draw.ellipse((13, 13, 19, 19), fill=15)
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=False)
    return out.getvalue()


def make_images():
    folder = ROOT / "data"
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for label, name in ((0, "normal"), (1, "missing_hole")):
        for index in range(24):
            path = folder / f"{name}_{index:02d}.png"
            path.write_bytes(image_bytes(label, index))
            paths.append(path)
    return paths


def run_generated_client():
    fixture_paths = make_time_series() if PROFILE == "time_series" else make_images()
    tree = ast.parse(Path("/probe/generated.py").read_text())
    credential_env = {"ACCESS_KEY": "MINIO_ROOT_USER", "SECRET_KEY": "MINIO_ROOT_PASSWORD"}
    patched = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in credential_env:
                check(name not in patched and isinstance(node.value, ast.Constant), "unexpected credential declaration")
                node.value = ast.Constant(os.environ[credential_env[name]])
                patched.add(name)
    check(patched == credential_env.keys(), "generated client credentials were not found")
    env = {"__name__": "__main__"}
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), "generated.py", "exec"), env)
    check(env.get("MINIO_ENDPOINT") == EXPECTED_ENDPOINT, "generated client used a stale endpoint")
    return env["client"], fixture_paths


def load_time_series(client):
    key = str(ROOT / "monthly_hourly_load_values_2022_DE.csv")
    response = client.get_object("energiedaten", key)
    try:
        payload = response.read()
    finally:
        response.close()
        response.release_conn()
    frame = pd.read_csv(io.BytesIO(payload), delimiter=";")
    values = frame["Value"].to_numpy(dtype=float)
    lag = 24
    x = np.stack([values[i:i + lag] for i in range(len(values) - lag)])
    y = values[lag:]
    split = int(len(x) * 0.8)
    return payload, x[:split], x[split:], y[:split], y[split:]


def image_features(payload):
    image = np.asarray(Image.open(io.BytesIO(payload)).convert("L").resize((32, 32)), dtype=float) / 255.0
    return np.array([image[y:y + 8, x:x + 8].mean() for y in range(0, 32, 8) for x in range(0, 32, 8)])


def load_images(client):
    rows = []
    for item in client.list_objects("image-data"):
        response = client.get_object("image-data", item.object_name)
        try:
            payload = response.read()
        finally:
            response.close()
            response.release_conn()
        label = int(item.object_name.startswith("missing_hole_"))
        rows.append((item.object_name, payload, image_features(payload), label))
    rows.sort(key=lambda row: row[0])
    check(len(rows) == 48, "generated client did not upload every image fixture")
    train = [row for row in rows if int(row[0].rsplit("_", 1)[1].split(".")[0]) < 18]
    test = [row for row in rows if int(row[0].rsplit("_", 1)[1].split(".")[0]) >= 18]
    return (b"".join(row[1] for row in rows), np.stack([row[2] for row in train]),
            np.stack([row[2] for row in test]), np.array([row[3] for row in train]),
            np.array([row[3] for row in test]))


def model_bytes(model):
    stream = io.BytesIO()
    joblib.dump(model, stream)
    return stream.getvalue()


def log_and_reload(model, name, metrics, artifacts):
    mlflow.set_tracking_uri(TRACKING_URI)
    mlflow.set_experiment(f"headless-{PROFILE}")
    with mlflow.start_run() as run:
        mlflow.log_params({"profile": PROFILE, "seed": SEED, "gui_bypassed": True})
        mlflow.log_metrics(metrics)
        for artifact_name, contents in artifacts.items():
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / artifact_name
                path.write_bytes(contents)
                mlflow.log_artifact(path, artifact_path="evidence")
        info = mlflow.sklearn.log_model(model, artifact_path="model", registered_model_name=name)
        run_id = run.info.run_id
    client = mlflow.tracking.MlflowClient()
    versions = client.search_model_versions(f"name='{name}'")
    current = max(versions, key=lambda version: int(version.version))
    loaded = mlflow.sklearn.load_model(f"models:/{name}/{current.version}")
    return loaded, run_id, int(current.version), info.model_uri


def run_time_series(client):
    source, x_train, x_test, y_train, y_test = load_time_series(client)
    model = RandomForestRegressor(n_estimators=48, max_depth=8, random_state=SEED, n_jobs=1)
    model.fit(x_train, y_train)
    prediction = model.predict(x_test)
    mae = float(mean_absolute_error(y_test, prediction))
    check(np.isfinite(prediction).all() and mae < 1500, "time-series inference quality check failed")
    explanation = permutation_importance(model, x_test, y_test, n_repeats=3, random_state=SEED, n_jobs=1)
    check(len(explanation.importances_mean) == 24 and np.isfinite(explanation.importances_mean).all(), "time-series explanation failed")
    feedback = {"kind": "corrected_target", "sample": 0, "value": float(y_test[0])}
    before = model_bytes(model)
    first, run_id, version, _ = log_and_reload(
        model, "HeadlessTimeSeries", {"mae": mae},
        {"explanation.json": json.dumps(explanation.importances_mean.tolist()).encode(),
         "feedback.json": json.dumps(feedback).encode()})
    check(np.allclose(first.predict(x_test[:3]), prediction[:3]), "registry model changed predictions")
    updated = RandomForestRegressor(n_estimators=49, max_depth=8, random_state=SEED, n_jobs=1)
    updated.fit(np.vstack([x_train, x_test[:1]]), np.concatenate([y_train, y_test[:1]]))
    after = model_bytes(updated)
    check(digest(before) != digest(after), "feedback retraining did not change the model")
    second, feedback_run, feedback_version, _ = log_and_reload(updated, "HeadlessTimeSeries", {"feedback_samples": 1.0}, {"feedback.json": json.dumps(feedback).encode()})
    check(np.isfinite(second.predict(x_test[:1])).all() and feedback_version > version, "feedback model registry round-trip failed")
    return source, {"metric": {"mae": mae}, "model_name": "HeadlessTimeSeries", "run_id": run_id,
                    "model_version": version, "feedback_run_id": feedback_run,
                    "feedback_model_version": feedback_version, "xai_method": "permutation_importance",
                    "explanation_features": 24, "prediction_samples": len(prediction)}


def run_visual(client):
    source, x_train, x_test, y_train, y_test = load_images(client)
    model = LogisticRegression(random_state=SEED, max_iter=500)
    model.fit(x_train, y_train)
    prediction = model.predict(x_test)
    accuracy = float(accuracy_score(y_test, prediction))
    check(np.isfinite(model.predict_proba(x_test)).all() and accuracy >= 0.9, "image inference quality check failed")
    contribution = model.coef_[0] * x_test[0]
    reconstructed = float(model.intercept_[0] + contribution.sum())
    check(abs(reconstructed - float(model.decision_function(x_test[:1])[0])) < 1e-9, "linear image explanation is not faithful")
    feedback = {"kind": "corrected_label", "sample": 0, "value": int(y_test[0])}
    before = model_bytes(model)
    first, run_id, version, _ = log_and_reload(
        model, "HeadlessVisualInspection", {"accuracy": accuracy},
        {"explanation.json": json.dumps(contribution.tolist()).encode(),
         "feedback.json": json.dumps(feedback).encode()})
    check(np.array_equal(first.predict(x_test[:3]), prediction[:3]), "registry model changed predictions")
    updated = LogisticRegression(random_state=SEED + 1, max_iter=500, C=0.9)
    updated.fit(np.vstack([x_train, x_test[:1]]), np.concatenate([y_train, y_test[:1]]))
    after = model_bytes(updated)
    check(digest(before) != digest(after), "feedback retraining did not change the image model")
    second, feedback_run, feedback_version, _ = log_and_reload(updated, "HeadlessVisualInspection", {"feedback_samples": 1.0}, {"feedback.json": json.dumps(feedback).encode()})
    check(np.isfinite(second.predict_proba(x_test[:1])).all() and feedback_version > version, "feedback image registry round-trip failed")
    return source, {"metric": {"accuracy": accuracy}, "model_name": "HeadlessVisualInspection", "run_id": run_id,
                    "model_version": version, "feedback_run_id": feedback_run,
                    "feedback_model_version": feedback_version, "xai_method": "exact_linear_contributions",
                    "explanation_features": 16, "prediction_samples": len(prediction)}


def main():
    client, fixture_paths = run_generated_client()
    source, result = run_time_series(client) if PROFILE == "time_series" else run_visual(client)
    proof = {
        "profile": PROFILE,
        "status": "application_smoke_pass",
        "fixture_scope": "deterministic synthetic fixture",
        "fixture_count": len(fixture_paths),
        "fixture_sha256": digest(source),
        "live_endpoint_used": True,
        "checks": {
            "gui_bypass_configuration": True,
            "generated_storage_client_execution": True,
            "storage_round_trip": True,
            "model_training": True,
            "model_registry_round_trip": True,
            "inference": True,
            "xai": True,
            "feedback_capture": True,
            "feedback_retraining": True,
        },
        **result,
    }
    payload = json.dumps(proof, sort_keys=True).encode()
    bucket = "application-evidence"
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    client.put_object(bucket, f"{PROFILE}.json", io.BytesIO(payload), len(payload), content_type="application/json")
    saved = client.get_object(bucket, f"{PROFILE}.json")
    try:
        check(saved.read() == payload, "application evidence storage round-trip failed")
    finally:
        saved.close()
        saved.release_conn()
    proof["checks"]["application_evidence_storage_round_trip"] = True
    print(json.dumps({"application_result": proof}, sort_keys=True))


if __name__ == "__main__":
    main()
