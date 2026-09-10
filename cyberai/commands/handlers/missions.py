"""Mission commands: /run, /stop, /mission, /dryrun.

/run launches the orchestrator EXACTLY like the Web UI's POST /api/tasks:
same CyberAIOrchestrator flags, same event publishing, same PermissionError
handling. Hosts attach a mission_runner so async launching is uniform.
"""

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand

_MODES = ("SIMULATE", "PLAN", "LAB", "AUTHORIZED")


def _mode_from(parsed: ParsedCommand, default: str = "SIMULATE") -> str:
    mode = parsed.kwarg("mode", default).upper()
    if mode not in _MODES:
        raise ValueError(
            f"invalid mode {mode!r}; valid: {', '.join(_MODES)}")
    return mode


def _flags_for_mode(mode: str) -> dict:
    """Map execution mode → CyberAIOrchestrator flags (safest defaults)."""
    return {
        "SIMULATE": {"simulate": True, "dry_run": False},
        "PLAN": {"simulate": True, "dry_run": True},
        "LAB": {"simulate": False, "dry_run": False},
        "AUTHORIZED": {"simulate": False, "dry_run": False},
    }[mode]


def _run(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Launch a mission. Natural language after /run is the objective.

    /run analyze lab-web-01 target=lab-web-01 mode=SIMULATE
    """
    objective = " ".join(parsed.args).strip()
    if not objective:
        return CommandResult.failure("run", "usage: /run <objective> [target=<id>] [mode=SIMULATE|PLAN|LAB|AUTHORIZED]")
    target_id = parsed.kwarg("target", "") or None
    try:
        mode = _mode_from(parsed)
    except ValueError as e:
        return CommandResult.failure("run", str(e))
    flags = _flags_for_mode(mode)

    if ctx.mission_runner is None:
        return CommandResult.failure(
            "run", "no mission runner attached to this host; "
            "use 'cyber-ai task -o <objective>' instead")

    try:
        ctx.mission_runner(objective=objective, target_id=target_id,
                           mode=mode, **flags)
    except PermissionError as e:
        return CommandResult.blocked_result("run", str(e))
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("run", f"{type(e).__name__}: {e}")
    ctx.publish("audit", {
        "actor": "OPERATOR", "agent": "-", "tool": "console",
        "target": target_id or "-", "action": f"mission launch ({mode})",
        "result": "ISSUED", "session": "-",
    })
    return CommandResult.success("run", data={
        "status": "accepted", "objective": objective,
        "target_id": target_id, "mode": mode,
    }, message=f"mission accepted ({mode})")


def _stop(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Cooperative stop of the running orchestrator (never errors)."""
    holder = ctx.orchestrator_holder or {}
    orch = holder.get("orchestrator")
    if orch is None:
        return CommandResult.success("stop", data={"status": "no_active_task"})
    try:
        orch.stop()
        ctx.publish("audit", {
            "actor": "OPERATOR", "agent": "-", "tool": "console",
            "target": "-", "action": "stop task", "result": "ISSUED",
            "session": "-",
        })
        return CommandResult.success("stop", data={"status": "stop_requested"})
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("stop", f"{type(e).__name__}: {e}")


def _mission_status(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Active mission status from the live orchestrator holder."""
    holder = ctx.orchestrator_holder or {}
    orch = holder.get("orchestrator")
    if orch is None:
        return CommandResult.success("mission", data={"status": "idle"})
    try:
        return CommandResult.success("mission", data={
            "status": "running",
            "objective": getattr(orch, "current_objective", None),
        })
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("mission", f"{type(e).__name__}: {e}")


def register(registry) -> None:
    from cyberai.commands.models import CommandSpec
    registry.register(CommandSpec(
        name="run", category="missions", description="Launch a mission (safest mode default)",
        handler=_run, aliases=["mission-run"],
        usage="run <objective> [target=<id>] [mode=SIMULATE|PLAN|LAB|AUTHORIZED]",
        examples=['run analyze the web target target=lab-web-01 mode=SIMULATE'],
        destructive=True,
    ))
    registry.register(CommandSpec(
        name="stop", category="missions", description="Stop the running mission",
        handler=_stop, usage="stop", destructive=True,
    ))
    registry.register(CommandSpec(
        name="mission", category="missions", description="Active mission status",
        handler=_mission_status, usage="mission",
    ))
