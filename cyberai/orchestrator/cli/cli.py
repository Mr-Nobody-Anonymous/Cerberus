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
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from cyberai.config import WORKSPACE_ROOT
from cyberai.orchestrator import Orchestrator
from cyberai.orchestrator import ToolRegistry
from cyberai.orchestrator import MemoryManager
from cyberai.orchestrator import PolicyEngine
from cyberai.orchestrator.adapters.adapter_manager import AdapterManager


def _get_workspace_root() -> Path:
    return WORKSPACE_ROOT


# ---------------------------------------------------------------------------
# Output modes (spec §14) — --json / --yaml / --table / --quiet / --verbose
#                   / --debug / --no-color
# ---------------------------------------------------------------------------
_OUTPUT_MODE: Dict[str, bool] = {
    "json": False, "yaml": False, "table": False, "quiet": False,
    "verbose": False, "debug": False, "no_color": False,
}


def _emit_json(payload: Any) -> None:
    """Print payload as JSON (used when --json is set)."""
    click.echo(json.dumps(payload, indent=2, default=str))


def _emit_table(rows: List[Dict[str, Any]], columns: List[str],
                 headers: Optional[List[str]] = None) -> None:
    """Print rows as a human table; suppressed entirely in --quiet mode."""
    if _OUTPUT_MODE["quiet"]:
        return
    headers = headers or columns
    for row in rows:
        click.echo("  " + "  ".join(str(row.get(c, "")) for c in columns))


def _emit_info(msg: str) -> None:
    """Human-mode informational line; hidden in --quiet, shown in --verbose."""
    if _OUTPUT_MODE["quiet"]:
        return
    click.echo(msg)


@click.group(name="cyber-ai")
@click.version_option("2.0.0")
@click.option("--json", "as_json", is_flag=True, default=False,
              help="Output machine-readable JSON (spec §14 output mode).")
@click.option("--yaml", "as_yaml", is_flag=True, default=False,
              help="Output machine-readable YAML (spec §14 output mode).")
@click.option("--table", "as_table", is_flag=True, default=False,
              help="Force tabular output for list-like results.")
@click.option("--quiet", is_flag=True, default=False,
              help="Suppress human output (only errors).")
@click.option("--verbose", is_flag=True, default=False,
              help="Show extra detail (durations, paths, diagnostics).")
@click.option("--debug", is_flag=True, default=False,
              help="Show tracebacks and internal diagnostics.")
@click.option("--no-color", "no_color", is_flag=True, default=False,
              help="Disable ANSI colors (also honored via NO_COLOR env var).")
@click.pass_context
def cli(ctx, as_json, as_yaml, as_table, quiet, verbose, debug, no_color):
    """Cyber AI — integrated local AI security research orchestrator."""
    # Global output modes (spec §14). Stored on a module-level dict so
    # subcommands and helpers can read them without threading Context.
    _OUTPUT_MODE["json"] = as_json
    _OUTPUT_MODE["yaml"] = as_yaml
    _OUTPUT_MODE["table"] = as_table
    _OUTPUT_MODE["quiet"] = quiet or as_json  # JSON mode implies no human noise
    _OUTPUT_MODE["verbose"] = verbose
    _OUTPUT_MODE["debug"] = debug
    _OUTPUT_MODE["no_color"] = no_color or bool(os.environ.get("NO_COLOR"))
    if _OUTPUT_MODE["no_color"]:
        # Rich/click honor NO_COLOR; also strip click's own styling.
        os.environ["NO_COLOR"] = "1"
    ctx.ensure_object(dict)
    ctx.obj["json"] = as_json
    ctx.obj["yaml"] = as_yaml
    ctx.obj["table"] = as_table
    ctx.obj["quiet"] = quiet
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    ctx.obj["no_color"] = no_color


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
def task(ctx, objective, target_id, dry_run, simulate, scope):
    """Run an autonomous assessment.

    The orchestrator determines what to do, which agent/tool/model to use,
    executes in the authorized lab, verifies results, and learns.

    Examples:
      cyber-ai task -o "Analyze my authorized lab target" -t lab-web-01
      cyber-ai task -o "Analyze my authorized lab target" --dry-run
      cyber-ai task -o "Analyze my authorized lab target" --simulate
    """
    asyncio.run(_run_task(objective, target_id, dry_run, simulate, scope))


@cli.command()
@click.option("--objective", "-o", "objective", required=True)
@click.option("--target", "-t", "target_id", default=None)
@click.option("--dry-run", "dry_run", is_flag=True, default=False)
@click.option("--simulate", "simulate", is_flag=True, default=False)
def assess(objective, target_id, dry_run, simulate):
    """Legacy alias for 'task'."""
    asyncio.run(_run_task(objective, target_id, dry_run, simulate))


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
        payload = orch.get_status()
        if _OUTPUT_MODE["json"]:
            _emit_json(payload)
        else:
            _emit_info(json.dumps(payload, indent=2, default=str))
    finally:
        orch.close()


