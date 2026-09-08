"""
LLM Gateway for CERBERUS.

Provides a unified async interface for all LLM calls with a real
transport-based fallback chain (per the README):

    1. LiteLLM proxy      (OpenAI-compatible /v1/chat/completions,
                           authenticated with LITELLM_MASTER_KEY)
    2. Direct Ollama      (/api/chat on the local model service)
    3. Direct provider    (OpenAI / Anthropic HTTP APIs) — only when
                           PRIVACY_MODE != local_only and an API key exists

Each hop has its own timeout and produces a structured error/log entry on
failure — failures are never silently swallowed. ``local_only`` privacy mode
blocks cloud hops *at the gateway level* (not just config) and logs every
blocked attempt.

Prompts live with the agents; this module never hardcodes agent prompts.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from cyberai.config import config, load_required_yaml
from cyberai.llm_gateway import openai_compat

logger = logging.getLogger(__name__)

# Workspace-relative location of the model registry (package data).
MODEL_REGISTRY_PATH = "cyberai/llm_gateway/models/models.yaml"

# Logical roles -> model alias mapping (configurable).
ROLE_MODEL_MAP = {
    "planner": "local_reasoner",
    "reasoner": "local_reasoner",
    "researcher": "research_model",
    "coder": "local_coder",
    "analyst": "local_reasoner",
    "summarizer": "local_fast",
    "verifier": "local_reasoner",
    "local_sensitive": "local_coder",
    "fast": "local_fast",
    "default": "local_fast",
}

# Per-hop default timeouts (seconds). Each hop is timed independently.
DEFAULT_HOP_TIMEOUTS = {
    "litellm": 60,
    "ollama": 300,
    "provider": 60,
    "health": 5,
}


# Fallback registry used only if models.yaml cannot be loaded (degrades
# loudly with an error log; never silently).
DEFAULT_MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "local_reasoner": {
        "provider": "ollama",
        "default_model": "llama3.1:8b",
        "purpose": ["reasoning", "planning", "verification"],
    },
    "local_coder": {
        "provider": "ollama",
        "default_model": "codellama:7b",
        "purpose": ["code_analysis", "code_generation", "exploit_development"],
    },
    "local_fast": {
        "provider": "ollama",
        "default_model": "llama3.2:3b",
        "purpose": ["classification", "summarization", "tool_selection"],
    },
    "research_model": {
        "provider": "ollama",
        "default_model": "qwen2.5:7b",
        "purpose": ["web_research", "vulnerability_research", "cve_analysis"],
    },
    "embeddings": {
        "provider": "ollama",
        "default_model": "nomic-embed-text",
        "purpose": ["semantic_memory_retrieval"],
    },
    "cloud_reasoner": {
        "provider": "openai",
        "default_model": "gpt-4o",
        "purpose": ["complex_reasoning", "advanced_planning"],
    },
    "cloud_fast": {
        "provider": "anthropic",
        "default_model": "claude-3-5-haiku-latest",
        "purpose": ["fast_analysis", "classification"],
    },
}


def _load_registry() -> Dict[str, Dict[str, Any]]:
    """Load the model registry from models.yaml, failing fast with context."""
    try:
        data = load_required_yaml(MODEL_REGISTRY_PATH, section="models")
        registry: Dict[str, Dict[str, Any]] = {}
        for alias, entry in data.items():
            if not isinstance(entry, dict) or "provider" not in entry:
                logger.warning("Skipping invalid model registry entry %r", alias)
                continue
            if entry.get("provider") == "openai_compatible":
                problems = openai_compat.validate_entry(alias, entry)
                if problems:
                    for p in problems:
                        logger.error("Registry entry rejected: %s", p)
                    continue
            registry[alias] = dict(entry)
        if not registry:
            raise ValueError("model registry is empty")
        return registry
    except Exception as e:  # noqa: BLE001 — degrade loudly, never silently
        logger.error("Failed to load model registry from %s: %s — using defaults",
                     MODEL_REGISTRY_PATH, e)
        return {k: dict(v) for k, v in DEFAULT_MODEL_REGISTRY.items()}


class LLMGateway:
    """
    Unified LLM gateway with a real transport fallback chain, health
    checks, per-alias availability and local-only privacy enforcement.
    """

    def __init__(
        self,
        config_path: Optional[Any] = None,  # kept for API compatibility
        local_only: Optional[bool] = None,
        client_factory=None,
    ):
        # Privacy mode: explicit arg wins, else central config (env/.env aware)
        self.local_only = (
            local_only if local_only is not None else config.is_local_only()
        )

        # Endpoints from the central config loader
        self.ollama_host = str(
            config.get("llm", "ollama_host", "http://localhost:11434")
        ).rstrip("/")
        litellm_host = str(
            config.get("llm", "litellm_host", "http://localhost")
        ).strip().rstrip("/")
        if litellm_host and "://" not in litellm_host:
            litellm_host = f"http://{litellm_host}"  # scheme-less host in .env
        self.litellm_port = int(config.get("llm", "litellm_port", 4000))
        self.litellm_base = f"{litellm_host}:{self.litellm_port}"
        self.litellm_master_key = config.get("llm", "litellm_master_key", "") or ""

        # Per-hop timeouts (independently configurable)
        self.hop_timeouts = dict(DEFAULT_HOP_TIMEOUTS)
        for hop in ("litellm", "ollama", "provider", "health"):
            self.hop_timeouts[hop] = int(
                config.get("llm", f"{hop}_timeout", DEFAULT_HOP_TIMEOUTS[hop])
            )

        # Injectable httpx.AsyncClient factory (for tests)
        self._client_factory = client_factory or self._default_client_factory

        # Model registry + cached health state
        self._model_registry: Dict[str, Dict[str, Any]] = _load_registry()
        self._apply_env_model_overrides()
        self._ollama_available: Optional[bool] = None
        self._ollama_models: List[str] = []
        self._litellm_available: Optional[bool] = None
        self._performance: Dict[str, List[Dict[str, Any]]] = {}

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------
    @staticmethod
    def _default_client_factory(timeout: float):
        import httpx

        return httpx.AsyncClient(timeout=timeout)

    def _apply_env_model_overrides(self) -> None:
        """Allow env vars like LOCAL_REASONER_MODEL to override concrete names."""
        for alias, entry in self._model_registry.items():
            env_val = os.environ.get(f"{alias.upper()}_MODEL")
            if env_val:
                entry["default_model"] = env_val
            else:
                cfg_val = config.get("llm", f"{alias.lower()}_model", None)
                if cfg_val:
                    entry["default_model"] = str(cfg_val)


    # ------------------------------------------------------------------
    # Health checks (real network probes, not just config presence)
    # ------------------------------------------------------------------
    async def check_ollama(self) -> Dict[str, Any]:
        """Ping Ollama's /api/tags and cache the installed model list."""
        url = f"{self.ollama_host}/api/tags"
        try:
            async with self._client_factory(self.hop_timeouts["health"]) as client:
                resp = await client.get(url)
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                self._ollama_available = True
                self._ollama_models = models
                return {"status": "AVAILABLE", "models": models,
                        "host": self.ollama_host}
            self._ollama_available = False
            return {"status": "ERROR",
                    "message": f"Ollama returned status {resp.status_code}"}
        except Exception as e:  # noqa: BLE001
            self._ollama_available = False
            logger.error("Ollama health probe failed: %s", e)
            return {"status": "OFFLINE", "message": str(e), "host": self.ollama_host}

    async def check_litellm(self) -> Dict[str, Any]:
        """Ping the LiteLLM proxy /health endpoint."""
        if not self.litellm_master_key:
            self._litellm_available = False
            return {"status": "NOT_CONFIGURED",
                    "message": "LITELLM_MASTER_KEY not set",
                    "base": self.litellm_base}
        url = f"{self.litellm_base}/health"
        try:
            async with self._client_factory(self.hop_timeouts["health"]) as client:
                resp = await client.get(url)
            self._litellm_available = resp.status_code == 200
            return {"status": "AVAILABLE" if resp.status_code == 200 else "ERROR",
                    "base": self.litellm_base}
        except Exception as e:  # noqa: BLE001
            self._litellm_available = False
            logger.error("LiteLLM health probe failed: %s", e)
            return {"status": "OFFLINE", "message": str(e), "base": self.litellm_base}


    async def health(self) -> Dict[str, Any]:
        """
        Probe every transport and report per-alias availability.

        Returns dict with: ollama, litellm, aliases (per-alias status),
        local_only.
        """
        ollama = await self.check_ollama()
        litellm = await self.check_litellm()

        aliases: Dict[str, Dict[str, Any]] = {}
        for alias, entry in self._model_registry.items():
            provider = entry.get("provider", "")
            model = entry.get("default_model", "")
            if provider == "ollama":
                if ollama["status"] != "AVAILABLE":
                    aliases[alias] = {
                        "status": "OFFLINE", "provider": provider,
                        "model": model,
                        "reason": f"Ollama not reachable at {self.ollama_host}",
                    }
                elif model and model not in self._ollama_models:
                    aliases[alias] = {
                        "status": "UNAVAILABLE", "provider": provider,
                        "model": model,
                        "reason": f"Model '{model}' not pulled "
                                  f"(ollama pull {model})",
                    }
                else:
                    aliases[alias] = {"status": "AVAILABLE", "provider": provider,
                                      "model": model, "reason": "ok"}
            elif provider == "openai_compatible":
                endpoint = str(entry.get("endpoint", ""))
                is_local = openai_compat.is_local_endpoint(endpoint)
                if self.local_only and not is_local:
                    aliases[alias] = {
                        "status": "BLOCKED_LOCAL_ONLY", "provider": provider,
                        "model": model,
                        "reason": "PRIVACY_MODE=local_only blocks remote "
                                  "endpoints",
                    }
                else:
                    probe = await self._probe_openai_compat(alias, entry)
                    aliases[alias] = probe
            else:  # cloud providers
                key = os.environ.get(f"{provider.upper()}_API_KEY", "")
                if self.local_only:
                    aliases[alias] = {
                        "status": "BLOCKED_LOCAL_ONLY", "provider": provider,
                        "model": model,
                        "reason": "PRIVACY_MODE=local_only blocks cloud routes",
                    }
                elif not key:
                    aliases[alias] = {
                        "status": "NOT_CONFIGURED", "provider": provider,
                        "model": model,
                        "reason": f"No {provider.upper()}_API_KEY",
                    }
                else:
                    aliases[alias] = {"status": "AVAILABLE", "provider": provider,
                                      "model": model, "reason": "API key present"}

        return {"ollama": ollama, "litellm": litellm, "aliases": aliases,
                "local_only": self.local_only}

    async def health_check(self) -> Dict[str, Any]:
        """Alias of :meth:`health` (kept for backward compatibility)."""
        return await self.health()

    async def _probe_openai_compat(
        self, alias: str, entry: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Probe an OpenAI-compatible endpoint's /v1/models for health()."""
        endpoint = str(entry.get("endpoint", ""))
        url = openai_compat.models_url(endpoint)
        api_key = openai_compat.resolve_api_key(entry)
        try:
            async with self._client_factory(self.hop_timeouts["health"]) as client:
                resp = await client.get(url, headers=openai_compat.headers_for(entry, api_key))
            if resp.status_code == 200:
                model = entry.get("default_model", "")
                served = []
                try:
                    served = [m.get("id", "") for m in resp.json().get("data", [])]
                except Exception:  # noqa: BLE001 — models list is advisory
                    pass
                if model and served and model not in served:
                    return {
                        "status": "UNAVAILABLE", "provider": "openai_compatible",
                        "model": model,
                        "reason": f"Model '{model}' not served by {endpoint}",
                    }
                return {
                    "status": "AVAILABLE", "provider": "openai_compatible",
                    "model": model, "reason": f"endpoint {endpoint} reachable",
                }
            return {
                "status": "ERROR", "provider": "openai_compatible",
                "model": entry.get("default_model", ""),
                "reason": f"endpoint returned {resp.status_code}",
            }
        except Exception as e:  # noqa: BLE001
            return {
                "status": "OFFLINE", "provider": "openai_compatible",
                "model": entry.get("default_model", ""),
                "reason": f"{type(e).__name__}: {e}",
            }


    # ------------------------------------------------------------------
    # Model resolution
    # ------------------------------------------------------------------
    def resolve_model(self, alias: str) -> Optional[Dict[str, Any]]:
        """Resolve a model alias to its registry entry."""
        if alias in self._model_registry:
            return self._model_registry[alias]
        for _name, info in self._model_registry.items():
            if info.get("default_model", "") == alias:
                return info
        return None

    def get_model_for_role(self, role: str) -> str:
        """Get the model alias for a logical role."""
        return ROLE_MODEL_MAP.get(role, ROLE_MODEL_MAP["default"])

    def is_model_available(self, alias: str) -> bool:
        """Check if a model alias is currently usable (cached health state)."""
        entry = self.resolve_model(alias)
        if not entry:
            return False
        provider = entry.get("provider", "")
        if provider == "ollama":
            if self._ollama_available is False:
                return False
            model_name = entry.get("default_model", "")
            if self._ollama_models and model_name not in self._ollama_models:
                return False
            return True
        if provider == "openai_compatible":
            endpoint = str(entry.get("endpoint", ""))
            if self.local_only and not openai_compat.is_local_endpoint(endpoint):
                return False
            return True  # reachability is checked per-call via the chain
        if provider in ("openai", "anthropic"):
            if self.local_only:
                return False
            return bool(os.environ.get(f"{provider.upper()}_API_KEY", ""))
        return False


    # ------------------------------------------------------------------
    # Transport hops
    # ------------------------------------------------------------------
    async def _call_litellm(
        self, alias: str, messages: List[Dict[str, str]],
        max_tokens: int, temperature: float,
    ) -> str:
        """Hop 1 — OpenAI-compatible call through the LiteLLM proxy."""
        if not self.litellm_master_key:
            raise RuntimeError("LITELLM_MASTER_KEY not configured")

        url = f"{self.litellm_base}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.litellm_master_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": alias,  # LiteLLM maps alias → concrete model server-side
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        async with self._client_factory(self.hop_timeouts["litellm"]) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _call_ollama(
        self, model_name: str, messages: List[Dict[str, str]],
        max_tokens: int, temperature: float,
    ) -> str:
        """Hop 2 — direct call to the local Ollama service (/api/chat)."""
        url = f"{self.ollama_host}/api/chat"
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }
        async with self._client_factory(self.hop_timeouts["ollama"]) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")


    async def _call_provider(
        self, provider: str, model_name: str, messages: List[Dict[str, str]],
        max_tokens: int, temperature: float,
    ) -> str:
        """Hop 3 — direct call to a cloud provider API (OpenAI/Anthropic)."""
        if provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY", "")
            url = "https://api.openai.com/v1/chat/completions"
        elif provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            url = "https://api.anthropic.com/v1/messages"
        else:
            raise ValueError(f"Unsupported cloud provider: {provider}")

        if not api_key:
            raise RuntimeError(f"No API key configured for {provider}")

        if provider == "openai":
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        else:  # anthropic
            system = ""
            user_messages = []
            for m in messages:
                if m.get("role") == "system":
                    system = m.get("content", "")
                else:
                    user_messages.append(m)
            payload = {
                "model": model_name,
                "messages": user_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system:
                payload["system"] = system
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }

        async with self._client_factory(self.hop_timeouts["provider"]) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if provider == "openai":
                return data["choices"][0]["message"]["content"]
            return data["content"][0]["text"]


    async def _call_openai_compat(
        self, entry: Dict[str, Any], messages: List[Dict[str, str]],
        max_tokens: int, temperature: float,
    ) -> str:
        """Hop — call any OpenAI-compatible endpoint (vLLM, llama.cpp,
        LM Studio, OpenRouter, remote GPU servers, ...)."""
        endpoint = str(entry.get("endpoint", ""))
        url = openai_compat.chat_url(endpoint)
        api_key = openai_compat.resolve_api_key(entry)
        payload = openai_compat.build_chat_payload(
            entry.get("default_model", ""), messages, max_tokens, temperature)
        async with self._client_factory(self.hop_timeouts["provider"]) as client:
            resp = await client.post(
                url, headers=openai_compat.headers_for(entry, api_key),
                json=payload)
            resp.raise_for_status()
            return openai_compat.parse_chat_response(resp.json())


    # ------------------------------------------------------------------
    # Completion entry point with transport fallback chain
    # ------------------------------------------------------------------
    def _transport_chain(self, alias: str) -> List[str]:
        """
        Ordered transport chain for an alias:

            ollama alias     -> ["litellm", "ollama"]
            openai/anthropic -> ["litellm", "provider"]

        Cloud hops are removed entirely when local_only is active.
        """
        entry = self.resolve_model(alias)
        provider = (entry or {}).get("provider", "")

        if provider == "ollama":
            return ["litellm", "ollama"]
        if provider == "openai_compatible":
            endpoint = str((entry or {}).get("endpoint", ""))
            if self.local_only and not openai_compat.is_local_endpoint(endpoint):
                return []  # remote endpoint blocked at gateway level
            return ["openai_compat"]
        if provider in ("openai", "anthropic"):
            if self.local_only:
                return []  # cloud blocked at gateway level
            return ["litellm", "provider"]
        return []

    async def complete(
        self,
        role: str = "reasoner",
        prompt: str = "",
        messages: Optional[List[Dict[str, str]]] = None,
        alias: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate a completion, walking the transport fallback chain:
        LiteLLM proxy -> direct Ollama -> direct provider API.

        Every hop has its own timeout; every failure produces a structured
        error entry (returned in ``errors`` and logged). Cloud hops are
        blocked and logged when ``local_only`` privacy mode is active.
        """
        start = time.time()
        if max_tokens is None:
            max_tokens = int(config.get("llm", "max_tokens", 2048))
        if temperature is None:
            temperature = float(config.get("llm", "temperature", 0.7))

        resolved_alias = alias or self.get_model_for_role(role)
        entry = self.resolve_model(resolved_alias)
        if not entry:
            return self._failure(resolved_alias, start,
                                 [f"Unknown model alias: {resolved_alias}"], [])

        if not messages:
            messages = [{"role": "user", "content": prompt}]

        provider = entry.get("provider", "")
        concrete_model = entry.get("default_model", "")
        errors: List[str] = []
        blocked: List[str] = []


        # local_only enforcement — at the gateway, before any network attempt
        if self.local_only and provider != "ollama":
            if provider == "openai_compatible":
                endpoint = str(entry.get("endpoint", ""))
                if not openai_compat.is_local_endpoint(endpoint):
                    msg = (f"Blocked remote openai_compatible route to "
                           f"{concrete_model} at {endpoint} "
                           "(PRIVACY_MODE=local_only)")
                    blocked.append(msg)
                    logger.warning("LOCAL_ONLY BLOCK: %s", msg)
            else:
                msg = (f"Blocked cloud route to {provider}/{concrete_model} "
                       "(PRIVACY_MODE=local_only)")
                blocked.append(msg)
                logger.warning("LOCAL_ONLY BLOCK: %s", msg)

        for hop in self._transport_chain(resolved_alias):
            hop_label = f"{hop}:{resolved_alias}"
            try:
                if hop == "litellm":
                    content = await self._call_litellm(
                        resolved_alias, messages, max_tokens, temperature)
                elif hop == "ollama":
                    content = await self._call_ollama(
                        concrete_model, messages, max_tokens, temperature)
                elif hop == "provider":
                    content = await self._call_provider(
                        provider, concrete_model, messages, max_tokens,
                        temperature)
                elif hop == "openai_compat":
                    content = await self._call_openai_compat(
                        entry, messages, max_tokens, temperature)
                else:
                    errors.append(f"{hop_label}: unknown transport")
                    continue

                latency = time.time() - start
                self._record_performance(resolved_alias, role, latency,
                                         success=True)
                logger.info(
                    "LLM complete via %s (alias=%s provider=%s latency=%.2fs)",
                    hop, resolved_alias, provider, latency)
                return {
                    "content": content,
                    "model": resolved_alias,
                    "concrete_model": concrete_model,
                    "provider": provider,
                    "via": hop,
                    "latency": latency,
                    "success": True,
                    "errors": errors,
                    "blocked": blocked,
                }
            except Exception as e:  # noqa: BLE001 — structured, logged fallback
                msg = f"{hop_label}: {type(e).__name__}: {e}"
                errors.append(msg)
                logger.error("LLM hop failed (%s)", msg)

        return self._failure(resolved_alias, start, errors, blocked)


    def _failure(
        self, alias: str, start: float,
        errors: List[str], blocked: List[str],
    ) -> Dict[str, Any]:
        """Uniform failure result — never fabricate content."""
        self._record_performance(alias, "complete", time.time() - start,
                                 success=False)
        return {
            "content": "",
            "model": alias,
            "concrete_model": "",
            "provider": "none",
            "via": "none",
            "latency": time.time() - start,
            "success": False,
            "errors": errors,
            "blocked": blocked,
            "message": "All transports in the fallback chain failed. "
                       "Never fabricating a response.",
        }

    async def generate(
        self,
        role: str = "reasoner",
        messages: Optional[List[Dict[str, str]]] = None,
        prompt: str = "",
        task_context: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Alias of :meth:`complete` (kept for backward compatibility)."""
        return await self.complete(
            role=role, prompt=prompt, messages=messages,
            max_tokens=max_tokens, temperature=temperature,
        )

    # ------------------------------------------------------------------
    # Performance tracking
    # ------------------------------------------------------------------
    def _record_performance(self, model: str, role: str, latency: float,
                            success: bool) -> None:
        """Record model performance for meta-learning."""
        key = f"{model}:{role}"
        self._performance.setdefault(key, []).append({
            "latency": latency,
            "success": success,
            "timestamp": time.time(),
        })
        if len(self._performance[key]) > 100:
            self._performance[key] = self._performance[key][-100:]

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get model performance statistics for meta-learning."""
        stats: Dict[str, Any] = {}
        for key, records in self._performance.items():
            if not records:
                continue
            successes = sum(1 for r in records if r["success"])
            stats[key] = {
                "calls": len(records),
                "success_rate": successes / len(records),
                "avg_latency": sum(r["latency"] for r in records)
                               / len(records),
            }
        return stats

    # ------------------------------------------------------------------
    # Registry access
    # ------------------------------------------------------------------
    async def discover_models(self) -> List[Dict[str, Any]]:
        """Discover models actually installed on the local Ollama service."""
        health = await self.check_ollama()
        if health.get("status") != "AVAILABLE":
            return []
        return [{"name": m} for m in self._ollama_models]

    def list_registry(self) -> List[Dict[str, Any]]:
        """List all models in the registry with concrete names."""
        out = []
        for alias, entry in self._model_registry.items():
            provider = entry.get("provider", "")
            out.append({
                "alias": alias,
                "provider": provider,
                "model": entry.get("default_model", ""),
                "status": entry.get("status", ""),
                "purpose": entry.get("purpose", []),
                "capabilities": entry.get("capabilities", {}),
                "locality": "LOCAL" if provider in ("ollama",) else "CLOUD",
            })
        return out


__all__ = ["LLMGateway", "ROLE_MODEL_MAP", "DEFAULT_MODEL_REGISTRY"]
