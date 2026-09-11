"""Agent-level tests: recon, verifier, analyst, coder, reporter, researcher.

Covers the six lowest-covered agents using the established fake-dependency
pattern (no network, no real LLM, no real adapters):
- ReconAgent: run() LLM-only path, adapter path, _try_adapter matrix
- VerifierAgent: verify_finding state machine, challenge_conclusion,
  _llm_challenge, _parse_llm_review
- AnalystAgent: run() with/without memory, experience recording
- CoderAgent: analyze/generate routing, sensitive-source routing,
  unknown action
- ReporterAgent: run() report shape, findings/evidence summaries,
  evidence file save, experience recording
- ResearcherAgent: run() with/without memory, experience recording
- BaseAgent: run() contract, _llm_call failure modes, _record_experience
"""

import sys
import types

import pytest

from cyberai.orchestrator.agents.base import BaseAgent
from cyberai.orchestrator.agents.recon.recon import ReconAgent
from cyberai.orchestrator.agents.verifier.verifier import VerifierAgent
from cyberai.orchestrator.agents.analyst.analyst import AnalystAgent
from cyberai.orchestrator.agents.coder.coder import CoderAgent
from cyberai.orchestrator.agents.reporter.reporter import ReporterAgent
from cyberai.orchestrator.agents.researcher.researcher import ResearcherAgent


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeGateway:
    """Configurable LLM gateway fake that records every complete() call."""

    def __init__(self, content="analysis output", success=True, exc=None):
        self.content = content
        self.success = success
        self.exc = exc
        self.calls = []

    async def complete(self, role, prompt, **kwargs):
        self.calls.append({"role": role, "prompt": prompt, "kwargs": kwargs})
        if self.exc:
            raise self.exc
        if self.success:
            return {
                "success": True, "content": self.content,
                "model": "fake-model", "transport": "mock", "latency_ms": 1,
            }
        return {
            "success": False, "message": "all hops failed",
            "errors": ["hop1"], "blocked": [],
        }


class FakeMemory:
    """Memory manager fake: stores experiences/findings, serves searches."""

    def __init__(self, search_results=None):
        self.experiences = []
        self.findings = []
        self.search_results = search_results or []
        self.search_queries = []

    def store_experience(self, exp):
        self.experiences.append(exp)
        return f"exp-{len(self.experiences)}"

    def store_finding(self, finding):
        self.findings.append(finding)
        return f"finding-{len(self.findings)}"

    def search_experiences(self, query, limit=5):
        self.search_queries.append((query, limit))
        return self.search_results


class FakeLogger:
    def __init__(self):
        self.events = []
        self.saved_evidence = []

    def log_event(self, session_id, category, data):
        self.events.append((session_id, category, data))

    def save_evidence(self, session_id, kind, payload):
        self.saved_evidence.append((session_id, kind, payload))


class FakeToolRegistry:
    def __init__(self, tools=None, paths=None):
        self.tools = tools or []
        self.paths = paths or {}
        self.capability_queries = []

    def get_tools_by_capability(self, capability):
        self.capability_queries.append(capability)
        return [{"name": t} for t in self.tools]

    def get_adapter_path(self, name):
        return self.paths.get(name)


@pytest.fixture()
def evt(tmp_path, monkeypatch):
    """Redirect the shared EventStore into tmp_path (advisory events)."""
    import cyberai.orchestrator.event_store as es_mod
    store = es_mod.EventStore(db_path=tmp_path / "events.db")
    monkeypatch.setattr(es_mod, "_STORE", store)
    monkeypatch.setattr(es_mod, "get_event_store", lambda: store)
    yield store
    store.close()


def _install_adapter_module(monkeypatch, name, adapter_cls):
    """Register a fake adapter module so __import__(name) resolves to it."""
    mod = types.ModuleType(name)
    if adapter_cls is not None:
        mod.Adapter = adapter_cls
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_base_agent_run_not_implemented():
    agent = BaseAgent(name="x")
    with pytest.raises(NotImplementedError):
        await agent.run({"target": "t"})


