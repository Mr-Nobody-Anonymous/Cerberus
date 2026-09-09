# Contributing to Cerberus

Thank you for your interest in contributing to **Cerberus** — the self-evolving multi-agent cyber AI security research orchestrator.

This project deals with offensive security tooling. Contributions are welcome, but they must respect the ethical boundaries described below.

## ⚖️ Ground Rules (read first)

1. **Authorized use only.** Every tool in this platform is intended for use in authorized engagements, lab environments, and research. Never contribute code whose primary purpose is attacking systems you do not own or have written permission to test.
2. **Lab-first design.** New capabilities must be testable against local lab targets (see `lab/targets/`) without touching third-party infrastructure.
3. **Policy gate compliance.** All tool execution flows through the policy engine (`cyberai/security/`). New adapters must respect `policy_engine.is_authorized()` — no bypasses.
4. **Evidence-first.** Actions that produce findings must log evidence via the evidence manager. Silent actions are not acceptable.

## 🛠️ Development Setup

### Prerequisites

- Python **3.10+**
- Git
- (Optional) Docker — for sandboxed tool execution and lab targets
- (Optional) Ollama — for local LLM inference

### Steps

```bash
# 1. Clone
git clone https://github.com/Mr-Nobody-Anonymous/Cerberus.git
cd Cerberus

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install in editable mode with dev + api extras
pip install -e ".[dev,api]"

# 4. Copy the environment template and adjust as needed
cp .env.example .env

# 5. Run the health check
cyber-ai doctor

# 6. Run the test suite
pytest
```

> **Note:** Never commit your virtual environment, `.env`, or any runtime artifacts (logs, memory dumps, evidence). The `.gitignore` already excludes them — if you find something tracked that shouldn't be, open an issue.

## 🧪 Testing

The test suite lives in `tests/` (unit + integration, 155 tests).

```bash
# Full suite
pytest

# Fast subset while developing
pytest tests/test_config.py tests/test_event_core.py -q

# With coverage
pytest --cov=cyberai --cov-report=term-missing
```

**Requirements for every PR:**

- All tests pass (`pytest` exits 0)
- `cyber-ai doctor` exits 0
- New features come with tests
- Bug fixes come with a regression test that fails before the fix

CI runs the full suite on every push and pull request (see `.github/workflows/ci.yml`). A red CI blocks merging.

## 🏗️ Architecture Orientation

Before writing code, skim [`ARCHITECTURE.md`](ARCHITECTURE.md). The short version:

| Layer | Location | Role |
|---|---|---|
| Orchestration | `cyberai/orchestrator/` | Task lifecycle, CLI, evidence, policy wiring |
| Capabilities | `cyberai/capabilities/` | Tool registry — 17 security tools |
| Adapters | `adapters/` | Wrappers around external security tools (h4cker, drakben, hexstrike, …) |
| LLM Gateway | `cyberai/llm_gateway/` | LiteLLM proxy / Ollama / provider fallback chain |
| Evolution | `cyberai/evolution/` | Self-improvement loop, strategy memory |
| Security | `cyberai/security/` | Policy engine, authorization gates |
| UI | `cyberai/ui/` | FastAPI dashboard (port 8710) |

### Adding a new tool adapter

1. Create `adapters/<tool-name>/` with a `SecurityToolAdapter`-compatible wrapper.
2. Register it in `cyberai/orchestrator/tools.yaml` (name, description, adapter path).
3. Ensure it appears in `cyberai/capabilities/registry.py` (directly or via fallback discovery).
4. Add tests under `tests/`.
5. Run `cyber-ai doctor` — it must report the adapter.

## 📝 Commit & PR Conventions

- **Commit style:** Conventional Commits — `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`.
- **Branching:** `main` is the release branch. Work in feature branches (`feat/<topic>`, `fix/<topic>`).
- **PR size:** Keep PRs focused. One logical change per PR.
- **PR description:** What changed, why, how it was tested (commands + output summary).

## 📦 Release Process

Releases are tagged from `main` (`v2.0.0` style, matching `pyproject.toml`). Every release gets a `CHANGELOG.md` entry.

## 🐛 Reporting Issues

- **Bugs:** Open an issue with reproduction steps, expected vs actual behavior, and `cyber-ai doctor` output.
- **Security vulnerabilities:** Do **not** open a public issue — see [`SECURITY.md`](SECURITY.md).

## 📄 License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
