"""Session commands: /sessions, /session, /resume, /fork, /rename.

These REUSE the existing MemoryManager session system (spec: do not
create a second persistence system). Chat threads in the new UI map to
sessions rows; ``kind`` distinguishes operator chats from mission runs.
"""

import json
from datetime import datetime, timezone

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_meta(session: dict) -> dict:
    """Parse the sessions.metadata JSON column defensively."""
    raw = session.get("metadata") or ""
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}


def _list(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    mm = None
    try:
        mm = ctx.memory_manager()
        rows = mm.list_sessions()
        q = parsed.kwarg("q", "").lower()
        if q:
            rows = [s for s in rows
                    if q in (s.get("objective") or "").lower()
                    or q in (s.get("id") or "").lower()
                    or q in (s.get("target_id") or "").lower()]
        status = parsed.kwarg("status", "")
        if status:
            rows = [s for s in rows if (s.get("status") or "") == status]
        limit = int(parsed.kwarg("limit", "100"))
        out = []
        for s in rows[:limit]:
            meta = _session_meta(s)
            out.append({
                "id": s.get("id"),
                "title": meta.get("title") or (s.get("objective") or "Untitled")[:80],
                "objective": s.get("objective"),
                "target_id": s.get("target_id"),
                "status": s.get("status"),
                "kind": meta.get("kind", "mission"),
                "started_at": s.get("started_at"),
                "completed_at": s.get("completed_at"),
                "findings_count": s.get("findings_count"),
            })
        return CommandResult.success(
            "sessions", data={"sessions": out, "total": len(rows)},
            rows=out, columns=["id", "title", "status", "kind", "started_at"],
        )
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("sessions", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(mm)


def _show(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    session_id = parsed.arg(0)
    if not session_id:
        return CommandResult.failure("session", "usage: /session <id>")
    mm = None
    try:
        mm = ctx.memory_manager()
        s = mm.get_session(session_id)
        if not s:
            return CommandResult.failure("session", f"unknown session: {session_id}")
        findings = [f for f in mm.get_findings()
                    if f.get("session_id") == session_id]
        return CommandResult.success("session", data={
            "session": s, "findings": findings,
            "metadata": _session_meta(s),
        })
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("session", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(mm)


def _rename(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Rename a session by writing title into the metadata JSON column.

    Title comes from title=... (quoted for multi-word) or from the
    remaining positional args: /rename <id> My New Title
    """
    session_id = parsed.arg(0)
    title = parsed.kwarg("title", "")
    if not title and len(parsed.args) > 1:
        title = " ".join(parsed.args[1:])
    if not session_id or not title:
        return CommandResult.failure("rename", 'usage: /rename <id> title="New title" | /rename <id> New title')
    mm = None
    try:
        mm = ctx.memory_manager()
        s = mm.get_session(session_id)
        if not s:
            return CommandResult.failure("rename", f"unknown session: {session_id}")
        meta = _session_meta(s)
        meta["title"] = title
        with mm._conn:
            mm._conn.execute(
                "UPDATE sessions SET metadata = ? WHERE id = ?",
                (json.dumps(meta), session_id),
            )
        return CommandResult.success("rename",
                                     data={"id": session_id, "title": title},
                                     message=f"renamed to {title!r}")
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("rename", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(mm)


def _fork(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Fork a session: new row copying objective/target, linked via metadata."""
    session_id = parsed.arg(0)
    if not session_id:
        return CommandResult.failure("fork", "usage: /fork <id>")
    mm = None
    try:
        mm = ctx.memory_manager()
        s = mm.get_session(session_id)
        if not s:
            return CommandResult.failure("fork", f"unknown session: {session_id}")
        new_id = mm.create_session(
            target_id=s.get("target_id") or "",
            objective=s.get("objective") or "",
        )
        meta = _session_meta(s)
        meta["forked_from"] = session_id
        meta["kind"] = meta.get("kind", "mission")
        with mm._conn:
            mm._conn.execute(
                "UPDATE sessions SET metadata = ? WHERE id = ?",
                (json.dumps(meta), new_id),
            )
        ctx.publish("audit", {
            "actor": "OPERATOR", "agent": "-", "tool": "memory",
            "target": "-", "action": f"fork session {session_id}",
            "result": "SUCCESS", "session": new_id,
        })
        return CommandResult.success("fork", data={
            "id": new_id, "forked_from": session_id,
        }, message=f"forked {session_id} → {new_id}")
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("fork", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(mm)


def register(registry) -> None:
    from cyberai.commands.models import CommandSpec
    registry.register(CommandSpec(
        name="sessions", category="history", description="List sessions (chats + missions)",
        handler=_list, aliases=["s", "history"],
        usage="sessions [q=text] [status=active] [limit=100]",
        examples=["sessions", "sessions status=active"],
    ))
    registry.register(CommandSpec(
        name="session", category="history", description="Show one session with findings",
        handler=_show, usage="session <id>",
    ))
    registry.register(CommandSpec(
        name="rename", category="history", description="Rename a session",
        handler=_rename, usage="rename <id> title=New title",
    ))
    registry.register(CommandSpec(
        name="fork", category="history", description="Fork a session into a new one",
        handler=_fork, usage="fork <id>",
    ))
