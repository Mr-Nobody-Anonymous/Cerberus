<div align="center">
  <img src="ult.jpg" alt="ULTRONE Battlefield AI" width="600"/>
</div>

# ⚡ CERBERUS - Self-Evolving Multi-Agent Cyber AI Orchestrator

> **An autonomous, self-improving security research platform coordinating specialized AI agents across local labs**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/Mr-Nobody-Anonymous/Cerberus/actions/workflows/ci.yml/badge.svg)](https://github.com/Mr-Nobody-Anonymous/Cerberus/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![AI Powered](https://img.shields.io/badge/AI-Powered-purple.svg)](https://github.com/Mr-Nobody-Anonymous/Cerberus)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![Evolution](https://img.shields.io/badge/Self--Evolution-Genetic%20Algorithms-orange.svg)](https://github.com/Mr-Nobody-Anonymous/Cerberus)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-red.svg)](https://modelcontextprotocol.io/)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20%7C%20LiteLLM-8A2BE2.svg)](https://ollama.com/)

---

## 🌟 What Makes CERBERUS Different?

Unlike traditional security platforms, **CERBERUS thinks and evolves**. Every engagement feeds back into a collective intelligence mesh—strategies mutate, fitness scores update, elite tactics are archived, and failures teach the system what to avoid. The platform coordinates specialized AI agents through a master orchestrator, routing tasks to appropriate tools and models while maintaining strict lab isolation.

```
🧬 INTELLIGENCE BECOMES STRENGTH 🧬
```

---

## 🚀 Core Capabilities

### 🧬 **Evolutionary Combat Engine**
- Tactical strategies mutate in real-time based on assessment performance
- Combinatorial strategy generation: `RECON + ANALYSIS → VERIFIED FINDING`
- Automatic adaptation when threat patterns change
- **Population Management**: Successful strategies breed; failures are recorded and avoided
- **Elite Archive**: Best-of-generation strategies persist across sessions
- **Coevolution**: Red Force counter-evolves alongside Blue, creating an adversarial arms race
- **A-Evolve Integration**: Universal infrastructure for self-improving agents (`cyberai/evolution/a-evolve/`)

### 🤖 **Specialized AI Agents**
Each capability has its own AI specialist coordinated by the Master Orchestrator:

| Agent | Role | Capability | Specialty |
|-------|------|-----------|-----------|
| 🧠 **Planner** | Decomposes objectives into actionable steps | `planning` | Mission planning, strategy selection |
| 🔍 **Researcher** | Gathers intelligence on targets | `research` | Threat intelligence, CVE analysis |
| 🛰️ **Recon** | Network and host discovery | `reconnaissance` | Port scanning, service enumeration |
| 📊 **Analyst** | Correlates findings, identifies patterns | `analysis` | Vulnerability pattern recognition |
| 💻 **Coder** | Generates exploits and PoC code | `code_generation` | Exploit development, code analysis |
| ✅ **Verifier** | Challenges findings, requires evidence | `verification` | Independent verification, evidence validation |
| 📋 **Reporter** | Generates structured reports | `reporting` | Assessment reporting, documentation |

### ⚡ **Capability-Based Routing**
Instead of hard-coding which tool to use, CERBERUS reasons in **capabilities**:

| Capability | Top Providers |
|-----------|---------------|
| **Reconnaissance** | Strix → PentAGI → Recon Agent |
| **Source Analysis** | CAI → local-coder → Analyst Agent |
| **Web Testing** | Dark-Moon → PentAGI |
| **Tool Execution** | HexStrike → MCPStrike |
| **Research** | PentestGPT → Researcher Agent |
| **Planning** | Planner Agent → local-reasoner model |
| **Verification** | Verifier Agent → local-reasoner model |
| **Exploitation** | PentAGI → Dark-Moon |
| **Static Analysis** | PenClaw → CAI |
| **Secret Detection** | PenClaw |
| **Dynamic Scanning** | PenClaw → Strix |

The orchestrator asks *"I need reconnaissance"* and the registry returns the best available providers.

### 🧠 **Meta-Learning Performance Tracker**
- **SQLite-backed** performance database tracking every model, agent, tool, and strategy call
- **Adaptive Routing**: The system learns which entity performs best for each task type
- **Success Rate Tracking**: `best_for_task()` finds the optimum provider per capability
- **Ranking Engine**: `ranking_for_task()` provides ranked provider lists
- **Quality Scoring**: Latency, verification status, and quality metrics per entity

### 🔄 **Self-Improvement Pipeline**
AI-proposed code improvements flow through a controlled gatekeeper:

```
AI Proposes → Patch Generated → Static Checks → Unit Tests →
Security Checks → Benchmark Compare → Human Approval → Git Branch → Apply
```

- **10-stage validation**: The AI *cannot* directly modify production code
- **Static checks**: Python syntax validation on all changed files
- **Security checks**: Blocks dangerous patterns (`os.system`, `eval`, `exec`, etc.)
- **Benchmark gating**: Accepted only if it beats or preserves the baseline score
- **Git-based rollback**: Every applied proposal records its rollback commit
- **Proposal lifecycle**: `PENDING → VALIDATED → APPROVED → APPLIED → ROLLED_BACK`

### 🤝 **Agent Collaboration Pipeline**
- **Sequential orchestration**: Researcher → Recon → Analyst → Verifier → Reporter
- **Context filtering**: Each agent receives only relevant context, not every previous output
- **Bloat prevention**: Prevents context window overflow in long assessments
- **Failure isolation**: One agent's failure doesn't kill the pipeline

### 🎛️ **Human-in-the-Loop API**
- FastAPI REST server for live operational command
- `GET /status` — Platform health and metrics
- `GET /targets` — List registered targets
- `GET /targets/authorized` — List authorized targets
- `GET /sessions` — Session management
- `GET /findings` — Retrieve findings by verification status
- `GET /memory/search` — Semantic memory search
- `GET /tools` — Tool registry listing
- `GET /models` — Model routing table

### 🛡️ **Policy & Safety Engine**
- **Target Authorization**: All active testing requires explicit target registration in `lab/targets/targets.yaml` with `allowed: true`
- **Environment Enforcement**: The policy engine blocks execution on unregistered targets
- **Action Whitelisting**: Per-target `allowed_actions` control what operations are permitted
- **Lab-Only Default**: No tools execute against the host system or external networks by default
- **Evidence Retention**: All actions logged with timestamps, tool outputs, and verification status

### 🔫 **F2T2EA Kill Chain Management**
- Full **Find → Fix → Track → Target → Engage → Assess** state machine
- Phase timeout and success/failure tracking per target
- Concurrent multi-target engagement coordination
- **Verification states**: `UNVERIFIED → LIKELY → VERIFIED` or `REJECTED`

### 📡 **Multi-Model LLM Gateway**
- **Local Models**: Ollama serves quantized models (Llama 3.1, CodeLlama, Qwen, etc.) for offline operation
- **Cloud Models**: LiteLLM gateway routes to OpenAI, Anthropic, Google, AWS Bedrock, and 100+ providers
- **Model Aliases**: Agents use abstract aliases (`local-reasoner`, `local-coder`, `research-model`) decoupled from specific model names
- **Fallback Chain**: LiteLLM proxy → Direct Ollama → Direct provider API
- **Privacy Enforcement**: `local_only` mode blocks all cloud calls

### 👻 **Ghost Wargaming & Failure Learning**
- **Failure Memory**: Every failed strategy is recorded with its reason and category
- **Avoidance Logic**: Similar-to-failed strategies are skipped automatically
- **Failure Analytics**: Query failures by tool or category
- **Fast-forward simulation**: Test evolved strategies in `simulate` mode

---

## 🏗️ Master Architecture

```
                         ┌─────────────────┐
                         │   USER / CLI    │
                         │  Open WebUI     │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  MASTER         │
                         │  ORCHESTRATOR   │
                         │  (CyberAI)      │
                         │                 │
                         │  ┌────────────┐ │
                         │  │  Planner   │ │
                         │  └────────────┘ │
                         │  ┌────────────┐ │
                         │  │ Researcher │ │
                         │  └────────────┘ │
                         │  ┌────────────┐ │
                         │  │  Recon     │ │
                         │  └────────────┘ │
                         │  ┌────────────┐ │
                         │  │  Analyst   │ │
                         │  └────────────┘ │
                         │  ┌────────────┐ │
                         │  │   Coder    │ │
                         │  └────────────┘ │
                         │  ┌────────────┐ │
                         │  │  Verifier  │ │
                         │  └────────────┘ │
                         │  ┌────────────┐ │
                         │  │  Reporter  │ │
                         │  └────────────┘ │
                         └────────┬────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
┌────────▼─────────┐   ┌──────────▼─────────┐   ┌──────────▼─────────┐
│  CAPABILITY      │   │  LLM GATEWAY       │   │  TOOL GATEWAY      │
│  REGISTRY        │   │  (Ollama/LiteLLM)  │   │  (MCP / Adapters)  │
│                  │   │                    │   │                    │
│  reconnaissance  │   │  Model Aliases:    │   │  Adapters:          │
│  source_analysis │   │  - local-reasoner  │   │  - PentAGI          │
│  web_testing     │   │  - local-coder     │   │  - Strix            │
│  tool_execution  │   │  - local-fast      │   │  - HexStrike        │
│  research        │   │  - research-model  │   │  - MCPStrike        │
│  planning        │   │  - cloud-reasoner  │   │  - Dark-Moon        │
│  verification    │   │  - embeddings      │   │  - CAI              │
│  code_generation │   │                    │   │  - PentestGPT       │
│  analysis        │   │  Providers:        │   │  - PentestAgent     │
│  reporting       │   │  - Ollama (local)  │   │  - CyberStrikeAI    │
│  exploitation    │   │  - OpenAI (cloud)  │   │  - AutoPentest      │
│  static_analysis │   │  - Anthropic       │   │  - PenClaw          │
│  secret_detection│   │  - Custom          │   │  - LuaN1aoAgent     │
│  dynamic_scanning│   │                    │   │  - ARACNE           │
└──────────────────┘   └────────────────────┘   │  - Guardian-CLI     │
         │                        │             │  - DRAKBEN          │
         │                        │             │  - h4cker (KB)      │
         │                        │             │  - kali-pentest     │
         │                        │             └──────────┬─────────┘
         │                        │                        │
┌────────▼─────────┐   ┌──────────▼─────────┐   ┌──────────▼─────────┐
│  EVOLUTION       │   │  META-LEARNING     │   │  SELF-IMPROVEMENT  │
│  ENGINE          │   │  TRACKER           │   │  PIPELINE          │
│                  │   │                    │   │                    │
│  Population      │   │  SQLite-backed     │   │  Proposals         │
│  Mutation        │   │  performance.db    │   │  Static Checks     │
│  Selection       │   │  best_for_task()   │   │  Unit Tests        │
│  Evaluation      │   │  ranking_for_task()│   │  Security Checks   │
│  Fitness         │   │  success_rate      │   │  Benchmark Gate    │
│  Elite Archive   │   │  avg_latency       │   │  Human Approval    │
│  Failure Memory  │   │  quality_score     │   │  Git Branch/Rollback│
└──────────────────┘   └────────────────────┘   └────────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                    ┌──────────────▼──────────────┐
                    │      AUTHORIZED LAB         │
                    │   ┌─────────────────────┐   │
                    │   │  Docker Targets     │   │
                    │   └─────────────────────┘   │
                    │   ┌─────────────────────┐   │
                    │   │  VM Targets         │   │
                    │   └─────────────────────┘   │
                    │   ┌─────────────────────┐   │
                    │   │  CTF Challenges     │   │
                    │   └─────────────────────┘   │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   EVIDENCE & MEMORY         │
                    │   ┌─────────────────────┐   │
                    │   │  SQLite DB          │   │
                    │   │  (experiences,      │   │
                    │   │   findings,         │   │
                    │   │   sessions,         │   │
                    │   │   performance)      │   │
                    │   └─────────────────────┘   │
                    │   ┌─────────────────────┐   │
                    │   │  Evolution Archive  │   │
                    │   │  (elite, failures,  │   │
                    │   │   population)       │   │
                    │   └─────────────────────┘   │
                    │   ┌─────────────────────┐   │
                    │   │  Knowledge Base     │   │
                    │   │  (CVE, CWE,         │   │
                    │   │   techniques)       │   │
                    │   └─────────────────────┘   │
                    └─────────────────────────────┘
```

---

## 🔄 The Evolution Loop

Every engagement feeds back into the evolutionary engine:

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────┐    ┌────────┐
│  Solve  │───▶│ Observe │───▶│ Evolve  │───▶│ Gate │───▶│ Reload │
└─────────┘    └─────────┘    └─────────┘    └──────┘    └────────┘
```

1. **Solve** — Agents process tasks (black-box execution in the lab)
2. **Observe** — Trajectories + benchmark feedback collected into structured logs
3. **Evolve** — Evolution engine mutates strategies (prompts, skills, memory)
4. **Gate** — Validate mutations; regressed strategies are rolled back
5. **Reload** — The system reloads with the (possibly rolled-back) workspace

Every accepted mutation is git-tagged (`evo-1`, `evo-2`, …) providing a full audit trail.

### Fitness Function
```
Success:            +1.0
Verification:       +0.8
Evidence Quality:   +0.6
Repeatability:      +0.5
Unnecessary Actions: -0.3
Failures:           -0.5
```

---

## 🧩 Non-Weight Learning Loop

```
Hypothesis → Execution → Sandbox Verification → Memory Storage
     │              │                │                  │
     │              │                │                  ▼
     │              │                │          Score: +1 (success)
     │              │                │          Score: -1 (failure)
     │              │                │                  │
     └──────────────┴────────────────┴──────────────────┘
                    Future Planning Retrieves Relevant Experiences
```

- **No model weight retraining**: Underlying LLM weights remain stable
- **Scored experiences**: Successful strategies gain positive scores; failures lose points
- **Semantic retrieval**: Vector embeddings enable similarity search for relevant past experiences
- **Pattern recognition**: The planner retrieves top-K similar past scenarios before generating new plans

---

## 🗂️ Project Structure

```
CERBERUS/
├── README.md                    # This file
├── ARCHITECTURE.md              # Deep-dive technical reference
├── WORKSPACE_INVENTORY.md       # Detailed repository inventory
├── REPOSITORY_MAP.yaml          # Repository-to-role mapping
├── INTEGRATION_STATUS.md        # Component status tracking
├── FINAL_STATUS.md              # Final delivery report
├── PHASE2_AUDIT.md              # Phase 2 audit report
├── .env.example                 # Environment configuration template
├── .gitignore                   # Git ignore rules
├── docker-compose.yml           # Infrastructure services
├── ult.jpg                      # Platform banner image
│
├── cyberai/                     # Core platform package
│   ├── __init__.py
│   ├── config.py                # Central configuration loader
│   ├── task.py                  # Canonical Task state (shared across components)
│   │
│   ├── capabilities/            # Capability-based routing
│   │   ├── __init__.py
│   │   └── registry.py          # Maps capabilities → providers (agents/tools/models)
│   │
│   ├── collaboration/           # Multi-agent collaboration
│   │   ├── __init__.py
│   │   └── pipeline.py          # AgentPipeline: sequential agent execution
│   │
│   ├── evolution/               # 🧬 Evolutionary strategy engine
│   │   ├── __init__.py
│   │   ├── engine.py            # EvolutionEngine: coordinates the evolution loop
│   │   ├── strategy.py          # Strategy dataclass (genome)
│   │   ├── population.py        # Population management
│   │   ├── mutation.py          # Mutation & crossover operations
│   │   ├── selection.py         # Fitness-based selection
│   │   ├── evaluation.py        # Strategy evaluation (lab/simulation)
│   │   ├── fitness.py           # Fitness function scoring
│   │   ├── archive.py           # Elite strategy archive
│   │   └── a-evolve/            # 📦 A-Evolve: universal self-improving agent infra
│   │       ├── README.md        # Full A-Evolve documentation
│   │       ├── DESIGN.md
│   │       ├── QUICKSTART.md
│   │       ├── agent_evolve/    # Evolution framework
│   │       ├── artifacts/       # Evolution artifacts
│   │       ├── docs/            # Algorithm docs
│   │       ├── examples/        # Example agents
│   │       ├── figs/            # Figures
│   │       ├── seed_workspaces/ # Seed agent workspaces
│   │       └── tests/           # Test suite
│   │
│   ├── llm_gateway/             # 🔌 LLM Gateway
│   │   ├── __init__.py          # LLMGateway: routing, fallback, health checks
│   │   └── models/              # Model registry config
│   │
│   ├── llm-gateway/             # LiteLLM gateway config
│   │   ├── config/              # LiteLLM configuration
│   │   ├── litellm/             # LiteLLM service files
│   │   └── models/              # models.yaml model registry
│   │
│   ├── memory/                  # 🧠 Memory system
│   │   ├── __init__.py
│   │   └── memory_store.py      # Typed memory (episodic, semantic, procedural)
│   │
│   ├── meta_learning/           # 📊 Meta-learning
│   │   ├── __init__.py
│   │   └── tracker.py           # PerformanceTracker: SQLite performance DB
│   │
│   ├── observability/           # 👁️ Observability
│   │   ├── __init__.py
│   │   └── logger.py            # Structured logging
│   │
│   ├── orchestrator/            # 🎛️ Master Orchestrator
│   │   ├── __init__.py
│   │   ├── master.py            # CyberAIOrchestrator: unified AI interface
│   │   ├── orchestrator.py      # Core orchestrator
│   │   ├── tool_registry.py     # Security tool registry
│   │   ├── tools.yaml           # Tool registry YAML
│   │   ├── adapters/            # Adapter management
│   │   │   ├── __init__.py
│   │   │   ├── adapter_manager.py  # AdapterManager
│   │   │   └── base.py          # Base adapter interface
│   │   ├── agents/              # 🤖 AI agents
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # Base agent interface
│   │   │   ├── planner/         # 🧠 Planner agent
│   │   │   ├── researcher/      # 🔍 Researcher agent
│   │   │   ├── recon/           # 🛰️ Recon agent
│   │   │   ├── analyst/         # 📊 Analyst agent
│   │   │   ├── coder/           # 💻 Coder agent
│   │   │   ├── verifier/        # ✅ Verifier agent
│   │   │   └── reporter/        # 📋 Reporter agent
│   │   ├── api/                 # 🔌 REST API
│   │   │   └── api_server.py    # FastAPI server
│   │   ├── cli/                 # ⌨️ Command-line interface
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py
│   │   │   ├── cli.py           # CLI entry point
│   │   │   └── doctor.py        # Health check
│   │   ├── evidence/            # 📎 Evidence collection
│   │   │   └── evidence.py      # Evidence chain management
│   │   ├── knowledge/           # 📚 Knowledge base
│   │   │   └── knowledge_loader.py
│   │   ├── logging/             # 📝 Session logging
│   │   │   └── session_logger.py
│   │   ├── memory/              # 🧠 Orchestrator memory
│   │   │   └── memory_manager.py
│   │   ├── policies/            # 🛡️ Safety policies
│   │   │   └── policy_engine.py # Target authorization & action whitelisting
│   │   ├── routing/             # 🔀 Model routing
│   │   │   ├── model_router.py  # ModelRouter
│   │   │   └── routing.yaml     # Routing fallback chains
│   │   ├── scheduler/           # 📅 Task scheduling
│   │   │   └── scheduler.py
│   │   └── workflows/           # 🔄 Workflow management
│   │       └── workflow_manager.py
│   │
│   ├── self_improvement/        # 🧬 Self-improvement
│   │   ├── __init__.py
│   │   ├── pipeline.py          # SelfImprovementPipeline: 10-stage gatekeeper
│   │   └── proposal.py          # ImprovementProposal model
│   │
│   ├── tool-gateway/            # 🔧 MCP Tool Gateway
│   │   └── mcp/                 # MCP server management
│   │
│   └── ui/                      # 🖥️ UI package
│       └── __init__.py
│
├── adapters/                    # 🔌 Security tool adapters (17 tracked)
│   ├── pentagi/                 # Primary pentesting agent
│   ├── strix/                   # Assessment agent
│   ├── darkmoon/                # MCP pentesting agent
│   ├── hexstrike/               # MCP tool gateway (150+ tools)
│   ├── cai/                     # Agent framework
│   ├── pentestgpt/              # Research/planning
│   ├── cyberstrikeai/           # Gin REST + MCP
│   ├── autopentest/             # LangChain research
│   ├── penclaw/                 # Static/dynamic analysis
│   ├── luan1aoagent/            # Cognitive agent
│   ├── aracne/                  # SSH-driven pentesting
│   ├── guardian-cli/            # CLI pentesting
│   ├── drakben/                 # Autonomous pentesting
│   ├── h4cker/                  # Knowledge base (reference)
│   └── kali-pentest/            # Skill definitions (reference)
│
├── infrastructure/              # ⚙️ Infrastructure services
│   ├── ollama/                  # Ollama models and config
│   ├── open-webui/              # Open WebUI data
│   ├── airllm/                  # AirLLM inference
│   └── other-inference/         # Additional inference engines
│
├── lab/                         # 🔬 Isolated lab environment
│   ├── targets/                 # Authorized target registry
│   │   └── targets.yaml         # Target definitions
│   ├── docker/                  # Docker Compose stacks
│   ├── networks/                # Network definitions
│   ├── snapshots/               # VM/target snapshots
│   ├── scenarios/               # Pre-built assessment scenarios
│   └── evidence/                # Collected evidence files
│
├── knowledge/                   # 📚 Security knowledge base
│   ├── cve/                     # CVE database
│   ├── cwe/                     # CWE weakness taxonomy
│   ├── advisories/              # Security advisories
│   ├── techniques/              # ATT&CK techniques
│   ├── research/                # Security research papers
│   └── documentation/           # Tool documentation
│
├── memory/                      # 🧠 Persistent memory
│   ├── memory.db                # SQLite database
│   ├── performance.db           # Performance tracking DB
│   ├── evolution/               # Evolution engine state
│   │   ├── population/          # Strategy population
│   │   ├── elite/               # Elite strategy archive
│   │   └── failures/            # Failure records
│   ├── embeddings/              # Vector embeddings
│   ├── findings/                # Individual findings
│   ├── failures/                # Failed strategies
│   ├── successful-strategies/   # Successful tactics
│   ├── observations/            # Agent observations
│   └── sessions/                # Session logs
│
├── logs/                        # 📝 Platform logs
│   └── sessions/                # Per-session logs
│
├── projects/                    # 📦 Additional projects
│   ├── security-agents/         # Custom security agents
│   ├── research-tools/          # Research utilities
│   ├── analysis-tools/          # Analysis scripts
│   └── legacy/                  # Legacy integrations
│
├── scripts/                     # ⚡ Utility scripts
├── backups/                     # 💾 Backup storage
└── tests/                       # 🧪 Test suite
```

---

## 🛠️ Quick Start & Setup Guide

> [!NOTE]
> **Current Integration Status (Phase A & B Verified):**
> Platform health checks pass with exit code 0 (`python -m cyberai.orchestrator.cli doctor`). The system coordinates **17 tracked adapters** (all 17 with `SecurityToolAdapter` wrappers), **7 specialized AI agents**, **4 persistent SQLite memory tables** (230+ experiences, 135+ findings), and **40+ CLI commands**. All paths resolve cleanly via `cyberai/config.py` without stdlib conflicts.

### Prerequisites
- Windows 11 / Linux / macOS
- Docker Desktop (for containerized services)
- Python 3.10+ (for orchestrator core)
- Ollama (for local models)
- Git (for repository management)

### Installation

```bash
# 1. Set up Python environment
python -m venv .venv
.\.venv\Scripts\activate        # Windows (or: source .venv/bin/activate on Linux)

# 2. Install core dependencies
pip install -r requirements.txt
# OR install as editable package:
pip install -e .

# 3. Configure environment
copy .env.example .env          # Windows (or: cp .env.example .env on Linux)
# Edit .env with your API keys and preferences

# 4. Install Ollama and pull models
# Download from https://ollama.com
ollama pull llama3.1:8b
ollama pull codellama:7b
ollama pull llama3.2:3b
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# 5. Start infrastructure services (optional / when Docker is running)
docker compose up -d

# 6. Run health check (exits 0)
python -m cyberai.orchestrator.cli doctor
```

### Configuration

#### Workspace Path Resolution (`CERBERUS_HOME`)
CERBERUS centralizes all file resolution through `cyberai.config.resolve_path()` to avoid hardcoded paths. By default, the workspace root is auto-detected as the repository root. If running outside the repo directory or within custom container mount paths, set:
```env
# Workspace Root Override (defaults to auto-detected repository root)
CERBERUS_HOME=C:\Users\hp\Desktop\Cerberus
```

#### Gateway Configuration (`.env`)
```env
# Workspace root override
# CERBERUS_HOME=C:\Users\hp\Desktop\Cerberus

# Ollama Local Models
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# LiteLLM Gateway
LITELLM_MASTER_KEY=sk-your-master-key-here
LITELLM_PORT=4000
LITELLM_CONFIG_PATH=cyberai/llm_gateway/config/config.yaml

# Cloud Providers (Optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...

# Privacy Mode (local_only | hybrid)
PRIVACY_MODE=local_only

# Lab Configuration
LAB_TARGETS_PATH=lab/targets/targets.yaml
REQUIRE_TARGET_AUTHORIZATION=true
```

#### Lab Targets (`lab/targets/targets.yaml`)
```yaml
targets:
  - id: lab-web-01
    environment: authorized_lab
    allowed: true
    host: 127.0.0.1
    port: 8080
    description: OWASP Juice Shop
    allowed_actions:
      - recon
      - scan
      - analysis
      - exploitation
```

### Using the Master Orchestrator

```python
import asyncio
from cyberai.orchestrator.master import CyberAIOrchestrator

async def main():
    ai = CyberAIOrchestrator(simulate=True)  # Simulation mode
    result = await ai.run("Find SQL injection vulnerabilities", target_id="lab-web-01")
    print(result["status"])
    ai.close()

asyncio.run(main())
```

### Using the CLI

The CLI provides 40+ operational commands via `python -m cyberai.orchestrator.cli <command>` (run with no arguments for the full list, or enter the interactive REPL with `python -m cyberai.orchestrator.cli`):

```bash
# 1. Health check — full diagnostic suite (exits 0)
python -m cyberai.orchestrator.cli doctor

# 2. Platform status — subsystem availability & metrics
python -m cyberai.orchestrator.cli status

# 3. End-to-end simulation — complete autonomous multi-agent run (zero external deps)
python -m cyberai.orchestrator.cli simulate "Analyze authorized lab target"

# 4. Capability, agent, model, and adapter catalogs
python -m cyberai.orchestrator.cli tools        # 17 registered tools
python -m cyberai.orchestrator.cli agents       # 7 AI specialist agents
python -m cyberai.orchestrator.cli models       # LLM aliases & transport status
python -m cyberai.orchestrator.cli adapters     # 17 tracked security tool adapters

# 5. Persistent memory & findings
python -m cyberai.orchestrator.cli findings
python -m cyberai.orchestrator.cli memory "SQL injection"

# 6. Evolutionary strategy engine
python -m cyberai.orchestrator.cli evolve

# 7. Lab targets & session management
python -m cyberai.orchestrator.cli lab list
python -m cyberai.orchestrator.cli session list

# 8. Target assessment (requires authorized target in lab/targets/targets.yaml)
python -m cyberai.orchestrator.cli task lab-web-01 --objective "Find SQL injection"
# (or legacy alias: python -m cyberai.orchestrator.cli assess lab-web-01)

# 9. CERBERUS Command Deck Web UI
python -m cyberai.orchestrator.cli ui
```

### Using the REST API

```bash
# Start the API server
uvicorn cyberai.orchestrator.api.api_server:create_app --factory --host 0.0.0.0 --port 8000

# Check platform status
curl http://localhost:8000/status

# List authorized targets
curl http://localhost:8000/targets/authorized

# Search memory
curl "http://localhost:8000/memory/search?query=SQL%20injection"

# List tools
curl http://localhost:8000/tools

# List model routes
curl http://localhost:8000/models
```

---

## 🔬 A-Evolve: Self-Improving Agent Infrastructure

CERBERUS integrates **A-Evolve** (`cyberai/evolution/a-evolve/`), the universal infrastructure for self-improving agents. A-Evolve evolves *any* agent across *any* domain using *any* evolution algorithm — with zero human intervention.

### The Evolution Loop (A-Evolve)

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────┐    ┌────────┐
│  Solve  │───▶│ Observe │───▶│ Evolve  │───▶│ Gate │───▶│ Reload │
└─────────┘    └─────────┘    └─────────┘    └──────┘    └────────┘
```

1. **Solve** — Agent processes a batch of tasks (black-box execution)
2. **Observe** — Collect trajectories + benchmark feedback into structured logs
3. **Evolve** — Evolution engine mutates workspace files (prompts, skills, memory)
4. **Gate** — Validate mutations on holdout tasks; regressions rolled back via git
5. **Reload** — Agent reloads from the (possibly rolled-back) workspace

### Built-in Adapters

| Adapter | Domain | Seed Workspace |
| :--- | :--- | :--- |
| `swe-verified` | Real-world GitHub issues (Python repos) | `seed_workspaces/swe/` |
| `mcp-atlas` | Tool-calling via MCP (16+ servers) | `seed_workspaces/mcp/` |
| `terminal-bench` | Terminal/CLI ops in Docker | `seed_workspaces/terminal/` |
| `skill-bench` | Agentic skill discovery | `seed_workspaces/skillbench/` |

### 3-Line Evolution

```python
import agent_evolve as ae

evolver = ae.Evolver(agent="./my_agent", benchmark="swe-verified")
results = evolver.run(cycles=10)
```

---

## 🧩 Tool Registry — 17 Integrated Adapters

| Tool | Type | API | Capabilities |
|------|------|-----|--------------|
| **PentAGI** | Security Agent | REST/GraphQL + MCP | Research, Analysis, Exploitation, Reporting |
| **Strix** | Security Agent | Server API | Assessment, Vulnerability Scanning |
| **HexStrike** | Tool Gateway | Flask REST + MCP | Tool Execution, MCP Servers, Web Scraping |
| **MCPStrike** | Tool Gateway | FastAPI + MCP | Tool Execution, MCP Servers |
| **Dark-Moon** | Security Agent | MCP Server | Research, Analysis, Exploitation |
| **CAI** | Security Agent | Python Library + MCP | Research, Analysis, Agent Framework |
| **PentestGPT** | Security Agent | CLI | Research, Planning |
| **PentestAgent** | Security Agent | CLI + MCP | Research, Analysis, Exploitation |
| **CyberStrikeAI** | Security Agent | Gin REST + MCP | Tool Execution, MCP Servers, Analysis |
| **AutoPentest** | Security Agent | CLI | Research, Planning |
| **PenClaw** | Analysis Tool | CLI | Static Analysis, Dynamic Scanning, Secret Detection |
| **LuaN1aoAgent** | Security Agent | CLI/Web | Research, Analysis, Planning |
| **ARACNE** | Security Agent | CLI (SSH) | Research, Exploitation, SSH-Driven |
| **Guardian-CLI** | Security Agent | CLI | Research, Analysis, Reporting |
| **DRAKBEN** | Security Agent | CLI (async) | Research, Analysis, Exploitation |
| **Kali-Pentest** | Skill Definitions | Documentation | Tool Guidance, Methodology |
| **h4cker** | Knowledge Base | Documentation | Reference, Training, Labs |

---

## 🔒 Ethical & Safety Boundaries

### Authorized Use Only

This platform is designed for:
- **Authorized penetration tests** on systems you own or have explicit written permission to test
- **CTF competitions** and practice environments
- **Security research** in isolated lab environments
- **Educational purposes** in controlled settings

### Hard-Coded Restrictions

1. **Target Authorization**: All active testing requires explicit target registration in `lab/targets/targets.yaml` with `allowed: true`
2. **Environment Enforcement**: The policy engine blocks execution on unregistered targets
3. **Lab-Only Default**: No tools execute against the host system or external networks by default
4. **Evidence Retention**: All actions are logged with timestamps, tool outputs, and verification status
5. **Privacy Mode**: `local_only` mode blocks all cloud model calls

### Prohibited Uses

- Unauthorized access to computer systems
- Data exfiltration from systems you don't own
- Denial of service attacks against third parties
- Malware development or distribution
- Any activity violating local, state, or international laws

### Responsible Disclosure

If you discover vulnerabilities during authorized testing:
1. Document findings with evidence
2. Report to the system owner
3. Allow time for remediation before disclosure
4. Follow coordinated disclosure principles

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | This file - platform overview and quick start |
| `ARCHITECTURE.md` | Deep-dive technical reference |
| `WORKSPACE_INVENTORY.md` | Detailed repository inventory |
| `REPOSITORY_MAP.yaml` | Repository-to-role mapping |
| `INTEGRATION_STATUS.md` | Component status tracking |
| `FINAL_STATUS.md` | Final delivery report |
| `PHASE2_AUDIT.md` | Phase 2 audit report |
| `cyberai/evolution/a-evolve/README.md` | A-Evolve full documentation |
| `.env.example` | Environment configuration template |

---

## 🧪 Running Tests

```bash
# Run the full test suite
python -m pytest tests/ -v

# Run a single test module
python -m pytest tests/test_evolution.py -v
```

---

## 🤝 Support & Contributing

- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Join community discussions for use cases and integrations
- **Contributing**: See `CONTRIBUTING.md` in individual repositories

---

## 📜 License

This platform structure is provided as-is. Individual components retain their original licenses. See `REPOSITORY_MAP.yaml` for details.

**Primary Licenses:**
- MIT: litellm, hexstrike-ai, mcpstrike, pentestgpt, pentestagent, strix, drakben, a-evolve
- Apache 2.0: ollama, open-webui, strix
- GPL v3: Dark-Moon
- Dual MIT + Proprietary: CAI
- AGPL v3: LuaN1aoAgent

---

## 🙏 Acknowledgments

This platform integrates the following open-source security research projects:
- **A-Evolve** by A-EVO-Lab — Universal self-improving agent infrastructure
- **PentAGI** by vxcontrol — Autonomous penetration testing
- **Strix** by usestrix — Security assessment agent
- **HexStrike AI** by 0x4m4 — MCP tool gateway
- **MCPStrike** by ente0 — Ollama-driven MCP
- **Dark-Moon** by ASCIT31 — Autonomous pentesting
- **CAI** by aliasrobotics — Cybersecurity AI framework
- **LiteLLM** by BerriAI — LLM gateway
- **Ollama** by ollama — Local model serving
- **Open WebUI** by open-webui — Web interface

And many more. See `WORKSPACE_INVENTORY.md` for complete list.

---

> **Status**: Platform structure complete and ready for deployment. Awaiting Docker, Ollama, and API key configuration for full operational capability.

<div align="center">
  <sub>Built with 🧬 evolutionary intelligence · CERBERUS</sub>
</div>