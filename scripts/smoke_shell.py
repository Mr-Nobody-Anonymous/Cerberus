"""Scripted smoke test for the interactive console (non-TTY safe).

Feeds a fixed sequence of commands to run_console by monkeypatching the
plain-input fallback, then prints what the console rendered.
"""
import builtins
import sys

import cyberai.orchestrator.cli.shell.interactive as mod


def main():
    lines = ["/help", "/targets", "/findings", "/memory sql injection",
             "/status", "/quit"]
    it = iter(lines)

    def fake_input(prompt=""):
        try:
            line = next(it)
        except StopIteration:
            raise EOFError
        print(f"cerberus > {line}")
        return line

    # Force the plain-input fallback path (deterministic, no ptk needed)
    real_import = builtins.__import__

    def _no_ptk(name, *a, **k):
        if name.startswith("prompt_toolkit"):
            raise ImportError("disabled for smoke test")
        return real_import(name, *a, **k)

    builtins.__import__ = _no_ptk
    real_input = builtins.input
    builtins.input = fake_input
    try:
        mod.run_console(simulate=True, verbose=False)
    finally:
        builtins.input = real_input
        builtins.__import__ = real_import
    print("SMOKE-OK")


if __name__ == "__main__":
    main()