@pytest.mark.asyncio
async def test_base_llm_call_success(evt):
    gw = FakeGateway(content="hello")
    agent = BaseAgent(name="analyst", llm_gateway=gw)
    out = await agent._llm_call("prompt", task_type="reasoning")
    assert out == "hello"
    assert gw.calls[0]["role"] == "reasoning"
    types_seen = [e.type for e in evt.history()]
    assert "model.started" in types_seen
    assert "model.completed" in types_seen


@pytest.mark.asyncio
async def test_base_llm_call_unavailable(evt):
    gw = FakeGateway(success=False)
    agent = BaseAgent(name="recon", llm_gateway=gw)
    out = await agent._llm_call("prompt", task_type="web_research")
    assert out.startswith("[LLM_UNAVAILABLE:")
    assert "model.failed" in [e.type for e in evt.history()]


@pytest.mark.asyncio
async def test_base_llm_call_exception():
    gw = FakeGateway(exc=RuntimeError("boom"))
    agent = BaseAgent(name="coder", llm_gateway=gw)
    out = await agent._llm_call("prompt", task_type="code_generation")
    assert out.startswith("[LLM_ERROR:")


@pytest.mark.asyncio
async def test_base_llm_call_logs_to_session_logger():
    gw = FakeGateway()
    log = FakeLogger()
    agent = BaseAgent(name="recon", llm_gateway=gw, session_logger=log)
    await agent._llm_call("prompt text", task_type="web_research")
    assert len(log.events) == 1
    session_id, category, data = log.events[0]
    assert session_id == ""
    assert category == "model_calls"
    assert data["agent"] == "recon"
    assert data["prompt"] == "prompt text"


def test_base_record_experience_with_memory():
    mem = FakeMemory()
    agent = BaseAgent(name="recon", memory_manager=mem)
    exp_id = agent._record_experience(
        session_id="s1", target_id="t1",
        observation="obs", hypothesis="hyp", action="recon",
        tool="nmap", result="success", confidence=0.5,
    )
    assert exp_id == "exp-1"
    assert mem.experiences[0]["action"] == "recon"
    assert mem.experiences[0]["tool"] == "nmap"
    assert mem.experiences[0]["environment"] == "authorized_lab"


def test_base_record_experience_without_memory():
    agent = BaseAgent(name="recon")
    assert agent._record_experience(
        session_id="s", target_id="t", observation="o", hypothesis="h",
        action="a", tool="tool", result="success") is None


# ---------------------------------------------------------------------------
# ReconAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recon_run_llm_only(evt):
    """No tool registry -> pure LLM analysis, no adapter call."""
    gw = FakeGateway(content="recon summary")
    agent = ReconAgent(llm_gateway=gw)
    result = await agent.run({
        "target": "juice-shop", "target_id": "juice-shop",
        "session_id": "sess-1", "scope": "full", "depth": "active",
    })
    assert result["target"] == "juice-shop"
    assert result["scope"] == "full"
    assert result["depth"] == "active"
    assert result["tools_available"] == []
    assert result["tool_used"] is None
    assert result["raw_output"] is None
    assert result["findings"] == "recon summary"
    assert gw.calls[0]["role"] == "web_research"


