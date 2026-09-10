"""Tests for the Self-Improvement subsystem (cyberai.self_improvement).

Covers the controlled AI-change pipeline:
  ImprovementProposal â€” dataclass serialization round-trips, defaults
  SelfImprovementPipeline:
    - proposal creation + persistence
    - static checks (missing files, syntax errors)
    - security checks (dangerous patterns in patches)
    - benchmark comparison (accept only >= baseline)
    - approve / reject lifecycle
    - apply() refuses unapproved proposals (the core safety property)
    - rollback() refuses non-applied proposals
    - listing + status aggregation
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cyberai.self_improvement.pipeline import SelfImprovementPipeline
from cyberai.self_improvement.proposal import (
    ImprovementProposal,
    ProposalStatus,
)


@pytest.fixture
def pipeline(tmp_path):
    return SelfImprovementPipeline(proposals_dir=tmp_path / "proposals")


class TestProposalDataclass:
    def test_defaults(self):
        p = ImprovementProposal(reason="why")
        assert p.status == ProposalStatus.DRAFT.value
        assert p.risk == "low"
        assert p.files_changed == []
        assert p.tests == []
        assert p.proposal_id  # uuid assigned
        assert p.created_at

    def test_to_dict_round_trip(self):
        p = ImprovementProposal(
            reason="optimize router",
            files_changed=["cyberai/x.py"],
            tests=["tests/test_x.py"],
            benchmark="latency",
            before_score=0.9,
            risk="medium",
        )
        restored = ImprovementProposal.from_dict(p.to_dict())
        assert restored.reason == "optimize router"
        assert restored.files_changed == ["cyberai/x.py"]
        assert restored.before_score == 0.9
        assert restored.risk == "medium"
        assert restored.proposal_id == p.proposal_id

    def test_from_dict_defaults_for_missing_fields(self):
        restored = ImprovementProposal.from_dict({"reason": "r"})
        assert restored.status == ProposalStatus.DRAFT.value
        assert restored.patch == ""
        assert restored.metadata == {}

    def test_status_values(self):
        assert {s.value for s in ProposalStatus} == {
            "draft", "pending_review", "approved",
            "rejected", "applied", "rolled_back",
        }


class TestCreateProposal:
    def test_create_persists_to_disk(self, pipeline):
        proposal = pipeline.create_proposal(
            reason="speed up scanner",
            files_changed=["cyberai/scanner.py"],
            patch="+++ improved",
            tests=["tests/test_scanner.py"],
            benchmark="throughput",
            before_score=10.0,
            risk="low",
        )
        path = pipeline.proposals_dir / f"{proposal.proposal_id}.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["reason"] == "speed up scanner"
        assert data["status"] == ProposalStatus.DRAFT.value

    def test_create_stores_in_memory(self, pipeline):
        proposal = pipeline.create_proposal(reason="r", files_changed=[])
        assert pipeline.get_proposal(proposal.proposal_id) is proposal

    def test_load_existing_proposals_on_init(self, tmp_path):
        p1 = SelfImprovementPipeline(proposals_dir=tmp_path / "p")
        created = p1.create_proposal(reason="persisted", files_changed=[])
        # A new pipeline instance over the same dir reloads it.
        p2 = SelfImprovementPipeline(proposals_dir=tmp_path / "p")
        loaded = p2.get_proposal(created.proposal_id)
        assert loaded is not None
        assert loaded.reason == "persisted"

    def test_corrupt_proposal_file_skipped(self, tmp_path):
        d = tmp_path / "p"
        d.mkdir()
        (d / "bad.json").write_text("{broken", encoding="utf-8")
        pipeline = SelfImprovementPipeline(proposals_dir=d)  # no crash
        assert pipeline.get_status()["total_proposals"] == 0


class TestStaticChecks:
    def test_missing_file_fails(self, pipeline):
        proposal = pipeline.create_proposal(
            reason="r", files_changed=["no/such/file.py"])
        result = pipeline._run_static_checks(proposal)
        assert result["passed"] is False
        assert any("File not found" in e for e in result["errors"])

    def test_syntax_error_fails(self, pipeline, tmp_path):
        bad = tmp_path / "bad.py"
        bad.write_text("def broken(:\n", encoding="utf-8")
        proposal = pipeline.create_proposal(
            reason="r", files_changed=[str(bad)])
        result = pipeline._run_static_checks(proposal)
        assert result["passed"] is False
        assert any("Syntax error" in e for e in result["errors"])

    def test_valid_file_passes(self, pipeline, tmp_path):
        good = tmp_path / "good.py"
        good.write_text("x = 1\n", encoding="utf-8")
        proposal = pipeline.create_proposal(
            reason="r", files_changed=[str(good)])
        result = pipeline._run_static_checks(proposal)
        assert result["passed"] is True
        assert result["errors"] == []

    def test_non_python_file_skips_compile(self, pipeline, tmp_path):
        doc = tmp_path / "notes.md"
        doc.write_text("# fine", encoding="utf-8")
        proposal = pipeline.create_proposal(
            reason="r", files_changed=[str(doc)])
        assert pipeline._run_static_checks(proposal)["passed"] is True


class TestSecurityChecks:
    @pytest.mark.parametrize("pattern_snippet", [
        "os.system(", "subprocess.call(", "subprocess.Popen(",
        "eval(", "exec(", "pickle.loads(", "yaml.load(",
    ])
    def test_dangerous_patterns_rejected(self, pipeline, pattern_snippet):
        proposal = pipeline.create_proposal(
            reason="r", files_changed=[], patch=f"x = {pattern_snippet}'cmd')")
        result = pipeline._run_security_checks(proposal)
        assert result["passed"] is False
        assert any("Dangerous pattern" in e for e in result["errors"])

    def test_clean_patch_passes(self, pipeline):
        proposal = pipeline.create_proposal(
            reason="r", files_changed=[], patch="def add(a, b):\n    return a + b\n")
        result = pipeline._run_security_checks(proposal)
        assert result["passed"] is True
        assert result["errors"] == []


class TestValidation:
    def test_run_validation_aggregates(self, pipeline, tmp_path):
        good = tmp_path / "ok.py"
        good.write_text("y = 2\n", encoding="utf-8")
        proposal = pipeline.create_proposal(
            reason="r", files_changed=[str(good)], patch="z = 3")
        result = pipeline.run_validation(proposal)
        assert set(result) == {"static_checks", "unit_tests",
                               "security_checks", "all_passed"}
        assert result["all_passed"] is True

    def test_unit_tests_skipped_when_none(self, pipeline):
        proposal = pipeline.create_proposal(reason="r", files_changed=[])
        result = pipeline._run_unit_tests(proposal)
        assert result["passed"] is True
        assert result.get("skipped") is True

    def test_unit_test_failure_fails_validation(self, pipeline, tmp_path):
        proposal = pipeline.create_proposal(
            reason="r", files_changed=[], tests=["tests/test_does_not_exist_xyz.py"])
        result = pipeline._run_unit_tests(proposal)
        assert result["passed"] is False


class TestBenchmark:
    def test_improvement_accepted(self, pipeline):
        proposal = pipeline.create_proposal(reason="r", files_changed=[], before_score=10.0)
        assert pipeline.compare_benchmark(proposal, 12.0) is True
        assert proposal.after_score == 12.0

    def test_regression_rejected(self, pipeline):
        proposal = pipeline.create_proposal(reason="r", files_changed=[], before_score=10.0)
        assert pipeline.compare_benchmark(proposal, 9.9) is False

    def test_equal_score_accepted(self, pipeline):
        proposal = pipeline.create_proposal(reason="r", files_changed=[], before_score=10.0)
        assert pipeline.compare_benchmark(proposal, 10.0) is True


class TestLifecycle:
    def test_approve_sets_status(self, pipeline):
        proposal = pipeline.create_proposal(reason="r", files_changed=[])
        pipeline.approve(proposal)
        assert proposal.status == ProposalStatus.APPROVED.value
        assert proposal.reviewed_at
        # Persisted.
        data = json.loads(
            (pipeline.proposals_dir / f"{proposal.proposal_id}.json").read_text())
        assert data["status"] == ProposalStatus.APPROVED.value

    def test_reject_sets_reason(self, pipeline):
        proposal = pipeline.create_proposal(reason="r", files_changed=[])
        pipeline.reject(proposal, reason="too risky")
        assert proposal.status == ProposalStatus.REJECTED.value
        assert proposal.metadata["rejection_reason"] == "too risky"

    def test_apply_requires_approval(self, pipeline):
        """THE core safety property: unapproved proposals cannot be applied."""
        proposal = pipeline.create_proposal(reason="r", files_changed=[], patch="changes")
        assert pipeline.apply(proposal) is False
        assert proposal.status == ProposalStatus.DRAFT.value

    def test_rollback_requires_applied(self, pipeline):
        proposal = pipeline.create_proposal(reason="r", files_changed=[])
        assert pipeline.rollback(proposal) is False

    def test_list_proposals_filtered(self, pipeline):
        a = pipeline.create_proposal(reason="a", files_changed=[])
        b = pipeline.create_proposal(reason="b", files_changed=[])
        pipeline.approve(a)
        pipeline.reject(b)
        assert {p.reason for p in pipeline.list_proposals()} == {"a", "b"}
        approved = pipeline.list_proposals(status=ProposalStatus.APPROVED.value)
        assert {p.reason for p in approved} == {"a"}

    def test_get_status_counts(self, pipeline):
        a = pipeline.create_proposal(reason="a", files_changed=[])
        b = pipeline.create_proposal(reason="b", files_changed=[])
        pipeline.approve(a)
        pipeline.reject(b)
        s = pipeline.get_status()
        assert s["total_proposals"] == 2
        assert s["approved"] == 1
        assert s["rejected"] == 1
        assert s["applied"] == 0
