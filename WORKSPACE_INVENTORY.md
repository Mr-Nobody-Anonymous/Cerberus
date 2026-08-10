# Cyber AI Orchestrator — Workspace Inventory

**Generated:** 2026-08-10  
**Workspace:** `C:\Users\hp\Desktop\cyber`

This document inventories every repository present in the workspace, documenting its original identity, capabilities, and potential role in the Cyber AI Orchestrator platform.

---

## Environment Summary

| Component | Status |
|-----------|--------|
| OS | Windows 11 |
| Shell | PowerShell |
| Git | 2.49.0.windows.1 |
| Python | 3.10.11 |
| Node.js | 24.18.0 |
| Docker | **NOT INSTALLED** |
| Ollama | **NOT RUNNING** (no response on localhost:11434) |
| GPU | Not detected |

---

## Repository Inventory

### 1. airllm

| Field | Value |
|-------|-------|
| Repository | airllm |
| Original name | airllm |
| Original path | `airllm/` |
| Language | Python |
| Framework | PyTorch / Transformers |
| Entry point | Python library (`air_llm/`) |
| How to run | `pip install -r requirements.txt` |
| API available | No (library) |
| CLI available | No |
| MCP available | No |
| Docker support | No |
| LLM provider | Self (inference engine) |
| Local model support | Yes (runs 70B+ models on low VRAM) |
| Important dependencies | bitsandbytes, transformers, peft, accelerate |
| Potential role | Local inference engine (alternative to Ollama) |
| Git remote | https://github.com/lyogavin/airllm |
| License | Apache 2.0 |
| Current status | Clean, on main branch |

### 2. aracne

| Field | Value |
|-------|-------|
| Repository | aracne |
| Original name | ARACNE |
| Original path | `aracne/` |
| Language | Python |
| Framework | OpenAI SDK, Paramiko |
| Entry point | `aracne.py` |
| How to run | `pip install -r requirements.txt && python aracne.py` |
| API available | No |
| CLI available | Yes |
| MCP available | No |
| Docker support | Yes (Dockerfile, docker-compose.yml) |
| LLM provider | OpenAI / Ollama |
| Local model support | Yes (Ollama) |
| Important dependencies | openai, paramiko, python-dotenv, PyYAML |
| Potential role | SSH-driven pentesting agent adapter |
| Git remote | https://github.com/stratosphereips/aracne |
| License | (LICENSE file present) |
| Current status | Clean, on main branch |

### 3. autopentest

| Field | Value |
|-------|-------|
| Repository | autopentest |
| Original name | AutoPentest |
| Original path | `autopentest/` |
| Language | Python |
| Framework | LangChain / LangGraph |
| Entry point | `src/main.py` |
| How to run | `poetry install && poetry run python src/main.py` |
| API available | No |
| CLI available | Yes |
| MCP available | No |
| Docker support | Yes (Dockerfile) |
| LLM provider | OpenAI (GPT-4o) |
| Local model support | No (OpenAI only) |
| Important dependencies | langchain, langgraph, langchain-openai, pinecone |
| Potential role | Research/planning agent adapter |
| Git remote | https://github.com/JuliusHenke/autopentest |
| License | (LICENSE.md present) |
| Current status | Clean, on main branch |

### 4. CAI

| Field | Value |
|-------|-------|
| Repository | CAI |
| Original name | Cybersecurity AI (CAI) |
| Original path | `CAI/` |
| Language | Python |
| Framework | OpenAI SDK, custom agent framework |
| Entry point | Python library (`src/cai/`) |
| How to run | `pip install -e .` |
| API available | No |
| CLI available | Yes |
| MCP available | Yes (MCP.md docs) |
| Docker support | Yes (Dockerfile, docker-compose.yml) |
| LLM provider | OpenAI / Alias models |
| Local model support | Partial |
| Important dependencies | openai, httpx, pydantic, rich |
| Potential role | Security agent framework adapter |
| Git remote | https://github.com/aliasrobotics/CAI |
| License | Dual MIT + Proprietary |
| Current status | **HAS UNCOMMITTED DELETIONS** (2 files deleted) |

### 5. CyberStrikeAI

| Field | Value |
|-------|-------|
| Repository | CyberStrikeAI |
| Original name | CyberStrikeAI |
| Original path | `CyberStrikeAI/` |
| Language | Go |
| Framework | Eino, Gin, MCP |
| Entry point | `cmd/server/main.go`, `cmd/mcp-stdio/main.go` |
| How to run | `go build ./cmd/server` |
| API available | Yes (Gin REST) |
| CLI available | Yes |
| MCP available | Yes (MCP-native tools) |
| Docker support | No |
| LLM provider | OpenAI-compatible |
| Local model support | Yes (via OpenAI-compatible endpoints) |
| Important dependencies | eino, gin, sqlite3, mcp |
| Potential role | MCP tool gateway / security agent |
| Git remote | https://github.com/Ed1s0nZ/CyberStrikeAI |
| License | (LICENSE present) |
| Current status | **HAS UNCOMMITTED DELETION** (1 file deleted) |

