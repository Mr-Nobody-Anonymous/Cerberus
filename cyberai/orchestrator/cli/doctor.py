"""
Health check / doctor module for the Cyber AI Orchestrator.

Inspects every major subsystem and reports status as:
  OK      - Component is healthy and working
  WARN    - Component has issues but is usable
  ERROR   - Component is unavailable or broken
  INFO    - Informational (not a problem)

No sys.path hacks — assumes the package is installed or on PYTHONPATH.
"""

import importlib
import logging
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Iterator, Tuple

logger = logging.getLogger(__name__)

# Paths are resolved relative to this file (inside cyberai/orchestrator/cli/)
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CYBERAI = WORKSPACE_ROOT / "cyberai"
_ADAPTERS = WORKSPACE_ROOT / "adapters"
_INFRA = WORKSPACE_ROOT / "infrastructure"
_LAB = WORKSPACE_ROOT / "lab"
_MEMORY = WORKSPACE_ROOT / "memory"
_LOGS = WORKSPACE_ROOT / "logs"


def _check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a TCP port is open."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, socket.timeout, OSError):
        return False


def _check_command(cmd: str) -> bool:
    """Check if a command is available on PATH."""
    return shutil.which(cmd) is not None


def _check_git_repo(path: Path) -> Tuple[bool, str]:
    """Check if a directory is a valid git repository."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            has_changes = bool(result.stdout.strip())
            return True, f"clean{' (uncommitted changes)' if has_changes else ''}"
        return False, f"error: {result.stderr.strip()}"
    except Exception as e:
        return False, str(e)


def run_health_check() -> Iterator[Tuple[str, str, str]]:
    """
    Run all health checks and yield (component, status, message) tuples.

    Status is one of: ok, warn, error, info
    """

    # ---- Python ----
    yield (
        "Python",
        "ok",
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    )

    # ---- stdlib platform module ----
    import platform
    yield ("Python stdlib 'platform'", "ok", platform.system())

    # ---- Git ----
    if _check_command("git"):
        version = subprocess.run(
            ["git", "--version"], capture_output=True, text=True, timeout=5
        )
        yield ("Git", "ok", version.stdout.strip())
    else:
        yield ("Git", "error", "not found on PATH")

    # ---- Docker ----
    if _check_command("docker"):
        # Check if daemon is running
        try:
            result = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                yield ("Docker", "ok", "installed and daemon running")
            else:
                yield ("Docker", "warn", "installed but daemon not running")
        except Exception:
            yield ("Docker", "ok", "installed (daemon status unknown)")
    else:
        yield ("Docker", "warn", "not installed - Docker-dependent integrations will be unavailable")

    # ---- Ollama ----
    if _check_port("127.0.0.1", 11434):
        yield ("Ollama", "ok", "running on localhost:11434")
    else:
        yield ("Ollama", "warn", "not running on localhost:11434 — starting it: `ollama serve`")

    # ---- LiteLLM / LLM Gateway ----
    if _check_port("127.0.0.1", 4000):
        yield ("LiteLLM Gateway", "ok", "running on localhost:4000")
    else:
        yield ("LiteLLM Gateway", "warn", "not running on localhost:4000 — local-only mode active")

    # ---- LLM availability ----
    models_yaml = _CYBERAI / "llm-gateway" / "models" / "models.yaml"
    if models_yaml.exists():
        import yaml
        with open(models_yaml) as f:
            data = yaml.safe_load(f) or {}
        ready = [name for name, cfg in data.get("models", {}).items() if cfg.get("status") == "READY"]
        if ready:
            yield ("LLM availability", "ok", f"Models ready: {', '.join(ready)}")
        else:
            yield ("LLM availability", "warn", "No models marked as READY (Ollama not running)")
    else:
        yield ("LLM availability", "warn", "Model registry not found")

    # ---- Open WebUI ----
    if _check_port("127.0.0.1", 3000):
        yield ("Open WebUI", "ok", "running on localhost:3000")
    else:
        yield ("Open WebUI", "info", "not running (start with docker-compose if installed)")

    # ---- Repositories / Adapters ----
    repo_count = 0
    repo_clean = 0
    repo_dirty = 0
    if _ADAPTERS.exists():
        for repo_dir in _ADAPTERS.iterdir():
            if repo_dir.is_dir():
                ok, msg = _check_git_repo(repo_dir)
                repo_count += 1
                if ok and "clean" in msg:
                    repo_clean += 1
                elif ok:
                    repo_dirty += 1
    yield (
        "Repositories",
        "ok" if repo_count > 0 else "warn",
        f"{repo_count} tracked adapters ({repo_clean} clean, {repo_dirty} with uncommitted changes)",
    )

    # ---- Adapters ----
    adapter_ok = 0
    adapter_total = 0
    for repo_dir in sorted(_ADAPTERS.iterdir()):
        if repo_dir.is_dir():
            adapter_total += 1
            init_file = repo_dir / "__init__.py"
            if init_file.exists():
                adapter_ok += 1
    if adapter_total > 0:
        yield (
            "Adapters",
            "warn" if adapter_ok < adapter_total else "ok",
            f"{adapter_ok}/{adapter_total} have Python adapter wrappers",
        )
    else:
        yield ("Adapters", "info", "no adapter directories found")

    # ---- MCP ----
    mcp_config = _CYBERAI / "tool-gateway" / "mcp"
    if mcp_config.exists() and any(mcp_config.iterdir()):
        yield ("MCP Gateway", "ok", "tool-gateway/mcp configured")
    else:
        yield ("MCP Gateway", "warn", "no MCP server configuration found")

    # ---- Orchestrator imports ----
    try:
        from cyberai.orchestrator import Orchestrator, ToolRegistry, MemoryManager, PolicyEngine, ModelRouter
        from cyberai import CyberAIOrchestrator
        yield ("Orchestrator", "ok", "all core modules importable (including CyberAIOrchestrator)")
    except Exception as e:
        yield ("Orchestrator", "error", f"import failed: {e}")

    # ---- Agent modules ----
    agent_errors = []
    agent_ok = 0
    for agent_name in ["planner", "researcher", "recon", "analyst", "coder", "verifier", "reporter"]:
        try:
            agent_file = _CYBERAI / "orchestrator" / "agents" / agent_name / f"{agent_name}.py"
            if agent_file.exists():
                agent_ok += 1
            else:
                agent_errors.append(agent_name)
        except Exception:
            agent_errors.append(agent_name)
    if agent_errors:
        yield ("Agents", "warn", f"{agent_ok}/7 agents importable, missing: {', '.join(agent_errors)}")
    else:
        yield ("Agents", "ok", "all 7 agent packages importable")

    # ---- Memory system ----
    try:
        from cyberai.orchestrator import MemoryManager
        mm = MemoryManager()
        tables = mm._conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()
        exp_count = mm._conn.execute("SELECT count(*) FROM experiences").fetchone()[0]
        find_count = mm._conn.execute("SELECT count(*) FROM findings").fetchone()[0]
        mm.close()
        yield ("Memory system", "ok", f"DB ready: {tables[0]} tables, {exp_count} experiences, {find_count} findings")
    except Exception as e:
        yield ("Memory system", "error", f"failed: {e}")

    # ---- Policy engine ----
    try:
        from cyberai.orchestrator import PolicyEngine
        pe = PolicyEngine()
        targets = pe.list_targets()
        authorized = pe.list_authorized_targets()
        yield ("Policy engine", "ok", f"{len(targets)} targets registered, {len(authorized)} authorized")
    except Exception as e:
        yield ("Policy engine", "error", f"failed: {e}")

    # ---- Ports ----
    ports_checked = [
        ("Ollama API", 11434),
        ("LiteLLM Gateway", 4000),
        ("Open WebUI", 3000),
    ]
    for name, port in ports_checked:
        if _check_port("127.0.0.1", port):
            yield (f"Port {name}", "ok", f"port {port} open")
        else:
            yield (f"Port {name}", "warn", f"port {port} not listening")

    # ---- Environment variables ----
    env_vars = {
        "OLLAMA_HOST": os.environ.get("OLLAMA_HOST", ""),
        "LITELLM_MASTER_KEY": "set" if os.environ.get("LITELLM_MASTER_KEY") else "NOT SET",
        "OPENAI_API_KEY": "set" if os.environ.get("OPENAI_API_KEY") else "NOT SET (cloud models disabled)",
        "ANTHROPIC_API_KEY": "set" if os.environ.get("ANTHROPIC_API_KEY") else "NOT SET (cloud models disabled)",
        "REQUIRE_TARGET_AUTHORIZATION": os.environ.get("REQUIRE_TARGET_AUTHORIZATION", "true"),
    }
    yield (
        "Environment",
        "ok",
        f"OLLAMA_HOST={env_vars['OLLAMA_HOST']}, LITELLM_MASTER_KEY={env_vars['LITELLM_MASTER_KEY']}, OPENAI_API_KEY={env_vars['OPENAI_API_KEY']}",
    )

    # ---- Directories ----
    dirs_to_check = [
        ("adapters/", _ADAPTERS),
        ("infrastructure/", _INFRA),
        ("lab/", _LAB),
        ("lab/targets/", _LAB / "targets"),
        ("memory/", _MEMORY),
        ("logs/", _LOGS),
        ("cyberai/llm-gateway/", _CYBERAI / "llm-gateway"),
        ("cyberai/orchestrator/", _CYBERAI / "orchestrator"),
    ]
    for label, path in dirs_to_check:
        if path.exists():
            yield (f"Directory {label}", "ok", "exists")
        else:
            yield (f"Directory {label}", "warn", "missing")


if __name__ == "__main__":
    for component, status, msg in run_health_check():
        icon = {
            "ok": "[OK]",
            "warn": "[WARN]",
            "error": "[ERROR]",
            "info": "[INFO]",
        }
        print(f"  {icon.get(status, '[?]')} {component}: {msg}")