# ---------------------------------------------------------------------------
# models — model registry
# ---------------------------------------------------------------------------
@cli.command()
def models():
    """List available models and their health."""
    gw_status = asyncio.run(_model_status())
    if _OUTPUT_MODE["json"]:
        _emit_json(gw_status)
        return
    if _OUTPUT_MODE["quiet"]:
        return
    for m in gw_status.get("models", []):
        click.echo(f"  {m.get('alias', '?'):20s} provider={m.get('provider', '?'):10s} "
                  f"model={m.get('model', '?')}")
    if _OUTPUT_MODE["verbose"]:
        click.echo("\nHealth:")
        click.echo(json.dumps(gw_status.get("health", {}), indent=2, default=str))


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
    tools_dict = reg.to_dict()["tools"]
    if _OUTPUT_MODE["json"]:
        _emit_json({"tools": tools_dict, "total": len(tools_dict)})
        return
    if _OUTPUT_MODE["quiet"]:
        return
    for name, t in tools_dict.items():
        click.echo(f"  {name}: type={t['type']}, status={t['status']}")
    if _OUTPUT_MODE["verbose"]:
        click.echo(f"\n  total: {len(tools_dict)} tools")


# ---------------------------------------------------------------------------
# agents — agent types
# ---------------------------------------------------------------------------
@cli.command()
def agents():
    """List available agent types."""
    roster = [
        ("planner", "Creates attack plans via planner.py agent"),
        ("researcher", "Gathers information via researcher.py agent"),
        ("recon", "Performs reconnaissance via recon.py agent"),
        ("analyst", "Analyzes findings via analyst.py agent"),
        ("coder", "Writes code/exploits via coder.py agent"),
        ("verifier", "Verifies findings via verifier.py agent"),
        ("reporter", "Generates reports via reporter.py agent"),
    ]
    if _OUTPUT_MODE["json"]:
        _emit_json({"agents": [{"name": n, "description": d} for n, d in roster]})
        return
    if _OUTPUT_MODE["quiet"]:
        return
    for name, desc in roster:
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
    try:
        rows = mm.get_findings(status=status)
        if _OUTPUT_MODE["json"]:
            _emit_json({"findings": rows, "total": len(rows)})
            return
        if _OUTPUT_MODE["quiet"]:
            return
        for f in rows:
            click.echo(f"  [{f.get('status', '')}] {f.get('observation', '')[:80]}")
    finally:
        mm.close()


@cli.command()
@click.argument("query", required=False)
@click.option("--limit", default=10)
def memory(query, limit):
    """Search experience memory."""
    mm = MemoryManager()
    try:
        if not query:
            if not _OUTPUT_MODE["quiet"]:
                click.echo("Usage: cyber-ai memory '<query>' [--limit N]")
            return
        results = mm.search_experiences(query, limit=limit)
        if _OUTPUT_MODE["json"]:
            _emit_json({"query": query, "results": results, "total": len(results)})
            return
        if _OUTPUT_MODE["quiet"]:
            return
        for r in results:
            click.echo(f"  [{r.get('result', '')}] {r.get('observation', '')[:80]}")
    finally:
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
@click.option("--force", is_flag=True, default=False,
              help="Force restart even if the target appears to be running")
def lab_start(target_id, force):
    """Start an authorized lab target.

    Uses Docker when available (target must declare docker_image);
    otherwise falls back to a local mock service so the platform
    stays usable offline.
    """
    from cyberai.orchestrator.lab import LabManager

    lm = LabManager()
    try:
        if not lm.docker_available():
            click.echo("[INFO] Docker not available — using mock service fallback")
        result = asyncio.run(lm.start_target(target_id, force=force))
        st = result.get("status", "?")
        icon = {"RUNNING": "[OK]", "STARTING": "[..]", "DENIED": "[DENIED]",
                "ERROR": "[ERROR]", "STOPPED": "[OK]"}.get(st, "[?]")
        click.echo(f"  {icon} {target_id}: {st}")
        for k in ("mode", "host", "port", "container", "message", "error"):
            if result.get(k):
                click.echo(f"      {k}: {result[k]}")
        if st == "DENIED":
            sys.exit(2)
        if st == "ERROR":
            sys.exit(1)
    finally:
        lm.close()


@lab.command(name="stop")
@click.argument("target_id")
def lab_stop(target_id):
    """Stop a running lab target (container or mock service)."""
    from cyberai.orchestrator.lab import LabManager

    lm = LabManager()
    try:
        result = asyncio.run(lm.stop_target(target_id))
        st = result.get("status", "?")
        icon = {"STOPPED": "[OK]", "NOT_RUNNING": "[INFO]",
                "ERROR": "[ERROR]"}.get(st, "[?]")
        click.echo(f"  {icon} {target_id}: {st}")
        for k in ("mode", "message", "error"):
            if result.get(k):
                click.echo(f"      {k}: {result[k]}")
    finally:
        lm.close()


@lab.command(name="status")
@click.argument("target_id", required=False)
def lab_status(target_id):
    """Show lab target status (all targets, or one by ID)."""
    from cyberai.orchestrator.lab import LabManager

    lm = LabManager()
    try:
        rows = lm.status_all()
        if target_id:
            rows = [r for r in rows if r["id"] == target_id]
            if not rows:
                click.echo(f"Target not found: {target_id}")
                return
        click.echo(f"\n{'TARGET':16s} {'HOST':22s} {'MODE':9s} {'REACHABLE':9s} AUTH")
        click.echo("-" * 70)
        for r in rows:
            reach = "UP" if r["reachable"] else "down"
            auth = "yes" if r["authorized"] else "NO"
            click.echo(f"  {r['id']:14s} {r['host'] + ':' + str(r['port']):20s} "
                       f"{r['mode']:9s} {reach:9s} {auth}")
        if not rows:
            click.echo("  (no targets registered)")
    finally:
        lm.close()


