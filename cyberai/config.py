"""
Central configuration loader for the Cyber AI platform.

Provides a single source of truth for all configuration, merging:
- Defaults
- YAML config files
- Environment variables (.env)

Supports privacy modes: local_only and hybrid.
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Workspace root = parent of cyberai/
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


class Config:
    """Central configuration with defaults, file, and env merging."""

    DEFAULTS: Dict[str, Any] = {
        "privacy": {
            "mode": "local_only",  # local_only | hybrid
        },
        "llm": {
            "ollama_host": "http://localhost:11434",
            "ollama_model": "llama3.1:8b",
            "litellm_port": 4000,
            "litellm_master_key": "",
            "timeout_seconds": 300,
            "max_tokens": 2048,
            "temperature": 0.7,
        },
        "policy": {
            "require_target_authorization": True,
            "targets_path": "lab/targets/targets.yaml",
            "default_allowed_actions": ["recon", "scan", "analysis"],
        },
        "memory": {
            "db_path": "memory/memory.db",
            "evolution_dir": "memory/evolution",
        },
        "logging": {
            "level": "INFO",
            "tasks_dir": "logs/tasks",
            "models_dir": "logs/models",
            "agents_dir": "logs/agents",
            "evolution_dir": "logs/evolution",
        },
        "evolution": {
            "population_size": 10,
            "elite_size": 3,
            "mutation_rate": 0.3,
            "crossover_rate": 0.5,
            "fitness_weights": {
                "success": 1.0,
                "verification": 0.8,
                "evidence_quality": 0.6,
                "repeatability": 0.5,
                "unnecessary_actions": -0.3,
                "failures": -0.5,
            },
        },
        "routing": {
            "fallback_chain": ["preferred", "fallback", "local_fallback"],
            "local_only": True,
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or WORKSPACE_ROOT / "config.yaml"
        self._data: Dict[str, Any] = self._deep_copy(self.DEFAULTS)
        self._load_file()
        self._load_env()

    def _deep_copy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        import copy
        return copy.deepcopy(data)

    def _load_file(self) -> None:
        """Load config from YAML file if present."""
        if self.config_path.exists():
            try:
                import yaml
                with open(self.config_path, "r") as f:
                    file_data = yaml.safe_load(f) or {}
                self._merge(self._data, file_data)
                logger.info(f"Loaded config from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_path}: {e}")

    def _merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge override into base."""
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                self._merge(base[key], value)
            else:
                base[key] = value

    def _load_env(self) -> None:
        """Load environment variables (with .env support)."""
        self._load_dotenv()
        env_map = {
            "OLLAMA_HOST": ("llm", "ollama_host"),
            "OLLAMA_MODEL": ("llm", "ollama_model"),
            "LITELLM_PORT": ("llm", "litellm_port"),
            "LITELLM_MASTER_KEY": ("llm", "litellm_master_key"),
            "LAB_TARGETS_PATH": ("policy", "targets_path"),
            "REQUIRE_TARGET_AUTHORIZATION": ("policy", "require_target_authorization"),
            "PRIVACY_MODE": ("privacy", "mode"),
        }
        for env_name, (section, key) in env_map.items():
            val = os.environ.get(env_name)
            if val is not None:
                self._data[section][key] = self._coerce(val)

    def _coerce(self, value: str) -> Any:
        """Coerce string env values to appropriate types."""
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    def _load_dotenv(self) -> None:
        """Load .env file if present (without python-dotenv dependency)."""
        env_path = WORKSPACE_ROOT / ".env"
        if env_path.exists():
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key and key not in os.environ:
                            os.environ[key] = value
            except Exception as e:
                logger.warning(f"Failed to load .env: {e}")

    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """Get a config value by section and optional key."""
        if section not in self._data:
            return default
        if key is None:
            return self._data[section]
        return self._data[section].get(key, default)

    def is_local_only(self) -> bool:
        """Check if privacy mode is local_only."""
        return self.get("privacy", "mode", "local_only") == "local_only"

    def resolve_path(self, relative: str) -> Path:
        """Resolve a workspace-relative path."""
        p = Path(relative)
        if p.is_absolute():
            return p
        return WORKSPACE_ROOT / p

    def to_dict(self) -> Dict[str, Any]:
        """Return full config as dict."""
        return self._deep_copy(self._data)


# Singleton instance
config = Config()