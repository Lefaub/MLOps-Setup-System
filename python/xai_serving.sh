
kubectl cp python/xai_serving/. xai-deployment-5d97649c99-fbfkv:/home
kubectl cp tools/xai_serving_config/. xai-deployment-5d97649c99-fbfkv:/home
kubectl exec xai-deployment-5d97649c99-fbfkv -- pip install -r /home/requirements.txt
kubectl exec xai-deployment-5d97649c99-fbfkv -- streamlit run /home/main.py