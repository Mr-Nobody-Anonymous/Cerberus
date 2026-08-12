"""
Recon Agent for the Cyber AI Orchestrator.

Performs reconnaissance on authorized targets using registered security tools.
Delegates actual scanning to adapter tools (strix, darkmoon, etc.).
"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseAgent

logger = logging.getLogger(__name__)


class ReconAgent(BaseAgent):
    """
    Reconnaissance agent that scans targets using available security tools.

    Routes recon tasks to fast models for classification and summary,
    and delegates actual scanning to registered tool adapters.
    """

    def __init__(self, **kwargs):
        super().__init__(name="recon", **kwargs)

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform reconnaissance on an authorized target.

        Args:
            task: Dict with keys:
                - target: Target identifier (IP, hostname, URL)
                - target_id: Authorized target ID
                - session_id: Current session ID
                - scope: Optional scope description
                - depth: recon depth (passive, active, full)

        Returns:
            Recon result dict with findings
        """
        target = task.get("target", "")
        target_id = task.get("target_id", "")
        session_id = task.get("session_id", "")
        scope = task.get("scope", "passive")
        depth = task.get("depth", "passive")

        # Build task spec for tool execution
        tool_task = {
            "action": "recon",
            "target": {
                "id": target_id,
                "host": target,
                "environment": "authorized_lab",
                "allowed": True,
            },
            "parameters": {
                "scope": scope,
                "depth": depth,
            },
            "session_id": session_id,
        }

        # Find recon-capable tools
        recon_tools = []
        if self.tool_registry:
            tools = self.tool_registry.get_tools_by_capability("research")
            recon_tools = [t["name"] for t in tools]

        # Try to execute via adapter if available
        adapter_result = None
        used_tool = None
        if recon_tools and self.tool_registry:
            # Use the first available tool
            used_tool = recon_tools[0]
            adapter_path = self.tool_registry.get_adapter_path(used_tool)
            if adapter_path:
                adapter_result = await self._try_adapter(adapter_path, tool_task)

        # Generate analysis using LLM
        prompt = (
            f"You are a reconnaissance analyst. Analyze the following recon "
            f"data and extract key findings.\n\n"
            f"Target: {target}\n"
            f"Scope: {scope}\n"
            f"Depth: {depth}\n"
            f"Available tools: {', '.join(recon_tools) if recon_tools else 'none registered'}\n"
            f"\nProvide a structured summary of potential attack surfaces, "
            f"open ports, services, and interesting findings."
        )

        if adapter_result and adapter_result.get("success"):
            prompt += f"\n\nTool output:\n{adapter_result.get('output', '')[:3000]}"
        else:
            prompt += "\n\nNo automated tool output available (tools may not be configured)."

        llm_response = await self._llm_call(prompt, task_type="web_research")

        result = {
            "session_id": session_id,
            "target": target,
            "target_id": target_id,
            "scope": scope,
            "depth": depth,
            "tools_available": recon_tools,
            "tool_used": used_tool,
            "findings": llm_response,
            "raw_output": adapter_result.get("output", "") if adapter_result else None,
            "evidence": adapter_result.get("evidence", []) if adapter_result else [],
        }

        # Log
        if self.logger and session_id:
            self.logger.log_event(session_id, "tool_calls", {
                "agent": self.name,
                "target": target,
                "action": "recon",
                "tool": used_tool,
                "success": adapter_result.get("success", False) if adapter_result else False,
            })

        # Record experience
        self._record_experience(
            session_id=session_id,
            target_id=target_id,
            observation=f"Recon (depth={depth}, scope={scope}) on {target}",
            hypothesis=f"Reconnaissance will reveal attack surfaces on {target}",
            action="recon",
            tool=used_tool or "none",
            result="success" if adapter_result and adapter_result.get("success") else "partial",
            evidence=result.get("evidence", []),
            confidence=0.5 if adapter_result and adapter_result.get("success") else 0.3,
        )

        return result

    async def _try_adapter(self, adapter_path: str, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Attempt to call an adapter's execute method."""
        try:
            # adapter_path is like "adapters.pentagi"
            module = __import__(adapter_path, fromlist=["Adapter"])
            adapter_cls = getattr(module, "Adapter", None)
            if adapter_cls:
                adapter = await adapter_cls.create(task) if hasattr(adapter_cls, "create") else adapter_cls()
                result = await adapter.execute(task)
                if hasattr(result, "dict"):
                    return result.dict()
                elif hasattr(result, "__dict__"):
                    return result.__dict__
                elif isinstance(result, dict):
                    return result
                return {"success": True, "output": str(result)}
        except Exception as e:
            logger.warning(f"Adapter call failed for {adapter_path}: {e}")
        return None
