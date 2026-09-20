"""Observe generated pure functions in an isolated Python interpreter."""
import importlib.util
import json
import platform
from pathlib import Path

spec = importlib.util.spec_from_file_location("generated_code", Path("module.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cases = json.loads(Path("cases.json").read_text(encoding="utf-8"))
rows = []
for case in cases:
    before = json.dumps(case["args"], sort_keys=True, allow_nan=False)
    try:
        result = {"actual": module.FUNCTIONS[case["function"]](*case["args"])}
    except Exception as error:
        result = {"error": str(error)}
    rows.append({"id": case["id"], **result, "inputUnchanged": before == json.dumps(case["args"], sort_keys=True, allow_nan=False)})
print(json.dumps({"runtime": "python:" + platform.python_version(), "cases": rows}, allow_nan=False))
