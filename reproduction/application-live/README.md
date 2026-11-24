# Headless application live smoke test

This test bypasses the Flask/browser configuration UI and passes the two
versioned paper profiles directly to the pinned generator. Each generated
storage client is bound to a newly discovered MinIO service in a disposable
kind cluster and is executed with deterministic synthetic fixtures.

For each profile the probe then performs model training, an MLflow model
registry write/read, inference, an explanation, feedback capture, retraining,
a second registry write/read, and an evidence-object round trip through MinIO.
The MinIO, Python client, and official MLflow server images are resolved to
immutable digests before the cluster is created.

Success requires `mode: execute`, `application_smoke_pass` for both cases, and
every boolean check in both the outer case and nested application result to be
true. The workflow uploads `application-live-evidence` containing
`evidence.json` and `runner.txt`.

The result is an application-path smoke test. It does not validate the browser
GUI, external production datasets, production-scale model quality, or the
historic TU Delft services that are not included in the repository.