@pytest.mark.asyncio
async def test_recon_run_adapter_success(evt, monkeypatch):
    """Registry offers a recon tool whose adapter executes successfully."""
    class Adapter:
        @staticmethod
        async def create(task):
            return Adapter()

        async def execute(self, task):
            return {
                "success": True, "output": "open ports: 22, 80",
                "evidence": [{"type": "nmap", "content": "port list"}],
            }

    _install_adapter_module(monkeypatch, "adapters.fake_scan", Adapter)
    gw = FakeGateway(content="analyzed")
    mem = FakeMemory()
    log = FakeLogger()
    reg = FakeToolRegistry(
        tools=["fake_scan"], paths={"fake_scan": "adapters.fake_scan"})
    agent = ReconAgent(
        llm_gateway=gw, memory_manager=mem, session_logger=log,
        tool_registry=reg)
    result = await agent.run({
        "target": "juice-shop", "target_id": "juice-shop",
        "session_id": "sess-1",
    })
    assert result["tool_used"] == "fake_scan"
    assert result["tools_available"] == ["fake_scan"]
    assert result["raw_output"] == "open ports: 22, 80"
    assert result["evidence"] == [{"type": "nmap", "content": "port list"}]
    assert result["findings"] == "analyzed"
    # adapter output is fed into the analysis prompt
    assert "open ports: 22, 80" in gw.calls[0]["prompt"]
    # experience recorded as success with 0.5 confidence
    assert mem.experiences[0]["result"] == "success"
    assert mem.experiences[0]["confidence"] == 0.5
    assert mem.experiences[0]["tool"] == "fake_scan"
    # session logger got the tool_calls event (after _llm_call's own entry)
    tool_calls = [e for e in log.events if e[1] == "tool_calls"]
    assert tool_calls[0][0] == "sess-1"
    assert tool_calls[0][2]["tool"] == "fake_scan"
    # advisory events published
    types_seen = [e.type for e in evt.history()]
    assert "tool.started" in types_seen
    assert "tool.completed" in types_seen
    # registry was queried for the research capability
    assert reg.capability_queries == ["research"]


@pytest.mark.asyncio
async def test_recon_run_adapter_failure_partial(evt, monkeypatch):
    """Adapter returns None -> partial result, no raw output."""
    class Adapter:
        @staticmethod
        async def create(task):
            return Adapter()

        async def execute(self, task):
            raise RuntimeError("adapter exploded")

    _install_adapter_module(monkeypatch, "adapters.fake_scan", Adapter)
    gw = FakeGateway()
    mem = FakeMemory()
    reg = FakeToolRegistry(
        tools=["fake_scan"], paths={"fake_scan": "adapters.fake_scan"})
    agent = ReconAgent(llm_gateway=gw, memory_manager=mem, tool_registry=reg)
    result = await agent.run({
        "target": "juice-shop", "target_id": "juice-shop",
        "session_id": "sess-1",
    })
    assert result["tool_used"] == "fake_scan"
    assert result["raw_output"] is None
    assert result["evidence"] == []
    assert mem.experiences[0]["result"] == "partial"
    assert mem.experiences[0]["confidence"] == 0.3
    types_seen = [e.type for e in evt.history()]
    assert "tool.started" in types_seen
    assert "tool.failed" in types_seen


@pytest.mark.asyncio
async def test_recon_run_tool_without_adapter_path():
    """Tool known but no adapter path -> LLM-only fallback."""
    gw = FakeGateway()
    reg = FakeToolRegistry(tools=["strix"], paths={})  # no path for strix
    agent = ReconAgent(llm_gateway=gw, tool_registry=reg)
    result = await agent.run({
        "target": "juice-shop", "target_id": "juice-shop",
        "session_id": "sess-1",
    })
    assert result["tool_used"] == "strix"
    assert result["raw_output"] is None


@pytest.mark.asyncio
async def test_recon_try_adapter_dict_result(monkeypatch):
    class Adapter:
        @staticmethod
        async def create(task):
            return Adapter()

        async def execute(self, task):
            return {"success": True, "output": "ok"}

    _install_adapter_module(monkeypatch, "adapters.m1", Adapter)
    agent = ReconAgent()
    out = await agent._try_adapter("adapters.m1", {"action": "recon"})
    assert out == {"success": True, "output": "ok"}


