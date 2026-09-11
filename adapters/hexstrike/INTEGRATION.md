# Integration Record — HexStrike AI

## Original Project
- **Name:** HexStrike AI
- **Repository:** https://github.com/0x4m4/hexstrike-ai
- **License:** MIT
- **Vendored as:** `adapters/hexstrike/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Tool gateway exposing 150+ offensive security tools via REST/MCP
- **Integration Method:** Flask REST API + MCP (default port 8000)
- **Adapter Module:** `adapters.hexstrike` (registry key: `hexstrike`)
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
- `tool_execution` — Execute security tools via HexStrike REST
- `mcp_servers` — Drive HexStrike MCP servers
- `web_scraping` — Web scraping via HexStrike browser agent

## Health Check Prerequisites
- HexStrike server listening (default `http://localhost:8000`; override with `HEXSTRIKE_API_URL`)

## How To Run
```
python adapters/hexstrike/hexstrike_server.py
# configure API keys for the tools you want to drive
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/hexstrike                     # Windows: Remove-Item -Recurse adapters\hexstrike
git clone https://github.com/0x4m4/hexstrike-ai adapters/hexstrike
```
The Cerberus adapter wrapper lives in `adapters/hexstrike/__init__.py`;
the upstream tree starts at `adapters/hexstrike/hexstrike tree at the adapter root`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/hexstrike/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/0x4m4/hexstrike-ai
- **License:** MIT
