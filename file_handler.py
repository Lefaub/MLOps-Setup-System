import json


def read_json_file_content(filename):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return f"The file at {filename} was not found."
    except IOError:
        return f"An error occurred while trying to read the file at {filename}."
