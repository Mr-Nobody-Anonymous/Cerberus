"""Target commands: /targets, /targets authorize."""

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand


def _targets(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """List registered targets with authorization + reachability state.

    Also honors the documented subcommand syntax:
        /targets authorize <id>   → delegates to _authorize
        /targets revoke <id>      → delegates to _revoke
    """
    sub = parsed.arg(0)
    if sub == "authorize":
        return _authorize(ctx, parsed)
    if sub == "revoke":
        return _revoke(ctx, parsed)

    import socket

    pe = None
    try:
        pe = ctx.policy()
        rows = pe.list_targets()
        out = []
        for t in rows:
            host = t.get("host", "")
            port = int(t.get("port") or 0)
            reachable = False
            if host and port:
                try:
                    with socket.create_connection((host, port), timeout=1.0):
                        reachable = True
                except OSError:
                    reachable = False
            if not t.get("allowed"):
                state = "UNAUTHORIZED"
            elif not reachable:
                state = "OFFLINE"
            else:
                state = "ACTIVE"
            out.append({**t, "state": state, "reachable": reachable})
        return CommandResult.success(
            "targets", data={"targets": out, "total": len(out)},
            rows=out, columns=["id", "host", "port", "type", "allowed", "state"],
        )
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("targets", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(pe)


def _authorize(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Authorize a target for active testing (policy-gated write).

    /targets authorize <target_id> — flips allowed=true via PolicyEngine.
    """
    # Works both as "/targets authorize <id>" (arg 1) and the hidden
    # "/targets-authorize <id>" alias (arg 0).
    target_id = parsed.arg(1) if parsed.arg(0) in ("authorize", "revoke") else parsed.arg(0)
    if not target_id:
        return CommandResult.failure("targets",
                                      "usage: /targets authorize <target_id>")
    pe = None
    try:
        pe = ctx.policy()
        existing = pe.get_target(target_id)
        if not existing:
            return CommandResult.failure("targets", f"unknown target: {target_id}")
        pe.register_target({**existing, "allowed": True})
        ctx.publish("audit", {
            "actor": "OPERATOR", "agent": "-", "tool": "policy",
            "target": target_id, "action": "authorize target",
            "result": "SUCCESS", "session": "-",
        })
        return CommandResult.success("targets", data={"authorized": target_id},
                                     message=f"target {target_id} authorized")
    except PermissionError as e:
        return CommandResult.blocked_result("targets", str(e))
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("targets", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(pe)


def _revoke(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Revoke a target's authorization (policy-gated write).

    /targets revoke <target_id> — flips allowed=false via PolicyEngine.
    """
    target_id = parsed.arg(0) if parsed.name == "targets" else parsed.arg(1)
    if parsed.name == "targets" and parsed.arg(0) in ("authorize", "revoke"):
        target_id = parsed.arg(1)
    if not target_id:
        return CommandResult.failure("targets",
                                      "usage: /targets revoke <target_id>")
    pe = None
    try:
        pe = ctx.policy()
        existing = pe.get_target(target_id)
        if not existing:
            return CommandResult.failure("targets", f"unknown target: {target_id}")
        pe.register_target({**existing, "allowed": False})
        ctx.publish("audit", {
            "actor": "OPERATOR", "agent": "-", "tool": "policy",
            "target": target_id, "action": "revoke target",
            "result": "SUCCESS", "session": "-",
        })
        return CommandResult.success("targets", data={"revoked": target_id},
                                     message=f"target {target_id} revoked")
    except PermissionError as e:
        return CommandResult.blocked_result("targets", str(e))
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("targets", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(pe)


def register(registry) -> None:
    from cyberai.commands.models import CommandSpec
    registry.register(CommandSpec(
        name="targets", category="security", description="List targets with auth + reachability state",
        handler=_targets, aliases=["target", "tg"],
        usage="targets [authorize <id>]",
        examples=["targets", "targets authorize lab-web-01"],
    ))
    # register the authorize subcommand as a hidden alias handler
    registry.register(CommandSpec(
        name="targets-authorize", category="security",
        description="Authorize a target (subcommand of /targets)",
        handler=_authorize, hidden=True,
    ))
