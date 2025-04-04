import json
import os
import re
from collections import defaultdict

from jinja2 import Template


# code_template_path="code_templates.json"


def script_generation(code_template_path, feature_data, configuration):
    try:
        global ips
        ips = extract_services("kubernetes_resources.txt")
        print(ips)
    except:
        print("IPs not yet initialized")

    containers, code_template = container_creation(code_template_path, configuration, feature_data)
    # print(containers)
    generate_files(containers, code_template, configuration)
    # print("Feature data:")
    # print(feature_data)
    # print("Containers:")
    # print(containers)


def parse_ips_to_dict(ips_string):
    ip_dict = {}
    lines = ips_string.splitlines()
    for line in lines:
        if '=' in line:
            key, value = line.split('=')
            ip_dict[key.strip()] = value.strip().strip('"')
    return ip_dict


def container_creation(code_template_path, configuration, feature_data):
    containers = []
    current_header = None
    current_elements = []
    config_data = json.loads(configuration)
    # print(configuration)

    with open(code_template_path, 'r') as file:
        code_template = json.load(file)

    for field in feature_data:
        if field["type"] == "header2":
            if current_header:
                containers.append((current_header, current_elements))
            current_header = field["content"]
            current_elements = []
        elif field["type"] in ["text", "checkbox", "dropdown"]:
            if current_header:
                value = str(get_value(config_data, field["name"]))
                current_elements.append(f'{field["name"].upper()}={value}')
    if current_header:
        containers.append((current_header, current_elements))

    return containers, code_template


def generate_files(containers, code_template, configuration):
    # print(code_template)
    output_dirs = search_output_dir(code_template)

    for script in code_template["script_types"]:
        print(f"- Name: {script['name']}, Output Path: {script['output_path']}, Extension: {script['extension']}")

    # print (output_dirs)
    for key, path in output_dirs.items():
        os.makedirs(path, exist_ok=True)

    config_data = json.loads(configuration)

    general_settings = {}
    general_globals_list = []

    # Durchlaufe alle Containers und füge die Elemente für "General" hinzu
    for header, elements in containers:
        if "General" in header:
            print(f"Header: {header}, Elements: {elements}")

            # Dynamisches Hinzufügen der Elemente für jede Instanz von "General"
            general_settings[header] = elements
            for element in elements:
                key, value = element.split("=")
                formatted_value = f'"{value}"'  # Wert in Anführungszeichen setzen

                # Füge den formatierten Wert zur globalen Liste hinzu
                general_globals_list.append(f'{key}={formatted_value}')

                formatted_global_value = f'{value}'  # Wert in Anführungszeichen setzen
                # Erstelle eine globale Variable für jedes Element
                globals()[key] = formatted_global_value  # Dynamisch eine Variable erstellen

    # Initialisierung der Liste zum Speichern aller Strings
    global general_strings_list
    general_strings_list = []
    ips_dict = parse_ips_to_dict(ips)
    globals().update(ips_dict)  # Hier werden die IPs global verfügbar gemacht

    # Durchlaufe alle Containers und füge die Elemente für "General" hinzu
    for header, elements in containers:
        if "General" in header:
            # Füge alle Elemente als Strings mit Anführungszeichen zur Liste hinzu
            for element in elements:
                general_strings_list.append(f'{element.split("=")[0]}="{element.split("=")[1]}"')

    # Ausgabe der einzelnen Strings in der Liste
    print("\nAlle allgemeinen Einstellungen als Strings:")
    for setting in general_strings_list:
        print(setting)

    config_data.pop("", None)
    print(config_data)
    for header, elements in containers:
        sanitized_header = header.lower().replace(" ", "_")
        # print("\n"+sanitized_header)
        script_types = {
            script["name"]: (
            f"{output_dirs.get(script['name'], 'unknown')}/{sanitized_header}{script['extension']}", script["name"]) for
            script in code_template["script_types"] if
            should_generate_script(sanitized_header.capitalize(), code_template, elements, config_data, script)
            # if should_generate_script(script, code_template['rules'], elements, config_data)# if xxx == True # xxx.get('', True)
        }

        # print(should_generate_script(sanitized_header.capitalize(), code_template, elements, config_data))

        generate_script(sanitized_header, elements, code_template, script_types, config_data)


def should_generate_script(header, code_template, elements, config_data, script):
    """
    Prüft, ob ein Skript anhand der Regeln generiert werden soll.
    """

    for rule in code_template["rules"]:

        if rule["name"] == header:
            if rule["value"] == True and rule["script_type"] == script["name"]:
                if rule["condition"] == "":  ########################## hier noch die Abfrage einbauen
                    print(header.capitalize() + " " + script["name"] + " activated")
                    return True

    return False


def search_output_dir(code_template):
    return {script["name"]: script["output_path"] for script in code_template["script_types"]}


