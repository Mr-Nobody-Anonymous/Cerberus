"""CLI surface tests — click.testing.CliRunner over the ``cyber-ai`` command group.

Covers the primary user surface (``cyberai/orchestrator/cli/cli.py``):

- Output modes: ``--json`` / ``--quiet`` / ``--no-color`` / ``--version`` / ``--help``
- Read-only commands: agents, tools, adapters, lab list/status, workflow,
  config, history, intel, blueprint, replay, report, scorecard, mem,
  wargame, killchain, doctor, profile, watch (bounded), benchmark
- Heavy-dependency commands (task/assess/simulate/status/models/hunt,
  mcp *, lab start/stop) run against lightweight fakes so no network
  probes, Docker, or full orchestrator construction happen in tests.

Isolation strategy
------------------
- All writable platform resources (memory/experiences/performance DBs,
  evolution dir) are redirected into pytest's ``tmp_path`` by patching
  the config singleton's data — every constructor resolves its path at
  call time, so this is sufficient.
- Kill-chain state is redirected by patching ``WORKSPACE_ROOT`` inside
  the ``kill_chain`` module (the engine resolves its state file at call
  time).
- ``lab register`` runs against a tmp copy of the real targets file so
  the repository's ``lab/targets/targets.yaml`` is never rewritten.
"""

import json
import os
import re
import shutil

import pytest
from click.testing import CliRunner

from cyberai.config import WORKSPACE_ROOT, config
from cyberai.orchestrator.cli.cli import cli


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def iso(monkeypatch, tmp_path):
    """Redirect every writable platform resource into tmp_path."""
    monkeypatch.setitem(config._data["memory"], "db_path",
                        str(tmp_path / "memory.db"))
    monkeypatch.setitem(config._data["memory"], "experiences_db_path",
                        str(tmp_path / "experiences.db"))
    monkeypatch.setitem(config._data["memory"], "performance_db_path",
                        str(tmp_path / "performance.db"))
    monkeypatch.setitem(config._data["memory"], "evolution_dir",
                        str(tmp_path / "evolution"))
    return tmp_path


@pytest.fixture()
def killchain_tmp(monkeypatch, tmp_path):
    """Redirect kill-chain state (lab/state/kill_chains.json) into tmp_path."""
    monkeypatch.setattr(
        "cyberai.orchestrator.workflows.kill_chain.WORKSPACE_ROOT", tmp_path)
    return tmp_path


@pytest.fixture()
def tmp_targets(monkeypatch, tmp_path):
    """Point the policy engine at a tmp copy of the real targets file."""
    src = WORKSPACE_ROOT / "lab" / "targets" / "targets.yaml"
    dst = tmp_path / "targets.yaml"
    shutil.copy(src, dst)
    monkeypatch.setitem(config._data["policy"], "targets_path", str(dst))
    return dst


def _seed_memory():
    """Seed the isolated memory DB: 1 session, 2 findings, 1 experience.

    Returns the session id.
    """
    from cyberai.orchestrator import MemoryManager

    mm = MemoryManager()
    try:
        sid = mm.create_session("juice-shop", "Test objective")
        mm.store_finding({
            "session_id": sid, "target_id": "juice-shop",
            "observation": "nginx 1.18.0 detected on juice-shop",
            "status": "VERIFIED", "confidence": 0.9, "source": "recon",
        })
        mm.store_finding({
            "session_id": sid, "target_id": "juice-shop",
            "observation": "default admin page exposed",
            "status": "UNVERIFIED", "confidence": 0.4, "source": "recon",
        })
        mm.store_experience({
            "session_id": sid, "target_id": "juice-shop",
            "observation": "nginx version header disclosed on juice-shop",
            "hypothesis": "h", "action": "banner grab", "tool": "nmap",
            "result": "success", "confidence": 0.8,
        })
        return sid
    finally:
        mm.close()


def _seed_mem_store():
    """Seed the isolated typed-memory store with two entries."""
    from cyberai.memory.memory_store import MemoryStore

    ms = MemoryStore()
    try:
        ms.store_simple("semantic",
                        "SQL injection authentication bypass via union select",
                        confidence=0.8)
        ms.store_simple("failure", "nmap scan timed out on hardened host",
                        confidence=0.5)
    finally:
        ms.close()


def _seed_failure(iso_path):
    """Seed one failure record into the isolated evolution dir."""
    from cyberai.evolution.engine import EvolutionEngine
    from cyberai.evolution.strategy import Strategy

    eng = EvolutionEngine(evolution_dir=iso_path / "evolution",
                          simulate=True)
    eng.record_failure(
        Strategy(description="aggressive nmap sweep", tools=["nmap"]),
        reason="nmap crashed mid-scan",
        failure_category="tool_unavailable",
    )


