
echo Time-Series
echo Copying python files
kubectl cp python/model_selection/. ml-serving-deployment-58b68f6c58-6pj4j:/home
echo Copying config files
kubectl cp tools/model_selection_config/. ml-serving-deployment-58b68f6c58-6pj4j:/home
 echo Create directory on node
kubectl exec ml-serving-deployment-58b68f6c58-6pj4j --  mkdir /home/timeshap
kubectl cp tools/timeshap/src/timeshap/. ml-serving-deployment-58b68f6c58-6pj4j:/home/timeshap
kubectl exec ml-serving-deployment-58b68f6c58-6pj4j -- pip install -r /home/requirements.txt
kubectl exec ml-serving-deployment-58b68f6c58-6pj4j -- streamlit run /home/main.py