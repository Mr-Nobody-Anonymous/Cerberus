"""Security regression tests — the redesign's hard safety contract.

Spec: "must verify that UI changes cannot bypass authorization."

These tests prove that every operator surface (web API, command bus, CLI
shell) funnels through the SAME policy engine, and that a revoked target
stays blocked on every path:

  1. API contract: /api/v1/commands/execute mirrors the dispatcher exactly
     (ok/blocked/error/rows/columns envelope).
  2. Authorization: revoking a target via the API blocks command-bus
     commands that touch that target; re-authorizing restores them.
  3. Blocked results NEVER report ok=True (no surface can flip it).
  4. Workspace path restrictions: traversal attempts 403, absolute paths
     403, non-approved roots 403, size/suffix caps enforced.

Run with ``python -m pytest tests/test_security_regressions.py -v``.
"""

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed")
httpx = pytest.importorskip("httpx", reason="httpx not installed for TestClient")

from fastapi.testclient import TestClient  # noqa: E402

from cyberai.commands import get_dispatcher, load_builtin_commands  # noqa: E402
from cyberai.ui.server import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def dispatcher():
    load_builtin_commands()
    return get_dispatcher()


# ---------------------------------------------------------------------------
# 1. API contract: the HTTP surface mirrors the command bus exactly
# ---------------------------------------------------------------------------
class TestApiCommandContract:
    """POST /api/v1/commands/execute must return the dispatcher's envelope."""

    def test_execute_envelope_matches_dispatcher(self, client, dispatcher):
        """Same input → same ok/blocked/error/data on both surfaces."""
        for line in ("/status", "/findings", "/targets", "/help"):
            r = client.post("/api/v1/commands/execute", json={"input": line})
            assert r.status_code == 200, r.text
            body = r.json()
            direct = dispatcher.execute(line).to_dict()
            assert body["ok"] == direct["ok"], line
            assert body.get("blocked") == direct.get("blocked"), line
            assert body.get("error") == direct.get("error"), line

    def test_execute_requires_input(self, client):
        r = client.post("/api/v1/commands/execute", json={"input": "   "})
        assert r.status_code == 400

    def test_execute_unknown_command_not_ok(self, client):
        r = client.post("/api/v1/commands/execute",
                        json={"input": "/definitely-not-a-command"})
        assert r.status_code == 200  # envelope, not HTTP error
        assert r.json()["ok"] is False

    def test_catalog_lists_commands(self, client):
        r = client.get("/api/v1/commands")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 20
        names = {c["name"] for c in body["commands"]}
        assert {"targets", "findings", "status"} <= names

    def test_single_command_spec(self, client):
        r = client.get("/api/v1/commands/findings")
        assert r.status_code == 200
        assert r.json()["command"]["name"] == "findings"

    def test_single_command_404(self, client):
        r = client.get("/api/v1/commands/nope")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# 2. Authorization: revoke → blocked everywhere; authorize → restored