@cli.group()
def session():
    """Session management commands."""
    pass


@session.command(name="list")
def session_list():
    """List all sessions."""
    mm = MemoryManager()
    try:
        rows = mm.list_sessions()
        if _OUTPUT_MODE["json"]:
            _emit_json({"sessions": rows, "total": len(rows)})
            return
        if _OUTPUT_MODE["quiet"]:
            return
        for s in rows:
            click.echo(f"  {s['id']}: target={s.get('target_id', '')}, status={s.get('status', '')}")
    finally:
        mm.close()


@session.command(name="show")
@click.argument("session_id")
def session_show(session_id):
    """Show session details."""
    mm = MemoryManager()
    try:
        s = mm.get_session(session_id)
        if _OUTPUT_MODE["json"]:
            _emit_json(s if s else {"error": f"Session not found: {session_id}"})
            return
        if s:
            click.echo(json.dumps(s, indent=2, default=str))
        else:
            click.echo(f"Session not found: {session_id}")
    finally:
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
# profile — hardware detection + execution profile
# ---------------------------------------------------------------------------
@cli.command()
def profile():
    """Detect hardware and show the recommended execution profile.

    Probes OS, CPU, RAM, GPUs (nvidia-smi), Docker and Ollama, then maps
    the machine to one of: MINIMAL / CLOUD / HYBRID / LOCAL / SERVER.
    Override with the CERBERUS_PROFILE env var.
    """
    from cyberai.llm_gateway.hardware import detect_hardware, format_report

    hp = detect_hardware()
    if _OUTPUT_MODE["json"]:
        _emit_json(hp.as_dict())
        return
    if _OUTPUT_MODE["quiet"]:
        return
    click.echo("CERBERUS HARDWARE PROFILE")
    click.echo(format_report(hp))


# ---------------------------------------------------------------------------
# doctor — health check
# ---------------------------------------------------------------------------
@cli.command()
def doctor():
    """Run comprehensive health checks."""
    from cyberai.orchestrator.cli.doctor import run_health_check
    results = run_health_check()
    if _OUTPUT_MODE["json"]:
        _emit_json([{"component": c, "status": s, "message": m}
                    for c, s, m in results])
        return
    icon = {"ok": "[OK]", "warn": "[WARN]", "error": "[ERROR]", "info": "[INFO]"}
    for component, status_val, msg in results:
        click.echo(f"  {icon.get(status_val, '[?]')} {component}: {msg}")


# ---------------------------------------------------------------------------
# watch — live-tail of platform events (audit, tasks, findings) for the CLI
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--interval", default=2.0, type=float, help="Polling interval seconds")
@click.option("--max-events", default=0, type=int, help="Stop after N events (0 = forever)")
@click.option("--source", default="all",
              type=click.Choice(["all", "audit", "tasks", "findings"]),
              help="Which event source to tail")
def watch(interval, max_events, source):
    """Live-tail CERBERUS events: tasks, findings, audit.

    Example:
      cyber-ai watch --interval 1.5 --source audit
    """
    asyncio.run(_run_watch(interval, max_events, source))


async def _run_watch(interval, max_events, source):
    """Async implementation of the watch command."""
    from cyberai.orchestrator import MemoryManager
    import datetime as dt

    mm = MemoryManager()
    seen = set()
    count = 0
    click.echo("[CERBERUS] watching for events (Ctrl+C to stop)…")
    try:
        while True:
            if source in ("all", "tasks"):
                for s in mm.list_sessions():
                    sid = s.get("id")
                    if sid and sid not in seen:
                        seen.add(sid)
                        click.echo(f"  [TASK ] {sid[:8]} target={s.get('target_id','?')} status={s.get('status','?')}")
                        count += 1
            if source in ("all", "findings"):
                for f in mm.get_findings():
                    fid = f.get("id")
                    if fid and fid not in seen:
                        seen.add(fid)
                        click.echo(f"  [FIND ] {fid[:8]} [{f.get('status','')}] {str(f.get('observation',''))[:80]}")
                        count += 1
            if source in ("all", "audit"):
                logs_dir = WORKSPACE_ROOT / "logs" / "sessions"
                if logs_dir.exists():
                    for f in sorted(logs_dir.glob("*.jsonl"),
                                    key=lambda p: p.stat().st_mtime, reverse=True)[:3]:
                        try:
                            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines()[-5:]:
                                line = line.strip()
                                if line and line not in seen:
                                    seen.add(line)
                                    rec = json.loads(line)
                                    click.echo(f"  [AUDIT] {rec.get('action','')[:40]} tool={rec.get('tool','')} result={rec.get('result','')}")
                                    count += 1
                        except Exception:
                            pass
            if max_events and count >= max_events:
                break
            await asyncio.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        mm.close()
        click.echo(f"[CERBERUS] stopped after {count} events.")


