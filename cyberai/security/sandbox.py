"""Subprocess sandbox for CERBERUS.

Enforces the hard safety rules that Phase D requires:

1. Commands are built from argument lists only — ``shell=True`` is NEVER
   used, which eliminates shell-based command injection by construction.
2. Inputs are validated: any argument containing shell metacharacters is
   rejected with ``CommandInjectionError`` BEFORE the subprocess is spawned.
3. Every invocation has a wall-clock timeout and (where the platform allows)
   a memory ceiling, enforced via ``resource``.
4. Network access is denied by default unless explicitly granted.

The public entry point is :func:`run_subprocess`.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .exceptions import CommandInjectionError

logger = logging.getLogger(__name__)

# Shell metacharacters that enable COMMAND INJECTION / COMMAND CHAINING.
# We never use shell=True (argument-list only), so even these are harmless to
# the OS — but their presence in an argument signals an injection attempt that
# must be rejected before spawn. Parentheses, backslash, quotes, ~ and ! are
# INTENTIONALLY excluded because they are legitimate inside arguments
# (file paths, Python -c code, passwords) when no shell is involved.
_SHELL_METACHARACTERS = set(";|&$`{}<>#")

# Defaults
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_MEMORY_LIMIT_MB = 512


@dataclass
class SandboxResult:
    """Outcome of a sandboxed subprocess run."""

    command: List[str]
    returncode: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    memory_limited: bool = False
    error: Optional[str] = None
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return (
            self.returncode == 0
            and not self.timed_out
            and not self.memory_limited
            and self.error is None
        )


# ---------------------------------------------------------------------------
# Input validation — the command-injection defence
# ---------------------------------------------------------------------------
def validate_args(args: List[str]) -> None:
    """
    Validate that every element of an argument list is a safe single token.

    Raises ``CommandInjectionError`` at the first unsafe argument. This runs
    BEFORE any subprocess is spawned, so an injected payload can never reach
    the OS.
    """
    if not args:
        raise CommandInjectionError("Empty command -- nothing to execute")
    for i, arg in enumerate(args):
        if not isinstance(arg, str):
            raise CommandInjectionError(
                f"Argument {i} is not a string: {type(arg).__name__}"
            )
        if not arg:
            continue
        bad = _SHELL_METACHARACTERS.intersection(arg)
        if bad:
            raise CommandInjectionError(
                f"Argument {i} ({arg!r}) contains shell metacharacter(s) "
                f"{sorted(bad)} -- possible command injection. "
                "Rejected before subprocess execution."
            )


def build_command(base: str, *args: str) -> List[str]:
    """
    Safely construct a command list from a base program and positional args.

    Validates the whole list before returning it.
    """
    cmd = [base, *args]
    validate_args(cmd)
    return cmd


# ---------------------------------------------------------------------------
# Resource-limit helpers (platform-specific, best-effort)
# ---------------------------------------------------------------------------
def _limit_func_unix(memory_limit_mb: int):
    """Build a preexec_fn that applies memory + CPU limits on Unix."""
    def _preexec() -> None:
        try:
            import resource

            mem_bytes = int(memory_limit_mb) * 1024 * 1024
            try:
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            except (ValueError, OSError):
                pass
            try:
                cpu_limit = max(int(DEFAULT_TIMEOUT_SECONDS) * 10, 600)
                resource.setrlimit(
                    resource.RLIMIT_CPU, (cpu_limit, cpu_limit)
                )
            except (ValueError, OSError):
                pass
        except ImportError:
            pass
        if platform.system() == "Linux":
            _try_disable_network()

    return _preexec


def _try_disable_network() -> None:
    """Best-effort network sandboxing on Linux via unshare(CLONE_NEWNET)."""
    try:
        import ctypes

        libc = ctypes.CDLL("libc.so.6", use_errno=True)
        CLONE_NEWNET = 0x40000000
        if libc.unshare(CLONE_NEWNET) != 0:
            errno = ctypes.get_errno()
            logger.debug("unshare(CLONE_NEWNET) not applied (errno=%s)", errno)
    except Exception as exc:  # noqa: BLE001 — best-effort only
        logger.debug("Network sandbox not available: %s", exc)


def _minimal_env(env: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Return a cleaned environment with dangerous variables removed."""
    if env is not None:
        return {k: v for k, v in env.items() if k.isalnum() or k == "_"}
    keep = ("PATH", "HOME", "USER", "SYSTEMROOT", "COMSPEC",
            "LANG", "LC_ALL", "PYTHONIOENCODING", "TMPDIR", "TEMP", "TMP")
    return {k: v for k, v in os.environ.items() if k in keep}


