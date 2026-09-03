"""Manual Phase A Step 3.3 check — config loader fail-fast behavior.

1. Breaks a required YAML field in a copied targets file and confirms the
   loader raises a readable ConfigError (not a raw KeyError/NoneType crash).
2. Confirms a broken CERBERUS_HOME also fails fast.
3. Confirms the real repo targets file still validates.
"""
import subprocess
import sys

PY = sys.executable

CHECKS = r"""
import json
import os
import tempfile
import pathlib
import sys

sys.path.insert(0, r"c:\Users\hp\Desktop\Cerberus")

results = {}

# --- 1. missing required field -> readable ConfigError
from cyberai.config import ConfigError, load_required_yaml, validate_targets_file

src = pathlib.Path(r"c:\Users\hp\Desktop\Cerberus\lab\targets\targets.yaml").read_text(encoding="utf-8")
broken = src.replace("environment: authorized_lab", "environment: authorized_labx", 1)
# remove a required field from the first entry
lines = broken.splitlines()
for i, l in enumerate(lines):
    if l.strip().startswith("allowed:"):
        del lines[i]
        break
broken = "\n".join(lines)

with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td) / "targets.yaml"
    p.write_text(broken, encoding="utf-8")
    try:
        validate_targets_file(p)
        results["missing_field"] = {"raised": False}
    except ConfigError as e:
        results["missing_field"] = {"raised": True, "msg": str(e), "type": type(e).__name__}

    # --- 2. wrong environment -> readable ConfigError
    p2 = pathlib.Path(td) / "t2.yaml"
    p2.write_text("targets:\n  - id: t1\n    environment: production\n    allowed: true\n", encoding="utf-8")
    try:
        validate_targets_file(p2)
        results["wrong_env"] = {"raised": False}
    except ConfigError as e:
        results["wrong_env"] = {"raised": True, "msg": str(e), "type": type(e).__name__}

    # --- 3. missing section -> readable ConfigError
    p3 = pathlib.Path(td) / "t3.yaml"
    p3.write_text("other: 1\n", encoding="utf-8")
    try:
        validate_targets_file(p3)
        results["missing_section"] = {"raised": False}
    except ConfigError as e:
        results["missing_section"] = {"raised": True, "msg": str(e), "type": type(e).__name__}

# --- 4. broken CERBERUS_HOME -> readable ConfigError
os.environ["CERBERUS_HOME"] = r"Q:\definitely\not\a\dir"
try:
    import importlib
    import cyberai.config as c
    importlib.reload(c)
    results["bad_home"] = {"raised": False}
except Exception as e:
    results["bad_home"] = {"raised": True, "msg": str(e), "type": type(e).__name__}

# --- 5. real repo targets still validate
del os.environ["CERBERUS_HOME"]
targets = validate_targets_file()
results["real_targets_ok"] = {"count": len(targets)}

print(json.dumps(results, indent=2))
"""

with open("_check_config_out.txt", "w", encoding="utf-8") as f:
    r = subprocess.run([PY, "-c", CHECKS], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=120)
    f.write(f"RETURNCODE={r.returncode}\n--- STDOUT ---\n{r.stdout}\n--- STDERR ---\n{r.stderr}\n")
print("done")
