# S2. Technical validation record

Three records answer different questions: what the original generator emits, what ran on Kubernetes during revision, and what a later rule correction changes. The original lab deployments lack scenario-specific logs.

## Original generator: offline replay

The [tested source](https://github.com/Lefaub/MLOps-Setup-System/tree/01209591e1d020dafc388a9b77b6985122308d6b) was fixed for both profiles. With Python 3.13.5 and Jinja2 3.1.6, two baseline runs per profile produced identical files. A third changed only a stored service address: the generated client used the new address in both variants. The time-series profile emitted 22 platform and 11 pipeline files; the image profile emitted 31 and 14. Three and eight files, respectively, were empty or comment-only. The examples folder contains one unmodified, hash-verified Kubernetes manifest per profile.

## Five steps in the revision tests

1. **Select and validate:** each profile specifies all 44 fields. Both passed the encoded rules; deliberately inconsistent selections failed the offline checks.
2. **Generate:** the same generator emitted distinct profiles. The streaming example and the image-specific XAI example each contain a Deployment and a Service; generating them is not proof that every selected service ran.
3. **Deploy:** on a disposable kind cluster, the live harness deployed the selected MinIO workload with an overlay and an MLflow registry in each profile’s namespace. It checked service rollout and reachability.
4. **Discover:** the live harness obtained a fresh inventory and storage endpoint independently for each profile. The historical archive contains only one unlabelled inventory (13 services; 24 pods recorded as running).
5. **Bind and execute:** the generated storage client used the discovered endpoint. A separate application probe trained and registered a model, reloaded it, ran inference, computed an explanation and recorded simulated feedback before retraining.

## Live run and boundary

The [primary run](https://github.com/Lefaub/MLOps-Setup-System/actions/runs/45399032543) passed four orchestration checks and ten application checks per profile. Across five development jobs on this branch, three passed for both profiles, one failed during generation and one during MLflow rollout. Workflow revisions differed. The rollout command returned exit 1 in both profiles; 720 seconds was its time limit, not a measured failure time. Pod diagnostics were not retained.

The OS was Ubuntu 24.04.5 x86-64 and kind v0.27.0 used a single control-plane node (server 1.32.2). The recorded client was kubectl 1.37.2. CPU and RAM were not recorded for this runner. The evidence directory contains the run record, environment, attempt ledger, exact images, and per-profile checks. This is evidence for the tested synthetic paths; industrial price forecasts, operator interaction, explanation quality and deployment reliability were not measured.

## Separate feature correction and verification

The [follow-up fix](https://github.com/Lefaub/MLOps-Setup-System/commit/9f0f76208897b28fb1eeda6f29cbeb207b992eb8) restored a lost prerequisite and corrected hardware exclusions in the form. A repeatable Boolean audit found 26 distinct clauses before and 27 after the change. Both profiles remain valid. The original renderer passed three of eight form checks; the corrected renderer passed all eight, including in [CI](https://github.com/Lefaub/MLOps-Setup-System/actions/runs/45452289178). This was a simulated form test, not a new Kubernetes or interactive usability run.

Start with **python verify_evidence.py** in S2. The README gives exact commands for source replay, the live workflow with pinned images, and both feature audits. The prospective manual-comparison protocol is a study design, not a record of additional participants or measurements.