# ---------------------------------------------------------------------------
# Lightweight fakes for heavy dependencies
# ---------------------------------------------------------------------------

class _FakeOrchestrator:
    """Stands in for the heavy CyberAIOrchestrator."""

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs

    async def run(self, objective, target_id=None, scope=None):
        return {
            "status": "completed",
            "objective": objective,
            "target_id": target_id,
            "scope": scope,
            "findings": [{"observation": "fake finding"}],
            "final_report": {"content": "# fake report"},
        }

    def get_status(self):
        return {"platform": "Cyber AI", "version": "2.0.0",
                "local_only": True}

    def close(self):
        pass


class _DenyingOrchestrator:
    """Orchestrator whose run() refuses authorization."""

    def __init__(self, *args, **kwargs):
        pass

    async def run(self, objective, target_id=None, scope=None):
        raise PermissionError("target 'x' is not in the authorized lab")

    def close(self):
        pass


class _FakeLLMGateway:
    """Stands in for the network-probing LLMGateway."""

    async def health_check(self):
        return {"ollama": "down", "litellm": "down"}

    def list_registry(self):
        return [{
            "alias": "local-fast", "provider": "ollama",
            "model": "llama3.1:8b", "status": "READY",
            "purpose": "fast", "capabilities": ["chat"],
            "locality": "local",
        }]


class _FakeLabManager:
    """Stands in for LabManager (no Docker / subprocess / state writes)."""

    start_result = {"status": "RUNNING", "mode": "mock",
                    "host": "127.0.0.1", "port": 8080}
    stop_result = {"status": "STOPPED", "mode": "mock",
                    "message": "stopped"}

    def __init__(self, *args, **kwargs):
        pass

    def docker_available(self):
        return False

    async def start_target(self, target_id, force=False):
        return dict(self.start_result)

    async def stop_target(self, target_id):
        return dict(self.stop_result)

    def close(self):
        pass


class _FakeMCPGateway:
    """Stands in for the subprocess-probing MCPGateway."""

    def __init__(self):
        self._servers = {"preconfigured": {"type": "stdio"}}
        self.registered = {}

    def discover_mcp_servers(self):
        return [{"name": "fake-mcp", "type": "stdio",
                 "capabilities": ["tool_execution"]}]

    def register_server(self, name, cfg):
        self.registered[name] = cfg
        self._servers[name] = cfg

    async def health_check_all(self):
        return {"fake-mcp": {"status": "HEALTHY", "message": "responds"}}

    async def list_server_tools(self, server):
        if server == "fake-mcp":
            return {"status": "SUCCESS", "tools": [
                {"name": "nmap_scan", "description": "Run nmap"}]}
        return {"status": "OFFLINE", "error": "server unreachable"}

    async def call_tool(self, server, tool, args, timeout=60.0):
        return {"status": "SUCCESS", "server": server, "tool": tool,
                "args": args, "result": "ok"}


class _UnauthorizedPolicyEngine:
    """PolicyEngine stub whose targets are never allowed."""

    def __init__(self, *args, **kwargs):
        pass

    def get_target(self, target_id):
        return {"id": target_id, "allowed": False,
                "host": "127.0.0.1", "port": 1234}

    def close(self):
        pass


# ---------------------------------------------------------------------------
# Group basics & output modes
# ---------------------------------------------------------------------------

def test_version(runner):
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "2.0.0" in result.output


