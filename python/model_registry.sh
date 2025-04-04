

    kubectl cp python/model_registry/. ml-serving-deployment-58b68f6c58-6pj4j:/
    kubectl cp tools/mlflow_config/. ml-serving-deployment-58b68f6c58-6pj4j:/
    kubectl exec ml-serving-deployment-58b68f6c58-6pj4j  -- pip install -r /requirements.txt
    kubectl exec ml-serving-deployment-58b68f6c58-6pj4j  -- python3 /main.py
    