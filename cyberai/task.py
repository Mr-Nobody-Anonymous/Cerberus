"""
Canonical Task state for the Cyber AI orchestrator.
Every component works against this shared state object.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class TaskStatus(Enum):
    CREATED = "created"
    PLANNING = "planning"
    PLAN_READY = "plan_ready"
    EXECUTING = "executing"
    WAITING_VERIFICATION = "waiting_verification"
    VERIFIED = "verified"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VerificationState(Enum):
    UNVERIFIED = "UNVERIFIED"
    LIKELY = "LIKELY"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


@dataclass
class Task:
    """Canonical shared task state."""

    objective: str
    scope: str = "authorized_lab"
    environment: str = "authorized_lab"
    authorization: str = "pending"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = TaskStatus.CREATED.value
    plan: List[Dict[str, Any]] = field(default_factory=list)
    observations: List[Dict[str, Any]] = field(default_factory=list)
    hypotheses: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    agents_used: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    models_used: List[str] = field(default_factory=list)
    verification: List[Dict[str, Any]] = field(default_factory=list)
    memory_references: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    timestamps: Dict[str, str] = field(default_factory=lambda: {
        "created": datetime.now(timezone.utc).isoformat(),
    })
    metadata: Dict[str, Any] = field(default_factory=dict)
    final_report: Optional[Dict[str, Any]] = None

    def set_status(self, status: TaskStatus) -> None:
        self.status = status.value
        self.timestamps[f"status_{status.value}"] = datetime.now(timezone.utc).isoformat()

    def is_terminal(self) -> bool:
        return self.status in (
            TaskStatus.COMPLETED.value,
            TaskStatus.FAILED.value,
            TaskStatus.CANCELLED.value,
        )

    def add_plan_step(self, action: str, capability: str, description: str = "",
                      agent: str = "", tool: str = "", model: str = "",
                      expected_evidence: str = "") -> Dict[str, Any]:
        step = {
            "id": str(uuid.uuid4()),
            "step": len(self.plan) + 1,
            "action": action,
            "capability": capability,
            "description": description,
            "agent": agent,
            "tool": tool,
            "model": model,
            "expected_evidence": expected_evidence,
            "status": "planned",
            "result": None,
            "observations": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.plan.append(step)
        return step

    def update_plan_step(self, step_id: str, **updates: Any) -> None:
        for step in self.plan:
            if step["id"] == step_id:
                step.update(updates)
                step["timestamp"] = datetime.now(timezone.utc).isoformat()
                return

    def add_observation(self, content: str, source: str = "", confidence: float = 0.0,
                        evidence: Optional[List[str]] = None,
                        verification: str = VerificationState.UNVERIFIED.value) -> Dict[str, Any]:
        obs = {
            "id": str(uuid.uuid4()),
            "content": content,
            "source": source,
            "confidence": confidence,
            "evidence": evidence or [],
            "verification": verification,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.observations.append(obs)
        return obs

    def add_hypothesis(self, statement: str, confidence: float = 0.0,
                       supporting_observations: Optional[List[str]] = None,
                       verification: str = VerificationState.UNVERIFIED.value) -> Dict[str, Any]:
        hyp = {
            "id": str(uuid.uuid4()),
            "statement": statement,
            "confidence": confidence,
            "supporting_observations": supporting_observations or [],
            "verification": verification,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.hypotheses.append(hyp)
        return hyp

    def add_action(self, action: str, tool: str, agent: str = "", model: str = "",
                   parameters: Optional[Dict[str, Any]] = None,
                   result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        act = {
            "id": str(uuid.uuid4()),
            "action": action,
            "tool": tool,
            "agent": agent,
            "model": model,
            "parameters": parameters or {},
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.actions.append(act)
        if tool not in self.tools_used:
            self.tools_used.append(tool)
        if agent and agent not in self.agents_used:
            self.agents_used.append(agent)
        if model and model not in self.models_used:
            self.models_used.append(model)
        return act

    def add_evidence(self, content: str, source: str = "", evidence_type: str = "observation",
                     hash: str = "", confidence: float = 0.0) -> Dict[str, Any]:
        import hashlib
        ev = {
            "id": str(uuid.uuid4()),
            "content": content,
            "source": source,
            "type": evidence_type,
            "hash": hash or hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.evidence.append(ev)
        return ev

    def add_finding(self, description: str, confidence: float = 0.0,
                    evidence_ids: Optional[List[str]] = None, source: str = "",
                    verification: str = VerificationState.UNVERIFIED.value) -> Dict[str, Any]:
        finding = {
            "id": str(uuid.uuid4()),
            "description": description,
            "confidence": confidence,
            "evidence_ids": evidence_ids or [],
            "source": source,
            "verification": verification,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.findings.append(finding)
        return finding

    def update_finding_verification(self, finding_id: str, verification: str) -> None:
        for finding in self.findings:
            if finding["id"] == finding_id:
                finding["verification"] = verification
                return

    def add_error(self, component: str, message: str, details: str = "") -> None:
        self.errors.append({
            "component": component,
            "message": message,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "objective": self.objective,
            "scope": self.scope,
            "environment": self.environment,
            "authorization": self.authorization,
            "status": self.status,
            "plan": self.plan,
            "observations": self.observations,
            "hypotheses": self.hypotheses,
            "actions": self.actions,
            "evidence": self.evidence,
            "findings": self.findings,
            "agents_used": self.agents_used,
            "tools_used": self.tools_used,
            "models_used": self.models_used,
            "verification": self.verification,
            "memory_references": self.memory_references,
            "errors": self.errors,
            "timestamps": self.timestamps,
            "metadata": self.metadata,
            "final_report": self.final_report,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        task = cls(
            objective=data["objective"],
            scope=data.get("scope", "authorized_lab"),
            environment=data.get("environment", "authorized_lab"),
            authorization=data.get("authorization", "pending"),
            id=data.get("id", str(uuid.uuid4())),
            status=data.get("status", TaskStatus.CREATED.value),
        )
        task.plan = data.get("plan", [])
        task.observations = data.get("observations", [])
        task.hypotheses = data.get("hypotheses", [])
        task.actions = data.get("actions", [])
        task.evidence = data.get("evidence", [])
        task.findings = data.get("findings", [])
        task.agents_used = data.get("agents_used", [])
        task.tools_used = data.get("tools_used", [])
        task.models_used = data.get("models_used", [])
        task.verification = data.get("verification", [])
        task.memory_references = data.get("memory_references", [])
        task.errors = data.get("errors", [])
        task.timestamps = data.get("timestamps", {"created": datetime.now(timezone.utc).isoformat()})
        task.metadata = data.get("metadata", {})
        task.final_report = data.get("final_report")
        return task