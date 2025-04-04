import json


def generate_html(form_data, saved_values=None):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Generated Configuration Form</title>

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
	    .header h1 {
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
                font-family: 'Lato', sans-serif;
                background-color: #f4f4f4;
                margin: 0;
                padding: 20px;
                text-align: left;
            }
            .container {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                max-width: 100%;
                margin: auto;
            }
            h1, h2 {
                color: #2c3e50;
            }
            label {
                display: inline-flex;
                align-items: center;
                font-weight: bold;
                margin-bottom: 5px;
            }
            input, select {
                width: 100%;
                padding: 8px;
                margin-top: 5px;
                border-radius: 5px;
                border: 1px solid #ccc;
                transition: background-color 0.3s ease;
            }
            input:focus, select:focus {
                background-color: #ecf0f1;
                outline: none;
                border-color: #3498db;
            }
            input[type="checkbox"] {
                width: auto;
                margin-right: 10px;
                transform: scale(1.2);
            }
            input[type="submit"], button {
                background-color: #555;
                color: white;
                padding: 10px 15px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                margin-top: 10px;
                transition: background-color 0.3s ease;
            }
            input[type="submit"]:hover, button:hover {
                background-color: #3498db;
            }
            .disabled {
                opacity: 0.5;
                pointer-events: none;
            }
            .fade-in {
                animation: fadeIn 0.5s ease-in-out;
            }
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            /* Stile für die erste Aktivierungs-Checkbox */
.activation-checkbox:first-of-type {
    display: inline-block;
    margin-left: 10px;
    vertical-align: middle;
}

