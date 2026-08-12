"""Cyber AI Orchestrator — CLI."""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import click
from cyberai.orchestrator import Orchestrator
from cyberai.orchestrator import ToolRegistry
from cyberai.orchestrator import PolicyEngine


@click.group()
def cli():
    """Cyber AI Orchestrator — Local AI Security Research Platform."""
    pass


@cli.command()
def status():
    """Show orchestrator status."""
    orch = Orchestrator()
    click.echo(json.dumps(orch.get_status(), indent=2))
    orch.memory.close()


@cli.command()
def models():
    """List available models."""
    import yaml
    p = Path(__file__).parent.parent.parent / "llm-gateway" / "models" / "models.yaml"
    if p.exists():
        data = yaml.safe_load(open(p))
        for name, info in data.get("models", {}).items():
            click.echo(f"  {name}: provider={info['provider']}, status={info['status']}")
    else:
        click.echo("No model registry found.")


@cli.command()
def agents():
    """List available agent types."""
    for name, desc in [
        ("planner", "Creates attack plans"),
        ("researcher", "Gathers information"),
        ("recon", "Scans targets"),
        ("analyst", "Analyzes findings"),
        ("coder", "Writes code/exploits"),
        ("verifier", "Checks findings"),
        ("reporter", "Generates reports"),
    ]:
        click.echo(f"  {name}: {desc}")


@cli.command()
def tools():
    """List available tools and adapters."""
    reg = ToolRegistry()
    for name in reg.list_tools():
        t = reg.get_tool(name)
        click.echo(f"  {name}: type={t['type']}, status={t['status']}")


@cli.group()
def lab():
    """Lab management commands."""
    pass


@lab.command(name="list")
def lab_list():
    """List lab targets."""
    policy = PolicyEngine()
    targets = policy.list_targets()
    if not targets:
        click.echo("No registered targets. Edit lab/targets/targets.yaml")
        return
    for t in targets:
        st = "AUTHORIZED" if t.get("allowed") else "NOT AUTHORIZED"
        click.echo(f"  {t['id']}: {st}")


@lab.command(name="start")
@click.argument("target_id")
def lab_start(target_id):
    """Start a lab target."""
    click.echo(f"[NOT YET IMPLEMENTED] Start target: {target_id}")
    click.echo("Lab environment requires Docker (not installed on this system).")


@cli.command()
@click.argument("target_id")
@click.option("--objective", "-o", required=True)
def assess(target_id, objective):
    """Run an assessment on an authorized target."""
    async def _run():
        orch = Orchestrator()
        try:
            result = await orch.assess(target_id, objective)
            click.echo(json.dumps(result, indent=2, default=str))
        except PermissionError as e:
            click.echo(f"[ERROR] {e}", err=True)
        finally:
            orch.memory.close()
    asyncio.run(_run())


@cli.command()
@click.option("--status", default=None)
def findings(status):
    """List findings."""
    orch = Orchestrator()
    for f in orch.memory.get_findings(status=status):
        click.echo(f"  [{f.get('status','')}] {f.get('observation','')[:80]}")
    orch.memory.close()


@cli.command()
@click.argument("query", required=False)
@click.option("--limit", default=10)
def memory(query, limit):
    """Search memory for relevant experiences."""
    orch = Orchestrator()
    if not query:
        click.echo("Usage: cyberai memory '<query>'")
        orch.memory.close()
        return
    for r in orch.memory.search_experiences(query, limit=limit):
        click.echo(f"  [{r.get('result','')}] {r.get('observation','')[:80]}")
    orch.memory.close()


@cli.group()
def session():
    """Session management commands."""
    pass


@session.command(name="list")
def session_list():
    """List all sessions."""
    orch = Orchestrator()
    for s in orch.memory.list_sessions():
        click.echo(f"  {s['id']}: target={s.get('target_id','')}, status={s.get('status','')}")
    orch.memory.close()


@session.command(name="show")
@click.argument("session_id")
def session_show(session_id):
    """Show session details."""
    orch = Orchestrator()
    s = orch.memory.get_session(session_id)
    if s:
        click.echo(json.dumps(s, indent=2, default=str))
    else:
        click.echo(f"Session not found: {session_id}")
    orch.memory.close()


@cli.command()
def doctor():
    """Run health check."""
    from cyberai.orchestrator.cli.doctor import run_health_check
    for component, status, msg in run_health_check():
        icon = {"ok": "[OK]", "warn": "[WARN]", "error": "[ERROR]", "info": "[INFO]"}
        click.echo(f"  {icon.get(status, '[?]')} {component}: {msg}")


if __name__ == "__main__":
    cli()
