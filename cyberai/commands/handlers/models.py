"""Model commands: /models, /model."""

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand


def _models(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    gw = None
    try:
        gw = ctx.gateway()
        models = gw.list_registry()
        return CommandResult.success(
            "models", data={"models": models},
            rows=models, columns=["alias", "provider", "default_model"],
        )
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("models", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(gw)


def _routing(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Task-type → model-alias routing table (read-only here; the Web UI
    exposes the write path through /api/models/routing)."""
    try:
        from cyberai.orchestrator.routing.model_router import ModelRouter
        mr = ModelRouter()
        routes = mr.get_all_routes()
        rows = [{"task_type": k, "model_alias": v} for k, v in routes.items()]
        return CommandResult.success(
            "models-routing", data={"routes": routes},
            rows=rows, columns=["task_type", "model_alias"],
        )
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("models-routing", f"{type(e).__name__}: {e}")


def register(registry) -> None:
    from cyberai.commands.models import CommandSpec
    registry.register(CommandSpec(
        name="models", category="operations", description="List the model registry",
        handler=_models, aliases=["m"],
        usage="models",
    ))
    registry.register(CommandSpec(
        name="routing", category="operations", description="Show task-type → model routing",
        handler=_routing, usage="routing",
    ))
