# Integration Record — CyberStrikeAI

## Original Project
- **Name:** CyberStrikeAI
- **Repository:** https://github.com/Ed1s0nZ/CyberStrikeAI
- **License:** See LICENSE
- **Vendored as:** `adapters/cyberstrikeai/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** MCP-driven security tool executor with analysis
- **Integration Method:** Gin (Go) REST API + MCP (default port 8080)
- **Adapter Module:** `adapters.cyberstrikeai` (registry key: `cyberstrikeai`)
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
- `tool_execution` — Execute security tools via CyberStrikeAI
- `mcp_servers` — Drive CyberStrikeAI MCP servers
- `analysis` — Analyze target findings

## Health Check Prerequisites
- CyberStrikeAI Go server listening (default `http://localhost:8080`; override with `CYBERSTRIKEAI_API_URL`)

## How To Run
```
cd adapters/cyberstrikeai
go build ./cmd/...   # then start the server (see upstream README)
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/cyberstrikeai                     # Windows: Remove-Item -Recurse adapters\cyberstrikeai
git clone https://github.com/Ed1s0nZ/CyberStrikeAI adapters/cyberstrikeai
```
The Cerberus adapter wrapper lives in `adapters/cyberstrikeai/__init__.py`;
the upstream tree starts at `adapters/cyberstrikeai/Go sources at the adapter root`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/cyberstrikeai/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/Ed1s0nZ/CyberStrikeAI
- **License:** See LICENSE
