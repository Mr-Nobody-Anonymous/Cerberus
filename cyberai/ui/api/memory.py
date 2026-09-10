"""Memory endpoints.

    GET /api/v1/memory/stats    memory store statistics
    GET /api/v1/memory/search   semantic search
"""

from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


@router.get("/stats")
async def memory_stats():
    from cyberai.memory.memory_store import MemoryStore
    store = MemoryStore()
    try:
        return {"stats": store.get_stats()}
    finally:
        store.close()


@router.get("/search")
async def memory_search(q: str = "", limit: int = 20):
    if not q.strip():
        return {"results": []}
    from cyberai.memory.memory_store import MemoryStore
    store = MemoryStore()
    try:
        results = store.semantic_search(q.strip(), limit=limit)
        return {"results": results, "query": q}
    finally:
        store.close()
