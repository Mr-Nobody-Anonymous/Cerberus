# Changelog

All notable changes to Cerberus are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- **Vendored LiteLLM source tree** (`cyberai/llm_gateway/litellm/`, 8,184 files / 152 MB) — it was never imported: the gateway talks HTTP to the LiteLLM proxy, which now runs as the pinned Docker image `ghcr.io/berriai/litellm:v1.97.0` (exact version previously vendored).
- **Vendored A-Evolve source tree** (`cyberai/evolution/a-evolve/`, 417 files / 6.4 MB) — never imported by the native evolution engine; retained upstream as design reference (see REPOSITORY_MAP.yaml).

### Fixed
- **Broken kebab-case paths** left over from the `platform/` → `cyberai/` rename: `docker-compose.yml` volume mounts, `.env.example` `LITELLM_CONFIG_PATH`, `scaffold_system.py` gateway-config writes, and `.gitignore` LiteLLM data paths now point at the real `cyberai/llm_gateway/` (snake_case) directory. The compose mounts previously referenced `cyberai/llm-gateway/`, which does not exist — Docker would have mounted empty dirs.
- **ARCHITECTURE.md** no longer describes `cyberai/tool-gateway/` as an "empty legacy directory" — it hosts the live MCP gateway (loaded via `importlib`).

### Changed
- **Package build no longer sweeps 5,685 vendored files** into the wheel/sdist (`[tool.setuptools.packages.find]` glob `cyberai*` previously matched the vendored trees).
- **Coverage config** no longer needs to omit the vendored tree.

## [2.0.0] - 2026-09-09

### Added
- **CI pipeline** (`.github/workflows/ci.yml`): full test suite + doctor health check on every push/PR (Python 3.10 & 3.11, Ubuntu runner)
- **CONTRIBUTING.md** — development setup, testing requirements, adapter contribution guide
- **SECURITY.md** — responsible disclosure policy, authorized-use scope, platform security controls
- **CODE_OF_CONDUCT.md** — Contributor Covenant
- **Coverage configuration** (`[tool.coverage.*]` in `pyproject.toml`) — `pytest --cov` works out of the box
- **Pre-commit hooks** (`.pre-commit-config.yaml`) — trailing whitespace, EOF newlines, YAML/JSON validity, large-file guard

### Removed
- **Internal session/audit artifacts:** `FINAL_STATUS.md`, `INTEGRATION_STATUS.md`, `PHASE2_AUDIT.md`, `REDESIGN_AUDIT.md`, `REDESIGN_GAP_ANALYSIS.md`, `WORKSPACE_INVENTORY.md`, and `logs/darkmoon_probe.txt` — historical working documents superseded by README/ARCHITECTURE/CHANGELOG; all cross-references updated.

### Fixed
- **Adapters were never wired to the policy engine** — every real adapter execution failed with `Policy denied: 'NoneType' object has no attribute 'is_authorized'`. The orchestrator now injects `policy_engine`, `evidence_manager`, and `session_id` into each adapter before execution.
- **CLI `task` command crash** — click option `--target-id` was bound to a mismatched parameter name.
- **`execute_task` sent incomplete target data** — adapters now receive the full target dict so the policy gate can authorize properly.
- **9 tools missing from the capability registry** — all 17 tools are now selectable (17/17).
- **UTF-8 encoding corruption** in `tool_registry.py` and `model_router.py` (em-dashes mangled on Windows cp1252).
- **Duplicate `view-graph` section** in the UI dashboard `index.html`.
- **README banner image path** (`ult.ipg` → `ult.jpg`).

### Changed
- **Repository hygiene:** untracked the committed virtual environment (5,318 files), 17 dev scratch files, stale doctor baseline, and 8 dead one-off fix scripts. Clones are now ~19% smaller.
- **Documentation accuracy:** corrected stale adapter counts (17 wrappers, not 15+2) and test counts (155, not 98) across README, FINAL_STATUS, ARCHITECTURE, WORKSPACE_INVENTORY, INTEGRATION_STATUS.
- **Runtime artifacts untracked:** 464 evolution JSONs that churned on every test run, plus gradle build lock files.

### Verified
- 155/155 tests pass (fresh-venv install from `pyproject.toml` only)
- `cyber-ai doctor` exits 0
- End-to-end task execution: real adapter run → policy gate pass → 5 knowledge findings → evidence logged

## [1.x] - Historical

Earlier development history (multi-phase build: orchestrator core, 17 tool adapters, LLM gateway, evolution loop, UI dashboard) predates this changelog. See the git log for details.
