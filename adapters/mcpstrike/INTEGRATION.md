# Integration Record — mcpstrike

## Original Project
- **Name:** mcpstrike
- **Repository:** https://github.com/ente0/mcpstrike
- **License:** MIT
- **Vendored as:** `adapters/mcpstrike/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Ollama-driven MCP tool gateway
- **Integration Method:** FastAPI server + MCP (default port 8080)
- **Adapter Module:** `adapters.mcpstrike` (registry key: `mcpstrike`)
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
- `tool_execution` — Execute security tools via mcpstrike
- `mcp_servers` — Drive mcpstrike MCP servers

## Health Check Prerequisites
- mcpstrike server listening (default `http://localhost:8080`; override with `MCPSTRIKE_API_URL`)

## How To Run
```
cd adapters/mcpstrike/src
python -m mcpstrike.server.app   # needs a local Ollama daemon
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/mcpstrike                     # Windows: Remove-Item -Recurse adapters\mcpstrike
git clone https://github.com/ente0/mcpstrike adapters/mcpstrike
```
The Cerberus adapter wrapper lives in `adapters/mcpstrike/__init__.py`;
the upstream tree starts at `adapters/mcpstrike/src/`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/mcpstrike/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/ente0/mcpstrike
- **License:** MIT
