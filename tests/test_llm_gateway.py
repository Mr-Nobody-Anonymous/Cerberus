"""Phase B — LLM Gateway tests.

Covers:
- complete() transport fallback chain: LiteLLM proxy -> direct Ollama
- structured error entries on hop failure (never silently swallowed)
- local_only privacy mode provably blocks cloud routes at gateway level
- health() real probes with per-alias availability

All HTTP is served by httpx.MockTransport — no external services required.
"""

import json

import httpx
import pytest

from cyberai.llm_gateway import LLMGateway


def make_gateway(handler, local_only=True, master_key="sk-test"):
    """Build a gateway whose HTTP traffic is served by a MockTransport."""
    transport = httpx.MockTransport(handler)

    def factory(timeout):
        return httpx.AsyncClient(timeout=timeout, transport=transport)

    gw = LLMGateway(local_only=local_only, client_factory=factory)
    gw.litellm_master_key = master_key
    return gw


def ollama_chat_ok(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode())
    return httpx.Response(200, json={
        "model": body.get("model", ""),
        "message": {"role": "assistant", "content": "OLLAMA-SAYS-OK"},
    })


def litellm_chat_ok(request: httpx.Request) -> httpx.Response:
    assert request.headers.get("authorization") == "Bearer sk-test"
    return httpx.Response(200, json={
        "choices": [{"message": {"role": "assistant", "content": "LITELLM-SAYS-OK"}}],
    })


@pytest.mark.asyncio
async def test_litellm_hop_is_primary():
    """A healthy LiteLLM proxy answers before Ollama is ever contacted."""
    called = {"ollama": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/chat/completions":
            return litellm_chat_ok(request)
        if request.url.path == "/api/chat":
            called["ollama"] += 1
            return ollama_chat_ok(request)
        return httpx.Response(404)

    gw = make_gateway(handler)
    result = await gw.complete(role="reasoner", prompt="hello")
    assert result["success"] is True
    assert result["via"] == "litellm"
    assert result["content"] == "LITELLM-SAYS-OK"
    assert called["ollama"] == 0


@pytest.mark.asyncio
async def test_fallback_chain_litellm_fails_then_ollama():
    """When the proxy hop fails, the gateway falls through to direct Ollama
    and records a structured error for the failed hop."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(500, text="proxy down")
        if request.url.path == "/api/chat":
            return ollama_chat_ok(request)
        return httpx.Response(404)

    gw = make_gateway(handler)
    result = await gw.complete(role="reasoner", prompt="hello")
    assert result["success"] is True
    assert result["via"] == "ollama"
    assert result["content"] == "OLLAMA-SAYS-OK"
    assert any("litellm" in e for e in result["errors"]), result["errors"]


@pytest.mark.asyncio
async def test_all_hops_fail_never_fabricates():
    """Total failure returns success=False with empty content and structured
    errors for every hop."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    gw = make_gateway(handler)
    result = await gw.complete(role="reasoner", prompt="hello")
    assert result["success"] is False
    assert result["content"] == ""
    assert len(result["errors"]) == 2  # litellm + ollama both logged
    assert "Never fabricating" in result["message"]


@pytest.mark.asyncio
async def test_local_only_blocks_cloud_call():
    """local_only mode must block the cloud route at the gateway level:
    no HTTP request to the provider is attempted, and a structured block
    entry is returned and logged."""
    called = {"any": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["any"] += 1
        return httpx.Response(200, json={})

    gw = make_gateway(handler, local_only=True)
    result = await gw.complete(alias="cloud_reasoner", prompt="hello")
    assert result["success"] is False
    assert called["any"] == 0  # no network call whatsoever
    assert any("Blocked cloud route" in b for b in result["blocked"])
    assert gw._transport_chain("cloud_reasoner") == []


@pytest.mark.asyncio
async def test_hybrid_mode_reaches_provider():
    """With local_only disabled, the provider hop is reachable after the
    proxy hop fails."""
    called = {"provider": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.openai.com":
            called["provider"] += 1
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "OPENAI-SAYS-OK"}}],
            })
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(503, text="proxy down")
        return httpx.Response(404)

    gw = make_gateway(handler, local_only=False)
    # No real key needed: mock transport intercepts before the network,
    # but _call_provider raises without a key — set one via env.
    import os
    os.environ["OPENAI_API_KEY"] = "sk-fake-for-test"
    try:
        result = await gw.complete(alias="cloud_reasoner", prompt="hello")
    finally:
        os.environ.pop("OPENAI_API_KEY", None)
    assert result["success"] is True
    assert result["via"] == "provider"
    assert called["provider"] == 1


@pytest.mark.asyncio
async def test_health_reports_per_alias_availability():
    """health() really pings both transports and computes per-alias status."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.1:8b"}]})
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(404)

    gw = make_gateway(handler)
    health = await gw.health()
    assert health["ollama"]["status"] == "AVAILABLE"
    assert health["litellm"]["status"] == "AVAILABLE"

    aliases = health["aliases"]
    assert aliases["local_reasoner"]["status"] == "AVAILABLE"
    assert aliases["local_coder"]["status"] == "UNAVAILABLE"
    assert "not pulled" in aliases["local_coder"]["reason"]
    assert aliases["cloud_reasoner"]["status"] == "BLOCKED_LOCAL_ONLY"


@pytest.mark.asyncio
async def test_health_when_ollama_offline():
    """health() reports OFFLINE (not a crash) when Ollama is unreachable."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    gw = make_gateway(handler)
    health = await gw.health()
    assert health["ollama"]["status"] == "OFFLINE"
    assert health["aliases"]["local_reasoner"]["status"] == "OFFLINE"


@pytest.mark.asyncio
async def test_litellm_requires_master_key():
    """Without LITELLM_MASTER_KEY the proxy hop fails fast with a clear
    error and the chain continues to Ollama."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/chat":
            return ollama_chat_ok(request)
        return httpx.Response(500)

    gw = make_gateway(handler, master_key="")
    result = await gw.complete(role="reasoner", prompt="hello")
    assert result["success"] is True
    assert result["via"] == "ollama"
    assert any("LITELLM_MASTER_KEY" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_unknown_alias_fails_cleanly():
    gw = make_gateway(lambda req: httpx.Response(200, json={}))
    result = await gw.complete(alias="does_not_exist", prompt="x")
    assert result["success"] is False
    assert any("Unknown model alias" in e for e in result["errors"])


def test_generate_is_backward_compatible_alias():
    """generate() must remain callable with the legacy signature."""
    import inspect

    sig = inspect.signature(LLMGateway.generate)
    assert "role" in sig.parameters
    assert "prompt" in sig.parameters
    assert "messages" in sig.parameters
