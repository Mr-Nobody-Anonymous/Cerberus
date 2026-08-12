# Local Autonomous Multi-Agent Security Research Platform

**Cyber AI Orchestrator** — A local, orchestrator-centric offensive security research and vulnerability testing platform that leverages AI agents, local models (Ollama), and cloud model routing (LiteLLM Gateway) to conduct authorized security assessments in isolated lab environments.

---

## System Overview

The Cyber AI Orchestrator is a production-grade security research platform designed for authorized penetration testing, vulnerability assessment, and security research. It coordinates multiple specialized AI agents through a central orchestrator, routing tasks to appropriate tools and models while maintaining strict lab isolation and comprehensive audit logging.

### Core Design Philosophy

1. **Non-Destructive Modular Integration**: Original repositories are preserved intact; integration occurs through adapters and the Model Context Protocol (MCP), never through merged source code.
2. **Experience-Based Learning**: The platform records tactics, techniques, and results to persistent memory without corrupting model weights. Success and failure patterns inform future planning.
3. **Strict Lab Isolation**: All active execution is confined to explicitly authorized lab targets (Docker containers, VMs, CTF environments). The host system is never directly targeted.
4. **Verification Over Trust**: Every finding requires evidence and passes through a verifier agent before acceptance. Finding states: UNVERIFIED, LIKELY, VERIFIED, REJECTED.

---

## Master Architecture

```
                         ┌─────────────────┐
                         │   USER / CLI    │
                         │  Open WebUI     │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  ORCHESTRATOR   │
                         │  (PentAGI Core) │
                         │                 │
                         │  ┌────────────┐ │
                         │  │  Planner   │ │
                         │  └────────────┘ │
                         │  ┌────────────┐ │
                         │  │ Researcher │ │
                         │  └────────────┘ │
                         │  ┌────────────┐ │
                         │  │ Recon Agent│ │
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
                    ┌─────────────┴─────────────┐
                    │                           │
          ┌─────────▼──────────┐    ┌───────────▼─────────┐
          │  LLM GATEWAY       │    │  TOOL GATEWAY       │
          │  (LiteLLM)         │    │  (MCP / Adapters)   │
          │                    │    │                     │
          │  Model Aliases:    │    │  Adapters:          │
          │  - local-reasoner  │    │  - PentAGI          │
          │  - local-coder     │    │  - Strix            │
          │  - local-fast      │    │  - HexStrike        │
          │  - research-model  │    │  - MCPStrike        │
          │  - cloud-reasoner  │    │  - Dark-Moon        │
          │                    │    │  - CAI              │
          │  Providers:        │    │  - PentestGPT       │
          │  - Ollama (local)  │    │  - PentestAgent     │
          │  - OpenAI (cloud)  │    │  - CyberStrikeAI    │
          │  - Anthropic       │    │  - AutoPentest      │
          │  - Custom          │    │  - PenClaw          │
          └────────────────────┘    │  - LuaN1aoAgent     │
                                    │  - ARACNE           │
                                    │  - Guardian-CLI     │
                                    │  - DRAKBEN          │
                                    │  - h4cker (KB)      │
                                    │  - kali-pentest(Skills)│
                                    └───────────┬─────────┘
                                                │
                                  ┌─────────────▼─────────────┐
                                  │   AUTHORIZED LAB          │
                                  │   ┌───────────────────┐   │
                                  │   │  Docker Targets   │   │
                                  │   └───────────────────┘   │
                                  │   ┌───────────────────┐   │
                                  │   │  VM Targets       │   │
                                  │   └───────────────────┘   │
                                  │   ┌───────────────────┐   │
                                  │   │  CTF Challenges   │   │
                                  │   └───────────────────┘   │
                                  └─────────────┬─────────────┘
                                                │
                                  ┌─────────────▼─────────────┐
                                  │   EVIDENCE & MEMORY       │
                                  │   ┌───────────────────┐   │
                                  │   │  SQLite DB        │   │
                                  │   │  (experiences,    │   │
                                  │   │   findings,       │   │
                                  │   │   sessions)       │   │
                                  │   └───────────────────┘   │
                                  │   ┌───────────────────┐   │
                                  │   │  Knowledge Base   │   │
                                  │   │  (CVE, CWE,       │   │
                                  │   │   techniques)     │   │
                                  │   └───────────────────┘   │
                                  └───────────────────────────┘
```

---

