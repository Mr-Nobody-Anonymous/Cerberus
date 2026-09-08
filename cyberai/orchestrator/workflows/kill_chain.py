"""
F2T2EA Kill Chain Engine for the Cyber AI Orchestrator.

Implements the full Find → Fix → Track → Target → Engage → Assess
state machine described in the README:

- Phase timeout and success/failure tracking per target
- Concurrent multi-target engagement coordination
- Verification states: UNVERIFIED → LIKELY → VERIFIED or REJECTED
- Failure memory integration (ghost wargaming avoidance)

The engine is deliberately self-contained: it persists state to a JSON
file under lab/state/ so kill chains survive restarts, and it records
failures into the MemoryStore so evolved strategies can avoid them.
"""

import json
import logging
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from cyberai.config import WORKSPACE_ROOT

logger = logging.getLogger(__name__)

# Default phase timeouts (seconds). A target stuck in a phase longer
# than this is marked TIMED_OUT and the chain moves on (or aborts).
DEFAULT_PHASE_TIMEOUTS = {
    "FIND": 600.0,
    "FIX": 300.0,
    "TRACK": 600.0,
    "TARGET": 300.0,
    "ENGAGE": 900.0,
    "ASSESS": 300.0,
}

PHASE_ORDER = ["FIND", "FIX", "TRACK", "TARGET", "ENGAGE", "ASSESS"]


class Phase(str, Enum):
    FIND = "FIND"
    FIX = "FIX"
    TRACK = "TRACK"
    TARGET = "TARGET"
    ENGAGE = "ENGAGE"
    ASSESS = "ASSESS"


class PhaseStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class Verification(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    LIKELY = "LIKELY"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class KillChainError(Exception):
    """Raised for invalid kill-chain transitions."""


class TargetChain:
    """One target's progress through the F2T2EA phases."""

    def __init__(self, target: str, chain_id: Optional[str] = None):
        self.chain_id = chain_id or uuid.uuid4().hex[:8]
        self.target = target
        self.created_at = time.time()
        self.updated_at = self.created_at
        self.current_phase: Phase = Phase.FIND
        self.phase_status: Dict[str, str] = {p: PhaseStatus.PENDING.value for p in PHASE_ORDER}
        self.phase_status[Phase.FIND.value] = PhaseStatus.ACTIVE.value
        self.phase_started: Dict[str, float] = {Phase.FIND.value: self.created_at}
        self.phase_ended: Dict[str, float] = {}
        self.phase_notes: Dict[str, str] = {}
        self.verification: str = Verification.UNVERIFIED.value
        self.findings: List[Dict[str, Any]] = []
        self.status: str = "ACTIVE"  # ACTIVE | COMPLETE | ABORTED
        self.error: Optional[str] = None

    # -- transitions ------------------------------------------------------

    def _require_active(self, phase: Phase) -> None:
        if self.status != "ACTIVE":
            raise KillChainError(f"chain for {self.target} is {self.status}")
        if self.current_phase != phase:
            raise KillChainError(
                f"{self.target}: current phase is {self.current_phase.value}, not {phase.value}")
        if self.phase_status.get(phase.value) != PhaseStatus.ACTIVE.value:
            raise KillChainError(f"phase {phase.value} is {self.phase_status.get(phase.value)}")

    def advance(self, note: str = "", finding: Optional[Dict[str, Any]] = None) -> Phase:
        """Mark the current phase COMPLETE and move to the next phase."""
        phase = self.current_phase
        self._require_active(phase)
        now = time.time()
        self.phase_status[phase.value] = PhaseStatus.COMPLETE.value
        self.phase_ended[phase.value] = now
        if note:
            self.phase_notes[phase.value] = note
        if finding:
            self.findings.append({**finding, "phase": phase.value, "ts": now})
        idx = PHASE_ORDER.index(phase.value)
        if idx + 1 < len(PHASE_ORDER):
            self.current_phase = Phase(PHASE_ORDER[idx + 1])
            self.phase_status[self.current_phase.value] = PhaseStatus.ACTIVE.value
            self.phase_started[self.current_phase.value] = now
        else:
            self.status = "COMPLETE"
            self._promote_verification()
        self.updated_at = now
        return self.current_phase

    def fail(self, reason: str, category: str = "execution",
             abort: bool = True) -> None:
        """Mark the current phase FAILED; abort the chain by default."""
        phase = self.current_phase
        self._require_active(phase)
        now = time.time()
        self.phase_status[phase.value] = PhaseStatus.FAILED.value
        self.phase_ended[phase.value] = now
        self.phase_notes[phase.value] = reason
        self.error = reason
        if abort:
            self.status = "ABORTED"
        self.updated_at = now

    def timeout_phase(self, phase: Optional[Phase] = None) -> bool:
        """Mark a phase TIMED_OUT if it exceeded its timeout. Returns True if timed out."""
        phase = phase or self.current_phase
        if self.phase_status.get(phase.value) != PhaseStatus.ACTIVE.value:
            return False
        started = self.phase_started.get(phase.value)
        if started is None:
            return False
        elapsed = time.time() - started
        limit = DEFAULT_PHASE_TIMEOUTS.get(phase.value, 600.0)
        if elapsed > limit:
            now = time.time()
            self.phase_status[phase.value] = PhaseStatus.TIMED_OUT.value
            self.phase_ended[phase.value] = now
            self.phase_notes[phase.value] = f"timed out after {elapsed:.0f}s (limit {limit:.0f}s)"
            self.error = self.phase_notes[phase.value]
            self.status = "ABORTED"
            self.updated_at = now
            return True
        return False

    def _promote_verification(self) -> None:
        """On completion, promote verification based on findings."""
        verified = [f for f in self.findings if f.get("verification") == Verification.VERIFIED.value]
        rejected = [f for f in self.findings if f.get("verification") == Verification.REJECTED.value]
        if verified:
            self.verification = Verification.VERIFIED.value
        elif rejected and not any(
            f.get("verification") in (Verification.LIKELY.value, Verification.UNVERIFIED.value)
            for f in self.findings
        ):
            self.verification = Verification.REJECTED.value
        elif any(f.get("verification") == Verification.LIKELY.value for f in self.findings):
            self.verification = Verification.LIKELY.value

    # -- serialization ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "target": self.target,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "current_phase": self.current_phase.value,
            "phase_status": self.phase_status,
            "phase_started": self.phase_started,
            "phase_ended": self.phase_ended,
            "phase_notes": self.phase_notes,
            "verification": self.verification,
            "findings": self.findings,
            "status": self.status,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TargetChain":
        c = cls.__new__(cls)
        c.chain_id = d["chain_id"]
        c.target = d["target"]
        c.created_at = d["created_at"]
        c.updated_at = d["updated_at"]
        c.current_phase = Phase(d["current_phase"])
        c.phase_status = d["phase_status"]
        c.phase_started = d["phase_started"]
        c.phase_ended = d["phase_ended"]
        c.phase_notes = d.get("phase_notes", {})
        c.verification = d.get("verification", Verification.UNVERIFIED.value)
        c.findings = d.get("findings", [])
        c.status = d.get("status", "ACTIVE")
        c.error = d.get("error")
        return c


class KillChainEngine:
    """Coordinates F2T2EA chains across multiple targets concurrently."""

    def __init__(self, state_path: Optional[Path] = None,
                 memory_store: Optional[Any] = None):
        # lab/state/kill_chains.json — workspace resource
        self.state_path = state_path or WORKSPACE_ROOT / "lab" / "state" / "kill_chains.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._chains: Dict[str, TargetChain] = {}  # keyed by target
        self._load()
        # Optional MemoryStore for ghost-wargaming failure recording
        self._memory = memory_store

    # -- persistence ------------------------------------------------------

    def _load(self) -> None:
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                for d in data.get("chains", []):
                    c = TargetChain.from_dict(d)
                    self._chains[c.target] = c
                logger.info(f"Loaded {len(self._chains)} kill chains")
            except Exception as e:
                logger.warning(f"Failed to load kill chain state: {e}")

    def _save(self) -> None:
        data = {"chains": [c.to_dict() for c in self._chains.values()]}
        self.state_path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8")

    # -- chain lifecycle ---------------------------------------------------

    def start_chain(self, target: str) -> TargetChain:
        """Start (or resume) a kill chain for a target."""
        if target in self._chains:
            chain = self._chains[target]
            if chain.status == "ACTIVE":
                return chain  # resume
            # completed/aborted → restart fresh
        chain = TargetChain(target)
        self._chains[target] = chain
        self._save()
        logger.info(f"Kill chain {chain.chain_id} started for {target}")
        return chain

    def get_chain(self, target: str) -> Optional[TargetChain]:
        return self._chains.get(target)

    def list_chains(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._chains.values()]

    def advance(self, target: str, note: str = "",
                finding: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Advance a target's chain to the next F2T2EA phase."""
        chain = self._chains.get(target)
        if chain is None:
            raise KillChainError(f"no active chain for {target}")
        try:
            chain.advance(note=note, finding=finding)
        except KillChainError as e:
            self._record_failure_memory(chain, str(e), "transition")
            raise
        self._save()
        return chain.to_dict()

    def fail(self, target: str, reason: str, category: str = "execution") -> Dict[str, Any]:
        """Fail the current phase for a target and abort its chain."""
        chain = self._chains.get(target)
        if chain is None:
            raise KillChainError(f"no active chain for {target}")
        chain.fail(reason=reason, category=category)
        self._record_failure_memory(chain, reason, category)
        self._save()
        return chain.to_dict()

    def check_timeouts(self) -> List[Dict[str, Any]]:
        """Check all ACTIVE chains for phase timeouts. Returns timed-out chains."""
        timed_out = []
        for chain in self._chains.values():
            if chain.status == "ACTIVE" and chain.timeout_phase():
                timed_out.append(chain.to_dict())
                self._record_failure_memory(
                    chain, chain.error or "phase timeout", "timeout")
        if timed_out:
            self._save()
        return timed_out

    # -- ghost wargaming integration ----------------------------------------

    def _record_failure_memory(self, chain: TargetChain, reason: str,
                               category: str) -> None:
        """Record a failure into the MemoryStore for future avoidance."""
        if self._memory is None:
            return
        try:
            self._memory.record_failure(
                strategy_id=f"killchain-{chain.chain_id}",
                reason=reason,
                failure_category=category,
                tool="kill-chain-engine",
                agent="orchestrator",
            )
        except Exception as e:
            logger.warning(f"Failed to record failure memory: {e}")

    # -- reporting -----------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Aggregate status across all chains."""
        active = [c for c in self._chains.values() if c.status == "ACTIVE"]
        complete = [c for c in self._chains.values() if c.status == "COMPLETE"]
        aborted = [c for c in self._chains.values() if c.status == "ABORTED"]
        by_phase: Dict[str, int] = {}
        for c in active:
            by_phase[c.current_phase.value] = by_phase.get(c.current_phase.value, 0) + 1
        return {
            "total": len(self._chains),
            "active": len(active),
            "complete": len(complete),
            "aborted": len(aborted),
            "active_by_phase": by_phase,
            "chains": [c.to_dict() for c in self._chains.values()],
        }

    def reset(self) -> None:
        """Drop all chain state (fresh start)."""
        self._chains.clear()
        self._save()
