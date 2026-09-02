"""Phase A — central config loader tests.

Validates:
- CERBERUS_HOME env-var resolution and repo-root fallback
- Path resolution relative to the workspace root
- Fail-fast YAML validation (missing file, missing section, missing fields)
- Targets file validation (environment must be authorized_lab, allowed bool)
"""

import os
from pathlib import Path

import pytest

from cyberai.config import (
    Config,
    ConfigError,
    WORKSPACE_ROOT,
    get_workspace_root,
    load_required_yaml,
    resolve_path,
    validate_targets_file,
)


def test_workspace_root_is_repo_root():
    """By default the workspace root is the parent of the cyberai package."""
    assert WORKSPACE_ROOT.is_dir()
    assert (WORKSPACE_ROOT / "cyberai").is_dir()
    assert get_workspace_root() == WORKSPACE_ROOT


def test_cerberus_home_env_override(monkeypatch, tmp_path):
    """CERBERUS_HOME must be honoured when set to a valid directory."""
    monkeypatch.setenv("CERBERUS_HOME", str(tmp_path))
    assert get_workspace_root() == tmp_path.resolve()


def test_cerberus_home_invalid_fails_fast(monkeypatch):
    """CERBERUS_HOME pointing at a non-directory raises a clear error."""
    monkeypatch.setenv("CERBERUS_HOME", "Z:/definitely/not/a/dir")
    with pytest.raises(ConfigError, match="not an existing directory"):
        get_workspace_root()


def test_resolve_path_relative_and_absolute():
    resolved = resolve_path("lab/targets/targets.yaml")
    assert resolved.is_absolute()
    assert resolved == WORKSPACE_ROOT / "lab" / "targets" / "targets.yaml"

    absolute = Path(os.path.abspath(os.sep)) / "somewhere"
    assert resolve_path(absolute) == absolute


def test_load_required_yaml_missing_file_fails_fast(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_required_yaml(tmp_path / "missing.yaml")


def test_load_required_yaml_missing_section(tmp_path):
    p = tmp_path / "conf.yaml"
    p.write_text("other: 1\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Required section 'targets'"):
        load_required_yaml(p, section="targets")


def test_load_required_yaml_missing_fields(tmp_path):
    p = tmp_path / "targets.yaml"
    p.write_text(
        "targets:\n  - id: t1\n    allowed: true\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="missing required field"):
        load_required_yaml(p, section="targets", required_fields=["id", "environment"])


def test_validate_targets_file_current_repo_targets():
    """The repo's own targets file must validate cleanly."""
    targets = validate_targets_file()
    assert len(targets) >= 1
    for t in targets:
        assert t["environment"] == "authorized_lab"
        assert isinstance(t["allowed"], bool)


def test_validate_targets_file_rejects_wrong_environment(tmp_path):
    p = tmp_path / "targets.yaml"
    p.write_text(
        "targets:\n  - id: t1\n    environment: production\n    allowed: true\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="authorized_lab"):
        validate_targets_file(p)


def test_config_defaults_and_env_precedence(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://example:1234")
    cfg = Config(config_path=WORKSPACE_ROOT / "definitely-missing.yaml")
    assert cfg.get("llm", "ollama_host") == "http://example:1234"
    assert cfg.is_local_only() is True
