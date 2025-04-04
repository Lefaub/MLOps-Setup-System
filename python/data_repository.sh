
kubectl exec ml-serving-deployment-58b68f6c58-6pj4j -- mkdir /home/data_repository/data 
kubectl cp python/data_repository/. ml-serving-deployment-58b68f6c58-6pj4j:/home/data_repository

kubectl cp tools/minio_config/. ml-serving-deployment-58b68f6c58-6pj4j:/home/data_repository
kubectl exec ml-serving-deployment-58b68f6c58-6pj4j -- pip install -r /home/data_repository/requirements.txt
kubectl exec ml-serving-deployment-58b68f6c58-6pj4j -- python3 /home/data_repository/main.py