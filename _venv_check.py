"""Phase A Step 4.4/5 — fresh-venv dependency + doctor verification.

Creates a clean venv, installs ONLY requirements.txt, imports cyberai,
and runs doctor. Writes a full log to _venv_check.txt.
"""
import os
import subprocess
import sys
import venv

ROOT = r"c:\Users\hp\Desktop\Cerberus"
VENV_DIR = os.path.join(ROOT, "_cerberus-clean-check")
LOG = os.path.join(ROOT, "_venv_check.txt")

lines = []


def log(s):
    lines.append(s)


def run(cmd, timeout, env=None, cwd=ROOT):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, env=env, cwd=cwd)
    return r


def main():
    # 1. create venv
    if os.path.isdir(VENV_DIR):
        import shutil
        shutil.rmtree(VENV_DIR)
    log("=== creating venv ===")
    r = run([sys.executable, "-m", "venv", VENV_DIR], 300)
    log(f"venv create rc={r.returncode} {r.stdout} {r.stderr}")

    py = os.path.join(VENV_DIR, "Scripts", "python.exe")
    if not os.path.isfile(py):
        log(f"FATAL: venv python not found at {py}")
        return

    # 2. pip install -r requirements.txt (fresh index; no surrounding env)
    log("=== pip install -r requirements.txt ===")
    r = run([py, "-m", "pip", "install", "-r", "requirements.txt"], 1800)
    log(f"pip install rc={r.returncode}")
    log("--- pip stdout (tail) ---")
    log("\n".join(r.stdout.splitlines()[-25:]))
    log("--- pip stderr (tail) ---")
    log("\n".join(r.stderr.splitlines()[-10:]))

    if r.returncode != 0:
        log("FATAL: pip install failed — stopping.")
        return

    # 3. import cyberai — needs cwd=ROOT because the package is not installed;
    #    this mirrors 'python -c "import cyberai"' from the repo root.
    log("=== python -c 'import cyberai' (cwd=repo root) ===")
    r = run([py, "-c", "import cyberai; print('import-ok', cyberai.__version__)"], 300, cwd=ROOT)
    log(f"import rc={r.returncode}")
    log(r.stdout)
    log(r.stderr)

    # 4. doctor
    log("=== python -m cyberai.orchestrator.cli doctor ===")
    r = run([py, "-m", "cyberai.orchestrator.cli", "doctor"], 600, cwd=ROOT)
    log(f"doctor rc={r.returncode}")
    log("--- doctor stdout ---")
    log(r.stdout)
    log("--- doctor stderr ---")
    log(r.stderr)

    # 5. show installed pins for the record
    log("=== pip freeze (venv) ===")
    r = run([py, "-m", "pip", "freeze"], 120)
    log(r.stdout)

    with open(LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("venv check written")


if __name__ == "__main__":
    main()
