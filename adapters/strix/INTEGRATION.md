# Integration Record — Strix

## Original Project
- **Name:** Strix
- **Repository:** https://github.com/usestrix/strix
- **License:** Apache-2.0
- **Vendored as:** `adapters/strix/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Autonomous pentest agent (recon, scanning, analysis, exploitation)
- **Integration Method:** CLI invocation of `strix/interface/main.py` in the sandbox
- **Adapter Module:** `adapters.strix` (registry key: `strix`)
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
- `recon` — Recon via Strix agent
- `scan` — Vulnerability scan via Strix agent
- `analysis` — Analyze findings via Strix agent
- `exploitation` — Exploit via Strix agent (authorized lab only)

## Health Check Prerequisites
- Python interpreter available
- `strix/interface/main.py` present
- Docker installed for real scans (the Strix sandbox image) — without it the adapter reports WARN

## How To Run
```
# Real scans need Docker + a configured LLM:
cd adapters/strix
python -m strix.interface.main --help   # importability probe
# full usage: see the upstream README.md in this directory
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/strix                     # Windows: Remove-Item -Recurse adapters\strix
git clone https://github.com/usestrix/strix adapters/strix
```
The Cerberus adapter wrapper lives in `adapters/strix/__init__.py`;
the upstream tree starts at `adapters/strix/strix/`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/strix/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/usestrix/strix
- **License:** Apache-2.0
