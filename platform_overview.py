import os
import shutil
import subprocess

from kubernetes import client, config


def get_services():
    # Load Kubernetes configuration
    kubeconfig_path = os.path.expanduser("~/kubeconfig.yaml")  # Store in home directory

    # Get the kubeconfig content
    kubeconfig_data = subprocess.run(["kubectl", "config", "view", "--raw"], capture_output=True, text=True).stdout

    # Write to file
    with open(kubeconfig_path, "w") as f:
        f.write(kubeconfig_data)

    # Load kubeconfig
    config.load_kube_config(kubeconfig_path)
    v1 = client.CoreV1Api()

    # Get services
    services = v1.list_service_for_all_namespaces().items
    service_data = []
    for svc in services:
        service_data.append({
            "name": svc.metadata.name,
            "namespace": svc.metadata.namespace,
            "cluster_ip": svc.spec.cluster_ip,
            "ports": [f"{port.port}/{port.protocol}" for port in svc.spec.ports]
        })

    # Get pods
    pods = v1.list_pod_for_all_namespaces().items
    pod_data = []
    for pod in pods:
        pod_data.append({
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "node": pod.spec.node_name,
            "status": pod.status.phase
        })

    # Write to file
    file_path = "kubernetes_resources.txt"
    with open(file_path, 'w') as file:
        file.write("=== Services ===\n")
        for service in service_data:
            file.write(f"Service Name: {service['name']}\n")
            file.write(f"Namespace: {service['namespace']}\n")
            file.write(f"Cluster IP: {service['cluster_ip']}\n")
            file.write(f"Ports: {', '.join(service['ports'])}\n\n")

        file.write("=== Pods ===\n")
        for pod in pod_data:
            file.write(f"Pod Name: {pod['name']}\n")
            file.write(f"Namespace: {pod['namespace']}\n")
            file.write(f"Node: {pod['node']}\n")
            file.write(f"Status: {pod['status']}\n\n")
    return (service_data, pod_data)


def get_platform_overview():
    TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kubernetes Platform Services</title>

    <style>
                .header {
	    position: relative;
	    display: flex;
	    justify-content: center; /* Centers the h1 */
	    align-items: center;
	    padding: 20px;
	    background: linear-gradient(90deg, #333, #555); /* Smooth gradient */
	    border-radius: 10px;
	    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
	    color: white;
	    }
	.header img {
	    position: absolute;
	    left: 20px; /* Keeps logo to the left */
	    max-width: 120px; /* Adjusted size */
	    height: auto;
	    border: 2px solid white; /* Softer contrast */
	    border-radius: 8px; /* Rounded corners */
	    padding: 5px;
	    background-color: white;
	}
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            max-width: 800px;
            margin: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1);
            background: white;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #333;
            color: white;
            text-transform: uppercase;
            font-size: 14px;
        }
        tr:hover {
            background-color: #f1f1f1;
        }
        button {
            background-color: #333;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            margin-top: 10px;
        }
        button:hover {
            background-color: #0056b3;
        }
        .service-links {
            margin-top: 20px;
            text-align: left;
        }
        .service-links a {
            display: block;
            padding: 5px;
            color: #007BFF;
            text-decoration: none;
            font-weight: bold;
        }
        .service-links a:hover {
            text-decoration: underline;
        }
    </style>

    <script>
        setTimeout(function() { location.reload(); }, 20000); // Refresh every 20 seconds

        function executeAction(url, button) {
            button.innerText = "Running...";
            button.disabled = true;

            fetch(url, { method: "POST" })
            .then(response => response.json())
            .then(data => {
                button.innerText = data.message;
                setTimeout(() => {
                    button.innerText = button.getAttribute("data-original-text");
                    button.disabled = false;
                }, 3000);
            })
            .catch(error => {
                console.error("Error:", error);
                button.innerText = "Error!";
                setTimeout(() => {
                    button.innerText = button.getAttribute("data-original-text");
                    button.disabled = false;
                }, 3000);
            });
        }
    </script>
