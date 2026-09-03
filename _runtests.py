"""Run pytest and write a completion marker (Phase A verification)."""
import subprocess
import sys

r = subprocess.run(
    [sys.executable, "-m", "pytest", "tests", "-q", "--no-header", "--tb=short"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=600,
    cwd=r"c:\Users\hp\Desktop\Cerberus",
)
out = []
out.append(f"RETURNCODE={r.returncode}")
out.append("--- STDOUT ---")
out.append(r.stdout or "")
out.append("--- STDERR ---")
out.append(r.stderr or "")
with open("_pytest_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("marker written")
