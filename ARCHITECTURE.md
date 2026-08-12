# Cyber AI Orchestrator — Architecture Reference

**Local Autonomous Multi-Agent Security Research Platform**  
Technical deep-dive into directory layout, component map, data flow, and integration methodologies.

---

## Table of Contents

1. [Directory Tree](#directory-tree)
2. [Component Breakdown](#component-breakdown)
3. [Integration Methodologies](#integration-methodologies)
4. [Memory & Learning Schema](#memory--learning-schema)
5. [Model Routing Matrix](#model-routing-matrix)
6. [Data Flow Specifications](#data-flow-specifications)
7. [Security Boundaries](#security-boundaries)

---

## Directory Tree

```
C:\Users\hp\Desktop\cyber/
├── .env.example                          # Environment configuration template
├── .gitignore                            # Git ignore rules (secrets, DB, logs)
├── docker-compose.yml                    # Infrastructure services (LiteLLM, Ollama, Open WebUI)
├── README.md                             # Platform overview and quick start
├── ARCHITECTURE.md                       # This file - technical reference
├── WORKSPACE_INVENTORY.md                # Detailed repository inventory
├── REPOSITORY_MAP.yaml                   # Repository-to-role mapping
├── INTEGRATION_STATUS.md                 # Component status tracking
├── FINAL_STATUS.md                       # Final delivery report
│
├── platform/                             # Core platform code
│   ├── orchestrator/                     # Master orchestrator
│   │   ├── __init__.py                   # Package init, version info
│   │   ├── orchestrator.py               # Master coordinator, session management
│   │   ├── tool_registry.py              # Machine-readable tool catalog
│   │   ├── tools.yaml                    # Tool definitions and capabilities
│   │   │
│   │   ├── agents/                       # AI agent implementations
│   │   │   ├── __init__.py               # Agent package init
│   │   │   ├── base.py                   # BaseAgent class with LLM/tool/memory access
│   │   │   ├── planner/
│   │   │   │   ├── __init__.py           # Exports PlannerAgent
│   │   │   │   └── planner.py            # Planning agent with experience retrieval
│   │   │   ├── researcher/
│   │   │   │   ├── __init__.py           # Exports ResearcherAgent
│   │   │   │   └── researcher.py         # Research and intelligence gathering
│   │   │   ├── recon/
│   │   │   │   ├── __init__.py           # Exports ReconAgent
│   │   │   │   └── recon.py              # Network and host discovery
│   │   │   ├── analyst/
│   │   │   │   ├── __init__.py           # Exports AnalystAgent
│   │   │   │   └── analyst.py            # Finding correlation and pattern analysis
│   │   │   ├── coder/
│   │   │   │   ├── __init__.py           # Exports CoderAgent
│   │   │   │   └── coder.py              # Exploit and PoC generation
│   │   │   ├── verifier/
│   │   │   │   ├── __init__.py           # Exports VerifierAgent
│   │   │   │   └── verifier.py           # Finding verification and evidence challenges
│   │   │   └── reporter/
│   │   │       ├── __init__.py           # Exports ReporterAgent
│   │   │       └── reporter.py           # Report generation
│   │   │
│   │   ├── routing/                      # Routing engines
│   │   │   ├── model_router.py           # Task-to-model alias routing
│   │   │   └── routing.yaml              # Configurable routing rules
│   │   │
│   │   ├── memory/                       # Experience storage
│   │   │   ├── __init__.py
│   │   │   ├── memory_manager.py         # SQLite-backed memory system
│   │   │   └── memory.db                 # SQLite database (auto-created)
│   │   │
│   │   ├── policies/                     # Authorization and safety
│   │   │   ├── __init__.py
│   │   │   └── policy_engine.py          # Target authorization enforcement
│   │   │
│   │   ├── scheduler/                    # Task scheduling
│   │   │   ├── __init__.py
│   │   │   └── scheduler.py              # Async task prioritization and lifecycle
│   │   │
│   │   ├── workflows/                    # Predefined assessment flows
│   │   │   ├── __init__.py
│   │   │   └── workflow_manager.py       # Workflow definitions (recon_to_report, code_audit, etc.)
│   │   │
│   │   ├── api/                          # REST API server
│   │   │   ├── __init__.py
│   │   │   └── api_server.py             # FastAPI endpoints for status, sessions, findings
│   │   │
│   │   ├── evidence/                     # Evidence collection
│   │   │   ├── __init__.py
│   │   │   └── evidence.py               # Evidence storage and retrieval
│   │   │
│   │   ├── knowledge/                    # Knowledge base loader
│   │   │   ├── __init__.py
│   │   │   └── knowledge_loader.py       # CVE/CWE/techniques indexing
│   │   │
│   │   ├── logging/                      # Session logging
│   │   │   └── session_logger.py         # JSONL session logs
│   │   │
│   │   ├── adapters/                     # Adapter framework
│   │   │   ├── __init__.py
│   │   │   ├── base.py                   # SecurityToolAdapter interface
│   │   │   ├── adapter_registry.py       # Adapter loading and management
│   │   │   └── registry.yaml             # Adapter configuration
│   │   │
│   │   └── cli/                          # Command-line interface
│   │       ├── __init__.py
│   │       ├── cli.py                    # Click-based CLI (status, tools, lab, assess, etc.)
│   │       └── doctor.py                 # Health check subsystem
│   │
│   ├── llm-gateway/                      # LiteLLM integration
│   │   ├── __init__.py                   # LLMGateway class
│   │   ├── models/
│   │   │   └── models.yaml               # Model registry (aliases, providers, status)
│   │   ├── config/
│   │   │   └── config.yaml               # LiteLLM proxy configuration
│   │   └── logs/                         # Gateway logs
│   │
│   ├── tool-gateway/                     # MCP tool discovery
│   │   └── mcp/
│   │       ├── __init__.py
│   │       ├── mcp_server.py             # MCPGateway class
│   │       └── mcp_config.json           # MCP server definitions
│   │
│   └── ui/                               # UI package (future expansion)
│       └── __init__.py
│
├── adapters/                             # Security tool adapters (preserved upstream repos)
│   ├── __init__.py                       # Adapters package init
│   │
│   ├── pentagi/                          # PentAGI - Primary autonomous pentesting agent
│   │   ├── INTEGRATION.md                # Integration record
│   │   ├── adapter.py                    # Adapter wrapper
│   │   ├── __init__.py                   # Package init (re-export)
│   │   ├── README.md                     # Original documentation
│   │   ├── LICENSE                       # Original license
│   │   ├── docker-compose.yml            # Original Docker config
│   │   ├── backend/                      # Backend API (Go)
│   │   ├── frontend/                     # Frontend UI (React)
│   │   └── ...                           # All other original files preserved
│   │
│   ├── strix/                            # Strix - Security assessment agent
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   ├── strix/                        # Python package
│   │   └── ...
│   │
│   ├── darkmoon/                         # Dark-Moon - Autonomous pentesting agent (MCP)
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   ├── mcp/                          # MCP server implementation
│   │   └── ...
│   │
│   ├── hexstrike/                        # HexStrike AI - MCP tool gateway (150+ tools)
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   ├── hexstrike_server.py           # Flask REST server
│   │   ├── hexstrike_mcp.py              # MCP server
│   │   └── ...
│   │
│   ├── mcpstrike/                        # MCPStrike - Ollama-driven MCP gateway
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   └── src/mcpstrike/               # Python package
│   │
│   ├── cai/                              # CAI - Cybersecurity AI framework
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   └── src/cai/                      # Python package
│   │
│   ├── pentestgpt/                       # PentestGPT - Research/planning agent
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   └── pentestgpt_legacy/            # Python package
│   │
│   ├── pentestagent/                     # PentestAgent - LiteLLM-based security agent
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   └── pentestagent/                 # Python package
│   │
│   ├── cyberstrikeai/                    # CyberStrikeAI - Gin REST + MCP
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   ├── cmd/                          # Go entry points
│   │   └── ...
│   │
│   ├── autopentest/                      # AutoPentest - LangChain/LangGraph research
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   └── src/                          # Python source
│   │
│   ├── penclaw/                          # PenClaw - Static/dynamic analysis (Node.js)
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   └── dist/                         # Compiled CLI
│   │
│   ├── luan1aoagent/                     # LuaN1aoAgent - Cognitive security agent
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   └── dist/                         # Compiled CLI/Web
│   │
│   ├── aracne/                           # ARACNE - SSH-driven pentesting agent
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   └── aracne.py                     # Main entry point
│   │
│   ├── guardian-cli/                     # Guardian - CLI-based pentesting
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   └── cli/                          # CLI implementation
│   │
│   ├── drakben/                          # DRAKBEN - Autonomous pentesting agent
│   │   ├── INTEGRATION.md
│   │   ├── adapter.py
│   │   ├── __init__.py
│   │   └── drakben.py                    # Main entry point
│   │
│   ├── h4cker/                           # h4cker - Knowledge base (reference)
│   │   ├── README.md                     # Original documentation
│   │   └── ...                           # Documentation and scripts
│   │
│   └── kali-pentest/                     # kali-pentest - Skill definitions (reference)
│       ├── README.md
│       └── ...                           # Skill definitions for AI agents
│
├── infrastructure/                       # Infrastructure services
│   ├── ollama/                           # Ollama local model service
│   │   ├── models/                       # Model storage (gitignored)
│   │   └── config/                       # Ollama configuration
│   ├── open-webui/                       # Open WebUI interface
│   │   └── data/                         # WebUI data storage
│   ├── airllm/                           # AirLLM - Low-VRAM inference
│   │   └── air_llm/                      # Python package
│   └── other-inference/                  # Additional inference engines
│
├── lab/                                  # Isolated lab environment
│   ├── targets/                          # Authorized target registry
│   │   └── targets.yaml                  # Target definitions (id, host, port, actions)
│   ├── docker/                           # Docker Compose stacks
│   │   ├── docker-compose.yml            # Lab-specific compose
│   │   └── Dockerfiles/                  # Custom target images
│   ├── networks/                         # Network definitions
│   │   └── lab-network.yml               # Docker network config
│   ├── snapshots/                        # VM/target snapshots
│   ├── scenarios/                        # Pre-built assessment scenarios
│   │   ├── juice-shop.yml
│   │   └── dvwa.yml
│   └── evidence/                         # Collected evidence files
│       └── .gitkeep
│
├── knowledge/                            # Security knowledge base
│   ├── cve/                              # CVE database files
│   │   └── .gitkeep
│   ├── cwe/                              # CWE weakness taxonomy
│   │   └── .gitkeep
│   ├── advisories/                       # Security advisories
│   │   └── .gitkeep
│   ├── techniques/                       # ATT&CK techniques
│   │   └── .gitkeep
│   ├── research/                         # Security research papers
│   │   └── .gitkeep
│   └── documentation/                    # Tool and technique documentation
│       └── .gitkeep
│
├── memory/                               # Persistent memory
│   ├── memory.db                         # SQLite database (auto-created, gitignored)
│   ├── embeddings/                       # Vector embeddings for semantic search
│   │   └── .gitkeep
│   ├── findings/                         # Individual finding files
│   │   └── .gitkeep
│   ├── failures/                         # Failed strategy records
│   │   └── .gitkeep
│   ├── successful-strategies/            # Successful tactic records
│   │   └── .gitkeep
│   ├── observations/                     # Agent observation logs
│   │   └── .gitkeep
│   └── sessions/                         # Session logs
│       └── .gitkeep
│
├── logs/                                 # Platform logs
│   └── sessions/                         # Per-session execution logs
│       └── .gitkeep
│
├── projects/                             # Additional projects
│   ├── security-agents/                  # Custom security agent implementations
│   ├── research-tools/                   # Research utilities
│   ├── analysis-tools/                   # Analysis scripts
│   └── legacy/                           # Legacy integrations
│
├── scripts/                              # Utility scripts
│   └── generate_platform.py              # Platform generator (creates adapters, modules)
│
├── backups/                              # Backup storage
│   └── .gitkeep
│
└── tests/                                # Test suite
    ├── __init__.py
    └── test_health.py                    # Basic health check tests
```

---

## Component Breakdown

### `platform/orchestrator/`

The brain of the platform. Coordinates agents, routes tasks, manages memory, and enforces policies.

#### Core Modules

| File | Purpose | Key Classes/Functions |
|------|---------|----------------------|
| `orchestrator.py` | Master coordinator | `Orchestrator` - session management, task execution, assessment flow |
| `tool_registry.py` | Tool catalog | `ToolRegistry` - 15 tools registered with capabilities |
| `tools.yaml` | Tool definitions | YAML config for all adapters |

#### Agents (`agents/`)

Seven specialized AI agents, each inheriting from `BaseAgent`:

| Agent | File | Purpose | LLM Task Type |
|-------|------|---------|---------------|
| **Planner** | `planner.py` | Decomposes objectives into steps | `planning` |
| **Researcher** | `researcher.py` | Gathers target intelligence | `vulnerability_research` |
| **Recon** | `recon.py` | Network/host discovery | `web_research` |
| **Analyst** | `analyst.py` | Correlates findings | `reasoning` |
| **Coder** | `coder.py` | Generates exploits/PoC | `code_generation` |
| **Verifier** | `verifier.py` | Challenges findings, requires evidence | `verification` |
| **Reporter** | `reporter.py` | Generates reports | `report_generation` |

**Base Agent Capabilities:**
- `_llm_call()` - Routes through model router to LLM gateway
- `_record_experience()` - Stores outcomes to memory
- Access to: model_router, tool_registry, memory, policy, logger

#### Memory (`memory/`)

SQLite-backed persistent storage with three tables:

```sql
experiences: observation, hypothesis, action, tool, result, evidence, confidence, lessons, score
findings: observation, evidence, status (UNVERIFIED/LIKELY/VERIFIED/REJECTED), confidence, source
sessions: target_id, started_at, ended_at, status, summary
```

**Key Methods:**
- `store_experience()` - Record tactic/result with score
- `search_experiences()` - Keyword search (future: semantic)
- `score_experience()` - Update success/failure score
- `store_finding()` - Record finding with verification status

#### Policies (`policies/`)

Target authorization enforcement:

```yaml
target:
  id: lab-web-01
  environment: authorized_lab
  allowed: true
  allowed_actions: [recon, scan, analysis, exploitation]
```

**Key Methods:**
- `is_authorized(target_id)` - Check if target is registered and allowed
- `check_action_allowed(target_id, action)` - Verify specific action permitted
- `register_target(target)` - Add new authorized target

#### Routing (`routing/`)

Task-to-model alias mapping:

```yaml
planning: local-reasoner
code_analysis: local-coder
classification: local-fast
vulnerability_research: research-model
```

Configurable via `routing.yaml`. Defaults defined in `DEFAULT_ROUTES`.

#### CLI (`cli/`)

Click-based command-line interface:

| Command | Purpose |
|---------|---------|
| `status` | Orchestrator status |
| `models` | List available models |
| `agents` | List agent types |
| `tools` | List tools and adapters |
| `lab list` | List authorized targets |
| `lab start <target>` | Start lab target |
| `assess <target>` | Run assessment |
| `findings` | List findings |
| `memory search <query>` | Search experiences |
| `session list/show` | Session management |
| `doctor` | Health check |

---

### `platform/llm-gateway/`

Unified LLM interface. Routes through LiteLLM proxy when available, falls back to direct provider calls.

#### Model Registry (`models/models.yaml`)

Defines model aliases decoupled from provider-specific names:

```yaml
models:
  local_reasoner:
    provider: ollama
    default_model: llama3.1:8b
    purpose: [reasoning, planning, verification]
    status: REQUIRES_MODEL_DOWNLOAD

  local_coder:
    provider: ollama
    default_model: codellama:7b
    purpose: [code_analysis, code_generation, exploit_development]
    status: REQUIRES_MODEL_DOWNLOAD

  cloud_reasoner:
    provider: openai
    default_model: gpt-4o
    purpose: [complex_reasoning, advanced_planning]
    status: DISABLED_NO_API_KEY
```

#### Gateway Class (`__init__.py`)

`LLMGateway` provides:
- `resolve_model(alias)` - Resolve alias to provider config
- `complete(model_alias, prompt)` - Generate completion
- `list_available_models()` - List registry with status

**Routing Priority:**
1. LiteLLM proxy (if running with API key)
2. Direct Ollama (for ollama provider models)
3. Direct provider API (if API key configured)

---

### `platform/tool-gateway/mcp/`

MCP server discovery and management.

#### MCP Gateway (`mcp_server.py`)

`MCPGateway` discovers MCP servers from:
- Configured definitions in `mcp_config.json`
- Adapter directories (hexstrike, mcpstrike, darkmoon)
- Runtime discovery

**Discovered Servers:**
```python
{
    "hexstrike-mcp": {
        "type": "stdio",
        "command": "python",
        "args": ["hexstrike_mcp.py"],
        "cwd": "adapters/hexstrike/",
        "capabilities": ["tool_execution", "mcp_servers"]
    },
    "mcpstrike-mcp": {
        "type": "stdio",
        "command": "python",
        "args": ["-m", "mcpstrike.server"],
        "cwd": "adapters/mcpstrike/",
        "capabilities": ["tool_execution", "mcp_servers"]
    }
}
```

---

### `adapters/`

Thin wrappers around original repositories. Each adapter:
1. Implements `SecurityToolAdapter` interface
2. Preserves original project files and attribution
3. Provides health check, capabilities, and execution methods
4. Reports status: OK, WARN, ERROR

#### Adapter Categories

**Primary Security Agents (Docker-based):**
| Adapter | Original Project | Capabilities | Integration |
|---------|-----------------|--------------|-------------|
| `pentagi` | PentAGI | research, analysis, exploitation, reporting | REST/GraphQL API |
| `strix` | Strix | assessment, vulnerability_scanning | Server API |
| `darkmoon` | Dark-Moon | research, analysis, exploitation | MCP Server |

**MCP Tool Gateways:**
| Adapter | Original Project | Capabilities | Integration |
|---------|-----------------|--------------|-------------|
| `hexstrike` | HexStrike AI | tool_execution, mcp_servers, web_scraping | Flask REST + MCP |
| `mcpstrike` | MCPStrike | tool_execution, mcp_servers | FastAPI + MCP |

**Agent Frameworks:**
| Adapter | Original Project | Capabilities | Integration |
|---------|-----------------|--------------|-------------|
| `cai` | CAI | research, analysis, agent_framework | Python Library |
| `pentestagent` | PentestAgent | research, analysis, exploitation | CLI + MCP |
| `cyberstrikeai` | CyberStrikeAI | tool_execution, mcp_servers, analysis | Gin REST + MCP |

**Research/Planning:**
| Adapter | Original Project | Capabilities | Integration |
|---------|-----------------|--------------|-------------|
| `pentestgpt` | PentestGPT | research, planning | CLI Wrapper |
| `autopentest` | AutoPentest | research, planning | CLI (LangChain) |

**Analysis Tools:**
| Adapter | Original Project | Capabilities | Integration |
|---------|-----------------|--------------|-------------|
| `penclaw` | PenClaw | static_analysis, dynamic_scanning, secret_detection | CLI (Node.js) |
| `luan1aoagent` | LuaN1aoAgent | research, analysis, planning | CLI/Web (Node.js) |

**Specialized:**
| Adapter | Original Project | Capabilities | Integration |
|---------|-----------------|--------------|-------------|
| `aracne` | ARACNE | research, exploitation, ssh_driven | CLI (Python/SSH) |
| `guardian-cli` | Guardian | research, analysis, reporting | CLI (Python) |
| `drakben` | DRAKBEN | research, analysis, exploitation | CLI (Python/async) |

**Knowledge References:**
| Adapter | Original Project | Purpose | Integration |
|---------|-----------------|---------|-------------|
| `h4cker` | h4cker | Knowledge base (docs, labs) | Documentation |
| `kali-pentest` | kali-pentest | Skill definitions | Documentation |

#### Adapter Interface

All adapters implement `SecurityToolAdapter`:

```python
class SecurityToolAdapter(ABC):
    name: str
    version: str
    description: str

    async def health_check(self) -> Dict[str, Any]:
        """Check if tool/service is available"""

    async def capabilities(self) -> List[AdapterCapability]:
        """Return list of capabilities"""

    async def execute(self, task: Dict[str, Any]) -> AdapterResult:
        """Execute task using underlying tool"""

    async def collect_results(self) -> AdapterResult:
        """Collect results from async execution"""

    async def shutdown(self) -> None:
        """Clean up resources"""
```

---

### `lab/`

Isolated execution environment for authorized targets.

#### Targets (`targets/targets.yaml`)

Registry of authorized lab targets:

```yaml
targets:
  - id: juice-shop
    environment: authorized_lab
    allowed: true
    host: 127.0.0.1
    port: 3000
    description: OWASP Juice Shop
    allowed_actions: [recon, scan, analysis, exploitation]
```

**Policy Enforcement:**
- All targets must be explicitly registered
- `allowed: true` required for active testing
- Actions restricted to `allowed_actions` list
- Unauthorized targets are refused by policy engine

#### Docker (`docker/`)

Docker Compose stacks for lab targets:
- Custom target images
- Network isolation configs
- Volume mappings for evidence

#### Networks (`networks/`)

Docker network definitions:
- `lab-network` - Isolated bridge network
- Custom subnets for target environments
- Traffic isolation rules

#### Snapshots (`snapshots/`)

VM/target snapshots for:
- Clean state restoration
- Pre/post-assessment comparison
- Rollback on failure

#### Scenarios (`scenarios/`)

Pre-built assessment configurations:
- `juice-shop.yml` - OWASP Juice Shop assessment
- `dvwa.yml` - DVWA assessment
- `vulhub.yml` - VulHub scenarios

#### Evidence (`evidence/`)

Collected evidence files:
- Scan outputs
- Tool responses
- Screenshots
- Network captures
- Manual notes

---

### `knowledge/`

Security knowledge base for RAG retrieval.

| Directory | Contents | Format |
|-----------|----------|--------|
| `cve/` | CVE database | JSON, YAML |
| `cwe/` | CWE weakness taxonomy | JSON, YAML |
| `advisories/` | Security advisories | Markdown, JSON |
| `techniques/` | ATT&CK techniques | Markdown, YAML |
| `research/` | Security papers | PDF, Markdown |
| `documentation/` | Tool docs | Markdown |

**Loading:** `KnowledgeBase` class indexes all files on initialization, supports full-text search.

---

### `memory/`

Persistent experience storage.

| Path | Type | Purpose |
|------|------|---------|
| `memory.db` | SQLite | Primary storage (experiences, findings, sessions) |
| `embeddings/` | Directory | Vector embeddings for semantic search |
| `findings/` | Directory | Individual finding JSON files |
| `failures/` | Directory | Failed strategy records |
| `successful-strategies/` | Directory | Successful tactic records |
| `observations/` | Directory | Agent observation logs |
| `sessions/` | Directory | Session log files |

---

### `infrastructure/`

Supporting services.

| Directory | Service | Purpose |
|-----------|---------|---------|
| `ollama/` | Ollama | Local model serving (Llama, CodeLlama, Qwen) |
| `open-webui/` | Open WebUI | Human-facing web interface |
| `airllm/` | AirLLM | Low-VRAM inference alternative |
| `other-inference/` | TGI, vLLM | Additional inference engines |

---

### `gateway/` (Alternative naming)

Some documentation may reference `gateway/` instead of `platform/llm-gateway/`. Both refer to the LiteLLM integration layer.

---

## Integration Methodologies

The orchestrator integrates external tools through adapters using multiple methods:

### 1. REST API (HTTP)

**Tools:** PentAGI, Strix, CyberStrikeAI, HexStrike

**Method:** Direct HTTP calls to tool's REST API

```python
async def _execute_via_api(self, action, target, parameters, health):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{self._api_url}/api/v1/execute",
            json={"action": action, "target": target, "params": parameters},
            headers={"Authorization": f"Bearer {self._api_token}"}
        )
        return resp.json()
```

### 2. MCP Protocol (Model Context Protocol)

**Tools:** Dark-Moon, HexStrike, MCPStrike, PentestAgent, CyberStrikeAI

**Method:** Stdio or SSE MCP server communication

```python
# Via FastMCP client
from fastmcp import Client
client = Client("hexstrike-mcp")
async with client:
    result = await client.call_tool("nmap_scan", {"target": target})
```

### 3. CLI Subprocess

**Tools:** PentestGPT, AutoPentest, PenClaw, LuaN1aoAgent, ARACNE, Guardian-CLI, DRAKBEN

**Method:** Spawn subprocess, capture stdout/stderr

```python
async def _execute_via_cli(self, action, target, parameters):
    cmd = [self._cli_path, action, "--target", target["host"]]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    return {"success": proc.returncode == 0, "output": stdout.decode()}
```

### 4. Docker SDK

**Tools:** PentAGI, Strix, Dark-Moon, CAI, ARACNE, DRAKBEN

**Method:** Python Docker SDK for container management

```python
import docker
client = docker.from_env()
container = client.containers.run(
    "pentagi:latest",
    environment={"OLLAMA_URL": "http://ollama:11434"},
    network="cyberai-net",
    detach=True
)
```

### 5. Python Library

**Tools:** CAI, AirLLM

**Method:** Direct Python import and function calls

```python
from cai.sdk.agents import Agent
agent = Agent(model="ollama/llama3.1:8b")
result = await agent.run("Scan target for open ports")
```

### Integration Priority Matrix

| Method | Latency | Isolation | Complexity | Preferred For |
|--------|---------|-----------|------------|---------------|
| REST API | Low | Medium | Low | Services with HTTP APIs |
| MCP | Low | High | Medium | MCP-native tools |
| CLI | Medium | Low | Low | Simple wrappers |
| Docker | High | Very High | High | Full isolated environments |
| Library | Very Low | None | Medium | Tight integration |

---

## Memory & Learning Schema

### Experience Record Schema

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
    {
      "type": "scan_output",
      "content": "Nmap scan report...",
      "source": "hexstrike"
    }
  ],
  "confidence": 0.9,
  "lessons": ["Always check alternative ports", "HTTP 200 on non-standard port indicates app"],
  "timestamp": "2026-08-11T10:30:00Z",
  "score": 1.0
}
```

### Finding Record Schema

```json
{
  "id": "uuid",
  "session_id": "uuid",
  "target_id": "lab-web-01",
  "observation": "SQL injection vulnerability in login form",
  "evidence": [
    {
      "type": "tool_response",
      "content": "sqlmap identified boolean-based blind injection",
      "source": "pentagi"
    },
    {
      "type": "http_request",
      "content": "POST /login HTTP/1.1...",
      "source": "burp"
    }
  ],
  "status": "VERIFIED",
  "confidence": 0.95,
  "source": "pentagi",
  "timestamp": "2026-08-11T10:45:00Z"
}
```

### Session Record Schema

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

### Scoring Mechanism

- **Success**: +1.0 to +2.0 (dependent on confidence and verification)
- **Partial Success**: +0.5
- **Failure**: -1.0 to -2.0
- **Rejected Finding**: -2.0

**Retrieval:** `search_experiences(query, limit=10)` performs keyword search. Future: vector similarity search using embeddings.

---

## Model Routing Matrix

| Task Type | Model Alias | Provider | Model | Context Window | Best For |
|-----------|-------------|----------|-------|----------------|----------|
| **Planning** | `local-reasoner` | Ollama | llama3.1:8b | 8K | Strategic planning, step decomposition |
| **Reasoning** | `local-reasoner` | Ollama | llama3.1:8b | 8K | Complex analysis, vulnerability correlation |
| **Verification** | `local-reasoner` | Ollama | llama3.1:8b | 8K | Evidence evaluation, finding validation |
| **Code Analysis** | `local-coder` | Ollama | codellama:7b | 16K | Code review, vulnerability identification |
| **Code Generation** | `local-coder` | Ollama | codellama:7b | 16K | Exploit development, PoC generation |
| **Exploit Development** | `local-coder` | Ollama | codellama:7b | 16K | ROP chain construction, shellcode |
| **Classification** | `local-fast` | Ollama | llama3.2:3b | 4K | Quick categorization, routing decisions |
| **Summarization** | `local-fast` | Ollama | llama3.2:3b | 4K | Report summaries, briefings |
| **Tool Selection** | `local-fast` | Ollama | llama3.2:3b | 4K | Adapter selection for tasks |
| **Web Research** | `research-model` | Ollama | qwen2.5:7b | 32K | OSINT, vulnerability research |
| **CVE Analysis** | `research-model` | Ollama | qwen2.5:7b | 32K | CVE analysis, exploitability assessment |
| **Report Generation** | `local-fast` | Ollama | llama3.2:3b | 4K | Final report synthesis |
| **Sensitive Source** | `local-coder` | Ollama | codellama:7b | 16K | Always local for sensitive data |
| **Complex Reasoning** | `cloud-reasoner` | OpenAI | gpt-4o | 128K | Complex analysis (requires API key) |
| **Fast Analysis** | `cloud-fast` | Anthropic | claude-3-5-haiku | 200K | Quick triage (requires API key) |
| **Embeddings** | `embeddings` | Ollama | nomic-embed-text | 8K | Semantic memory retrieval |

**Fallback Strategy:**
1. Try `local-*` alias (Ollama)
2. If Ollama unavailable, try `cloud-*` alias (if API key set)
3. If both fail, return error message to agent

---

## Data Flow Specifications

### Assessment Flow

```
User CLI: cyberai assess juice-shop --objective "Find SQL injection"
    │
    ▼
Orchestrator.assess(target_id, objective)
    │
    ├── 1. PolicyEngine.is_authorized(target_id)
    │   └── Check lab/targets/targets.yaml
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
    │   │   ├── Adapter.health_check()
    │   │   ├── Execute via API/MCP/CLI/Docker
    │   │   └── Return AdapterResult
    │   ├── EvidenceManager.store_evidence()
    │   └── MemoryManager.store_experience()
    │
    ├── 5. VerifierAgent.verify_finding(finding)
    │   ├── Check evidence quality
    │   ├── Update finding status (UNVERIFIED/LIKELY/VERIFIED/REJECTED)
    │   └── MemoryManager.store_finding()
    │
    ├── 6. ReporterAgent.run(task)
    │   └── Generate structured report
    │
    └── 7. Orchestrator.end_session(session_id, summary)
        └── MemoryManager.end_session()
```

### LLM Call Flow

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
    │   └── {provider: "ollama", default_model: "llama3.1:8b", status: "REQUIRES_MODEL_DOWNLOAD"}
    │
    ├── Try LiteLLM proxy (http://localhost:4000)
    │   └── POST /chat/completions {model: "local-reasoner", messages: [...]}
    │
    ├── Fallback: Direct Ollama (http://localhost:11434)
    │   └── POST /api/generate {model: "llama3.1:8b", prompt: "..."}
    │
    └── Return response text
```

### Tool Execution Flow

```
Orchestrator.execute_task(session_id, target_id, tool_name, action, parameters)
    │
    ├── 1. PolicyEngine.is_authorized(target_id)
    │   └── If False: raise PermissionError
    │
    ├── 2. PolicyEngine.check_action_allowed(target_id, action)
    │   └── If False: raise PermissionError
    │
    ├── 3. ToolRegistry.get_tool(tool_name)
    │   └── Return tool config (adapter path, capabilities)
    │
    ├── 4. Load adapter module
    │   └── importlib.import_module(adapter_path)
    │
    ├── 5. Adapter.health_check()
    │   └── Return {status: "OK"/"WARN"/"ERROR", ...}
    │
    ├── 6. Adapter.execute(task)
    │   ├── Check health
    │   ├── Route to appropriate method (API/MCP/CLI/Docker)
    │   └── Return AdapterResult
    │
    ├── 7. Store experience
    │   └── MemoryManager.store_experience({...})
    │
    └── 8. Collect evidence
        └── EvidenceManager.store_evidence(session_id, ...)
```

---

## Security Boundaries

### Target Authorization Model

```
                    ┌──────────────────┐
                    │  EXTERNAL NETWORK │
                    │   (Blocked)      │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  POLICY ENGINE   │
                    │                  │
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
                    │                  │
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

### Evidence Chain

Every action produces audit trail:
1. **Timestamp** - ISO 8601 with timezone
2. **Source** - Tool/adapter name
3. **Action** - What was executed
4. **Parameters** - Input parameters (secrets redacted)
5. **Output** - Tool response
6. **Hash** - SHA256 of output for integrity
7. **Verification** - UNVERIFIED → LIKELY → VERIFIED → REJECTED

### Secret Handling

- API keys never logged
- Credentials redacted from tool output
- `.env` files gitignored
- Secrets stored in environment variables only

---

## Configuration Reference

### Environment Variables (`.env`)

| Variable | Purpose | Default |
|----------|---------|---------|
| `OLLAMA_HOST` | Ollama API endpoint | `http://localhost:11434` |
| `OLLAMA_MODEL` | Default Ollama model | `llama3.1:8b` |
| `LITELLM_MASTER_KEY` | LiteLLM proxy auth | (empty) |
| `LITELLM_PORT` | LiteLLM proxy port | `4000` |
| `OPENAI_API_KEY` | OpenAI API key | (empty) |
| `ANTHROPIC_API_KEY` | Anthropic API key | (empty) |
| `GEMINI_API_KEY` | Google AI API key | (empty) |
| `LAB_TARGETS_PATH` | Targets file path | `lab/targets/targets.yaml` |
| `REQUIRE_TARGET_AUTHORIZATION` | Enforce lab boundary | `true` |

### Model Registry (`platform/llm-gateway/models/models.yaml`)

Defines all available model aliases with provider, model name, purpose, and status.

### Routing Rules (`platform/orchestrator/routing/routing.yaml`)

Maps task types to model aliases. Override defaults here.

---

## Extension Points

### Adding a New Adapter

1. Place repository in `adapters/<name>/`
2. Create `INTEGRATION.md` with attribution and integration details
3. Implement `SecurityToolAdapter` in `adapter.py`
4. Add capabilities to `tool_registry.py` `DEFAULT_TOOLS`
5. Run `python scripts/generate_platform.py` to regenerate wrapper

### Adding a New Agent Type

1. Create `platform/orchestrator/agents/<type>/<type>.py`
2. Inherit from `BaseAgent`
3. Implement `run(task)` method
4. Export in `agents/__init__.py`

### Adding a New Model Provider

1. Add to `platform/llm-gateway/models/models.yaml`
2. Configure in `platform/llm-gateway/config/config.yaml`
3. Set API key in `.env`

---

## Troubleshooting

### Import Error: `'platform' is not a package`

Python stdlib `platform` module conflicts with local `platform/` directory.

**Workaround:** Use direct path imports:
```python
import importlib.util
spec = importlib.util.spec_from_file_location("module", "platform/orchestrator/orchestrator.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
```

**Permanent Fix:** Rename `platform/` to `cyber_platform/` and update all imports.

### Docker Not Installed

Most adapters and infrastructure services require Docker Desktop.

**Install:** https://www.docker.com/products/docker-desktop/

### Ollama Not Running

Start Ollama service:
```bash
ollama serve
```

Pull required models:
```bash
ollama pull llama3.1:8b
ollama pull codellama:7b
```

### No Models Available

Check model registry:
```bash
python -m platform.orchestrator.cli models
```

Ensure models are pulled and Ollama is running.

---

## References

- **LiteLLM Documentation**: https://docs.litellm.ai
- **Ollama Documentation**: https://ollama.com/docs
- **Open WebUI Documentation**: https://docs.openwebui.com
- **MCP Protocol**: https://modelcontextprotocol.io
- **PentAGI**: https://github.com/vxcontrol/pentagi
- **Strix**: https://github.com/usestrix/strix
- **HexStrike AI**: https://github.com/0x4m4/hexstrike-ai

---

**Document Version**: 1.0  
**Last Updated**: 2026-08-11  
**Platform Version**: 0.1.0