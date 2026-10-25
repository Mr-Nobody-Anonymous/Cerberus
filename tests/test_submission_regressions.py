"""Submission regression tests for CERBERUS.

Verifies all confirmed defects from the submission readiness audit:
  1. No hardcoded machine paths in fix_doctor.py
  2. docker-compose.yml and REPOSITORY_MAP.yaml LiteLLM image reconciliation
  3. No insecure secret defaults (sk-test) in docker-compose.yml
  4. Pinned Docker image tags (no :latest) in docker-compose.yml
  5. pyproject.toml and requirements.txt dependency consistency (prompt-toolkit)
  6. pyproject.toml setuptools package-data includes static web UI assets
  7. start_cerberus.py checks core modules and uses workspace-relative paths
  8. Master get_status() runs safely in an active async loop without unawaited coroutine warnings
  9. Active operations enforce authorized target and allowed actions
  10. Self-improvement pipeline blocks proposals failing validation from approval or application
  11. Seeded demo data is clearly labeled with [DEMO] and never presented as live telemetry
  12. UI server and API endpoints respond healthy
"""

import inspect
import warnings
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from cyberai.config import WORKSPACE_ROOT
from cyberai.orchestrator.master import CyberAIOrchestrator
from cyberai.self_improvement.pipeline import SelfImprovementPipeline
from cyberai.ui.server import APPROVAL_QUEUE, _seed_approvals, app


