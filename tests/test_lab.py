"""Tests for the Lab subsystem (cyberai.orchestrator.lab).

Covers LabManager start/stop/status with:
  - unknown / unauthorized targets rejected
  - already-running external services detected via port probe
  - graceful degradation to the mock service when Docker is unavailable
  - state persistence (lab/state/lab_state.json)
  - docker_available caching
"""

import json
import socket
from pathlib import Path
from unittest.mock import patch

import pytest

from cyberai.orchestrator.lab.lab_manager import (
    LabManager,
    _port_open,
)
from cyberai.orchestrator.policies.policy_engine import PolicyEngine


TARGETS_YAML = """\
targets:
- id: juice-shop
  host: 127.0.0.1
  port: {free1}
  protocol: http
  environment: authorized_lab
  allowed: true
  allowed_actions: [recon, scan]
  description: Juice Shop mock
- id: dvwa
  host: 127.0.0.1
  port: {free2}
  protocol: http
  environment: authorized_lab
  allowed: true
  allowed_actions: [recon]
  description: DVWA mock
- id: forbidden
  host: 127.0.0.1
  port: {free3}
  protocol: http
  environment: authorized_lab
  allowed: false
  allowed_actions: []
  description: Not authorized for active testing
"""


def _free_port() -> int:
    """Grab an ephemeral free TCP port (left closed after the probe)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def lab_env(tmp_path, monkeypatch):
    """Isolated targets file + state file for each test."""
    p1, p2, p3 = _free_port(), _free_port(), _free_port()
    targets = tmp_path / "targets.yaml"
    targets.write_text(TARGETS_YAML.format(free1=p1, free2=p2, free3=p3),
                       encoding="utf-8")
    state_file = tmp_path / "state" / "lab_state.json"
    monkeypatch.setattr("cyberai.orchestrator.lab.lab_manager.STATE_FILE",
                        state_file)
    policy = PolicyEngine(targets_path=targets)
    manager = LabManager(policy_engine=policy)
    return manager, state_file, {"juice-shop": p1, "dvwa": p2, "forbidden": p3}


class TestPortProbe:
    def test_port_open_false_for_closed(self):
        port = _free_port()
        assert _port_open("127.0.0.1", port, timeout=0.2) is False

    def test_port_open_true_for_listener(self):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        try:
            assert _port_open("127.0.0.1", port, timeout=0.5) is True
        finally:
            server.close()


class TestStartTarget:
    async def test_unknown_target_errors(self, lab_env):
        manager, _, _ = lab_env
        result = await manager.start_target("ghost")
        assert result["status"] == "ERROR"
        assert "Unknown target" in result["error"]

    async def test_unauthorized_target_denied(self, lab_env):
        manager, _, _ = lab_env
        result = await manager.start_target("forbidden")
        assert result["status"] == "DENIED"
        assert "not authorized" in result["error"]

    async def test_already_running_external(self, lab_env):
        manager, state_file, ports = lab_env
        server = socket.socket()
        server.bind(("127.0.0.1", ports["juice-shop"]))
        server.listen(1)
        try:
            result = await manager.start_target("juice-shop")
            assert result["status"] == "RUNNING"
            assert result["mode"] == "external"
            state = json.loads(state_file.read_text())
            assert state["juice-shop"]["mode"] == "external"
        finally:
            server.close()

    async def test_mock_fallback_when_no_docker(self, lab_env):
        """Docker unavailable → graceful degradation to the mock service."""
        manager, state_file, ports = lab_env
        with patch.object(LabManager, "docker_available", return_value=False):
            result = await manager.start_target("juice-shop")
        assert result["status"] == "RUNNING", result
        assert result["mode"] == "mock"
        assert result["port"] == ports["juice-shop"]
        state = json.loads(state_file.read_text())
        assert state["juice-shop"]["mode"] == "mock"
        assert state["juice-shop"]["pid"]
        # Clean up the spawned mock process.
        await manager.stop_target("juice-shop")

    async def test_mock_fallback_stops_cleanly(self, lab_env):
        manager, _, _ = lab_env
        with patch.object(LabManager, "docker_available", return_value=False):
            await manager.start_target("dvwa")
            result = await manager.stop_target("dvwa")
        assert result["status"] == "STOPPED"
        assert result["mode"] == "mock"

    async def test_docker_failure_falls_back_to_mock(self, lab_env):
        """Docker present but docker run fails → mock fallback."""
        manager, _, _ = lab_env
        from asyncio import create_subprocess_exec as _real_exec

        async def fake_exec(*args, **kwargs):
            if args and args[0] == "docker":
                raise OSError("docker daemon down")
            return await _real_exec(*args, **kwargs)

        with patch.object(LabManager, "docker_available", return_value=True), \
             patch("cyberai.orchestrator.lab.lab_manager.subprocess.run"), \
             patch("cyberai.orchestrator.lab.lab_manager.asyncio.create_subprocess_exec",
                   side_effect=fake_exec):
            result = await manager.start_target("juice-shop")
        assert result["status"] == "RUNNING", result
        assert result["mode"] == "mock"
        await manager.stop_target("juice-shop")


class TestStopTarget:
    async def test_stop_unknown_target(self, lab_env):
        manager, _, _ = lab_env
        result = await manager.stop_target("ghost")
        assert result["status"] == "ERROR"

    async def test_stop_not_running(self, lab_env):
        manager, _, _ = lab_env
        result = await manager.stop_target("juice-shop")
        assert result["status"] == "NOT_RUNNING"

    async def test_stop_external_removes_state(self, lab_env):
        manager, state_file, ports = lab_env
        server = socket.socket()
        server.bind(("127.0.0.1", ports["juice-shop"]))
        server.listen(1)
        try:
            await manager.start_target("juice-shop")
            assert "juice-shop" in json.loads(state_file.read_text())
        finally:
            server.close()
        result = await manager.stop_target("juice-shop")
        assert result["status"] == "STOPPED"
        assert "juice-shop" not in json.loads(state_file.read_text())


class TestStatusAll:
    def test_status_lists_all_targets(self, lab_env):
        manager, _, ports = lab_env
        statuses = manager.status_all()
        by_id = {s["id"]: s for s in statuses}
        assert set(by_id) == {"juice-shop", "dvwa", "forbidden"}
        assert by_id["forbidden"]["authorized"] is False
        assert by_id["juice-shop"]["authorized"] is True
        assert by_id["juice-shop"]["port"] == ports["juice-shop"]

    def test_status_reachable_flag(self, lab_env):
        manager, _, ports = lab_env
        server = socket.socket()
        server.bind(("127.0.0.1", ports["dvwa"]))
        server.listen(1)
        try:
            statuses = {s["id"]: s for s in manager.status_all()}
            assert statuses["dvwa"]["reachable"] is True
            assert statuses["juice-shop"]["reachable"] is False
        finally:
            server.close()

    def test_status_mode_stopped_when_unreachable(self, lab_env):
        manager, _, _ = lab_env
        statuses = {s["id"]: s for s in manager.status_all()}
        assert statuses["juice-shop"]["mode"] == "stopped"


class TestDockerAvailability:
    def test_docker_checked_cached(self, lab_env):
        manager, _, _ = lab_env
        with patch("cyberai.orchestrator.lab.lab_manager.shutil.which",
                   return_value=None):
            assert manager.docker_available() is False
        # Second call uses the cache even though `which` would now succeed.
        assert manager.docker_available() is False
        assert manager._docker_checked is False

    def test_docker_unavailable_when_no_cli(self, lab_env):
        manager, _, _ = lab_env
        manager._docker_checked = None
        with patch("cyberai.orchestrator.lab.lab_manager.shutil.which",
                   return_value=None):
            assert manager.docker_available() is False

    def test_docker_available_when_daemon_up(self, lab_env):
        manager, _, _ = lab_env
        manager._docker_checked = None
        fake_proc = type("P", (), {"returncode": 0, "stdout": "24.0", "stderr": ""})()
        with patch("cyberai.orchestrator.lab.lab_manager.shutil.which",
                   return_value="/usr/bin/docker"), \
             patch("cyberai.orchestrator.lab.lab_manager.subprocess.run",
                   return_value=fake_proc):
            assert manager.docker_available() is True
