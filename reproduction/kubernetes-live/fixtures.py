"""Small public synthetic payloads, not datasets from either evaluation."""
from base64 import b64decode
from hashlib import sha256

FIXTURES = {
    "time_series": ("monthly_hourly_load_values_2022_DE.csv",
                    b"timestamp,load_mw\n2022-01-01T00:00:00Z,140\n2022-01-01T01:00:00Z,145\n"),
    "visual_inspection": ("data/synthetic-pixel.png",
                          b64decode("iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFklEQVR4nGM0r57FwMDAxMDAwMDAAAAPVwFQB71jngAAAABJRU5ErkJggg==")),
}

def expected(profile):
    name, payload = FIXTURES[profile]
    return {"fixture":name.rsplit("/", 1)[-1], "sha256":sha256(payload).hexdigest(), "bytes":len(payload)}
