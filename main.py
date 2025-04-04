import json
import os
import signal
import subprocess

from flask import Flask, render_template_string, request, jsonify

import file_handler
import html_generation
import platform_overview
import script_generation

app = Flask(__name__)
SCRIPTS_DIR = "./python"
processes = {}


@app.route('/')
def home():
    # Simulating saved values for the form (from the previous request)
    saved_values = request.cookies.get('saved_values')  # You could use session or another method
    print(saved_values)
    if saved_values:
        saved_values = json.loads(saved_values)
    else:
        saved_values = {}

    # Generate HTML with saved form values
    html_template = html_generation.generate_html(file_handler.read_json_file_content("feature_model.fm"),
                                                  saved_values=saved_values)
    return html_template


@app.route('/update', methods=['POST'])
def update():
    form_data = request.get_json()

    # Save form data in session or cookies
    response = jsonify({'updated_html': html_generation.generate_html(
        file_handler.read_json_file_content("feature_model.fm"), saved_values=form_data)})
    response.set_cookie('saved_values', json.dumps(form_data))  # Save selected values for later use
    return response


@app.route('/code_generation', methods=['POST'])
def code_generation():
    print("Code generation")
    configuration = request.cookies.get('saved_values')  # request.get_json()
    # print("Configuration: "+configuration)
    feature_data = file_handler.read_json_file_content("feature_model.fm")
    script_generation.script_generation("code_templates.json", feature_data, configuration)

    results = ''
    return "\n".join(results) if results else "No scripts selected."


@app.route('/get_config')
def get_config():
    configuration = request.cookies.get('saved_values')  # request.get_json()
    print("Configuration: " + configuration)
    return configuration


@app.route('/platform_services')
def platform_services():
    services, pods = platform_overview.get_services()
    return render_template_string(platform_overview.get_platform_overview(), services=services)


@app.route('/run_deployment', methods=['POST'])
def run_deployment():
    result = platform_overview.run_all_deployment_scripts()
    return jsonify({"message": result})


@app.route('/run_ml_pipeline', methods=['POST'])
def run_ml_pipeline():
    print("ML pipeline code generation")
    configuration = request.cookies.get('saved_values')  # request.get_json()
    # print("Configuration: "+configuration)
    feature_data = file_handler.read_json_file_content("feature_model.fm")
    script_generation.script_generation("ml_pipeline_templates.json", feature_data, configuration)

    results = ''
    # return "\n".join(results) if results else "No scripts selected."
    return jsonify({"message": results})


@app.route('/delete', methods=['POST'])
def delete():
    result = platform_overview.delete_all_kubernetes_deployments()
    return jsonify({"message": result})


@app.route('/platform')
def platform():
    services, pods = platform_overview.get_services()
    # print(services)
    HTML_TEMPLATE = platform_overview.get_platform()
    return render_template_string(HTML_TEMPLATE, services=services)

@app.route('/start')
def start():
    scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith(".sh")]
    html_template = platform_overview.start()
    return render_template_string(html_template, scripts=scripts)


@app.route('/stream_script')
def stream_script():
    script_name = request.args.get("script")
    script_path = os.path.join(SCRIPTS_DIR, script_name)

    if not os.path.isfile(script_path):
        return "Script nicht gefunden.", 404

    def generate():
        process = subprocess.Popen(["bash", script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                   preexec_fn=os.setsid)
        processes[script_name] = process
        for line in iter(process.stdout.readline, ""):
            yield f"data: {line}\n\n"
        process.stdout.close()
        process.wait()
        del processes[script_name]

    return app.response_class(generate(), mimetype="text/event-stream")


@app.route('/stop_script', methods=['POST'])
def stop_script():
    script_name = request.json.get("script")
    if script_name in processes:
        os.killpg(os.getpgid(processes[script_name].pid), signal.SIGTERM)
        del processes[script_name]
        return jsonify({"message": f"{script_name} wurde gestoppt."})
    return jsonify({"message": f"{script_name} läuft nicht."})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
