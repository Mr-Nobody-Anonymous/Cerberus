"""Tool commands: /tools."""

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand


def _tools(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    tr = None
    am = None
    try:
        tr = ctx.tools()
        registry = tr.to_dict().get("tools", {})
        am = ctx.adapters()
        discovered = am.discover()
        out = []
        for name in sorted(registry):
            info = registry[name]
            out.append({
                "name": name,
                "present": name in discovered,
                "category": info.get("category", ""),
                "description": info.get("description", ""),
            })
        return CommandResult.success(
            "tools", data={"tools": out, "total": len(out)},
            rows=out, columns=["name", "present", "category"],
        )
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("tools", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(tr)
        ctx.close_resource(am)


def register(registry) -> None:
    from cyberai.commands.models import CommandSpec
    registry.register(CommandSpec(
        name="tools", category="operations", description="List registered tools + adapter presence",
        handler=_tools, aliases=["t"],
        usage="tools",
    ))
