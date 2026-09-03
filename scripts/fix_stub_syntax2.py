"""Fix broken stub adapter syntax across adapters/."""
import re
from pathlib import Path

URL_RE = re.compile(
    r'self\._api_url = os\.environ\.get\("[^"]*",\s*"[^"]*"\)\s+if\s+.*?\s+else\s+None')
TOKEN_RE = re.compile(
    r'self\._api_token = os\.environ\.get\("[^"]*",\s*"[^"]*"\)\s+if\s+.*?\s+else\s+None')


def fix_file(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    if not (URL_RE.search(text) or TOKEN_RE.search(text)):
        return False
    has_api_env = "API_URL_ENV" in text
    if has_api_env:
        text = URL_RE.sub(
            'self._api_url = os.environ.get(API_URL_ENV, "http://localhost:0") '
            'if API_URL_ENV else "http://localhost:0"', text)
        text = TOKEN_RE.sub(
            'self._api_token = os.environ.get(API_TOKEN_ENV, "") '
            'if API_TOKEN_ENV else ""', text)
    else:
        text = URL_RE.sub('self._api_url = "http://localhost:0"', text)
        text = TOKEN_RE.sub('self._api_token = None', text)
    p.write_text(text, encoding="utf-8")
    return True


def main():
    fixed = []
    paths = list(Path("adapters").rglob("__init__.py")) + list(Path("adapters").rglob("adapter.py"))
    for p in paths:
        try:
            if fix_file(p):
                fixed.append(str(p))
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR {p}: {exc}")
    for f in fixed:
        print(f"FIXED {f}")
    print(f"done: {len(fixed)} fixed")


if __name__ == "__main__":
    main()
