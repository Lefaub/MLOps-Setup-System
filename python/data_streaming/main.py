airflow_service_service_1_ip = "10.103.53.196:8080"
airflow_service_pod_1 = "airflow-deployment-5b58db478c-xfkgb"
data_streaming_service_service_1_ip = "10.103.196.92:5020"
data_streaming_service_pod_1 = "data-streaming-deployment-7db4847bc8-s2sdk"
evidently_service_service_1_ip = "10.99.11.196:8000"
evidently_service_pod_1 = "evidently-deployment-9776f7558-cbxhk"
git_server_service_service_1_ip = "10.104.60.12:3000"
git_server_service_service_2_ip = "10.104.60.12:22"
git_server_service_pod_1 = "git-server-deployment-5f4849d6cc-njp2n"
jupyter_service_service_1_ip = "10.100.131.209:80"
jupyter_service_pod_1 = "jupyter-deployment-5d467f85dd-pkw5z"
kubernetes_service_1_ip = "10.96.0.1:443"
label_studio_service_service_1_ip = "10.103.79.44:8080"
label_studio_service_pod_1 = "label-studio-deployment-786d475696-lkm92"
minio_service_1_ip = "10.106.76.125:9000"
minio_pod_1 = "minio-7f859678fd-qpfvs"
minio_console_service_1_ip = "10.103.226.32:9001"
minio_console_pod_1 = "minio-7f859678fd-qpfvs"
ml_flow_service_service_1_ip = "10.101.132.32:5000"
ml_flow_service_pod_1 = "ml-flow-deployment-85c7c7d8b9-sdkfl"
ml_flow_service_pod_2 = "ml-serving-deployment-58b68f6c58-6pj4j"
ml_serving_service_1_ip = "10.107.192.214:8050"
ml_serving_pod_1 = "ml-flow-deployment-85c7c7d8b9-sdkfl"
ml_serving_pod_2 = "ml-serving-deployment-58b68f6c58-6pj4j"
xai_serving_service_1_ip = "10.105.86.213:8040"
xai_serving_pod_1 = "xai-deployment-5d97649c99-fbfkv"
kube_dns_service_1_ip = "10.96.0.10:53"
kube_dns_service_2_ip = "10.96.0.10:53"
kube_dns_service_3_ip = "10.96.0.10:9153"
kube_dns_pod_1 = "kube-apiserver-leonhard-omen-by-hp-laptop-15-dh0xxx"
kube_dns_pod_2 = "kube-controller-manager-leonhard-omen-by-hp-laptop-15-dh0xxx"
kube_dns_pod_3 = "kube-proxy-6sl56"
kube_dns_pod_4 = "kube-proxy-jhtnb"
kube_dns_pod_5 = "kube-proxy-ns2tw"
kube_dns_pod_6 = "kube-proxy-qt656"
kube_dns_pod_7 = "kube-scheduler-leonhard-omen-by-hp-laptop-15-dh0xxx"
import json
import re

import mlflow
import numpy as np
import requests
from mlflow.tracking import MlflowClient
from rich.console import Console

# Setze die Verbindung zu MLflow
mlflow.set_tracking_uri("http://10.101.132.32:5000")

# MLflow Client erstellen
client = MlflowClient()

# Hole die Experiment-ID anhand des Namens
experiment_name = "ENTSOE_TimeSeries"
experiment = client.get_experiment_by_name(experiment_name)
if experiment is None:
    print(f"Experiment '{experiment_name}' not found.")
    exit(1)
else:
    print("[INFO] Experiment found")
experiment_id = experiment.experiment_id

# Suchen nach dem letzten Run im Experiment
runs = mlflow.search_runs(experiment_ids=[experiment_id], order_by=["start_time DESC"])
if runs.empty:
    print("No runs found.")
    exit(1)
else:
    print(runs)

# Neuesten Run auswählen
latest_run = runs.iloc[0]
run_id = latest_run.run_id
print(f"Newest Run: {run_id}")

# Überprüfen, ob das Modell existiert
artifacts = client.list_artifacts(run_id)
artifact_paths = [artifact.path for artifact in artifacts]
if "time_series_model" not in artifact_paths:
    print("Modell 'time_series_model' nicht gefunden.")
    exit(1)
else:
    print("Model time_series_model found")

# Baue die Modell-URI
model_uri = f"runs:/{run_id}/time_series_model"
print(f"Load model from {model_uri}")

# Lade das Modell als PyFuncModel
try:
    loaded_model = mlflow.pyfunc.load_model(model_uri)
    print("Success.")
except Exception as e:
    print(f"Error loading model: {e}")
    exit(1)

# Konfiguration
DATA_STREAM_URL = "http://10.103.196.92:5020/stream-data/modified?time_interval=0.001"
SESSION_COOKIE = ".eJyNkMtugzAQRX8lmnUgw8MkpqtK7bLbbkplGXsQTgFHtkkbofx7SUObLrMazdU9dx4TKO8aEewHDVACY5oxvk3qDDkmeVpTQbrQknOFTZZjhsmO8TqBNajRORqC0DJIT2GGx0Nnpfab3g6h7U6itaOby0UUR9mN5EWKaSqenmPlj3NEb7VpDDlhnSYH5RukHJElWx6pJi-iPMddJBumIqS0qHGbZ9QU8H4jPZTTfVAJUwWH08bWe1KhgnJVwbK6-E2LpdYmGDvclMdFeVmECtYz2AszaPq6pOC1_zQ6tP96ZbuxH65jXi-3L-BfTLnKEDH-sRt9Nd5zSAVnOK_B04GcDHb-GjzA-RsieIw9.Z90OLA.g5k3b1rP6uKvW_d3Ft9VbzaiJyg"
console = Console()

# HTTP-Header setzen (Firefox-User-Agent nachahmen)
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "en-US,en;q=0.5",
           "Upgrade-Insecure-Requests": "1",
           "Priority": "u=0, i"
           }

# Session erstellen und Cookie setzen
session = requests.Session()
domain = re.sub(r':5020', '', "10.103.196.92:5020")
session.cookies.set("session", SESSION_COOKIE, domain=domain, path="/")


def fetch_data():
    try:
        response = session.get(DATA_STREAM_URL, headers=HEADERS, stream=True, timeout=10)
        if response.status_code == 200:
            console.print("[bold green][INFO][/bold green] Erfolgreiche Verbindung zum Datenstream!")
        else:
            console.print(
                f"[bold red][ERROR][/bold red] Verbindung fehlgeschlagen mit Statuscode {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        console.print(f"[bold red][ERROR][/bold red] Konnte Datenstream nicht erreichen: {e}")
        return

    for line in response.iter_lines():
        if line:
            yield line.decode("utf-8")


def parse_json(raw_data):
    try:
        if raw_data.startswith("data:"):
            raw_data = raw_data[len("data:"):].strip()
        return json.loads(raw_data)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Fehler beim Parsen von JSON: {e}")
        print(f"[DEBUG] Empfangene Daten: {raw_data}")  # Debugging-Ausgabe
        return None


def display_stream():
    for raw_data in fetch_data():
        parsed_data = parse_json(raw_data)
        if parsed_data:
            time_to = parsed_data.get("TimeTo", "00:00")
            value = parsed_data.get("Value", 0)
            print(f"TimeTo: {time_to}, Value: {value}")

            try:
                input_data = np.array([[value]])
                predictions = loaded_model.predict(input_data)
                print("Predictions:")
                print(predictions)
            except Exception as e:
                print(f"Fehler bei der Vorhersage: {e}")


if __name__ == "__main__":
    display_stream()
