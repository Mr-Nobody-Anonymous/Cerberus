<div align="center">
  <img src="ult.jpg" alt="CERBERUS Battlefield AI" width="700"/>

  # CERBERUS
  ### Autonomous, Self-Evolving Cyber AI Orchestrator

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
  [![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
  [![CI](https://github.com/Mr-Nobody-Anonymous/Cerberus/actions/workflows/ci.yml/badge.svg)](https://github.com/Mr-Nobody-Anonymous/Cerberus/actions/workflows/ci.yml)
  [![Tests](https://img.shields.io/badge/Tests-624%20passed-success.svg)](tests/)
  [![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
  [![Architecture](https://img.shields.io/badge/Architecture-7%20Agents%20%7C%2017%20Adapters-8A2BE2.svg)](#-master-architecture)
  [![Safety](https://img.shields.io/badge/Safety-Policy%20Gated-critical.svg)](#-safety--ethical-boundaries)

  <p align="center">
    <b>An intelligent security research platform coordinating specialized AI agent swarms, evolutionary tactical strategy mutations, and multi-model routing across isolated laboratory targets.</b>
  </p>

  <p align="center">
    <a href="#-quick-start">Quick Start</a> •
    <a href="#-master-architecture">Architecture</a> •
    <a href="#-specialized-ai-agents">Agents</a> •
    <a href="#-operational-interfaces">Interfaces</a> •
    <a href="#-safety--ethical-boundaries">Safety Policy</a> •
    <a href="#-documentation-index">Docs</a>
  </p>
</div>

---

## 🌟 Overview

**CERBERUS** bridges the divide between static security tooling and autonomous decision-making. Traditional security frameworks operate sequentially through rigid scripts; CERBERUS coordinates an adaptive swarm of specialized AI agents that formulate hypotheses, select and execute tools, challenge each finding through independent verification, and retain knowledge across engagements.

### Core Distinctions
- **Adaptive Evolutionary Intelligence**: Employs genetic algorithms to mutate assessment strategies based on empirical outcomes. High-performing strategies are archived into an elite gene pool, while unsuccessful paths are cataloged into failure memory to prevent recurring mistakes.
- **Capability-Based Provider Mesh**: Agents request abstract capabilities (such as `reconnaissance`, `source_analysis`, or `dynamic_scanning`) rather than specific tools. The platform dynamically routes tasks to the highest-performing provider among 17 integrated tool adapters.
- **Defense-in-Depth Guardrails**: Real execution is restricted by hardcoded policy controls. Active actions require explicit target authorization, whitelisted actions, and isolated sandboxing. Simulation mode allows complete risk-free task execution without emitting network traffic.
- **Multi-Model LLM Gateway**: Decouples agent reasoning from specific model providers using semantic aliases (`local-reasoner`, `local-coder`, `research-model`) with automatic fallbacks across local Ollama instances, LiteLLM proxies, and cloud APIs.

---

## 🏗️ Master Architecture

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

| Agent | Capability | Responsibility | Primary Specialist Tools |
| :--- | :--- | :--- | :--- |
| 🧠 **Planner** | `planning` | Decomposes high-level mission goals into structured, phased task graphs. | Reasoning Models, Task Memory |
| 🔍 **Researcher** | `research` | Mines CVE databases, advisory feeds, and security documentation for target intelligence. | PentestGPT, Knowledge Base, Web Search |
| 🛰️ **Recon** | `reconnaissance` | Discovers target infrastructure, active services, ports, and software versions. | Strix, Nmap, PentAGI |
| 📊 **Analyst** | `analysis` | Correlates recon signals with vulnerability signatures to isolate genuine attack surfaces. | CAI, PenClaw, CVE Correlation |
| 💻 **Coder** | `code_generation` | Constructs targeted test scripts, payloads, and proof-of-concept validators. | Local Coder LLM, AST Validators |
| ✅ **Verifier** | `verification` | Strictly challenges findings; validates evidence and rejects false positives. | Independent Reasoner, Sandbox Execution |
| 📋 **Reporter** | `reporting` | Compiles structured executive and technical markdown/JSON audit reports. | Report Generator, Evidence Store |

---

## ⚡ Dynamic Capability Routing

Instead of hard-coding tool executions, agents request abstract operational capabilities. The Capability Registry routes demands to the optimal available adapter:

| Capability | Provider Routing Order | Primary Focus |
| :--- | :--- | :--- |
| **Reconnaissance** | `Strix` → `PentAGI` → `Recon Agent` | Port scanning, host discovery, service enumeration |
| **Source Analysis** | `CAI` → `local-coder` → `Analyst Agent` | Static code analysis, semantic vulnerability audits |
| **Web Testing** | `Dark-Moon` → `PentAGI` | Web application surface and API assessment |
| **Tool Execution** | `HexStrike` → `MCPStrike` | Modular execution of 150+ standard security tools |
| **Research** | `PentestGPT` → `Researcher Agent` | Threat intelligence, exploit research, CVE lookup |
| **Static Analysis** | `PenClaw` → `CAI` | SAST scans, secret detection, code smell identification |
| **Verification** | `Verifier Agent` → `local-reasoner` | Independent proof-of-exploit validation |

---

## 🧬 Evolutionary Strategy Engine

CERBERUS features a native strategy evolution engine (`cyberai/evolution/`) designed to iteratively discover optimal assessment workflows:

1. **Genome Formulation**: Tactics, prompts, and execution chains are serialized into discrete `Strategy` genomes.
2. **Evaluation & Fitness**: Each strategy is evaluated in simulation or against authorized lab targets. Fitness is scored on verification accuracy (+0.8), evidence quality (+0.6), efficiency, and penalty for non-essential actions (-0.3).
3. **Genetic Mutation & Crossover**: High-scoring strategies are crossed and mutated with new tactical combinations.
4. **Elite Archival & Ghost Wargaming**: Elite tactics are stored in persistent memory (`memory/evolution/elite/`). Failed attempts are preserved in failure memory (`memory/evolution/failures/`) so future planning runs avoid dead-end strategies.

---

## 🚀 Quick Start

### 1. Prerequisites
- **Operating System**: Windows 10/11, Ubuntu 20.04+, or macOS 12+
- **Python**: Version 3.10 or 3.11
- **Node.js**: Version 18+ (only if modifying frontend UI source)
- **Optional**: [Ollama](https://ollama.com/) (for offline local models) and Docker (for containerized lab targets)

### 2. Installation

```bash
# Clone repository
git clone https://github.com/Mr-Nobody-Anonymous/Cerberus.git
cd Cerberus

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install in editable mode with all dependencies
pip install -r requirements.txt
pip install -e .
```

### 3. Preflight Health Check
Verify your environment, configuration, and dependencies:
```bash
cyber-ai doctor
# Or using the unified launcher:
python start_cerberus.py --doctor
```

> [!TIP]
> `start_cerberus.py` works portably from any working directory and automatically configures UTF-8 console encoding and project path overrides (`CERBERUS_HOME`).

---

## 💻 Operational Interfaces

CERBERUS provides multiple interfaces tailored to different operational requirements:

### 1. Safe End-to-End Simulation
Run an autonomous multi-agent mission in safe simulation mode with zero external network traffic:
```bash
cyber-ai simulate "Audit laboratory web application for authentication flaws"
```

### 2. Command Deck Web UI
Launch the unified FastAPI server and modern React Command Deck:
```bash
cyber-ai ui --port 8000
# Or:
python start_cerberus.py --ui --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser. The Command Deck features real-time agent telemetry, session history, memory search, an interactive security approval queue, and mission analytics.

### 3. Interactive CLI Shell
Start the terminal shell with tab-completion, persistent command history, and shared slash commands:
```bash
cyber-ai interactive
```
Available slash commands inside the interactive shell include:
- `/status` — System telemetry and subsystem diagnostics
- `/targets` — List authorized lab targets
- `/findings` — Inspect collected vulnerability findings
- `/models` — Display model routing table and health
- `/tools` — Inspect active tool adapters
- `/help` — Command assistance

### 4. CLI Batch Commands
```bash
# Inspect platform status and model routes
cyber-ai status
cyber-ai models

# Review registered tools and specialist agents
cyber-ai tools
cyber-ai agents

# Query findings and persistent memory
cyber-ai findings
cyber-ai memory "SQL injection"

# Execute a mission against an authorized lab target
cyber-ai task lab-web-01 --objective "Audit authentication endpoints"
```

### 5. Python Orchestrator SDK
```python
import asyncio
from cyberai.orchestrator.master import CyberAIOrchestrator

async def main():
    # Initialize orchestrator in safe simulation mode
    orchestrator = CyberAIOrchestrator(simulate=True)

    result = await orchestrator.run(
        objective="Inspect laboratory API for IDOR vulnerabilities",
        target_id="lab-web-01"
    )

    print(f"Mission Status: {result['status']}")
    print(f"Findings Verified: {len(result.get('findings', []))}")
    orchestrator.close()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔒 Safety & Ethical Boundaries

> [!IMPORTANT]
> **Authorized Testing Only**: CERBERUS is strictly engineered for authorized penetration testing, academic security research, CTF practice, and defensive validation in controlled laboratory environments.

### Hardcoded Guardrails
1. **Target Authorization Engine**: All active engagements require targets to be explicitly declared in [lab/targets/targets.yaml](lab/targets/targets.yaml) with `allowed: true`.
2. **Action Whitelisting**: Active operations are restricted to per-target `allowed_actions` (e.g., `recon`, `scan`, `analysis`). Unregistered operations are rejected by the policy engine.
3. **Simulation Default**: By default, the orchestrator operates in `simulate=True` mode, preventing any unapproved network interaction.
4. **Self-Improvement Validation Gate**: AI-generated code proposals must pass strict static syntax analysis, security checks (preventing arbitrary code execution primitives like `eval` or untracked subprocesses), and baseline regression benchmarks before being eligible for human approval.
5. **Privacy Enforcement**: A configurable `local_only` mode ensures that no sensitive target data, tokens, or outputs are transmitted to external cloud providers.

---

## 🧪 Testing & Verification

The repository maintains an automated test suite verifying orchestration pipelines, security policies, adapter integrations, and regression prevention:

```bash
# Run the complete test suite (624 tests)
pytest

# Run dedicated submission regression tests
pytest tests/test_submission_regressions.py -v

# Run specific functional suites
pytest tests/test_agents.py tests/test_security_regressions.py -v
```

---

## 📁 Repository Structure

```
CERBERUS/
├── start_cerberus.py            # Universal multi-platform launcher
├── pyproject.toml               # Package definition and dependencies
├── requirements.txt             # Pinned dependency specifications
├── docker-compose.yml           # Local inference & database infrastructure
├── REPOSITORY_MAP.yaml          # Mapping of adapters and architectural roles
├── ult.jpg                      # Platform banner asset
│
├── cyberai/                     # Core Python platform package
│   ├── capabilities/            # Dynamic capability router
│   ├── collaboration/           # Multi-agent collaboration pipelines
│   ├── evolution/               # Genetic strategy evolution engine
│   ├── llm_gateway/             # Model routing, aliases & fallbacks
│   ├── memory/                  # SQLite episodic and semantic store
│   ├── meta_learning/           # Performance tracking & ranking
│   ├── orchestrator/            # Master Orchestrator, CLI & agents
│   │   ├── agents/              # 7 AI specialist agents
│   │   ├── api/                 # FastAPI REST application
│   │   ├── cli/                 # CLI entry point, doctor & REPL shell
│   │   └── policies/            # Authorization & safety policies
│   ├── security/                # Policy enforcement & sandbox execution
│   ├── self_improvement/        # 10-stage gated self-improvement pipeline
│   └── ui/                      # Web server & compiled Command Deck UI
│
├── adapters/                    # 17 security tool adapters
├── lab/                         # Isolated laboratory configurations
│   └── targets/targets.yaml     # Authorized target registry
├── docs/                        # Technical guides, architecture & ADRs
└── tests/                       # Unit, integration & regression test suites
```

---

## 📚 Documentation Index

| Resource | Scope and Purpose |
| :--- | :--- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | In-depth technical specification of orchestrator subsystems and data flows |
| [docs/CLI_GUIDE.md](docs/CLI_GUIDE.md) | Exhaustive CLI guide covering all 40+ commands and interactive shell |
| [docs/COMMANDS.md](docs/COMMANDS.md) | Reference documentation for shared slash commands and dispatch bus |
| [docs/UI_GUIDE.md](docs/UI_GUIDE.md) | Walkthrough of the Command Deck Web UI features and views |
| [docs/FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md) | Architecture and state model of the React frontend application |
| [REPOSITORY_MAP.yaml](REPOSITORY_MAP.yaml) | Structural map and provenance of external adapters and components |
| [CHANGELOG.md](CHANGELOG.md) | History of release modifications, fixes, and feature additions |
| [LICENSE](LICENSE) | MIT open source licensing terms |

---

<div align="center">
  <sub>Engineered for autonomous security research · CERBERUS</sub>
</div>
