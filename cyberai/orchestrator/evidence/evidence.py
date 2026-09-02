"""
Evidence Manager for the Cyber AI Orchestrator.

Manages collection, storage, and retrieval of evidence from tool executions.
Evidence is stored in lab/evidence/ and also logged to session logs.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.config import config

logger = logging.getLogger(__name__)

EVIDENCE_DIR = config.get_path("evidence", "dir", "lab/evidence")


class EvidenceManager:
    """
    Manages evidence collection and storage.

    Evidence can be of various types:
    - scan_output: Raw scanner output
    - tool_response: Tool API response
    - file_content: File contents from target
    - screenshot: Screenshot of web page
    - network_capture: PCAP or network traffic
    - manual_note: Manually taken notes
    """

    EVIDENCE_TYPES = [
        "scan_output",
        "tool_response",
        "file_content",
        "screenshot",
        "network_capture",
        "manual_note",
    ]

    def __init__(self, evidence_dir: Optional[Path] = None):
        self.evidence_dir = evidence_dir or EVIDENCE_DIR
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        # Create .gitkeep
        (self.evidence_dir / ".gitkeep").touch(exist_ok=True)

    def store_evidence(
        self,
        session_id: str,
        evidence_type: str,
        content: Any,
        source: str = "unknown",
        verification_status: str = "UNVERIFIED",
        confidence: float = 0.0,
        timestamp: Optional[str] = None,
    ) -> str:
        """
        Store an evidence item.

        Args:
            session_id: The session this evidence belongs to
            evidence_type: Type of evidence (scan_output, tool_response, etc.)
            content: The evidence content
            source: Source tool or agent
            verification_status: UNVERIFIED, LIKELY, VERIFIED, REJECTED
            confidence: Confidence level (0.0-1.0)
            timestamp: ISO timestamp (defaults to now)

        Returns:
            Evidence ID (hash-based)
        """
        if evidence_type not in self.EVIDENCE_TYPES:
            logger.warning(f"Unknown evidence type: {evidence_type}")

        now = timestamp or datetime.now(timezone.utc).isoformat()

        # Serialize content for hashing
        content_str = json.dumps(content, default=str, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]

        evidence_id = f"{session_id[:8]}_{evidence_type}_{content_hash}"

        evidence_record = {
            "id": evidence_id,
            "session_id": session_id,
            "type": evidence_type,
            "source": source,
            "verification_status": verification_status,
            "confidence": confidence,
            "timestamp": now,
            "content": content,
        }

        # Save to file
        evidence_path = self.evidence_dir / f"{evidence_id}.json"
        with open(evidence_path, "w") as f:
            json.dump(evidence_record, f, indent=2, default=str)

        logger.info(f"Stored evidence {evidence_id} (type: {evidence_type})")
        return evidence_id

    def get_evidence(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve evidence by ID."""
        evidence_path = self.evidence_dir / f"{evidence_id}.json"
        if evidence_path.exists():
            with open(evidence_path) as f:
                return json.load(f)
        return None

    def list_evidence(self, session_id: str) -> List[Dict[str, Any]]:
        """List all evidence for a session."""
        results = []
        for f in self.evidence_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                if data.get("session_id") == session_id:
                    results.append(data)
            except Exception:
                continue
        return sorted(results, key=lambda x: x.get("timestamp", ""))

    def update_verification_status(self, evidence_id: str, status: str, confidence: float = None) -> bool:
        """Update the verification status of an evidence item."""
        evidence_path = self.evidence_dir / f"{evidence_id}.json"
        if not evidence_path.exists():
            return False

        with open(evidence_path) as f:
            data = json.load(f)

        data["verification_status"] = status
        if confidence is not None:
            data["confidence"] = confidence

        with open(evidence_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return True
