#!/usr/bin/env python3
"""
CERBERUS — Unified System Scaffolding Script
============================================
Creates all missing data models, physical database folders, configuration
files, and target profiles required for the platform to run.

Run:  python scaffold_system.py
"""

import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WORKSPACE_ROOT = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# 1. Directory structure
# ---------------------------------------------------------------------------
DIRECTORIES = [
    "memory/embeddings",
    "memory/evolution/population",
    "memory/evolution/elite",
    "memory/evolution/failures",
    "memory/findings",
    "memory/failures",
    "memory/observations",
    "memory/successful-strategies",
    "memory/sessions",
    "logs/sessions",
    "logs/tasks",
    "logs/models",
    "logs/agents",
    "logs/evolution",
    "lab/targets",
    "lab/docker",
    "lab/networks",
    "lab/snapshots",
    "lab/scenarios",
    "lab/evidence",
    "knowledge/cve",
    "knowledge/cwe",
    "knowledge/advisories",
    "knowledge/techniques",
    "knowledge/research",
    "knowledge/documentation",
    "cyberai/llm-gateway/config",
    "cyberai/llm-gateway/models",
    "cyberai/tool-gateway/mcp",
    "backups",
]

# ---------------------------------------------------------------------------
# 2. .env content
# ---------------------------------------------------------------------------
ENV_CONTENT = """# ============================================================
# CERBERUS — Cyber AI Orchestrator Environment Configuration
# ============================================================
# Copy this file to .env and fill in your values.
# NEVER commit real secrets.

# ==================== CORE ====================
PLATFORM_NAME=CERBERUS
LOG_LEVEL=INFO
PRIVACY_MODE=local_only

# ==================== OLLAMA (LOCAL LLM) ====================
# Local model service — maps abstract aliases to real Ollama calls
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.1:8b

# Model alias → Ollama model mapping
LOCAL_REASONER_MODEL=llama3.1:8b
LOCAL_CODER_MODEL=codellama:7b
LOCAL_FAST_MODEL=llama3.2:3b
RESEARCH_MODEL=qwen2.5:7b
EMBEDDINGS_MODEL=nomic-embed-text

# ==================== LITELLM GATEWAY ====================
LITELLM_MASTER_KEY=sk-cerberus-local-master-key
LITELLM_PORT=4000
LITELLM_HOST=127.0.0.1
LITELLM_CONFIG_PATH=cyberai/llm-gateway/config/config.yaml

# ==================== FASTAPI API SERVER ====================
API_HOST=127.0.0.1
API_PORT=8000

# ==================== CLOUD LLM PROVIDERS (OPTIONAL) ====================
# Only add keys if you want to use cloud providers through the gateway
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=

# ==================== OPEN WEBUI ====================
OPEN_WEBUI_PORT=3000
OPEN_WEBUI_HOST=127.0.0.1

# ==================== MEMORY ====================
MEMORY_DB_PATH=memory/memory.db
EXPERIENCES_DB_PATH=memory/experiences.db
PERFORMANCE_DB_PATH=memory/performance.db

# ==================== LAB ====================
LAB_TARGETS_PATH=lab/targets/targets.yaml
LAB_NETWORK=cyber-lab-net
REQUIRE_TARGET_AUTHORIZATION=true

# ==================== SECURITY ====================
ALLOWED_HOSTS=127.0.0.1,localhost
"""

