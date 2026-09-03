"""Policy gate + evidence recording for adapter execution.

The single chokepoint through which EVERY adapter ``execute()`` call MUST
pass. There is no bypass path:

1. Authorize the target + action with the policy engine (fails closed).
2. Record the action (tool, target, timestamp, actor) to the evidence log
   EVEN ON FAILURE — this is non-negotiable for chain of custody.

Adapters that do not inherit :class:`SandboxedAdapter` (in
``orchestrator/adapters/base.py``) still go through this gate via
``AdapterManager.execute``, which calls :func:`authorize_and_record` first.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .exceptions import PolicyDeniedError

logger = logging.getLogger(__name__)

# Actor identifier for orchestrator-initiated actions.
ACTOR_CERBERUS = "cerberus:orchestrator"


def authorize(
    policy_engine: Any,
    target: Dict[str, Any],
    action: str,
) -> None:
    """
    Authorize an action against a target. Fails CLOSED.

    Only targets explicitly marked ``allowed: true`` in
    ``lab/targets/targets.yaml`` may be actively tested, and only actions
    listed in the target's ``allowed_actions`` are permitted.

    Args:
        policy_engine: the PolicyEngine instance
        target: target info dict (must contain at least ``id``)
        action: the action to perform (e.g. ``"scan"``, ``"recon"``)

    Raises:
        PolicyDeniedError: if the target is not authorized or the action
            is not whitelisted. The action is NOT performed.
    """
    target_id = (target or {}).get("id") if isinstance(target, dict) else None

    if not target_id:
        raise PolicyDeniedError(
            f"Action '{action}' denied: no target id supplied"
        )

    if not policy_engine.is_authorized(target_id):
        raise PolicyDeniedError(
            f"Action '{action}' denied: target '{target_id}' is not "
            "authorized (allowed:true in lab/targets/targets.yaml required)"
        )

    if not policy_engine.check_action_allowed(target_id, action):
        raise PolicyDeniedError(
            f"Action '{action}' denied: not in allowed_actions for "
            f"target '{target_id}'"
        )


def record_action(
    evidence_manager: Any,
    *,
    session_id: str,
    tool: str,
    target: Dict[str, Any],
    action: str,
    success: bool,
    output: Any = None,
    error: Optional[str] = None,
) -> str:
    """
    Record an action to the evidence log. Called for EVERY adapter action,
    including failures, so the audit trail is complete.

    Returns the evidence id.
    """
    target_id = (target or {}).get("id", "") if isinstance(target, dict) else ""
    content: Dict[str, Any] = {
        "tool": tool,
        "target_id": target_id,
        "action": action,
        "actor": ACTOR_CERBERUS,
        "success": success,
        "output": _safe_truncate(output),
        "error": error,
    }
    evidence_id = evidence_manager.store_evidence(
        session_id=session_id,
        evidence_type="tool_response" if success else "manual_note",
        content=content,
        source=tool,
        verification_status="UNVERIFIED",
        confidence=1.0 if success else 0.0,
    )
    logger.info(
        "Recorded action: tool=%s target=%s action=%s success=%s evidence=%s",
        tool, target_id, action, success, evidence_id,
    )
    return evidence_id


def _safe_truncate(value: Any, limit: int = 4000) -> Any:
    """Truncate large outputs so evidence records stay bounded."""
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + f"\n... [truncated, {len(value)} chars total]"
    return value