# ---------------------------------------------------------------------------
# 1. Launcher & Path Portability
# ---------------------------------------------------------------------------
class TestPortabilityAndPackaging:
    def test_fix_doctor_no_hardcoded_machine_path(self):
        fix_doc_path = WORKSPACE_ROOT / "fix_doctor.py"
        assert fix_doc_path.exists()
        content = fix_doc_path.read_text(encoding="utf-8")
        assert "C:\\Users\\" not in content
        assert "Path(__file__)" in content

    def test_docker_compose_and_repository_map_litellm_reconciled(self):
        dc_path = WORKSPACE_ROOT / "docker-compose.yml"
        rm_path = WORKSPACE_ROOT / "REPOSITORY_MAP.yaml"

        dc = yaml.safe_load(dc_path.read_text(encoding="utf-8"))
        rm = yaml.safe_load(rm_path.read_text(encoding="utf-8"))

        litellm_service = dc["services"]["litellm"]
        assert litellm_service["image"] == "ghcr.io/berriai/litellm:v1.97.0"

        # Check REPOSITORY_MAP note
        repo_entry = next((r for r in rm["repositories"] if r.get("original_name") == "litellm"), None)
        assert repo_entry is not None
        assert "ghcr.io/berriai/litellm:v1.97.0" in repo_entry.get("note", "")

    def test_docker_compose_no_insecure_sk_test_default(self):
        dc_text = (WORKSPACE_ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        assert "sk-test" not in dc_text

    def test_docker_compose_images_pinned(self):
        dc = yaml.safe_load((WORKSPACE_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
        for svc_name, svc_conf in dc.get("services", {}).items():
            image = svc_conf.get("image", "")
            if image:
                assert ":latest" not in image, f"Service '{svc_name}' uses floating tag ':latest': {image}"
                assert ":main" not in image, f"Service '{svc_name}' uses floating tag ':main': {image}"

    def test_dependency_consistency_prompt_toolkit(self):
        pyproj_text = (WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        reqs_text = (WORKSPACE_ROOT / "requirements.txt").read_text(encoding="utf-8")

        assert "prompt-toolkit" in pyproj_text
        assert "prompt-toolkit" in reqs_text

    def test_package_data_includes_ui_assets(self):
        pyproj_text = (WORKSPACE_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        for ext in ("*.html", "*.css", "*.js"):
            assert ext in pyproj_text, f"Missing '{ext}' in pyproject.toml package-data"

    def test_start_cerberus_checks_core_modules(self):
        import start_cerberus
        assert hasattr(start_cerberus, "check_core_modules")
        missing = start_cerberus.check_core_modules()
        assert isinstance(missing, list)
        src = inspect.getsource(start_cerberus.check_core_modules)
        assert "prompt_toolkit" in src
        assert "fastapi" in src


# ---------------------------------------------------------------------------
# 2. Master Lifecycle & Warning Free Status
# ---------------------------------------------------------------------------
class TestMasterOrchestratorRobustness:
    @pytest.mark.asyncio
    async def test_get_status_in_async_context_no_unawaited_warning(self):
        orch = CyberAIOrchestrator(simulate=True, local_only=True)
        try:
            with warnings.catch_warnings(record=True) as recorded:
                warnings.simplefilter("always")
                status = orch.get_status()
                # Verify no RuntimeWarning regarding unawaited coroutine
                unawaited = [
                    w for w in recorded
                    if issubclass(w.category, RuntimeWarning) and "was never awaited" in str(w.message)
                ]
                assert len(unawaited) == 0, f"Found unawaited coroutine warning: {unawaited}"
                assert status["platform"] == "Cyber AI"
                assert "agents" in status
                assert "models" in status
        finally:
            orch.close()


# ---------------------------------------------------------------------------
# 3. Security: Active Target Authorization & Allowed Actions
# ---------------------------------------------------------------------------
class TestActiveTargetAuthorization:
    @pytest.mark.asyncio
    async def test_active_run_without_target_rejected(self):
        orch = CyberAIOrchestrator(simulate=False, dry_run=False)
        try:
            with pytest.raises(PermissionError, match="Target ID is required for active operations"):
                await orch.run("Scan production server")
        finally:
            orch.close()

    @pytest.mark.asyncio
    async def test_active_run_unauthorized_target_rejected(self):
        orch = CyberAIOrchestrator(simulate=False, dry_run=False)
        try:
            with pytest.raises(PermissionError, match="is not authorized"):
                await orch.run("Analyze target", target_id="unregistered-rogue-target-999")
        finally:
            orch.close()

    @pytest.mark.asyncio
    async def test_active_run_unauthorized_action_rejected(self):
        orch = CyberAIOrchestrator(simulate=False, dry_run=False)
        # Register a target that explicitly only allows "scan"
        orch.policy.register_target({
            "id": "restricted-target-test",
            "environment": "authorized_lab",
            "allowed": True,
            "allowed_actions": ["scan"],
        })
        try:
            # "analysis" is not in allowed_actions
            with pytest.raises(PermissionError, match="not allowed on target"):
                await orch.run("Analyze target", target_id="restricted-target-test")
        finally:
            # Clean up target
            orch.policy._targets.pop("restricted-target-test", None)
            orch.policy._save_targets()
            orch.close()


# ---------------------------------------------------------------------------
# 4. Security: Self-Improvement Validation Enforcement
# ---------------------------------------------------------------------------
class TestSelfImprovementSecurity:
    def test_approve_blocks_unvalidated_or_failed_proposal(self, tmp_path):
        pipeline = SelfImprovementPipeline(proposals_dir=tmp_path / "proposals")
        # Create proposal with dangerous code pattern that must fail security checks
        proposal = pipeline.create_proposal(
            reason="malicious change attempt",
            files_changed=[],
            patch="import os\nos.system('echo compromised')",
        )
        with pytest.raises(PermissionError, match="validation checks failed"):
            pipeline.approve(proposal)

        assert proposal.status == "rejected"
        assert "Validation failed" in proposal.metadata.get("rejection_reason", "")

    def test_apply_refuses_proposal_without_passed_validation(self, tmp_path):
        pipeline = SelfImprovementPipeline(proposals_dir=tmp_path / "proposals")
        proposal = pipeline.create_proposal(
            reason="bypass attempt",
            files_changed=[],
            patch="import os\nos.system('whoami')",
        )
        # Manually force status to approved to attempt bypass
        proposal.status = "approved"
        applied = pipeline.apply(proposal)
        assert applied is False


# ---------------------------------------------------------------------------
# 5. Demo Data Labeling
# ---------------------------------------------------------------------------
class TestDemoDataLabeling:
    def test_seeded_approvals_explicitly_labeled_demo(self):
        _seed_approvals()
        assert len(APPROVAL_QUEUE) > 0
        for item in APPROVAL_QUEUE:
            if item.get("demo"):
                assert "[DEMO]" in item["action"]
                assert item["source"] == "demo_seed"

    @pytest.mark.asyncio
    async def test_seeded_audit_entries_labeled_demo(self):
        client = TestClient(app)
        r = client.get("/api/audit")
        assert r.status_code == 200
        entries = r.json().get("entries", [])
        for entry in entries:
            if entry.get("demo"):
                assert "[DEMO]" in entry["action"]
                assert entry.get("source") == "demo_seed"
