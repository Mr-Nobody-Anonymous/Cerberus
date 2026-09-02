"""
Central configuration loader for CERBERUS.

This module is the single source of truth for all configuration:

* Paths are resolved relative to the ``CERBERUS_HOME`` environment variable
  (when set) or the repository root (parent of the ``cyberai/`` package).
* ``.env``, YAML config files and environment variables are merged in
  increasing order of precedence (defaults < YAML < env).
* Required YAML files/sections are validated *on load* and fail fast with a
  clear ``ConfigError`` instead of surfacing "file not found" at call time.

Usage::

    from cyberai.config import config, ConfigError, resolve_path

    host = config.get("llm", "ollama_host")
    targets = load_required_yaml("lab/targets/targets.yaml", section="targets")
"""

import copy
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ConfigError(RuntimeError):
    """Raised when configuration is missing, invalid, or cannot be resolved."""


def get_workspace_root() -> Path:
    """
    Resolve the CERBERUS workspace root.

    Priority:
      1. ``CERBERUS_HOME`` env var (must exist and be a directory).
      2. Repository root: parent of the ``cyberai/`` package.

    Returns:
        Absolute ``Path`` to the workspace root.

    Raises:
        ConfigError: if ``CERBERUS_HOME`` points at a non-existent path.
    """
    env_home = os.environ.get("CERBERUS_HOME", "").strip()
    if env_home:
        p = Path(env_home).resolve()
        if not p.is_dir():
            raise ConfigError(
                f"CERBERUS_HOME is set to '{env_home}' which is not an existing "
                "directory. Fix the variable or unset it to use the repo root."
            )
        return p
    return Path(__file__).resolve().parent.parent


# Workspace root — resolved once at import time.
WORKSPACE_ROOT = get_workspace_root()


def resolve_path(relative: "str | Path") -> Path:
    """
    Resolve a possibly-relative path against the workspace root.

    Absolute paths are returned unchanged. Relative paths are made relative
    to ``CERBERUS_HOME`` (or the repo root).

    Args:
        relative: path-like value (str or Path)

    Returns:
        Absolute ``Path``.
    """
    p = Path(relative)
    if p.is_absolute():
        return p
    return WORKSPACE_ROOT / p


def load_required_yaml(
    rel_path: "str | Path",
    section: Optional[str] = None,
    required_fields: Optional[list] = None,
    item_label: str = "entry",
) -> Any:
    """
    Load and validate a required YAML file, failing fast on any problem.

    Args:
        rel_path: Workspace-relative (or absolute) path to the YAML file.
        section: If set, the YAML must contain this top-level key.
        required_fields: If set, every item in the (list-valued) section must
            contain these keys.
        item_label: Human-readable label used in validation errors.

    Returns:
        Parsed YAML data (dict or list).

    Raises:
        ConfigError: if the file is missing, unparsable, lacks the required
            section, or contains entries missing required fields.
    """
    import yaml

    path = resolve_path(rel_path)
    if not path.exists():
        raise ConfigError(
            f"Required YAML file not found: {path}. "
            "Install the project's data files or fix the configured path."
        )
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:  # noqa: BLE001 — re-raise as ConfigError
        raise ConfigError(f"Failed to parse YAML at {path}: {e}") from e

    if data is None:
        data = {}

    if section is not None:
        if not isinstance(data, dict) or section not in data or data[section] is None:
            raise ConfigError(f"Required section '{section}' missing/empty in {path}")
        data = data[section]

    if required_fields:
        if not isinstance(data, list):
            raise ConfigError(f"Section in {path} must be a list of {item_label}s")
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ConfigError(f"{item_label} #{i} in {path} is not a mapping")
            missing = [f for f in required_fields if f not in item]
            if missing:
                raise ConfigError(
                    f"{item_label} #{i} ('{item.get('id', '<no id>')}') in {path} "
                    f"is missing required field(s): {', '.join(missing)}"
                )

    return data


