# Integration Record — DRAKBEN

## Original Project
- **Name:** DRAKBEN
- **Repository:** https://github.com/ahmetdrak/drakben
- **License:** MIT
- **Vendored as:** `adapters/drakben/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Autonomous pentesting agent (recon, analysis, exploitation)
- **Integration Method:** CLI invocation of `drakben.py` in the sandbox
- **Adapter Module:** `adapters.drakben` (registry key: `drakben`)
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
- `recon` — Network recon via DRAKBEN tools
- `analysis` — Analyze target findings
- `exploitation` — Exploit weaknesses

## Health Check Prerequisites
- Python interpreter available
- `drakben.py` present
- `core/` package present

## How To Run
```
cd adapters/drakben
python drakben.py --help
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/drakben                     # Windows: Remove-Item -Recurse adapters\drakben
git clone https://github.com/ahmetdrak/drakben adapters/drakben
```
The Cerberus adapter wrapper lives in `adapters/drakben/__init__.py`;
the upstream tree starts at `adapters/drakben/drakben.py + core/`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/drakben/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/ahmetdrak/drakben
- **License:** MIT
