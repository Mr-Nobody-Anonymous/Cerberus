"""Scratch audit scanner for Phase A (not part of the package)."""
import ast
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXCLUDE_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules",
                ".pytest_cache", "dist", "build", ".mypy_cache", ".ruff_cache",
                ".git", ".idea", ".vscode"}

WIN_ABS = re.compile(r"[A-Za-z]:\\+")
SINGLE_CHAR = re.compile(r"^[a-zA-Z]$")
TRUNC_IMPORT = re.compile(r"^\s*(?:from|import)\s*$")

CFG_EXTS = {".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".conf", ".env", ".dockerfile"}
CFG_NAMES = {"dockerfile", ".env"}


def py_flags(line):
    flags = []
    if "/home/" in line or "/Users/" in line or "/root/" in line:
        flags.append("user-home-abs-path")
    if "Path(__file__)" in line:
        flags.append("Path(__file__)")
    if "os.path.dirname(__file__)" in line:
        flags.append("os.path.dirname(__file__)")
    if "../.." in line:
        flags.append("double-parent-traversal")
    if "os.environ[" in line:
        flags.append("os.environ[...]")
    if "sys.path.insert" in line or "sys.path.append" in line:
        flags.append("sys.path-hack")
    if "Path.home()" in line or "expanduser" in line:
        flags.append("user-home-relative")
    if WIN_ABS.search(line):
        flags.append("windows-abs-path")
    if "llm-gateway" in line:
        flags.append("stale-llm-gateway-name")
    return flags


def cfg_flags(line):
    flags = []
    if "/home/" in line or "/Users/" in line or "/root/" in line:
        flags.append("user-home-abs-path")
    if "../.." in line:
        flags.append("double-parent-traversal")
    if WIN_ABS.search(line):
        flags.append("windows-abs-path")
    return flags


def iter_files(base, exts, names=None):
    names = names or set()
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() in exts or fn.lower() in names:
                yield p


def main():
    out = []
    core_imports = set()
    aevolve_imports = set()
    test_imports = set()

    # --- python files under cyberai/ ---
    for p in iter_files(ROOT / "cyberai", {".py"}):
        rel = p.relative_to(ROOT).as_posix()
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            out.append(f"READ_FAIL {rel}: {e}")
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines[:100], 1):
            if SINGLE_CHAR.match(line):
                out.append(f"SINGLE_CHAR_LINE {rel}:{i}: {line!r}")
            elif TRUNC_IMPORT.match(line):
                out.append(f"TRUNCATED_IMPORT {rel}:{i}: {line!r}")
        for i, line in enumerate(lines, 1):
            for flag in py_flags(line):
                out.append(f"PY:{flag} {rel}:{i}: {line.strip()[:150]}")
        is_aevolve = rel.startswith("cyberai/evolution/a-evolve/")
        target = aevolve_imports if is_aevolve else core_imports
        try:
            tree = ast.parse(text)
        except SyntaxError as e:
            out.append(f"SYNTAX_FAIL {rel}: {e}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    target.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    target.add(node.module.split(".")[0])

    # --- tests ---
    tdir = ROOT / "tests"
    if tdir.is_dir():
        for p in iter_files(tdir, {".py"}):
            try:
                tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        test_imports.add(a.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.level == 0:
                        test_imports.add(node.module.split(".")[0])

    # --- config-style files in cyberai/, adapters/, infrastructure/ ---
    for base in ("cyberai", "adapters", "infrastructure"):
        bd = ROOT / base
        if not bd.is_dir():
            continue
        for p in iter_files(bd, CFG_EXTS, CFG_NAMES):
            rel = p.relative_to(ROOT).as_posix()
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                out.append(f"READ_FAIL {rel}: {e}")
                continue
            for i, line in enumerate(text.splitlines(), 1):
                for flag in cfg_flags(line):
                    out.append(f"CFG:{flag} {rel}:{i}: {line.strip()[:150]}")

    out.append("")
    out.append("=== IMPORTS core (cyberai excl. evolution/a-evolve) ===")
    out.append(", ".join(sorted(core_imports)))
    out.append("=== IMPORTS a-evolve ===")
    out.append(", ".join(sorted(aevolve_imports)))
    out.append("=== IMPORTS tests ===")
    out.append(", ".join(sorted(test_imports)))
    print("\n".join(out))


if __name__ == "__main__":
    main()
