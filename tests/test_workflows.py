"""Tests for the workflows subsystem (cyberai.orchestrator.workflows).

Covers:
  WorkflowManager — predefined workflows, registration, lookups
  KillChainEngine / TargetChain — F2T2EA state machine:
    - phase transitions and ordering
    - invalid-transition errors
    - failure / timeout handling
    - verification promotion on completion
    - persistence (save/load round-trip)
    - failure-memory integration (ghost wargaming)
"""

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cyberai.orchestrator.workflows import (
    KillChainEngine,
    Phase,
    PhaseStatus,
    PHASE_ORDER,
    TargetChain,
    Verification,
    WorkflowManager,
)
from cyberai.orchestrator.workflows.kill_chain import KillChainError


# ---------------------------------------------------------------------------
# WorkflowManager
# ---------------------------------------------------------------------------

class TestWorkflowManager:
    def test_predefined_workflows_present(self):
        wf = WorkflowManager()
        names = wf.list_workflows()
        assert "recon_to_report" in names
        assert "code_audit" in names
        assert "target_assessment" in names

    def test_list_workflows_sorted(self):
        assert WorkflowManager().list_workflows() == sorted(WorkflowManager().list_workflows())

    def test_get_workflow_definition(self):
        wf = WorkflowManager().get_workflow("recon_to_report")
        assert wf["name"] == "Reconnaissance to Report"
        assert isinstance(wf["steps"], list) and wf["steps"]

    def test_get_workflow_unknown_returns_none(self):
        assert WorkflowManager().get_workflow("nope") is None

    def test_get_workflow_steps(self):
        steps = WorkflowManager().get_workflow_steps("code_audit")
        assert steps[0]["agent"] == "coder"
        assert all("agent" in s and "action" in s for s in steps)

    def test_get_workflow_steps_unknown_returns_empty(self):
        assert WorkflowManager().get_workflow_steps("nope") == []

    def test_register_custom_workflow(self):
        wf = WorkflowManager()
        wf.register_workflow("custom", {"name": "Custom", "steps": [{"agent": "x"}]})
        assert "custom" in wf.list_workflows()
        assert wf.get_workflow_steps("custom") == [{"agent": "x"}]

    def test_register_does_not_mutate_predefined_constant(self):
        wf = WorkflowManager()
        wf.register_workflow("custom", {"name": "Custom", "steps": []})
        # A second manager starts from the pristine predefined set.
        assert "custom" not in WorkflowManager().list_workflows()

    def test_steps_reference_known_agents(self):
        wf = WorkflowManager()
        known_agents = {
            "researcher", "recon", "analyst", "verifier", "reporter",
            "coder", "planner",
        }
        for name in wf.list_workflows():
            for step in wf.get_workflow_steps(name):
                assert step["agent"] in known_agents, (name, step)


# ---------------------------------------------------------------------------
# TargetChain — the F2T2EA state machine
# ---------------------------------------------------------------------------

