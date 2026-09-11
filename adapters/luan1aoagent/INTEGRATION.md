# Integration Record — LuaN1aoAgent

## Original Project
- **Name:** LuaN1aoAgent
- **Repository:** https://github.com/SanMuzZzZz/LuaN1aoAgent
- **License:** AGPL v3
- **Vendored as:** `adapters/luan1aoagent/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Autonomous security agent (research, analysis, planning)
- **Integration Method:** Node.js CLI (`dist/cli.js`) run in the sandbox
- **Adapter Module:** `adapters.luan1aoagent` (registry key: `luan1aoagent`)
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
- `research` — Research via LuaN1aoAgent
- `analysis` — Analyze via LuaN1aoAgent
- `planning` — Plan via LuaN1aoAgent

## Health Check Prerequisites
- Node.js installed
- `dist/cli.js` built — otherwise run `npm install && npm run build`

## How To Run
```
cd adapters/luan1aoagent
npm install && npm run build
node dist/cli.js --help
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/luan1aoagent                     # Windows: Remove-Item -Recurse adapters\luan1aoagent
git clone https://github.com/SanMuzZzZz/LuaN1aoAgent adapters/luan1aoagent
```
The Cerberus adapter wrapper lives in `adapters/luan1aoagent/__init__.py`;
the upstream tree starts at `adapters/luan1aoagent/TypeScript sources (built to dist/)`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/luan1aoagent/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/SanMuzZzZz/LuaN1aoAgent
- **License:** AGPL v3
