# S2 · What can be reproduced from the MLOps prototype?

**How to use this supplement.** Start with **Validation_summary.pdf**. From this directory, run **python verify_evidence.py** to check the included evidence offline (standard Python 3, no cluster). The original generator, the live-test workflow and the later feature-form correction have different purposes and are pinned separately. All reported study evidence is supplied with the journal submission or linked by commit; a draft release is not needed for review. The historical lab deployments are not reproduced.
 
| Record | Version and question |
|---|---|
| Original generator | [01209591](https://github.com/Lefaub/MLOps-Setup-System/tree/01209591e1d020dafc388a9b77b6985122308d6b). What does this generator emit and bind for each profile? |
| Live application test | [33488eda](https://github.com/Lefaub/MLOps-Setup-System/tree/33488eda3d8bb0018296c30e7abc5d46531cad43). Which services and application checks ran with the original generator? |
| Feature-form follow-up | [Correction 9f0f7620](https://github.com/Lefaub/MLOps-Setup-System/commit/9f0f76208897b28fb1eeda6f29cbeb207b992eb8); [CI head fd779c50](https://github.com/Lefaub/MLOps-Setup-System/tree/fd779c508cafa32748cf312d118bdb1174bf3bd7). Which rule and form tests pass with the correction? No Kubernetes run is attributed to this version. |

Verify the files as supplied with `sha256sum -c SHA256SUMS` from this directory.

## Artifact and exact execution

- Immutable tested source: [Lefaub/MLOps-Setup-System, 01209591e1d020dafc388a9b77b6985122308d6b](https://github.com/Lefaub/MLOps-Setup-System/tree/01209591e1d020dafc388a9b77b6985122308d6b). This identifies the source of the **new** replay. The commit used on the historical lab machines is unknown.
- Direct files: [feature model](https://github.com/Lefaub/MLOps-Setup-System/blob/01209591e1d020dafc388a9b77b6985122308d6b/feature_model.fm), [generator](https://github.com/Lefaub/MLOps-Setup-System/blob/01209591e1d020dafc388a9b77b6985122308d6b/script_generation.py), [platform templates](https://github.com/Lefaub/MLOps-Setup-System/blob/01209591e1d020dafc388a9b77b6985122308d6b/code_templates.json), [pipeline templates](https://github.com/Lefaub/MLOps-Setup-System/blob/01209591e1d020dafc388a9b77b6985122308d6b/ml_pipeline_templates.json), [archived resource inventory](https://github.com/Lefaub/MLOps-Setup-System/blob/01209591e1d020dafc388a9b77b6985122308d6b/kubernetes_resources.txt). Input content is checked against `input_sha256.json` on every run.
- Related [EXPLAIN infrastructure repository](https://www.uni-hildesheim.de/gitlab/sse/explain-initial-architecture-implementation/) and [dissertation](https://doi.org/10.25528/372), chs. 16–17 and Appendix E. Neither is used as the source of templates for this replay.
- New offline run environment: Debian 13, Linux x86-64; the operating system reported AMD EPYC 9V45, 9 logical CPUs available to the process, and 10,206,472 KiB visible RAM. No Kubernetes cluster, GPU, container runtime, live endpoint or credentials were used. Python 3.13.5, Jinja2 3.1.6, MarkupSafe 2.1.5, PyYAML 6.0.2. These describe the replay host, not the original cluster. It is unnecessary to match the CPU/RAM for a byte comparison.

From the extracted `S2_Technical` directory, using Python 3.13.5:

```sh
git clone https://github.com/Lefaub/MLOps-Setup-System.git ../MLOps-Setup-System
git -C ../MLOps-Setup-System checkout --detach 01209591e1d020dafc388a9b77b6985122308d6b
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python replay.py --repo ../MLOps-Setup-System --out reproduced
diff -u evidence/artifact_sha256.csv reproduced/artifact_sha256.csv
```

Every run starts with a fresh temporary output tree and imports the original generator; generated code is not executed. `evidence/runs.json` records versions, scenario, run identity, profile/inventory hashes, file counts and checks. `evidence/artifact_sha256.csv` records every emitted path and SHA-256 by run and stage. Two byte-exact, non-sensitive manifests from the first baseline run are included in **examples/**; the replay regenerates them in **reproduced/examples/** and every emitted file is listed by hash. Other generated files can contain demonstration configuration values and are not distributed. On a different platform the environment entry in `runs.json` can differ.

## Exact feature selections and observed outputs

`profiles/time_series.json` and `profiles/visual_inspection.json` are **new author-review replay configurations**, not recovered original selections. Each specifies all 44 named fields. Unselected checkboxes are `false`. Both use a dummy registry account, tag `review-r1`, and memory field `512`; no uploads occur. Both activate CPU, serialization, packaging, model selection/training, guided selection, streaming, repository/S3, IDE, orchestration and monitoring. The time-series profile uses `Time-Series` and `Conventional`, and enables simulation and drift detection. The image profile selects `Image` and `NN`, collection/labeling, XAI selection, visualization and serving, incremental explanatory training and image prediction/explanation feedback. The JSON files, rather than this prose, define the exact selections. Some headers such as model registry are emitted without a user activation field; a feature selection is not itself a test of runtime behavior.

| Profile | Fresh archived-inventory runs | Changed-address runs | Platform / pipeline files per run | Static observations |
|---|---:|---:|---:|---|
| Time series | 2 | 1 | 22 / 11 | 7 YAML files containing 15 Kubernetes resource documents; 4 nonempty pipeline Python files parsed; 3 emitted files empty or comments only |
| Visual inspection | 2 | 1 | 31 / 14 | 10 YAML files containing 21 resource documents; 5 nonempty pipeline Python files parsed; 8 emitted files empty or comments only |

The time-series branch reads the named German **electricity-load** CSV for 2022. It does not establish a price-forecasting result. The image branch generates the image storage and XAI paths. The replay does not train a classifier, generate an explanation, execute an operator feedback session, or measure correctness, throughput or reliability.

## Evidence for the five validation steps

| Step | What the profiles demonstrate | Boundary |
|---|---|---|
| 1. Validate configuration | Each 44-field profile passes the independent checker; deliberately broken dependencies and conflicting hardware are rejected in the offline controls. The live harness reads the same files, identified by their hashes. | No user completed a configuration task; see the separate form regression. |
| 2. Generate artifacts | The original generator emits different platform and pipeline artifacts per profile. The packaged time-series streaming and image XAI manifests each contain a Deployment and a Service; their hashes match the baseline output CSV. | Emitting a service manifest does not show that every service ran. |
| 3. Deploy | Each live profile used a separate namespace on a disposable kind cluster. The test overlaid the generated MinIO workload and deployed the MLflow registry used by the harness; rollout and endpoint checks passed in the primary run. | This is a selected deployment path, not the entire original platform. An earlier rollout check failed. |
| 4. Discover services | The primary live run queried Kubernetes and recorded fresh inventory hashes and ready storage endpoints for each profile. The offline replay independently exercised the parser on a stored inventory. | The unlabelled historical inventory cannot be assigned to either original deployment. |
| 5. Bind and use endpoints | Changing only the stored address changed the generated client's binding offline. The original generator's storage client used the discovered live MinIO endpoint. A separate probe then exercised training, MLflow registry, inference, explanation and simulated feedback/retraining. | The probe is not the emitted XAI service or a real operator session. Neither price-forecast accuracy nor industrial performance was tested. |

## Prospective protocol for full-platform validation (not executed)

The original prototype describes Ubuntu 22.04, a control plane plus at least one worker, Flannel, Kubernetes and Docker; the dissertation gives 1.24.7 (Kubernetes), 26.1.3 (Docker) and 3.12.3 (Python) as examples, not a complete per-scenario lockfile. `dep/requirements.txt` includes unpinned tools such as MLflow, Evidently and scikit-learn; templates use tags such as `python:3.10` and `python:3.10-slim`. Helm, images and external tool repositories also need pinned versions for a live replay. Refer to the [pinned upstream setup README](https://github.com/Lefaub/MLOps-Setup-System/blob/01209591e1d020dafc388a9b77b6985122308d6b/README.md).

1. Use a fresh dedicated test cluster and clean repository checkout for each profile; record commit, profile file and hash, UTC start/end, node count/roles, CPU/RAM, GPU, OS/kernel, storage class and network plugin. Export the versions from `kubectl version -o yaml`, `kubectl get nodes -o wide`, `docker version`, `helm version`, `python --version` and `python -m pip freeze`. Record resolved container digests, external tool commits, and the test data checksum. Strip credentials and identifying addresses from material shared publicly.
2. In the disposable checkout, configure authorized test registry and storage settings and pin external resources. Preserve the resulting profile and exact changes from the supplied offline profile. Start the configurator locally (`flask --app main run --host 127.0.0.1 --port 5000` in its prepared runtime). Using the UI or an HTTP session, set the profile via `POST /update`; retain its session for `GET /get_config` and `POST /code_generation`. Compare the saved profile and generated manifest with the chosen scenario.
3. In that test environment run the selected deployment through `POST /run_deployment`. Record the underlying build/deploy commands and exit codes. For each expected deployment, run `kubectl -n "$namespace" rollout status deployment/"$deployment" --timeout=300s`. Save node and pod conditions, ready replica counts and image IDs, and inspect applicable Jobs and PVCs separately. A `Running` pod alone is insufficient.
4. Request `GET /platform_services` after rollout; the application writes a fresh resource inventory. Keep the dated per-profile copy and compare the expected service ports and ready EndpointSlices against the live API (`kubectl -n "$namespace" get services,endpointslices -o wide`). Record missing services and all failed checks.
5. With the same session, use `POST /run_ml_pipeline` to generate pipeline files from the newly discovered inventory. Confirm the service variable reaches the consumer, then run a profile-specific client health or artifact round-trip check with non-sensitive test data. Record expected/actual outcome, exit code, timestamps and artifact hash. The endpoint name in the UI is not evidence that a client executed successfully. Count and retain failures as well as successes. If price forecasting is claimed, supply an actual price dataset, forecast output and corresponding validation; if interactive XAI is claimed, record an inference/explanation/feedback cycle with a fixture image and the resulting event.

## Reviewer 1: automated Boolean audit and configuration-to-artifact trace

The unmodified [runtime feature model](https://github.com/Lefaub/MLOps-Setup-System/blob/01209591e1d020dafc388a9b77b6985122308d6b/feature_model.fm) is also supplied byte-for-byte as **feature_model.fm**. The [separate IVML description](https://github.com/Lefaub/MLOps-Setup-System/blob/01209591e1d020dafc388a9b77b6985122308d6b/PL_MLOps_platform.ivml) describes a distinct model and was not input to this audit. Both generator catalogs are linked above; their activation rules and templates are the transformation specification for the replay. The commit-pinned links are immutable identifiers, and this supplement carries the model, configurations, analysis and evidence. It is not a new permanent third-party archive of the entire implementation or a frozen deployment image.

    python feature_audit.py --repo ../MLOps-Setup-System --output reproduced_feature_audit.json
    diff -u evidence/feature_audit.json reproduced_feature_audit.json

The checker translates requires A→B to a clause (¬A ∨ B), and excludes to (¬A ∨ ¬B). It checks the entire 39-checkbox projection, with each checkbox optional under an implicit mandatory root. The base admits a configuration; every feature is selectable and deselectable in some valid configuration. Removing any of the 26 distinct clauses permits a violation of that clause, so none is logically redundant relative to the others. Six extra declarations duplicate symmetric hardware exclusions. The runtime JSON parser keeps the last of two requires keys for guided model selection: it enforces data streaming while the listed model-selection prerequisite is discarded. Both replay profiles include both prerequisites. The input was not edited to retrofit the intended behavior; the separate follow-up below restores the lost dependency without changing this snapshot. This audit does not cover the non-Boolean memory-size gate, an IVML hierarchy, or execution of the generated assets.

| Profile / selection | Representative output or input link | Checked result |
|---|---|---|
| Both: data store selected | src/kubernetes/data_repository/deployment.yml | Representative deployment file emitted in both profiles |
| Time series: data_type Time-Series | python/data_repository/main.py | Uses German electricity load CSV, not price data |
| Image: data_type Image, XAI serving and incremental explanatory training enabled | src/kubernetes/xai_serving/deployment.yml; src/kubernetes/incremental_explanatory_training/deployment.yml; python/xai_serving/main.py | Image/XAI artifacts emitted; absent in the time-series run |
| Both: stored MinIO endpoint, then alternate input | python/data_repository/main.py | Client uses the bound address; changing only the stored address changed the assignment and digest |
| Live endpoint binding | Per-profile fresh inventory and storage round-trip in the primary live evidence | Both synthetic profiles pass; the original lab deployments have no per-profile logs. |

The six offline runs passed the specified profile, emission and binding checks. Static inspection observed no invalid YAML or pipeline Python parse errors among parsed files, but found empty/comment-only emissions (three time-series, eight image per run); those paths are recorded as diagnostics. This is not a test of image availability, workload readiness, or live service connectivity.

## Live application test and reproducible command

The [primary run 45399032543](https://github.com/Lefaub/MLOps-Setup-System/actions/runs/45399032543) executed both profiles with deterministic synthetic inputs. The generator was 01209591; the harness and [workflow](https://github.com/Lefaub/MLOps-Setup-System/blob/33488eda3d8bb0018296c30e7abc5d46531cad43/.github/workflows/application-live.yml) were 33488eda. The [job setup and output](https://github.com/Lefaub/MLOps-Setup-System/actions/runs/45399032543/job/138462451743), original evidence and runner record supply the environment information in **evidence/application-live/environment.json**.

Use a disposable Linux environment with Docker, Git, Python, kubectl and kind v0.27.0. From a **separate checkout of the harness commit**, run the command below. Supplying the observed digests matters: the unmodified script otherwise resolves the mutable Python and MLflow tags again. It creates a uniquely named cluster and leaves it available for inspection; use the cleanup command printed by the harness after collecting the new evidence.

```sh
git clone https://github.com/Lefaub/MLOps-Setup-System.git mlops-live-harness
cd mlops-live-harness
git checkout --detach 33488eda3d8bb0018296c30e7abc5d46531cad43
export MINIO_IMAGE='docker.io/jcometki/minio@sha256:3f97c5651cb6662b880c787a232b6b34fec8d8922e08d6617b25d241a21164bb'
export CLIENT_IMAGE='python@sha256:a0e2dd78cc679ddfffea960fe45ecfcff9ac2f68d67917a0edfcde5c2100151b'
export MLFLOW_IMAGE='ghcr.io/mlflow/mlflow@sha256:ae2b2faf8c8ce2bd356e99f268eb2fa652f6bcf9c7c27c84241d519d4c454ce7'
bash reproduction/application-live/run_on_kind.sh both
```

The primary job used Ubuntu 24.04.5 x86-64 (runner image 20261116.133.1), the default one-control-plane-node kind topology, and the pinned node image recorded in runner.txt. The archive records kubectl **1.37.2** and server **1.32.2**. The observed commands succeeded, but that pairing is outside the [Kubernetes supported client–server minor-version range](https://kubernetes.io/releases/version-skew-policy/#kubectl). A repeat using a matching 1.32.x client should be labelled as a new environment. CPU model, vCPU count, host RAM and allocatable node resources were not recorded; the offline replay host specifications do not apply to the live job. For a new run, capture host CPU/RAM and the per-node resource capacities from that run without disclosing names, addresses or credentials. Direct Python component versions, fixture hashes, image digests, profile hashes and acceptance checks are in evidence.json; a complete transitive dependency lockfile is not claimed.

**All five application-workflow jobs on the test branch on 24 November 2026:** [45390543301](https://github.com/Lefaub/MLOps-Setup-System/actions/runs/45390543301) failed during generation (dictionary-conversion ValueError in both profiles); [45390896384](https://github.com/Lefaub/MLOps-Setup-System/actions/runs/45390896384) failed during MLflow rollout (exit 1 in both profiles). The command set a maximum of 720 s; this does not establish an elapsed duration of 720 s or a pod-level cause. [45395643264](https://github.com/Lefaub/MLOps-Setup-System/actions/runs/45395643264), [45395678860](https://github.com/Lefaub/MLOps-Setup-System/actions/runs/45395678860) and the primary run passed all four orchestration and ten application checks for each profile. Per-run commits, triggers and per-profile outcomes are supplied in **workflow_attempts.json** inside **evidence/application-live/**. The earlier [storage-only run](https://github.com/Lefaub/MLOps-Setup-System/actions/runs/45373698298) is not in this count. These development attempts span different workflow commits; a reliability or speed estimate would not follow from their outcomes.

## Feature correction (separate from the live proof)

The original rendered form omitted one prerequisite for guided model selection and could undo a hardware exclusion while visiting later fields. The [fix](https://github.com/Lefaub/MLOps-Setup-System/commit/9f0f76208897b28fb1eeda6f29cbeb207b992eb8) preserves both prerequisites and computes the hardware exclusions before setting field availability. Five of eight checks failed on the original; eight passed on the corrected renderer, locally and in the [follow-up CI run](https://github.com/Lefaub/MLOps-Setup-System/actions/runs/45452289178). Both exact form renderers, both models, the unchanged CI test, licence, source blob IDs, local output and a compact CI record are in **feature_followup/**. From S2:

```sh
python feature_audit.py --repo feature_followup/original --output original.json
python feature_audit.py --snapshot followup --repo feature_followup/fixed --output fixed.json
diff -u evidence/feature_audit.json original.json
diff -u feature_followup/boolean_fixed.json fixed.json
node feature_followup/test_dependencies.cjs feature_followup/original
# Expected: 3 pass, 5 fail; this baseline invocation intentionally exits 1.
node feature_followup/test_dependencies.cjs feature_followup/fixed
# Expected: 8 pass, 0 fail; exit 0.
```

The 39-checkbox projection has 26 distinct clauses at the original commit and 27 after the fix. Under the stated mandatory-root interpretation both are satisfiable, both profiles remain valid, and neither version has dead features, false-optional features or redundant **distinct** clauses. Six symmetric duplicate declarations remain. These are tests of rule semantics and JavaScript with a simulated document, not a browser session, full conceptual-model proof or validation of deployments using the fix.

For the proposed controlled comparison with manual setup, see **Prospective_comparison.md**. This is not a result of the current study.