def generate_script(header, elements, code_template, script_types, config_data):
    output_dirs = search_output_dir(code_template)

    print("\n" + header.capitalize())

    for script_type, (path, key) in script_types.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Aktivierung prüfen
        flag = any(element == header.upper() + "_ACTIVATION=True" for element in elements)
        flag2 = any(element == header.upper() + "_ACTIVATION=False" for element in elements)
        enabled = flag or (not flag2)

        if enabled:
            print(f"Script creation {header.upper()} ({script_type})")

            # Code-Template abrufen (z. B. aus einer Datei oder Datenbank)
            raw_template = get_script_routine(header, code_template, key)

            # Jinja2-Template erstellen
            template = Template(raw_template)

            print(header, " ", elements, " ", script_type)

            # Skript mit Jinja2 rendern
            script_content_raw = template.render(get_globals_for_template(), config=config_data)

            # Zusätzliche Bash-spezifische Anpassungen
            if script_type == "bash":
                script_content = "#!/bin/bash\n"
                print("Add: ", elements)
                script_content += "\n".join(elements)
                script_content += "\n"
                script_content += "\n".join(general_strings_list)
                script_content += script_content_raw
            elif script_type == "docker":
                script_content = script_content_raw
            elif script_type == "kubernetes":
                script_content = script_content_raw
            elif script_type == "python_init":
                script_content = ''
                script_content += ips
                script_content += script_content_raw
            else:
                script_content = script_content_raw

            # Datei speichern
            with open(path, "w") as file:
                file.write(script_content)

            # Ausführbar machen
            os.chmod(path, 0o777)
            print(f"{script_type.capitalize()} script created: {path}")
        else:
            print(f"{script_type.capitalize()} script deactivated.")


def get_globals_for_template():
    # Filtern der globalen Variablen (kann angepasst werden, um nur bestimmte Variablen zu wählen)
    globals_dict = globals()  # Hole den globalen Namespace
    template_vars = {key: value for key, value in globals_dict.items() if not key.startswith("__")}
    return template_vars


def get_script_routine(title, config_json, script_type):
    return config_json.get(title, {}).get(script_type, f"# No {script_type} code template found for '{title}'.")


def get_value(data, key):
    return data.get(key, "Key not found")


def extract_services(file_path):
    # Read the services file
    with open(file_path, 'r') as file:
        content = file.read()

    # Define regex patterns to find services and pods
    service_pattern = re.compile(
        r"Service Name: (.*?)\s*Namespace: (.*?)\s*Cluster IP: (\d+\.\d+\.\d+\.\d+)\s*Ports: (.*?)\n", re.DOTALL)
    pod_pattern = re.compile(r"Pod Name: (.*?)\s*Namespace: (.*?)\s*Node: (.*?)\s*Status: (.*?)\n", re.DOTALL)

    # Find all matches
    service_matches = service_pattern.findall(content)
    pod_matches = pod_pattern.findall(content)

    # Dictionary to track unique numbers for services, pods, and service-ports
    service_count = defaultdict(int)
    pod_count = defaultdict(int)
    unique_names = set()  # Track used variable names

    # Map services to namespaces
    service_namespace_map = {match[0]: match[1] for match in service_matches}

    # Map pods to services based on name similarity
    pod_service_map = defaultdict(list)
    for pod in pod_matches:
        pod_name = pod[0]
        namespace = pod[1]

        for service_name, service_namespace in service_namespace_map.items():
            if namespace == service_namespace and (
                    service_name in pod_name or pod_name.startswith(service_name.split('-')[0])):
                pod_service_map[service_name].append(pod_name)

    # Prepare the result in the desired format
    service_strings = []
    for match in service_matches:
        service_name = match[0].replace("-", "_")  # Replace "-" with "_"
        ip = match[2]
        ports = match[3].split(', ')  # Split multiple ports if they exist
        pods = pod_service_map.get(match[0], [])  # Get related pods

        # Assign a unique number to each service name
        service_count[service_name] += 1
        service_number = service_count[service_name]

        # For each port, create a uniquely named variable
        for port in ports:
            port_number = port.split('/')[0]  # Extract port number

            # Generate a base name for the variable
            base_name = f"{service_name}_service_{service_number}_ip"

            # Ensure uniqueness
            name_variant = base_name
            count = 1
            while name_variant in unique_names:
                count += 1
                name_variant = f"{service_name}_service_{count}_ip"

            # Store the name to avoid duplicates
            unique_names.add(name_variant)

            # Create the formatted string
            service_strings.append(f"{name_variant} = \"{ip}:{port_number}\"")

        # Append pod names associated with the service
        for pod in pods:
            pod_var = pod.replace("-", "_")
            pod_count[service_name] += 1
            pod_number = pod_count[service_name]

            base_pod_name = f"{service_name}_pod_{pod_number}"
            unique_names.add(base_pod_name)
            service_strings.append(f"{base_pod_name} = \"{pod}\"")

    # Return the formatted string for all services and pods
    return '\n'.join(service_strings)