### 6. Dark-Moon

| Field | Value |
|-------|-------|
| Repository | Dark-Moon |
| Original name | Dark-Moon |
| Original path | `Dark-Moon/` |
| Language | Python |
| Framework | Custom agent framework |
| Entry point | `mcp/src/server.py` |
| How to run | Docker compose |
| API available | Yes (MCP server) |
| CLI available | Yes |
| MCP available | Yes (MCP server) |
| Docker support | Yes (docker-compose.yml, dev, gpu variants) |
| LLM provider | Multiple (OpenAI, Anthropic, etc.) |
| Local model support | Yes |
| Important dependencies | (Python, MCP) |
| Potential role | Autonomous pentesting agent adapter |
| Git remote | https://github.com/ASCIT31/Dark-Moon |
| License | GPL v3 |
| Current status | Clean, on master branch |

### 7. drakben

| Field | Value |
|-------|-------|
| Repository | drakben |
| Original name | DRAKBEN |
| Original path | `drakben/` |
| Language | Python |
| Framework | Custom (async) |
| Entry point | `perceive.py`, `reflect.py`, `retrieve.py` |
| How to run | `pip install -r requirements.txt` |
| API available | No |
| CLI available | Yes |
| MCP available | No |
| Docker support | Yes (Dockerfile, docker-compose.yml) |
| LLM provider | Multiple |
| Local model support | Yes |
| Important dependencies | rich, requests, aiohttp, psutil |
| Potential role | Autonomous pentesting agent adapter |
| Git remote | https://github.com/ahmetdrak/drakben |
| License | MIT |
| Current status | Clean, on main branch |

### 8. guardian-cli

| Field | Value |
|-------|-------|
| Repository | guardian-cli |
| Original name | Guardian |
| Original path | `guardian-cli/` |
| Language | Python |
| Framework | Custom CLI |
| Entry point | `cli/main.py` |
| How to run | `pip install -e . && guardian` |
| API available | No |
| CLI available | Yes |
| MCP available | No |
| Docker support | Yes (Dockerfile, docker-compose.yml) |
| LLM provider | OpenAI, Claude, Gemini, OpenRouter |
| Local model support | No |
| Important dependencies | (Python 3.11+) |
| Potential role | CLI-based pentesting adapter |
| Git remote | https://github.com/zakirkun/guardian-cli |
| License | MIT |
| Current status | Clean, on main branch |

### 9. h4cker

| Field | Value |
|-------|-------|
| Repository | h4cker |
| Original name | h4cker |
| Original path | `h4cker/` |
| Language | Multi (docs, scripts) |
| Framework | N/A (knowledge base) |
| Entry point | N/A |
| How to run | N/A (reference material) |
| API available | No |
| CLI available | No |
| MCP available | No |
| Docker support | Yes (example Dockerfiles) |
| LLM provider | N/A |
| Local model support | N/A |
| Important dependencies | N/A |
| Potential role | Knowledge base / reference material |
| Git remote | https://github.com/The-Art-of-Hacking/h4cker |
| License | (LICENSE present) |
| Current status | Clean, on master branch |

### 10. hexstrike-ai

| Field | Value |
|-------|-------|
| Repository | hexstrike-ai |
| Original name | HexStrike AI MCP Agents |
| Original path | `hexstrike-ai/` |
| Language | Python |
| Framework | Flask, FastMCP |
| Entry point | `hexstrike_server.py`, `hexstrike_mcp.py` |
| How to run | `pip install -r requirements.txt && python hexstrike_server.py` |
| API available | Yes (Flask REST) |
| CLI available | Yes |
| MCP available | Yes (MCP server) |
| Docker support | No |
| LLM provider | Multiple |
| Local model support | Yes |
| Important dependencies | flask, fastmcp, requests, selenium |
| Potential role | MCP tool gateway (150+ tools) |
| Git remote | https://github.com/0x4m4/hexstrike-ai |
| License | MIT |
| Current status | Clean, on master branch |

### 11. kali-pentest

