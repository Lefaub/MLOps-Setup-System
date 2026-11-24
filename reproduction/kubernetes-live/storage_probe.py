"""Runs inside the smoke Job. Retains generator logic, replacing demo credentials in memory."""
import ast
import contextlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
from fixtures import FIXTURES, expected

root = Path("/home/data_repository")
root.mkdir(parents=True, exist_ok=True)
image = os.environ["PROFILE"] == "visual_inspection"
filename, payload = FIXTURES[os.environ["PROFILE"]]
target = root / filename
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(payload)
tree = ast.parse(Path("/probe/generated.py").read_text())
credentials = {"ACCESS_KEY": "MINIO_ROOT_USER", "SECRET_KEY": "MINIO_ROOT_PASSWORD"}
patched = set()
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        if name in credentials:
            if name in patched or not isinstance(node.value, ast.Constant):
                raise ValueError("unexpected generated credential declaration")
            node.value = ast.Constant(os.environ[credentials[name]])
            patched.add(name)
if patched != credentials.keys():
    raise ValueError("expected both generated credential declarations")
# The original client can print details and catch storage errors. Do not publish its
# stdout; an independent retrieval and byte check is the actual success criterion.
env = {"__name__": "__main__"}
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    exec(compile(ast.fix_missing_locations(tree), "generated.py", "exec"), env)
if env.get("MINIO_ENDPOINT") != os.environ["EXPECTED_ENDPOINT"]:
    raise RuntimeError("generated client did not use the freshly discovered endpoint")
bucket = "image-data" if image else "energiedaten"
key = target.name if image else str(target)
stream = env["client"].get_object(bucket, key)
try:
    actual = stream.read(len(payload) + 1)
finally:
    stream.close()
    stream.release_conn()
if actual != payload:
    raise RuntimeError("storage round-trip did not match the fixture")
print(json.dumps({"profile": os.environ["PROFILE"], **expected(os.environ["PROFILE"]),
                  "live_endpoint_used": True, "round_trip": "pass",
                  "client_versions": {k: importlib.metadata.version(k) for k in ("minio", "pandas", "urllib3")}}))
