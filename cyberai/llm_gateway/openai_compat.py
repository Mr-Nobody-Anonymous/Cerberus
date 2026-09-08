"""
OpenAI-compatible provider support for the CERBERUS LLM Gateway.

One transport covers every endpoint that speaks the OpenAI HTTP dialect
(``POST {endpoint}/v1/chat/completions``):

    vLLM            — GPU inference server (single node or Ray Serve cluster)
    llama.cpp       — llama-server with --api-key / OpenAI middleware
    LM Studio       — local GUI server (default :1234)
    OpenRouter      — cloud aggregator of 100+ models
    LiteLLM proxy   — any provider behind the local gateway
    Gemini          — OpenAI-compat endpoint
    Remote clusters — any custom OpenAI-compatible server

Registry entries opt in with ``provider: openai_compatible`` plus:

    endpoint:     http://gpu-server:8000     (base URL, no /v1 suffix)
    api_key_env:  VLLM_API_KEY               (optional — local servers
                                              often run unauthenticated)
    default_model: Qwen/Qwen3-32B             (model name the server knows)

Privacy semantics: an endpoint on a private/loopback address is treated as
LOCAL (allowed under local_only); anything else is treated as CLOUD and is
blocked under PRIVACY_MODE=local_only, exactly like OpenAI/Anthropic.
"""

import ipaddress
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

# Registry keys this provider understands (beyond the standard ones).
REQUIRED_KEYS = ("endpoint",)
OPTIONAL_KEYS = ("api_key_env",)

# Endpoints on these networks are considered local (private infrastructure).
_LOCAL_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),    # IPv4 loopback
    ipaddress.ip_network("10.0.0.0/8"),     # private
    ipaddress.ip_network("172.16.0.0/12"),  # private
    ipaddress.ip_network("192.168.0.0/16"), # private
    ipaddress.ip_network("::1/128"),        # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),       # IPv6 unique-local
    ipaddress.ip_network("fe80::/10"),     # IPv6 link-local
)


def normalize_endpoint(endpoint: str) -> str:
    """
    Normalize a registry endpoint to a base URL.

    Accepts (all equivalent):
        http://gpu-server:8000
        http://gpu-server:8000/
        http://gpu-server:8000/v1
        http://gpu-server:8000/v1/

    Returns:
        Base URL WITHOUT trailing slash and WITHOUT /v1,
        e.g. ``http://gpu-server:8000``.
    """
    base = str(endpoint).strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    return base


def chat_url(endpoint: str) -> str:
    """Full chat-completions URL for an endpoint base."""
    return f"{normalize_endpoint(endpoint)}/v1/chat/completions"


def models_url(endpoint: str) -> str:
    """Models-list URL for an endpoint base (used by health probes)."""
    return f"{normalize_endpoint(endpoint)}/v1/models"


def is_local_endpoint(endpoint: str) -> bool:
    """
    Decide whether an endpoint is local/private infrastructure.

    Hostnames that resolve to private/loopback IPs, literal private IPs,
    ``localhost``, and ``*.local`` names are LOCAL. Everything else
    (public IPs, public DNS names) is CLOUD.

    DNS resolution is attempted but never fatal: on failure the endpoint is
    conservatively treated as CLOUD (blocked under local_only).
    """
    try:
        host = urlsplit(normalize_endpoint(endpoint)).hostname or ""
    except ValueError:
        return False
    if not host:
        return False
    if host == "localhost" or host.endswith(".local") or host == "host.docker.internal":
        return True
    # Literal IP?
    try:
        ip = ipaddress.ip_address(host)
        return any(ip in net for net in _LOCAL_NETWORKS)
    except ValueError:
        pass
    # Resolve hostname (best-effort; failure => treat as cloud)
    import socket

    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr.split("%")[0])
        except ValueError:
            continue
        if any(ip in net for net in _LOCAL_NETWORKS):
            return True
    return False


def resolve_api_key(entry: Dict[str, Any]) -> str:
    """
    Resolve the API key for a registry entry.

    Priority: ``api_key_env`` named env var -> entry's inline ``api_key``
    -> "" (many local servers run unauthenticated).
    """
    env_name = str(entry.get("api_key_env", "") or "")
    if env_name:
        return os.environ.get(env_name, "")
    return str(entry.get("api_key", "") or "")


def validate_entry(alias: str, entry: Dict[str, Any]) -> List[str]:
    """
    Validate an openai_compatible registry entry.

    Returns a list of problems (empty list = valid).
    """
    problems: List[str] = []
    endpoint = str(entry.get("endpoint", "") or "").strip()
    if not endpoint:
        problems.append(f"{alias}: openai_compatible requires 'endpoint'")
    else:
        parsed = urlsplit(endpoint)
        if parsed.scheme not in ("http", "https"):
            problems.append(
                f"{alias}: endpoint must be http(s) URL, got {endpoint!r}")
    if entry.get("api_key_env") and not isinstance(entry.get("api_key_env"), str):
        problems.append(f"{alias}: api_key_env must be an env var name")
    return problems


def build_chat_payload(
    model_name: str,
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    """Build the OpenAI-dialect chat-completions request body."""
    return {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }


def parse_chat_response(data: Dict[str, Any]) -> str:
    """Extract assistant content from an OpenAI-dialect response."""
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ValueError(f"Malformed OpenAI-compatible response: {e}") from e


def headers_for(entry: Dict[str, Any], api_key: str) -> Dict[str, str]:
    """Build request headers (Authorization only when a key exists)."""
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def describe(alias: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    """Human/JSON-friendly summary of an openai_compatible entry."""
    endpoint = normalize_endpoint(str(entry.get("endpoint", "")))
    return {
        "alias": alias,
        "provider": "openai_compatible",
        "endpoint": endpoint,
        "model": entry.get("default_model", ""),
        "local": is_local_endpoint(endpoint),
        "authenticated": bool(resolve_api_key(entry)),
    }


__all__ = [
    "normalize_endpoint",
    "chat_url",
    "models_url",
    "is_local_endpoint",
    "resolve_api_key",
    "validate_entry",
    "build_chat_payload",
    "parse_chat_response",
    "headers_for",
    "describe",
]
