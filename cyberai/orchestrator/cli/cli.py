"""
Cyber AI Orchestrator — CLI entry point.

Provides a single `cyber-ai` (or `cyberai`) command group with subcommands:
  - task       Run an autonomous assessment (supports --dry-run, --simulate)
  - simulate   Full end-to-end simulation without external dependencies
  - assess     Legacy alias for task (with --dry-run, --simulate)
  - status     Show platform health
  - models     List model registry
  - adapters   List adapter health
  - tools      List registered tools
  - agents     List agent types
  - findings   List findings from memory
  - memory     Search experience memory
  - lab        Lab target management
  - session    Session management
  - doctor     Health check
  - evolve     Run one generation of strategy evolution
  - ui         Launch the unified Command Deck web UI

No sys.path hacks — the package is importable because the workspace root
is on PYTHONPATH (or the package is installed).
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import click

from cyberai.config import WORKSPACE_ROOT
from cyberai.orchestrator import Orchestrator
from cyberai.orchestrator import ToolRegistry
from cyberai.orchestrator import MemoryManager
from cyberai.orchestrator import PolicyEngine
from cyberai.orchestrator.adapters.adapter_manager import AdapterManager


def _get_workspace_root() -> Path:
    return WORKSPACE_ROOT


@click.group(name="cyber-ai")
@click.version_option("2.0.0")
def cli():
    """Cyber AI — integrated local AI security research orchestrator."""
    pass


# ---------------------------------------------------------------------------
# task / assess — the main autonomous entry point
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--objective", "-o", "objective", required=True,
              help="Natural language objective, e.g. 'Analyze my authorized lab target'")
@click.option("--target", "-t", "target_id", default=None,
              help="Authorized lab target ID (see 'lab list')")
@click.option("--dry-run", "dry_run", is_flag=True, default=False,
              help="Show planned agents, tools, models, and actions without executing")
@click.option("--simulate", "simulate", is_flag=True, default=False,
              help="Run in simulation mode with deterministic mock results (no Docker/Ollama/API needed)")
@click.option("--scope", default="authorized_lab", help="Task scope boundary")
@click.pass_context
def task(ctx, objective, target, dry_run, simulate, scope):
    """Run an autonomous assessment.

    The orchestrator determines what to do, which agent/tool/model to use,
    executes in the authorized lab, verifies results, and learns.

    Examples:
      cyber-ai task -o "Analyze my authorized lab target" -t lab-web-01
      cyber-ai task -o "Analyze my authorized lab target" --dry-run
      cyber-ai task -o "Analyze my authorized lab target" --simulate
    """
    asyncio.run(_run_task(objective, target, dry_run, simulate, scope))


@cli.command()
@click.option("--objective", "-o", "objective", required=True)
@click.option("--target", "-t", "target_id", default=None)
@click.option("--dry-run", "dry_run", is_flag=True, default=False)
@click.option("--simulate", "simulate", is_flag=True, default=False)
def assess(objective, target, dry_run, simulate):
    """Legacy alias for 'task'."""
    asyncio.run(_run_task(objective, target, dry_run, simulate))


async def _run_task(objective, target_id, dry_run, simulate, scope="authorized_lab"):
    """Async implementation of the task/assess command."""
    from cyberai import CyberAIOrchestrator

    orch = CyberAIOrchestrator(
        simulate=simulate,
        dry_run=dry_run,
    )
    try:
        result = await orch.run(objective, target_id=target_id, scope=scope)
        click.echo(json.dumps(result, indent=2, default=str))
    except PermissionError as e:
        click.echo(f"[ERROR] Authorization required: {e}", err=True)
        sys.exit(1)
    finally:
        orch.close()


# ---------------------------------------------------------------------------
# simulate — full end-to-end simulation
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("objective")
def simulate(objective):
    """Run a complete end-to-end simulation without any external dependencies.

    Uses deterministic mock agents, mock tools, and local-only model fallback.
    Demonstrates the full orchestration loop: PLAN → MEMORY → ROUTING →
    AGENT → TOOL → RESULT → VERIFY → MEMORY → EVOLUTION → REPORT.

    Example:
      cyber-ai simulate "Analyze authorized lab target"
    """
    asyncio.run(_run_simulate(objective))


async def _run_simulate(objective):
    """Async implementation of the simulate command."""
    from cyberai import CyberAIOrchestrator

    orch = CyberAIOrchestrator(simulate=True, local_only=True)
    try:
        result = await orch.run(objective, target_id="lab-web-01")
        click.echo(json.dumps(result, indent=2, default=str))
    finally:
        orch.close()


# ---------------------------------------------------------------------------
# status — platform health
# ---------------------------------------------------------------------------
@cli.command()
def status():
    """Show full platform status."""
    from cyberai import CyberAIOrchestrator
    orch = CyberAIOrchestrator()
    try:
        click.echo(json.dumps(orch.get_status(), indent=2, default=str))
    finally:
        orch.close()


# ---------------------------------------------------------------------------
# models — model registry
# ---------------------------------------------------------------------------
@cli.command()
def models():
    """List available models and their health."""
    gw_status = asyncio.run(_model_status())
    click.echo(json.dumps(gw_status, indent=2, default=str))


async def _model_status():
    from cyberai.llm_gateway import LLMGateway
    gw = LLMGateway()
    health = await gw.health_check()
    models_list = gw.list_registry()
    return {
        "health": health,
        "models": models_list,
    }


# ---------------------------------------------------------------------------
# adapters — adapter health
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--all", "check_all", is_flag=True, default=False,
              help="Health-check all 17 adapters (takes ~30s)")
def adapters(check_all):
    """List available adapters and their health."""
    manager = AdapterManager()
    discovered = manager.discover()
    click.echo(f"Discovered {len(discovered)} adapters with Python wrappers:\n")
    for name in discovered:
        info = manager._adapter_info[name]
        click.echo(f"  {name:20s}  integration={info['integration']:14s}  "
                   f"docker={info['docker']}")

    if check_all:
        click.echo("\nRunning health checks (this may take a moment):\n")
        results = asyncio.run(_adapter_health_check(manager))
        click.echo(json.dumps(results, indent=2, default=str))


async def _adapter_health_check(manager):
    return await manager.health_check_all()


# ---------------------------------------------------------------------------
# tools — tool registry
# ---------------------------------------------------------------------------
@cli.command()
def tools():
    """List registered tools."""
    reg = ToolRegistry()
    for name, t in reg.to_dict()["tools"].items():
        click.echo(f"  {name}: type={t['type']}, status={t['status']}")


# ---------------------------------------------------------------------------
# agents — agent types
# ---------------------------------------------------------------------------
@cli.command()
def agents():
    """List available agent types."""
    for name, desc in [
        ("planner", "Creates attack plans via planner.py agent"),
        ("researcher", "Gathers information via researcher.py agent"),
        ("recon", "Performs reconnaissance via recon.py agent"),
        ("analyst", "Analyzes findings via analyst.py agent"),
        ("coder", "Writes code/exploits via coder.py agent"),
        ("verifier", "Verifies findings via verifier.py agent"),
        ("reporter", "Generates reports via reporter.py agent"),
    ]:
        click.echo(f"  {name}: {desc}")


# ---------------------------------------------------------------------------
# evolve — run evolution for a task type
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--task-type", default="assessment")
@click.option("--generations", default=1, type=int)
@click.option("--population", default=3, type=int)
def evolve(task_type, generations, population):
    """Run the evolutionary strategy engine."""
    from cyberai.evolution.engine import EvolutionEngine
    engine = EvolutionEngine(simulate=True)
    for gen in range(generations):
        result = asyncio.run(engine.evolve_generation(
            task_type=task_type,
            task_context={},
            num_strategies=population,
        ))
        click.echo(f"\nGeneration {gen + 1}:")
        for s in result.get("results", []):
            click.echo(f"  {s.get('strategy_id', '?')}: fitness={s.get('fitness', 0):.3f}")


# ---------------------------------------------------------------------------
# Memory / findings / session (read-only)
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--status", default=None)
def findings(status):
    """List findings from memory."""
    mm = MemoryManager()
    for f in mm.get_findings(status=status):
        click.echo(f"  [{f.get('status', '')}] {f.get('observation', '')[:80]}")
    mm.close()


@cli.command()
@click.argument("query", required=False)
@click.option("--limit", default=10)
def memory(query, limit):
    """Search experience memory."""
    mm = MemoryManager()
    if not query:
        click.echo("Usage: cyber-ai memory '<query>' [--limit N]")
        mm.close()
        return
    for r in mm.search_experiences(query, limit=limit):
        click.echo(f"  [{r.get('result', '')}] {r.get('observation', '')[:80]}")
    mm.close()


@cli.group()
def lab():
    """Lab target management commands."""
    pass


@lab.command(name="list")
def lab_list():
    """List lab targets."""
    pe = PolicyEngine()
    targets = pe.list_targets()
    if not targets:
        click.echo("No registered targets. Edit lab/targets/targets.yaml")
        pe.close()
        return
    for t in targets:
        st = "AUTHORIZED" if t.get("allowed") else "NOT AUTHORIZED"
        click.echo(f"  {t['id']}: {st}")
    pe.close()


@lab.command(name="register")
@click.argument("target_id")
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=0, type=int)
@click.option("--description", default="")
def lab_register(target_id, host, port, description):
    """Register an authorized lab target."""
    pe = PolicyEngine()
    targets = pe.list_targets()
    # Check if already exists
    existing = [t for t in targets if t.get("id") == target_id]
    if existing:
        click.echo(f"Target '{target_id}' already registered. Use YAML to edit.")
    else:
        pe.register_target({
            "id": target_id,
            "environment": "authorized_lab",
            "allowed": True,
            "host": host,
            "port": port,
            "description": description,
            "allowed_actions": ["recon", "scan", "analysis", "verification"],
        })
        click.echo(f"Registered target '{target_id}'")
    pe.close()


@lab.command(name="start")
@click.argument("target_id")
def lab_start(target_id):
    """Start a lab target (requires Docker)."""
    click.echo(f"[NOT YET IMPLEMENTED] Start target: {target_id}")
    click.echo("Lab environment requires Docker (not installed on this system).")


@cli.group()
def session():
    """Session management commands."""
    pass


@session.command(name="list")
def session_list():
    """List all sessions."""
    mm = MemoryManager()
    for s in mm.list_sessions():
        click.echo(f"  {s['id']}: target={s.get('target_id', '')}, status={s.get('status', '')}")
    mm.close()


@session.command(name="show")
@click.argument("session_id")
def session_show(session_id):
    """Show session details."""
    mm = MemoryManager()
    s = mm.get_session(session_id)
    if s:
        click.echo(json.dumps(s, indent=2, default=str))
    else:
        click.echo(f"Session not found: {session_id}")
    mm.close()


# ---------------------------------------------------------------------------
# ui — one-command launch of the unified command deck
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--port", default=8710, help="UI port (default 8710)")
@click.option("--no-browser", is_flag=True, default=False, help="Do not auto-open the browser")
def ui(port, no_browser):
    """Launch the unified CERBERUS Command Deck web UI (one AI cockpit)."""
    try:
        import uvicorn
        from cyberai.ui.server import app
    except ImportError as e:
        click.echo(f"[ERROR] UI dependencies missing: {e}")
        click.echo("Install with: pip install fastapi uvicorn")
        return

    url = f"http://127.0.0.1:{port}"
    click.echo(f"[CERBERUS] Command Deck listening on {url}")
    if not no_browser:
        import threading
        import webbrowser
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


# ---------------------------------------------------------------------------
# doctor — health check
# ---------------------------------------------------------------------------
@cli.command()
def doctor():
    """Run comprehensive health checks."""
    from cyberai.orchestrator.cli.doctor import run_health_check
    for component, status_val, msg in run_health_check():
        icon = {"ok": "[OK]", "warn": "[WARN]", "error": "[ERROR]", "info": "[INFO]"}
        click.echo(f"  {icon.get(status_val, '[?]')} {component}: {msg}")


if __name__ == "__main__":
    cli()
