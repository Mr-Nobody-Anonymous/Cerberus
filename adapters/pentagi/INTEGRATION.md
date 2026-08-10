# Integration Record — PentAGI

## Original Project
- **Name:** PentAGI
- **Repository:** https://github.com/vxcontrol/pentagi
- **Version/Commit:** (as cloned, main branch)
- **License:** See LICENSE file in repository

## Local Platform Integration
- **Local Platform Name:** Cyber AI Orchestrator
- **Local Role:** Primary security agent (autonomous penetration testing)
- **Integration Method:** Adapter (REST/GraphQL API)

## Changes Made
- No source code modifications. Repository preserved as-is.
- Local directory renamed from `pentagi` to `adapters/pentagi` for platform organization.

## How To Run
```bash
# Requires Docker (not currently installed on this system)
cd adapters/pentagi
cp .env.example .env
# Configure LLM providers in .env
docker compose up -d
# Access at https://localhost:8443
```

## How To Update From Upstream
```bash
cd adapters/pentagi
git pull origin main
```

## Attribution
- **Original Author:** vxcontrol
- **Original Repository:** https://github.com/vxcontrol/pentagi
- **License:** See LICENSE file

## Integration Status
- **Status:** NOT_TESTED (Docker not installed)
- **API Available:** Yes (REST + GraphQL)
- **MCP Available:** Yes (client integration)
- **Local Model Support:** Yes (Ollama, vLLM)