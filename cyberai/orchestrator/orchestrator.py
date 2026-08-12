"""
Master Orchestrator for the Cyber AI Orchestrator.

The orchestrator is the brain of the platform. It coordinates:
- Planning agents
- Research agents
- Verification agents
- LLM routing (via LiteLLM gateway)
- Tool routing (via MCP/adapters)
- Memory and experience storage
- Policy enforcement
- Evidence collection
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .memory.memory_manager import MemoryManager
from .policies.policy_engine import PolicyEngine
from .routing.model_router import ModelRouter
from .tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Master orchestrator that coordinates all platform components.

    The orchestrator does NOT contain the implementation of every
    security tool. Instead it routes tasks through the tool registry
    to the appropriate adapter.
    """

    def __init__(
        self,
        memory: Optional[MemoryManager] = None,
        policy: Optional[PolicyEngine] = None,
        model_router: Optional[ModelRouter] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.memory = memory or MemoryManager()
        self.policy = policy or PolicyEngine()
        self.model_router = model_router or ModelRouter()
        self.tool_registry = tool_registry or ToolRegistry()
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._active_tasks: Dict[str, asyncio.Task] = {}

    async def start_session(self, target_id: str) -> Dict[str, Any]:
        """
        Start a new orchestration session.

        Args:
            target_id: The authorized target ID

        Returns:
            Session info dict
        """
        # Check authorization
        if not self.policy.is_authorized(target_id):
            raise PermissionError(
                f"Target '{target_id}' is not authorized. "
                "Register it in lab/targets/targets.yaml first."
            )

        session_id = self.memory.create_session(target_id)
        session = {
            "id": session_id,
            "target_id": target_id,
            "status": "active",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "tasks": [],
        }
        self._sessions[session_id] = session
        logger.info(f"Started session {session_id} for target {target_id}")
        return session

    async def end_session(self, session_id: str, summary: str = "") -> None:
        """End a session."""
        if session_id in self._sessions:
            self._sessions[session_id]["status"] = "completed"
            self._sessions[session_id]["ended_at"] = datetime.now(timezone.utc).isoformat()
        self.memory.end_session(session_id, summary)
        logger.info(f"Ended session {session_id}")

    async def plan(self, session_id: str, objective: str) -> Dict[str, Any]:
        """
        Plan a task using the planner agent.

        Args:
            session_id: The session ID
            objective: The objective to plan for

        Returns:
            Plan dict
        """
        # Route to appropriate model
        model_alias = self.model_router.route("planning")

        # Retrieve relevant past experiences
        experiences = self.memory.search_experiences(objective, limit=5)

        plan = {
            "session_id": session_id,
            "objective": objective,
            "model": model_alias,
            "steps": [],
            "relevant_experiences": [
                {
                    "id": e["id"],
                    "observation": e["observation"],
                    "result": e["result"],
                    "score": e["score"],
                }
                for e in experiences
            ],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Generate plan steps (in a real deployment, this would use the LLM)
        # For now, create a basic plan structure
        plan["steps"] = [
            {"step": 1, "action": "recon", "description": f"Reconnaissance on {objective}"},
            {"step": 2, "action": "analysis", "description": f"Analyze findings for {objective}"},
            {"step": 3, "action": "verification", "description": f"Verify findings for {objective}"},
            {"step": 4, "action": "report", "description": f"Generate report for {objective}"},
        ]

        logger.info(f"Created plan for session {session_id}")
        return plan

    async def execute_task(
        self,
        session_id: str,
        target_id: str,
        tool_name: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a task using a registered tool.

        Args:
            session_id: The session ID
            target_id: The authorized target ID
            tool_name: The tool to use (from tool registry)
            action: The action to perform
            parameters: Tool-specific parameters

        Returns:
            Task result dict
        """
        # Check authorization
        if not self.policy.is_authorized(target_id):
            raise PermissionError(f"Target '{target_id}' is not authorized")

        if not self.policy.check_action_allowed(target_id, action):
            raise PermissionError(
                f"Action '{action}' is not allowed on target '{target_id}'"
            )

        # Get tool from registry
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Route to appropriate model
        model_alias = self.model_router.route(action)

        task = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "target_id": target_id,
            "tool": tool_name,
            "action": action,
            "parameters": parameters or {},
            "model": model_alias,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        # In a real deployment, this would call the adapter
        # For now, return a stub result
        task["status"] = "completed"
        task["result"] = {
            "success": True,
            "message": f"Task executed via {tool_name} adapter (stub)",
            "tool": tool_name,
            "action": action,
        }
        task["completed_at"] = datetime.now(timezone.utc).isoformat()

        # Store experience
        self.memory.store_experience({
            "session_id": session_id,
            "target_id": target_id,
            "target_type": "authorized_lab",
            "environment": "authorized_lab",
            "observation": f"Executed {action} on {target_id} using {tool_name}",
            "hypothesis": "",
            "action": action,
            "tool": tool_name,
            "result": "success",
            "evidence": [],
            "confidence": 0.5,
            "lessons": [],
        })

        logger.info(f"Executed task {task['id']} using {tool_name}")
        return task

    async def verify(self, session_id: str, finding: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a finding using the verifier agent.

        Args:
            session_id: The session ID
            finding: The finding to verify

        Returns:
            Verified finding
        """
        from .agents.verifier.verifier import VerifierAgent

        verifier = VerifierAgent(memory_manager=self.memory, model_router=self.model_router)
        verified = await verifier.verify_finding(finding)
        verified["session_id"] = session_id
        return verified

    async def assess(self, target_id: str, objective: str) -> Dict[str, Any]:
        """
        Run a full assessment on an authorized target.

        Args:
            target_id: The authorized target ID
            objective: The assessment objective

        Returns:
            Assessment result
        """
        session = await self.start_session(target_id)
        session_id = session["id"]

        try:
            # 1. Plan
            plan = await self.plan(session_id, objective)

            # 2. Execute each plan step
            results = []
            for step in plan["steps"]:
                # Find a tool that can handle this action
                tools = self.tool_registry.get_tools_by_capability(step["action"])
                if tools:
                    tool_name = tools[0]["name"]
                    result = await self.execute_task(
                        session_id, target_id, tool_name, step["action"]
                    )
                    results.append(result)

            # 3. Generate summary
            summary = {
                "session_id": session_id,
                "target_id": target_id,
                "objective": objective,
                "plan": plan,
                "results": results,
                "status": "completed",
            }

            await self.end_session(session_id, summary=json.dumps(summary))
            return summary

        except Exception as e:
            await self.end_session(session_id, summary=f"Failed: {e}")
            raise

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "platform": "Cyber AI Orchestrator",
            "sessions": len(self._sessions),
            "active_tasks": len(self._active_tasks),
            "tools_registered": len(self.tool_registry.list_tools()),
            "targets_authorized": len(self.policy.list_authorized_targets()),
        }