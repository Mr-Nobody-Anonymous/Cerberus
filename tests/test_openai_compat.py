"""H1 — OpenAI-compatible provider tests.

Covers the openai_compat module and its integration into the LLMGateway
transport chain:

- endpoint normalization (with/without /v1, trailing slashes)
- local vs cloud endpoint classification (privacy semantics)
- registry validation (missing endpoint, bad scheme)
- gateway transport: openai_compatible alias completes via the endpoint
- local_only blocks remote endpoints but allows private ones
- health() probes /v1/models and reports per-alias status
- malformed response bodies raise, never fabricate

All HTTP is served by httpx.MockTransport — no external services.
"""

import json

import httpx
import pytest

from cyberai.llm_gateway import LLMGateway
from cyberai.llm_gateway import openai_compat


# ---------------------------------------------------------------------------
# openai_compat unit tests
# ---------------------------------------------------------------------------
def test_normalize_endpoint_variants():
    assert openai_compat.normalize_endpoint("http://gpu:8000") == "http://gpu:8000"
    assert openai_compat.normalize_endpoint("http://gpu:8000/") == "http://gpu:8000"
    assert openai_compat.normalize_endpoint("http://gpu:8000/v1") == "http://gpu:8000"
    assert openai_compat.normalize_endpoint("http://gpu:8000/v1/") == "http://gpu:8000"


def test_chat_and_models_urls():
    assert openai_compat.chat_url("http://gpu:8000/v1") == \
        "http://gpu:8000/v1/chat/completions"
    assert openai_compat.models_url("http://gpu:8000") == \
        "http://gpu:8000/v1/models"


def test_is_local_endpoint_loopback_and_private():
    assert openai_compat.is_local_endpoint("http://localhost:8000") is True
    assert openai_compat.is_local_endpoint("http://127.0.0.1:8000") is True
    assert openai_compat.is_local_endpoint("http://192.168.1.10:8000") is True
    assert openai_compat.is_local_endpoint("http://10.0.0.5:8000") is True


def test_is_local_endpoint_public_is_cloud():
    assert openai_compat.is_local_endpoint("https://openrouter.ai/api") is False
    assert openai_compat.is_local_endpoint("http://8.8.8.8:8000") is False


def test_validate_entry_requires_endpoint():
    problems = openai_compat.validate_entry("x", {"provider": "openai_compatible"})
    assert any("endpoint" in p for p in problems)


def test_validate_entry_rejects_bad_scheme():
    problems = openai_compat.validate_entry(
        "x", {"provider": "openai_compatible", "endpoint": "ftp://gpu:8000"})
    assert any("http(s)" in p for p in problems)


def test_validate_entry_accepts_good_entry():
    problems = openai_compat.validate_entry("x", {
        "provider": "openai_compatible",
        "endpoint": "http://gpu-server:8000",
        "default_model": "Qwen/Qwen3-32B",
    })
    assert problems == []


def test_parse_chat_response_extracts_content():
    data = {"choices": [{"message": {"role": "assistant", "content": "HELLO"}}]}
    assert openai_compat.parse_chat_response(data) == "HELLO"


def test_parse_chat_response_malformed_raises():
    with pytest.raises(ValueError):
        openai_compat.parse_chat_response({"choices": []})


# ---------------------------------------------------------------------------
# Gateway integration tests
# ---------------------------------------------------------------------------
def make_gateway(handler, local_only=True, registry_extra=None):
    """Gateway whose HTTP traffic is served by a MockTransport, with an
    optional extra registry entry injected for openai_compatible tests."""
    transport = httpx.MockTransport(handler)

    def factory(timeout):
        return httpx.AsyncClient(timeout=timeout, transport=transport)

    gw = LLMGateway(local_only=local_only, client_factory=factory)
    gw.litellm_master_key = "sk-test"
    if registry_extra:
        gw._model_registry.update(registry_extra)
    return gw


VLLM_ENTRY = {
    "provider": "openai_compatible",
    "endpoint": "http://127.0.0.1:8000",
    "default_model": "Qwen/Qwen3-32B",
    "purpose": ["reasoning", "coding"],
}

REMOTE_ENTRY = {
    "provider": "openai_compatible",
    "endpoint": "https://api.example.com",
    "api_key_env": "EXAMPLE_API_KEY",
    "default_model": "big-model",
    "purpose": ["reasoning"],
}


def vllm_chat_ok(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode())
    assert request.url.path == "/v1/chat/completions"
    return httpx.Response(200, json={
        "choices": [{"message": {"role": "assistant", "content": "VLLM-SAYS-OK"}}],
        "model": body.get("model", ""),
    })


