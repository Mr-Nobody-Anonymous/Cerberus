"""Agent commands: /agents."""

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand

_BASE_AGENTS = [
    {"name": "planner", "role": "Mission planning", "capability": "planning"},
    {"name": "researcher", "role": "Threat intelligence", "capability": "research"},
    {"name": "recon", "role": "Network discovery", "capability": "reconnaissance"},
    {"name": "analyst", "role": "Pattern analysis", "capability": "analysis"},
    {"name": "coder", "role": "Exploit / PoC code", "capability": "code_generation"},
    {"name": "verifier", "role": "Evidence validation", "capability": "verification"},
    {"name": "reporter", "role": "Report generation", "capability": "reporting"},
]


def _agents(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    tracker = None
    try:
        tracker = ctx.tracker()
        stats = tracker.get_all_stats("agent")
    except Exception:
        stats = {}
    finally:
        ctx.close_resource(tracker)
    out = []
    for a in _BASE_AGENTS:
        ag = stats.get(a["name"], {})
        calls = sum(v.get("calls", 0) for v in ag.values())
        rates = [v.get("success_rate", 0) for v in ag.values()]
        out.append({
            **a,
            "calls": calls,
            "success_rate": round(sum(rates) / len(rates), 3) if rates else None,
        })
    return CommandResult.success(
        "agents", data={"agents": out},
        rows=out, columns=["name", "role", "calls", "success_rate"],
    )


def register(registry) -> None:
    from cyberai.commands.models import CommandSpec
    registry.register(CommandSpec(
        name="agents", category="operations", description="List agents with performance stats",
        handler=_agents, aliases=["ag"],
        usage="agents",
    ))
