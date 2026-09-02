"""
LLM Gateway for the Cyber AI platform.

Provides a unified interface for LLM calls with:
- Logical role routing (planner, reasoner, researcher, coder, etc.)
- Automatic model selection based on task characteristics
- Graceful fallback chains
- Health checks for Ollama and LiteLLM
- Local-only privacy enforcement
- Model performance tracking
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from cyberai.config import WORKSPACE_ROOT

# Workspace root resolved by the central config loader
from cyberai.config import config

# Environment (from central config: defaults < .env < process env)
OLLAMA_HOST = config.get("llm", "ollama_host", "http://localhost:11434")
LITELLM_PORT = str(config.get("llm", "litellm_port", 4000))
LITELLM_MASTER_KEY = config.get("llm", "litellm_master_key", "")

# Logical roles -> model alias mapping (configurable)
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
}

# Model registry (defaults, overridden by models.yaml)
DEFAULT_MODEL_REGISTRY = {
    "local_reasoner": {
        "provider": "ollama",
        "default_model": "llama3.1:8b",
        "purpose": ["reasoning", "planning", "verification"],
        "status": "REQUIRES_MODEL_DOWNLOAD",
    },
    "local_coder": {
        "provider": "ollama",
        "default_model": "codellama:7b",
        "purpose": ["code_analysis", "code_generation", "exploit_development"],
        "status": "REQUIRES_MODEL_DOWNLOAD",
    },
    "local_fast": {
        "provider": "ollama",
        "default_model": "llama3.2:3b",
        "purpose": ["classification", "summarization", "tool_selection"],
        "status": "REQUIRES_MODEL_DOWNLOAD",
    },
    "research_model": {
        "provider": "ollama",
        "default_model": "qwen2.5:7b",
        "purpose": ["web_research", "vulnerability_research", "cve_analysis"],
        "status": "REQUIRES_MODEL_DOWNLOAD",
    },
    "embeddings": {
        "provider": "ollama",
        "default_model": "nomic-embed-text",
        "purpose": ["semantic_memory_retrieval"],
        "status": "REQUIRES_MODEL_DOWNLOAD",
    },
    "cloud_reasoner": {
        "provider": "openai",
        "default_model": "gpt-4o",
        "purpose": ["complex_reasoning", "advanced_planning"],
        "status": "DISABLED_NO_API_KEY",
    },
    "cloud_fast": {
        "provider": "anthropic",
        "default_model": "claude-3-5-haiku-latest",
        "purpose": ["fast_analysis", "classification"],
        "status": "DISABLED_NO_API_KEY",
    },
}


class LLMGateway:
    """Unified LLM gateway with routing, fallback, and health checks."""

    def __init__(self, config_path: Optional[Path] = None, local_only: bool = True):
        self.config_path = config_path or WORKSPACE_ROOT / "cyberai" / "llm-gateway" / "models" / "models.yaml"
        self.local_only = local_only
        self._model_registry: Dict[str, Dict[str, Any]] = dict(DEFAULT_MODEL_REGISTRY)
        self._load_registry()
        self._ollama_available: Optional[bool] = None
        self._ollama_models: List[str] = []
        self._litellm_available: Optional[bool] = None
        self._performance: Dict[str, List[Dict[str, Any]]] = {}

    def _load_registry(self) -> None:
        """Load model registry from YAML if present."""
        if self.config_path.exists():
            try:
                import yaml
                with open(self.config_path, "r") as f:
                    data = yaml.safe_load(f) or {}
                models = data.get("models", {})
                if models:
                    self._model_registry.update(models)
                logger.info(f"Loaded {len(models)} model aliases from registry")
            except Exception as e:
                logger.warning(f"Failed to load model registry: {e}")

    # --- Health checks ---------------------------------------------------
    async def check_ollama(self) -> Dict[str, Any]:
        """Check if Ollama is running and discover models."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{OLLAMA_HOST}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    self._ollama_available = True
                    self._ollama_models = models
                    return {
                        "status": "AVAILABLE",
                        "models": models,
                        "host": OLLAMA_HOST,
                    }
                self._ollama_available = False
                return {"status": "ERROR", "message": f"Ollama returned status {resp.status_code}"}
        except Exception as e:
            self._ollama_available = False
            return {"status": "OFFLINE", "message": str(e), "host": OLLAMA_HOST}

    async def check_litellm(self) -> Dict[str, Any]:
        """Check if LiteLLM proxy is running."""
        if not LITELLM_MASTER_KEY:
            self._litellm_available = False
            return {"status": "NOT_CONFIGURED", "message": "LITELLM_MASTER_KEY not set"}
        try:
            import httpx
            url = f"http://localhost:{LITELLM_PORT}/health"
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(url)
                self._litellm_available = resp.status_code == 200
                return {
                    "status": "AVAILABLE" if resp.status_code == 200 else "ERROR",
                    "port": LITELLM_PORT,
                }
        except Exception as e:
            self._litellm_available = False
            return {"status": "OFFLINE", "message": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Full health check for all LLM providers."""
        ollama = await self.check_ollama()
        litellm = await self.check_litellm()
        return {
            "ollama": ollama,
            "litellm": litellm,
            "local_only": self.local_only,
        }

    # --- Model resolution ------------------------------------------------
    def resolve_model(self, alias: str) -> Optional[Dict[str, Any]]:
        """Resolve a model alias to its configuration."""
        if alias in self._model_registry:
            return self._model_registry[alias]
        for name, info in self._model_registry.items():
            if info.get("default_model", "") == alias:
                return info
        return None

    def get_model_for_role(self, role: str) -> str:
        """Get the model alias for a logical role."""
        return ROLE_MODEL_MAP.get(role, ROLE_MODEL_MAP.get("fast", "local_fast"))

    def is_model_available(self, alias: str) -> bool:
        """Check if a model alias is currently available."""
        config = self.resolve_model(alias)
        if not config:
            return False
        provider = config.get("provider", "")
        status = config.get("status", "")
        if status in ("DISABLED_NO_API_KEY", "INCOMPATIBLE"):
            return False
        if provider == "ollama":
            if self._ollama_available is False:
                return False
            model_name = config.get("default_model", "")
            if self._ollama_models and model_name not in self._ollama_models:
                return False
            return True
        if provider in ("openai", "anthropic"):
            if self.local_only:
                return False
            key = os.environ.get(f"{provider.upper()}_API_KEY", "")
            return bool(key)
        return False

    # --- Generation ------------------------------------------------------
    async def generate(
        self,
        role: str = "reasoner",
        messages: Optional[List[Dict[str, str]]] = None,
        prompt: str = "",
        task_context: Optional[Dict[str, Any]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate a completion using the router-decided model.

        Args:
            role: Logical role (planner, reasoner, researcher, coder, etc.)
            messages: Chat messages (if provided, prompt is ignored)
            prompt: Plain prompt text
            task_context: Task metadata for routing decisions
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            Dict with 'content', 'model', 'provider', 'latency', 'success'
        """
        start = time.time()
        alias = self.get_model_for_role(role)

        # Build messages
        if not messages:
            messages = [{"role": "user", "content": prompt}]

        # Try fallback chain
        chain = self._build_fallback_chain(alias, task_context or {})
        errors = []

        for candidate in chain:
            config = self.resolve_model(candidate)
            if not config:
                errors.append(f"Unknown model alias: {candidate}")
                continue

            provider = config.get("provider", "")
            status = config.get("status", "")

            # Skip disabled models
            if status in ("DISABLED_NO_API_KEY", "INCOMPATIBLE"):
                errors.append(f"Model {candidate} disabled ({status})")
                continue

            # Enforce local-only
            if self.local_only and provider not in ("ollama",):
                errors.append(f"Model {candidate} is cloud ({provider}) but local_only mode is active")
                continue

            try:
                if provider == "ollama":
                    content = await self._call_ollama(
                        config.get("default_model", ""), messages, max_tokens, temperature
                    )
                elif provider in ("openai", "anthropic"):
                    content = await self._call_cloud(
                        provider, config.get("default_model", ""), messages, max_tokens, temperature
                    )
                else:
                    errors.append(f"Unknown provider: {provider}")
                    continue

                latency = time.time() - start
                self._record_performance(alias, role, latency, success=True)
                return {
                    "content": content,
                    "model": candidate,
                    "provider": provider,
                    "latency": latency,
                    "success": True,
                    "fallback_used": candidate != alias,
                }
            except Exception as e:
                errors.append(f"{candidate}: {e}")
                logger.warning(f"Model {candidate} failed: {e}")

        # All models failed
        self._record_performance(alias, role, time.time() - start, success=False)
        return {
            "content": "",
            "model": alias,
            "provider": "none",
            "latency": time.time() - start,
            "success": False,
            "errors": errors,
            "message": "All models in fallback chain failed. Never fabricating a response.",
        }

    def _build_fallback_chain(self, alias: str, task_context: Dict[str, Any]) -> List[str]:
        """Build a fallback chain for a model alias."""
        chain = [alias]
        config = self.resolve_model(alias)
        if not config:
            return chain

        provider = config.get("provider", "")
        purpose = config.get("purpose", [])

        # Add local alternatives
        if provider == "ollama":
            # Try other local models
            for other_alias, other_config in self._model_registry.items():
                if other_alias != alias and other_config.get("provider") == "ollama":
                    if other_config.get("status") != "DISABLED_NO_API_KEY":
                        chain.append(other_alias)
                        if len(chain) >= 4:
                            break
        else:
            # Cloud model -> local fallback
            chain.append("local_reasoner")
            chain.append("local_fast")

        return chain

    async def _call_ollama(
        self, model_name: str, messages: List[Dict[str, str]], max_tokens: int, temperature: float
    ) -> str:
        """Call Ollama API."""
        import httpx

        # Convert chat messages to prompt
        prompt = self._messages_to_prompt(messages)

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    async def _call_cloud(
        self, provider: str, model_name: str, messages: List[Dict[str, str]],
        max_tokens: int, temperature: float
    ) -> str:
        """Call a cloud provider API."""
        import httpx

        if provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY", "")
            url = "https://api.openai.com/v1/chat/completions"
        elif provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            url = "https://api.anthropic.com/v1/messages"
        else:
            raise ValueError(f"Unsupported cloud provider: {provider}")

        if not api_key:
            raise ValueError(f"No API key for {provider}")

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        if provider == "openai":
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
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

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            if provider == "openai":
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
            else:
                return data.get("content", [{}])[0].get("text", "")

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert chat messages to a plain prompt for Ollama."""
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        return "\n\n".join(parts)

    # --- Performance tracking --------------------------------------------
    def _record_performance(self, model: str, role: str, latency: float, success: bool) -> None:
        """Record model performance for meta-learning."""
        key = f"{model}:{role}"
        if key not in self._performance:
            self._performance[key] = []
        self._performance[key].append({
            "latency": latency,
            "success": success,
            "timestamp": time.time(),
        })
        # Keep only last 100
        if len(self._performance[key]) > 100:
            self._performance[key] = self._performance[key][-100:]

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get model performance statistics for meta-learning."""
        stats = {}
        for key, records in self._performance.items():
            if not records:
                continue
            successes = sum(1 for r in records if r["success"])
            stats[key] = {
                "calls": len(records),
                "success_rate": successes / len(records),
                "avg_latency": sum(r["latency"] for r in records) / len(records),
            }
        return stats

    # --- Model discovery --------------------------------------------------
    async def discover_models(self) -> List[Dict[str, Any]]:
        """Discover available models from Ollama."""
        health = await self.check_ollama()
        if health["status"] != "AVAILABLE":
            return []
        return [{"name": m} for m in self._ollama_models]

    def list_registry(self) -> List[Dict[str, Any]]:
        """List all models in the registry."""
        return [
            {
                "alias": alias,
                "provider": config.get("provider", ""),
                "model": config.get("default_model", ""),
                "status": config.get("status", ""),
                "purpose": config.get("purpose", []),
            }
            for alias, config in self._model_registry.items()
        ]