| Field | Value |
|-------|-------|
| Repository | kali-pentest |
| Original name | kali-pentest |
| Original path | `kali-pentest/` |
| Language | Multi (skill definitions) |
| Framework | N/A (agent skill) |
| Entry point | N/A |
| How to run | N/A (skill for AI agents) |
| API available | No |
| CLI available | No |
| MCP available | No |
| Docker support | No |
| LLM provider | N/A |
| Local model support | N/A |
| Important dependencies | N/A |
| Potential role | Kali Linux skill definitions for agents |
| Git remote | https://github.com/x-glacier/kali-pentest |
| License | (LICENSE present) |
| Current status | Clean, on main branch |

### 12. litellm

| Field | Value |
|-------|-------|
| Repository | litellm |
| Original name | LiteLLM |
| Original path | `litellm/` |
| Language | Python |
| Framework | FastAPI (proxy server) |
| Entry point | `litellm/proxy/` |
| How to run | `pip install litellm && litellm --config config.yaml` |
| API available | Yes (OpenAI-compatible REST) |
| CLI available | Yes |
| MCP available | Yes (MCP integration) |
| Docker support | Yes (Dockerfile) |
| LLM provider | 100+ providers |
| Local model support | Yes (Ollama, vLLM, etc.) |
| Important dependencies | openai, httpx, fastapi |
| Potential role | **LLM GATEWAY** (core component) |
| Git remote | https://github.com/BerriAI/litellm |
| License | MIT |
| Current status | Clean, on litellm_internal_staging branch |

### 13. LuaN1aoAgent

| Field | Value |
|-------|-------|
| Repository | LuaN1aoAgent |
| Original name | LuaN1aoAgent |
| Original path | `LuaN1aoAgent/` |
| Language | TypeScript / Node.js |
| Framework | Pi SDK, Vite |
| Entry point | `dist/src/cli.js`, `dist/src/web-server.js` |
| How to run | `npm install && npm run build && npm start` |
| API available | Yes (web server) |
| CLI available | Yes |
| MCP available | No |
| Docker support | Yes (Dockerfile) |
| LLM provider | Multiple |
| Local model support | Yes |
| Important dependencies | @earendil-works/pi-coding-agent, TypeScript |
| Potential role | Cognitive security agent adapter |
| Git remote | https://github.com/SanMuzZzZz/LuaN1aoAgent |
| License | AGPL v3 |
| Current status | Clean, on main branch |

### 14. mcpstrike

| Field | Value |
|-------|-------|
| Repository | mcpstrike |
| Original name | mcpstrike |
| Original path | `mcpstrike/` |
| Language | Python |
| Framework | FastMCP, FastAPI |
| Entry point | `src/mcpstrike/server/app.py` |
| How to run | `pip install -e . && mcpstrike` |
| API available | Yes (FastAPI) |
| CLI available | Yes |
| MCP available | Yes (MCP server) |
| Docker support | No |
| LLM provider | Ollama |
| Local model support | Yes (Ollama) |
| Important dependencies | fastmcp, httpx, pydantic, rich |
| Potential role | MCP tool gateway (Ollama-driven) |
| Git remote | https://github.com/ente0/mcpstrike |
| License | MIT |
| Current status | Clean, on main branch |

### 15. ollama

| Field | Value |
|-------|-------|
| Repository | ollama |
| Original name | Ollama |
| Original path | `ollama/` |
| Language | Go |
| Framework | Gin |
| Entry point | `cmd/` |
| How to run | `go build && ./ollama serve` |
| API available | Yes (REST API on :11434) |
| CLI available | Yes |
| MCP available | No |
| Docker support | Yes (Dockerfile) |
| LLM provider | Self (local inference) |
| Local model support | Yes (native) |
| Important dependencies | gin, cobra, sqlite3 |
| Potential role | **LOCAL MODEL SERVICE** (core component) |
| Git remote | https://github.com/ollama/ollama |
| License | (LICENSE present) |
| Current status | Clean, on main branch. **NOT RUNNING** |

### 16. open-webui

| Field | Value |
|-------|-------|
| Repository | open-webui |
| Original name | Open WebUI |
| Original path | `open-webui/` |
| Language | Python + Svelte |
| Framework | FastAPI, SvelteKit |
| Entry point | `backend/main.py` |
| How to run | `pip install -e . && open-webui serve` |
| API available | Yes (REST) |
| CLI available | Yes |
| MCP available | No |
| Docker support | Yes (docker-compose variants) |
| LLM provider | Ollama, OpenAI-compatible |
| Local model support | Yes |
| Important dependencies | fastapi, pydantic, svelte |
| Potential role | **HUMAN-FACING UI** (core component) |
| Git remote | https://github.com/open-webui/open-webui |
| License | (LICENSE present) |
| Current status | Clean, on main branch |

### 17. penclaw