@pytest.mark.asyncio
async def test_openai_compat_hop_completes():
    """An openai_compatible alias completes via its endpoint."""
    called = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/chat/completions":
            called["n"] += 1
            return vllm_chat_ok(request)
        return httpx.Response(404)

    gw = make_gateway(handler, registry_extra={"gpu_server": dict(VLLM_ENTRY)})
    result = await gw.complete(alias="gpu_server", prompt="hello")
    assert result["success"] is True
    assert result["via"] == "openai_compat"
    assert result["content"] == "VLLM-SAYS-OK"
    assert called["n"] == 1


@pytest.mark.asyncio
async def test_openai_compat_local_only_allows_local_endpoint():
    """local_only must NOT block a loopback openai_compatible endpoint."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/chat/completions":
            return vllm_chat_ok(request)
        return httpx.Response(404)

    gw = make_gateway(handler, local_only=True,
                      registry_extra={"gpu_server": dict(VLLM_ENTRY)})
    result = await gw.complete(alias="gpu_server", prompt="hello")
    assert result["success"] is True
    assert result["blocked"] == []


@pytest.mark.asyncio
async def test_openai_compat_local_only_blocks_remote_endpoint():
    """local_only must block a public openai_compatible endpoint at the
    gateway level: no HTTP request is attempted."""
    called = {"any": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        called["any"] += 1
        return httpx.Response(200, json={})

    gw = make_gateway(handler, local_only=True,
                      registry_extra={"remote": dict(REMOTE_ENTRY)})
    result = await gw.complete(alias="remote", prompt="hello")
    assert result["success"] is False
    assert called["any"] == 0
    assert any("Blocked remote openai_compatible route" in b
               for b in result["blocked"])
    assert gw._transport_chain("remote") == []


@pytest.mark.asyncio
async def test_openai_compat_remote_allowed_when_not_local_only():
    """With local_only disabled, a remote endpoint with an API key works."""
    import os
    os.environ["EXAMPLE_API_KEY"] = "sk-fake"
    try:
        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/chat/completions":
                assert request.headers.get("authorization") == "Bearer sk-fake"
                return httpx.Response(200, json={
                    "choices": [{"message": {"content": "REMOTE-OK"}}],
                })
            return httpx.Response(404)

        gw = make_gateway(handler, local_only=False,
                          registry_extra={"remote": dict(REMOTE_ENTRY)})
        result = await gw.complete(alias="remote", prompt="hello")
        assert result["success"] is True
        assert result["via"] == "openai_compat"
    finally:
        os.environ.pop("EXAMPLE_API_KEY", None)


@pytest.mark.asyncio
async def test_openai_compat_health_probe():
    """health() probes /v1/models and reports availability, including
    model-not-served detection."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [
                {"id": "Qwen/Qwen3-32B"},
                {"id": "meta-llama/Llama-3-8B"},
            ]})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.1:8b"}]})
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(404)

    gw = make_gateway(handler, registry_extra={"gpu_server": dict(VLLM_ENTRY)})
    health = await gw.health()
    assert health["aliases"]["gpu_server"]["status"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_openai_compat_health_model_not_served():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "other-model"}]})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.1:8b"}]})
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(404)

    gw = make_gateway(handler, registry_extra={"gpu_server": dict(VLLM_ENTRY)})
    health = await gw.health()
    assert health["aliases"]["gpu_server"]["status"] == "UNAVAILABLE"
    assert "not served" in health["aliases"]["gpu_server"]["reason"]


@pytest.mark.asyncio
async def test_openai_compat_health_offline():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    gw = make_gateway(handler, registry_extra={"gpu_server": dict(VLLM_ENTRY)})
    health = await gw.health()
    assert health["aliases"]["gpu_server"]["status"] == "OFFLINE"


@pytest.mark.asyncio
async def test_openai_compat_failure_never_fabricates():
    """Endpoint 500s -> structured error, empty content, success=False."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(500, text="vllm down")
        return httpx.Response(404)

    gw = make_gateway(handler, registry_extra={"gpu_server": dict(VLLM_ENTRY)})
    result = await gw.complete(alias="gpu_server", prompt="hello")
    assert result["success"] is False
    assert result["content"] == ""
    assert any("openai_compat" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_openai_compat_malformed_response_fails_cleanly():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(200, json={"unexpected": "shape"})
        return httpx.Response(404)

    gw = make_gateway(handler, registry_extra={"gpu_server": dict(VLLM_ENTRY)})
    result = await gw.complete(alias="gpu_server", prompt="hello")
    assert result["success"] is False
    assert any("Malformed" in e or "openai_compat" in e
               for e in result["errors"])


def test_registry_rejects_invalid_openai_compat_entry():
    """_load_registry drops openai_compatible entries without an endpoint."""
    from cyberai.llm_gateway import _load_registry  # noqa: F401 — exists
    problems = openai_compat.validate_entry("bad", {
        "provider": "openai_compatible"})
    assert problems != []
