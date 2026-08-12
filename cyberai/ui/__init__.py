"""
CERBERUS — Human-facing Command Deck UI.

The web cockpit presents the entire multi-agent platform as ONE unified AI.
It talks to the single CyberAIOrchestrator facade and streams every agent,
phase, and finding live over Server-Sent-Events.

Run standalone:
    python -m cyberai.ui.server
    # then open http://127.0.0.1:8710

Or launch everything with:
    python start_cerberus.py
"""

from cyberai.ui.server import app, EVENT_BUS, LiveEventBus

__all__ = ["app", "EVENT_BUS", "LiveEventBus"]
__version__ = "2.0.0"