def test_help_lists_commands(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for cmd in ("task", "doctor", "killchain", "wargame", "workflow",
                "scorecard", "lab", "mcp", "mem"):
        assert cmd in result.output


def test_quiet_suppresses_output(runner):
    result = runner.invoke(cli, ["--quiet", "agents"])
    assert result.exit_code == 0
    assert result.output == ""


def test_no_color_sets_env(runner):
    try:
        result = runner.invoke(cli, ["--no-color", "agents"])
        assert result.exit_code == 0
        assert "planner" in result.output
        assert os.environ.get("NO_COLOR") == "1"
    finally:
        # The group callback writes os.environ directly — restore it.
        os.environ.pop("NO_COLOR", None)


def test_json_mode_agents(runner):
    result = runner.invoke(cli, ["--json", "agents"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    names = {a["name"] for a in data["agents"]}
    assert names == {"planner", "researcher", "recon", "analyst",
                     "coder", "verifier", "reporter"}


# ---------------------------------------------------------------------------
# agents / tools / adapters
# ---------------------------------------------------------------------------

def test_agents_roster(runner):
    result = runner.invoke(cli, ["agents"])
    assert result.exit_code == 0
    assert "planner:" in result.output
    assert "verifier:" in result.output
    assert "reporter:" in result.output


def test_tools_lists_registry(runner):
    result = runner.invoke(cli, ["tools"])
    assert result.exit_code == 0
    assert "pentagi:" in result.output
    assert "type=security_agent" in result.output


def test_tools_verbose_total(runner):
    result = runner.invoke(cli, ["--verbose", "tools"])
    assert result.exit_code == 0
    assert "total:" in result.output
    assert "tools" in result.output


def test_tools_json(runner):
    result = runner.invoke(cli, ["--json", "tools"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total"] >= 1
    assert "pentagi" in data["tools"]


def test_adapters_discovery(runner):
    result = runner.invoke(cli, ["adapters"])
    assert result.exit_code == 0
    match = re.search(r"Discovered (\d+) adapters", result.output)
    assert match
    assert int(match.group(1)) >= 5
    assert "pentagi" in result.output
    assert "integration=" in result.output


# ---------------------------------------------------------------------------
# findings / memory / session
# ---------------------------------------------------------------------------

def test_findings_empty(runner, iso):
    result = runner.invoke(cli, ["findings"])
    assert result.exit_code == 0
    assert result.output == ""


def test_findings_empty_json(runner, iso):
    result = runner.invoke(cli, ["--json", "findings"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {"findings": [], "total": 0}


def test_findings_seeded(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["findings"])
    assert result.exit_code == 0
    assert "nginx 1.18.0 detected" in result.output
    assert "default admin page exposed" in result.output


def test_findings_status_filter(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["findings", "--status", "VERIFIED"])
    assert result.exit_code == 0
    assert "nginx 1.18.0 detected" in result.output
    assert "default admin page" not in result.output


def test_memory_search(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["memory", "nginx"])
    assert result.exit_code == 0
    assert "nginx version header disclosed" in result.output


def test_memory_search_json(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["--json", "memory", "nginx"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["query"] == "nginx"
    assert data["total"] >= 1


def test_memory_no_query_shows_usage(runner, iso):
    result = runner.invoke(cli, ["memory"])
    assert result.exit_code == 0
    assert "Usage: cyber-ai memory" in result.output


def test_session_list(runner, iso):
    sid = _seed_memory()
    result = runner.invoke(cli, ["session", "list"])
    assert result.exit_code == 0
    assert sid[:8] in result.output
    assert "target=juice-shop" in result.output
    assert "status=active" in result.output


def test_session_list_json(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["--json", "session", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total"] == 1
    assert data["sessions"][0]["target_id"] == "juice-shop"


def test_session_show(runner, iso):
    sid = _seed_memory()
    result = runner.invoke(cli, ["session", "show", sid])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["target_id"] == "juice-shop"
    assert data["objective"] == "Test objective"


def test_session_show_not_found(runner, iso):
    result = runner.invoke(cli, ["session", "show", "bogus-session"])
    assert result.exit_code == 0
    assert "Session not found: bogus-session" in result.output


def test_session_show_not_found_json(runner, iso):
    result = runner.invoke(cli, ["--json", "session", "show", "bogus"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "error" in data


# ---------------------------------------------------------------------------
# lab
# ---------------------------------------------------------------------------

def test_lab_list(runner):
    result = runner.invoke(cli, ["lab", "list"])
    assert result.exit_code == 0
    assert "juice-shop" in result.output
    assert "AUTHORIZED" in result.output


def test_lab_register_new(runner, tmp_targets):
    result = runner.invoke(cli, ["lab", "register", "test-target-1",
                                 "--host", "10.0.0.9", "--port", "9999",
                                 "--description", "tmp test target"])
    assert result.exit_code == 0
    assert "Registered target 'test-target-1'" in result.output

    # The tmp targets file now contains the new target.
    result = runner.invoke(cli, ["lab", "list"])
    assert "test-target-1" in result.output
    # ...and the repository file was untouched.
    assert "test-target-1" not in (WORKSPACE_ROOT / "lab" / "targets"
                                   / "targets.yaml").read_text("utf-8")


def test_lab_register_existing(runner, tmp_targets):
    result = runner.invoke(cli, ["lab", "register", "juice-shop"])
    assert result.exit_code == 0
    assert "already registered" in result.output


def test_lab_status(runner):
    result = runner.invoke(cli, ["lab", "status"])
    assert result.exit_code == 0
    assert "TARGET" in result.output
    assert "juice-shop" in result.output


def test_lab_status_unknown(runner):
    result = runner.invoke(cli, ["lab", "status", "no-such-target"])
    assert result.exit_code == 0
    assert "Target not found: no-such-target" in result.output


def test_lab_start_with_fake_manager(runner, monkeypatch):
    monkeypatch.setattr("cyberai.orchestrator.lab.LabManager",
                        _FakeLabManager)
    result = runner.invoke(cli, ["lab", "start", "test-tgt"])
    assert result.exit_code == 0
    assert "Docker not available" in result.output
    assert "[OK] test-tgt: RUNNING" in result.output
    assert "mode: mock" in result.output


def test_lab_start_denied_exits_2(runner, monkeypatch):
    monkeypatch.setattr("cyberai.orchestrator.lab.LabManager",
                        _FakeLabManager)
    monkeypatch.setattr(_FakeLabManager, "start_result",
                        {"status": "DENIED", "message": "not authorized"})
    result = runner.invoke(cli, ["lab", "start", "test-tgt"])
    assert result.exit_code == 2
    assert "[DENIED] test-tgt: DENIED" in result.output


def test_lab_stop_with_fake_manager(runner, monkeypatch):
    monkeypatch.setattr("cyberai.orchestrator.lab.LabManager",
                        _FakeLabManager)
    result = runner.invoke(cli, ["lab", "stop", "test-tgt"])
    assert result.exit_code == 0
    assert "[OK] test-tgt: STOPPED" in result.output


def test_lab_stop_not_running(runner, monkeypatch):
    monkeypatch.setattr("cyberai.orchestrator.lab.LabManager",
                        _FakeLabManager)
    monkeypatch.setattr(_FakeLabManager, "stop_result",
                         {"status": "NOT_RUNNING"})
    result = runner.invoke(cli, ["lab", "stop", "test-tgt"])
    assert result.exit_code == 0
    assert "[INFO] test-tgt: NOT_RUNNING" in result.output


# ---------------------------------------------------------------------------
# workflow
# ---------------------------------------------------------------------------

def test_workflow_list(runner):
    result = runner.invoke(cli, ["workflow", "list"])
    assert result.exit_code == 0
    for name in ("recon_to_report", "code_audit", "target_assessment"):
        assert name in result.output
    assert "steps:" in result.output


def test_workflow_show(runner):
    result = runner.invoke(cli, ["workflow", "show", "recon_to_report"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["name"] == "Reconnaissance to Report"
    assert len(data["steps"]) == 5


def test_workflow_show_unknown(runner):
    result = runner.invoke(cli, ["workflow", "show", "bogus"])
    assert result.exit_code == 0
    assert "Unknown workflow: bogus" in result.output


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

def test_config_list(runner):
    result = runner.invoke(cli, ["config", "--list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    for section in ("privacy", "llm", "policy", "memory", "routing"):
        assert section in data
    assert "targets_path" in data["policy"]


def test_config_no_args_lists_all(runner):
    result = runner.invoke(cli, ["config"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "policy" in data


def test_config_section(runner):
    result = runner.invoke(cli, ["config", "policy"])
    assert result.exit_code == 0
    assert result.output.startswith("policy = ")
    data = json.loads(result.output.split(" = ", 1)[1])
    assert "targets_path" in data


def test_config_dotted_key(runner):
    result = runner.invoke(cli, ["config", "policy.targets_path"])
    assert result.exit_code == 0
    assert result.output.startswith("policy.targets_path = ")
    assert "<unset>" not in result.output


def test_config_unknown_section(runner):
    result = runner.invoke(cli, ["config", "bogus"])
    assert result.exit_code == 0
    assert "[?] bogus = <unset>" in result.output


def test_config_unknown_key(runner):
    result = runner.invoke(cli, ["config", "policy.bogus_key"])
    assert result.exit_code == 0
    assert "[?] policy.bogus_key = <unset>" in result.output


# ---------------------------------------------------------------------------
# history / intel / blueprint / replay / report / scorecard
# ---------------------------------------------------------------------------

def test_history(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["history"])
    assert result.exit_code == 0
    assert "=== HISTORY (3/3) ===" in result.output
    assert "SESSION" in result.output
    assert "FINDING" in result.output


def test_history_limit(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["history", "--limit", "1"])
    assert result.exit_code == 0
    assert "=== HISTORY (1/3) ===" in result.output


def test_intel_target(runner, iso):
    result = runner.invoke(cli, ["intel", "juice-shop"])
    assert result.exit_code == 0
    assert "=== INTEL: juice-shop ===" in result.output
    assert "Host: 127.0.0.1:8080" in result.output
    assert "No findings recorded yet." in result.output


def test_intel_with_findings(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["intel", "juice-shop"])
    assert result.exit_code == 0
    assert "--- FINDINGS (2) ---" in result.output
    assert "nginx 1.18.0 detected" in result.output


def test_intel_unknown_target(runner, iso):
    result = runner.invoke(cli, ["intel", "no-such-target"])
    assert result.exit_code == 0
    assert "=== INTEL: no-such-target ===" in result.output
    assert "Host:" not in result.output


def test_blueprint_text(runner):
    result = runner.invoke(cli, ["blueprint", "juice-shop"])
    assert result.exit_code == 0
    assert "=== TARGET BLUEPRINT: juice-shop ===" in result.output
    assert "host" in result.output
    assert "127.0.0.1" in result.output


def test_blueprint_json(runner):
    result = runner.invoke(cli, ["blueprint", "juice-shop",
                                 "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == "juice-shop"
    assert data["environment"] == "authorized_lab"
    assert data["allowed"] is True


def test_blueprint_not_found(runner):
    result = runner.invoke(cli, ["blueprint", "no-such-target"])
    assert result.exit_code == 0
    assert "Target not found: no-such-target" in result.output


def test_replay(runner, iso):
    sid = _seed_memory()
    result = runner.invoke(cli, ["replay", sid])
    assert result.exit_code == 0
    assert f"=== SESSION {sid[:8]} ===" in result.output
    assert "Target: juice-shop" in result.output
    assert "--- FINDINGS (2) ---" in result.output
    assert "nginx 1.18.0 detected" in result.output


def test_replay_not_found(runner, iso):
    result = runner.invoke(cli, ["replay", "bogus-session"])
    assert result.exit_code == 0
    assert "Session not found: bogus-session" in result.output


def test_report_writes_markdown(runner, iso, tmp_path):
    sid = _seed_memory()
    out = tmp_path / "reports" / "session.md"
    result = runner.invoke(cli, ["report", sid, "-o", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    content = out.read_text("utf-8")
    assert content.startswith("# CERBERUS Session Report")
    assert f"**Session:** `{sid}`" in content
    # Findings are ordered timestamp DESC, so either status can be #1.
    assert "### 1. [VERIFIED] recon" in content or \
           "### 1. [UNVERIFIED] recon" in content
    assert "### 2. [UNVERIFIED] recon" in content or \
           "### 2. [VERIFIED] recon" in content
    assert "[VERIFIED]" in content and "[UNVERIFIED]" in content
    assert "(2 findings)" in result.output


def test_report_not_found(runner, iso):
    result = runner.invoke(cli, ["report", "bogus-session"])
    assert result.exit_code == 0
    assert "Session not found: bogus-session" in result.output


def test_scorecard_text(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["scorecard"])
    assert result.exit_code == 0
    assert "========= CERBERUS SCORECARD =========" in result.output
    assert "Sessions:   1 (0 completed)" in result.output
    assert "Targets:" in result.output
    assert "Tools:" in result.output
    assert "VERIFIED" in result.output


def test_scorecard_json(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["--json", "scorecard"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["sessions"] == {"total": 1, "completed": 0}
    assert data["targets"]["registered"] >= 2
    assert data["tools"]["total"] >= 1
    assert data["findings"]["by_status"]["VERIFIED"] == 1
    assert data["findings"]["by_status"]["UNVERIFIED"] == 1
    assert "tracked" in data


# ---------------------------------------------------------------------------
# mem (typed memory store)
# ---------------------------------------------------------------------------

def test_mem_stats(runner, iso):
    _seed_mem_store()
    result = runner.invoke(cli, ["mem", "stats"])
    assert result.exit_code == 0
    assert "=== MEMORY STATS ===" in result.output
    assert "Total: 2" in result.output
    assert "semantic" in result.output
    assert "failure" in result.output


def test_mem_search_hit(runner, iso):
    _seed_mem_store()
    result = runner.invoke(cli, ["mem", "search",
                                 "sql injection bypass"])
    assert result.exit_code == 0
    assert "MATCHES ===" in result.output
    assert "(semantic)" in result.output
    assert "SQL injection" in result.output


def test_mem_search_miss(runner, iso):
    _seed_mem_store()
    result = runner.invoke(cli, ["mem", "search",
                                 "kubernetes cluster policy"])
    assert result.exit_code == 0
    assert "No matching memories." in result.output


def test_mem_search_type_filter(runner, iso):
    _seed_mem_store()
    result = runner.invoke(cli, ["mem", "search", "--type", "failure",
                                 "nmap scan timed out"])
    assert result.exit_code == 0
    assert "(failure)" in result.output


# ---------------------------------------------------------------------------
# wargame (ghost wargaming)
# ---------------------------------------------------------------------------

def test_wargame_failures_empty(runner, iso):
    result = runner.invoke(cli, ["wargame", "failures"])
    assert result.exit_code == 0
    assert "No failures recorded." in result.output


def test_wargame_failures_seeded(runner, iso):
    _seed_failure(iso)
    result = runner.invoke(cli, ["wargame", "failures"])
    assert result.exit_code == 0
    assert "=== 1 RECENT FAILURES ===" in result.output
    assert "[tool_unavailable]" in result.output
    assert "nmap crashed mid-scan" in result.output


def test_wargame_analytics(runner, iso):
    _seed_failure(iso)
    result = runner.invoke(cli, ["wargame", "analytics"])
    assert result.exit_code == 0
    assert "=== WARGAME ANALYTICS ===" in result.output
    assert "Total failures: 1" in result.output
    assert "By category:" in result.output
    assert "tool_unavailable" in result.output
    assert "By tool:" in result.output
    assert "nmap" in result.output


def test_wargame_fast_forward(runner, iso):
    result = runner.invoke(cli, ["wargame", "fast-forward",
                                 "--num-strategies", "2"])
    assert result.exit_code == 0
    assert "Mode: simulate (no live execution)" in result.output
    assert "Generated: 2" in result.output


# ---------------------------------------------------------------------------
# killchain (F2T2EA)
# ---------------------------------------------------------------------------

def test_killchain_lifecycle(runner, killchain_tmp):
    # start
    result = runner.invoke(cli, ["killchain", "start", "juice-shop"])
    assert result.exit_code == 0
    assert "Chain " in result.output
    assert "for 'juice-shop'" in result.output
    assert "Phase: FIND" in result.output
    assert "Status: ACTIVE" in result.output

    # advance with a note
    result = runner.invoke(cli, ["killchain", "advance", "juice-shop",
                                 "-n", "target located"])
    assert result.exit_code == 0
    assert "Advanced 'juice-shop' to phase: FIX" in result.output

    # advance with a key=value finding
    result = runner.invoke(cli, ["killchain", "advance", "juice-shop",
                                 "-f", "service=nginx", "-f", "port=8080"])
    assert result.exit_code == 0
    assert "Advanced 'juice-shop' to phase: TRACK" in result.output

    # per-target status shows the phase table
    result = runner.invoke(cli, ["killchain", "status", "juice-shop"])
    assert result.exit_code == 0
    assert "[+] FIND" in result.output
    assert "[+] FIX" in result.output
    assert "[>] TRACK" in result.output
    assert "[ ] TARGET" in result.output

    # fail the current phase → chain aborts
    result = runner.invoke(cli, ["killchain", "fail", "juice-shop",
                                 "-r", "exploit crashed"])
    assert result.exit_code == 0
    assert "Aborted chain for 'juice-shop': exploit crashed" in result.output
    assert "Status: ABORTED" in result.output


def test_killchain_advance_unknown(runner, killchain_tmp):
    result = runner.invoke(cli, ["killchain", "advance", "ghost"])
    assert result.exit_code == 0
    assert "Error: no active chain for ghost" in result.output


def test_killchain_status_unknown_target(runner, killchain_tmp):
    result = runner.invoke(cli, ["killchain", "status", "ghost"])
    assert result.exit_code == 0
    assert "No chain for 'ghost'" in result.output


def test_killchain_status_aggregate(runner, killchain_tmp):
    runner.invoke(cli, ["killchain", "start", "juice-shop"])
    result = runner.invoke(cli, ["killchain", "status"])
    assert result.exit_code == 0
    assert "=== KILL CHAIN STATUS ===" in result.output
    assert "Active: 1" in result.output
    assert "juice-shop" in result.output


def test_killchain_reset_confirmed(runner, killchain_tmp):
    runner.invoke(cli, ["killchain", "start", "juice-shop"])
    result = runner.invoke(cli, ["killchain", "reset"], input="y")
    assert result.exit_code == 0
    assert "Kill-chain state cleared." in result.output

    result = runner.invoke(cli, ["killchain", "status"])
    assert "Active: 0" in result.output
    assert "juice-shop" not in result.output


def test_killchain_reset_declined(runner, killchain_tmp):
    runner.invoke(cli, ["killchain", "start", "juice-shop"])
    result = runner.invoke(cli, ["killchain", "reset"], input="n")
    assert result.exit_code != 0
    # State must survive the declined reset.
    result = runner.invoke(cli, ["killchain", "status"])
    assert "Active: 1" in result.output


# ---------------------------------------------------------------------------
# evolve / doctor / profile
# ---------------------------------------------------------------------------

def test_evolve_generation(runner, iso):
    result = runner.invoke(cli, ["evolve", "--generations", "1",
                                 "--population", "2"])
    assert result.exit_code == 0
    assert "Generation 1:" in result.output
    assert "fitness=" in result.output


def test_doctor(runner, iso):
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "Python" in result.output
    assert "Git:" in result.output
    assert "[OK]" in result.output


def test_doctor_json(runner, iso):
    result = runner.invoke(cli, ["--json", "doctor"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) >= 10
    for item in data:
        assert set(item) == {"component", "status", "message"}
        assert item["status"] in ("ok", "warn", "error", "info")


def test_profile(runner):
    result = runner.invoke(cli, ["profile"])
    assert result.exit_code == 0
    assert "CERBERUS HARDWARE PROFILE" in result.output
    assert "Execution profile:" in result.output


def test_profile_json_env_override(runner, monkeypatch):
    monkeypatch.setenv("CERBERUS_PROFILE", "MINIMAL")
    result = runner.invoke(cli, ["--json", "profile"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["profile"] == "MINIMAL"
    assert data["profile_source"] == "env"


# ---------------------------------------------------------------------------
# status / models / task / assess / simulate / hunt  (faked orchestrator)
# ---------------------------------------------------------------------------

def test_status(runner, monkeypatch):
    monkeypatch.setattr("cyberai.CyberAIOrchestrator", _FakeOrchestrator)
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "Cyber AI" in result.output


def test_status_json(runner, monkeypatch):
    monkeypatch.setattr("cyberai.CyberAIOrchestrator", _FakeOrchestrator)
    result = runner.invoke(cli, ["--json", "status"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["platform"] == "Cyber AI"
    assert data["version"] == "2.0.0"


def test_models(runner, monkeypatch):
    monkeypatch.setattr("cyberai.llm_gateway.LLMGateway", _FakeLLMGateway)
    result = runner.invoke(cli, ["models"])
    assert result.exit_code == 0
    assert "local-fast" in result.output
    assert "provider=ollama" in result.output


def test_models_json(runner, monkeypatch):
    monkeypatch.setattr("cyberai.llm_gateway.LLMGateway", _FakeLLMGateway)
    result = runner.invoke(cli, ["--json", "models"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["models"][0]["alias"] == "local-fast"
    assert data["health"]["ollama"] == "down"


def test_models_verbose(runner, monkeypatch):
    monkeypatch.setattr("cyberai.llm_gateway.LLMGateway", _FakeLLMGateway)
    result = runner.invoke(cli, ["--verbose", "models"])
    assert result.exit_code == 0
    assert "Health:" in result.output


def test_task(runner, monkeypatch):
    monkeypatch.setattr("cyberai.CyberAIOrchestrator", _FakeOrchestrator)
    result = runner.invoke(cli, ["task", "-o", "Analyze lab target"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "completed"
    assert data["objective"] == "Analyze lab target"


def test_task_with_target_and_scope(runner, monkeypatch):
    monkeypatch.setattr("cyberai.CyberAIOrchestrator", _FakeOrchestrator)
    result = runner.invoke(cli, ["task", "-o", "obj", "-t", "juice-shop",
                                 "--simulate"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["target_id"] == "juice-shop"
    assert data["scope"] == "authorized_lab"


def test_task_permission_error_exits_1(runner, monkeypatch):
    monkeypatch.setattr("cyberai.CyberAIOrchestrator",
                        _DenyingOrchestrator)
    result = runner.invoke(cli, ["task", "-o", "obj"])
    assert result.exit_code == 1
    assert "[ERROR] Authorization required" in result.output


def test_assess_alias(runner, monkeypatch):
    monkeypatch.setattr("cyberai.CyberAIOrchestrator", _FakeOrchestrator)
    result = runner.invoke(cli, ["assess", "-o", "legacy objective"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["objective"] == "legacy objective"


def test_simulate_command(runner, monkeypatch):
    monkeypatch.setattr("cyberai.CyberAIOrchestrator", _FakeOrchestrator)
    result = runner.invoke(cli, ["simulate", "end to end objective"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["target_id"] == "lab-web-01"
    assert data["status"] == "completed"


def test_hunt_authorized(runner, monkeypatch):
    monkeypatch.setattr("cyberai.CyberAIOrchestrator", _FakeOrchestrator)
    result = runner.invoke(cli, ["hunt", "juice-shop",
                                 "-o", "Identify services"])
    assert result.exit_code == 0
    assert "[HUNT] target=juice-shop" in result.output
    assert "[HUNT] objective=Identify services" in result.output
    assert "[HUNT] mode=SIMULATE" in result.output
    assert "=== HUNT RESULTS ===" in result.output
    assert "Status: COMPLETED" in result.output
    assert "Findings: 1" in result.output
    assert "--- REPORT ---" in result.output


def test_hunt_unknown_target(runner, monkeypatch):
    monkeypatch.setattr("cyberai.CyberAIOrchestrator", _FakeOrchestrator)
    result = runner.invoke(cli, ["hunt", "no-such-target"])
    assert result.exit_code == 0
    assert "[ERROR] Unknown target: no-such-target" in result.output


def test_hunt_unauthorized(runner, monkeypatch):
    monkeypatch.setattr("cyberai.CyberAIOrchestrator", _FakeOrchestrator)
    monkeypatch.setattr("cyberai.orchestrator.PolicyEngine",
                        _UnauthorizedPolicyEngine)
    result = runner.invoke(cli, ["hunt", "locked-target"])
    assert result.exit_code == 0
    assert "[ERROR] Target not authorized: locked-target" in result.output


# ---------------------------------------------------------------------------
# mcp (faked gateway — never launches subprocess probes)
# ---------------------------------------------------------------------------

@pytest.fixture()
def fake_mcp(monkeypatch):
    gw = _FakeMCPGateway()
    monkeypatch.setattr("cyberai.orchestrator.cli._mcp.get_mcp_gateway",
                        lambda: gw)
    return gw


def test_mcp_list(runner, fake_mcp):
    result = runner.invoke(cli, ["mcp", "list"])
    assert result.exit_code == 0
    assert "=== MCP SERVERS (1 discovered) ===" in result.output
    assert "fake-mcp" in result.output
    assert "Configured servers: 1" in result.output
    assert "- preconfigured" in result.output


def test_mcp_register(runner, fake_mcp):
    result = runner.invoke(cli, ["mcp", "register", "my-mcp",
                                 "--command", "python",
                                 "-a", "server.py",
                                 "-c", "tool_execution"])
    assert result.exit_code == 0
    assert "Registered MCP server 'my-mcp' (session-scoped)" in result.output
    cfg = fake_mcp.registered["my-mcp"]
    assert cfg["command"] == "python"
    assert cfg["args"] == ["server.py"]
    assert cfg["capabilities"] == ["tool_execution"]


def test_mcp_tools_success(runner, fake_mcp):
    result = runner.invoke(cli, ["mcp", "tools", "fake-mcp"])
    assert result.exit_code == 0
    assert "=== TOOLS on fake-mcp (1) ===" in result.output
    assert "nmap_scan" in result.output


def test_mcp_tools_offline(runner, fake_mcp):
    result = runner.invoke(cli, ["mcp", "tools", "offline-srv"])
    assert result.exit_code == 0
    assert "[OFFLINE] server unreachable" in result.output


def test_mcp_health(runner, fake_mcp):
    result = runner.invoke(cli, ["mcp", "health"])
    assert result.exit_code == 0
    assert "=== MCP HEALTH ===" in result.output
    assert "[OK] fake-mcp" in result.output
    assert "responds" in result.output


def test_mcp_call(runner, fake_mcp):
    result = runner.invoke(cli, ["mcp", "call", "fake-mcp", "nmap_scan",
                                 "-a", "target=juice-shop"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "SUCCESS"
    assert data["tool"] == "nmap_scan"
    assert data["args"] == {"target": "juice-shop"}


# ---------------------------------------------------------------------------
# watch / benchmark
# ---------------------------------------------------------------------------

def test_watch_max_events(runner, iso):
    _seed_memory()
    result = runner.invoke(cli, ["watch", "--max-events", "1",
                                 "--source", "tasks"])
    assert result.exit_code == 0
    assert "[TASK ]" in result.output
    assert "target=juice-shop" in result.output
    assert "stopped after 1 events" in result.output


def test_benchmark(runner, iso):
    result = runner.invoke(cli, ["benchmark", "--rounds", "1"])
    assert result.exit_code == 0
    assert "=== CERBERUS BENCHMARK (1 rounds) ===" in result.output
    assert "memory (open+list+close):" in result.output
    assert "policy (load+list):" in result.output
    assert "tools  (registry+dict):" in result.output
    assert "ms/op" in result.output