## Key Capabilities

### Multi-Model Routing
- **Local Models**: Ollama serves quantized models (Llama 3.1, CodeLlama, Qwen, etc.) for offline operation
- **Cloud Models**: LiteLLM gateway routes to OpenAI, Anthropic, Google, AWS Bedrock, and 100+ providers
- **Model Aliases**: Agents use abstract aliases (`local-reasoner`, `local-coder`, `research-model`) decoupled from specific model names
- **Fallback Chain**: LiteLLM proxy → Direct Ollama → Direct provider API

### Agent Specialization
| Agent | Role | Primary Tools |
|-------|------|---------------|
| **Planner** | Decomposes objectives into actionable steps | PentAGI, AutoPentest |
| **Researcher** | Gathers intelligence on targets | Strix, PentestGPT |
| **Recon** | Network and host discovery | HexStrike, MCPStrike |
| **Analyst** | Correlates findings, identifies patterns | CAI, DRAKBEN |
| **Coder** | Generates exploits and proof-of-concept code | PentAGI, HexStrike |
| **Verifier** | Challenges findings, requires evidence | Built-in verifier |
| **Reporter** | Generates structured reports | Built-in reporter |

### Non-Weight Learning Loop
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

### Safe Execution Layer
- **Docker Isolation**: All active tools execute in containers with network isolation
- **VM Support**: Targets can be isolated virtual machines with snapshots
- **CTF Framework**: Integration with Docker-based CTF platforms (Juice Shop, DVWA, etc.)
- **Network Segmentation**: Lab traffic isolated on dedicated Docker networks
- **Evidence Chain**: All tool outputs captured with timestamps, hashes, and verification status

---

## Quick Start & Setup Guide

### Prerequisites
- Windows 11 / Linux / macOS
- Docker Desktop (for containerized services)
- Python 3.10+ (for orchestrator core)
- Ollama (for local models)
- Git (for repository management)

### Installation

```bash
# 1. Clone the platform (already done)
cd C:\Users\hp\Desktop\cyber

# 2. Set up Python environment
python -m venv .venv
.\.venv\Scripts\activate
pip install -e platform\orchestrator

# 3. Configure environment
copy .env.example .env
# Edit .env with your API keys and preferences

# 4. Install Ollama and pull models
# Download from https://ollama.com
ollama pull llama3.1:8b
ollama pull codellama:7b
ollama pull llama3.2:3b
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# 5. Start infrastructure services
docker compose up -d

# 6. Run health check
python -m cyberai.orchestrator.cli doctor
```

### Configuration

#### Gateway Configuration (`.env`)
```env
# Ollama Local Models
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# LiteLLM Gateway
LITELLM_MASTER_KEY=sk-your-master-key-here
LITELLM_PORT=4000
LITELLM_CONFIG_PATH=platform/llm-gateway/config/config.yaml

# Cloud Providers (Optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...

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

### Running the Platform

#### Start Infrastructure
```bash
# Start LiteLLM, Ollama, Open WebUI
docker compose up -d

# Verify services
docker compose ps
```

#### Use the CLI
```bash
# Check status
python -m cyberai.orchestrator.cli status

# List available tools
python -m cyberai.orchestrator.cli tools

# List lab targets
python -m cyberai.orchestrator.cli lab list

# Run assessment (requires authorized target)
python -m cyberai.orchestrator.cli assess lab-web-01 --objective "Find SQL injection vulnerabilities"

# Search memory for past experiences
python -m cyberai.orchestrator.cli memory search "SQL injection"

