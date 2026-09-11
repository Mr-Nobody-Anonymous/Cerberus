# Integration Record — Dark-Moon

## Original Project
- **Name:** Dark-Moon
- **Repository:** https://github.com/ASCIT31/Dark-Moon
- **License:** GPL v3
- **Vendored as:** `adapters/darkmoon/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Autonomous pentesting agent (research, analysis, exploitation)
- **Integration Method:** MCP over HTTP (default port 8000)
- **Adapter Module:** `adapters.darkmoon` (registry key: `darkmoon`)
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
- `research` — Research via Dark-Moon agent
- `analysis` — Analyze target findings
- `exploitation` — Exploit weaknesses (authorized lab only)

## Health Check Prerequisites
- Dark-Moon MCP server listening (default `http://localhost:8000`; override with `DARKMOON_API_URL`)

## How To Run
```
python adapters/darkmoon/mcp/src/server.py
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/darkmoon                     # Windows: Remove-Item -Recurse adapters\darkmoon
git clone https://github.com/ASCIT31/Dark-Moon adapters/darkmoon
```
The Cerberus adapter wrapper lives in `adapters/darkmoon/__init__.py`;
the upstream tree starts at `adapters/darkmoon/mcp/`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/darkmoon/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/ASCIT31/Dark-Moon
- **License:** GPL v3