# ---------------------------------------------------------------------------
# replay — replay a session's trajectory as a step-by-step narrative
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("session_id")
def replay(session_id):
    """Replay a session's findings + experiences as a step-by-step narrative.

    Example:
      cyber-ai replay <session_id>
    """
    from cyberai.orchestrator import MemoryManager

    mm = MemoryManager()
    s = mm.get_session(session_id)
    if not s:
        click.echo(f"Session not found: {session_id}")
        mm.close()
        return
    click.echo(f"\n=== SESSION {session_id[:8]} ===")
    click.echo(f"Target: {s.get('target_id','?')}")
    click.echo(f"Started: {s.get('started_at','?')}")
    click.echo(f"Ended: {s.get('completed_at') or s.get('ended_at') or '?'}")
    click.echo(f"Status: {s.get('status','?')}")
    if s.get("summary"):
        click.echo(f"Summary: {s['summary']}")

    findings = [f for f in mm.get_findings() if f.get("session_id") == session_id]
    click.echo(f"\n--- FINDINGS ({len(findings)}) ---")
    for f in findings:
        click.echo(f"  [{f.get('status','')}] conf={f.get('confidence',0):.2f} src={f.get('source','')}")
        click.echo(f"    {str(f.get('observation',''))[:140]}")

    mm.close()


# ---------------------------------------------------------------------------
# hunt — guided target-hunting wizard
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("target_id")
@click.option("--objective", "-o", default="Full reconnaissance and enumeration",
              help="Hunt objective")
@click.option("--simulate", is_flag=True, default=True)
def hunt(target_id, objective, simulate):
    """Launch a guided hunt against an authorized target.

    Example:
      cyber-ai hunt lab-web-01 -o "Identify exposed services"
    """
    asyncio.run(_run_hunt(target_id, objective, simulate))


async def _run_hunt(target_id, objective, simulate):
    """Async implementation of hunt."""
    from cyberai import CyberAIOrchestrator
    from cyberai.orchestrator import PolicyEngine

    pe = PolicyEngine()
    target = pe.get_target(target_id)
    pe.close()
    if not target:
        click.echo(f"[ERROR] Unknown target: {target_id}")
        return
    if not target.get("allowed"):
        click.echo(f"[ERROR] Target not authorized: {target_id}")
        return

    click.echo(f"[HUNT] target={target_id} host={target.get('host')}:{target.get('port')}")
    click.echo(f"[HUNT] objective={objective}")
    click.echo(f"[HUNT] mode={'SIMULATE' if simulate else 'LIVE'}")

    orch = CyberAIOrchestrator(simulate=simulate, local_only=True)
    try:
        result = await orch.run(
            objective,
            target_id=target_id,
            scope="authorized_lab",
        )
        click.echo("\n=== HUNT RESULTS ===")
        click.echo(f"Status: {result.get('status','?').upper()}")
        click.echo(f"Findings: {len(result.get('findings', []))}")
        report = result.get("final_report") or {}
        if report.get("content"):
            click.echo("\n--- REPORT ---")
            click.echo(report["content"][:2000])
    finally:
        orch.close()


# ---------------------------------------------------------------------------
# blueprint — export target blueprint (port map + service inventory)
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("target_id")
@click.option("--format", "fmt", default="text",
              type=click.Choice(["text", "json"]))
def blueprint(target_id, fmt):
    """Show the blueprint of an authorized target.

    Example:
      cyber-ai blueprint lab-web-01
      cyber-ai blueprint lab-web-01 --format json
    """
    from cyberai.orchestrator import PolicyEngine

    pe = PolicyEngine()
    target = pe.get_target(target_id)
    pe.close()
    if not target:
        click.echo(f"Target not found: {target_id}")
        return
    blueprint = {
        "id": target.get("id"),
        "host": target.get("host"),
        "port": target.get("port"),
        "protocol": target.get("protocol", "tcp"),
        "environment": target.get("environment", "authorized_lab"),
        "allowed": target.get("allowed"),
        "description": target.get("description", ""),
        "allowed_actions": target.get("allowed_actions", []),
        "tags": target.get("tags", []),
        "owner": target.get("owner", ""),
    }
    if fmt == "json":
        click.echo(json.dumps(blueprint, indent=2))
    else:
        click.echo(f"\n=== TARGET BLUEPRINT: {target_id} ===")
        for k, v in blueprint.items():
            click.echo(f"  {k:18s} {v}")


# ---------------------------------------------------------------------------
# intel — quick intelligence summary for a target
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("target_id")
def intel(target_id):
    """Quick intelligence summary: findings + memory + status for a target.

    Example:
      cyber-ai intel lab-web-01
    """
    from cyberai.orchestrator import MemoryManager, PolicyEngine

    pe = PolicyEngine()
    target = pe.get_target(target_id)
    pe.close()
    mm = MemoryManager()
    findings = [f for f in mm.get_findings() if f.get("target_id") == target_id]
    mm.close()
    click.echo(f"\n=== INTEL: {target_id} ===")
    if target:
        click.echo(f"  Host: {target.get('host')}:{target.get('port')}")
        click.echo(f"  Environment: {target.get('environment')}")
        click.echo(f"  Authorized: {target.get('allowed')}")
    click.echo(f"\n--- FINDINGS ({len(findings)}) ---")
    for f in findings[:20]:
        click.echo(f"  [{f.get('status','')}] {str(f.get('observation',''))[:100]}")
    if not findings:
        click.echo("  No findings recorded yet.")