</head>
<body>
    <header class="header">
    	<h1>Kubernetes Platform Services</h1>
        <img src="https://explain-project.eu/wp-content/uploads/2022/10/logo.jpg" alt="EXPLAIN Project Logo" width="100">
    </header>
    <div class="container">

        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Namespace</th>
                    <th>Cluster IP</th>
                    <th>Ports</th>
                </tr>
            </thead>
            <tbody>
                {% for service in services %}
                <tr>
                    <td>{{ service.name }}</td>
                    <td>{{ service.namespace }}</td>
                    <td>{{ service.cluster_ip }}</td>
                    <td>{{ ", ".join(service.ports) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <button onclick=window.location.href="/">Config and script generation</button>

        <button data-original-text="Run deployment scripts" onclick="executeAction('/run_deployment', this)">
            Run deployment scripts
        </button>

        <button data-original-text="ML pipeline code generation" onclick="executeAction('/run_ml_pipeline', this)">
            Run ML pipeline code generation
        </button>
        
        <button onclick="window.open('/start', '_blank')">Run ML pipeline</button>

        <button data-original-text="Delete scripts and deployments" onclick="executeAction('/delete', this)">
            Delete scripts and deployments
        </button>

                <!-- Service Links Overview -->
        <div class="service-links">
            <h2>Service Links</h2>
            {% for service in services %}
                {% for port in service.ports %}
                    <a href="http://{{ service.cluster_ip }}:{{ port.split('/')[0] }}" target="_blank">
                        {{ service.name }} ({{ service.cluster_ip }}:{{ port }})
                    </a>
                {% endfor %}
            {% endfor %}
        </div>

        <br><br>
        <p>Developed and coded by Leonhard Faubel-Teich</p>
    </div>
</body>
</html>
"""
    return TEMPLATE


def run_all_deployment_scripts():
    """Executes all shell scripts in the 'build_scripts' folder."""
    script_dir = "build_scripts"

    if not os.path.isdir(script_dir):
        print("Error! Directory {script_dir} not found")
        return {"message": "Error!", "output": f"Directory '{script_dir}' not found."}

    # results = []

    try:
        # Alle .sh-Skripte im Verzeichnis finden und ausführen
        for script in sorted(os.listdir(script_dir)):  # Sortiert für konsistente Reihenfolge
            if script.endswith(".sh"):
                print(script)
                script_path = os.path.join(script_dir, script)
                subprocess.run(f"chmod +x {script_path}", shell=True)  # Skript ausführbar machen

                result = subprocess.run(script_path, shell=True, check=True, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
                print(result)
                # results.append({"script": script, "message": "Success!", "output": result.stdout})
    except subprocess.CalledProcessError as e:
        print(f"Error executing {script}: {e.stderr}")
        print(f"Output before error: {e.stdout}")

    return ""


# def delete_all_kubernetes_deployments():
#    """Deletes all Kubernetes deployments and associated files from 'build_scripts'."""
#    script_dir = "build_scripts"
#    results = []

#    try:
# Alle laufenden Deployments, Pods und Services löschen
#        kubectl_delete_cmds = [
#            "kubectl delete deployments --all",
#            "kubectl delete pods --all",
#            "kubectl delete services --all",
#            "kubectl delete daemonsets --all",
#            "kubectl delete statefulsets --all",
#            "kubectl delete jobs --all",
#            "kubectl delete cronjobs --all",
#            "kubectl delete pvc --all",
#            "kubectl delete configmaps --all",
#            "kubectl delete secrets --all"
#        ]

#        for cmd in kubectl_delete_cmds:
#            result = subprocess.run(cmd, shell=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
#            results.append({"command": cmd, "output": result.stdout, "error": result.stderr})

# kripte und Deployment-Dateien im 'build_scripts' Verzeichnis löschen
#        if os.path.isdir(script_dir):
#            for file in os.listdir(script_dir):
#                file_path = os.path.join(script_dir, file)
#                if os.path.isfile(file_path) and (file.endswith(".sh") or file.endswith(".yaml") or file.endswith(".yml")):
#                    os.remove(file_path)
#                    results.append({"file": file, "message": "Deleted"})

# Falls das Verzeichnis leer ist, löschen
#            if not os.listdir(script_dir):
#                shutil.rmtree(script_dir)
#                results.append({"directory": script_dir, "message": "Deleted"})

#    except Exception as e:
#        results.append({"error": str(e)})

#    return results

def delete_all_kubernetes_deployments():
    """Forcefully deletes all Kubernetes resources, including Helm releases, ServiceAccounts, and persistent volumes."""
    results = []

    try:
        # Alle Helm-Releases auflisten und löschen
        helm_list = subprocess.run("helm list --all --short", shell=True, check=False, stdout=subprocess.PIPE,
                                   text=True)
        helm_releases = helm_list.stdout.strip().split("\n")

        for release in helm_releases:
            if release:
                cmd = f"helm uninstall {release} --namespace default --no-hooks"
                result = subprocess.run(cmd, shell=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True)
                results.append({"command": cmd, "output": result.stdout, "error": result.stderr})

        # Kubernetes ServiceAccounts, ConfigMaps & PVCs erzwingen
        kubectl_delete_cmds = [
            "kubectl delete deployments --all",
            "kubectl delete pods --all",
            "kubectl delete services --all",
            "kubectl delete daemonsets --all",
            "kubectl delete statefulsets --all",
            "kubectl delete jobs --all",
            "kubectl delete cronjobs --all",
            "kubectl delete configmaps --all",
            "kubectl delete serviceaccount --all --force --grace-period=0",
            "kubectl delete configmap --all --force --grace-period=0",
            "kubectl delete pvc --all --force --grace-period=0",
            "kubectl delete pv --all --force --grace-period=0",
            "kubectl delete secrets --all --force --grace-period=0",
            "kubectl delete all --all --force --grace-period=0"
        ]

        for cmd in kubectl_delete_cmds:
            result = subprocess.run(cmd, shell=True, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True)
            results.append({"command": cmd, "output": result.stdout, "error": result.stderr})

        # Deployment-Skripte & Helm-Chart-Dateien löschen
        script_dirs = ["build_scripts", "helm_charts", "src"]

        for script_dir in script_dirs:
            if os.path.isdir(script_dir):
                shutil.rmtree(script_dir)
                results.append({"directory": script_dir, "message": "Deleted"})

    except Exception as e:
        print("Delete unsuccessful", e)
        results.append({"error": str(e)})
    print(results)
    return results


def get_platform():
    HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MLOps Platform</title>
    <style>
	.header {
	    position: relative;
	    display: flex;
	    justify-content: center; /* Centers the h1 */
	    align-items: center;
	    padding: 20px;
	    background: linear-gradient(90deg, #333, #555); /* Smooth gradient */
	    border-radius: 10px;
	    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
	}
	.header img {
	    position: absolute;
	    left: 20px; /* Keeps logo to the left */
	    max-width: 120px; /* Adjusted size */
	    height: auto;
	    border: 2px solid white; /* Softer contrast */
	    border-radius: 8px; /* Rounded corners */
	    padding: 5px;
	    background-color: white;
	}
	.header h1 {
	    color: white;
	    font-size: 28px;
	    font-weight: bold;
	    text-transform: uppercase;
	    padding: 10px 20px;
	    background: rgba(0, 0, 0, 0.3); /* Slight transparent black */
	    border-radius: 8px;
	    box-shadow: 2px 2px 10px rgba(255, 255, 255, 0.2);
	}
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding:0;
            background-color: #f4f4f4;
            text-align: center;
            h1 {
            	color:white;
            	background: #333;
            	border-radius: 18px;
            };
        }
        .tabs {
            display: flex;
            cursor: pointer;
            background: #333;
            padding: 10px;
            color: white;
        }
        .tab {
            flex: 1;
            padding: 10px 20px;
            cursor: ponter;
            background: 333;
            color: white;
            border: none;
            margin: 5px;
            border-radius: 5px;
            text-align: center;
        }
        .tab:last-child {
            border-right: none;
        }
        .tab:hover {
            background: #0056b3;
        }
        .content {
            display: none;
            height: 600px;
        }
        iframe {
            width: 100%;
            height: 100%;
            border: none;
        }
        .active {
            display: block;
        }
        .split-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin-top: 20px;
            padding: 10px;
            width: 90%;
            margin: auto;
            text-align: center;
        }
        .split {
            flex: 1 1 calc(90% - 10px);
            height: 400px;
            border: 1px solid #ddd;
        }
        .jupyter {
            flex: 2;
            height: 600px;
            border: 1px solid #ddd;
        }
        .right-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }        
        .dashboard {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin-top: 20px;
            padding: 10px;
            width: 90%;
            margin: auto;
        }        
        .service {
            flex: 1;
            height: 350px;
            border: 1px solid #ddd;
        }
        .all-services {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-top: 20px;
            padding: 10px;
            width: 90%;
            margin: auto;
        }
        .all-services .service {
            height: 400px;
        }
    </style>
    <script>
        function showTab(index) {
            document.querySelectorAll('.content').forEach((el, i) => {
                el.classList.toggle('active', i === index);
            });
        }
    </script>
</head>
<body>
    <header class="header">
    	<h1>MLOps Platform</h1>
        <img src="https://explain-project.eu/wp-content/uploads/2022/10/logo.jpg" alt="EXPLAIN Project Logo" width="100">
    </header>
    
    <div class="tabs">
        {% for service in services %}
            {% if service.name != 'kubernetes'  %}
            {% if service.name != 'kube-dns'  %}
            {% if service.name != 'minio-1741518696'  %}
            {% if service.name != 'minio-1741518696-console'  %}
                <div class="tab" onclick="showTab({{ loop.index0 }})">{{ service.name }}</div>
            {% endif %}
            {% endif %}
            {% endif %}
            {% endif %}
        {% endfor %} 
    </div>
    
    {% for service in services %}
        <div class="content {% if loop.first %}active{% endif %}">
            <iframe src="http://{{ service.cluster_ip }}:{{ service.ports[0].split('/')[0] }}"></iframe>
        </div>
    {% endfor %}
    
    <div class="dashboard">
        {% for service in services %}
            {% if service.name == 'jupyter-service' %}
                <div class="jupyter">
                    <iframe src="http://{{ service.cluster_ip }}:{{ service.ports[0].split('/')[0] }}"></iframe>
                </div>
            {% endif %}
        {% endfor %}
        <div class="right-container">
            {% for service in services %}
                {% if service.name == 'ml-flow-service' or service.name == 'evidently-service' %}
                    <div class="service">
                        <iframe src="http://{{ service.cluster_ip }}:{{ service.ports[0].split('/')[0] }}"></iframe>
                    </div>
                {% endif %}
            {% endfor %}
        </div>
    </div>
    

</body>
</html>
"""
    return HTML_TEMPLATE


def run_ml_pipeline():
    # ML-Pipeline-Aufruf
    subprocess.run(["echo", "Running ML pipeline..."])
    return "ML pipeline executed"

def start():
    html_template = """
        <!DOCTYPE html>
        <html lang="de">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Shell-Skripte</title>
            <style>
                .header {
    	    position: relative;
    	    display: flex;
    	    justify-content: center; /* Centers the h1 */
    	    align-items: center;
    	    padding: 20px;
    	    background: linear-gradient(90deg, #333, #555); /* Smooth gradient */
    	    border-radius: 10px;
    	    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    	    }
    	.header img {
    	    position: absolute;
    	    left: 20px; /* Keeps logo to the left */
    	    max-width: 120px; /* Adjusted size */
    	    height: auto;
    	    border: 2px solid white; /* Softer contrast */
    	    border-radius: 8px; /* Rounded corners */
    	    padding: 5px;
    	    background-color: white;
    	}
                body { font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; text-align: center; }
                .container { max-width: 900px; margin: auto; padding: 20px; }
                .script-box { background: #1e1e1e; padding: 15px; margin: 10px 0; border-radius: 10px; box-shadow: 0 0 10px rgba(255, 255, 255, 0.1); }
                .script-button { margin: 10px; padding: 10px 20px; border: none; background-color: #6200ea; color: white; cursor: pointer; border-radius: 5px; font-size: 16px; }
                .script-button:hover { background-color: #3700b3; }
                .stop-button { margin: 10px; padding: 10px 20px; border: none; background-color: #d32f2f; color: white; cursor: pointer; border-radius: 5px; font-size: 16px; }
                .stop-button:hover { background-color: #b71c1c; }
                .output-container { margin-top: 10px; padding: 10px; background: #252525; border-radius: 5px; white-space: pre-wrap; text-align: left; height: 200px; overflow-y: auto; border: 1px solid #444; font-family: monospace; color: #fff; }
            </style>
            <script>
                function runScript(scriptName) {
                    let outputDiv = document.getElementById("output-" + scriptName);
                    outputDiv.innerHTML = "<em>Das Skript wird ausgeführt...</em>";

                    let eventSource = new EventSource("/stream_script?script=" + scriptName);

                    eventSource.onmessage = function(event) {
                        outputDiv.innerHTML += event.data + "<br>";
                    };

                    eventSource.onerror = function() {
                        eventSource.close();
                    };
                }

                function stopScript(scriptName) {
                    fetch("/stop_script", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ script: scriptName })
                    }).then(response => response.json()).then(data => {
                        alert(data.message);
                    });
                }
            </script>
        </head>
        <body>
            <header class="header">
        	<h1>ML Pipeline Script Execution</h1>
            <img src="https://explain-project.eu/wp-content/uploads/2022/10/logo.jpg" alt="EXPLAIN Project Logo" width="100">
        </header>
            <div class="container">

                {% for script in scripts %}
                    <div class="script-box">
                        <button class="script-button" onclick="runScript('{{ script }}')">Start {{ script }}</button>
                        <button class="stop-button" onclick="stopScript('{{ script }}')">Stop {{ script }}</button>
                        <div id="output-{{ script }}" class="output-container"></div>
                    </div>
                {% endfor %}
            </div>
        </body>
        </html>
        """
    return html_template