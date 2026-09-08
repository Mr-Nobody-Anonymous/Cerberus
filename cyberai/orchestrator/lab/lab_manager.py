"""
Lab Environment Manager for the Cyber AI Orchestrator.

Manages the lifecycle of authorized lab targets:
  - start   — launch a target (Docker container when available, otherwise
              a local mock service so the platform stays fully usable)
  - stop    — stop a running target
  - status  — report which targets are up and how they were started

Docker support is optional: when the Docker CLI is unavailable or the
daemon is down, the manager degrades gracefully to a lightweight mock
HTTP server ("mock mode") so demos, tests, and the UI keep working.
"""

import asyncio
import json
import logging
import shutil
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.config import WORKSPACE_ROOT
from cyberai.orchestrator import PolicyEngine

logger = logging.getLogger(__name__)

STATE_FILE = WORKSPACE_ROOT / "lab" / "state" / "lab_state.json"
CONTAINER_PREFIX = "cerberus-lab-"


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check whether a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class LabManager:
    """Start/stop/status for authorized lab targets."""

    def __init__(self, policy_engine: Optional[PolicyEngine] = None):
        self.policy_engine = policy_engine or PolicyEngine()
        self._docker_checked: Optional[bool] = None

    # ------------------------------------------------------------------
    # Docker availability
    # ------------------------------------------------------------------
    def docker_available(self) -> bool:
        """True if the docker CLI exists and the daemon responds."""
        if self._docker_checked is not None:
            return self._docker_checked
        if shutil.which("docker") is None:
            self._docker_checked = False
            return False
        try:
            proc = subprocess.run(
                ["docker", "info", "--format", "{{.ServerVersion}}"],
                capture_output=True, text=True, timeout=10,
            )
            self._docker_checked = proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            self._docker_checked = False
        return self._docker_checked

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------
    def _load_state(self) -> Dict[str, Dict[str, Any]]:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_state(self, state: Dict[str, Dict[str, Any]]) -> None:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _container_name(self, target_id: str) -> str:
        return f"{CONTAINER_PREFIX}{target_id}"

    # ------------------------------------------------------------------
    # start
    # ------------------------------------------------------------------
    async def start_target(self, target_id: str, force: bool = False) -> Dict[str, Any]:
        """Start an authorized lab target.

        Strategy:
          1. If the target's port is already accepting connections → RUNNING.
          2. If Docker is available and the target declares docker_image →
             launch a container.
          3. Otherwise → start a local mock HTTP service on the target port
             (graceful degradation, keeps the platform demo-able offline).
        """
        target = self.policy_engine.get_target(target_id)
        if not target:
            return {"status": "ERROR", "error": f"Unknown target: {target_id}"}
        if not target.get("allowed"):
            return {"status": "DENIED",
                    "error": f"Target '{target_id}' is not authorized for active testing"}

        host = target.get("host", "127.0.0.1")
        port = int(target.get("port") or 0)
        state = self._load_state()

        if not force and _port_open(host, port):
            state[target_id] = {
                "mode": state.get(target_id, {}).get("mode", "external"),
                "host": host, "port": port,
                "started_at": state.get(target_id, {}).get("started_at", _now()),
            }
            self._save_state(state)
            return {"status": "RUNNING", "mode": "external", "host": host,
                    "port": port, "message": f"Port {host}:{port} already accepting connections"}

        meta = target.get("metadata") or {}
        image = meta.get("docker_image")

        if self.docker_available() and image:
            result = await self._start_docker(target_id, target, image)
            if result.get("status") in ("RUNNING", "OK"):
                state[target_id] = {"mode": "docker", "host": host, "port": port,
                                    "container": result.get("container"),
                                    "started_at": _now()}
                self._save_state(state)
                return result
            if not force:
                return result

        # Graceful degradation: mock service
        result = await self._start_mock(target_id, target)
        if result.get("status") == "RUNNING":
            state[target_id] = {"mode": "mock", "host": host, "port": port,
                                "pid": result.get("pid"),
                                "started_at": _now()}
            self._save_state(state)
        return result

    async def _start_docker(self, target_id: str, target: Dict[str, Any],
                            image: str) -> Dict[str, Any]:
        name = self._container_name(target_id)
        host = target.get("host", "127.0.0.1")
        port = int(target.get("port") or 0)
        meta = target.get("metadata") or {}
        docker_port = meta.get("docker_port") or f"{port}:{port}"

        # Remove stale container with the same name
        subprocess.run(["docker", "rm", "-f", name],
                       capture_output=True, timeout=30)

        cmd = ["docker", "run", "-d", "--name", name,
               "--network", "bridge", "-p", docker_port, image]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
        except (OSError, asyncio.TimeoutError) as e:
            return {"status": "ERROR", "error": f"docker run failed: {e}"}

        if proc.returncode != 0:
            err = (stderr or b"").decode(errors="ignore")[:300]
            return {"status": "ERROR", "error": f"docker run failed: {err}"}

        container = (stdout or b"").decode(errors="ignore").strip()[:12]
        # Wait for the port to come up (max ~30s)
        for _ in range(30):
            if _port_open(host, port):
                return {"status": "RUNNING", "mode": "docker", "host": host,
                        "port": port, "container": container,
                        "message": f"Container {name} up ({image})"}
            await asyncio.sleep(1.0)
        return {"status": "STARTING", "mode": "docker", "host": host, "port": port,
                "container": container,
                "message": f"Container {name} launched; port not yet open (image may still be pulling)"}

    async def _start_mock(self, target_id: str, target: Dict[str, Any]) -> Dict[str, Any]:
        """Start a lightweight mock HTTP service imitating the target."""
        host = target.get("host", "127.0.0.1")
        port = int(target.get("port") or 0)
        if port == 0:
            return {"status": "ERROR", "error": "Target has no port; cannot start mock"}

        script = WORKSPACE_ROOT / "lab" / "docker" / "mock_target.py"
        if not script.exists():
            return {"status": "ERROR",
                    "error": f"mock target script missing: {script}"}

        try:
            proc = await asyncio.create_subprocess_exec(
                "python", str(script), "--host", host, "--port", str(port),
                "--name", target_id,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError as e:
            return {"status": "ERROR", "error": f"cannot launch mock: {e}"}

        for _ in range(20):
            if _port_open(host, port):
                return {"status": "RUNNING", "mode": "mock", "host": host,
                        "port": port, "pid": proc.pid,
                        "message": f"Mock service for '{target_id}' on {host}:{port} (Docker unavailable)"}
            await asyncio.sleep(0.25)

        return {"status": "ERROR", "mode": "mock",
                "error": f"mock service did not open {host}:{port} within 5s"}

    # ------------------------------------------------------------------
    # stop
    # ------------------------------------------------------------------
    async def stop_target(self, target_id: str) -> Dict[str, Any]:
        state = self._load_state()
        info = state.get(target_id)
        target = self.policy_engine.get_target(target_id)

        if info and info.get("mode") == "docker" and self.docker_available():
            name = self._container_name(target_id)
            subprocess.run(["docker", "rm", "-f", name],
                           capture_output=True, timeout=60)
            state.pop(target_id, None)
            self._save_state(state)
            return {"status": "STOPPED", "mode": "docker",
                    "message": f"Container {name} removed"}

        if info and info.get("mode") == "mock" and info.get("pid"):
            killed = _kill_pid(info["pid"])
            state.pop(target_id, None)
            self._save_state(state)
            return {"status": "STOPPED", "mode": "mock", "killed": killed,
                    "message": f"Mock service (pid {info['pid']}) stopped"}

        if info:
            state.pop(target_id, None)
            self._save_state(state)
            return {"status": "STOPPED", "mode": info.get("mode", "?"),
                    "message": "Removed from state (service was not started by us)"}

        if target:
            return {"status": "NOT_RUNNING",
                    "message": f"Target '{target_id}' is not currently started"}
        return {"status": "ERROR", "error": f"Unknown target: {target_id}"}

    # ------------------------------------------------------------------
    # status
    # ------------------------------------------------------------------
    def status_all(self) -> List[Dict[str, Any]]:
        state = self._load_state()
        out = []
        for t in self.policy_engine.list_targets():
            tid = t.get("id")
            host = t.get("host", "127.0.0.1")
            port = int(t.get("port") or 0)
            info = state.get(tid, {})
            reachable = _port_open(host, port) if port else False
            mode = info.get("mode", "external" if reachable else "stopped")
            out.append({
                "id": tid,
                "host": host,
                "port": port,
                "authorized": bool(t.get("allowed")),
                "reachable": reachable,
                "mode": mode if reachable else ("stopped" if not info else mode),
                "docker_image": (t.get("metadata") or {}).get("docker_image"),
                "started_at": info.get("started_at"),
                "description": t.get("description", ""),
            })
        return out

    def close(self) -> None:
        self.policy_engine.close()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def _kill_pid(pid: int) -> bool:
    """Best-effort kill of a mock service PID (Windows + POSIX)."""
    try:
        if shutil.which("taskkill") is not None:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, timeout=15)
        else:
            import signal
            import os
            os.kill(pid, signal.SIGTERM)
        return True
    except Exception:
        return False