# ---------------------------------------------------------------------------
# scorecard — show overall platform scorecard
# ---------------------------------------------------------------------------
@cli.command()
def scorecard():
    """Show the overall CERBERUS platform scorecard.

    Aggregates: sessions, findings (by status), memory, tools, models, performance.
    """
    from cyberai.orchestrator import MemoryManager, PolicyEngine, ToolRegistry
    from cyberai.meta_learning.tracker import PerformanceTracker

    mm = MemoryManager()
    sessions = mm.list_sessions()
    findings = mm.get_findings()
    by_status: Dict[str, int] = {}
    for f in findings:
        s = f.get("status", "UNKNOWN")
        by_status[s] = by_status.get(s, 0) + 1
    mm.close()

    pe = PolicyEngine()
    targets = pe.list_targets()
    auth = [t for t in targets if t.get("allowed")]
    pe.close()

    tr = ToolRegistry()
    tools = list(tr.to_dict()["tools"].keys())

    pt = PerformanceTracker()
    model_stats = pt.get_all_stats("model")
    agent_stats = pt.get_all_stats("agent")
    pt.close()

    completed = sum(1 for s in sessions if s.get("status") == "completed")
    payload = {
        "sessions": {"total": len(sessions), "completed": completed},
        "targets": {"registered": len(targets), "authorized": len(auth)},
        "tools": {"total": len(tools)},
        "findings": {"by_status": {st: by_status.get(st, 0)
                                   for st in ("VERIFIED", "LIKELY", "UNVERIFIED", "REJECTED")}},
        "tracked": {"agents": len(agent_stats), "models": len(model_stats)},
    }
    if _OUTPUT_MODE["json"]:
        _emit_json(payload)
        return
    if _OUTPUT_MODE["quiet"]:
        return
    click.echo("\n========= CERBERUS SCORECARD =========")
    click.echo(f"Sessions:   {len(sessions)} ({completed} completed)")
    click.echo(f"Targets:    {len(targets)} registered / {len(auth)} authorized")
    click.echo(f"Tools:      {len(tools)} registered")
    click.echo("\nFindings by status:")
    for st in ("VERIFIED", "LIKELY", "UNVERIFIED", "REJECTED"):
        click.echo(f"  {st:12s} {by_status.get(st, 0)}")
    click.echo(f"\nTracked agents: {len(agent_stats)}  ·  Tracked models: {len(model_stats)}")
    click.echo("=====================================")


# ---------------------------------------------------------------------------
# report — generate a markdown report from a session
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("session_id")
@click.option("--out", "-o", default=None, help="Output file (default: reports/<id>.md)")
def report(session_id, out):
    """Generate a Markdown report for a completed session.

    Example:
      cyber-ai report <session_id> -o reports/hunt1.md
    """
    from cyberai.orchestrator import MemoryManager

    mm = MemoryManager()
    s = mm.get_session(session_id)
    if not s:
        click.echo(f"Session not found: {session_id}")
        mm.close()
        return
    findings = [f for f in mm.get_findings() if f.get("session_id") == session_id]
    mm.close()

    out_path = Path(out) if out else WORKSPACE_ROOT / "reports" / f"{session_id[:8]}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# CERBERUS Session Report",
        "",
        f"**Session:** `{session_id}`",
        f"**Target:** {s.get('target_id', '?')}",
        f"**Started:** {s.get('started_at', '?')}",
        f"**Status:** {s.get('status', '?')}",
        "",
    ]
    if s.get("summary"):
        lines += ["## Summary", "", s["summary"], ""]
    lines += ["## Findings", ""]
    if findings:
        for i, f in enumerate(findings, 1):
            lines += [
                f"### {i}. [{f.get('status', '?')}] {f.get('source', '?')}",
                "",
                f"- **Confidence:** {f.get('confidence', 0):.2f}",
                f"- **Observation:** {f.get('observation', '')}",
                "",
            ]
    else:
        lines += ["_No findings recorded._", ""]

    out_path.write_text("\n".join(lines), encoding="utf-8")
    click.echo(f"Report written to {out_path} ({len(findings)} findings)")


# ---------------------------------------------------------------------------
# config — view / manage platform configuration
# ---------------------------------------------------------------------------
@cli.command("config")
@click.argument("key", required=False)
@click.option("--list", "list_all", is_flag=True, default=False, help="List all config")
def config_cmd(key, list_all):
    """View platform configuration (sections or section.key).

    Examples:
      cyber-ai config --list
      cyber-ai config policy
      cyber-ai config policy targets_path
    """
    from cyberai.config import config

    if list_all or not key:
        click.echo(json.dumps(config.to_dict(), indent=2, default=str))
        return
    parts = key.split(".", 1)
    section = parts[0]
    subkey = parts[1] if len(parts) > 1 else None
    val = config.get(section, subkey)
    if val is None:
        click.echo(f"[?] {key} = <unset>")
    else:
        click.echo(f"{key} = {json.dumps(val, default=str)}")


# ---------------------------------------------------------------------------
# history — show recent platform activity
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--limit", default=20, type=int, help="Max entries")
def history(limit):
    """Show recent platform activity (sessions + findings merged)."""
    from cyberai.orchestrator import MemoryManager

    mm = MemoryManager()
    events = []
    for s in mm.list_sessions():
        events.append((s.get("started_at") or "", "SESSION",
                       f"{s.get('id', '')[:8]} target={s.get('target_id', '?')} "
                       f"status={s.get('status', '?')}"))
    for f in mm.get_findings():
        events.append((f.get("created_at") or f.get("timestamp") or "", "FINDING",
                       f"[{f.get('status', '')}] {str(f.get('observation', ''))[:90]}"))
    mm.close()

    events.sort(key=lambda e: e[0], reverse=True)
    click.echo(f"\n=== HISTORY ({min(len(events), limit)}/{len(events)}) ===")
    for ts, kind, desc in events[:limit]:
        click.echo(f"  {ts[:19]:20s} [{kind:8s}] {desc}")