/* Stile für alle nachfolgenden Aktivierungs-Checkboxen */
.activation-checkbox:not(:first-of-type) {
    display: block;
    margin-top: 5px;
}

        </style>

        <script>
        let debounceTimeout;
        let isUpdating = false;

        function getFieldData(fieldId) {
            const formData = JSON.parse(document.getElementById('form-data').textContent);
            return formData.find(field => field.name === fieldId);
        }

        function updateDependencies() {
            const formData = JSON.parse(document.getElementById('form-data').textContent);

            formData.forEach(field => {
                const element = document.getElementById(field.name);
                if (!element) return;

                let enabled = true;

                // "requires" Constraint prüfen
                if (field.dependencies && field.dependencies.requires) {
                    enabled = field.dependencies.requires.every(req => {
                        const [depField, depValue] = req.split(":");
                        const depElement = document.getElementById(depField);

                        if (!depElement) return false;

                        if (depElement.type === "checkbox") {
                            return depValue === "true" ? depElement.checked : depElement.checked === false;
                        } else {
                            return depElement.value === depValue;
                        }
                    });
                }

                // "excludes" Constraint prüfen
                if (field.constraints && field.constraints.excludes) {
                    field.constraints.excludes.forEach(excludedField => {
                        const excludedElement = document.getElementById(excludedField);
                        if (excludedElement) {
                            excludedElement.disabled = element.checked;
                            document.querySelector(`label[for="${excludedField}"]`).style.color = element.checked ? "gray" : "";
                            if (element.checked && excludedElement.type === "checkbox") {
                                excludedElement.checked = false;
                            }
                        }
                    });
                }

                element.disabled = !enabled;
                document.querySelector(`label[for="${field.name}"]`).style.color = enabled ? "" : "gray";

                // Falls deaktiviert, Checkbox abwählen
                if (!enabled) {
                    if (element.type === "checkbox") {
                        element.checked = false;
                    } else if (element.type === "text") {
                        element.value = ""; // Textbox-Inhalt leeren
                    } else if (element.tagName === "SELECT") {
                        element.selectedIndex = -1; // Dropdown-Auswahl leeren
                    }
                }
                if (enabled) {
                    element.classList.remove("disabled");
                    element.classList.add("fade-in");
                } else {
                    element.classList.add("disabled");
                    element.classList.remove("fade-in");
                    if (element.type === "checkbox") {
                        element.checked = false;
                    } else {
                        element.value = "";
                    }
                }                
            });
        }

        function updateFormData() {
            const formData = {};
            document.querySelectorAll('input, select').forEach(element => {
                if (element.type === 'checkbox') {
                    formData[element.id] = element.checked;
                } else {
                    formData[element.id] = element.value;
                }
            });

            fetch('/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('form-data').textContent = JSON.stringify(data.form_data);
                updateDependencies();
            })
            .catch(error => console.error('Error updating form:', error));
        }

        function updateForm() {
            if (isUpdating) return;
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(function() {
                isUpdating = true;

                var formData = {};
                document.querySelectorAll('input, select').forEach(element => {
                    if (element.type === 'checkbox') {
                        formData[element.id] = element.checked;
                    } else {
                        formData[element.id] = element.value;
                    }
                });

                fetch('/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(formData)
                })
                .then(response => response.json())
                .then(data => {
                    document.body.innerHTML = data.updated_html;
                    updateDependencies();
                    isUpdating = false;
                })
                .catch(error => {
                    console.error('Error during update:', error);
                    isUpdating = false;
                });
            }, 300);
        }

        window.addEventListener('change', function() {
            updateForm();
            updateDependencies();
        });

        window.onload = updateDependencies;
        </script>
    </head>
    <body>
            <header class="header">
    	<h1>Script Configuration</h1>
        <img src="https://explain-project.eu/wp-content/uploads/2022/10/logo.jpg" alt="EXPLAIN Project Logo" width="100">
    </header>
    	<div class="container">
    """

    html_content += f'<script id="form-data" type="application/json">{json.dumps(form_data)}</script>'

    try:
        for field in form_data:
            if field["type"] == "header":
                html_content += f'<h1>{field["content"]}</h1>'
            elif field["type"] == "header2":
                html_content += f'<h2>{field["content"]}</h2>'
            elif field["type"] == "paragraph":
                html_content += f'<p>{field["content"]}</p>'
            elif field["type"] == "text":
                value = saved_values.get(field["name"], "") if saved_values else ""
                html_content += f'<label for="{field["name"]}">{field["label"]}:</label>'
                html_content += f'<input type="text" id="{field["name"]}" name="{field["name"]}" placeholder="{field.get("placeholder", "")}" value="{value}"><br><br>'
                if "dependencies" in field and "requires" in field["dependencies"]:
                    html_content += f' <small>(Requires: {", ".join(field["dependencies"]["requires"])} )</small>'
            elif field["type"] == "checkbox":
                checked = "checked" if saved_values and field["name"] in saved_values and saved_values[
                    field["name"]] else ""
                html_content += f'<input type="checkbox" id="{field["name"]}" name="{field["name"]}" value="true" {checked}>'
                html_content += f'<label for="{field["name"]}">{field["label"]}</label>'
                if "dependencies" in field and "requires" in field["dependencies"]:
                    html_content += f' <small>(Requires: {", ".join(field["dependencies"]["requires"])} )</small>'
                if "constraints" in field and "excludes" in field["constraints"]:
                    html_content += f' <small>(Excludes: {", ".join(field["constraints"]["excludes"])} )</small>'
                html_content += '<br><br>'
            elif field["type"] == "dropdown":
                selected_value = saved_values.get(field["name"], "") if saved_values else ""
                html_content += f'<label for="{field["name"]}">{field["label"]}:</label>'
                html_content += f'<select id="{field["name"]}" name="{field["name"]}">'
                for option in field["options"]:
                    selected = "selected" if option == selected_value else ""
                    html_content += f'<option value="{option}" {selected}>{option}</option>'
                html_content += '</select>'
                if "dependencies" in field and "requires" in field["dependencies"]:
                    html_content += f' <small>(Requires: {", ".join(field["dependencies"]["requires"])} )</small>'
                html_content += '<br><br>'

    except Exception as e:
        print(f"Error in generating form HTML: {e}")

    html_content += '<form id="dynamic-form"><input type="submit" value="Generate"></form>'
    html_content += '''
    <script>
    document.getElementById("dynamic-form").onsubmit = function(event) {
        event.preventDefault();

        document.querySelectorAll('input[name="preferences"]:checked').forEach(function(checkbox) {
            formData.preferences.push(checkbox.value);
        });

        fetch('/code_generation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            alert(data.message);
            window.location.href = "/platform_services";
        })
    };
    </script>
    '''
    html_content += '''<button onclick=window.location.href="/platform_services">Go to running platform services</button>'''
    html_content += '''<br><br><paragraph>Developed and coded by Leonhard Faubel-Teich</paragraph>'''
    html_content += '</div></body></html>'
    return html_content