# ---------------------------------------------------------------------------
# 3. targets.yaml content
# ---------------------------------------------------------------------------
TARGETS_CONTENT = """# ============================================================
# CERBERUS — Authorized Lab Targets
# ============================================================
# Only targets listed here with allowed: true can be actively tested.
# All other targets are refused by the policy engine.
#
# Schema:
#   id:              Unique target identifier
#   environment:     Must be 'authorized_lab'
#   allowed:         Must be true for active testing
#   host:            IP or hostname
#   port:            Service port
#   protocol:        http, https, tcp, udp
#   description:     Human-readable description
#   allowed_actions: Explicit array of permitted actions
#                    (recon, scan, analysis, exploitation, verification)
#   metadata:        Optional key-value pairs

targets:
  # --- OWASP Juice Shop (Docker container on localhost) ---
  - id: juice-shop
    environment: authorized_lab
    allowed: true
    host: 127.0.0.1
    port: 8080
    protocol: http
    description: OWASP Juice Shop — intentionally vulnerable web application
    allowed_actions:
      - recon
      - scan
      - analysis
      - exploitation
      - verification
    metadata:
      docker_image: bkimminich/juice-shop
      docker_port: "3000:8080"
      category: web_application
      difficulty: medium

  # --- DVWA (Damn Vulnerable Web Application) ---
  - id: dvwa
    environment: authorized_lab
    allowed: true
    host: 127.0.0.1
    port: 8081
    protocol: http
    description: Damn Vulnerable Web Application — PHP/MySQL vulnerable app
    allowed_actions:
      - recon
      - scan
      - analysis
      - exploitation
      - verification
    metadata:
      docker_image: vulnerables/web-dvwa
      docker_port: "80:8081"
      category: web_application
      difficulty: easy

  # --- Metasploitable 2 (VM target) ---
  - id: metasploitable2
    environment: authorized_lab
    allowed: true
    host: 192.168.56.101
    port: 22
    protocol: tcp
    description: Metasploitable 2 — intentionally vulnerable Linux VM
    allowed_actions:
      - recon
      - scan
      - analysis
      - exploitation
      - verification
    metadata:
      vm_image: metasploitable2
      category: linux_vm
      difficulty: easy

  # --- Local web lab (generic authorized target) ---
  - id: lab-web-01
    environment: authorized_lab
    allowed: true
    host: 127.0.0.1
    port: 8080
    protocol: http
    description: Local authorized web application lab target
    allowed_actions:
      - recon
      - scan
      - analysis
      - verification
    metadata:
      category: web_application
      difficulty: easy
"""

# ---------------------------------------------------------------------------
# 4. SQLite schema definitions (compatible with MemoryManager + enriched)
# ---------------------------------------------------------------------------
MEMORY_SCHEMA = """
-- ============================================================
-- CERBERUS — Memory Database Schema (memory.db)
-- ============================================================

-- Experiences table: records what happened during assessments
CREATE TABLE IF NOT EXISTS experiences (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    target_id TEXT,
    target_type TEXT,
    environment TEXT DEFAULT 'authorized_lab',
    observation TEXT NOT NULL,
    hypothesis TEXT,
    action TEXT,
    tool TEXT,
    result TEXT,
    evidence TEXT,
    confidence REAL DEFAULT 0.0,
    lessons TEXT,
    score REAL DEFAULT 0.0,
    verification TEXT DEFAULT 'UNVERIFIED',
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_experiences_session ON experiences (session_id);
CREATE INDEX IF NOT EXISTS idx_experiences_target ON experiences (target_id);
CREATE INDEX IF NOT EXISTS idx_experiences_tool ON experiences (tool);
CREATE INDEX IF NOT EXISTS idx_experiences_result ON experiences (result);
CREATE INDEX IF NOT EXISTS idx_experiences_ts ON experiences (timestamp);

-- Findings table: compatible with MemoryManager (observation/evidence/status)
-- plus enriched columns (description/verification/severity)
CREATE TABLE IF NOT EXISTS findings (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    target_id TEXT,
    observation TEXT,
    description TEXT,
    evidence TEXT,
    evidence_ids TEXT,
    source TEXT,
    status TEXT DEFAULT 'UNVERIFIED',
    verification TEXT DEFAULT 'UNVERIFIED',
    severity TEXT DEFAULT 'info',
    confidence REAL DEFAULT 0.0,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_findings_session ON findings (session_id);
CREATE INDEX IF NOT EXISTS idx_findings_target ON findings (target_id);
CREATE INDEX IF NOT EXISTS idx_findings_status ON findings (status);
CREATE INDEX IF NOT EXISTS idx_findings_verification ON findings (verification);

-- Sessions table: compatible with MemoryManager (target_id/started_at/status)
-- plus enriched columns (objective/agents_used/tools_used/models_used)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    target_id TEXT,
    objective TEXT,
    environment TEXT DEFAULT 'authorized_lab',
    status TEXT DEFAULT 'created',
    agents_used TEXT,
    tools_used TEXT,
    models_used TEXT,
    findings_count INTEGER DEFAULT 0,
    evidence_count INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    summary TEXT,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions (status);
CREATE INDEX IF NOT EXISTS idx_sessions_target ON sessions (target_id);

-- Memories table: typed memory store (episodic, semantic, procedural, etc.)
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT PRIMARY KEY,
    memory_type TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,
    confidence REAL DEFAULT 0.0,
    success_rate REAL DEFAULT 0.0,
    verification TEXT DEFAULT 'UNVERIFIED',
    timestamp TEXT NOT NULL,
    last_accessed TEXT,
    access_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories (memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_ts ON memories (timestamp);
CREATE INDEX IF NOT EXISTS idx_memories_verification ON memories (verification);
"""

