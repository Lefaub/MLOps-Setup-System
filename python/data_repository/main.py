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

import os

import pandas as pd
import urllib3
from minio import Minio
from minio.error import S3Error

urllib3.disable_warnings()

# MinIO Server-Konfiguration
MINIO_ENDPOINT = minio_service_1_ip  # MinIO API-Endpunkt innerhalb des Clusters
ACCESS_KEY = "rootuser"  # Ersetze mit deinem Access Key
SECRET_KEY = "rootpass123"  # Ersetze mit deinem Secret Key
BUCKET_NAME = "energiedaten"
FILENAME = "/home/data_repository/monthly_hourly_load_values_2022_DE.csv"  # Beispieldatei

# Verbindung zum MinIO-Server herstellen
client = Minio(
    MINIO_ENDPOINT,
    access_key=ACCESS_KEY,
    secret_key=SECRET_KEY,
    secure=False  # MinIO läuft ohne HTTPS
)

try:
    # Prüfen, ob der Bucket existiert, sonst erstellen
    if not client.bucket_exists(BUCKET_NAME):
        client.make_bucket(BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' wurde erstellt.")
    else:
        print(f"Bucket '{BUCKET_NAME}' existiert bereits.")

    # CSV-Datei laden
    if os.path.exists(FILENAME):
        print(f"Lade Datei '{FILENAME}'...")
        df = pd.read_csv(FILENAME)
        print("Datei erfolgreich geladen:")
        print(df.head())
    else:
        print(f"Fehler: Datei '{FILENAME}' nicht gefunden.")
        exit(1)

    # Datei in MinIO hochladen
    client.fput_object(BUCKET_NAME, FILENAME, FILENAME)
    print(f"Datei '{FILENAME}' wurde in den Bucket '{BUCKET_NAME}' hochgeladen.")

except S3Error as e:
    print(f"Fehler: {e}")
