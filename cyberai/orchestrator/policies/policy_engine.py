"""
Policy Engine for the Cyber AI Orchestrator.

Enforces the authorized lab boundary. All execution targets must be
explicitly registered and authorized before any active testing is allowed.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.config import config, validate_targets_file

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    Enforces execution policies.

    The default policy requires a target to be explicitly registered
    in the lab targets file before any active testing is permitted.
    """

    def __init__(self, targets_path: Optional[Path] = None):
        self.targets_path = targets_path or config.get_path(
            "policy", "targets_path", "lab/targets/targets.yaml"
        )
        self._targets: Dict[str, Dict[str, Any]] = {}
        self._load_targets()

    def _load_targets(self) -> None:
        """Load and validate authorized targets from the targets file."""
        if not self.targets_path.exists():
            raise FileNotFoundError(
                f"Targets file not found at {self.targets_path}. "
                "Create lab/targets/targets.yaml or set LAB_TARGETS_PATH."
            )
        try:
            # Central validation: fails fast with a clear error on
            # missing/invalid required fields (id, environment, allowed).
            targets = validate_targets_file(self.targets_path)
        except Exception as e:
            raise ValueError(f"Invalid targets file {self.targets_path}: {e}") from e
        for t in targets:
            target_id = t.get("id", "")
            if target_id:
                self._targets[target_id] = t
        logger.info("Loaded %d authorized targets", len(self._targets))

    def is_authorized(self, target_id: str) -> bool:
        """
        Check if a target is registered and authorized.

        Args:
            target_id: The target identifier

        Returns:
            True if the target is authorized for active testing
        """
        target = self._targets.get(target_id)
        if not target:
            return False
        return target.get("allowed", False) is True

    def get_target(self, target_id: str) -> Optional[Dict[str, Any]]:
        """Get target info by ID."""
        return self._targets.get(target_id)

    def list_targets(self) -> List[Dict[str, Any]]:
        """List all registered targets."""
        return list(self._targets.values())

    def list_authorized_targets(self) -> List[Dict[str, Any]]:
        """List only authorized targets."""
        return [t for t in self._targets.values() if t.get("allowed", False)]

    def check_action_allowed(self, target_id: str, action: str) -> bool:
        """
        Check if a specific action is allowed on a target.

        Args:
            target_id: The target identifier
            action: The action to perform (e.g., "scan", "exploit")

        Returns:
            True if the action is permitted
        """
        if not self.is_authorized(target_id):
            return False

        target = self._targets[target_id]
        allowed_actions = target.get("allowed_actions", ["scan", "recon", "analysis"])

        # If no specific actions listed, allow only passive actions
        if not allowed_actions:
            return action in ["recon", "analysis"]

        return action in allowed_actions

    def register_target(self, target: Dict[str, Any]) -> None:
        """
        Register a new target.

        Args:
            target: Dict with id, environment, allowed, etc.
        """
        target_id = target.get("id", "")
        if not target_id:
            raise ValueError("Target must have an 'id' field")

        self._targets[target_id] = target
        self._save_targets()
        logger.info(f"Registered target {target_id}")

    def _save_targets(self) -> None:
        """Save targets back to the YAML file."""
        import yaml

        self.targets_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"targets": list(self._targets.values())}
        with open(self.targets_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def close(self) -> None:
        """Clean up resources (no-op for PolicyEngine — file-based)."""
        pass