| Field | Value |
|-------|-------|
| Repository | penclaw |
| Original name | PenClaw |
| Original path | `penclaw/` |
| Language | TypeScript / Node.js |
| Framework | Custom CLI |
| Entry point | `dist/cli/index.js` |
| How to run | `npm install && npm run build && penclaw` |
| API available | No |
| CLI available | Yes |
| MCP available | No |
| Docker support | No |
| LLM provider | Multiple |
| Local model support | Yes |
| Important dependencies | Node.js >= 20 |
| Potential role | Static/dynamic analysis tool adapter |
| Git remote | https://github.com/andupetcu/penclaw |
| License | (LICENSE present) |
| Current status | Clean, on main branch |

### 18. pentagi

| Field | Value |
|-------|-------|
| Repository | pentagi |
| Original name | PentAGI |
| Original path | `pentagi/` |
| Language | Go |
| Framework | GraphQL, React |
| Entry point | `backend/cmd/` |
| How to run | Docker compose (recommended) |
| API available | Yes (REST + GraphQL) |
| CLI available | Yes |
| MCP available | Yes (MCP client integration) |
| Docker support | Yes (docker-compose.yml + variants) |
| LLM provider | 10+ providers (OpenAI, Anthropic, Ollama, etc.) |
| Local model support | Yes (Ollama, vLLM) |
| Important dependencies | Go, PostgreSQL, pgvector |
| Potential role | **PRIMARY SECURITY AGENT** (autonomous pentesting) |
| Git remote | https://github.com/vxcontrol/pentagi |
| License | (LICENSE present) |
| Current status | Clean, on main branch |

### 19. pentestagent

| Field | Value |
|-------|-------|
| Repository | pentestagent |
| Original name | PentestAgent |
| Original path | `pentestagent/` |
| Language | Python |
| Framework | LiteLLM, MCP |
| Entry point | `pentestagent/__main__.py` |
| How to run | `pip install -e . && pentestagent` |
| API available | No |
| CLI available | Yes |
| MCP available | Yes (MCP servers config) |
| Docker support | Yes (Dockerfile, docker-compose.yml) |
| LLM provider | LiteLLM-supported (OpenAI, Anthropic, etc.) |
| Local model support | Yes (via LiteLLM) |
| Important dependencies | litellm, mcp |
| Potential role | Security agent adapter (LiteLLM-based) |
| Git remote | https://github.com/GH05TCREW/pentestagent |
| License | MIT |
| Current status | Clean, on main branch |

### 20. pentestgpt

| Field | Value |
|-------|-------|
| Repository | pentestgpt |
| Original name | PentestGPT |
| Original path | `pentestgpt/` |
| Language | Python |
| Framework | Custom agent framework |
| Entry point | `pentestgpt_legacy/main.py` |
| How to run | `pip install -e . && pentestgpt` |
| API available | No |
| CLI available | Yes |
| MCP available | No |
| Docker support | Yes (Dockerfile, docker-compose.yml) |
| LLM provider | OpenAI, Claude |
| Local model support | No |
| Important dependencies | pydantic, pydantic-settings |
| Potential role | Research/planning agent adapter |
| Git remote | https://github.com/greydgl/pentestgpt |
| License | MIT |
| Current status | Clean, on main branch |

### 21. strix

| Field | Value |
|-------|-------|
| Repository | strix |
| Original name | Strix |
| Original path | `strix/` |
| Language | Python |
| Framework | Custom agent framework |
| Entry point | `strix/interface/tui/backend/server.py` |
| How to run | `pip install -e . && strix` |
| API available | Yes (server) |
| CLI available | Yes |
| MCP available | No |
| Docker support | Yes (Dockerfile) |
| LLM provider | Multiple |
| Local model support | Yes |
| Important dependencies | Python >= 3.12 |
| Potential role | Security assessment agent adapter |
| Git remote | https://github.com/usestrix/strix |
| License | Apache 2.0 |
| Current status | Clean, on main branch |

---

## Summary

| Category | Count |
|----------|-------|
| Total repositories | 21 |
| Python-based | 14 |
| Go-based | 4 |
| TypeScript/Node-based | 2 |
| Multi/knowledge | 1 |
| Docker support | 15 |
| MCP support | 8 |
| .env.example present | 10 |
| Clean git status | 19 |
| Uncommitted changes | 2 (CAI, CyberStrikeAI) |

## Key Findings

1. **Docker is NOT installed** — many repos require Docker for full functionality
2. **Ollama is NOT running** — no local models currently available
3. **CAI and CyberStrikeAI have uncommitted deletions** — must preserve before any changes
4. **litellm** is on `litellm_internal_staging` branch (not main)
5. **h4cker** is a knowledge base, not a tool
6. **kali-pentest** is a skill definition, not a standalone tool