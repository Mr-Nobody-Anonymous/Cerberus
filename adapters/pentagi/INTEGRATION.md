# Integration Record — PentAGI

## Original Project
- **Name:** PentAGI
- **Repository:** https://github.com/vxcontrol/pentagi
- **License:** See LICENSE file in repository
- **Vendored as:** `adapters/pentagi/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Primary autonomous pentesting agent (research, analysis, exploitation, reporting)
- **Integration Method:** REST/GraphQL API served by its Docker Compose stack
- **Adapter Module:** `adapters.pentagi` (registry key: `pentagi`)
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
- `research` — Research via PentAGI agent
- `analysis` — Analyze target findings
- `exploitation` — Exploit weaknesses (authorized lab only)
- `reporting` — Generate assessment report

## Health Check Prerequisites
- Docker installed and the PentAGI compose stack running (`docker compose up -d`)
- API port listening (default `https://localhost:8443`; override with `PENTAGI_API_URL`)
- UNAVAILABLE/WARN otherwise — WARN includes the exact start command

## How To Run
```
cd adapters/pentagi
cp .env.example .env   # configure LLM providers
docker compose up -d
# API at https://localhost:8443 (self-signed cert)
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/pentagi                     # Windows: Remove-Item -Recurse adapters\pentagi
git clone https://github.com/vxcontrol/pentagi adapters/pentagi
```
The Cerberus adapter wrapper lives in `adapters/pentagi/__init__.py`;
the upstream tree starts at `adapters/pentagi/pentagi tree at the adapter root`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/pentagi/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/vxcontrol/pentagi
- **License:** See LICENSE file in repository
