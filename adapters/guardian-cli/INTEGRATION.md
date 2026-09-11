# Integration Record — Guardian

## Original Project
- **Name:** Guardian
- **Repository:** https://github.com/zakirkun/guardian-cli
- **License:** MIT
- **Vendored as:** `adapters/guardian-cli/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Recon/scan/analysis/report security CLI
- **Integration Method:** CLI (`python -m cli.main`) run in the sandbox
- **Adapter Module:** `adapters.guardian-cli` (registry key: `guardian_cli`)
- **Adapter Base:** `SandboxedAdapter` — policy-gated, evidence-logged

## Adapter Contract
Implements the standard orchestrator adapter interface
(`cyberai/orchestrator/adapters/base.py`):

- `health_check()` → `{status, message, details}`; status is one of
  `AVAILABLE`, `WARN`, `UNAVAILABLE`, `ERROR`
- `capabilities()` → list of `AdapterCapability(name, description)`
- `execute(task)` → `AdapterResult(success, output, error, evidence, metadata)`.
  `execute()` is the only public entry point: it authorizes the target with
  the policy engine (fails closed) and records evidence before delegating
  to `_do_execute()`. Never call `_do_execute()` directly.
- Task shape: `{action, target: {id, host, environment, allowed}, parameters, session_id}`

## Capabilities
- `recon` — Network recon via Guardian scan
- `scan` — Port scan via Guardian scan
- `analysis` — Analyze via Guardian analyze
- `report` — Report via Guardian report

## Health Check Prerequisites
- `cli/main.py` present

## How To Run
```
cd adapters/guardian-cli
python -m cli.main --help
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/guardian-cli                     # Windows: Remove-Item -Recurse adapters\guardian-cli
git clone https://github.com/zakirkun/guardian-cli adapters/guardian-cli
```
The Cerberus adapter wrapper lives in `adapters/guardian-cli/__init__.py`;
the upstream tree starts at `adapters/guardian-cli/cli/`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/guardian-cli/__init__.py`)
after re-cloning.

The directory is dash-named; the orchestrator resolves it via the `_HyphenAdapterFinder` in `adapters/__init__.py` (registry key: `guardian_cli`, module string: `adapters.guardian-cli`).

## Attribution
- **Original Repository:** https://github.com/zakirkun/guardian-cli
- **License:** MIT
