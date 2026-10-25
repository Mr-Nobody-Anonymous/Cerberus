<div align="center">
  <img src="ult.jpg" alt="CERBERUS Battlefield AI" width="480" style="border-radius: 14px; box-shadow: 0 8px 24px rgba(0,0,0,0.4);"/>

  # CERBERUS
  ### Autonomous, Self-Evolving Cyber AI Orchestrator

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![Python 3.10+](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
  [![CI](https://github.com/Mr-Nobody-Anonymous/Cerberus/actions/workflows/ci.yml/badge.svg)](https://github.com/Mr-Nobody-Anonymous/Cerberus/actions/workflows/ci.yml)
  [![Tests](https://img.shields.io/badge/Tests-624%20passed%20%7C%20100%25-success.svg)](tests/)
  [![API](https://img.shields.io/badge/API-FastAPI%200.160.0-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![CLI](https://img.shields.io/badge/CLI-Click%208.5.0%20%7C%20Rich-orange.svg)](docs/CLI_GUIDE.md)
  [![Architecture](https://img.shields.io/badge/Architecture-7%20Agents%20%7C%2017%20Adapters-8A2BE2.svg)](#-system-architecture)
  [![Safety](https://img.shields.io/badge/Safety-Policy%20Gated%20%7C%20Sandboxed-critical.svg)](#-defense-in-depth-safety-architecture)

  <p align="center">
    <b>A self-improving security research platform coordinating specialized AI agent swarms, evolutionary tactical strategy mutations, capability-based tool routing, and multi-model fallbacks across isolated lab targets.</b>
  </p>

  <p align="center">
    <a href="#-overview">Overview</a> •
    <a href="#-system-architecture">Architecture</a> •
    <a href="#-specialized-ai-agents">Agents</a> •
    <a href="#-17-integrated-tool-adapters">Adapters</a> •
    <a href="#-evolutionary-strategy-engine">Evolution Engine</a> •
    <a href="#-quick-start--installation">Quick Start</a> •
    <a href="#-operational-modes">Usage Modes</a> •
    <a href="#-defense-in-depth-safety-architecture">Safety Policy</a> •
    <a href="#-documentation-index">Documentation</a>
  </p>
</div>

---

## 🌟 Overview

Traditional security frameworks operate sequentially through rigid, hardcoded scripts that break when targets deviate from expected patterns. **CERBERUS** introduces an autonomous multi-agent intelligence mesh that formulates hypotheses, executes assessments, challenges findings through independent verification, and evolves strategies based on empirical outcomes.

```
                    ┌──────────────────────────────────────────────┐
                    │  Hypothesis → Execution → Verification → Log │
                    │        ▲                             │       │
                    │        └────── Evolve & Mutate ◄─────┘       │
                    └──────────────────────────────────────────────┘
```

### What Makes CERBERUS Different?

1. **🧬 Evolutionary Combat Engine**: Tactical strategies mutate in real time based on task performance. High-performing combinations (`RECON + ANALYSIS → VERIFIED FINDING`) are archived into an elite gene pool, while suboptimal tactics feed failure memory to prevent recurring mistakes.
2. **🧠 Non-Weight Meta-Learning**: The platform learns continuously without model weight fine-tuning. A SQLite-backed performance tracker (`performance.db`) records latency, verification rate, and quality metrics across models, tools, and strategies to rank providers dynamically.
3. **⚡ Capability-Based Provider Routing**: Agents reason in abstract capabilities (such as `reconnaissance`, `source_analysis`, `dynamic_scanning`, or `secret_detection`) rather than fixed tool paths. The capability registry dynamically selects the highest-ranked provider among 17 integrated security tool adapters.
4. **🛡️ Defense-in-Depth Safety Guardrails**: Hardcoded policy controls strictly restrict execution. Active operations require explicit target authorization in `lab/targets/targets.yaml`, strict action whitelisting, and isolated sandboxing. Complete simulated runs execute end-to-end with zero network traffic.
5. **🔄 10-Stage Self-Improvement Pipeline**: AI-suggested code modifications flow through a gated validation pipeline (syntax validation, AST security checks, unit testing, benchmark comparison, and human approval) before any patch is applied.
6. **🔌 Decoupled Multi-Model LLM Gateway**: Decouples agent prompts from underlying models using semantic aliases (`local-reasoner`, `local-coder`, `local-fast`, `research-model`, `cloud-reasoner`) with automatic fallback chains across LiteLLM proxies, local Ollama models, and direct provider APIs.

---

## 🏗️ System Architecture

```
                               ┌───────────────────────────┐
                               │   HUMAN OPERATOR / CLI    │
                               │   Command Deck Web UI     │
                               │   FastAPI REST & Bus      │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
         ┌───────────────────────────────────────────────────────────────────────┐
         │                       MASTER ORCHESTRATOR                             │
         │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
         │  │   Planner    │  │  Researcher  │  │    Recon     │  │  Analyst   │  │
         │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
         │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
         │  │    Coder     │  │   Verifier   │  │   Reporter   │                  │
         │  └──────────────┘  └──────────────┘  └──────────────┘                  │
         └───────┬───────────────────────────┬───────────────────────────┬───────┘
                 │                           │                           │
                 ▼                           ▼                           ▼
      ┌──────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
      │ CAPABILITY REGISTRY  │    │  LLM ROUTING GATEWAY │    │  POLICY & SAFETY     │
      │                      │    │                      │    │                      │
      │ • reconnaissance     │    │ • local-reasoner     │    │ • targets.yaml check │
      │ • source_analysis    │    │ • local-coder        │    │ • action whitelist  │
      │ • web_testing        │    │ • research-model     │    │ • sandbox isolation  │
      │ • tool_execution     │    │ • Ollama / LiteLLM   │    │ • simulation default │
      └──────────┬───────────┘    └──────────┬───────────┘    └──────────┬───────────┘
                 │                           │                           │
                 └───────────────────────────┼───────────────────────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              ▼                              ▼                              ▼
     ┌──────────────────┐           ┌──────────────────┐           ┌──────────────────┐
     │ EVOLUTION ENGINE │           │  META-LEARNING   │           │ 17 TOOL ADAPTERS │
     │                  │           │                  │           │                  │
     │ • Population     │           │ • SQLite metrics │           │ • PentAGI        │
     │ • Strategy Gene  │           │ • Task ranking   │           │ • Strix          │
     │ • Elite Archive  │           │ • Success rate   │           │ • HexStrike      │
     │ • Ghost Wargame  │           │ • Latency logs   │           │ • PenClaw (etc.) │
     └────────┬─────────┘           └────────┬─────────┘           └────────┬─────────┘
              │                              │                              │
              └──────────────────────────────┼──────────────────────────────┘
                                             │
                              ┌──────────────▼──────────────┐
                              │   PERSISTENT MEMORY & LAB   │
                              │                             │
                              │ • SQLite DB (experiences)   │
                              │ • Evidence Chain & Logs     │
                              │ • Authorized Lab Containers │
                              └─────────────────────────────┘
```

---

## 🤖 Specialized AI Agents

CERBERUS coordinates seven specialized agents, each constrained to a focused domain within the F2T2EA (Find, Fix, Track, Target, Engage, Assess) kill chain:

| Agent | Icon | Capability | Kill-Chain Phase | Core Responsibility | Primary Tool Integrations |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **Planner** | 🧠 | `planning` | Mission Inception | Decomposes high-level mission goals into structured, phased task graphs. | Reasoning Models, Task Memory |
| **Researcher**| 🔍 | `research` | Find / Fix | Mines CVE databases, advisory feeds, and security documentation for target intelligence. | PentestGPT, Knowledge Base, Web Search |
| **Recon** | 🛰️ | `reconnaissance` | Track / Target | Discovers target infrastructure, active services, ports, and software versions. | Strix, Nmap, PentAGI |
| **Analyst** | 📊 | `analysis` | Target | Correlates recon signals with vulnerability signatures to isolate genuine attack surfaces. | CAI, PenClaw, CVE Correlation |
| **Coder** | 💻 | `code_generation` | Engage | Constructs targeted test scripts, payloads, and proof-of-concept validators. | Local Coder LLM, AST Validators |
| **Verifier** | ✅ | `verification` | Assess | Strictly challenges findings; validates evidence and rejects false positives. | Independent Reasoner, Sandbox Execution |
| **Reporter** | 📋 | `reporting` | Finalization | Compiles structured executive and technical markdown/JSON audit reports. | Report Generator, Evidence Store |

### Agent Collaboration Pipeline
- **Sequential Orchestration**: Researcher $\to$ Recon $\to$ Analyst $\to$ Coder $\to$ Verifier $\to$ Reporter.
- **Context Filtering**: Each agent receives only relevant context from prior phases, preventing context window overflow during prolonged assessments.
- **Failure Isolation**: An individual agent failure does not compromise the platform; the orchestrator triggers alternative routing or gracefully terminates the phase.

---

## 🧩 17 Integrated Tool Adapters

Every external tool operates through a standardized `SecurityToolAdapter` wrapper with health monitoring, execution timeouts, and capability registration:

| Tool Adapter | Category | Primary Interface | Provided Capabilities | Upstream Attribution |
| :--- | :--- | :--- | :--- | :--- |
| **PentAGI** | Security Agent | REST/GraphQL + MCP | Research, Analysis, Exploitation, Reporting | [vxcontrol/pentagi](https://github.com/vxcontrol/pentagi) (MIT) |
| **Strix** | Security Agent | Server API | Assessment, Vulnerability Scanning, Recon | [usestrix/strix](https://github.com/usestrix/strix) (MIT) |
| **HexStrike AI** | Tool Gateway | Flask REST + MCP | Tool Execution (150+ tools), Scraping, MCP | [0x4m4/hexstrike-ai](https://github.com/0x4m4/hexstrike-ai) (MIT) |
| **MCPStrike** | Tool Gateway | FastAPI + MCP | Tool Execution, Ollama MCP Servers | [ente0/mcpstrike](https://github.com/ente0/mcpstrike) (MIT) |
| **Dark-Moon** | Security Agent | MCP Server | Research, Analysis, Exploitation | [ASCIT31/Dark-Moon](https://github.com/ASCIT31/Dark-Moon) (GPLv3) |
| **CAI** | Security Agent | Python Library + MCP | Research, Analysis, Agent Framework | [aliasrobotics/cai](https://github.com/aliasrobotics/cai) (Dual MIT/Prop.) |
| **PentestGPT** | Security Agent | CLI | Research, Planning | [GreyDGL/PentestGPT](https://github.com/GreyDGL/PentestGPT) (MIT) |
| **PentestAgent** | Security Agent | CLI + MCP | Research, Analysis, Exploitation | [TideSec/PentestAgent](https://github.com/TideSec/PentestAgent) (MIT) |
| **CyberStrikeAI** | Security Agent | Gin REST + MCP | Tool Execution, MCP Servers, Analysis | [CyberStrikeAI](https://github.com/CyberStrikeAI) (MIT) |
| **AutoPentest** | Security Agent | CLI | Research, Planning, LangChain Automation | [AutoPentest](https://github.com/AutoPentest) (MIT) |
| **PenClaw** | Analysis Tool | CLI | Static Analysis, Dynamic Scanning, Secret Detection | [PenClaw](https://github.com/PenClaw) (MIT) |
| **LuaN1aoAgent** | Security Agent | CLI / Web | Cognitive Agent, Research, Analysis, Planning | [LuaN1aoAgent](https://github.com/LuaN1aoAgent) (AGPLv3) |
| **ARACNE** | Security Agent | CLI (SSH) | SSH-Driven Autonomous Pentesting | [ARACNE](https://github.com/ARACNE) (MIT) |
| **Guardian-CLI** | Security Agent | CLI | Research, Analysis, Reporting | [Guardian-CLI](https://github.com/Guardian-CLI) (MIT) |
| **DRAKBEN** | Security Agent | CLI (async) | Autonomous Pentesting, Exploit Discovery | [DRAKBEN](https://github.com/DRAKBEN) (MIT) |
| **Kali-Pentest** | Skill Definitions | Documentation | Pentest Methodology, Tool Guidance | Reference / Skill Catalog |
| **h4cker** | Knowledge Base | Documentation | Security Architecture, CVE/CWE Taxonomy | Reference Knowledge Base |

---

## 🧬 Evolutionary Strategy Engine

CERBERUS includes a native evolutionary strategy engine (`cyberai/evolution/`) designed to iteratively discover optimal assessment workflows:

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────┐    ┌────────┐
│  Solve  │───▶│ Observe │───▶│ Evolve  │───▶│ Gate │───▶│ Reload │
└─────────┘    └─────────┘    └─────────┘    └──────┘    └────────┘
```

1. **Solve**: Agents execute assessment tasks (in simulation or against authorized lab targets).
2. **Observe**: Telemetry, execution trajectories, and benchmark scores are recorded into structured logs.
3. **Evolve**: The mutation engine performs crossover and mutation on `Strategy` genomes (prompts, tool chains, parameters).
4. **Gate**: Variant strategies are evaluated against the fitness function; regressions are automatically rolled back.
5. **Reload**: High-fitness strategies are archived in persistent memory (`memory/evolution/elite/`).

### Fitness Scoring Function
$$\text{Fitness} = 1.0 \times \text{Success} + 0.8 \times \text{Verification} + 0.6 \times \text{Evidence Quality} + 0.5 \times \text{Repeatability} - 0.3 \times \text{Superfluous Actions} - 0.5 \times \text{Failures}$$

### Ghost Wargaming & Failure Avoidance
- **Failure Memory**: Suboptimal or failed tactics are indexed by tool, action, and error category in `memory/evolution/failures/`.
- **Negative Pattern Avoidance**: During planning, agents cross-reference prospective task plans against failure memory to eliminate known dead ends before issuing commands.

---

## 🚀 Quick Start & Installation

### Prerequisites
- **Operating System**: Windows 10/11, Ubuntu 20.04+, or macOS 12+
- **Python**: Version 3.10 or 3.11
- **Node.js**: Version 18+ (only required if rebuilding the frontend UI)
- **Optional**: [Ollama](https://ollama.com/) (for offline local models) and Docker (for containerized lab targets)

### 1. Clone & Set Up Virtual Environment

```bash
# Clone the repository
git clone https://github.com/Mr-Nobody-Anonymous/Cerberus.git
cd Cerberus

# Create and activate virtual environment
python -m venv .venv

# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install pinned dependencies
pip install -r requirements.txt

# Install CERBERUS in editable mode with CLI entry point
pip install -e .
```

### 3. Configure Environment

Copy the example configuration file and adjust settings as needed:
```bash
# On Windows:
copy .env.example .env
# On Linux / macOS:
cp .env.example .env
```

| Environment Variable | Default Value | Purpose |
| :--- | :--- | :--- |
| `CERBERUS_HOME` | Auto-detected | Workspace root directory override for portable execution |
| `OLLAMA_HOST` | `http://localhost:11434` | Host address of local Ollama model runtime |
| `LITELLM_MASTER_KEY` | *(Required)* | Master authentication key for LiteLLM gateway proxy |
| `PRIVACY_MODE` | `local_only` | `local_only` blocks all external cloud calls; `hybrid` permits cloud models |
| `LAB_TARGETS_PATH` | `lab/targets/targets.yaml` | Path to authorized target registry |
| `REQUIRE_TARGET_AUTHORIZATION`| `true` | Enforces hard policy block on unregistered targets |

### 4. Run Preflight Diagnostics

Verify system readiness, dependencies, and environment health:
```bash
cyber-ai doctor
# Or use the universal launcher:
python start_cerberus.py --doctor
```

> [!TIP]
> The launcher `start_cerberus.py` is portable across working directories, handles Windows UTF-8 console streams cleanly, and checks for required modules automatically.

---

## 💻 Operational Modes

### Mode 1: Safe End-to-End Simulation
Run a complete autonomous multi-agent mission in simulated mode without emitting any external network traffic:
```bash
cyber-ai simulate "Audit laboratory web application for authentication flaws"
```
*Expected Result*: The orchestrator runs Recon, Analyst, and Verifier agents in safe simulation mode, populates findings in memory, and generates an audit report.

### Mode 2: CERBERUS Command Deck Web UI
Launch the unified FastAPI server and React Command Deck:
```bash
cyber-ai ui --port 8000
# Or using the launcher:
python start_cerberus.py --ui --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser:
- **3-Pane Security IDE**: Interactive chat sidebar, 14 specialized navigation views, and live telemetry rail.
- **Ctrl+K Command Palette**: Global shortcut to trigger actions, search views, and switch modes.
- **Security Approval Queue**: Human-in-the-loop review for active operations. Seeded demo data is clearly marked with `<Pill tone="info">DEMO</Pill>` badges.

### Mode 3: Interactive Operator Terminal Shell
Start the interactive terminal REPL with syntax highlighting, persistent history (`~/.cerberus/cli_history`), and tab-completion:
```bash
cyber-ai interactive
```
Available slash commands in the interactive shell:
- `/status` — System health and active subsystem metrics
- `/targets` — List registered and authorized lab targets
- `/findings` — Display collected findings by verification status
- `/models` — Show active model routes and transport health
- `/tools` — Inspect active tool adapters
- `/help` — Interactive assistance and command listing

### Mode 4: Python Orchestrator SDK
```python
import asyncio
from cyberai.orchestrator.master import CyberAIOrchestrator

async def main():
    # Initialize orchestrator in safe simulation mode
    ai = CyberAIOrchestrator(simulate=True)

    result = await ai.run(
        objective="Inspect laboratory API for IDOR vulnerabilities",
        target_id="lab-web-01"
    )

    print(f"Status: {result['status']}")
    print(f"Findings Collected: {len(result.get('findings', []))}")
    ai.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Mode 5: REST API Server
Start the REST API server:
```bash
uvicorn cyberai.orchestrator.api.api_server:create_app --factory --host 0.0.0.0 --port 8000
```

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/status` | `GET` | Platform health, resource usage, and active subsystem statuses |
| `/targets` | `GET` | List all registered lab targets |
| `/targets/authorized` | `GET` | List targets authorized for active operations |
| `/sessions` | `GET` | List active and historical engagement sessions |
| `/findings` | `GET` | Retrieve findings filtered by verification status (`VERIFIED`, `UNVERIFIED`) |
| `/memory/search` | `GET` | Query episodic and semantic memory store |
| `/models` | `GET` | Inspect model aliases and active transport routes |
| `/tools` | `GET` | Inspect registered tool adapters and availability |

---

## ⌨️ CLI Command Catalog

The `cyber-ai` CLI provides 40+ operational commands. Global flags (`--json`, `--yaml`, `--table`, `--quiet`, `--verbose`, `--debug`, `--no-color`) precede or follow subcommands:

| Category | Command | Description |
| :--- | :--- | :--- |
| **Execution** | `cyber-ai simulate <obj>` | Run complete multi-agent mission in safe simulation mode |
| | `cyber-ai task <target>` | Execute an autonomous assessment against an authorized target |
| | `cyber-ai hunt <target>` | Launch a guided, interactive vulnerability hunt |
| | `cyber-ai wargame` | Run ghost wargaming simulations to learn from tactical failures |
| | `cyber-ai workflow` | Inspect, validate, or execute multi-phase assessment workflows |
| **Diagnostics** | `cyber-ai doctor` | Comprehensive environment, dependency, and port diagnostic suite |
| | `cyber-ai status` | Platform subsystem availability, memory stats, and active metrics |
| | `cyber-ai profile` | Detect hardware capabilities and classify the execution profile |
| | `cyber-ai scorecard` | Display overall CERBERUS platform evaluation scorecard |
| | `cyber-ai benchmark` | Benchmark memory, policy engine, and adapter execution times |
| **Target & Lab** | `cyber-ai lab list` | List configured lab environments and containers |
| | `cyber-ai blueprint <target>`| Display target architecture blueprint and authorized attack surface |
| **Intelligence** | `cyber-ai memory <query>` | Semantic search over historical experiences |
| | `cyber-ai findings` | List verified and unverified vulnerability findings |
| | `cyber-ai intel <target>` | Quick intelligence summary: findings, memory, and status |
| | `cyber-ai evolve` | Execute generation cycle in the evolutionary strategy engine |
| **Interfaces** | `cyber-ai interactive` | Launch the themed REPL operator shell with tab-completion |
| | `cyber-ai ui` | Start the FastAPI server and open the Command Deck Web UI |
| | `cyber-ai watch` | Live-tail platform events (tasks, findings, security audit logs) |
| | `cyber-ai mcp` | Manage Model Context Protocol (MCP) server endpoints |

---

## ⚙️ Hardware Execution Profiles

CERBERUS automatically probes host hardware at startup to recommend the optimal execution profile (`cyber-ai profile`):

| Profile | RAM Requirement | GPU / Compute | Recommended Model Configuration |
| :--- | :--- | :--- | :--- |
| `MINIMAL` | 4–8 GB | None | Cloud APIs via LiteLLM + quantized embeddings |
| `CLOUD` | 8–16 GB | None | Cloud reasoning models + local embeddings |
| `HYBRID` | 16–64 GB | Optional GPU | Local models for fast tasks + cloud models for complex reasoning |
| `LOCAL` | 64+ GB | Dedicated GPU (VRAM $\ge 16$ GB) | Full offline local execution via Ollama |
| `SERVER` | 128+ GB | Multi-GPU cluster | Distributed inference and concurrent agent swarms |

> [!NOTE]
> The execution profile can be manually overridden at any time by setting `CERBERUS_PROFILE=HYBRID` in your environment.

---

## 🛡️ Defense-in-Depth Safety Architecture

> [!IMPORTANT]
> **Authorized Testing Only**: CERBERUS is strictly engineered for authorized penetration tests on systems you own or have explicit written permission to assess, CTF competitions, and academic security research in isolated lab environments.

### Hardcoded Policy Controls
1. **Target Authorization Engine**: All active testing requires explicit target registration in [lab/targets/targets.yaml](lab/targets/targets.yaml) with `allowed: true`. Unregistered targets are rejected by `PolicyEngine` with a `PermissionError`.
2. **Action Whitelisting**: Per-target `allowed_actions` control permitted operations (e.g., `recon`, `scan`, `analysis`). Exploitation or write actions on read-only targets are rejected.
3. **Simulation Default**: The orchestrator defaults to `simulate=True`, preventing unintended network packets during exploration and testing.
4. **10-Stage Self-Improvement Validation Gate**: AI-generated code proposals must pass automated syntax compilation, AST security pattern checks (blocking `os.system`, `eval`, `exec`), unit tests, and regression benchmarks before human review.
5. **Multi-Threaded SQLite Concurrency**: SQLite memory stores operate with WAL mode (`PRAGMA journal_mode=WAL`) and `check_same_thread=False` to ensure data integrity during concurrent FastAPI request processing.
6. **No Default Secrets**: Docker Compose configurations require explicit environment variable definitions (`LITELLM_MASTER_KEY`) and reject insecure fallback defaults.

---

## 🧪 Testing & Verification

The CERBERUS test suite includes unit, integration, security policy, and regression tests:

```bash
# Run the complete test suite (624 tests)
pytest

# Run dedicated submission regression tests
pytest tests/test_submission_regressions.py -v

# Run static analysis and style checks
ruff check cyberai tests scripts

# Validate all Python byte-compilation
python -m compileall cyberai tests scripts
```

---

## 🗂️ Annotated Project Directory Tree

```
CERBERUS/
├── start_cerberus.py            # Universal multi-platform launcher
├── fix_doctor.py                # Doctor diagnostic path fixer
├── pyproject.toml               # Package specifications, scripts, and asset definitions
├── requirements.txt             # Pinned production dependencies
├── docker-compose.yml           # Pinned local inference & database stack
├── REPOSITORY_MAP.yaml          # Mapping of external adapters and architectural roles
├── ult.jpg                      # Platform banner asset
├── LICENSE                      # MIT Open Source License
├── CHANGELOG.md                 # Project release history
├── ARCHITECTURE.md              # Deep-dive technical architecture specification
│
├── cyberai/                     # Core platform package
│   ├── capabilities/            # Capability registry and provider mapping
│   ├── collaboration/           # Multi-agent collaboration pipelines
│   ├── commands/                # Shared slash command catalog and dispatcher
│   ├── evolution/               # Genetic strategy evolution engine & wargaming
│   ├── llm_gateway/             # Model routing, aliases, hardware detection & fallbacks
│   ├── memory/                  # SQLite episodic, semantic, and procedural memory stores
│   ├── meta_learning/           # Performance tracking & provider ranking database
│   ├── observability/           # Structured logging and session monitoring
│   ├── orchestrator/            # Master Orchestrator core
│   │   ├── agents/              # 7 AI specialist agents (Planner, Recon, etc.)
│   │   ├── api/                 # FastAPI REST application
│   │   ├── cli/                 # Click CLI, doctor diagnostics & interactive REPL shell
│   │   ├── evidence/            # Evidence chain collection and validation
│   │   ├── policies/            # Target authorization and safety policies
│   │   ├── routing/             # Semantic model router and fallback configuration
│   │   ├── scheduler/           # Asynchronous task scheduling
│   │   └── workflows/           # F2T2EA kill chain and workflow managers
│   ├── security/                # Policy enforcement and sandbox execution
│   ├── self_improvement/        # 10-stage gated self-improvement proposal pipeline
│   └── ui/                      # Web server & compiled Command Deck UI assets
│
├── adapters/                    # 17 security tool adapters (PentAGI, Strix, etc.)
├── lab/                         # Isolated laboratory configurations
│   └── targets/targets.yaml     # Authorized target registry
├── docs/                        # Comprehensive guides, architecture & ADRs
│   ├── CLI_GUIDE.md             # Exhaustive CLI command reference
│   ├── COMMANDS.md              # Slash commands and event bus documentation
│   ├── UI_GUIDE.md              # Walkthrough of the Command Deck Web UI
│   ├── FRONTEND_ARCHITECTURE.md # React frontend architecture and state models
│   └── adr/                     # Architecture Decision Records
└── tests/                       # Automated unit, integration, and regression suites
```

---

## 📚 Documentation Index

| Document | Scope and Description |
| :--- | :--- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | In-depth technical specification of orchestrator subsystems, data flows, and state machines |
| [docs/CLI_GUIDE.md](docs/CLI_GUIDE.md) | Exhaustive CLI reference covering all 40+ commands, flags, and interactive REPL shell |
| [docs/COMMANDS.md](docs/COMMANDS.md) | Detailed specification of shared slash commands and the unified command bus |
| [docs/UI_GUIDE.md](docs/UI_GUIDE.md) | Complete user guide for the CERBERUS Command Deck Web UI and its 14 views |
| [docs/FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md) | Architecture, state management, and design tokens of the React frontend |
| [REPOSITORY_MAP.yaml](REPOSITORY_MAP.yaml) | Authoritative mapping of integrated adapters, roles, and upstream licenses |
| [CHANGELOG.md](CHANGELOG.md) | Chronological log of enhancements, security fixes, and architectural revisions |
| [LICENSE](LICENSE) | MIT open-source licensing terms |

---

## 🙏 Upstream Acknowledgments

CERBERUS integrates and is inspired by the following open-source security research projects:
- **A-Evolve** by A-EVO-Lab — Design inspiration for the native strategy evolution engine
- **PentAGI** by vxcontrol — Autonomous penetration testing agent
- **Strix** by usestrix — Security assessment agent
- **HexStrike AI** by 0x4m4 — Tool gateway and security MCP servers
- **MCPStrike** by ente0 — Ollama-driven Model Context Protocol tooling
- **Dark-Moon** by ASCIT31 — Autonomous security assessment agent
- **CAI** by aliasrobotics — Cybersecurity AI framework
- **LiteLLM** by BerriAI — Multi-model LLM gateway proxy
- **Ollama** by ollama — Local model inference engine
- **Open WebUI** by open-webui — Web interface components

---

<div align="center">
  <sub>Engineered for autonomous security research · CERBERUS</sub>
</div>
