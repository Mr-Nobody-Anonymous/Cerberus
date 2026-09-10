"""CLI theme — Rich colors matching the CERBERUS web UI tokens.

The web UI (src/styles/tokens.ts) defines a dark cyber palette; this module
mirrors it for the terminal so both surfaces feel like one product.
"""

from rich.theme import Theme

# Core palette (kept in sync with src/styles/tokens.ts)
BG = "#0b0e14"
BG2 = "#11151d"
FG = "#d7dae0"
DIM = "#8b93a1"
ACCENT = "#4cc9f0"
GREEN = "#4ade80"
YELLOW = "#fbbf24"
RED = "#f87171"
PURPLE = "#c084fc"
ORANGE = "#fb923c"

CERBERUS_THEME = Theme({
    "cb.bg": BG,
    "cb.fg": FG,
    "cb.dim": DIM,
    "cb.accent": ACCENT,
    "cb.green": GREEN,
    "cb.yellow": YELLOW,
    "cb.red": RED,
    "cb.purple": PURPLE,
    "cb.orange": ORANGE,
    "cb.banner": ACCENT,
    "cb.prompt": GREEN,
    "cb.ok": GREEN,
    "cb.warn": YELLOW,
    "cb.err": RED,
    "cb.info": ACCENT,
    "cb.muted": DIM,
    "cb.header": "bold " + ACCENT,
    "cb.sub": DIM,
    "cb.mono": FG,
    "cb.pill.ok": "on " + BG2 + " " + GREEN,
    "cb.pill.warn": "on " + BG2 + " " + YELLOW,
    "cb.pill.err": "on " + BG2 + " " + RED,
    "cb.pill.info": "on " + BG2 + " " + ACCENT,
})

# State → style mapping (mirrors web UI stateTone)
STATE_STYLES = {
    "ACTIVE": "cb.green",
    "RUNNING": "cb.green",
    "VERIFIED": "cb.green",
    "HEALTHY": "cb.green",
    "ONLINE": "cb.green",
    "OK": "cb.green",
    "OFFLINE": "cb.yellow",
    "UNVERIFIED": "cb.yellow",
    "LIKELY": "cb.yellow",
    "DEGRADED": "cb.yellow",
    "WARN": "cb.yellow",
    "STARTING": "cb.yellow",
    "UNAUTHORIZED": "cb.red",
    "REJECTED": "cb.red",
    "FAILED": "cb.red",
    "ERROR": "cb.red",
    "DENIED": "cb.red",
    "BLOCKED": "cb.red",
    "PENDING": "cb.dim",
    "UNKNOWN": "cb.dim",
}


def state_style(state: str) -> str:
    """Map a state string to a Rich style tag."""
    return STATE_STYLES.get((state or "").upper(), "cb.dim")


BANNER = r"""
   ___ _____ ___ ___ _  _ ___ _  _ ___
  / __|_   _| __| _ ) \| | __| \| | __|
 | (__  | | | _|| _ ) .` | _|| .` | _|
  \___| |_| |___|___|_|\_|___|_|\_|___|
  AI Cyber-Security IDE — operator console
"""
