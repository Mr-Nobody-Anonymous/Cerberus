# Integration Record — PenClaw

## Original Project
- **Name:** PenClaw
- **Repository:** https://github.com/andupetcu/penclaw
- **License:** See LICENSE
- **Vendored as:** `adapters/penclaw/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Code security analysis (static, dynamic, secret detection)
- **Integration Method:** Node.js CLI (`dist/cli/index.js`) run in the sandbox
- **Adapter Module:** `adapters.penclaw` (registry key: `penclaw`)
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
- `static_analysis` — Static analysis via PenClaw
- `dynamic_scanning` — Dynamic scanning via PenClaw
- `secret_detection` — Secret detection via PenClaw

## Health Check Prerequisites
- Node.js installed
- `dist/cli/index.js` built — otherwise run `npm install && npm run build`

## How To Run
```
cd adapters/penclaw
npm install && npm run build
node dist/cli/index.js --help
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/penclaw                     # Windows: Remove-Item -Recurse adapters\penclaw
git clone https://github.com/andupetcu/penclaw adapters/penclaw
```
The Cerberus adapter wrapper lives in `adapters/penclaw/__init__.py`;
the upstream tree starts at `adapters/penclaw/src/ (built to dist/)`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/penclaw/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/andupetcu/penclaw
- **License:** See LICENSE
