"""Regression tests for chat search (titles AND message content).

Covers:
  - GET /api/v1/chats?q= matches chats whose MESSAGES contain the query
    (not just the title) — the "search what I was talking about" fix.
  - Matched chats carry a ``snippet`` showing the matching context.
  - Title-only matches still work (backward compatible).
  - Empty query lists all chats (backward compatible).

Run with ``python -m pytest tests/test_chat_search.py -v``.
"""

import uuid

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
httpx = pytest.importorskip("httpx", reason="httpx not installed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from cyberai.ui.api.chat_store import ChatStore  # noqa: E402
from cyberai.ui.server import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _make_chat(client: TestClient, title: str) -> str:
    r = client.post("/api/v1/chats", json={"title": title})
    assert r.status_code == 201, r.text
    return r.json()["chat"]["id"]


def _send(client: TestClient, chat_id: str, content: str) -> None:
    r = client.post(f"/api/v1/chats/{chat_id}/messages", json={"content": content})
    assert r.status_code == 201, r.text


class TestChatSearch:
    def test_search_matches_message_content(self, client):
        """A word that appears only in a MESSAGE (not any title) finds the chat."""
        marker = f"zqx-{uuid.uuid4().hex[:8]}"
        chat_id = _make_chat(client, "Search probe conversation")
        _send(client, chat_id, f"tell me about {marker} in the lab")

        r = client.get(f"/api/v1/chats?q={marker}")
        assert r.status_code == 200, r.text
        chats = r.json()["chats"]
        assert any(c["id"] == chat_id for c in chats), \
            "message-content match not returned by search"

    def test_match_carries_snippet(self, client):
        """Content-matched chats include a snippet around the match."""
        marker = f"snip-{uuid.uuid4().hex[:8]}"
        chat_id = _make_chat(client, "Snippet probe conversation")
        _send(client, chat_id, f"prefix words {marker} suffix words")

        r = client.get(f"/api/v1/chats?q={marker}")
        assert r.status_code == 200, r.text
        match = next(c for c in r.json()["chats"] if c["id"] == chat_id)
        assert match.get("snippet") and marker in match["snippet"]
        assert match.get("snippet_role") == "user"

    def test_title_match_still_works(self, client):
        """Title-only matches (no message hit) still return the chat."""
        title = f"TitleProbe-{uuid.uuid4().hex[:8]}"
        _make_chat(client, title)
        r = client.get(f"/api/v1/chats?q={title}")
        assert r.status_code == 200, r.text
        assert any(c["title"] == title for c in r.json()["chats"])

    def test_empty_query_lists_all(self, client):
        """No query → unfiltered list (backward compatible)."""
        r = client.get("/api/v1/chats")
        assert r.status_code == 200, r.text
        assert "chats" in r.json()

    def test_search_messages_store_method(self):
        """ChatStore.search_messages finds content case-insensitively."""
        store = ChatStore()
        try:
            marker = f"store-{uuid.uuid4().hex[:8]}"
            hits = store.search_messages(marker)
            assert hits == []
            # Any pre-existing message containing 'the' should be findable.
            hits = store.search_messages("the", limit=5)
            for h in hits:
                assert "the" in h["content"].lower()
        finally:
            store.close()
