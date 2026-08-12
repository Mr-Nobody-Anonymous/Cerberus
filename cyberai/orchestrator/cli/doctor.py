"""
Health check / doctor module for the Cyber AI Orchestrator.

Inspects every major subsystem and reports status as:
  OK      - Component is healthy and working
  WARN    - Component has issues but is usable
  ERROR   - Component is unavailable or broken
  INFO    - Informational (not a problem)
"""

import importlib
import logging
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Iterator, Tuple

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# Ensure workspace root is at front of sys.path for package imports
sys.path.insert(0, str(WORKSPACE_ROOT))
importlib.invalidate_caches()
_PLATFORM = WORKSPACE_ROOT / "cyberai"
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


def _import_from_path(module_name: str, file_path: Path):
    """Import a module from a file path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


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
        yield ("Docker", "ok", "installed (not verified if running)")
    else:
        yield ("Docker", "warn", "not installed - Docker-dependent integrations will be unavailable")

    # ---- Ollama ----
    if _check_port("127.0.0.1", 11434):
        yield ("Ollama", "ok", "running on localhost:11434")
    else:
        yield ("Ollama", "warn", "not running on localhost:11434")

    # ---- LiteLLM / LLM Gateway ----
    if _check_port("127.0.0.1", 4000):
        yield ("LiteLLM Gateway", "ok", "running on localhost:4000")
    else:
        yield ("LiteLLM Gateway", "warn", "not running on localhost:4000")

    # ---- LLM availability ----
    models_yaml = _PLATFORM / "llm-gateway" / "models" / "models.yaml"
    if models_yaml.exists():
        import yaml
        with open(models_yaml) as f:
            data = yaml.safe_load(f)
        ready = [name for name, cfg in data.get("models", {}).items() if cfg.get("status") == "READY"]
        if ready:
            yield ("LLM availability", "ok", f"Models ready: {', '.join(ready)}")
        else:
            yield ("LLM availability", "warn", "No models marked as READY (models may need Ollama to be running)")
    else:
        yield ("LLM availability", "warn", "Model registry not found")

    # ---- Open WebUI ----
    if _check_port("127.0.0.1", 3000):
        yield ("Open WebUI", "ok", "running on localhost:3000")
    else:
        yield ("Open WebUI", "info", "not running (start with docker-compose if installed)")

    # ---- Repositories ----
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
    mcp_config = _ADAPTERS.parent / "cyberai" / "tool-gateway" / "mcp"
    if mcp_config.exists() and any(mcp_config.iterdir()):
        yield ("MCP Gateway", "ok", "tool-gateway/mcp configured")
    else:
        yield ("MCP Gateway", "warn", "no MCP server configuration found")

    # ---- Orchestrator imports ----
    try:
        from cyberai.orchestrator import Orchestrator, ToolRegistry, MemoryManager, PolicyEngine, ModelRouter
        yield ("Orchestrator", "ok", "all core modules importable")
    except Exception as e:
        yield ("Orchestrator", "error", f"import failed: {e}")

    # ---- Agent modules ----
    agent_errors = []
    agent_ok = 0
    for agent_name in ["planner", "researcher", "recon", "analyst", "coder", "verifier", "reporter"]:
        try:
            agent_file = _PLATFORM / "orchestrator" / "agents" / agent_name / f"{agent_name}.py"
            if agent_file.exists():
                _import_from_path(f"agent_{agent_name}", agent_file)
                agent_ok += 1
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
        "OLLAMA_HOST": os_env("OLLAMA_HOST"),
        "LITELLM_MASTER_KEY": "set" if os_env("LITELLM_MASTER_KEY") else "NOT SET",
        "OPENAI_API_KEY": "set" if os_env("OPENAI_API_KEY") else "NOT SET (cloud models disabled)",
        "ANTHROPIC_API_KEY": "set" if os_env("ANTHROPIC_API_KEY") else "NOT SET (cloud models disabled)",
        "REQUIRE_TARGET_AUTHORIZATION": os_env("REQUIRE_TARGET_AUTHORIZATION", "true"),
    }
    has_env = any(v == "set" or v.startswith("http") for v in env_vars.values())
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
        ("cyberai/llm-gateway/", _PLATFORM / "llm-gateway"),
        ("cyberai/orchestrator/", _PLATFORM / "orchestrator"),
    ]
    for label, path in dirs_to_check:
        if path.exists():
            yield (f"Directory {label}", "ok", "exists")
        else:
            yield (f"Directory {label}", "warn", "missing")


def os_env(key: str, default: str = "") -> str:
    """Get environment variable with a default."""
    import os
    return os.environ.get(key, default)


if __name__ == "__main__":
    for component, status, msg in run_health_check():
        icon = {
            "ok": "[OK]",
            "warn": "[WARN]",
            "error": "[ERROR]",
            "info": "[INFO]",
        }
        print(f"  {icon.get(status, '[?]')} {component}: {msg}")
