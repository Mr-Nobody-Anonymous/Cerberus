"""
Session Logger for the Cyber AI Orchestrator.

Generates structured logs for every orchestration session.
Never logs API keys or secrets.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Patterns to redact from logs
SECRET_PATTERNS = [
    (re.compile(r"(api[_-]?key|token|secret|password|authorization)\s*[:=]\s*['\"]?([^'\",\s}]+)", re.IGNORECASE), r"\1=REDACTED"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), r"\1REDACTED"),
]


def redact_secrets(text: str) -> str:
    """Redact secrets from log output."""
    if not text:
        return text
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class SessionLogger:
    """
    Writes structured session logs to logs/sessions/<session_id>/.

    Structure:
        session.json       - Session metadata
        planner.jsonl      - Planning events
        tool_calls.jsonl   - Tool execution events
        model_calls.jsonl  - LLM call events
        findings.json      - Findings
        evidence/          - Evidence files
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).parent.parent.parent.parent / "logs" / "sessions"
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_session_dir(self, session_id: str) -> Path:
        """Create the log directory for a session."""
        session_dir = self.base_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "evidence").mkdir(exist_ok=True)
        return session_dir

    def write_session_meta(self, session_id: str, meta: Dict[str, Any]) -> None:
        """Write session metadata."""
        session_dir = self.create_session_dir(session_id)
        with open(session_dir / "session.json", "w") as f:
            json.dump(meta, f, indent=2)

    def log_event(self, session_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """
        Log an event to the appropriate JSONL file.

        Args:
            session_id: The session ID
            event_type: One of "planner", "tool_calls", "model_calls"
            data: Event data (secrets will be redacted)
        """
        session_dir = self.create_session_dir(session_id)
        filename = f"{event_type}.jsonl"

        # Redact secrets from string values
        clean_data = self._redact_dict(data)
        clean_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        with open(session_dir / filename, "a") as f:
            f.write(json.dumps(clean_data) + "\n")

    def write_findings(self, session_id: str, findings: List[Dict[str, Any]]) -> None:
        """Write findings to the session log."""
        session_dir = self.create_session_dir(session_id)
        with open(session_dir / "findings.json", "w") as f:
            json.dump(findings, f, indent=2)

    def save_evidence(self, session_id: str, evidence_id: str, content: Any) -> Path:
        """Save an evidence file."""
        session_dir = self.create_session_dir(session_id)
        evidence_path = session_dir / "evidence" / f"{evidence_id}.json"
        with open(evidence_path, "w") as f:
            json.dump(content, f, indent=2)
        return evidence_path

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact secrets from dict values."""
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = self._redact_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._redact_dict(v) if isinstance(v, dict) else redact_secrets(str(v))
                    for v in value
                ]
            elif isinstance(value, str):
                result[key] = redact_secrets(value)
            else:
                result[key] = value
        return result