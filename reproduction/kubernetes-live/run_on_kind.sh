#!/usr/bin/env bash
# Creates a new disposable test cluster; never selects an existing kubeconfig.
set -euo pipefail
kit="$(cd "$(dirname "$0")" && pwd)"
commit=01209591e1d020dafc388a9b77b6985122308d6b
profile="${1:-both}"
case "$profile" in both|time_series|visual_inspection) ;; *) echo "Use both, time_series or visual_inspection." >&2; exit 2;; esac
for bin in docker kind kubectl git; do
  command -v "$bin" >/dev/null || { echo "Missing command: $bin" >&2; exit 2; }
done
python_bin="${PYTHON_BIN:-python3}"
docker info --format '{{.ServerVersion}}' >/dev/null
cluster="paper-live-$(date -u +%y%m%d%H%M%S)-$$"
runroot="$(mktemp -d "$kit/$cluster.XXXXXX")"
chmod 700 "$runroot"
echo "Run directory: $runroot"
echo "The cluster will remain for inspection. Cleanup: kind delete cluster --name $cluster"
"$python_bin" -m venv "$runroot/venv"
"$runroot/venv/bin/python" -m pip install -r "$kit/supplement/requirements.txt"
repo="$runroot/MLOps-Setup-System"
git -c core.autocrlf=false clone https://github.com/Lefaub/MLOps-Setup-System.git "$repo"
git -C "$repo" checkout --detach "$commit"
server="${MINIO_IMAGE:-docker.io/minio/minio:RELEASE.2025-04-22T22-12-26Z}"
client="${CLIENT_IMAGE:-docker.io/library/python:3.12-slim}"
pin() {
  docker pull "$1" >&2
  if [[ "$1" == *@sha256:* ]]; then printf '%s\n' "$1"
  else docker image inspect --format '{{index .RepoDigests 0}}' "$1"
  fi
}
server_pin="$(pin "$server")"
client_pin="$(pin "$client")"
kubeconfig="$runroot/kubeconfig"
kind create cluster --name "$cluster" --kubeconfig "$kubeconfig" --wait 3m \
  --image 'kindest/node:v1.32.2@sha256:f226345927d7e348497136874b6d207e0b32cc52154ad8323129352923a3142f'
chmod 600 "$kubeconfig"
umask 077
printf 'kind=%s\nnode_image=%s\nhost=%s\n' "$(kind version)" \
  'kindest/node:v1.32.2@sha256:f226345927d7e348497136874b6d207e0b32cc52154ad8323129352923a3142f' \
  "$(uname -sm)" > "$runroot/runner.txt"
"$runroot/venv/bin/python" "$kit/run_live.py" --repo "$repo" --out "$runroot/evidence" \
  --execute --profile "$profile" --kubeconfig "$kubeconfig" --context "kind-$cluster" \
  --server-image "$server_pin" --client-image "$client_pin"
echo "Review before sharing: $runroot/evidence/evidence.json and $runroot/runner.txt"