PERFORMANCE_SCHEMA = """
-- ============================================================
-- CERBERUS — Performance Database Schema (performance.db)
-- ============================================================

-- Performance records: tracks every model/agent/tool/strategy call
CREATE TABLE IF NOT EXISTS performance (
    record_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    capability TEXT,
    success INTEGER DEFAULT 0,
    verification TEXT DEFAULT 'UNVERIFIED',
    latency REAL DEFAULT 0.0,
    token_usage INTEGER DEFAULT 0,
    quality_score REAL DEFAULT 0.0,
    environment TEXT DEFAULT 'authorized_lab',
    target_type TEXT,
    timestamp TEXT NOT NULL,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_perf_entity ON performance (entity_type, entity_name, task_type);
CREATE INDEX IF NOT EXISTS idx_perf_task ON performance (task_type);
CREATE INDEX IF NOT EXISTS idx_perf_success ON performance (success);
CREATE INDEX IF NOT EXISTS idx_perf_ts ON performance (timestamp);

-- Latency tracking view
CREATE VIEW IF NOT EXISTS v_latency_stats AS
SELECT
    entity_type,
    entity_name,
    task_type,
    COUNT(*) as calls,
    AVG(latency) as avg_latency,
    MIN(latency) as min_latency,
    MAX(latency) as max_latency,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
FROM performance
GROUP BY entity_type, entity_name, task_type;

-- Verification status tracking view
CREATE VIEW IF NOT EXISTS v_verification_stats AS
SELECT
    entity_type,
    entity_name,
    task_type,
    COUNT(*) as total,
    SUM(CASE WHEN verification = 'VERIFIED' THEN 1 ELSE 0 END) as verified,
    SUM(CASE WHEN verification = 'LIKELY' THEN 1 ELSE 0 END) as likely,
    SUM(CASE WHEN verification = 'UNVERIFIED' THEN 1 ELSE 0 END) as unverified,
    SUM(CASE WHEN verification = 'REJECTED' THEN 1 ELSE 0 END) as rejected
FROM performance
GROUP BY entity_type, entity_name, task_type;

-- Success rate tracking view
CREATE VIEW IF NOT EXISTS v_success_stats AS
SELECT
    entity_type,
    entity_name,
    task_type,
    COUNT(*) as calls,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
    ROUND(SUM(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) / COUNT(*), 4) as success_rate,
    AVG(quality_score) as avg_quality
FROM performance
GROUP BY entity_type, entity_name, task_type;
"""


# ---------------------------------------------------------------------------
# 5. Scaffold functions
# ---------------------------------------------------------------------------
def create_directories() -> None:
    """Create all required directory structure."""
    print("[1/6] Creating directory structure...")
    for d in DIRECTORIES:
        path = WORKSPACE_ROOT / d
        path.mkdir(parents=True, exist_ok=True)
    print(f"  [OK] Created {len(DIRECTORIES)} directories")