class TestTargetChain:
    def test_new_chain_starts_at_find(self):
        chain = TargetChain("juice-shop")
        assert chain.current_phase == Phase.FIND
        assert chain.phase_status["FIND"] == PhaseStatus.ACTIVE.value
        assert all(
            chain.phase_status[p] == PhaseStatus.PENDING.value
            for p in PHASE_ORDER[1:]
        )
        assert chain.status == "ACTIVE"
        assert chain.verification == Verification.UNVERIFIED.value

    def test_advance_walks_all_phases_in_order(self):
        chain = TargetChain("t")
        seen = []
        for _ in range(len(PHASE_ORDER)):
            seen.append(chain.current_phase.value)
            chain.advance()
        assert seen == PHASE_ORDER
        # The final advance (from ASSESS) completes the chain.
        assert chain.current_phase == Phase.ASSESS
        assert chain.status == "COMPLETE"

    def test_advance_records_note_and_finding(self):
        chain = TargetChain("t")
        chain.advance(note="found hosts", finding={"verification": "LIKELY"})
        assert chain.phase_notes["FIND"] == "found hosts"
        assert len(chain.findings) == 1
        assert chain.findings[0]["phase"] == "FIND"
        assert chain.findings[0]["verification"] == "LIKELY"

    def test_advance_inactive_phase_raises(self):
        chain = TargetChain("t")
        # Tamper: FIND is no longer ACTIVE in the status map.
        chain.phase_status[Phase.FIND.value] = PhaseStatus.PENDING.value
        with pytest.raises(KillChainError, match="PENDING"):
            chain.advance()

    def test_advance_after_complete_raises(self):
        chain = TargetChain("t")
        for _ in range(len(PHASE_ORDER)):
            chain.advance()
        assert chain.status == "COMPLETE"
        with pytest.raises(KillChainError, match="COMPLETE"):
            chain.advance()

    def test_fail_aborts_chain(self):
        chain = TargetChain("t")
        chain.fail("scanner crashed")
        assert chain.status == "ABORTED"
        assert chain.phase_status["FIND"] == PhaseStatus.FAILED.value
        assert chain.error == "scanner crashed"
        with pytest.raises(KillChainError, match="ABORTED"):
            chain.advance()

    def test_fail_without_abort_keeps_chain_active(self):
        chain = TargetChain("t")
        chain.fail("transient", abort=False)
        assert chain.status == "ACTIVE"
        assert chain.phase_status["FIND"] == PhaseStatus.FAILED.value

    def test_timeout_phase_marks_aborted(self):
        chain = TargetChain("t")
        # Backdate the FIND start beyond its 600s limit.
        chain.phase_started[Phase.FIND.value] = time.time() - 700
        assert chain.timeout_phase() is True
        assert chain.phase_status["FIND"] == PhaseStatus.TIMED_OUT.value
        assert chain.status == "ABORTED"
        assert "timed out" in chain.error

    def test_timeout_phase_within_limit_returns_false(self):
        chain = TargetChain("t")
        assert chain.timeout_phase() is False
        assert chain.status == "ACTIVE"

    def test_timeout_phase_not_active_returns_false(self):
        chain = TargetChain("t")
        chain.phase_status[Phase.FIND.value] = PhaseStatus.COMPLETE.value
        assert chain.timeout_phase(Phase.FIND) is False

    def test_verification_promotion_verified(self):
        chain = TargetChain("t")
        for phase in PHASE_ORDER[:-1]:
            chain.advance(finding={"verification": "VERIFIED"})
        chain.advance()  # ASSESS completes the chain
        assert chain.verification == Verification.VERIFIED.value

    def test_verification_promotion_likely(self):
        chain = TargetChain("t")
        for _ in PHASE_ORDER:
            chain.advance(finding={"verification": "LIKELY"})
        assert chain.verification == Verification.LIKELY.value

    def test_verification_promotion_rejected(self):
        chain = TargetChain("t")
        for _ in PHASE_ORDER:
            chain.advance(finding={"verification": "REJECTED"})
        assert chain.verification == Verification.REJECTED.value

    def test_verification_promotion_verified_beats_rejected(self):
        chain = TargetChain("t")
        chain.advance(finding={"verification": "REJECTED"})
        for _ in PHASE_ORDER[1:]:
            chain.advance(finding={"verification": "VERIFIED"})
        assert chain.verification == Verification.VERIFIED.value

    def test_to_dict_round_trip(self):
        chain = TargetChain("round-trip")
        chain.advance(note="n1", finding={"verification": "LIKELY"})
        chain.fail("boom") if False else None  # keep chain ACTIVE for round-trip
        d = chain.to_dict()
        restored = TargetChain.from_dict(d)
        assert restored.to_dict() == d
        assert restored.current_phase == Phase.FIX
        assert restored.findings == chain.findings

    def test_from_dict_defaults_for_legacy_state(self):
        d = {
            "chain_id": "abc", "target": "t", "created_at": 1.0, "updated_at": 1.0,
            "current_phase": "ENGAGE", "phase_status": {}, "phase_started": {},
            "phase_ended": {},
        }
        restored = TargetChain.from_dict(d)
        assert restored.verification == Verification.UNVERIFIED.value
        assert restored.findings == []
        assert restored.status == "ACTIVE"


# ---------------------------------------------------------------------------
# KillChainEngine — coordination + persistence
# ---------------------------------------------------------------------------

