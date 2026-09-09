# Cyber AI Orchestrator — Architecture Reference

**Local Autonomous Multi-Agent Security Research Platform**
Technical deep-dive into directory layout, component map, data flow, and integration methodologies.

> **Status:** This document reflects the post-Phase A layout (`platform/` → `cyberai/` rename) verified on 2026-09-03 against `python -m cyberai.orchestrator.cli doctor` (exit 0, 17 tracked adapters, 4 memory tables). For phase history and resolved issues see [INTEGRATION_STATUS.md](./INTEGRATION_STATUS.md). For the pre-rename skeleton see [PHASE2_AUDIT.md](./PHASE2_AUDIT.md).

---

## Table of Contents

1. [Directory Tree](#directory-tree)
2. [Component Breakdown](#component-breakdown)
3. [Integration Methodologies](#integration-methodologies)
4. [Memory & Learning Schema](#memory--learning-schema)
5. [Model Routing Matrix](#model-routing-matrix)
6. [Data Flow Specifications](#data-flow-specifications)
7. [Security Boundaries](#security-boundaries)
8. [Configuration Reference](#configuration-reference)
9. [Extension Points](#extension-points)

---

## Directory Tree

```
C:\Users\hp\Desktop\Cerberus/
├── .env.example                          # Environment configuration template
├── .gitignore                            # Git ignore rules (secrets, DB, logs)
├── docker-compose.yml                    # Infrastructure services (LiteLLM, Ollama, Open WebUI)
├── README.md                             # Platform overview and quick start
├── ARCHITECTURE.md                       # This file - technical reference
├── WORKSPACE_INVENTORY.md                # Detailed repository inventory
├── REPOSITORY_MAP.yaml                   # Repository-to-role mapping
├── INTEGRATION_STATUS.md                 # Component status tracking (source of truth)
├── FINAL_STATUS.md                       # 2026-08-11 baseline report (historical)
├── PHASE2_AUDIT.md                       # Pre-Phase-A audit (historical)
├── pyproject.toml                        # Build metadata + pinned deps
├── requirements.txt                      # Runtime pinned deps
│
├── cyberai/                              # Core platform code (the importable package)
│   ├── __init__.py                       # Re-exports CyberAIOrchestrator facade
│   ├── config.py                         # Central config loader (WORKSPACE_ROOT, resolve_path)
│   ├── task.py                           # Canonical Task object
│   │
│   ├── orchestrator/                     # Master orchestrator + subsystems
│   │   ├── master.py                     # CyberAIOrchestrator facade (top-level entry point)
│   │   ├── orchestrator.py               # Core session/task/assessment flow
│   │   ├── pipeline.py                   # Multi-agent execution pipeline (CyberAIPipeline)
│   │   ├── tool_registry.py              # Machine-readable tool catalog
│   │   ├── tools.yaml                    # Tool definitions and capabilities
│   │   ├── adapters/                     # Adapter framework (base.py, adapter_manager.py)
│   │   ├── agents/                       # AI agent implementations (planner, researcher, ...)
│   │   ├── api/                          # FastAPI REST server
│   │   ├── cli/                          # Click-based CLI (15 commands)
│   │   ├── evidence/                     # Evidence collection
│   │   ├── knowledge/                    # Knowledge base loader
│   │   ├── logging/                      # Structured session logging
│   │   ├── memory/                       # Experience/finding/session storage
│   │   ├── policies/                     # Authorization and safety
│   │   ├── routing/                      # Task→model-alias routing
│   │   ├── scheduler/                    # Task scheduling
│   │   └── workflows/                    # Predefined assessment flows
│   │
│   ├── capabilities/                     # Capability registry (17 capabilities)
│   ├── collaboration/                    # Multi-agent collaboration primitives
│   ├── evolution/                        # Evolution engine + A-Evolve integration
│   ├── llm_gateway/                      # LiteLLM integration (transport fallback chain)
│   ├── meta_learning/                    # Performance tracker / best_for_task() / ranking
│   ├── observability/                    # Structured logging + tracing
│   ├── security/                         # Policy + sandboxing helpers
│   ├── self_improvement/                 # 10-stage self-improvement pipeline
│   ├── tool-gateway/                     # MCP tool discovery (mcp/ subpackage)
│   └── ui/                               # Unified CERBERUS Command Deck (working)
│
├── adapters/                             # Security tool adapters (preserved upstream repos)
│   ├── __init__.py
│   ├── pentagi/   strix/   darkmoon/     # Primary autonomous pentesting agents (Docker)
│   ├── hexstrike/ mcpstrike/             # MCP tool gateways
│   ├── cai/  pentestagent/  cyberstrikeai/  # Agent frameworks
│   ├── pentestgpt/  autopentest/         # Research/planning agents
│   ├── penclaw/  luan1aoagent/           # Node.js analysis tools
│   ├── aracne/  guardian-cli/  drakben/  # Specialized CLI/SSH agents
│   └── h4cker/  kali-pentest/            # Knowledge references (no executable adapter)
│
├── infrastructure/                       # Infrastructure services
│   ├── ollama/                           # Ollama local model service
│   ├── open-webui/                       # Open WebUI interface
│   ├── airllm/                           # Low-VRAM inference (library)
│   └── other-inference/                  # Additional inference engines
│
├── config/                               # Workspace YAML configs (targets, routing, ...)
│
├── lab/                                  # Isolated lab environment
│   ├── targets/targets.yaml              # Authorized target registry
│   ├── docker/                           # Docker Compose stacks
│   ├── networks/                         # Network definitions
│   ├── snapshots/                        # VM/target snapshots
│   ├── scenarios/                        # Pre-built assessment scenarios
│   └── evidence/                         # Collected evidence files
│
├── knowledge/                            # Security knowledge base
│   ├── cve/  cwe/  advisories/
│   ├── techniques/  research/  documentation/
│
├── memory/                               # Persistent memory
│   ├── memory.db                         # SQLite database (auto-created, gitignored)
│   ├── embeddings/  findings/  failures/
│   ├── successful-strategies/  observations/  sessions/
│
├── logs/                                 # Platform logs (sessions/, ...)
│
├── projects/                             # Additional projects (legacy, research, analysis)
│
├── scripts/                              # Utility scripts
│
├── backups/                              # Backup storage
│
└── tests/                                # Test suite
```

> **Note on path layout:** The pre-Phase-A package was named `platform/`, which shadowed Python's stdlib `platform` module. Phase A renamed it to `cyberai/` — see [INTEGRATION_STATUS.md](./INTEGRATION_STATUS.md) "Resolved Issues" #1. Two empty legacy directories (`cyberai/llm-gateway/`, `cyberai/tool-gateway/`) remain after the kebab→snake rename; they are reserved and not part of the active code.

---

## Component Breakdown

### `cyberai/orchestrator/` — The brain

Coordinates agents, routes tasks, manages memory, enforces policies. The top-level facade `cyberai.CyberAIOrchestrator` (re-exported from `cyberai/__init__.py`) lives at `cyberai/orchestrator/master.py`.

#### Core modules

| File | Purpose |
|------|---------|
| `master.py` | `CyberAIOrchestrator` — unified AI entry point |
| `orchestrator.py` | Core session/task/assessment flow |
| `pipeline.py` | `CyberAIPipeline` — multi-agent collaborative pipeline |
| `tool_registry.py` | `ToolRegistry` — 17 tools registered with capabilities |
| `tools.yaml` | Tool definitions (intentionally package-relative) |

#### Agents (`cyberai/orchestrator/agents/`)

Seven specialized AI agents, each inheriting from `BaseAgent`:

| Agent | Purpose | LLM task type |
|-------|---------|---------------|
| **Planner** | Decomposes objectives into steps | `planning` |
| **Researcher** | Gathers target intelligence | `vulnerability_research` |
| **Recon** | Network/host discovery | `web_research` |
| **Analyst** | Correlates findings | `reasoning` |
| **Coder** | Generates exploits/PoC | `code_generation` |
| **Verifier** | Challenges findings, requires evidence | `verification` |
| **Reporter** | Generates reports | `report_generation` |

Each agent calls the gateway through its own `prompts.py` module — prompts are never hardcoded in the gateway.

#### Memory (`cyberai/orchestrator/memory/`)

SQLite-backed persistent storage. Doctor reports **4 tables** (`experiences`, `findings`, `sessions`, plus one performance/meta table). See [Memory & Learning Schema](#memory--learning-schema) for record shapes.

#### Policies (`cyberai/orchestrator/policies/`)

Target authorization enforcement. Doctor reports **4 targets registered, 4 authorized**. Targets are loaded from `lab/targets/targets.yaml` through the central config loader.

#### Routing (`cyberai/orchestrator/routing/`)

Task→model-alias mapping. `routing.yaml` is intentionally package-relative (registry data, not a workspace resource) — the only `Path(__file__)` site in this module, annotated in-code.

#### CLI (`cyberai/orchestrator/cli/`)

Click-based command-line interface with **15 commands**:

| Command | Purpose |
|---------|---------|
| `doctor` | Comprehensive health checks |
| `status` | Full platform status |
| `task` | Run an autonomous assessment |
| `assess` | Legacy alias for `task` |
| `simulate` | Run a complete end-to-end simulation without external dependencies |
| `evolve` | Run the evolutionary strategy engine |
| `tools` | List registered tools |
| `adapters` | List adapters and their health |
| `agents` | List agent types |
| `models` | List models and their health |
| `findings` | List findings from memory |
| `memory` | Search experience memory |
| `session` | Session management commands |
| `lab` | Lab target management commands |
| `ui` | Launch the CERBERUS Command Deck web UI |

#### REST API (`cyberai/orchestrator/api/`)

FastAPI server. Endpoints: `GET /status`, `GET /targets`, `GET /targets/authorized`, `GET /sessions`, `GET /findings`, `GET /memory/search`, `GET /tools`, `GET /models`. See also [INTEGRATION_STATUS.md](./INTEGRATION_STATUS.md) "Core Platform" row "REST API".

#### Adapter framework (`cyberai/orchestrator/adapters/`)

The internal `SecurityToolAdapter` base class (`base.py`) and dynamic loader `AdapterManager` (`adapter_manager.py`), which maintains the `KNOWN_ADAPTERS` metadata and discovers wrappers in `adapters/` at the repo root.

### `cyberai/llm_gateway/` — Unified LLM interface

Routes through LiteLLM proxy when available, falls back to direct Ollama, then to the direct provider API.

- `LLMGateway.complete()` implements **LiteLLM-proxy → direct-Ollama → direct-provider** transport fallback. Each hop is independently timed with structured error logging.
- `LLMGateway.health()` probes both transports and reports per-alias availability.
- `LLMGateway.local_only` provably blocks cloud routes at the gateway level.
- `models/` registry and `config/` are intentionally package-relative (registry data, not workspace resources).

### `cyberai/tool-gateway/mcp/` — MCP discovery

MCP server discovery and management. `mcp_config.json` is intentionally package-relative (default config).

### `adapters/` — Vendor wrappers

18 vendored adapter directories; all 17 tracked adapters expose `SecurityToolAdapter` wrappers implementing `health_check`, `capabilities`, `execute`, `collect_results`, and `shutdown`. The remaining non-wrapped directories are reference material only.

See [WORKSPACE_INVENTORY.md](./WORKSPACE_INVENTORY.md) for per-repository detail.

### `cyberai/evolution/` — Evolution engine

Population, mutation, selection, elite archive, failure memory. Includes A-Evolve integration at `cyberai/evolution/a-evolve/`.

### `cyberai/self_improvement/` — 10-stage pipeline

AI-proposed code improvements flow through: `AI Proposes → Patch Generated → Static Checks → Unit Tests → Security Checks → Benchmark Compare → Human Approval → Git Branch → Apply`. Each applied proposal records its rollback commit.

### `cyberai/capabilities/`, `cyberai/collaboration/`, `cyberai/meta_learning/`, `cyberai/observability/`, `cyberai/security/`, `cyberai/ui/`

Specialized subsystems supporting capability-based routing, multi-agent collaboration, performance tracking, structured logging/tracing, policy + sandboxing helpers, and the unified web UI respectively.

---

## Integration Methodologies

The orchestrator integrates external tools through adapters using multiple methods. The `KNOWN_ADAPTERS` registry in `cyberai/orchestrator/adapters/adapter_manager.py` records which method each adapter uses.

### 1. REST API (HTTP)

**Tools:** PentAGI, Strix, CyberStrikeAI, HexStrike

```python
async with httpx.AsyncClient() as client:
    resp = await client.post(
        f"{self._api_url}/api/v1/execute",
        json={"action": action, "target": target, "params": parameters},
        headers={"Authorization": f"Bearer {self._api_token}"},
    )
    return resp.json()
```

### 2. MCP Protocol

**Tools:** Dark-Moon, HexStrike, MCPStrike, PentestAgent, CyberStrikeAI

```python
from fastmcp import Client
client = Client("hexstrike-mcp")
async with client:
    result = await client.call_tool("nmap_scan", {"target": target})
```

### 3. CLI Subprocess

**Tools:** PentestGPT, AutoPentest, PenClaw, LuaN1aoAgent, ARACNE, Guardian-CLI, DRAKBEN

```python
proc = await asyncio.create_subprocess_exec(
    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
)
stdout, stderr = await proc.communicate()
```

### 4. Docker SDK

**Tools:** PentAGI, Strix, Dark-Moon, CAI, ARACNE, DRAKBEN

```python
import docker
client = docker.from_env()
container = client.containers.run(
    "pentagi:latest",
    environment={"OLLAMA_URL": "http://ollama:11434"},
    network="cyberai-net",
    detach=True,
)
```

### 5. Python Library

**Tools:** CAI, AirLLM

```python
from cai.sdk.agents import Agent
agent = Agent(model="ollama/llama3.1:8b")
result = await agent.run("Scan target for open ports")
```

### Integration priority matrix

| Method | Latency | Isolation | Complexity | Preferred for |
|--------|---------|-----------|------------|---------------|
| REST API | Low | Medium | Low | Services with HTTP APIs |
| MCP | Low | High | Medium | MCP-native tools |
| CLI | Medium | Low | Low | Simple wrappers |
| Docker | High | Very High | High | Full isolated environments |
| Library | Very Low | None | Medium | Tight integration |

---

## Memory & Learning Schema

### Experience record

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "target_id": "lab-web-01",
  "target_type": "authorized_lab",
  "environment": "authorized_lab",
  "observation": "Port 8080 responded with HTTP 200",
  "hypothesis": "Web application running on port 8080",
  "action": "nmap_scan",
  "tool": "hexstrike",
  "result": "success",
  "evidence": [
    {"type": "scan_output", "content": "Nmap scan report...", "source": "hexstrike"}
  ],
  "confidence": 0.9,
  "lessons": ["Always check alternative ports"],
  "timestamp": "2026-08-11T10:30:00Z",
  "score": 1.0
}
```

### Finding record

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "target_id": "lab-web-01",
  "observation": "SQL injection vulnerability in login form",
  "evidence": [
    {"type": "tool_response", "content": "sqlmap identified boolean-based blind injection", "source": "pentagi"},
    {"type": "http_request", "content": "POST /login HTTP/1.1...", "source": "burp"}
  ],
  "status": "VERIFIED",
  "confidence": 0.95,
  "source": "pentagi",
  "timestamp": "2026-08-11T10:45:00Z"
}
```

### Session record

```json
{
  "id": "uuid",
  "target_id": "lab-web-01",
  "started_at": "2026-08-11T10:00:00Z",
  "ended_at": "2026-08-11T11:00:00Z",
  "status": "completed",
  "summary": "Assessment found 3 vulnerabilities: SQL injection, XSS, CSRF"
}
```

### Scoring

- **Success**: +1.0 to +2.0 (dependent on confidence and verification)
- **Partial success**: +0.5
- **Failure**: -1.0 to -2.0
- **Rejected finding**: -2.0

**Retrieval:** `search_experiences(query, limit=10)` performs keyword search today; semantic search is staged behind the embeddings alias.

---

## Model Routing Matrix

| Task type | Model alias | Provider | Model | Best for |
|-----------|-------------|----------|-------|----------|
| **Planning** | `local-reasoner` | Ollama | llama3.1:8b | Strategic planning, step decomposition |
| **Reasoning** | `local-reasoner` | Ollama | llama3.1:8b | Complex analysis, vulnerability correlation |
| **Verification** | `local-reasoner` | Ollama | llama3.1:8b | Evidence evaluation, finding validation |
| **Code analysis** | `local-coder` | Ollama | codellama:7b | Code review, vulnerability identification |
| **Code generation** | `local-coder` | Ollama | codellama:7b | Exploit development, PoC generation |
| **Exploit development** | `local-coder` | Ollama | codellama:7b | ROP chain construction, shellcode |
| **Classification** | `local-fast` | Ollama | llama3.2:3b | Quick categorization, routing decisions |
| **Summarization** | `local-fast` | Ollama | llama3.2:3b | Report summaries, briefings |
| **Tool selection** | `local-fast` | Ollama | llama3.2:3b | Adapter selection for tasks |
| **Web research** | `research-model` | Ollama | qwen2.5:7b | OSINT, vulnerability research |
| **CVE analysis** | `research-model` | Ollama | qwen2.5:7b | CVE analysis, exploitability assessment |
| **Report generation** | `local-fast` | Ollama | llama3.2:3b | Final report synthesis |
| **Sensitive source** | `local-coder` | Ollama | codellama:7b | Always local for sensitive data |
| **Complex reasoning** | `cloud-reasoner` | OpenAI | gpt-4o | Complex analysis (requires API key) |
| **Fast analysis** | `cloud-fast` | Anthropic | claude-3-5-haiku | Quick triage (requires API key) |
| **Embeddings** | `embeddings` | Ollama | nomic-embed-text | Semantic memory retrieval |

**Fallback strategy (implemented in `cyberai/llm_gateway/`):**
1. Try LiteLLM proxy (`http://localhost:4000`)
2. Fall back to direct Ollama (`http://localhost:11434`)
3. Fall back to direct provider API (if API key set)
4. If `local_only` is true, cloud routes are blocked at the gateway level (tested).

---

## Data Flow Specifications

### Assessment flow

```
User CLI: cyberai task juice-shop --objective "Find SQL injection"
    │
    ▼
CyberAIOrchestrator.run(objective)
    │
    ├── 1. PolicyEngine.is_authorized(target_id)
    │   └── Reads lab/targets/targets.yaml via resolve_path()
    │
    ├── 2. MemoryManager.create_session(target_id)
    │   └── Insert session record, return session_id
    │
    ├── 3. PlannerAgent.run(task)
    │   ├── ModelRouter.route("planning") → "local-reasoner"
    │   ├── LLMGateway.complete("local-reasoner", prompt)
    │   ├── MemoryManager.search_experiences(objective)
    │   └── Return plan with steps
    │
    ├── 4. For each plan step:
    │   ├── ToolRegistry.get_tools_by_capability(action)
    │   ├── Adapter.execute(task)
    │   ├── EvidenceManager.store_evidence()
    │   └── MemoryManager.store_experience()
    │
    ├── 5. VerifierAgent.verify_finding(finding)
    │   └── Update finding status (UNVERIFIED/LIKELY/VERIFIED/REJECTED)
    │
    ├── 6. ReporterAgent.run(task)
    │   └── Generate structured report
    │
    └── 7. Orchestrator.end_session(session_id, summary)
```

### LLM call flow

```
Agent._llm_call(prompt, task_type="planning")
    │
    ▼
ModelRouter.route("planning")
    └── Returns: "local-reasoner"
    │
    ▼
LLMGateway.complete("local-reasoner", prompt)
    │
    ├── resolve_model("local-reasoner")
    │   └── {provider: "ollama", default_model: "llama3.1:8b"}
    │
    ├── Try LiteLLM proxy (http://localhost:4000)
    │   └── POST /chat/completions
    │
    ├── Fallback: Direct Ollama (http://localhost:11434)
    │   └── POST /api/generate
    │
    └── Fallback: Direct provider API (if API key configured)
```

### Tool execution flow

```
Orchestrator.execute_task(session_id, target_id, tool_name, action, parameters)
    │
    ├── 1. PolicyEngine.is_authorized(target_id)
    ├── 2. PolicyEngine.check_action_allowed(target_id, action)
    ├── 3. ToolRegistry.get_tool(tool_name)
    ├── 4. Load adapter module via registry
    ├── 5. Adapter.health_check()
    ├── 6. Adapter.execute(task)
    ├── 7. MemoryManager.store_experience()
    └── 8. EvidenceManager.store_evidence(session_id, ...)
```

---

## Security Boundaries

### Target authorization model

```
                    ┌──────────────────┐
                    │  EXTERNAL NETWORK │
                    │   (Blocked)      │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  POLICY ENGINE   │
                    │  (cyberai/security/) │
                    │  Check:          │
                    │  1. Target in    │
                    │     targets.yaml │
                    │  2. allowed: true│
                    │  3. Action in    │
                    │     allowed_actions│
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   LAB NETWORK    │
                    │   (Isolated)     │
                    │  ┌────────────┐ │
                    │  │   Docker   │ │
                    │  │   Targets  │ │
                    │  └────────────┘ │
                    │  ┌────────────┐ │
                    │  │   VMs      │ │
                    │  └────────────┘ │
                    │  ┌────────────┐ │
                    │  │   CTFs     │ │
                    │  └────────────┘ │
                    └──────────────────┘
```

### Evidence chain

Every action produces an audit trail:
1. **Timestamp** — ISO 8601 with timezone
2. **Source** — tool/adapter name
3. **Action** — what was executed
4. **Parameters** — input parameters (secrets redacted)
5. **Output** — tool response
6. **Hash** — SHA256 of output for integrity
7. **Verification** — `UNVERIFIED → LIKELY → VERIFIED → REJECTED`

### Secret handling

- API keys never logged
- Credentials redacted from tool output
- `.env` files gitignored
- Secrets stored in environment variables only

---

## Configuration Reference

### Workspace-root resolution (`cyberai/config.py`)

The single source of truth for paths:

1. `CERBERUS_HOME` env var (when set, must be an existing directory)
2. Repository root: parent of the `cyberai/` package

Use `from cyberai.config import resolve_path` everywhere; the only `Path(__file__)` sites are the bootstrap fallback in `config.py` itself and a handful of intentionally package-relative registry data files (`routing.yaml`, `tools.yaml`, `mcp_config.json`, `ui/static`) — each annotated in-code. See [INTEGRATION_STATUS.md](./INTEGRATION_STATUS.md) Phase A path audit table.

### Environment variables (`.env`)

| Variable | Purpose | Default |
|----------|---------|---------|
| `CERBERUS_HOME` | Workspace root override | (repo root) |
| `OLLAMA_HOST` | Ollama API endpoint | `http://localhost:11434` |
| `OLLAMA_MODEL` | Default Ollama model | `llama3.1:8b` |
| `LITELLM_MASTER_KEY` | LiteLLM proxy auth | (empty) |
| `LITELLM_PORT` | LiteLLM proxy port | `4000` |
| `OPENAI_API_KEY` | OpenAI API key | (empty) |
| `ANTHROPIC_API_KEY` | Anthropic API key | (empty) |
| `GEMINI_API_KEY` | Google AI key | (empty) |
| `LAB_TARGETS_PATH` | Targets file path | `lab/targets/targets.yaml` |
| `REQUIRE_TARGET_AUTHORIZATION` | Enforce lab boundary | `true` |

### Model registry

`cyberai/llm_gateway/models/models.yaml` — defines every alias with provider, model name, purpose, status.

### Routing rules

`cyberai/orchestrator/routing/routing.yaml` — maps task types to model aliases. Override defaults here.

### Targets

`lab/targets/targets.yaml` — registered authorized targets. Resolved through `resolve_path()`.

---

## Extension Points

### Adding a new adapter

1. Place repository in `adapters/<name>/`
2. Create `INTEGRATION.md` with attribution and integration details
3. Implement `SecurityToolAdapter` in `adapter.py`
4. Add capabilities to `cyberai/orchestrator/adapters/registry.yaml`

### Adding a new agent type

1. Create `cyberai/orchestrator/agents/<type>/<type>.py`
2. Inherit from `BaseAgent`
3. Implement `run(task)` method
4. Export in `agents/__init__.py`

### Adding a new model provider

1. Add to `cyberai/llm_gateway/models/models.yaml`
2. Configure in `cyberai/llm_gateway/config/config.yaml`
3. Set API key in `.env`