@pytest.mark.asyncio
async def test_recon_try_adapter_pydantic_style_result(monkeypatch):
    class Result:
        def dict(self):
            return {"success": True, "output": "pydantic"}

    class Adapter:
        @staticmethod
        async def create(task):
            return Adapter()

        async def execute(self, task):
            return Result()

    _install_adapter_module(monkeypatch, "adapters.m2", Adapter)
    agent = ReconAgent()
    out = await agent._try_adapter("adapters.m2", {})
    assert out == {"success": True, "output": "pydantic"}


@pytest.mark.asyncio
async def test_recon_try_adapter_plain_object_result(monkeypatch):
    class Result:
        def __init__(self):
            self.success = True
            self.output = "plain"

    class Adapter:
        @staticmethod
        async def create(task):
            return Adapter()

        async def execute(self, task):
            return Result()

    _install_adapter_module(monkeypatch, "adapters.m3", Adapter)
    agent = ReconAgent()
    out = await agent._try_adapter("adapters.m3", {})
    assert out["success"] is True
    assert out["output"] == "plain"


@pytest.mark.asyncio
async def test_recon_try_adapter_string_result(monkeypatch):
    class Adapter:
        @staticmethod
        async def create(task):
            return Adapter()

        async def execute(self, task):
            return "raw string output"

    _install_adapter_module(monkeypatch, "adapters.m4", Adapter)
    agent = ReconAgent()
    out = await agent._try_adapter("adapters.m4", {})
    assert out == {"success": True, "output": "raw string output"}


@pytest.mark.asyncio
async def test_recon_try_adapter_no_create_classmethod(monkeypatch):
    """Adapter without create() is instantiated directly."""

    class Adapter:
        async def execute(self, task):
            return {"success": True, "output": "direct"}

    _install_adapter_module(monkeypatch, "adapters.m5", Adapter)
    agent = ReconAgent()
    out = await agent._try_adapter("adapters.m5", {})
    assert out == {"success": True, "output": "direct"}


@pytest.mark.asyncio
async def test_recon_try_adapter_module_without_adapter(monkeypatch):
    _install_adapter_module(monkeypatch, "adapters.m6", adapter_cls=None)
    agent = ReconAgent()
    assert await agent._try_adapter("adapters.m6", {}) is None


@pytest.mark.asyncio
async def test_recon_try_adapter_import_error():
    agent = ReconAgent()
    assert await agent._try_adapter("adapters.does_not_exist_xyz", {}) is None


# ---------------------------------------------------------------------------
# VerifierAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_verifier_no_evidence_unverified():
    v = VerifierAgent()
    finding = {"observation": "x", "evidence": [], "confidence": 0.5}
    out = await v.verify_finding(finding)
    assert out["status"] == "UNVERIFIED"
    assert out["verification_notes"] == "No evidence provided"
    assert out["confidence"] == 0.5  # unchanged


@pytest.mark.asyncio
async def test_verifier_two_evidence_items_verified():
    v = VerifierAgent()
    finding = {
        "observation": "nginx version disclosed",
        "evidence": [
            {"source": "nmap", "content": "banner: nginx/1.18.0"},
            {"source": "curl", "content": "Server: nginx/1.18.0"},
        ],
        "confidence": 0.6,
    }
    out = await v.verify_finding(finding)
    assert out["status"] == "VERIFIED"
    assert "2 evidence items" in out["verification_notes"]
    assert out["confidence"] == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_verifier_confidence_capped_at_one():
    v = VerifierAgent()
    finding = {
        "observation": "x",
        "evidence": [{"content": "a"}, {"content": "b"}],
        "confidence": 0.95,
    }
    out = await v.verify_finding(finding)
    assert out["status"] == "VERIFIED"
    assert out["confidence"] == 1.0


@pytest.mark.asyncio
async def test_verifier_single_evidence_likely():
    v = VerifierAgent()
    finding = {
        "observation": "x",
        "evidence": [{"source": "nmap", "content": "one item"}],
        "confidence": 0.5,
    }
    out = await v.verify_finding(finding)
    assert out["status"] == "LIKELY"
    assert out["confidence"] == pytest.approx(0.5)  # unchanged for LIKELY


