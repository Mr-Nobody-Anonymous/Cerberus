# Integration Record — Cybersecurity AI (CAI)

## Original Project
- **Name:** Cybersecurity AI (CAI)
- **Repository:** https://github.com/aliasrobotics/CAI
- **License:** Dual MIT + Proprietary (see upstream LICENSE)
- **Vendored as:** `adapters/cai/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Agent framework for cybersecurity research and analysis
- **Integration Method:** Python library imported in-process (vendored source preferred)
- **Adapter Module:** `adapters.cai` (registry key: `cai`)
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
- `research` — Research via CAI agents
- `analysis` — Analyze via CAI agents
- `agent_framework` — Run CAI agent framework

## Health Check Prerequisites
- CAI importable in the current interpreter
- If not installed: `pip install -e adapters/cai` (the adapter also inserts the vendored source on sys.path)

## How To Run
```
pip install -e adapters/cai
# then the orchestrator can drive CAI agents in-process
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/cai                     # Windows: Remove-Item -Recurse adapters\cai
git clone https://github.com/aliasrobotics/CAI adapters/cai
```
The Cerberus adapter wrapper lives in `adapters/cai/__init__.py`;
the upstream tree starts at `adapters/cai/cai tree at the adapter root`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/cai/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/aliasrobotics/CAI
- **License:** Dual MIT + Proprietary (see upstream LICENSE)