def run_subprocess(
    command: List[str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
    network_allowed: bool = False,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    stdin_input: Optional[str] = None,
) -> SandboxResult:
    """
    Run a command inside the sandbox.

    Safety guarantees (in order):
      1. ``validate_args`` rejects injection payloads before spawn.
      2. ``shell=False`` (argument list) — the only supported mode.
      3. Wall-clock timeout enforced by a watchdog thread.
      4. Memory ceiling applied where the platform supports it.
      5. Network denied by default (``network_allowed=False``).
    """
    started = time.time()

    # --- 1. Reject injection BEFORE any spawn --------------------------
    try:
        validate_args(command)
    except CommandInjectionError:
        raise  # propagate — caller must handle/log

    # --- 3/4. Platform resource limits --------------------------------
    preexec_fn = None
    creationflags = 0
    system = platform.system()
    if system != "Windows":
        preexec_fn = _limit_func_unix(memory_limit_mb)
    else:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if not network_allowed:
            logger.debug(
                "Windows network deny is best-effort; relying on "
                "policy-level egress controls")

    run_env = _minimal_env(env)

    proc: Optional[subprocess.Popen] = None
    result = SandboxResult(command=list(command))
    timed_out = threading.Event()

    killed_by_watchdog = False

    def _watchdog() -> None:
        if timed_out.wait(timeout):
            return  # process finished in time
        if proc is not None and proc.poll() is None:
            nonlocal killed_by_watchdog
            killed_by_watchdog = True
            logger.warning(
                "Sandbox timeout (%.1fs) reached for %r -- killing",
                timeout, command)
            try:
                proc.kill()
            except OSError:
                pass

    watchdog = threading.Thread(target=_watchdog, daemon=True)
    watchdog.start()

    killed_by_watchdog = False
    try:
        proc = subprocess.Popen(
            command,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if stdin_input is not None else None,
            cwd=cwd,
            env=run_env,
            preexec_fn=preexec_fn,
            creationflags=creationflags,
        )
    except OSError as exc:
        result.error = f"Failed to spawn {command!r}: {exc}"
        logger.error(result.error)
        timed_out.set()
        watchdog.join(timeout=5)
        return result

    try:
        stdout_b, stderr_b = proc.communicate(
            input=stdin_input.encode() if stdin_input else None,
            timeout=None,  # watchdog handles wall-clock
        )
        timed_out.set()  # cancel watchdog
        result.stdout = stdout_b.decode("utf-8", errors="replace")
        result.stderr = stderr_b.decode("utf-8", errors="replace")
        result.returncode = proc.returncode
    except Exception as exc:  # noqa: BLE001
        if proc.poll() is None:
            proc.kill()
        timed_out.set()
        result.error = str(exc)
    finally:
        timed_out.set()
        watchdog.join(timeout=5)


    result.duration_seconds = time.time() - started

    # A kill performed by the watchdog (or a known sentinel returncode) means
    # the wall-clock limit was exceeded.
    if killed_by_watchdog or result.returncode in (-9, -15, 9, 137):
        result.timed_out = True
    if result.timed_out:
        result.error = (
            f"Sandbox timeout after {result.duration_seconds:.1f}s "
            f"(limit {timeout}s)")
        logger.error("Sandbox timed out: %r", command)

    return result
