"""Memory commands: /memory (search + stats)."""

from cyberai.commands.context import CommandContext
from cyberai.commands.models import CommandResult, ParsedCommand


def _memory(ctx: CommandContext, parsed: ParsedCommand) -> CommandResult:
    """Semantic memory search; no query → stats overview."""
    store = None
    try:
        store = ctx.memory_store()
        q = " ".join(parsed.args) or parsed.kwarg("q", "")
        if not q.strip():
            stats = store.get_stats()
            return CommandResult.success("memory", data={"stats": stats})
        limit = int(parsed.kwarg("limit", "20"))
        results = store.semantic_search(q.strip(), limit=limit)
        return CommandResult.success(
            "memory", data={"results": results, "query": q},
            rows=results, columns=["id", "kind", "summary"],
        )
    except Exception as e:  # noqa: BLE001
        return CommandResult.failure("memory", f"{type(e).__name__}: {e}")
    finally:
        ctx.close_resource(store)


def register(registry) -> None:
    from cyberai.commands.models import CommandSpec
    registry.register(CommandSpec(
        name="memory", category="history", description="Search long-term memory (or stats)",
        handler=_memory, aliases=["mem"],
        usage="memory <query> | memory",
        examples=["memory sql injection", "memory"],
    ))
