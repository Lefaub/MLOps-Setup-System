<h1>End to end Explanatory ML System Architecture</h1>
This repository is part of the public deliverable D 6.7 in the research project EXPLAIN. It contains the code of the final explanatory MLOps system. The system is a prototype, demonstrating model-based automation in MLOps setups.

<h2>Prerequisites</h2>
Setting up the MLOps system requires several steps as prerequisites. 

<ol>
  <li>First, a Kubernetes cluster with at least one node needs to be setup (<a href="https://www.uni-hildesheim.de/gitlab/sse/explain-initial-architecture-implementation/-/tree/main/Infrastructure?ref_type=heads">Kubernetes Readme</a>).</li>
  <li>Install docker</li>
  <li>Docker login</li>
  <li>Create access token (read, write delete)</li>
  <li>Install <a href ="https://helm.sh/docs/intro/install/">helm</a></li>
  <li>Install python and python-pip</li>
  <li>pip install flask kubernetes</li>
</ol>

<h2>Running the UI for the MLOps platform setup</h2>
<ol>
  <li>Clone this repository on the master node and clone the Tools below in the respective folders</li>
  <li>Run "sudo python main.py"</li>
  <li>Configure the data type, version tag, dockerhub name and all required features on the homepage.</li>
  <li>Click on "Generate" and on "Go to running platform services" button.</li>
  <li>Wait until containers are set up. Click on "ML pipeline code generation" and "Run ML pipeline".</li>
  <li>A new tab opens which allows to run scripts that enable the user to set up a ML pipelines, connecting the containers, selecting models, start training, inference services, or XAI methods.</li>
</ol>

<h2>Tools</h2>

<ul>
  <li><a href="https://www.uni-hildesheim.de/gitlab/explain/data-drift-simulator">Life Data and Drift Simulation</a></li>
  <li><a href="https://github.com/malikhunain/Optimized-Web-Interface">Image Drift Detection UI</a></li>
  <li><a href="https://github.com/Amirrgrbn/EXPLAIN_architecture">XAI and Feedback UI</a></li>
</ul>

<h2>Acknowledgements</h2>
This work is supported by the project EXPLAIN, funded by the German Federal Ministry of Education under grant 01—S22030E. Any opinions expressed herein are solely by the authors and not the funding agency. 

This project is licensed under the [MIT License](./LICENSE).
