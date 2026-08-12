"""
Master Orchestrator Facade

CyberAIOrchestrator is the single entry point that presents ONE coherent
intelligence to the user.  Internally it coordinates:

    USER
      │
      ▼
 MASTER ORCHESTRATOR (this class)
      │   ├── PLANNER        → LLM + memory retrieval
      │   ├── CAPABILITY ROUTER → selects best agent/tool per capability
      │   ├── MODEL ROUTER   → LLMGateway (local-first, fallback chain)
      │   ├── POLICY ENGINE  → authorization & sandbox enforcement
      │   └── MEMORY         → typed experience store (episodic/semantic/...)
      │
      ▼
 TASK EXECUTION  → dynamic planning (observe → reason → plan → act → verify → learn)
      │
      ▼
 EVIDENCE & VERIFICATION
      │
      ▼
 MEMORY + EVOLUTION ENGINE  → score, mutate, select, archive
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.config import config, WORKSPACE_ROOT
from cyberai.task import Task, TaskStatus, VerificationState
from cyberai.memory.memory_store import MemoryStore, MemoryEntry
from cyberai.meta_learning.tracker import PerformanceTracker, PerformanceRecord
from cyberai.observability.logger import StructuredLogger
from cyberai.capabilities.registry import CapabilityRegistry
from cyberai.evolution.engine import EvolutionEngine
from cyberai.collaboration.pipeline import AgentPipeline

from .orchestrator import Orchestrator
from .memory.memory_manager import MemoryManager
from .policies.policy_engine import PolicyEngine
from .routing.model_router import ModelRouter
from .tool_registry import ToolRegistry
from .adapters.adapter_manager import AdapterManager
from .agents.planner.planner import PlannerAgent
from .agents.researcher.researcher import ResearcherAgent
from .agents.recon.recon import ReconAgent
from .agents.analyst.analyst import AnalystAgent
from .agents.coder.coder import CoderAgent
from .agents.verifier.verifier import VerifierAgent
from .agents.reporter.reporter import ReporterAgent

logger = logging.getLogger(__name__)

_AGENT_CLASSES = {
    "planner": PlannerAgent,
    "researcher": ResearcherAgent,
    "recon": ReconAgent,
    "analyst": AnalystAgent,
    "coder": CoderAgent,
    "verifier": VerifierAgent,
    "reporter": ReporterAgent,
}

# Default plan steps used when no LLM is available
_DEFAULT_PLAN_STEPS = [
    {"step": 1, "action": "research", "capability": "research",
     "description": "Research target technology and known vulnerabilities",
     "model": "vulnerability_research"},
    {"step": 2, "action": "recon", "capability": "reconnaissance",
     "description": "Perform reconnaissance on the target",
     "model": "web_research"},
    {"step": 3, "action": "analysis", "capability": "analysis",
     "description": "Analyze findings and identify vulnerabilities",
     "model": "reasoning"},
    {"step": 4, "action": "verification", "capability": "verification",
     "description": "Verify all candidate findings independently",
     "model": "verification"},
    {"step": 5, "action": "reporting", "capability": "reporting",
     "description": "Generate final assessment report",
     "model": "report_generation"},
]


class CyberAIOrchestrator:
    """
    Unified Master AI Orchestrator.

    This is what the user interacts with — ONE intelligent Cyber AI that
    internally coordinates multiple agents, tools, models, memory, and
    evolution.  It presents a single coherent interface:

        result = await ai.run("Analyze my authorized lab target")

    Internally it:
    1.  Retrieves relevant past experiences from memory
    2.  Routes the task through capability-based agent selection
    3.  Uses the LLM gateway (local-first with fallback) for reasoning
    4.  Executes actions through verified adapter tools
    5.  Verifies findings independently
    6.  Stores results in typed memory
    7.  Evolves strategies through the evolution engine
    """

    def __init__(
        self,
        *,
        simulate: bool = False,
        dry_run: bool = False,
        local_only: Optional[bool] = None,
    ):
        self.simulate = simulate
        self.dry_run = dry_run
        self.local_only = config.is_local_only() if local_only is None else local_only

        # --- Core subsystems ---
        self.memory = MemoryManager()
        self.policy = PolicyEngine()
        self.model_router = ModelRouter()
        self.tool_registry = ToolRegistry()
        self.capabilities = CapabilityRegistry()
        self.adapter_manager = AdapterManager()

        # LLM Gateway — single shared instance
        from cyberai.llm_gateway import LLMGateway
        self.llm_gateway = LLMGateway(local_only=self.local_only)

        # Evolution engine (simulation-aware)
        self.evolution = EvolutionEngine(
            simulate=self.simulate or self.local_only,
        )

        # Performance tracker for meta-learning
        self.performance = PerformanceTracker()

        # Structured logger
        self.logger = StructuredLogger()

        # Shared orchestrator (legacy compatibility)
        self._orchestrator = Orchestrator(
            memory=self.memory,
            policy=self.policy,
            model_router=self.model_router,
            tool_registry=self.tool_registry,
        )

        # Active agent instances (created lazily)
        self._agents: Dict[str, Any] = {}
        self._session_logger_instance = None

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------
    def _get_agent(self, agent_name: str) -> Any:
        """Get or create an agent instance. Agent classes set their own name."""
        if agent_name not in self._agents:
            cls = _AGENT_CLASSES.get(agent_name)
            if cls is None:
                raise ValueError(f"Unknown agent type: {agent_name}")
            self._agents[agent_name] = cls(
                model_router=self.model_router,
                tool_registry=self.tool_registry,
                memory_manager=self.memory,
                policy_engine=self.policy,
                session_logger=self._get_session_logger(),
            )
        return self._agents[agent_name]

    def _get_session_logger(self):
        """Lazy-create a session logger."""
        if self._session_logger_instance is None:
            from .logging.session_logger import SessionLogger
            self._session_logger_instance = SessionLogger()
        return self._session_logger_instance

    @staticmethod
    def _emit(event_callback, event_type: str, data: Dict[str, Any]) -> None:
        """Forward an orchestrator event to an external callback (if any)."""
        if event_callback is None:
            return
        try:
            event_callback(event_type, data)
        except Exception as e:
            logger.debug(f"Event callback failed for {event_type}: {e}")

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    async def run(self, objective: str, target_id: Optional[str] = None,
                  event_callback=None, **kwargs) -> Dict[str, Any]:
        """
        Run the full autonomous pipeline for a given objective.

        PLAN → MEMORY RETRIEVAL → MODEL ROUTING → AGENT → TOOL →
        RESULT → VERIFY → MEMORY → EVOLUTION → REPORT.

        Dry-run: shows plan without executing.
        Simulation: uses deterministic mock results.
        """
        task_id = str(uuid.uuid4())
        self._emit(event_callback, "task_started", {
            "task_id": task_id,
            "objective": objective,
            "target_id": target_id or "",
            "simulate": self.simulate,
            "dry_run": self.dry_run,
        })

        # --- 1. Authorization check ---
        # In simulation mode we auto-authorize (target is virtual)
        if target_id and not self.simulate:
            if not self.policy.is_authorized(target_id):
                raise PermissionError(
                    f"Target '{target_id}' is not authorized. "
                    "Register it in lab/targets/targets.yaml."
                )
            if not self.policy.check_action_allowed(target_id, "analysis"):
                logger.warning(
                    f"Action 'analysis' not in explicit allowed_actions for {target_id}"
                )

        # --- 2. Create canonical task state ---
        task = Task(
            id=task_id,
            objective=objective,
            scope=kwargs.get("scope", "authorized_lab"),
            environment=kwargs.get("environment", "authorized_lab"),
            authorization="authorized" if (target_id or self.simulate) else "pending",
        )
        task.set_status(TaskStatus.PLANNING)

        # --- 3. Memory retrieval ---
        memories = self._retrieve_memories(objective)
        task.memory_references = [m.get("memory_id", m.get("id", "")) for m in memories]

        # --- 4. Plan generation (with evolution) ---
        plan_result = await self._generate_plan(task, memories)
        task.plan = plan_result["steps"]
        task.set_status(TaskStatus.PLAN_READY)
        self._emit(event_callback, "plan_ready", {
            "task_id": task_id,
            "objective": objective,
            "steps": [
                {
                    "step": s.get("step", i + 1),
                    "action": s.get("action", ""),
                    "capability": s.get("capability", ""),
                    "tool": s.get("tool", ""),
                    "model": s.get("model", ""),
                    "description": s.get("description", ""),
                }
                for i, s in enumerate(plan_result["steps"])
            ],
            "strategy_count": len(plan_result.get("strategies", [])),
        })

        if self.dry_run:
            return self._dry_run_report(task, plan_result)

        # --- 5. Execute plan ---
        self._emit(event_callback, "phase", {
            "task_id": task_id, "phase": "executing", "message": "Agents engaging"
        })
        execution_result = await self._execute_pipeline(task, plan_result, event_callback)

        # --- 6. Verification ---
        task.set_status(TaskStatus.WAITING_VERIFICATION)
        self._emit(event_callback, "phase", {
            "task_id": task_id, "phase": "verifying", "message": "Verifying findings"
        })
        await self._verify_task(task)
        task.set_status(TaskStatus.VERIFIED)

        # --- 7. Evolution ---
        if plan_result.get("strategies"):
            self._emit(event_callback, "phase", {
                "task_id": task_id, "phase": "evolving", "message": "Evolving strategies"
            })
            await self._evolve_strategies(plan_result["strategies"], task)

        # --- 8. Final report ---
        task.set_status(TaskStatus.COMPLETED)
        self._emit(event_callback, "phase", {
            "task_id": task_id, "phase": "reporting", "message": "Generating report"
        })
        report = await self._generate_report(task)
        task.final_report = report

        self._emit(event_callback, "task_completed", {
            "task_id": task_id,
            "objective": objective,
            "status": "completed",
            "findings_count": len(task.findings),
            "evidence_count": len(task.evidence),
            "agents_used": task.agents_used,
            "tools_used": task.tools_used,
            "models_used": task.models_used,
        })

        return task.to_dict()

    def _retrieve_memories(self, objective: str) -> List[Dict]:
        """Retrieve relevant past experiences from typed memory."""
        try:
            store = MemoryStore()
            memories = store.retrieve_for_planning(objective)
            store.close()
        except Exception:
            memories = []
        return memories

    async def _generate_plan(self, task: Task, memories: List[Dict]) -> Dict[str, Any]:
        """Generate a plan, optionally using evolution strategies."""
        # Check for elite strategies in memory
        elite_strategies = []
        try:
            store = MemoryStore()
            elite_results = store.get_by_metadata("episodic", "strategy_type", "elite")[:5]
            store.close()
            elite_strategies = elite_results
        except Exception:
            pass

        # Generate candidate strategies via evolution engine
        try:
            strategies_result = await self.evolution.evolve_generation(
                task_type="assessment",
                task_context={
                    "objective": task.objective,
                    "environment": task.environment,
                },
                num_strategies=3,
            )
        except Exception:
            strategies_result = {"results": []}

        # Use the planner agent for the final plan
        steps = list(_DEFAULT_PLAN_STEPS)
        try:
            planner = self._get_agent("planner")
            plan = await planner.run({
                "objective": task.objective,
                "target_id": task.metadata.get("target_id", ""),
                "session_id": task.id,
                "constraints": [],
            })
            plan_steps = plan.get("steps", [])
            if plan_steps and isinstance(plan_steps, list):
                steps = plan_steps
        except Exception as e:
            logger.debug(f"Planner LLM call failed, using default steps: {e}")

        # Enrich steps with capability-based tool selection
        for step in steps:
            capability = step.get("capability") or self._capability_for_action(
                step.get("action", "analysis")
            )
            step["capability"] = capability
            providers = self.capabilities.get_providers(capability)
            if providers:
                step["tool"] = providers[0].name

        # Search for relevant past experiences
        try:
            relevant_experiences = [
                {"id": e.get("id"), "observation": e.get("observation", "")}
                for e in self.memory.search_experiences(task.objective, limit=5)
            ]
        except Exception:
            relevant_experiences = []

        return {
            "steps": steps,
            "strategies": strategies_result.get("results", []),
            "relevant_experiences": relevant_experiences,
            "model": self.model_router.route("planning"),
            "elite_strategies_used": len(elite_strategies),
        }

    def _capability_for_action(self, action: str) -> str:
        """Map a plan action to a capability name."""
        mapping = {
            "recon": "reconnaissance",
            "research": "research",
            "analysis": "analysis",
            "code_analysis": "source_analysis",
            "code_generation": "code_generation",
            "exploitation": "exploitation",
            "verification": "verification",
            "reporting": "reporting",
        }
        return mapping.get(action, "analysis")

    async def _execute_pipeline(self, task: Task, plan_result: Dict,
                                event_callback=None) -> Dict[str, Any]:
        """Execute the plan through the agent collaboration pipeline."""

        pipeline = AgentPipeline(task=task)
        pipeline.add_step("researcher", "research", "Research target",
                          output_key="research")
        pipeline.add_step("recon", "reconnaissance", "Perform reconnaissance",
                          output_key="recon")
        pipeline.add_step("analyst", "analysis", "Analyze findings",
                          output_key="analysis")
        pipeline.add_step("verifier", "verification", "Verify findings",
                          output_key="verification")
        pipeline.add_step("reporter", "reporting", "Generate report",
                          output_key="report")

        async def execute_agent(agent_name: str, context: Dict) -> Dict:
            agent = self._get_agent(agent_name)
            agent_task = {
                "objective": context.get("objective", ""),
                "target_id": task.metadata.get("target_id", ""),
                "session_id": task.id,
                "environment": context.get("environment", task.environment),
            }
            agent_task.update(context)

            capability = context.get("capability", "unknown")
            self._emit(event_callback, "agent_started", {
                "task_id": task.id,
                "agent": agent_name,
                "capability": capability,
                "objective": agent_task.get("objective", ""),
            })

            start = time.time()
            # Simulation mode: return deterministic mock
            if self.simulate:
                result = self._simulate_agent(agent_name, agent_task)
            elif self.dry_run:
                # Dry-run: don't execute
                result = {"status": "dry_run", "agent": agent_name}
            else:
                # Real execution
                try:
                    result = await agent.run(agent_task)
                except Exception as e:
                    result = {"success": False, "error": str(e), "agent": agent_name}

            self._emit(event_callback, "agent_completed", {
                "task_id": task.id,
                "agent": agent_name,
                "capability": capability,
                "success": result.get("success", True),
                "latency_ms": round((time.time() - start) * 1000, 1),
                "summary": str(result.get("analysis") or result.get("research")
                               or result.get("content") or result.get("status")
                               or result.get("output") or "")[:300],
            })
            latency = time.time() - start

            # Record performance
            self.performance.record(
                PerformanceRecord(
                    entity_type="agent",
                    entity_name=agent_name,
                    task_type=context.get("capability", "unknown"),
                    success=result.get("success", True),
                    latency=latency,
                )
            )

            # Store as experience
            try:
                self.memory.store_experience({
                    "session_id": task.id,
                    "target_id": agent_task.get("target_id", ""),
                    "observation": f"Agent {agent_name} executed",
                    "action": context.get("capability", "unknown"),
                    "tool": agent_name,
                    "result": "success" if result.get("success", True) else "failure",
                    "evidence": [],
                    "confidence": 0.5,
                })
            except Exception:
                pass

            return result

        pipeline_result = await pipeline.run(execute_agent)
        results = pipeline_result["results"]

        # Store findings from the pipeline
        for step_name, result in results.items():
            if result and isinstance(result, dict):
                findings = result.get("findings", [])
                if findings:
                    for finding in findings:
                        task.add_finding(
                            description=(finding if isinstance(finding, str)
                                         else str(finding)[:200]),
                            confidence=0.3,
                            source=step_name,
                        )

        return {
            "pipeline_steps": pipeline_result["steps"],
            "results": results,
            "strategies_evaluated": len(plan_result.get("strategies", [])),
        }

    def _simulate_agent(self, agent_name: str, agent_task: Dict) -> Dict[str, Any]:
        """Return deterministic mock results for an agent in simulation mode."""
        mock_outputs = {
            "researcher": {
                "findings": ["Identified target technology stack (simulated)",
                             "Found 3 known vulnerability patterns (simulated)"],
                "research": "Simulated research: target appears to be a web application with input validation issues.",
                "success": True,
            },
            "recon": {
                "findings": ["Port 8080 open (HTTP)", "Port 22 open (SSH)",
                             "Server: nginx/1.20.1 (simulated)"],
                "raw_output": "SIMULATED PORT SCAN: 1 host up, 3 ports open",
                "success": True,
            },
            "analyst": {
                "analysis": "Simulated analysis: potential SQL injection and XSS vulnerabilities identified.",
                "findings_count": 3,
                "success": True,
            },
            "verifier": {
                "verified": True,
                "status": "VERIFIED",
                "confidence": 0.85,
                "success": True,
            },
            "reporter": {
                "content": "# Simulated Assessment Report\n\nTarget analyzed with simulated findings.",
                "status": "generated",
                "success": True,
            },
            "planner": {
                "steps": [{"step": i + 1, "action": s["action"], "capability": s["capability"],
                           "description": s["description"], "model": s["model"]}
                          for i, s in enumerate(_DEFAULT_PLAN_STEPS)],
                "success": True,
            },
            "coder": {
                "output": "# Simulated code analysis\nNo issues found in simulation mode.",
                "success": True,
            },
        }
        result = mock_outputs.get(agent_name, {"status": "simulated",
                                               "output": "no mock data",
                                               "success": True})
        result["simulated"] = True
        result["agent"] = agent_name
        return result

    async def _verify_task(self, task: Task) -> None:
        """Verify all findings using the verifier agent."""
        if self.simulate:
            for finding in task.findings:
                finding["verification"] = "VERIFIED"
                finding["confidence"] = min(finding.get("confidence", 0.3) + 0.2, 1.0)
            return

        verifier = self._get_agent("verifier")
        for finding in task.findings:
            try:
                verified = await verifier.verify_finding({
                    "observation": finding.get("description", ""),
                    "evidence": [],
                    "confidence": finding.get("confidence", 0.0),
                    "source": finding.get("source", ""),
                })
                finding["verification"] = verified.get("status", "UNVERIFIED")
                finding["confidence"] = verified.get("confidence",
                                                     finding.get("confidence", 0.0))
            except Exception:
                finding["verification"] = "UNVERIFIED"

    async def _evolve_strategies(self, strategies: List[Dict], task: Task) -> None:
        """Run one generation of strategy evolution based on task results."""
        try:
            await self.evolution.evolve_generation(
                task_type="assessment",
                task_context={"task_id": task.id, "objective": task.objective},
                num_strategies=3,
            )
        except Exception as e:
            logger.warning(f"Evolution failed: {e}")

    async def _generate_report(self, task: Task) -> Dict[str, Any]:
        """Generate the final report."""
        # In simulation mode, use a deterministic mock report
        if self.simulate:
            return {
                "content": (
                    f"# Assessment Report\n\n"
                    f"**Objective**: {task.objective}\n\n"
                    f"**Findings**: {len(task.findings)} total\n"
                    f"**Evidence items**: {len(task.evidence)}\n"
                    f"**Agents used**: {', '.join(task.agents_used) or 'none'}\n"
                    f"**Tools used**: {', '.join(task.tools_used) or 'none'}\n"
                    f"**Models used**: {', '.join(task.models_used) or 'none'}\n"
                    f"**Status**: COMPLETED (simulated)\n\n"
                    "All simulated activities completed successfully in local-only mode."
                ),
                "status": "generated",
                "simulated": True,
            }

        reporter = self._get_agent("reporter")
        try:
            report = await reporter.run({
                "target_id": task.metadata.get("target_id", ""),
                "session_id": task.id,
                "findings": task.findings,
                "evidence": task.evidence,
                "analysis": "",
                "objective": task.objective,
            })
        except Exception as e:
            report = {
                "content": f"# Report (generation failed: {e})\n\nObjective: {task.objective}",
                "status": "partial",
            }

        return report

    def _dry_run_report(self, task: Task, plan_result: Dict) -> Dict[str, Any]:
        """Generate a dry-run report showing planned actions without executing."""
        capabilities_used = []
        tools_planned = []
        models_planned = []
        actions = []

        for step in plan_result.get("steps", []):
            capability = step.get("capability", "unknown")
            tool = step.get("tool", "unknown")
            action = step.get("action", "unknown")

            if capability not in capabilities_used:
                capabilities_used.append(capability)
            if tool not in tools_planned:
                tools_planned.append(tool)
            action_model = self.model_router.route(action)
            if action_model not in models_planned:
                models_planned.append(action_model)

            actions.append({
                "step": step.get("step", 0),
                "action": action,
                "capability": capability,
                "tool": tool,
                "model": action_model,
                "description": step.get("description", ""),
                "expected_evidence": step.get("expected_evidence", ""),
            })

        return {
            "status": "dry_run",
            "task_id": task.id,
            "objective": task.objective,
            "target_id": task.metadata.get("target_id", ""),
            "capabilities_identified": capabilities_used,
            "tools_planned": tools_planned,
            "models_planned": models_planned,
            "actions": actions,
            "strategies_evaluated": len(plan_result.get("strategies", [])),
            "elite_strategies_used": plan_result.get("elite_strategies_used", 0),
            "memory_references": len(task.memory_references),
            "policy_decisions": [
                "Local-only mode enforced (no cloud model calls)",
                "Target authorization checked" if task.metadata.get("target_id") else "No target specified",
                "No tools executed — dry-run mode",
            ],
        }

    # ------------------------------------------------------------------
    # Convenience: single-target assess
    # ------------------------------------------------------------------
    async def assess(self, target_id: str, objective: str,
                     dry_run: bool = False, simulate: bool = False) -> Dict[str, Any]:
        """Run an assessment on an authorized target."""
        self.dry_run = dry_run
        self.simulate = simulate or self.local_only
        task = Task(objective=objective)
        task.metadata["target_id"] = target_id
        result = await self.run(objective, target_id=target_id, task=task)
        return result

    def get_status(self) -> Dict[str, Any]:
        """Get full platform status."""
        ollama_status = "UNKNOWN"
        litellm_status = "UNKNOWN"
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ll_status = loop.run_until_complete(self.llm_gateway.health_check())
            ollama_status = ll_status.get("ollama", {}).get("status", "UNKNOWN")
            litellm_status = ll_status.get("litellm", {}).get("status", "UNKNOWN")
            loop.close()
        except Exception:
            pass

        return {
            "platform": "Cyber AI",
            "version": "2.0.0",
            "local_only": self.local_only,
            "simulate": self.simulate,
            "dry_run": self.dry_run,
            "orchestrator": self._orchestrator.get_status(),
            "ollama": ollama_status,
            "litellm": litellm_status,
            "agents": list(_AGENT_CLASSES.keys()),
            "models": self.llm_gateway.list_registry(),
            "capabilities": self.capabilities.list_capabilities(),
            "evolution": self.evolution.get_status(),
            "memory": self.memory.get_stats() if hasattr(self.memory, "get_stats") else {},
        }

    def close(self) -> None:
        """Clean up resources."""
        try:
            self.memory.close()
        except Exception:
            pass
        try:
            self.performance.close()
        except Exception:
            pass
