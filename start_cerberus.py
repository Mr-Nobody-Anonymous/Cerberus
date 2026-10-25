"""
CERBERUS — ONE-COMMAND LAUNCHER.

Starts the entire platform as ONE unified AI and opens the Command Deck UI:

  - Health-checks Python + core dependencies
  - Installs missing core deps automatically
  - Optionally verifies with `cyber-ai doctor`
  - Starts the web UI server (http://127.0.0.1:8710)
  - Opens the browser automatically

Usage:
    python start_cerberus.py            # start UI + open browser
    python start_cerberus.py --no-browser
    python start_cerberus.py --port 9000
    python start_cerberus.py --doctor   # also run health check first
    python start_cerberus.py --cli      # CLI only (no web UI)

The entire multi-agent platform is surfaced through ONE interface:
CyberAIOrchestrator. The UI streams every agent/phase/finding live.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

# Ensure UTF-8 output on Windows consoles to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WORKSPACE_ROOT = Path(__file__).resolve().parent
os.environ.setdefault("CERBERUS_HOME", str(WORKSPACE_ROOT))
os.chdir(WORKSPACE_ROOT)
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

UI_PORT = 8710

BANNER = r"""
  ╔══════════════════════════════════════════════════════════╗
  ║                 ██████  ██████  ██████                   ║
  ║               CERBERUS  —  ONE AI, SEVEN AGENTS          ║
  ║        self-evolving multi-agent cyber orchestrator      ║
  ╚══════════════════════════════════════════════════════════╝
"""

PKG_MAP = {
    "yaml": "PyYAML",
    "prompt_toolkit": "prompt-toolkit",
    "dotenv": "python-dotenv",
}


def _safe_print(text: str) -> None:
    """Print text safely, replacing unencodable characters if needed."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", errors="replace").decode("ascii"))


def _port_free(port: int) -> bool:
    """Check if a TCP port is free on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def check_core_modules() -> list[str]:
    """Check required Python modules are importable."""
    required = ["fastapi", "uvicorn", "yaml", "httpx", "click", "rich", "prompt_toolkit"]
    missing = []
    for mod in required:
        if importlib.util.find_spec(mod) is None:
            missing.append(mod)
    return missing


def install_missing(missing: list[str]) -> None:
    """Install missing core dependencies with pip."""
    _safe_print(f"[CERBERUS] Installing missing dependencies: {', '.join(missing)}")
    req_file = WORKSPACE_ROOT / "requirements.txt"
    if req_file.exists():
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
            check=False,
            cwd=str(WORKSPACE_ROOT),
        )
    pkgs = [PKG_MAP.get(m, m) for m in missing]
    if pkgs:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q"] + pkgs,
            check=False,
            cwd=str(WORKSPACE_ROOT),
        )


def run_doctor() -> None:
    """Run the CLI health check."""
    _safe_print("[CERBERUS] Running platform health check...")
    try:
        from cyberai.orchestrator.cli.doctor import run_health_check
        ok = True
        for component, status, msg in run_health_check():
            icon = {"ok": "[OK]", "warn": "[WARN]", "error": "[ERROR]", "info": "[INFO]"}
            _safe_print(f"  {icon.get(status, '[?]')} {component}: {msg}")
            if status == "error":
                ok = False
        if not ok:
            _safe_print("[CERBERUS] Some components have ERRORS. The UI still runs in simulation mode.")
    except Exception as e:
        _safe_print(f"[CERBERUS] Doctor check failed: {e}")


def serve(port: int, open_browser: bool) -> None:
    """Start the web UI server and open the browser."""
    if not _port_free(port):
        _safe_print(f"[CERBERUS] Port {port} is already in use — assuming the UI is already running.")
        if open_browser:
            webbrowser.open(f"http://127.0.0.1:{port}")
        return

    # Import the UI app (creates the FastAPI app)
    from cyberai.ui.server import app
    import uvicorn

    url = f"http://127.0.0.1:{port}"
    _safe_print(f"[CERBERUS] Command Deck listening on {url}")

    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def main() -> None:
    parser = argparse.ArgumentParser(description="CERBERUS one-command launcher")
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")
    parser.add_argument("--port", type=int, default=UI_PORT, help="UI port (default 8710)")
    parser.add_argument("--doctor", action="store_true", help="Run health check before starting")
    parser.add_argument("--cli", action="store_true", help="CLI only (no web UI)")
    args = parser.parse_args()

    _safe_print(BANNER)
    _safe_print(f"[CERBERUS] Workspace: {WORKSPACE_ROOT}")

    # 1. Dependencies
    missing = check_core_modules()
    if missing:
        install_missing(missing)
        missing = check_core_modules()
        if missing:
            _safe_print(f"[CERBERUS] Could not install: {missing}. Install manually:")
            _safe_print("  pip install -r requirements.txt")
            _safe_print("  pip install fastapi uvicorn prompt-toolkit")
            sys.exit(1)

    # 2. Health check (optional)
    if args.doctor:
        run_doctor()

    # 3. CLI smoke test — verifies the orchestrator imports and runs
    try:
        from cyberai import CyberAIOrchestrator
        _safe_print("[CERBERUS] Orchestrator import OK — one unified AI facade ready.")
    except Exception as e:
        _safe_print(f"[CERBERUS] Orchestrator import FAILED: {e}")
        sys.exit(1)

    # 4. Start
    if args.cli:
        _safe_print("[CERBERUS] CLI mode. Try:")
        _safe_print("  python -m cyberai.orchestrator.cli doctor")
        _safe_print("  python -m cyberai.orchestrator.cli simulate \"Analyze the lab target\"")
        return

    serve(args.port, not args.no_browser)


if __name__ == "__main__":
    main()
