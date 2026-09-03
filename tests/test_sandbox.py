"""Phase D — sandbox safety tests.

Verifies the hard safety guarantees:
- command-injection payloads are rejected BEFORE subprocess execution
- argument-list-only enforcement (no shell=True)
- wall-clock timeout enforcement
- host environment is not leaked to the child
"""

import os
import sys
import tempfile

import pytest

from cyberai.security.sandbox import (
    CommandInjectionError,
    build_command,
    run_subprocess,
    validate_args,
)


def _run_script(script: str, *, timeout=30, args=None):
    """Write a Python script to a temp file and run it in the sandbox.
    This mirrors how adapters actually invoke real tool scripts (not
    `-c` one-liners), so the strict validator applies realistically."""
    if args is None:
        args = []
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(script)
        path = fh.name
    try:
        return run_subprocess([sys.executable, path, *args], timeout=timeout)
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Command-injection rejection (the P0 Phase D success criterion)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "args",
    [
        ["python", "-c", "print(1); rm -rf /"],
        ["ls", "|", "cat /etc/passwd"],
        ["echo", "$(whoami)"],
        ["echo", "`id`"],
        ["cmd", "&&", "malicious"],
        ["cmd", "foo&bar"],
        ["cmd", "foo>bar"],
        ["cmd", "foo<bar"],
        ["cmd", "hello#world"],
        ["cmd", "a;rm -rf /"],
    ],
)
def test_injection_payloads_rejected(args):
    """Every shell-metacharacter payload must raise CommandInjectionError
    BEFORE any subprocess is spawned."""
    with pytest.raises(CommandInjectionError):
        validate_args(args)


def test_safe_arguments_pass():
    """Plain arguments without shell metacharacters must be accepted."""
    validate_args(["python", "-c", "print(1)"])
    validate_args(["nmap", "-sV", "127.0.0.1"])
    validate_args(["python", "drakben.py", "--help"])
    validate_args(["echo", "hello world"])
    validate_args(["guardian", "scan", "--target", "127.0.0.1"])


def test_empty_command_rejected():
    with pytest.raises(CommandInjectionError):
        validate_args([])


def test_non_string_arg_rejected():
    with pytest.raises(CommandInjectionError):
        validate_args(["python", 123])


def test_build_command_rejects_injection():
    with pytest.raises(CommandInjectionError):
        build_command("python", "-c", "print(1); os.system('evil')")


# ---------------------------------------------------------------------------
# Sandbox execution behaviour
# ---------------------------------------------------------------------------
def test_sandbox_runs_safe_command():
    """A benign command runs and returns success with captured stdout."""
    result = run_subprocess(
        [sys.executable, "-c", "print('hello from sandbox')"],
        timeout=30,
    )
    assert result.success is True
    assert "hello from sandbox" in result.stdout
    assert result.returncode == 0


def test_sandbox_rejects_injection_before_spawn():
    """run_subprocess must raise CommandInjectionError for a payload and
    never spawn a process. This is the headline Phase D test."""
    with pytest.raises(CommandInjectionError):
        run_subprocess(
            [sys.executable, "-c", "print(1); import os; os.system('echo pwned')"],
            timeout=10,
        )


def test_sandbox_never_uses_shell():
    """Verify shell=False: an argument containing a space is kept as a SINGLE
    argv entry (a shell would have split it). Demonstrates no shell parsing."""
    script = "import sys\nprint(len(sys.argv))\n"
    # One argument that contains a space.
    result = _run_script(script, args=["foo bar"], timeout=10)
    assert result.success is True
    # sys.argv == [script_path, "foo bar"] == 2 entries; the space was NOT
    # treated as a separator because no shell parsed the argument list.
    assert result.stdout.strip() == "2"


def test_sandbox_enforces_timeout():
    """A command that sleeps longer than the timeout must be killed and
    reported as timed_out, never hanging the test."""
    script = "import time\ntime.sleep(60)\n"
    result = _run_script(script, timeout=3)
    assert result.timed_out is True
    assert result.success is False
    assert result.duration_seconds < 10  # killed well before 60s


def test_sandbox_captures_stderr():
    script = "import sys\nsys.stderr.write('boom')\n"
    result = _run_script(script, timeout=10)
    assert "boom" in result.stderr


def test_sandbox_nonzero_exit_reported():
    script = "import sys\nsys.exit(3)\n"
    result = _run_script(script, timeout=10)
    assert result.returncode == 3
    assert result.success is False


def test_sandbox_does_not_leak_host_env():
    """Dangerous env vars must be stripped from the subprocess environment."""
    os.environ["SECRET_API_KEY"] = "SHOULD-NOT-REACH-CHILD"
    try:
        script = "import os\nprint(os.environ.get('SECRET_API_KEY', ''))\n"
        result = _run_script(script, timeout=10)
        assert "SHOULD-NOT-REACH-CHILD" not in result.stdout
    finally:
        os.environ.pop("SECRET_API_KEY", None)