# ---------------------------------------------------------------------------
# benchmark — quick platform benchmark
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--rounds", default=3, type=int, help="Benchmark rounds")
def benchmark(rounds):
    """Benchmark core platform operations (memory, policy, tools)."""
    import time as _time

    from cyberai.orchestrator import MemoryManager, PolicyEngine, ToolRegistry

    click.echo(f"\n=== CERBERUS BENCHMARK ({rounds} rounds) ===")

    # Memory
    t0 = _time.perf_counter()
    for _ in range(rounds):
        mm = MemoryManager()
        mm.list_sessions()
        mm.get_findings()
        mm.close()
    dt = (_time.perf_counter() - t0) / rounds
    click.echo(f"  memory (open+list+close):  {dt * 1000:8.1f} ms/op")

    # Policy
    t0 = _time.perf_counter()
    for _ in range(rounds):
        pe = PolicyEngine()
        pe.list_targets()
        pe.close()
    dt = (_time.perf_counter() - t0) / rounds
    click.echo(f"  policy (load+list):        {dt * 1000:8.1f} ms/op")

    # Tools
    t0 = _time.perf_counter()
    for _ in range(rounds):
        tr = ToolRegistry()
        tr.to_dict()
    dt = (_time.perf_counter() - t0) / rounds
    click.echo(f"  tools  (registry+dict):    {dt * 1000:8.1f} ms/op")


# ---------------------------------------------------------------------------
# workflow — list and run predefined workflows
# ---------------------------------------------------------------------------
@cli.group()
def workflow():
    """Assessment workflow management."""
    pass


@workflow.command(name="list")
def workflow_list():
    """List available workflows."""
    from cyberai.orchestrator.workflows import WorkflowManager

    wm = WorkflowManager()
    for name in wm.list_workflows():
        wf = wm.get_workflow(name)
        click.echo(f"  {name:20s} {wf.get('description', '')}")
        click.echo(f"  {'':20s} steps: {' -> '.join(s['agent'] for s in wf.get('steps', []))}")


@workflow.command(name="show")
@click.argument("name")
def workflow_show(name):
    """Show a workflow definition."""
    from cyberai.orchestrator.workflows import WorkflowManager

    wm = WorkflowManager()
    wf = wm.get_workflow(name)
    if not wf:
        click.echo(f"Unknown workflow: {name}")
        return
    click.echo(json.dumps(wf, indent=2))


# ---------------------------------------------------------------------------
# mcp — MCP tool surface (list, call, health)
# ---------------------------------------------------------------------------
@cli.group()
def mcp():
    """Model Context Protocol (MCP) tool surface."""
    pass


@mcp.command(name="list")
def mcp_list():
    """List discovered MCP servers and tools."""
    from cyberai.orchestrator.cli._mcp import get_mcp_gateway

    gw = get_mcp_gateway()
    discovered = gw.discover_mcp_servers()
    click.echo(f"\n=== MCP SERVERS ({len(discovered)} discovered) ===")
    for s in discovered:
        click.echo(f"  {s['name']:25s} type={s['type']:8s} caps={','.join(s.get('capabilities', []))}")
    click.echo(f"\nConfigured servers: {len(gw._servers)}")
    for name in gw._servers:
        click.echo(f"  - {name}")


@mcp.command(name="health")
def mcp_health():
    """Health-check all configured MCP servers (real probes)."""
    from cyberai.orchestrator.cli._mcp import get_mcp_gateway

    gw = get_mcp_gateway()
    results = asyncio.run(gw.health_check_all())
    click.echo("\n=== MCP HEALTH ===")
    for name, info in results.items():
        st = info.get("status", "?")
        icon = {"HEALTHY": "[OK]", "DEGRADED": "[WARN]", "OFFLINE": "[OFFLINE]",
                "DISCOVERED": "[INFO]", "NOT_TESTED": "[?]"}.get(st, "[?]")
        click.echo(f"  {icon} {name:25s} {info.get('message', '')}")


@mcp.command(name="tools")
@click.argument("server")
def mcp_tools(server):
    """List tools exposed by an MCP server (JSON-RPC tools/list).

    Example:
      cyber-ai mcp tools hexstrike-mcp
    """
    import json as _json

    from cyberai.orchestrator.cli._mcp import get_mcp_gateway

    gw = get_mcp_gateway()
    result = asyncio.run(gw.list_server_tools(server))
    if result.get("status") == "SUCCESS":
        click.echo(f"\n=== TOOLS on {server} ({len(result['tools'])}) ===")
        for t in result["tools"]:
            click.echo(f"  {t['name']:30s} {(t.get('description') or '')[:70]}")
    else:
        click.echo(f"[{result.get('status', '?')}] {result.get('error', '')}")


