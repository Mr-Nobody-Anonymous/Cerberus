"""Fix the stray 'm,' at the start of doctor.py."""
import io

from pathlib import Path

PATH = Path(__file__).resolve().parent / "cyberai" / "orchestrator" / "cli" / "doctor.py"

with io.open(PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Remove the stray 'm,' before the opening triple-quote
if content.startswith('m,"""'):
    content = '"""' + content[4:]

with io.open(PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed doctor.py")
