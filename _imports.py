"""Compute unique top-level third-party imports for the dependency audit."""
import pathlib
import sys

STDLIB = {
    "__future__", "abc", "ast", "asyncio", "base64", "collections", "copy",
    "dataclasses", "datetime", "decimal", "enum", "functools", "glob", "hashlib",
    "importlib", "inspect", "io", "itertools", "json", "logging", "math", "os",
    "pathlib", "platform", "queue", "random", "re", "shlex", "shutil", "signal",
    "socket", "sqlite3", "string", "subprocess", "sys", "tempfile", "threading",
    "time", "traceback", "typing", "unittest", "urllib", "uuid", "warnings",
    "weakref", "stat", "contextlib", "textwrap", "types", "struct", "secrets",
    "html", "http", "email", "base64", "binascii", "zlib", "gzip", "tarfile",
    "zipfile", "configparser", "argparse", "getpass", "platform", "ctypes",
    "errno", "fnmatch", "operator", "pickle", "copyreg", "pprint", "site",
    "atexit", "concurrent",
}


def module_root(line):
    line = line.strip()
    if line.startswith("from "):
        rest = line[5:].split(" ")[0]
    elif line.startswith("import "):
        rest = line[7:].split(" ")[0]
        if "," in rest:
            rest = rest.split(",")[0]
    else:
        return None
    if rest.startswith("."):
        return None  # relative import
    return rest.split(".")[0]


def roots_from(path):
    out = set()
    if not pathlib.Path(path).exists():
        return out
    for line in pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("===END"):
            break
        r = module_root(line)
        if r:
            out.add(r)
    return out


core = roots_from("_h4_imports_cyberai.txt")
tests = roots_from("_h5_imports_tests.txt")
internal = {m for m in (core | tests) if m == "cyberai"}
third_party = sorted((core | tests) - STDLIB - internal)
lines = []
lines.append(f"CORE+TEST unique roots: {sorted(core | tests)}")
lines.append(f"THIRD-PARTY (non-stdlib, non-cyberai): {third_party}")
pathlib.Path("_imports_out.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("written")