@pytest.mark.asyncio
async def test_verifier_contentless_evidence_rejected():
    v = VerifierAgent()
    finding = {
        "observation": "x",
        "evidence": [{"source": "nmap"}, {"source": "curl"}],  # no content
        "confidence": 0.4,
    }
    out = await v.verify_finding(finding)
    assert out["status"] == "REJECTED"
    assert "lack content" in out["verification_notes"]
    assert out["confidence"] == pytest.approx(0.1)  # 0.4 - 0.3


@pytest.mark.asyncio
async def test_verifier_confidence_floor_at_zero():
    v = VerifierAgent()
    finding = {
        "observation": "x",
        "evidence": ["not a dict"],
        "confidence": 0.1,
    }
    out = await v.verify_finding(finding)
    assert out["status"] == "REJECTED"
    assert out["confidence"] == 0.0


@pytest.mark.asyncio
async def test_verifier_stores_finding_in_memory():
    mem = FakeMemory()
    v = VerifierAgent(memory_manager=mem)
    finding = {
        "observation": "x",
        "evidence": [{"content": "a"}, {"content": "b"}],
        "confidence": 0.5,
    }
    out = await v.verify_finding(finding)
    assert out["id"] == "finding-1"
    assert mem.findings[0]["status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_verifier_challenge_no_evidence():
    v = VerifierAgent(llm_gateway=FakeGateway(success=False))
    out = await v.challenge_conclusion("target is vulnerable", [], None)
    assert out["verified"] is False
    assert out["status"] == "UNVERIFIED"
    assert out["llm_review"] is None
    assert any("No direct evidence" in c for c in out["challenges"])
    assert any("No tool output" in c for c in out["challenges"])


@pytest.mark.asyncio
async def test_verifier_challenge_unknown_source_flagged():
    v = VerifierAgent(llm_gateway=FakeGateway(success=False))
    out = await v.challenge_conclusion(
        "vulnerable",
        [{"content": "mystery evidence"}],  # source defaults to unknown
        "some tool output",
    )
    assert out["verified"] is False
    assert any("source unknown" in c for c in out["challenges"])


@pytest.mark.asyncio
async def test_verifier_challenge_verified_with_solid_evidence():
    v = VerifierAgent(llm_gateway=FakeGateway(success=False))
    out = await v.challenge_conclusion(
        "nginx 1.18.0 is exposed",
        [{"source": "nmap", "content": "banner grab"},
         {"source": "curl", "content": "server header"}],
        "nmap scan output",
    )
    assert out["challenges"] == []
    assert out["verified"] is True
    assert out["status"] == "VERIFIED"


@pytest.mark.asyncio
async def test_verifier_challenge_llm_review_appended():
    gw = FakeGateway(content='{"challenges": ["sample too small"], "verdict": "weak"}')
    v = VerifierAgent(llm_gateway=gw)
    out = await v.challenge_conclusion(
        "conclusion",
        [{"source": "nmap", "content": "e1"}],
        "tool output",
    )
    assert out["llm_review"]["verdict"] == "weak"
    assert "LLM reviewer: sample too small" in out["challenges"]
    assert out["verified"] is False


@pytest.mark.asyncio
async def test_verifier_llm_challenge_gateway_failure_returns_none():
    v = VerifierAgent(llm_gateway=FakeGateway(success=False))
    review = await v._llm_challenge("conclusion", [], None)
    assert review is None


@pytest.mark.asyncio
async def test_verifier_llm_challenge_exception_returns_none():
    v = VerifierAgent(llm_gateway=FakeGateway(exc=OSError("network down")))
    review = await v._llm_challenge("conclusion", [], None)
    assert review is None


def test_verifier_parse_llm_review_plain_json():
    out = VerifierAgent._parse_llm_review('{"challenges": ["c1"]}')
    assert out == {"challenges": ["c1"]}


def test_verifier_parse_llm_review_fenced_json():
    out = VerifierAgent._parse_llm_review('```json\n{"verdict": "ok"}\n```')
    assert out == {"verdict": "ok"}


def test_verifier_parse_llm_review_non_json():
    assert VerifierAgent._parse_llm_review("not json at all") is None


def test_verifier_parse_llm_review_empty():
    assert VerifierAgent._parse_llm_review("") is None


def test_verifier_parse_llm_review_non_dict_json():
    assert VerifierAgent._parse_llm_review('["a", "b"]') is None


# ---------------------------------------------------------------------------
# AnalystAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analyst_run_with_memory_and_findings():
    gw = FakeGateway(content="risk analysis")
    mem = FakeMemory(search_results=[
        {"observation": "past sqli", "result": "success", "score": 0.9},
    ])
    log = FakeLogger()
    agent = AnalystAgent(llm_gateway=gw, memory_manager=mem, session_logger=log)
    result = await agent.run({
        "target_id": "juice-shop", "session_id": "sess-1",
        "findings": [{"observation": "sqli found", "evidence": ["e"]}],
        "evidence": [{"type": "http", "content": "error-based payload"}],
        "hypothesis": "auth bypass possible",
    })
    assert result["analysis"] == "risk analysis"
    assert result["findings_count"] == 1
    assert result["evidence_count"] == 1
    assert result["experiences_used"] == 1
    # memory searched with the first finding's observation
    assert mem.search_queries[0][0] == "sqli found"
    assert mem.search_queries[0][1] == 3
    # experience recorded
    assert mem.experiences[0]["action"] == "analysis"
    assert mem.experiences[0]["confidence"] == 0.7
    # logger got the planner-category event (after _llm_call's own entry)
    planner_events = [e for e in log.events if e[1] == "planner"]
    assert planner_events[0][0] == "sess-1"
    assert planner_events[0][2]["agent"] == "analyst"
    # prompt includes the past experience and the finding
    prompt = gw.calls[0]["prompt"]
    assert "past sqli" in prompt
    assert "sqli found" in prompt
    assert "error-based payload" in prompt
    assert "auth bypass possible" in prompt


@pytest.mark.asyncio
async def test_analyst_run_without_memory():
    gw = FakeGateway()
    agent = AnalystAgent(llm_gateway=gw)
    result = await agent.run({
        "target_id": "t", "session_id": "s",
        "findings": [{"observation": "x"}], "evidence": [],
    })
    assert result["experiences_used"] == 0
    assert result["analysis"] == "analysis output"


@pytest.mark.asyncio
async def test_analyst_run_empty_findings_no_search():
    mem = FakeMemory()
    agent = AnalystAgent(llm_gateway=FakeGateway(), memory_manager=mem)
    result = await agent.run({
        "target_id": "t", "session_id": "s",
        "findings": [], "evidence": [],
    })
    assert result["findings_count"] == 0
    assert mem.search_queries == []  # no search without findings
    assert len(mem.experiences) == 1  # but experience still recorded


# ---------------------------------------------------------------------------
# CoderAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coder_analyze_sensitive_routes_local():
    gw = FakeGateway(content="vulnerability: buffer overflow at line 3")
    agent = CoderAgent(llm_gateway=gw)
    result = await agent.run({
        "action": "analyze", "code": "def f(): pass",
        "target_id": "t", "session_id": "s", "language": "python",
    })
    assert result["action"] == "analyze"
    assert result["output"] == "vulnerability: buffer overflow at line 3"
    assert result["code_length"] == len("vulnerability: buffer overflow at line 3")
    assert result["sensitive"] is True  # default
    # sensitive source routes to the sensitive_source_code role
    assert gw.calls[0]["role"] == "sensitive_source_code"
    assert "def f(): pass" in gw.calls[0]["prompt"]


@pytest.mark.asyncio
async def test_coder_analyze_non_sensitive():
    gw = FakeGateway()
    agent = CoderAgent(llm_gateway=gw)
    result = await agent.run({
        "action": "analyze", "code": "print('hi')", "sensitive": False,
        "target_id": "t", "session_id": "s",
    })
    assert result["sensitive"] is False
    assert gw.calls[0]["role"] == "code_generation"


@pytest.mark.asyncio
async def test_coder_generate():
    gw = FakeGateway(content="import os\nos.system('ls')")
    mem = FakeMemory()
    agent = CoderAgent(llm_gateway=gw, memory_manager=mem)
    result = await agent.run({
        "action": "generate", "description": "list files in a directory",
        "language": "python", "target_id": "t", "session_id": "s",
        "sensitive": False,
    })
    assert result["action"] == "generate"
    assert result["output"] == "import os\nos.system('ls')"
    assert gw.calls[0]["role"] == "code_generation"
    assert "list files in a directory" in gw.calls[0]["prompt"]
    # generation records lower confidence than analysis
    assert mem.experiences[0]["confidence"] == 0.6


@pytest.mark.asyncio
async def test_coder_unknown_action():
    gw = FakeGateway()
    agent = CoderAgent(llm_gateway=gw)
    result = await agent.run({"action": "refactor", "session_id": "s"})
    assert "Unknown action" in result["error"]
    assert gw.calls == []  # no LLM call for invalid actions


@pytest.mark.asyncio
async def test_coder_logs_and_records_experience():
    gw = FakeGateway()
    mem = FakeMemory()
    log = FakeLogger()
    agent = CoderAgent(llm_gateway=gw, memory_manager=mem, session_logger=log)
    await agent.run({
        "action": "analyze", "code": "x=1", "session_id": "sess-9",
        "target_id": "t",
    })
    # the coder's own model_calls event carries the session id
    # (_llm_call logs a separate advisory event with an empty session id)
    own = [e for e in log.events if e[0] == "sess-9"]
    assert own[0][1] == "model_calls"
    assert own[0][2]["action"] == "analyze"


# ---------------------------------------------------------------------------
# ReporterAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reporter_generates_report_with_findings():
    gw = FakeGateway(content="# Final Report\nAll clear.")
    mem = FakeMemory()
    log = FakeLogger()
    agent = ReporterAgent(llm_gateway=gw, memory_manager=mem, session_logger=log)
    result = await agent.run({
        "target_id": "juice-shop",
        "session_id": "sess-r1",
        "findings": [
            {"status": "VERIFIED", "observation": "XSS in search",
             "confidence": 0.9, "source": "recon_agent"},
            {"status": "UNVERIFIED", "observation": "open port 3000",
             "confidence": 0.5, "source": "recon_agent"},
        ],
        "evidence": ["ev-1", "ev-2", "ev-3"],
        "analysis": "Two findings, one verified.",
        "objective": "Assess Juice Shop",
    })
    assert result["status"] == "generated"
    assert result["content"] == "# Final Report\nAll clear."
    assert result["findings_count"] == 2
    assert result["evidence_count"] == 3
    assert result["target_id"] == "juice-shop"
    assert result["session_id"] == "sess-r1"
    assert result["objective"] == "Assess Juice Shop"
    assert result["generated_at"]
    # routed to the report_generation task type
    assert gw.calls[0]["role"] == "report_generation"
    # findings summary is embedded in the prompt
    assert "XSS in search" in gw.calls[0]["prompt"]
    assert "VERIFIED" in gw.calls[0]["prompt"]
    # evidence file saved via the session logger
    assert log.saved_evidence == [("sess-r1", "final_report", result)]
    # experience recorded
    assert len(mem.experiences) == 1
    assert mem.experiences[0]["action"] == "reporting"
    assert mem.experiences[0]["tool"] == "reporter_agent"
    assert mem.experiences[0]["confidence"] == 0.9


@pytest.mark.asyncio
async def test_reporter_empty_findings_and_evidence():
    gw = FakeGateway(content="Nothing to report.")
    agent = ReporterAgent(llm_gateway=gw)
    result = await agent.run({
        "target_id": "t", "session_id": "sess-r2",
        "findings": [], "evidence": [], "analysis": "", "objective": "o",
    })
    assert result["findings_count"] == 0
    assert result["evidence_count"] == 0
    # empty-findings branch renders the "None recorded." summary
    assert "None recorded." in gw.calls[0]["prompt"]
    # empty-evidence branch renders the "No evidence items collected." line
    assert "No evidence items collected." in gw.calls[0]["prompt"]


@pytest.mark.asyncio
async def test_reporter_no_logger_no_memory():
    """run() works with neither logger nor memory (no evidence save)."""
    gw = FakeGateway(content="r")
    agent = ReporterAgent(llm_gateway=gw)
    result = await agent.run({
        "target_id": "t", "session_id": "sess-r3",
        "findings": [], "evidence": [], "analysis": "", "objective": "o",
    })
    assert result["status"] == "generated"
    assert result["content"] == "r"


@pytest.mark.asyncio
async def test_reporter_llm_unavailable_still_reports():
    """A failed LLM call yields the [LLM_UNAVAILABLE] marker, not a crash."""
    gw = FakeGateway(success=False)
    agent = ReporterAgent(llm_gateway=gw)
    result = await agent.run({
        "target_id": "t", "session_id": "sess-r4",
        "findings": [], "evidence": [], "analysis": "", "objective": "o",
    })
    assert result["status"] == "generated"
    assert result["content"].startswith("[LLM_UNAVAILABLE:")


# ---------------------------------------------------------------------------
# ResearcherAgent
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_researcher_run_with_memory():
    gw = FakeGateway(content="CVE-2024-1234 affects the target.")
    mem = FakeMemory(search_results=[
        {"observation": "target runs nginx 1.18", "result": "success"},
    ])
    log = FakeLogger()
    agent = ResearcherAgent(llm_gateway=gw, memory_manager=mem, session_logger=log)
    result = await agent.run({
        "target": "juice-shop", "topic": "known CVEs",
        "session_id": "sess-res1", "target_id": "juice-shop",
    })
    assert result["research"] == "CVE-2024-1234 affects the target."
    assert result["target"] == "juice-shop"
    assert result["topic"] == "known CVEs"
    assert result["relevant_experiences"] == 1
    assert result["findings"] == []
    # memory searched with "target topic" query
    assert mem.search_queries == [("juice-shop known CVEs", 5)]
    # routed to vulnerability_research
    assert gw.calls[0]["role"] == "vulnerability_research"
    # past experience embedded in the prompt
    assert "target runs nginx 1.18" in gw.calls[0]["prompt"]
    # experience recorded
    assert len(mem.experiences) == 1
    assert mem.experiences[0]["action"] == "research"
    assert mem.experiences[0]["tool"] == "researcher_agent"
    assert mem.experiences[0]["confidence"] == 0.6
    # event logged under the session id
    own = [e for e in log.events if e[0] == "sess-res1"]
    assert own[0][1] == "planner"
    assert own[0][2]["agent"] == "researcher"


@pytest.mark.asyncio
async def test_researcher_run_without_memory():
    gw = FakeGateway(content="no prior context")
    agent = ResearcherAgent(llm_gateway=gw)
    result = await agent.run({
        "target": "metasploitable", "topic": "exploit paths",
        "session_id": "sess-res2",
    })
    assert result["relevant_experiences"] == 0
    # no experiences section in the prompt
    assert "nginx" not in gw.calls[0]["prompt"]
    assert result["research"] == "no prior context"


@pytest.mark.asyncio
async def test_researcher_llm_unavailable():
    gw = FakeGateway(success=False)
    agent = ResearcherAgent(llm_gateway=gw)
    result = await agent.run({
        "target": "t", "topic": "x", "session_id": "sess-res3",
    })
    assert result["research"].startswith("[LLM_UNAVAILABLE:")
