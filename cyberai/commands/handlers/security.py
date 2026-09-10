"""Security commands: /security, /approvals, /approve, /deny."""

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand


def _security(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Security center: policy state, blocked actions, recent policy events."""
    blocked = []
    for ev in ctx.event_store().history(limit=300):
        d = ev.to_dict()
        if d.get("type") == "policy.blocked":
            blocked.append(d.get("data", {}))
    pe = None
    try:
        pe = ctx.policy()
        all_targets = pe.list_targets()
        authorized = [t for t in all_targets if t.get("allowed")]
    except Exception:
        all_targets, authorized = [], []
    finally:
        ctx.close_resource(pe)
    recent = [
        {"type": d.get("type"), "data": d.get("data", {}), "ts": d.get("timestamp")}
        for d in (e.to_dict() for e in ctx.event_store().history(limit=50))
        if d.get("type") in ("policy.blocked", "approval.required",
                             "approval.granted", "approval.denied")
    ]
    return CommandResult.success("security", data={
        "policy": {
            "mode": "LAB_ONLY",
            "description": "Active testing restricted to explicitly authorized lab targets",
            "targets_registered": len(all_targets),
            "targets_authorized": len(authorized),
        },
        "blocked_actions": blocked,
        "recent_events": recent,
    })


def _approvals(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """List pending approvals (host supplies the queue via ctx)."""
    queue = getattr(ctx, "approval_queue", None)
    if queue is None:
        return CommandResult.success("approvals",
                                     data={"approvals": [], "note": "no approval queue attached"})
    pending = [a for a in queue if a.get("status") == "PENDING"]
    return CommandResult.success(
        "approvals", data={"approvals": pending},
        rows=pending, columns=["id", "action", "risk", "status"],
    )


def _decide(ctx: CommandContext, parsed: ParsedCommand,
            decision: str) -> CommandResult:
    approval_id = parsed.arg(0)
    if not approval_id:
        return CommandResult.failure(
            "approve" if decision == "granted" else "deny",
            "usage: /approve <id> | /deny <id>")
    queue = getattr(ctx, "approval_queue", None)
    if queue is None:
        return CommandResult.failure("approve", "no approval queue attached")
    match = next((a for a in queue if a.get("id") == approval_id), None)
    if not match:
        return CommandResult.failure("approve", f"unknown approval: {approval_id}")
    match["status"] = "APPROVED" if decision == "granted" else "DENIED"
    match["decided_at"] = _now_iso()
    ctx.publish(f"approval.{decision}", {"id": approval_id})
    ctx.publish("audit", {
        "actor": "OPERATOR", "agent": "-", "tool": "policy",
        "target": "-", "action": f"approval {decision} {approval_id}",
        "result": "SUCCESS", "session": "-",
    })
    return CommandResult.success(
        "approve" if decision == "granted" else "deny",
        data={"id": approval_id, "status": match["status"]},
        message=f"approval {approval_id} {decision}")


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _approve(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    return _decide(ctx, parsed, "granted")


def _deny(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    return _decide(ctx, parsed, "denied")


def register(registry) -> None:
    from cyberai.commands.models import CommandSpec
    registry.register(CommandSpec(
        name="security", category="security", description="Security center: policy, blocks, events",
        handler=_security, aliases=["sec"],
        usage="security",
    ))
    registry.register(CommandSpec(
        name="approvals", category="security", description="List pending approvals",
        handler=_approvals, usage="approvals",
    ))
    registry.register(CommandSpec(
        name="approve", category="security", description="Approve a pending action",
        handler=_approve, usage="approve <id>",
    ))
    registry.register(CommandSpec(
        name="deny", category="security", description="Deny a pending action",
        handler=_deny, usage="deny <id>",
    ))
