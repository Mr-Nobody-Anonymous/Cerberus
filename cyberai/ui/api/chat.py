"""Chat endpoints — ChatGPT-style conversations backed by sessions.

    GET    /api/v1/chats                 list chats (kind=chat sessions)
    POST   /api/v1/chats                 create a chat
    GET    /api/v1/chats/{id}            chat detail + messages
    PATCH  /api/v1/chats/{id}            rename / archive
    DELETE /api/v1/chats/{id}            delete chat + messages
    GET    /api/v1/chats/{id}/messages   message history
    POST   /api/v1/chats/{id}/messages   send a message (LLM reply)
    POST   /api/v1/chats/{id}/fork       fork the conversation

Messages sent without a slash-command go to the LLMGateway (role=reasoner,
local models first). Slash-commands dispatch through the shared command
bus so chat and CLI behave identically.
"""

import asyncio
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from cyberai.ui.api._helpers import (get_session_or_404, now_iso,
                                     parse_session_meta, require_fields,
                                     session_title, write_session_meta)
from cyberai.ui.api.chat_store import ChatStore

router = APIRouter(prefix="/api/v1/chats", tags=["chats"])


def _chat_store() -> ChatStore:
    return ChatStore()


def _chat_summary(session: Dict[str, Any]) -> Dict[str, Any]:
    meta = parse_session_meta(session)
    return {
        "id": session.get("id"),
        "title": session_title(session, meta),
        "objective": session.get("objective"),
        "status": session.get("status"),
        "kind": meta.get("kind", "chat"),
        "mode": meta.get("mode", "SIMULATE"),
        "model": meta.get("model"),
        "forked_from": meta.get("forked_from"),
        "created_at": session.get("started_at"),
        "updated_at": meta.get("updated_at") or session.get("started_at"),
        "message_count": meta.get("message_count", 0),
    }


def _touch(mm, session_id: str, meta: Dict[str, Any],
           message_count: Optional[int] = None) -> None:
    meta["updated_at"] = now_iso()
    if message_count is not None:
        meta["message_count"] = message_count
    write_session_meta(mm, session_id, meta)


# --------------------------------------------------------------------- list
@router.get("")
async def list_chats(q: str = "", limit: int = 100):
    """All chat-kind sessions, newest first."""
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        rows = mm.list_sessions()
    finally:
        mm.close()
    chats = []
    for s in rows:
        meta = parse_session_meta(s)
        if meta.get("kind", "mission") != "chat":
            continue
        if q and q.lower() not in session_title(s, meta).lower():
            continue
        chats.append(_chat_summary(s))
    return {"chats": chats[:limit], "total": len(chats)}


