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
import tempfile

import joblib
import mlflow
import mlflow.tensorflow
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from statsmodels.tsa.arima.model import ARIMA
from tensorflow import keras
from tensorflow.keras import layers

path = "monthly_hourly_load_values_2022_DE.csv"
df = pd.read_csv(path, delimiter=";", parse_dates=["TimeTo"], index_col="TimeTo")

scaler = MinMaxScaler()
df["Value"] = scaler.fit_transform(df[["Value"]])


def create_sequences(data, seq_length):
    sequences, labels = [], []
    for i in range(len(data) - seq_length):
        sequences.append(data[i:i + seq_length])
        labels.append(data[i + seq_length])
    return np.array(sequences), np.array(labels)


seq_length = 24
X, y = create_sequences(df["Value"].values, seq_length)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)

mlflow.set_tracking_uri("http://" + ml_flow_service_service_1_ip)


def train_and_log_model(model_name, model, X_train, y_train, X_test, y_test):
    mlflow.set_experiment(f"{model_name}_TimeSeries")
    with mlflow.start_run():
        if model_name in ["LSTM", "GRU"]:
            history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=50, batch_size=16, verbose=0)
            mlflow.tensorflow.log_model(model, f"{model_name}_model")
        elif model_name == "ARIMA":
            model_fit = model.fit()
            with tempfile.TemporaryDirectory() as temp_dir:
                model_path = os.path.join(temp_dir, "arima_model.pkl")
                joblib.dump(model_fit, model_path)
                mlflow.log_artifact(model_path, "model")
        else:
            model.fit(X_train.reshape(X_train.shape[0], -1), y_train)
            with tempfile.TemporaryDirectory() as temp_dir:
                model_path = os.path.join(temp_dir, f"{model_name}_model.pkl")
                joblib.dump(model, model_path)
                mlflow.log_artifact(model_path, "model")

        model_uri = f"runs:/{mlflow.active_run().info.run_id}/model"
        client = mlflow.tracking.MlflowClient()
        try:
            model_version = mlflow.register_model(model_uri, f"{model_name}_TimeSeries").version
            client.transition_model_version_stage(name=f"{model_name}_TimeSeries", version=model_version,
                                                  stage="Production")
        except Exception as e:
            print(f"Model registration failed: {e}")


# LSTM
lstm_model = keras.Sequential([
    layers.LSTM(50, activation="relu", return_sequences=True, input_shape=(seq_length, 1)),
    layers.LSTM(50, activation="relu"),
    layers.Dense(1)
])
lstm_model.compile(optimizer="adam", loss="mse", metrics=["mae"])
train_and_log_model("LSTM", lstm_model, X_train, y_train, X_test, y_test)

# GRU
gru_model = keras.Sequential([
    layers.GRU(50, activation="relu", return_sequences=True, input_shape=(seq_length, 1)),
    layers.GRU(50, activation="relu"),
    layers.Dense(1)
])
gru_model.compile(optimizer="adam", loss="mse", metrics=["mae"])
train_and_log_model("GRU", gru_model, X_train, y_train, X_test, y_test)

# ARIMA
arima_model = ARIMA(df["Value"], order=(5, 1, 0))
train_and_log_model("ARIMA", arima_model, None, None, None, None)

# XGBoost
xgb_model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6)
train_and_log_model("XGBoost", xgb_model, X_train, y_train, X_test, y_test)

# RandomForest
rf_model = RandomForestRegressor(n_estimators=100, max_depth=10)
train_and_log_model("RandomForest", rf_model, X_train, y_train, X_test, y_test)