class TestKillChainEngine:
    def test_start_chain_creates_and_persists(self, tmp_path):
        engine = KillChainEngine(state_path=tmp_path / "kc.json")
        chain = engine.start_chain("juice-shop")
        assert chain.status == "ACTIVE"
        assert (tmp_path / "kc.json").exists()

    def test_start_chain_resumes_active(self, tmp_path):
        engine = KillChainEngine(state_path=tmp_path / "kc.json")
        first = engine.start_chain("t1")
        second = engine.start_chain("t1")
        assert first is second  # resume, not restart

    def test_start_chain_restarts_finished(self, tmp_path):
        engine = KillChainEngine(state_path=tmp_path / "kc.json")
        first = engine.start_chain("t1")
        for _ in PHASE_ORDER:
            first.advance()
        fresh = engine.start_chain("t1")
        assert fresh is not first
        assert fresh.current_phase == Phase.FIND
        assert fresh.status == "ACTIVE"

    def test_persistence_across_instances(self, tmp_path):
        e1 = KillChainEngine(state_path=tmp_path / "kc.json")
        e1.start_chain("t1")
        e1.advance("t1", note="progress")  # engine.advance persists state
        e2 = KillChainEngine(state_path=tmp_path / "kc.json")
        chain = e2.get_chain("t1")
        assert chain is not None
        assert chain.current_phase == Phase.FIX
        assert chain.phase_notes["FIND"] == "progress"

    def test_advance_unknown_target_raises(self, tmp_path):
        engine = KillChainEngine(state_path=tmp_path / "kc.json")
        with pytest.raises(KillChainError, match="no active chain"):
            engine.advance("ghost")

    def test_engine_advance_and_fail(self, tmp_path):
        engine = KillChainEngine(state_path=tmp_path / "kc.json")
        engine.start_chain("t1")
        d = engine.advance("t1", note="ok")
        assert d["current_phase"] == "FIX"
        d = engine.fail("t1", "tool broke")
        assert d["status"] == "ABORTED"

    def test_check_timeouts_reports_stale_chain(self, tmp_path):
        engine = KillChainEngine(state_path=tmp_path / "kc.json")
        chain = engine.start_chain("stale")
        chain.phase_started[Phase.FIND.value] = time.time() - 700
        timed_out = engine.check_timeouts()
        assert len(timed_out) == 1
        assert timed_out[0]["target"] == "stale"
        assert engine.get_chain("stale").status == "ABORTED"

    def test_check_timeouts_empty_when_healthy(self, tmp_path):
        engine = KillChainEngine(state_path=tmp_path / "kc.json")
        engine.start_chain("healthy")
        assert engine.check_timeouts() == []

    def test_failure_memory_recorded_on_fail(self, tmp_path):
        memory = MagicMock()
        engine = KillChainEngine(state_path=tmp_path / "kc.json",
                                 memory_store=memory)
        engine.start_chain("t1")
        engine.fail("t1", "explode")
        memory.record_failure.assert_called_once()
        kwargs = memory.record_failure.call_args.kwargs
        assert kwargs["reason"] == "explode"
        assert kwargs["failure_category"] == "execution"
        assert kwargs["strategy_id"].startswith("killchain-")

    def test_failure_memory_recorded_on_bad_transition(self, tmp_path):
        memory = MagicMock()
        engine = KillChainEngine(state_path=tmp_path / "kc.json",
                                 memory_store=memory)
        engine.start_chain("t1")
        chain = engine.get_chain("t1")
        chain.status = "ABORTED"  # force invalid transition
        with pytest.raises(KillChainError):
            engine.advance("t1")
        memory.record_failure.assert_called_once()

    def test_failure_memory_swallows_store_errors(self, tmp_path):
        memory = MagicMock()
        memory.record_failure.side_effect = RuntimeError("store down")
        engine = KillChainEngine(state_path=tmp_path / "kc.json",
                                 memory_store=memory)
        engine.start_chain("t1")
        d = engine.fail("t1", "boom")  # must not raise
        assert d["status"] == "ABORTED"

    def test_status_aggregates_chains(self, tmp_path):
        engine = KillChainEngine(state_path=tmp_path / "kc.json")
        engine.start_chain("active-1")
        engine.start_chain("active-2")
        done = engine.start_chain("done-1")
        for _ in PHASE_ORDER:
            done.advance()
        engine.start_chain("dead-1").fail("x")

        s = engine.status()
        assert s["total"] == 4
        assert s["active"] == 2
        assert s["complete"] == 1
        assert s["aborted"] == 1
        assert s["active_by_phase"]["FIND"] == 2
        assert len(s["chains"]) == 4

    def test_list_chains_serializable(self, tmp_path):
        engine = KillChainEngine(state_path=tmp_path / "kc.json")
        engine.start_chain("t1")
        chains = engine.list_chains()
        assert len(chains) == 1
        assert chains[0]["target"] == "t1"

    def test_reset_clears_state(self, tmp_path):
        engine = KillChainEngine(state_path=tmp_path / "kc.json")
        engine.start_chain("t1")
        engine.reset()
        assert engine.get_chain("t1") is None
        assert engine.status()["total"] == 0

    def test_corrupt_state_file_ignored(self, tmp_path):
        p = tmp_path / "kc.json"
        p.write_text("not json {", encoding="utf-8")
        engine = KillChainEngine(state_path=p)  # must not raise
        assert engine.get_chain("anything") is None

    def test_default_state_path_under_lab_state(self):
        engine = KillChainEngine(state_path=Path("lab/state/kill_chains_test_probe.json"))
        try:
            assert engine.state_path.parent.name == "state"
        finally:
            engine.state_path.unlink(missing_ok=True)