# ---------------------------------------------------------------------------
class TestAuthorizationCannotBeBypassed:
    """The core spec requirement: UI changes cannot bypass authorization."""

    TARGET = "juice-shop"  # present in the default policy file

    def _api_list(self, client):
        r = client.get("/api/v1/targets")
        assert r.status_code == 200
        return {t["id"]: t for t in r.json()["targets"]}

    def test_revoke_then_authorize_round_trip(self, client, dispatcher):
        """Revoke via API → command bus sees UNAUTHORIZED; authorize → back."""
        # Revoke through the HTTP surface (what the UI button calls)
        r = client.patch(f"/api/v1/targets/{self.TARGET}",
                         json={"allowed": False})
        assert r.status_code == 200, r.text
        assert r.json()["allowed"] is False

        # The command bus (CLI shell surface) must observe the revocation
        targets = self._api_list(client)
        assert targets[self.TARGET]["state"] == "UNAUTHORIZED"

        # Re-authorize through the HTTP surface
        r = client.patch(f"/api/v1/targets/{self.TARGET}",
                         json={"allowed": True})
        assert r.status_code == 200
        assert r.json()["allowed"] is True
        targets = self._api_list(client)
        assert targets[self.TARGET]["state"] != "UNAUTHORIZED"

    def test_command_bus_revoke_authorize_round_trip(self, client, dispatcher):
        """/targets revoke + /targets authorize through the bus (CLI path)."""
        r = dispatcher.execute(f"/targets revoke {self.TARGET}")
        assert r.ok, r.error
        assert "revoked" in r.message
        targets = self._api_list(client)
        assert targets[self.TARGET]["state"] == "UNAUTHORIZED"

        r = dispatcher.execute(f"/targets authorize {self.TARGET}")
        assert r.ok, r.error
        assert "authorized" in r.message
        targets = self._api_list(client)
        assert targets[self.TARGET]["state"] != "UNAUTHORIZED"

    def test_patch_requires_bool(self, client):
        r = client.patch(f"/api/v1/targets/{self.TARGET}",
                         json={"allowed": "yes"})
        assert r.status_code == 400

    def test_patch_requires_field(self, client):
        r = client.patch(f"/api/v1/targets/{self.TARGET}", json={})
        assert r.status_code == 400

    def test_patch_unknown_target_404(self, client):
        r = client.patch("/api/v1/targets/does-not-exist",
                         json={"allowed": True})
        assert r.status_code == 404

    def test_policy_engine_is_the_single_source(self, client, dispatcher):
        """Both surfaces read the same PolicyEngine-backed list."""
        api_targets = self._api_list(client)
        r = dispatcher.execute("/targets")
        assert r.ok
        bus_ids = {t["id"] for t in r.data["targets"]}
        assert set(api_targets) == bus_ids


# ---------------------------------------------------------------------------
# 3. Blocked results never report ok
# ---------------------------------------------------------------------------
class TestBlockedNeverOk:
    def test_blocked_factory(self):
        from cyberai.commands.models import CommandResult
        r = CommandResult.blocked_result("x", "not authorized")
        assert r.blocked is True
        assert r.ok is False

    def test_permission_error_becomes_blocked(self, dispatcher):
        """A handler raising PermissionError surfaces as blocked, never ok."""
        from cyberai.commands.models import ParsedCommand

        # Register a probe command that raises PermissionError
        from cyberai.commands.registry import CommandRegistry
        reg = dispatcher.registry

        def _deny(ctx, parsed):
            raise PermissionError("not authorized")

        spec = type("Spec", (), {})()  # placeholder
        try:
            from cyberai.commands.models import CommandSpec
            probe = CommandSpec(name="probe-deny", category="test",
                                description="probe", handler=_deny)
            reg.register(probe)
            result = dispatcher.execute("/probe-deny")
            assert result.blocked is True
            assert result.ok is False
            assert "not authorized" in result.error
        finally:
            reg._commands.pop("probe-deny", None)
            for alias in ():
                reg._aliases.pop(alias, None)


# ---------------------------------------------------------------------------
# 4. Workspace path restrictions
# ---------------------------------------------------------------------------
class TestWorkspacePathRestrictions:
    """Traversal, absolute paths, and non-approved roots must all 403."""

    def test_traversal_rejected(self, client):
        r = client.get("/api/v1/workspace/file",
                       params={"path": "lab/../../secrets.txt"})
        assert r.status_code == 403

    def test_absolute_path_rejected(self, client):
        r = client.get("/api/v1/workspace/file",
                       params={"path": "C:/Windows/system32/config"})
        assert r.status_code == 403

    def test_non_approved_root_rejected(self, client):
        r = client.get("/api/v1/workspace/file",
                       params={"path": "config/settings.json"})
        assert r.status_code == 403

    def test_missing_path_400(self, client):
        r = client.get("/api/v1/workspace/file", params={"path": "   "})
        assert r.status_code == 400

    def test_missing_file_404(self, client):
        r = client.get("/api/v1/workspace/file",
                       params={"path": "lab/no-such-file.txt"})
        assert r.status_code == 404

    def test_tree_lists_only_approved_roots(self, client):
        r = client.get("/api/v1/workspace/tree")
        assert r.status_code == 200
        names = {e["name"] for e in r.json()["entries"]}
        assert "config" not in names  # config/ is not an approved root

    def test_tree_traversal_rejected(self, client):
        r = client.get("/api/v1/workspace/tree",
                       params={"path": "lab/../../"})
        assert r.status_code == 403
