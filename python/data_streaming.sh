
kubectl cp python/data_streaming/. ml-serving-deployment-58b68f6c58-6pj4j:/home
kubectl cp tools/data_streaming_config/. ml-serving-deployment-58b68f6c58-6pj4j:/home
kubectl exec ml-serving-deployment-58b68f6c58-6pj4j -- pip install -r /home/requirements.txt
kubectl exec ml-serving-deployment-58b68f6c58-6pj4j -- python3 /home/main.py