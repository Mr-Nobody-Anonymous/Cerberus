# Integration Record — h4cker

## Original Project
- **Name:** h4cker
- **Repository:** https://github.com/The-Art-of-Hacking/h4cker
- **License:** See LICENSE
- **Vendored as:** `adapters/h4cker/` (plain copy — no nested `.git`)

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator (Cerberus)
- **Local Role:** Security training/research knowledge base (searchable reference)
- **Integration Method:** Documentation search over the vendored tree
- **Adapter Module:** `adapters.h4cker` (registry key: `h4cker`)
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
- `research` — Query CVEs, CWEs, and vulnerability research topics
- `documentation` — Query security training and methodology references

## Health Check Prerequisites
- Adapter directory present
- `README.md` present (the searchable index)

## How To Run
```
# No service to start — the adapter searches the vendored tree:
ls adapters/h4cker
```

## How To Update From Upstream
This is a vendored copy without `.git`, so `git pull` does not work.
To refresh from upstream:
```bash
# from the repository root
rm -rf adapters/h4cker                     # Windows: Remove-Item -Recurse adapters\h4cker
git clone https://github.com/The-Art-of-Hacking/h4cker adapters/h4cker
```
The Cerberus adapter wrapper lives in `adapters/h4cker/__init__.py`;
the upstream tree starts at `adapters/h4cker/h4cker tree at the adapter root`. Re-apply
the wrapper (from git history: `git show HEAD~:adapters/h4cker/__init__.py`)
after re-cloning.

## Attribution
- **Original Repository:** https://github.com/The-Art-of-Hacking/h4cker
- **License:** See LICENSE
