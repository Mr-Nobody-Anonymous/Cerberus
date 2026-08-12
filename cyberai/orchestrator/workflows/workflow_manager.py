"""
Workflow Manager for the Cyber AI Orchestrator.

Defines reusable assessment workflows that coordinate multiple agents
and tools in a specific sequence.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Predefined workflows
PREDEFINED_WORKFLOWS = {
    "recon_to_report": {
        "name": "Reconnaissance to Report",
        "description": "Full assessment: recon -> analysis -> verification -> report",
        "steps": [
            {"agent": "researcher", "action": "research", "task_type": "vulnerability_research"},
            {"agent": "recon", "action": "recon", "task_type": "web_research"},
            {"agent": "analyst", "action": "analysis", "task_type": "reasoning"},
            {"agent": "verifier", "action": "verification", "task_type": "verification"},
            {"agent": "reporter", "action": "reporting", "task_type": "report_generation"},
        ],
    },
    "code_audit": {
        "name": "Code Security Audit",
        "description": "Static analysis: code review -> vulnerability analysis -> report",
        "steps": [
            {"agent": "coder", "action": "code_analysis", "task_type": "sensitive_source_code"},
            {"agent": "analyst", "action": "analysis", "task_type": "reasoning"},
            {"agent": "verifier", "action": "verification", "task_type": "verification"},
            {"agent": "reporter", "action": "reporting", "task_type": "report_generation"},
        ],
    },
    "target_assessment": {
        "name": "Target Assessment",
        "description": "Targeted assessment with planning, recon, and verification",
        "steps": [
            {"agent": "planner", "action": "planning", "task_type": "planning"},
            {"agent": "researcher", "action": "research", "task_type": "vulnerability_research"},
            {"agent": "recon", "action": "recon", "task_type": "web_research"},
            {"agent": "analyst", "action": "analysis", "task_type": "reasoning"},
            {"agent": "verifier", "action": "verification", "task_type": "verification"},
            {"agent": "reporter", "action": "reporting", "task_type": "report_generation"},
        ],
    },
}


class WorkflowManager:
    """Manages workflow definitions and execution."""

    def __init__(self):
        self._workflows: Dict[str, Dict[str, Any]] = dict(PREDEFINED_WORKFLOWS)

    def list_workflows(self) -> List[str]:
        """Return names of all available workflows."""
        return sorted(self._workflows.keys())

    def get_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        """Get workflow definition by name."""
        return self._workflows.get(name)

    def get_workflow_steps(self, name: str) -> List[Dict[str, Any]]:
        """Get the steps for a named workflow."""
        wf = self._workflows.get(name)
        if wf:
            return wf["steps"]
        return []

    def register_workflow(self, name: str, definition: Dict[str, Any]) -> None:
        """Register a custom workflow."""
        self._workflows[name] = definition
        logger.info(f"Registered workflow: {name}")
