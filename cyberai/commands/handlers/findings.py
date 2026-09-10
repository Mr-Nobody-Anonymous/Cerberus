"""Findings commands: /findings, /findings verify|reject|likely."""

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand

_VALID_STATES = ("UNVERIFIED", "LIKELY", "VERIFIED", "REJECTED")


def _findings(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """List findings, filterable by status= and text query q=."""
    mm = None
    try:
        mm = ctx.memory_manager()
        status = parsed.kwarg("status", "").strip().upper()
        if status and status not in _VALID_STATES:
            return CommandResult.failure(
                "findings", f"invalid status {status!r}; valid: {', '.join(_VALID_STATES)}")
        rows = mm.get_findings(status=(status or None))
        q = parsed.kwarg("q", "").lower()
        if q:
            rows = [f for f in rows
                    if q in str(f.get("observation", "")).lower()
                    or q in str(f.get("source", "")).lower()]
        limit = int(parsed.kwarg("limit", "200"))
        return CommandResult.success(
            "findings", data={"findings": rows[:limit], "total": len(rows)},
            rows=rows[:limit],
            columns=["id", "target_id", "status", "confidence", "observation"],
        )
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("findings", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(mm)


def _set_status(ctx: CommandContext, parsed: ParsedCommand,
                new_status: str) -> CommandResult:
    finding_id = parsed.arg(0)
    if not finding_id:
        return CommandResult.failure(
            "findings", f"usage: /findings {new_status.lower()} <finding_id>")
    mm = None
    try:
        mm = ctx.memory_manager()
        match = [f for f in mm.get_findings() if f.get("id") == finding_id]
        if not match:
            return CommandResult.failure("findings", f"unknown finding: {finding_id}")
        mm.update_finding_status(finding_id, new_status)
        ctx.publish("audit", {
            "actor": "OPERATOR", "agent": "-", "tool": "memory",
            "target": "-", "action": f"finding {new_status.lower()}",
            "result": "SUCCESS", "session": match[0].get("session_id", "-"),
        })
        return CommandResult.success(
            "findings", data={"id": finding_id, "status": new_status},
            message=f"finding {finding_id} → {new_status}")
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("findings", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(mm)


def _verify(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    return _set_status(ctx, parsed, "VERIFIED")


def _reject(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    return _set_status(ctx, parsed, "REJECTED")


def _likely(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    return _set_status(ctx, parsed, "LIKELY")


def register(registry) -> None:
    from cyberai.commands.models import CommandSpec
    registry.register(CommandSpec(
        name="findings", category="operations", description="List/filter findings by status",
        handler=_findings, aliases=["f", "finding"],
        usage="findings [status=UNVERIFIED|LIKELY|VERIFIED|REJECTED] [q=text] [limit=200]",
        examples=["findings", "findings status=UNVERIFIED", "findings q=sql"],
    ))
    registry.register(CommandSpec(
        name="verify", category="operations", description="Mark a finding VERIFIED",
        handler=_verify, usage="verify <finding_id>",
    ))
    registry.register(CommandSpec(
        name="reject", category="operations", description="Mark a finding REJECTED",
        handler=_reject, usage="reject <finding_id>",
    ))
    registry.register(CommandSpec(
        name="likely", category="operations", description="Mark a finding LIKELY",
        handler=_likely, usage="likely <finding_id>",
    ))