def validate_targets_file(rel_path: "str | Path" = "lab/targets/targets.yaml") -> list:
    """
    Load and validate the authorized-targets file.

    Every target must have: ``id``, ``environment`` (== ``authorized_lab``)
    and ``allowed`` (a boolean). Fails fast with a descriptive error.

    Returns:
        List of validated target dicts.
    """
    targets = load_required_yaml(
        rel_path,
        section="targets",
        required_fields=["id", "environment", "allowed"],
        item_label="target",
    )
    for t in targets:
        if t["environment"] not in ("authorized_lab",):
            raise ConfigError(
                f"Target '{t['id']}' has environment='{t['environment']}'. "
                "Only 'authorized_lab' targets are permitted."
            )
        if not isinstance(t["allowed"], bool):
            raise ConfigError(
                f"Target '{t['id']}' field 'allowed' must be true/false, "
                f"got {t['allowed']!r}."
            )
    return targets
class Config:
    """Central configuration with defaults, YAML-file and env merging."""

    DEFAULTS: Dict[str, Any] = {
        "privacy": {
            "mode": "local_only",  # local_only | hybrid
        },
        "llm": {
            "ollama_host": "http://localhost:11434",
            "ollama_model": "llama3.1:8b",
            "litellm_host": "http://localhost",
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
            "experiences_db_path": "memory/experiences.db",
            "performance_db_path": "memory/performance.db",
            "evolution_dir": "memory/evolution",
        },
        "logging": {
            "level": "INFO",
            "tasks_dir": "logs/tasks",
            "models_dir": "logs/models",
            "agents_dir": "logs/agents",
            "evolution_dir": "logs/evolution",
            "sessions_dir": "logs/sessions",
        },
        "evidence": {
            "dir": "lab/evidence",
        },
        "evolution": {
            "population_size": 10,
            "elite_size": 3,
            "mutation_rate": 0.3,
            "crossover_rate": 0.5,
        },
        "routing": {
            "fallback_chain": ["preferred", "fallback", "local_fallback"],
            "local_only": True,
        },
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or WORKSPACE_ROOT / "config.yaml"
        self._data: Dict[str, Any] = copy.deepcopy(self.DEFAULTS)
        self._load_file()
        self._load_env()

    # --- loading ------------------------------------------------ #
    def _load_file(self) -> None:
        """Merge an optional ``config.yaml`` into the defaults."""
        if not self.config_path.exists():
            return
        try:
            import yaml

            with open(self.config_path, "r", encoding="utf-8") as f:
                file_data = yaml.safe_load(f) or {}
            if not isinstance(file_data, dict):
                raise ConfigError(f"config.yaml at {self.config_path} must be a mapping")
            self._merge(self._data, file_data)
            logger.info("Loaded config from %s", self.config_path)
        except ConfigError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ConfigError(f"Failed to load config file {self.config_path}: {e}") from e

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
        env_map: Dict[str, tuple] = {
            "OLLAMA_HOST": ("llm", "ollama_host"),
            "OLLAMA_MODEL": ("llm", "ollama_model"),
            "LITELLM_HOST": ("llm", "litellm_host"),
            "LITELLM_PORT": ("llm", "litellm_port"),
            "LITELLM_MASTER_KEY": ("llm", "litellm_master_key"),
            "PRIVACY_MODE": ("privacy", "mode"),
            "LAB_TARGETS_PATH": ("policy", "targets_path"),
            "REQUIRE_TARGET_AUTHORIZATION": ("policy", "require_target_authorization"),
            "MEMORY_DB_PATH": ("memory", "db_path"),
            "EXPERIENCES_DB_PATH": ("memory", "experiences_db_path"),
            "PERFORMANCE_DB_PATH": ("memory", "performance_db_path"),
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
        """Load .env file if present (stdlib-only, no python-dotenv needed)."""
        env_path = WORKSPACE_ROOT / ".env"
        if not env_path.exists():
            return
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load .env: %s", e)

    # --- accessors ---------------------------------------------- #
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """Get a config value by section and optional key."""
        if section not in self._data:
            return default
        if key is None:
            return self._data[section]
        return self._data[section].get(key, default)

    def get_path(self, section: str, key: str, default: str = "") -> Path:
        """Return a config value as a workspace-resolved absolute Path."""
        value = self.get(section, key, default)
        return resolve_path(value)

    def is_local_only(self) -> bool:
        """Check if privacy mode is local_only."""
        return self.get("privacy", "mode", "local_only").lower() == "local_only"

    def resolve_path(self, relative: "str | Path") -> Path:
        """Resolve a workspace-relative path (backwards-compatible helper)."""
        return resolve_path(relative)

    def to_dict(self) -> Dict[str, Any]:
        """Return full config as dict."""
        return copy.deepcopy(self._data)


# Singleton instance
config = Config()