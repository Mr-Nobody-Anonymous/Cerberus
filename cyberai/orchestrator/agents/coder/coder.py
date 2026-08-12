"""
Coder Agent for the Cyber AI Orchestrator.

Handles code analysis, exploit development, and code generation tasks.
Routes sensitive code operations to local-only models by default.
"""

import logging
from typing import Any, Dict, List, Optional

from ..base import BaseAgent

logger = logging.getLogger(__name__)


class CoderAgent(BaseAgent):
    """
    Code analysis and generation agent.

    Routes code analysis and generation to coding-specific models.
    Sensitive source code analysis is always routed to local-only models.
    """

    def __init__(self, **kwargs):
        super().__init__(name="coder", **kwargs)

    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze code or generate code/exploits.

        Args:
            task: Dict with keys:
                - action: "analyze" or "generate"
                - code: Source code to analyze (optional)
                - target_id: Authorized target ID
                - session_id: Current session ID
                - description: Description of code to generate
                - language: Programming language
                - sensitive: Whether this involves sensitive source code (default: True)

        Returns:
            Code analysis or generated code
        """
        action = task.get("action", "analyze")
        code = task.get("code", "")
        description = task.get("description", "")
        language = task.get("language", "python")
        sensitive = task.get("sensitive", True)
        target_id = task.get("target_id", "")
        session_id = task.get("session_id", "")

        # Always use local model for sensitive code
        task_type = "sensitive_source_code" if sensitive else "code_generation"

        if action == "analyze":
            prompt = (
                f"You are a security code analyst. Analyze the following source code "
                f"for security vulnerabilities, weaknesses, and potential exploits.\n\n"
                f"Language: {language}\n"
                f"Target: {target_id}\n"
                f"\nCode:\n```\n{code[:5000]}\n```\n"
                f"\nProvide:\n"
                f"1. Security issues found (CWE references where applicable)\n"
                f"2. Severity rating for each issue\n"
                f"3. Proof-of-concept code if applicable\n"
                f"4. Remediation recommendations\n"
                f"\nIMPORTANT: Use local-only model for this sensitive source code analysis."
            )
        elif action == "generate":
            prompt = (
                f"You are a code generation agent. Generate secure code for "
                f"the following specification.\n\n"
                f"Description: {description}\n"
                f"Language: {language}\n"
                f"Target: {target_id}\n"
                f"\nGenerate clean, well-commented code that follows security best practices."
            )
        else:
            return {"error": f"Unknown action: {action}"}

        llm_response = await self._llm_call(prompt, task_type=task_type)

        result = {
            "session_id": session_id,
            "target_id": target_id,
            "action": action,
            "language": language,
            "sensitive": sensitive,
            "model": "local-coder" if sensitive else "local-coder",
            "output": llm_response,
            "code_length": len(llm_response),
        }

        # Log
        if self.logger and session_id:
            self.logger.log_event(session_id, "model_calls", {
                "agent": self.name,
                "action": action,
                "task_type": task_type,
                "code_length": len(code),
                "output_length": len(llm_response),
            })

        # Record experience
        self._record_experience(
            session_id=session_id,
            target_id=target_id,
            observation=f"{'Code analysis' if action == 'analyze' else 'Code generation'} for {language}",
            hypothesis=f"Code review will find vulnerabilities" if action == "analyze" else f"Code will be generated correctly",
            action=action,
            tool="coder_agent",
            result="success",
            confidence=0.8 if action == "analyze" else 0.6,
        )

        return result
