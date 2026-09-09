"""
Model Router for the Cyber AI Orchestrator.

Routes LLM requests to the appropriate model based on task type.
All routing is configurable via YAML - no hard-coded model choices.

Supports two config formats:
  1. Simple:  task_type: "model_alias"
  2. Rich:    task_type: {preferred: ..., fallback: ..., local_fallback: ...}

Profile-aware routing (H3): when a hardware profile is attached, aliases
the machine cannot serve are demoted out of the preferred slot — e.g. on a
CLOUD/MINIMAL machine with Ollama down, heavy local aliases yield to
whatever the fallback chain offers. Per-profile overrides live in
routing.yaml under ``profile_overrides``.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default routing rules - simple string format
DEFAULT_ROUTES = {
    "planning": "local_reasoner",
    "reasoning": "local_reasoner",
    "verification": "local_reasoner",
    "code_analysis": "local_coder",
    "code_generation": "local_coder",
    "exploit_development": "local_coder",
    "classification": "local_fast",
    "summarization": "local_fast",
    "tool_selection": "local_fast",
    "web_research": "research_model",
    "vulnerability_research": "research_model",
    "cve_analysis": "research_model",
    "report_generation": "local_fast",
    "sensitive_source_code": "local_coder",
    "default": "local_fast",
}


class ModelRouter:
    """Routes tasks to appropriate models based on task type."""

    def __init__(self, config_path: Optional[Path] = None):
        # Intentionally package-relative: routing.yaml is registry data that
        # ships next to this module — NOT a workspace resource (do not route
        # through cyberai.config.resolve_path).
        self.config_path = config_path or Path(__file__).parent / "routing.yaml"
        self._routes: Dict[str, Any] = {}
        self._profile_overrides: Dict[str, Dict[str, str]] = {}
        self._profile: Optional[str] = None
        self._alias_serving: Optional[Any] = None  # callable(alias) -> bool
        self._load()

    def attach_profile(
        self, profile: str, alias_serving: Optional[Any] = None,
    ) -> None:
        """
        Attach a hardware execution profile for profile-aware routing.

        Args:
            profile: one of MINIMAL / CLOUD / HYBRID / LOCAL / SERVER.
            alias_serving: optional callable(alias) -> bool reporting whether
                an alias is currently servable (e.g. gateway health). When
                provided, unservable preferred aliases are demoted.
        """
        self._profile = profile
        self._alias_serving = alias_serving
        logger.info("ModelRouter attached profile: %s", profile)

    @property
    def profile(self) -> Optional[str]:
        """The attached execution profile (None = profile-agnostic)."""
        return self._profile

    def _apply_profile_override(self, task_type: str) -> Any:
        """Apply a per-profile route override if one is configured."""
        if self._profile and self._profile in self._profile_overrides:
            override = self._profile_overrides[self._profile].get(task_type)
            if override:
                return override
        return None

    def _demote_unservable(self, entry: Any) -> Any:
        """
        Demote unservable preferred aliases within a rich route entry.

        If the preferred alias is reported unservable, promote the first
        servable alias from the fallback chain. Simple (string) entries are
        returned unchanged — there is nothing to demote to.
        """
        if self._alias_serving is None or not isinstance(entry, dict):
            return entry
        preferred = entry.get("preferred", "")
        if not preferred or self._alias_serving(preferred):
            return entry
        for cand in (entry.get("fallback", ""),
                     entry.get("local_fallback", "")):
            if cand and self._alias_serving(cand):
                new_entry = dict(entry)
                new_entry["preferred"] = cand
                logger.info("Profile routing demoted %s -> %s "
                            "(preferred alias unservable)", preferred, cand)
                return new_entry
        return entry

    def _load(self) -> None:
        """Load routing rules from config file or use defaults."""
        if self.config_path.exists():
            try:
                import yaml

                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                self._routes = data.get("routes", {})
                self._profile_overrides = data.get("profile_overrides", {}) or {}
                logger.info("Loaded %d routing rules from %s", len(self._routes), self.config_path)
            except Exception as e:
                logger.warning("Failed to load routing config: %s", e)
                self._routes = {k: v for k, v in DEFAULT_ROUTES.items()}
        else:
            self._routes = {k: v for k, v in DEFAULT_ROUTES.items()}

    def _get_route_entry(self, task_type: str) -> Any:
        """Get the raw routing entry for a task type (profile-aware)."""
        override = self._apply_profile_override(task_type)
        if override is not None:
            return override
        return self._routes.get(task_type, self._routes.get("default", "local_fast"))

    def route(self, task_type: str) -> str:
        """
        Route a task type to a model alias (the preferred model).

        Profile-aware: when a serving-check is attached and the preferred
        alias is unservable, the first servable fallback is promoted.

        Args:
            task_type: The type of task (e.g., "planning", "code_analysis")

        Returns:
            Model alias string (e.g., "local_reasoner")
        """
        entry = self._demote_unservable(self._get_route_entry(task_type))
        if isinstance(entry, dict):
            return entry.get("preferred", "local_fast")
        return entry

    def route_with_fallback(self, task_type: str) -> List[str]:
        """
        Get the full fallback chain for a task type.

        Returns:
            Ordered list of model aliases: [preferred, fallback, local_fallback]
        """
        entry = self._demote_unservable(self._get_route_entry(task_type))
        if isinstance(entry, dict):
            chain = [
                entry.get("preferred", "local_fast"),
                entry.get("fallback", "local_fast"),
                entry.get("local_fallback", "local_fast"),
            ]
            seen = set()
            return [m for m in chain if not (m in seen or seen.add(m))]
        return [entry, entry]

    def get_all_routes(self) -> Dict[str, Any]:
        """Return all routing rules."""
        return dict(self._routes)

    def update_route(self, task_type: str, model_alias: str) -> None:
        """Update a routing rule at runtime (sets simple string format)."""
        self._routes[task_type] = model_alias
        logger.info("Updated route: %s -> %s", task_type, model_alias)

    def update_route_full(
        self,
        task_type: str,
        preferred: str,
        fallback: str = "",
        local_fallback: str = "",
    ) -> None:
        """Update a routing rule with full fallback chain."""
        self._routes[task_type] = {
            "preferred": preferred,
            "fallback": fallback or preferred,
            "local_fallback": local_fallback or preferred,
        }
        logger.info("Updated route: %s -> preferred=%s", task_type, preferred)

    def to_yaml(self) -> str:
        """Return routing rules as YAML."""
        import yaml

        return yaml.dump({"routes": self._routes}, default_flow_style=False)