@mcp.command(name="register")
@click.argument("name")
@click.option("--command", required=True, help="Executable to launch")
@click.option("--arg", "-a", multiple=True, help="Argument (repeatable)")
@click.option("--cwd", default=None, help="Working directory")
@click.option("--capability", "-c", multiple=True, help="Capability tag (repeatable)")
def mcp_register(name, command, arg, cwd, capability):
    """Register a new MCP server (in-memory for this session).

    Example:
      cyber-ai mcp register my-mcp --command python -a server.py --cwd ./tools
    """
    from cyberai.orchestrator.cli._mcp import get_mcp_gateway

    gw = get_mcp_gateway()
    gw.register_server(name, {
        "name": name,
        "type": "stdio",
        "command": command,
        "args": list(arg),
        "cwd": cwd,
        "capabilities": list(capability),
    })
    click.echo(f"Registered MCP server '{name}' (session-scoped)")


@mcp.command(name="call")
@click.argument("server")
@click.argument("tool")
@click.option("--arg", "-a", multiple=True, help="key=value argument (repeatable)")
@click.option("--timeout", "-t", default=60.0, show_default=True,
              help="Tool call timeout in seconds")
def mcp_call(server, tool, arg, timeout):
    """Call an MCP tool on a discovered server.

    Example:
      cyber-ai mcp call hexstrike-mcp nmap_scan -a target=lab-web-01
    """
    import json as _json

    from cyberai.orchestrator.cli._mcp import get_mcp_gateway

    gw = get_mcp_gateway()
    parsed = {}
    for a in arg:
        if "=" in a:
            k, v = a.split("=", 1)
            parsed[k.strip()] = v.strip()
    result = asyncio.run(gw.call_tool(server, tool, parsed, timeout=timeout))
    click.echo(_json.dumps(result, indent=2, default=str))


# ---------------------------------------------------------------------------
# F2T2EA Kill Chain
# ---------------------------------------------------------------------------

@cli.group()
def killchain():
    """F2T2EA kill-chain tracking (Find→Fix→Track→Target→Engage→Assess)."""


@killchain.command(name="start")
@click.argument("target")
def killchain_start(target):
    """Start (or resume) a kill chain for TARGET."""
    from cyberai.orchestrator.workflows.kill_chain import KillChainEngine

    engine = KillChainEngine()
    chain = engine.start_chain(target)
    click.echo(f"Chain {chain.chain_id} for '{target}'")
    click.echo(f"  Phase: {chain.current_phase.value}")
    click.echo(f"  Status: {chain.status}")


@killchain.command(name="advance")
@click.argument("target")
@click.option("--note", "-n", default="", help="Note for this phase")
@click.option("--finding", "-f", multiple=True, help="key=value finding (repeatable)")
def killchain_advance(target, note, finding):
    """Advance TARGET's chain to the next phase."""
    from cyberai.orchestrator.workflows.kill_chain import KillChainEngine, KillChainError

    engine = KillChainEngine()
    finding_dict = {}
    for kv in finding:
        if "=" in kv:
            k, v = kv.split("=", 1)
            finding_dict[k.strip()] = v.strip()
    try:
        result = engine.advance(target, note=note, finding=finding_dict or None)
        click.echo(f"Advanced '{target}' to phase: {result['current_phase']}")
    except KillChainError as e:
        click.echo(f"Error: {e}")


@killchain.command(name="fail")
@click.argument("target")
@click.option("--reason", "-r", required=True, help="Failure reason")
@click.option("--category", "-c", default="execution", show_default=True)
def killchain_fail(target, reason, category):
    """Fail TARGET's current phase and abort its chain."""
    from cyberai.orchestrator.workflows.kill_chain import KillChainEngine, KillChainError

    engine = KillChainEngine()
    try:
        result = engine.fail(target, reason=reason, category=category)
        click.echo(f"Aborted chain for '{target}': {reason}")
        click.echo(f"  Status: {result['status']}")
    except KillChainError as e:
        click.echo(f"Error: {e}")


@killchain.command(name="status")
@click.argument("target", required=False)
def killchain_status(target):
    """Show chain status (all chains, or one TARGET)."""
    from cyberai.orchestrator.workflows.kill_chain import (
        KillChainEngine, PHASE_ORDER,
    )

    engine = KillChainEngine()
    if target:
        chain = engine.get_chain(target)
        if not chain:
            click.echo(f"No chain for '{target}'")
            return
        click.echo(f"Chain {chain.chain_id} — target '{target}'")
        click.echo(f"  Phase: {chain.current_phase.value}  Status: {chain.status}")
        for ph in PHASE_ORDER:
            st = chain.phase_status.get(ph, "PENDING")
            mark = {"COMPLETE": "[+]", "ACTIVE": "[>]", "FAILED": "[!]",
                    "TIMED_OUT": "[T]", "PENDING": "[ ]"}.get(st, "[?]")
            click.echo(f"    {mark} {ph:<8} {st}")
    else:
        agg = engine.status()
        click.echo("=== KILL CHAIN STATUS ===")
        click.echo(f"  Active: {agg['active']}  Complete: {agg['complete']}  "
                   f"Aborted: {agg['aborted']}")
        for c in agg["chains"]:
            click.echo(f"  [{c['current_phase']:<7}] {c['target']:<20} {c['status']}")


@killchain.command(name="reset")
@click.confirmation_option(prompt="Delete all kill-chain state?")
def killchain_reset():
    """Drop all kill-chain state (fresh start)."""
    from cyberai.orchestrator.workflows.kill_chain import KillChainEngine

    engine = KillChainEngine()
    engine.reset()
    click.echo("Kill-chain state cleared.")