# Run health check
python -m cyberai.orchestrator.cli doctor
```

#### Open WebUI
```bash
# Access at http://localhost:3000
# Configure to use LiteLLM endpoint: http://localhost:4000
```

---

## Ethical & Safety Boundaries

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

## Repository Integration Map

| Original Repository | Local Path | Role | Integration Method |
|---------------------|------------|------|-------------------|
| **litellm** | `infrastructure/litellm/` | LLM Gateway | Service (Docker) |
| **ollama** | `infrastructure/ollama/` | Local Models | Service (Docker) |
| **open-webui** | `infrastructure/open-webui/` | Human UI | Service (Docker) |
| **airllm** | `infrastructure/airllm/` | Alternate Inference | Library |
| **pentagi** | `adapters/pentagi/` | Primary Security Agent | REST/GraphQL API |
| **strix** | `adapters/strix/` | Assessment Agent | Server API |
| **darkmoon** | `adapters/darkmoon/` | Pentesting Agent | MCP Server |
| **hexstrike-ai** | `adapters/hexstrike/` | Tool Gateway (150+ tools) | Flask REST + MCP |
| **mcpstrike** | `adapters/mcpstrike/` | Ollama MCP Gateway | FastAPI + MCP |
| **CAI** | `adapters/cai/` | Agent Framework | Python Library |
| **pentestgpt** | `adapters/pentestgpt/` | Research/Planning | CLI Wrapper |
| **pentestagent** | `adapters/pentestagent/` | Security Agent | CLI + MCP |
| **CyberStrikeAI** | `adapters/cyberstrikeai/` | MCP Tools | Gin REST + MCP |
| **autopentest** | `adapters/autopentest/` | Research/Planning | CLI (LangChain) |
| **penclaw** | `adapters/penclaw/` | Static/Dynamic Analysis | CLI (Node.js) |
| **LuaN1aoAgent** | `adapters/luan1aoagent/` | Cognitive Agent | CLI/Web (Node.js) |
| **aracne** | `adapters/aracne/` | SSH-Driven Pentesting | CLI (Python/SSH) |
| **guardian-cli** | `adapters/guardian-cli/` | CLI Pentesting | CLI (Python) |
| **drakben** | `adapters/drakben/` | Autonomous Pentesting | CLI (Python/async) |
| **h4cker** | `adapters/h4cker/` | Knowledge Base | Documentation |
| **kali-pentest** | `adapters/kali-pentest/` | Skill Definitions | Documentation |

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Orchestrator** | Python 3.10+, asyncio | Core coordination and agent management |
| **LLM Gateway** | LiteLLM, FastAPI | Unified model routing and proxy |
| **Local Models** | Ollama | Quantized model serving (Llama, CodeLlama, Qwen) |
| **Tool Gateway** | FastMCP, MCP Protocol | Tool discovery and execution |
| **Adapters** | Python, Go, Node.js | Integration wrappers for external tools |
| **Memory** | SQLite, JSON | Experience and finding storage |
| **Lab** | Docker, Docker Compose | Isolated execution environments |
| **UI** | Open WebUI, Click CLI | Human interfaces |
| **Monitoring** | Structured logging, JSONL | Audit trails and debugging |

---

## Project Structure

```
C:\Users\hp\Desktop\cyber/
├── README.md                    # This file
├── ARCHITECTURE.md              # Deep-dive technical reference
├── WORKSPACE_INVENTORY.md       # Detailed repository inventory
├── REPOSITORY_MAP.yaml          # Repository-to-role mapping
├── INTEGRATION_STATUS.md        # Component status tracking
├── FINAL_STATUS.md              # Final delivery report
├── .env.example                 # Environment configuration template
├── .gitignore                   # Git ignore rules
├── docker-compose.yml           # Infrastructure services
│
├── platform/                    # Core platform code
│   ├── orchestrator/            # Master orchestrator
│   │   ├── agents/              # AI agent implementations
│   │   ├── routing/             # Model and tool routing
│   │   ├── memory/              # Experience storage
│   │   ├── policies/            # Authorization and safety
│   │   ├── scheduler/           # Task scheduling
│   │   ├── workflows/           # Predefined assessment flows
│   │   ├── api/                 # REST API server
│   │   ├── evidence/            # Evidence collection
│   │   ├── knowledge/           # Knowledge base loader
│   │   └── cli/                 # Command-line interface
│   │
│   ├── llm-gateway/             # LiteLLM integration
│   │   ├── models/              # Model registry
│   │   ├── config/              # LiteLLM configuration
│   │   └── logs/                # Gateway logs
│   │
│   ├── tool-gateway/            # MCP tool discovery
│   │   └── mcp/                 # MCP server management
│   │
│   └── ui/                      # UI package (future)
│
├── adapters/                    # Security tool adapters
│   ├── pentagi/                 # Primary pentesting agent
│   ├── strix/                   # Assessment agent
│   ├── darkmoon/                # MCP pentesting agent
│   ├── hexstrike/               # MCP tool gateway
│   ├── mcpstrike/               # Ollama MCP gateway
│   ├── cai/                     # Agent framework
│   ├── pentestgpt/              # Research/planning
│   ├── pentestagent/            # LiteLLM-based agent
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
├── infrastructure/              # Infrastructure services
│   ├── ollama/                  # Ollama models and config
│   ├── open-webui/              # Open WebUI data
│   ├── airllm/                  # AirLLM inference
│   └── other-inference/         # Additional inference engines
│
├── lab/                         # Isolated lab environment
│   ├── targets/                 # Authorized target registry
│   │   └── targets.yaml         # Target definitions
│   ├── docker/                  # Docker Compose stacks
│   ├── networks/                # Network definitions
│   ├── snapshots/               # VM/target snapshots
│   ├── scenarios/               # Pre-built assessment scenarios
│   └── evidence/                # Collected evidence files
│
├── knowledge/                   # Security knowledge base
│   ├── cve/                     # CVE database
│   ├── cwe/                     # CWE weakness taxonomy
│   ├── advisories/              # Security advisories
│   ├── techniques/              # ATT&CK techniques
│   ├── research/                # Security research papers
│   └── documentation/           # Tool documentation
│
├── memory/                      # Persistent memory
│   ├── memory.db                # SQLite database
│   ├── embeddings/              # Vector embeddings
│   ├── findings/                # Individual findings
│   ├── failures/                # Failed strategies
│   ├── successful-strategies/   # Successful tactics
│   ├── observations/            # Agent observations
│   └── sessions/                # Session logs
│
├── logs/                        # Platform logs
│   └── sessions/                # Per-session logs
│
├── projects/                    # Additional projects
│   ├── security-agents/         # Custom security agents
│   ├── research-tools/          # Research utilities
│   ├── analysis-tools/          # Analysis scripts
│   └── legacy/                  # Legacy integrations
│
├── scripts/                     # Utility scripts
│   └── generate_platform.py     # Platform generator
│
├── backups/                     # Backup storage
└── tests/                       # Test suite
```

---

## Getting Started

### 1. Verify Installation
```bash
python -m cyberai.orchestrator.cli doctor
```

Expected output:
```
[OK] Python: 3.10.11
[OK] Git: git version 2.49.0.windows.1
[WARN] Docker: not installed (expected on fresh install)
[WARN] Ollama: not running
[OK] Repositories: 17 tracked adapters
[WARN] Adapters: 15/17 have Python wrappers
[OK] MCP Gateway: configured
[OK] Memory system: DB ready
[OK] Policy engine: 0 targets registered
```

### 2. Install Dependencies
```bash
# Install Docker Desktop from https://docker.com
# Install Ollama from https://ollama.com
# Pull required models
ollama pull llama3.1:8b
ollama pull codellama:7b
```

### 3. Configure Environment
```bash
copy .env.example .env
# Add your API keys to .env
```

### 4. Start Services
```bash
docker compose up -d
```

### 5. Register Lab Target
```yaml
# lab/targets/targets.yaml
targets:
  - id: juice-shop
    environment: authorized_lab
    allowed: true
    host: 127.0.0.1
    port: 3000
    description: OWASP Juice Shop
    allowed_actions: [recon, scan, analysis, exploitation]
