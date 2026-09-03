"""Remove stale appended stub content from guardian-cli __init__.py."""
from pathlib import Path

p = Path("adapters/guardian-cli/__init__.py")
text = p.read_text(encoding="utf-8")

# Keep everything before the second module docstring (the stale stub).
marker = '\n"""\nAdapter for Guardian (guardian-cli).\n'
idx = text.find(marker)
if idx == -1:
    print("marker not found; no change")
else:
    text = text[:idx] + "\n"
    p.write_text(text, encoding="utf-8")
    print(f"trimmed at index {idx}")