# ---------------------------------------------------------------------------
# Ghost Wargaming
# ---------------------------------------------------------------------------

@cli.group()
def wargame():
    """Ghost wargaming: learn from failures without live execution."""


@wargame.command(name="failures")
@click.option("--limit", default=10, show_default=True)
def wargame_failures(limit):
    """Show recent recorded failures."""
    from cyberai.evolution import GhostWargame

    gw = GhostWargame()
    fails = gw.recent_failures(limit=limit)
    if not fails:
        click.echo("No failures recorded.")
        return
    click.echo(f"=== {len(fails)} RECENT FAILURES ===")
    for f in fails:
        click.echo(f"  [{f.get('failure_category', '?')}] {f.get('strategy_id', '?')}: "
                   f"{str(f.get('reason', ''))[:70]}")


@wargame.command(name="analytics")
def wargame_analytics():
    """Show failure analytics (by category and tool)."""
    from cyberai.evolution import GhostWargame

    gw = GhostWargame()
    a = gw.analytics()
    click.echo("=== WARGAME ANALYTICS ===")
    click.echo(f"  Total failures: {a['total_failures']}")
    click.echo(f"  Population: {a['population_size']}  Elite: {a['elite_size']}")
    if a.get("by_category"):
        click.echo("  By category:")
        for cat, n in sorted(a["by_category"].items(), key=lambda x: -x[1]):
            click.echo(f"    {cat:<20} {n}")
    if a.get("by_tool"):
        click.echo("  By tool:")
        for tool, n in sorted(a["by_tool"].items(), key=lambda x: -x[1])[:10]:
            click.echo(f"    {tool:<20} {n}")


@wargame.command(name="fast-forward")
@click.option("--task-type", default="vulnerability_research", show_default=True)
@click.option("--num-strategies", default=3, show_default=True)
def wargame_fast_forward(task_type, num_strategies):
    """Simulate a generation of evolution (no live execution)."""
    import asyncio as _aio

    from cyberai.evolution import GhostWargame

    gw = GhostWargame()
    result = _aio.run(gw.fast_forward(task_type, num_strategies=num_strategies))
    click.echo(f"Mode: {result['mode']} (no live execution)")
    click.echo(f"  Generated: {result['new_strategies_generated']}")
    click.echo(f"  Successful: {result['successful']}  Failed: {result['failed']}")
    if result.get("avoided"):
        click.echo(f"  Ghost-avoided: {result['avoided']}")


# ---------------------------------------------------------------------------
# Semantic Memory Search
# ---------------------------------------------------------------------------

@cli.group()
def mem():
    """Typed memory store: semantic search over experiences."""


@mem.command(name="search")
@click.argument("query")
@click.option("--type", "memory_type", default=None,
              help="Filter by memory type (semantic, failure, procedural, ...)")
@click.option("--limit", default=10, show_default=True)
def mem_search(query, memory_type, limit):
    """Semantic (TF-IDF) memory search.

    Example:
      cyber-ai mem search "SQL injection auth bypass" --limit 5
    """
    from cyberai.memory.memory_store import MemoryStore

    ms = MemoryStore()
    results = ms.semantic_search(query, memory_type=memory_type, limit=limit)
    if not results:
        click.echo("No matching memories.")
        return
    click.echo(f"=== {len(results)} MATCHES ===")
    for r in results:
        sim = r.get("similarity", 0)
        click.echo(f"  [{sim:.2f}] ({r['memory_type']}) {r['content'][:80]}")


@mem.command(name="stats")
def mem_stats():
    """Show memory store statistics."""
    from cyberai.memory.memory_store import MemoryStore

    ms = MemoryStore()
    stats = ms.get_stats()
    click.echo("=== MEMORY STATS ===")
    click.echo(f"  Total: {stats['total']}")
    for t, n in sorted(stats["by_type"].items(), key=lambda x: -x[1]):
        click.echo(f"    {t:<12} {n}")


# ---------------------------------------------------------------------------
# interactive — themed operator shell (spec §22)
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--simulate", is_flag=True, default=False,
              help="Default all launched tasks to simulation mode")
@click.option("--verbose", is_flag=True, default=False,
              help="Show extra detail in command results")
@click.pass_context
def interactive(ctx, simulate, verbose):
    """Interactive operator shell — themed REPL with the shared command bus.

    A Claude-Code-style console: Rich tables, tab completion, persistent
    history (~/.cerberus/cli_history), background tasks, and the full
    slash-command catalog (/targets /findings /status …) dispatched through
    the SAME command bus as the web UI chat and the REST API.

    Local controls:
      /help                 command catalog (from the shared registry)
      /clear                clear the screen
      /stop                 stop the running background task
      /result               show the last task's result
      /watch                live-tail events until Ctrl+C
      /quit                 exit the shell

    Anything that is not a slash command is treated as a task objective.
    See docs/CLI_GUIDE.md and docs/COMMANDS.md.
    """
    verbose = verbose or bool(ctx.obj and ctx.obj.get("verbose"))
    from cyberai.orchestrator.cli.shell.interactive import run_console
    run_console(simulate=simulate, verbose=verbose)


if __name__ == "__main__":
    cli()
