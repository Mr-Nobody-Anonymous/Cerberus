"""One-time fix: repair the broken `if  else None` ternary in stub adapters."""
import glob
import re

PATTERN = re.compile(
    r'os\.environ\.get\("([^"]*)",\s*"([^"]*)"\)\s+if\s+else None'
)

for path in sorted(glob.glob("adapters/*/adapter.py")):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "if  else None" not in content:
        continue
    # Replace the broken ternary with a safe literal.
    fixed = PATTERN.sub(lambda m: '"{}"'.format(m.group(2)) if m.group(2) else "None", content)
    # Fallback: any remaining `if  else None` -> None
    fixed = fixed.replace("if  else None", "else None".replace("else None", "None"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(fixed)
    print("fixed", path)