```

### 6. Run First Assessment
```bash
python -m cyberai.orchestrator.cli assess juice-shop --objective "Identify injection vulnerabilities"
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | This file - platform overview and quick start |
| `ARCHITECTURE.md` | Deep-dive technical reference |
| `WORKSPACE_INVENTORY.md` | Detailed repository inventory |
| `REPOSITORY_MAP.yaml` | Repository-to-role mapping |
| `INTEGRATION_STATUS.md` | Component status tracking |
| `FINAL_STATUS.md` | Final delivery report |
| `.env.example` | Environment configuration template |

---

## Support & Contributing

- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Join community discussions for use cases and integrations
- **Contributing**: See `CONTRIBUTING.md` in individual repositories

---

## License

This platform structure is provided as-is. Individual components retain their original licenses. See `REPOSITORY_MAP.yaml` for details.

**Primary Licenses:**
- MIT: litellm, hexstrike-ai, mcpstrike, pentestgpt, pentestagent, strix, drakben
- Apache 2.0: ollama, open-webui, strix
- GPL v3: Dark-Moon
- Dual MIT + Proprietary: CAI
- AGPL v3: LuaN1aoAgent

---

## Acknowledgments

This platform integrates the following open-source security research projects:
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

**Status**: Platform structure complete and ready for deployment. Awaiting Docker, Ollama, and API key configuration for full operational capability.