# ------------------------------------------------------------------- create
@router.post("", status_code=201)
async def create_chat(body: Dict[str, Any]):
    """Create a new chat. Body: {title?, objective?, mode?, model?}"""
    from cyberai.orchestrator import MemoryManager
    require_fields(body, )  # no required fields — title optional
    title = str(body.get("title") or "").strip()
    objective = str(body.get("objective") or "").strip()
    mode = str(body.get("mode") or "SIMULATE").upper()
    model = str(body.get("model") or "").strip() or None
    mm = MemoryManager()
    try:
        session_id = mm.create_session(target_id="", objective=objective or title or "Chat")
        meta = {
            "kind": "chat",
            "title": title or "New chat",
            "mode": mode,
            "model": model,
            "message_count": 0,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        write_session_meta(mm, session_id, meta)
        session = mm.get_session(session_id)
    finally:
        mm.close()
    return {"chat": _chat_summary(session)}


# ------------------------------------------------------------------- detail
@router.get("/{chat_id}")
async def get_chat(chat_id: str):
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    store = _chat_store()
    try:
        session = get_session_or_404(mm, chat_id)
        meta = parse_session_meta(session)
        if meta.get("kind", "mission") != "chat":
            raise HTTPException(status_code=404, detail="not a chat session")
        messages = store.list_messages(chat_id)
    finally:
        mm.close()
        store.close()
    return {"chat": _chat_summary(session), "messages": messages}


# -------------------------------------------------------------------- patch
@router.patch("/{chat_id}")
async def update_chat(chat_id: str, body: Dict[str, Any]):
    """Rename (title) or archive (status=archived) a chat."""
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    try:
        session = get_session_or_404(mm, chat_id)
        meta = parse_session_meta(session)
        if meta.get("kind", "mission") != "chat":
            raise HTTPException(status_code=404, detail="not a chat session")
        title = str(body.get("title") or "").strip()
        if title:
            meta["title"] = title
        status = str(body.get("status") or "").strip().lower()
        if status:
            if status not in ("active", "archived"):
                raise HTTPException(status_code=400,
                                    detail="status must be active|archived")
            meta["status"] = status
        _touch(mm, chat_id, meta)
        session = mm.get_session(chat_id)
    finally:
        mm.close()
    return {"chat": _chat_summary(session)}


# ------------------------------------------------------------------- delete
@router.delete("/{chat_id}")
async def delete_chat(chat_id: str):
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    store = _chat_store()
    try:
        session = get_session_or_404(mm, chat_id)
        meta = parse_session_meta(session)
        if meta.get("kind", "mission") != "chat":
            raise HTTPException(status_code=404, detail="not a chat session")
        store.delete_chat(chat_id)
    finally:
        mm.close()
        store.close()
    return {"deleted": chat_id}


# ----------------------------------------------------------------- messages
@router.get("/{chat_id}/messages")
async def list_messages(chat_id: str, limit: int = 200):
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    store = _chat_store()
    try:
        get_session_or_404(mm, chat_id)
        messages = store.list_messages(chat_id, limit=limit)
    finally:
        mm.close()
        store.close()
    return {"messages": messages}


@router.post("/{chat_id}/messages", status_code=201)
async def send_message(chat_id: str, body: Dict[str, Any]):
    """Send a message. Body: {content, mode?, model?}

    - Slash-command content dispatches through the shared command bus.
    - Natural language goes to the LLMGateway with the chat history.
    """
    require_fields(body, "content")
    content = str(body["content"]).strip()
    mode = str(body.get("mode") or "").strip().upper() or None
    model = str(body.get("model") or "").strip() or None

    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    store = _chat_store()
    try:
        session = get_session_or_404(mm, chat_id)
        meta = parse_session_meta(session)
        if meta.get("kind", "mission") != "chat":
            raise HTTPException(status_code=404, detail="not a chat session")
        if mode:
            meta["mode"] = mode
        if model:
            meta["model"] = model

        # 1) Persist the user message immediately.
        user_msg = store.append_message(chat_id, "user", content, mode=mode)

        # 2) Route: slash-command → command bus; else → LLM gateway.
        if content.startswith("/"):
            reply, reply_meta = await _handle_command(content)
        else:
            reply, reply_meta = await _generate_reply(
                store, chat_id, content, meta)

        assistant_msg = store.append_message(
            chat_id, "assistant", reply, model=reply_meta.get("model"),
            mode=mode or meta.get("mode"), metadata=reply_meta)

        count = len(store.list_messages(chat_id, limit=1000))
        _touch(mm, chat_id, meta, message_count=count)
    finally:
        mm.close()
        store.close()
    return {"user_message": user_msg, "assistant_message": assistant_msg}


async def _handle_command(content: str):
    """Dispatch a slash-command through the shared command bus."""
    from cyberai.commands import get_dispatcher, load_builtin_commands
    from cyberai.commands.context import CommandContext
    load_builtin_commands()
    dispatcher = get_dispatcher()
    ctx = CommandContext()
    result = dispatcher.execute(content, ctx)
    reply = result.message or (json_dump(result.data) if result.ok else result.error)
    return reply, {
        "command": result.command,
        "ok": result.ok,
        "blocked": result.blocked,
        "data": result.data,
    }


def json_dump(data: Any) -> str:
    import json
    try:
        return json.dumps(data, indent=2, default=str)
    except (TypeError, ValueError):
        return str(data)


async def _generate_reply(store: ChatStore, chat_id: str, content: str,
                          meta: Dict[str, Any]):
    """Generate an assistant reply via the LLMGateway fallback chain."""
    from cyberai.llm_gateway import LLMGateway
    history = store.list_messages(chat_id, limit=20)
    messages = []
    for m in history:
        if m["role"] in ("user", "assistant"):
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": content})

    gw = LLMGateway()
    try:
        result = await gw.complete(
            role="reasoner",
            messages=messages,
            alias=meta.get("model") or None,
        )
    finally:
        pass
    if result.get("success"):
        reply = result["content"]
        reply_meta = {
            "model": result.get("model"),
            "via": result.get("via"),
            "latency": result.get("latency"),
        }
    else:
        # Never fabricate content — surface the structured failure.
        parts = ["All model transports failed (never fabricating a reply)."]
        for err in result.get("errors", [])[:3]:
            parts.append(f"- {err}")
        for blk in result.get("blocked", [])[:3]:
            parts.append(f"- {blk}")
        parts.append("")
        parts.append("Start Ollama (`ollama serve`) or configure the "
                     "LiteLLM proxy, then resend.")
        reply = "\n".join(parts)
        reply_meta = {
            "model": result.get("model"),
            "via": "none",
            "failed": True,
            "errors": result.get("errors", []),
            "blocked": result.get("blocked", []),
        }
    return reply, reply_meta


# --------------------------------------------------------------------- fork
@router.post("/{chat_id}/fork", status_code=201)
async def fork_chat(chat_id: str, body: Dict[str, Any] = None):
    """Fork a chat: new session copying metadata + full message history."""
    body = body or {}
    from cyberai.orchestrator import MemoryManager
    mm = MemoryManager()
    store = _chat_store()
    try:
        session = get_session_or_404(mm, chat_id)
        meta = parse_session_meta(session)
        if meta.get("kind", "mission") != "chat":
            raise HTTPException(status_code=404, detail="not a chat session")

        new_id = mm.create_session(
            target_id=session.get("target_id") or "",
            objective=session.get("objective") or "",
        )
        new_meta = dict(meta)
        new_meta["kind"] = "chat"
        new_meta["forked_from"] = chat_id
        new_meta["title"] = str(body.get("title") or f"{meta.get('title', 'Chat')} (fork)")
        new_meta["created_at"] = now_iso()
        new_meta["updated_at"] = now_iso()
        write_session_meta(mm, new_id, new_meta)

        # Copy the message history.
        for m in store.list_messages(chat_id, limit=1000):
            store.append_message(
                new_id, m["role"], m["content"],
                model=m.get("model"), mode=m.get("mode"),
                metadata=m.get("metadata"),
            )
        new_session = mm.get_session(new_id)
    finally:
        mm.close()
        store.close()
    return {"chat": _chat_summary(new_session), "forked_from": chat_id}
