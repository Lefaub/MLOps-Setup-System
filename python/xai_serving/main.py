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

import lime
import lime.lime_tabular
import mlflow
import numpy as np
import pandas as pd
import requests
import shap
import streamlit as st
from mlflow.tracking import MlflowClient
from rich.console import Console
from sklearn.preprocessing import MinMaxScaler

mlflow.set_tracking_uri("http://10.101.132.32:5000")
client = MlflowClient()

DATA_STREAM_URL = "http://10.103.196.92:5020/stream-data/modified?time_interval=0.001"
SESSION_COOKIE = ".eJyNkMtugzAQRX8lmnUgw8MkpqtK7bLbbkplGXsQTgFHtkkbofx7SUObLrMazdU9dx4TKO8aEewHDVACY5oxvk3qDDkmeVpTQbrQknOFTZZjhsmO8TqBNajRORqC0DJIT2GGx0Nnpfab3g6h7U6itaOby0UUR9mN5EWKaSqenmPlj3NEb7VpDDlhnSYH5RukHJElWx6pJi-iPMddJBumIqS0qHGbZ9QU8H4jPZTTfVAJUwWH08bWe1KhgnJVwbK6-E2LpdYmGDvclMdFeVmECtYz2AszaPq6pOC1_zQ6tP96ZbuxH65jXi-3L-BfTLnKEDH-sRt9Nd5zSAVnOK_B04GcDHb-GjzA-RsieIw9.Z90OLA.g5k3b1rP6uKvW_d3Ft9VbzaiJyg"
console = Console()

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "en-US,en;q=0.5",
           "Upgrade-Insecure-Requests": "1",
           "Priority": "u=0, i"}

session = requests.Session()
domain = re.sub(r':5020', '', "10.103.196.92:5020")
session.cookies.set("session", SESSION_COOKIE, domain=domain, path="/")

# Lade historische Min/Max-Werte aus dem Trainingsdatensatz
historical_data_path = "/home/monthly_hourly_load_values_2022_DE.csv"
console.print(f"[INFO] Loading historical data from {historical_data_path}")
df = pd.read_csv(historical_data_path, delimiter=";", parse_dates=["TimeTo"], index_col="TimeTo")

# Initialisiere den Scaler
scaler = MinMaxScaler()
scaler.fit(df[["Value"]].values)
console.print("[INFO] Scaler initialized with historical data.")

SEQ_LEN = 24

st.subheader("Modell laden")
experiment_name = "ENTSOE_TimeSeries"
experiment = client.get_experiment_by_name(experiment_name)
if experiment is None:
    st.error(f"Experiment '{experiment_name}' nicht gefunden.")
    exit(1)
experiment_id = experiment.experiment_id
runs = mlflow.search_runs(experiment_ids=[experiment_id], order_by=["start_time DESC"])
if runs.empty:
    st.error("Keine Runs gefunden.")
    exit(1)
latest_run = runs.iloc[0]
run_id = latest_run.run_id

artifacts = client.list_artifacts(run_id)
artifact_paths = [artifact.path for artifact in artifacts]
if "time_series_model" not in artifact_paths:
    st.error("Modell 'time_series_model' nicht gefunden.")
    exit(1)

model_uri = f"runs:/{run_id}/time_series_model"
model = mlflow.pyfunc.load_model(model_uri)
st.success("Modell erfolgreich geladen!")


def fetch_data():
    try:
        response = session.get(DATA_STREAM_URL, headers=HEADERS, stream=True, timeout=10)
        if response.status_code == 200:
            console.print("[INFO] Erfolgreiche Verbindung zum Datenstream!")
        else:
            console.print(f"[ERROR] Verbindung fehlgeschlagen mit Statuscode {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        console.print(f"[ERROR] Konnte Datenstream nicht erreichen: {e}")
        return
    for line in response.iter_lines():
        if line:
            decoded_line = line.decode("utf-8").strip()
            if decoded_line.startswith("data:"):
                decoded_line = decoded_line[len("data:"):].strip()
            if decoded_line:
                try:
                    yield json.loads(decoded_line)
                except json.JSONDecodeError as e:
                    console.print(f"[ERROR] Fehler beim Parsen von JSON: {e}")
                    console.print(f"[DEBUG] Empfangene Daten: {decoded_line}")


def process_stream():
    sequence_buffer = []
    pred_values = st.empty()
    for parsed_data in fetch_data():
        time_to = parsed_data.get("TimeTo", "00:00")
        value = parsed_data.get("Value", 0)
        scaled_value = scaler.transform(np.array([[value]]))[0][0]
        sequence_buffer.append(scaled_value)

        if len(sequence_buffer) < SEQ_LEN:
            continue

        input_data = np.array(sequence_buffer[-SEQ_LEN:]).reshape(1, SEQ_LEN, 1).astype(np.float32)
        prediction = model.predict(input_data)

        # SHAP Erklärung
        background_data = np.zeros((10, SEQ_LEN)).astype(np.float32)
        masker = shap.maskers.Independent(background_data)
        explainer = shap.Explainer(lambda x: model.predict(x.reshape(-1, SEQ_LEN, 1)), masker)
        shap_values = explainer(input_data.reshape(1, SEQ_LEN))

        # LIME Erklärung
        lime_explainer = lime.lime_tabular.LimeTabularExplainer(training_data=np.zeros((10, SEQ_LEN)),
                                                                mode="regression")
        lime_exp = lime_explainer.explain_instance(input_data.flatten(),
                                                   lambda x: model.predict(x.reshape(-1, SEQ_LEN, 1)))

        pred_values.write(f"Eingangsdaten: {input_data}")
        pred_values.write(f"Vorhersage: {prediction}")
        pred_values.write(f"SHAP Werte: {shap_values.values.tolist()}")
        pred_values.write(f"LIME Erklärung: {lime_exp.as_list()}")


if __name__ == "__main__":
    process_stream()
