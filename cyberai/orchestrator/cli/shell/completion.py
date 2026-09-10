"""Completion — slash-command completer for the interactive console.

Uses prompt_toolkit when available (history, fuzzy completion, mouse-free
navigation); the console degrades to plain input() otherwise.
"""

from typing import Iterable, List, Optional


def command_names() -> List[str]:
    """All visible command names + aliases from the shared registry."""
    from cyberai.commands import load_builtin_commands
    reg = load_builtin_commands()
    names: List[str] = []
    for spec in reg.specs():
        if spec.hidden:
            continue
        names.append(f"/{spec.name}")
        names.extend(f"/{a}" for a in spec.aliases)
    return sorted(set(names))


def command_completions(fragment: str) -> List[str]:
    """Simple prefix filter (used by the fallback completer)."""
    frag = fragment.lstrip("/").lower()
    return [n for n in command_names() if frag in n.lstrip("/").lower()]


def build_completer():
    """prompt_toolkit Completer over the command registry.

    Completes:
      - command names (with aliases) from '/'
      - key=value kwargs from each command's usage string
    """
    try:
        from prompt_toolkit.completion import Completer, CompleteEvent, Completion
        from prompt_toolkit.document import Document
    except ImportError:
        return None

    class SlashCompleter(Completer):
        def get_completions(self, document: Document,
                            event: CompleteEvent) -> Iterable[Completion]:
            text = document.text_before_cursor
            # Only complete at the start of a line (command position)
            if text.startswith("/"):
                word = document.get_word_before_cursor(WORD=True) or ""
                for name in command_names():
                    if name.startswith("/" + word.lstrip("/")):
                        yield Completion(name, start_position=-len(word))
            elif " " in text:
                # Suggest key=value kwargs for the active command
                parts = text.split(" ", 1)
                cmd = parts[0].lstrip("/")
                from cyberai.commands import load_builtin_commands
                spec = load_builtin_commands().command(cmd)
                if spec and spec.usage:
                    # crude: extract 'key' tokens from usage like 'findings status=…'
                    for tok in spec.usage.replace("[", " ").replace("]", " ").split():
                        if "=" in tok:
                            key = tok.split("=")[0]
                            frag = document.get_word_before_cursor(WORD=True)
                            if frag and not frag.startswith("-"):
                                yield Completion(f"{key}=", start_position=-len(frag))

    return SlashCompleter()


def build_history():
    """prompt_toolkit FileHistory backed by the user's state dir."""
    try:
        from pathlib import Path
        from prompt_toolkit.history import FileHistory
        hist_path = Path.home() / ".cerberus" / "cli_history"
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        return FileHistory(str(hist_path))
    except ImportError:
        return None
