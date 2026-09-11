# Integration Record — ARACNE

## Original Project
- **Name:** ARACNE
- **Repository:** https://github.com/stratosphereips/aracne
- **License:** See LICENSE
- **Vendored as:** `adapters/aracne/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** SSH-driven exploitation and research agent
- **Integration Method:** CLI invocation of `aracne.py` in the sandbox
- **Adapter Module:** `adapters.aracne` (registry key: `aracne`)
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
- `research` — Research via ARACNE
- `exploitation` — Exploit via ARACNE (authorized lab only)
- `ssh_driven` — SSH-driven execution via ARACNE

## Health Check Prerequisites
- Python interpreter available
- `aracne.py` present

## How To Run
```
cd adapters/aracne
python aracne.py --help
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/aracne                     # Windows: Remove-Item -Recurse adapters\aracne
git clone https://github.com/stratosphereips/aracne adapters/aracne
```
The Cerberus adapter wrapper lives in `adapters/aracne/__init__.py`;
the upstream tree starts at `adapters/aracne/aracne.py at the adapter root`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/aracne/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/stratosphereips/aracne
- **License:** See LICENSE
