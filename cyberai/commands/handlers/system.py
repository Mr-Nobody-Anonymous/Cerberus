"""System commands: /help, /status, /doctor, /health."""

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand
from cyberai.commands.registry import get_registry


def _help(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    registry = get_registry()
    if parsed.args:
        spec = registry.command(parsed.arg(0))
        if spec is None:
            return CommandResult.failure("help",
                                         f"unknown command: /{parsed.arg(0)}")
        return CommandResult.success("help", data={
            "name": spec.name, "category": spec.category,
            "description": spec.description, "usage": spec.usage,
            "examples": spec.examples, "aliases": spec.aliases,
        })
    return CommandResult.success("help", data={
        "categories": {
            cat: [{"name": s.name, "description": s.description}
                  for s in registry.specs(category=cat)]
            for cat in registry.categories()
        },
        "names": registry.names(),
    })


def _status(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    try:
        snapshot = ctx.status_snapshot()
        return CommandResult.success("status", data=snapshot)
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("status", f"{type(e).__name__}: {e}")


def _health(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Component health probe (ports + DBs), mirroring /api/system-health."""
    import socket

    def port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    components = []
    try:
        ctx.status_snapshot()
        components.append({"name": "Orchestrator", "status": "HEALTHY"})
    except Exception as e:  # noqa: BLE001
        components.append({"name": "Orchestrator", "status": "OFFLINE",
                           "detail": str(e)})
    components.append({"name": "Ollama",
                       "status": "HEALTHY" if port_open(11434) else "OFFLINE",
                       "detail": "localhost:11434"})
    components.append({"name": "LLM Gateway",
                       "status": "HEALTHY" if port_open(4000) else "OFFLINE",
                       "detail": "localhost:4000"})
    mm = None
    try:
        mm = ctx.memory_manager()
        components.append({"name": "Memory DB", "status": "HEALTHY",
                           "detail": str(getattr(mm, "db_path", ""))})
    except Exception as e:  # noqa: BLE001
        components.append({"name": "Memory DB", "status": "OFFLINE",
                           "detail": str(e)})
    finally:
        ctx.close_resource(mm)
    return CommandResult.success(
        "health", data={"components": components},
        rows=components, columns=["name", "status", "detail"],
    )


def _doctor(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Environment doctor: python, deps, docker, ollama, config."""
    import platform
    import shutil
    import sys

    checks = []
    checks.append({"name": "Python", "status": "OK",
                   "detail": f"{sys.version.split()[0]} ({platform.system()})"})
    for dep in ("fastapi", "uvicorn", "click", "rich", "prompt_toolkit"):
        try:
            __import__(dep)
            checks.append({"name": dep, "status": "OK", "detail": "installed"})
        except ImportError:
            checks.append({"name": dep, "status": "MISSING", "detail": "pip install " + dep})
    checks.append({"name": "Docker",
                   "status": "OK" if shutil.which("docker") else "MISSING",
                   "detail": "daemon required for adapters"})
    try:
        from cyberai.config import config
        cfg_ok = bool(config.get("privacy", "mode", "local_only"))
        checks.append({"name": "Config", "status": "OK", "detail": f"privacy={cfg_ok}"})
    except Exception as e:  # noqa: BLE001
        checks.append({"name": "Config", "status": "ERROR", "detail": str(e)})
    ok = all(c["status"] in ("OK",) for c in checks)
    return CommandResult(ok=ok, command="doctor",
                         data={"checks": checks},
                         message="environment healthy" if ok else "issues detected",
                         rows=checks, columns=["name", "status", "detail"])


def register(registry) -> None:
    from cyberai.commands.models import CommandSpec
    registry.register(CommandSpec(
        name="help", category="system", description="List commands or show help for one",
        handler=_help, aliases=["?", "h"],
        usage="help [command]", examples=["help", "help findings"],
    ))
    registry.register(CommandSpec(
        name="status", category="system", description="Platform status snapshot",
        handler=_status, aliases=["st"],
        usage="status",
    ))
    registry.register(CommandSpec(
        name="health", category="system", description="Component health probe",
        handler=_health, usage="health",
    ))
    registry.register(CommandSpec(
        name="doctor", category="system", description="Environment doctor (deps, docker, config)",
        handler=_doctor, usage="doctor",
    ))
