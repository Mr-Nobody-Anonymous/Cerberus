"""Definitive byte-level check of doctor.py line 1 (no shell quoting involved)."""
import ast
import pathlib

p = pathlib.Path("cyberai/orchestrator/cli/doctor.py")
raw = p.read_bytes()
lines = raw.split(b"\n")
out = []
out.append(f"size={len(raw)}")
out.append(f"first 24 bytes hex = {raw[:24].hex(' ')}")
out.append(f"first 24 bytes repr = {raw[:24]!r}")
out.append(f"line1 raw repr = {lines[0]!r} (len={len(lines[0])})")
out.append(f"line2 raw repr = {lines[1]!r}")
text = raw.decode("utf-8")
tree = ast.parse(text)
doc = ast.get_docstring(tree)
out.append(f"docstring first 20 chars = {doc[:20]!r}")
out.append(f"docstring starts with quote char: {doc.startswith(chr(34))}")

# Same check for every module directly modified by commit 6bff1dc's content edits
for rel in ("cyberai/llm_gateway/__init__.py",):
    q = pathlib.Path(rel)
    if q.exists():
        b = q.read_bytes()
        out.append(f"{rel}: first 12 bytes = {b[:12]!r}")

pathlib.Path("_hexdump_out.txt").write_text("\n".join(out) + "\n", encoding="utf-8")
print("written")
