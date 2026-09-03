"""Capture a final doctor run (dev env) and diff against the Step-1 baseline."""
import subprocess
import sys

r = subprocess.run(
    [sys.executable, "-m", "cyberai.orchestrator.cli", "doctor"],
    capture_output=True, text=True, encoding="utf-8", errors="replace",
    timeout=600, cwd=r"c:\Users\hp\Desktop\Cerberus",
)
with open("_doctor_final.txt", "w", encoding="utf-8") as f:
    f.write(f"RETURNCODE={r.returncode}\n")
    f.write(r.stdout)
    f.write("\n--- STDERR ---\n")
    f.write(r.stderr)
print("final doctor captured")
