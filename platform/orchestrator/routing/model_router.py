"""
Model Router for the Cyber AI Orchestrator.

Routes LLM requests to the appropriate model based on task type.
All routing is configurable via YAML - no hard-coded model choices.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Default routing rules - configurable via routing.yaml
DEFAULT_ROUTES = {
    "planning": "local-reasoner",
    "reasoning": "local-reasoner",
    "verification": "local-reasoner",
    "code_analysis": "local-coder",
    "code_generation": "local-coder",
    "exploit_development": "local-coder",
    "classification": "local-fast",
    "summarization": "local-fast",
    "tool_selection": "local-fast",
    "web_research": "research-model",
    "vulnerability_research": "research-model",
    "cve_analysis": "research-model",
    "report_generation": "local-fast",
    "sensitive_source_code": "local-coder",  # Always local for sensitive data
    "default": "local-fast",
}


class ModelRouter:
    """Routes tasks to appropriate models based on task type."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path(__file__).parent / "routing.yaml"
        self._routes: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        """Load routing rules from config file or use defaults."""
        if self.config_path.exists():
            try:
                import yaml

                with open(self.config_path, "r") as f:
                    data = yaml.safe_load(f)
                self._routes = data.get("routes", {})
                logger.info(f"Loaded {len(self._routes)} routing rules from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load routing config: {e}")
                self._routes = DEFAULT_ROUTES
        else:
            self._routes = DEFAULT_ROUTES

    def route(self, task_type: str) -> str:
        """
        Route a task type to a model alias.

        Args:
            task_type: The type of task (e.g., "planning", "code_analysis")

        Returns:
            Model alias string (e.g., "local-reasoner")
        """
        return self._routes.get(task_type, self._routes.get("default", "local-fast"))

    def get_all_routes(self) -> Dict[str, str]:
        """Return all routing rules."""
        return dict(self._routes)

    def update_route(self, task_type: str, model_alias: str) -> None:
        """Update a routing rule at runtime."""
        self._routes[task_type] = model_alias
        logger.info(f"Updated route: {task_type} -> {model_alias}")

    def to_yaml(self) -> str:
        """Return routing rules as YAML."""
        import yaml

        return yaml.dump({"routes": self._routes}, default_flow_style=False)