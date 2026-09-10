"""Parser for slash-command syntax.

Grammar (whitespace-separated tokens):

    /name [positional...] [key=value ...]

- A leading ``/`` marks a command; anything else is natural language the
  host routes to the chat/mission surface.
- ``key=value`` tokens become kwargs; everything else stays positional.
- Values may be quoted: ``/run objective="scan the lab" target=lab-web-01``.
- An empty ``/`` or ``/`` + unknown name still parses (dispatcher reports
  the unknown command so hosts can offer suggestions).
"""

import shlex
from typing import List, Tuple

from cyberai.commands.models import ParsedCommand

_MAX_TOKENS = 64


def tokenize(raw: str) -> List[str]:
    """Split a raw line into tokens honoring double quotes."""
    raw = raw.strip()
    if not raw:
        return []
    try:
        return shlex.split(raw)[:_MAX_TOKENS]
    except ValueError:
        # Unbalanced quote — fall back to naive whitespace split.
        return raw.split()[:_MAX_TOKENS]


def _split_kv(token: str) -> Tuple[str, str] | None:
    if "=" not in token:
        return None
    key, _, value = token.partition("=")
    if not key or not value:
        return None
    return key, value


def parse_command(raw: str) -> ParsedCommand:
    """Parse one operator input line into a ParsedCommand."""
    tokens = tokenize(raw)
    if not tokens or not tokens[0].startswith("/"):
        return ParsedCommand(raw=raw, is_command=False)

    name = tokens[0][1:].lower()
    args: List[str] = []
    kwargs = {}
    for token in tokens[1:]:
        kv = _split_kv(token)
        if kv is not None:
            kwargs[kv[0]] = kv[1]
        else:
            args.append(token)
    return ParsedCommand(raw=raw, name=name, args=args, kwargs=kwargs,
                          is_command=True)


def suggestions(fragment: str, names: List[str], limit: int = 5) -> List[str]:
    """Prefix-match suggestions for autocomplete surfaces."""
    frag = fragment.lower().lstrip("/")
    if not frag:
        return []
    return [n for n in names if n.startswith(frag)][:limit]