def create_env_file() -> None:
    """Create the active .env file."""
    print("[2/6] Creating .env configuration...")
    env_path = WORKSPACE_ROOT / ".env"
    if env_path.exists():
        print("  [WARN] .env already exists — skipping (remove it to regenerate)")
        return
    env_path.write_text(ENV_CONTENT, encoding="utf-8")
    print(f"  [OK] Created {env_path}")


def create_targets_file() -> None:
    """Create the pre-populated targets.yaml file."""
    print("[3/6] Creating lab/targets/targets.yaml...")
    targets_path = WORKSPACE_ROOT / "lab" / "targets" / "targets.yaml"
    targets_path.parent.mkdir(parents=True, exist_ok=True)
    targets_path.write_text(TARGETS_CONTENT, encoding="utf-8")
    print(f"  [OK] Created {targets_path} with 4 authorized targets")


def create_databases() -> None:
    """Create physical SQLite databases with full schemas."""
    print("[4/6] Creating physical SQLite databases...")

    # memory.db — experiences, findings, sessions, memories
    memory_db = WORKSPACE_ROOT / "memory" / "memory.db"
    if memory_db.exists():
        memory_db.unlink()
        print("    (Removed existing memory.db for schema migration)")
    conn = sqlite3.connect(str(memory_db))
    conn.executescript(MEMORY_SCHEMA)
    conn.commit()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    views = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
    ).fetchall()]
    conn.close()
    print(f"  [OK] Created {memory_db}")
    print(f"    Tables: {', '.join(tables)}")
    print(f"    Views: {', '.join(views) if views else 'none'}")

    # experiences.db — typed memory store
    experiences_db = WORKSPACE_ROOT / "memory" / "experiences.db"
    if experiences_db.exists():
        experiences_db.unlink()
        print("    (Removed existing experiences.db for schema migration)")
    conn = sqlite3.connect(str(experiences_db))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS memories (
            memory_id TEXT PRIMARY KEY,
            memory_type TEXT,
            content TEXT,
            metadata TEXT,
            confidence REAL,
            success_rate REAL,
            verification TEXT,
            timestamp TEXT,
            last_accessed TEXT,
            access_count INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_memories_type ON memories (memory_type);
        CREATE INDEX IF NOT EXISTS idx_memories_ts ON memories (timestamp);
    """)
    conn.commit()
    conn.close()
    print(f"  [OK] Created {experiences_db}")

    # performance.db — meta-learning performance cache
    perf_db = WORKSPACE_ROOT / "memory" / "performance.db"
    if perf_db.exists():
        perf_db.unlink()
        print("    (Removed existing performance.db for schema migration)")
    conn = sqlite3.connect(str(perf_db))
    conn.executescript(PERFORMANCE_SCHEMA)
    conn.commit()
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    views = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
    ).fetchall()]
    conn.close()
    print(f"  [OK] Created {perf_db}")
    print(f"    Tables: {', '.join(tables)}")
    print(f"    Views: {', '.join(views)}")


def create_llm_gateway_config() -> None:
    """Create the LiteLLM gateway configuration files."""
    print("[5/6] Creating LLM gateway configuration...")

    # models.yaml — model registry
    models_path = WORKSPACE_ROOT / "cyberai" / "llm-gateway" / "models" / "models.yaml"
    models_path.parent.mkdir(parents=True, exist_ok=True)
    models_content = """# CERBERUS — Model Registry
# Maps abstract model aliases to concrete provider/model pairs.

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

  local_fast:
    provider: ollama
    default_model: llama3.2:3b
    purpose: [classification, summarization, tool_selection]
    status: REQUIRES_MODEL_DOWNLOAD

  research_model:
    provider: ollama
    default_model: qwen2.5:7b
    purpose: [web_research, vulnerability_research, cve_analysis]
    status: REQUIRES_MODEL_DOWNLOAD

  embeddings:
    provider: ollama
    default_model: nomic-embed-text
    purpose: [semantic_memory_retrieval, knowledge_embedding]
    status: REQUIRES_MODEL_DOWNLOAD

  cloud_reasoner:
    provider: openai
    default_model: gpt-4o
    purpose: [complex_reasoning, advanced_planning]
    status: DISABLED_NO_API_KEY

  cloud_fast:
    provider: anthropic
    default_model: claude-3-5-haiku-latest
    purpose: [fast_analysis, classification]
    status: DISABLED_NO_API_KEY
"""
    models_path.write_text(models_content, encoding="utf-8")
    print(f"  [OK] Created {models_path}")

    # config.yaml — LiteLLM proxy config
    config_path = WORKSPACE_ROOT / "cyberai" / "llm-gateway" / "config" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_content = """# CERBERUS — LiteLLM Proxy Configuration
model_list:
  - model_name: local_reasoner
    litellm_params:
      model: ollama/llama3.1:8b
      api_base: http://127.0.0.1:11434

  - model_name: local_coder
    litellm_params:
      model: ollama/codellama:7b
      api_base: http://127.0.0.1:11434

  - model_name: local_fast
    litellm_params:
      model: ollama/llama3.2:3b
      api_base: http://127.0.0.1:11434

  - model_name: research_model
    litellm_params:
      model: ollama/qwen2.5:7b
      api_base: http://127.0.0.1:11434

  - model_name: embeddings
    litellm_params:
      model: ollama/nomic-embed-text
      api_base: http://127.0.0.1:11434

litellm_settings:
  drop_params: true
  set_verbose: false

general_settings:
  master_key: sk-cerberus-local-master-key
  database_url: sqlite:///memory/litellm.db
"""
    config_path.write_text(config_content, encoding="utf-8")
    print(f"  [OK] Created {config_path}")


def create_routing_config() -> None:
    """Create the model routing configuration."""
    print("[6/6] Creating routing configuration...")
    routing_path = WORKSPACE_ROOT / "cyberai" / "orchestrator" / "routing" / "routing.yaml"
    routing_path.parent.mkdir(parents=True, exist_ok=True)
    routing_content = """# CERBERUS — Model Routing Configuration
# Maps task types to model aliases with fallback chains.

routes:
  planning:
    preferred: local_reasoner
    fallback: local_fast
    local_fallback: local_fast

  reasoning:
    preferred: local_reasoner
    fallback: local_fast
    local_fallback: local_fast

  vulnerability_research:
    preferred: research_model
    fallback: local_reasoner
    local_fallback: local_fast

  web_research:
    preferred: research_model
    fallback: local_reasoner
    local_fallback: local_fast

  code_analysis:
    preferred: local_coder
    fallback: local_reasoner
    local_fallback: local_fast

  code_generation:
    preferred: local_coder
    fallback: local_reasoner
    local_fallback: local_fast

  classification:
    preferred: local_fast
    fallback: local_reasoner
    local_fallback: local_fast

  summarization:
    preferred: local_fast
    fallback: local_reasoner
    local_fallback: local_fast

  verification:
    preferred: local_reasoner
    fallback: local_fast
    local_fallback: local_fast

  report_generation:
    preferred: local_fast
    fallback: local_reasoner
    local_fallback: local_fast

  tool_selection:
    preferred: local_fast
    fallback: local_reasoner
    local_fallback: local_fast

  default:
    preferred: local_reasoner
    fallback: local_fast
    local_fallback: local_fast
"""
    routing_path.write_text(routing_content, encoding="utf-8")
    print(f"  [OK] Created {routing_path}")


def main() -> None:
    """Run the full scaffolding process."""
    print("=" * 60)
    print("  CERBERUS — Unified System Scaffolding")
    print("=" * 60)
    print()

    create_directories()
    create_env_file()
    create_targets_file()
    create_databases()
    create_llm_gateway_config()
    create_routing_config()

    print()
    print("=" * 60)
    print("  Scaffolding complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Install dependencies:  pip install -r requirements.txt")
    print("  2. Start Ollama:          ollama serve")
    print("  3. Pull models:           ollama pull llama3.1:8b")
    print("  4. Run health check:      python -m cyberai.orchestrator.cli doctor")
    print("  5. Run simulation:        python -m cyberai.orchestrator.cli simulate")
    print()


if __name__ == "__main__":
    main()