"""Event endpoints — SSE stream + pollable feed.

    GET /api/v1/events          pollable event feed (EventStore-backed)
    GET /api/v1/events/stream   Server-Sent-Events live stream
"""

import asyncio
import json
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from cyberai.ui.server import EVENT_BUS

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("")
async def event_feed(since: str = "", limit: int = 200):
    """Pollable canonical event feed (same store the SSE stream reads)."""
    from cyberai.orchestrator.event_store import get_event_store
    store = get_event_store()
    out = [ev.to_dict() for ev in store.history(limit=limit, since=since)]
    return {"events": out, "stats": store.stats()}


@router.get("/stream")
async def event_stream():
    """Live SSE stream — identical wire format to /api/realtime."""
    subscriber_id = EVENT_BUS.subscribe()

    async def generator():
        try:
            # Replay recent history first, then stream live events.
            for payload in EVENT_BUS.history(limit=60):
                yield f"data: {json.dumps(payload)}\n\n"
            queue = EVENT_BUS._subscribers.get(subscriber_id)
            if queue is None:
                return
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield f"data: {json.dumps(payload)}\n\n"
        finally:
            EVENT_BUS.unsubscribe(subscriber_id)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
