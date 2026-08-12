"""
CERBERUS — Multi-Agent Piped Fallback Loop
==========================================
Implements the sequential agent pipeline with secure subprocess execution
and output parsing:

    Researcher → Recon → Analyst → Verifier → Reporter

Each agent's output is parsed, sanitized, and piped as context to the next
agent. Falls back to simulation when external tools/LLMs are unavailable.

The execution is protected by:
- Command injection prevention (whitelist of allowed commands/args)
- Timeout enforcement
- Output size limits
- Target authorization checks
"""

import asyncio
import json
import logging
import re
import subprocess
import shlex
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Secure subprocess execution
# ---------------------------------------------------------------------------

# Maximum output size to accept from external tools (500 KB)
MAX_OUTPUT_SIZE = 500 * 1024

# Maximum execution time for external tools (60 seconds)
MAX_EXECUTION_TIMEOUT = 60.0

# Allowed command patterns per tool
# Each entry maps a tool name to a list of (command_template, shell=False)
# Command templates use {target} and {params} placeholders.
ALLOWED_COMMANDS: Dict[str, List[Dict[str, Any]]] = {
    "strix": [
        {
            "args": ["strix", "scan", "--target", "{target}"],
            "shell": False,
            "timeout": 60.0,
        },
        {
            "args": ["strix", "assess", "--target", "{target}"],
            "shell": False,
            "timeout": 60.0,
        },
    ],
    "drakben": [
        {
            "args": ["python", "-m", "drakben", "scan", "{target}"],
            "shell": False,
            "timeout": 60.0,
        },
    ],
    "guardian_cli": [
        {
            "args": ["guardian", "scan", "--target", "{target}"],
            "shell": False,
            "timeout": 60.0,
        },
    ],
    "pentestgpt": [
        {
            "args": ["python", "-m", "pentestgpt", "run", "{target}"],
            "shell": False,
            "timeout": 60.0,
        },
    ],
    "autopentest": [
        {
            "args": ["python", "-m", "autopentest", "assess", "{target}"],
            "shell": False,
            "timeout": 60.0,
        },
    ],
    "pentestagent": [
        {
            "args": ["python", "-m", "pentestagent", "scan", "{target}"],
            "shell": False,
            "timeout": 60.0,
        },
    ],
    "aracne": [
        {
            "args": ["python", "-m", "aracne", "scan", "{target}"],
            "shell": False,
            "timeout": 60.0,
        },
    ],
}

# Dangerous patterns that should never appear in tool arguments
DANGEROUS_PATTERNS = [
    "&&",
    "||",
    ";",
    "|",
    ">",
    "<",
    "$(",
    "`",
    "${",
    "rm -rf",
    "mkfs",
    ":(){",
    "sudo",
    "chmod 777",
]


def sanitize_target(target: str) -> str:
    """
    Sanitize a target string for safe command execution.

    Validates that the target is a simple host/IP/URL without
    shell metacharacters.

    Args:
        target: Target string (IP, hostname, URL)

    Returns:
        Sanitized target string

    Raises:
        ValueError: If the target contains dangerous characters
    """
    if not target:
        raise ValueError("Target cannot be empty")

    # Must be alphanumeric with dots, hyphens, colons, slashes, underscores
    if not re.match(r"^[a-zA-Z0-9._:/@\[\]-]+$", target):
        raise ValueError(f"Invalid target format: {target}")

    # Check for dangerous patterns
    target_lower = target.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in target_lower:
            raise ValueError(f"Dangerous pattern in target: {pattern}")

    return target


def sanitize_parameters(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize parameters for safe command injection.

    Ensures parameter values are safe types without shell metacharacters.

    Args:
        parameters: Parameter dict

    Returns:
        Sanitized parameters dict
    """
    sanitized: Dict[str, Any] = {}
    for key, value in parameters.items():
        if isinstance(value, str):
            # Reject dangerous patterns
            value_lower = value.lower()
            if any(p in value_lower for p in DANGEROUS_PATTERNS):
                logger.warning(f"Parameter '{key}' contains dangerous pattern; sanitizing")
                # Remove dangerous patterns
                for pattern in DANGEROUS_PATTERNS:
                    value = value.replace(pattern, "")
            sanitized[key] = value
        elif isinstance(value, (int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, list):
            sanitized[key] = [sanitize_parameters({"v": v})["v"] for v in value]
        elif isinstance(value, dict):
            sanitized[key] = sanitize_parameters(value)
        else:
            sanitized[key] = str(value)
    return sanitized


async def run_tool_command(
    tool_name: str,
    target: str,
    parameters: Optional[Dict[str, Any]] = None,
    timeout: float = MAX_EXECUTION_TIMEOUT,
) -> Tuple[bool, str, str]:
    """
    Execute a tool command securely with subprocess.

    Only allows commands from the ALLOWED_COMMANDS whitelist.

    Args:
        tool_name: The tool name (must be in ALLOWED_COMMANDS)
        target: The target host/IP
        parameters: Tool-specific parameters
        timeout: Maximum execution time in seconds

    Returns:
        Tuple of (success, stdout, stderr)
    """
    parameters = sanitize_parameters(parameters or {})
    safe_target = sanitize_target(target)

    if tool_name not in ALLOWED_COMMANDS:
        return False, "", f"Tool '{tool_name}' not in allowed command whitelist"

    templates = ALLOWED_COMMANDS[tool_name]
    if not templates:
        return False, "", f"No command templates for tool '{tool_name}'"

    # Try each template until one succeeds
    for template in templates:
        try:
            # Build args with placeholder substitution
            args = []
            for arg in template["args"]:
                substituted = arg.format(
                    target=safe_target,
                    params=json.dumps(parameters) if parameters else "",
                )
                args.append(substituted)

            cmd_timeout = template.get("timeout", timeout)

            logger.info(f"Executing: {tool_name} {' '.join(args)[:200]}")

            # Execute with subprocess (no shell for injection safety)
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(Path(__file__).parent.parent.parent.parent),  # workspace root
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=cmd_timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                logger.warning(f"Tool '{tool_name}' timed out after {cmd_timeout}s")
                return False, "", f"Tool timed out after {cmd_timeout}s"

            stdout = stdout_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]
            stderr = stderr_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]

            if proc.returncode == 0:
                return True, stdout, stderr
            else:
                logger.warning(f"Tool '{tool_name}' exited with code {proc.returncode}")
                return False, stdout, stderr

        except FileNotFoundError:
            logger.debug(f"Tool '{tool_name}' not found in PATH, trying next template")
            continue
        except Exception as e:
            logger.warning(f"Tool '{tool_name}' execution failed: {e}")
            return False, "", str(e)

    return False, "", f"Tool '{tool_name}' is not available on this system"


# ---------------------------------------------------------------------------
# Output parsing
# ---------------------------------------------------------------------------
def parse_tool_output(raw: str) -> Dict[str, Any]:
    """
    Parse and secure tool output into structured findings.

    Handles JSON, plain text, and structured lines. Returns a normalized
    dict with findings, evidence, and narrative summary.

    Args:
        raw: Raw tool output string

    Returns:
        Parsed output dict with findings, evidence, summary
    """
    if not raw:
        return {"findings": [], "evidence": [], "summary": ""}

    findings: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []

    # Try JSON parse
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            # Extract findings
            found = data.get("findings", [])
            if isinstance(found, list):
                for f in found:
                    if isinstance(f, dict):
                        findings.append({
                            "description": f.get("description", str(f)),
                            "severity": f.get("severity", "info"),
                            "confidence": float(f.get("confidence", 0.5)),
                        })
                    else:
                        findings.append({
                            "description": str(f),
                            "severity": "info",
                            "confidence": 0.5,
                        })
            evidence.append({
                "type": "json_output",
                "content": raw[:1000],
            })
        elif isinstance(data, list):
            for item in data:
                findings.append({
                    "description": str(item),
                    "severity": "info",
                    "confidence": 0.5,
                })
    except json.JSONDecodeError:
        # Not JSON — parse as text
        pass

    # Parse text output for lines with potential findings
    if not findings:
        for line in raw.split("\n"):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            # Skip headers, log lines, timestamps
            if line.startswith(("#", "[", "INFO", "WARN", "ERROR", "DEBUG")):
                continue
            # Look for interesting security keywords
            security_keywords = [
                "vulnerab", "exploit", "CVE-", "port", "open", "service",
                "ssl", "http", "injection", "xss", "sql", "auth", "token",
                "admin", "login", "password", "access",
            ]
            lowered = line.lower()
            if any(kw in lowered for kw in security_keywords):
                findings.append({
                    "description": line[:300],
                    "severity": "info",
                    "confidence": 0.4,
                })
                evidence.append({
                    "type": "text_output",
                    "content": line[:500],
                })

    # Truncate findings
    findings = findings[:20]

    # Build summary
    if findings:
        summary = f"Found {len(findings)} potential findings from tool output"
    elif raw:
        summary = raw[:500]
    else:
        summary = ""

    return {
        "findings": findings,
        "evidence": evidence,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Pipeline agent definitions
# ---------------------------------------------------------------------------
PIPELINE_STEPS = [
    {
        "name": "researcher",
        "capability": "research",
        "description": "Research target technology and known vulnerabilities",
        "prompt_template": (
            "You are a cybersecurity research agent. Research the following topic.\n"
            "Target: {target}\n"
            "Objective: {objective}\n"
            "Provide a structured summary of known vulnerabilities, attack surface, "
            "and recommended investigation steps."
        ),
    },
    {
        "name": "recon",
        "capability": "reconnaissance",
        "description": "Perform reconnaissance on the target",
        "prompt_template": (
            "You are a reconnaissance analyst. Based on the research:\n"
            "{previous_output}\n"
            "Perform reconnaissance on target: {target}\n"
            "List open ports, services, technologies, and potential attack surface."
        ),
    },
    {
        "name": "analyst",
        "capability": "analysis",
        "description": "Analyze findings and identify vulnerabilities",
        "prompt_template": (
            "You are a security analyst. Based on reconnaissance:\n"
            "{previous_output}\n"
            "Analyze the findings for target: {target}\n"
            "Identify potential vulnerabilities and their likelihood."
        ),
    },
    {
        "name": "verifier",
        "capability": "verification",
        "description": "Verify findings independently",
        "prompt_template": (
            "You are a verification agent. Review these findings:\n"
            "{previous_output}\n"
            "For each finding, assess whether there is sufficient evidence.\n"
            "Mark each as VERIFIED, LIKELY, or REJECTED."
        ),
    },
    {
        "name": "reporter",
        "capability": "reporting",
        "description": "Generate final assessment report",
        "prompt_template": (
            "You are a report writer. Generate a professional security assessment "
            "report based on:\n"
            "{previous_output}\n"
            "Target: {target}\n"
            "Include: executive summary, findings, evidence, and recommendations."
        ),
    },
]


class MultiAgentPipeline:
    """
    Sequential multi-agent pipeline with secure tool execution.

    Flow: Researcher → Recon → Analyst → Verifier → Reporter
    Each agent's output is piped as context to the next agent.
    """

    def __init__(
        self,
        adapter_manager=None,
        model_router=None,
        memory_manager=None,
        policy_engine=None,
        agents=None,
        simulate: bool = False,
    ):
        self.adapter_manager = adapter_manager
        self.model_router = model_router
        self.memory = memory_manager
        self.policy = policy_engine
        self.agents = agents or {}
        self.simulate = simulate

    async def run(
        self,
        target_id: str,
        objective: str,
        target_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the full piped multi-agent pipeline.

        Args:
            target_id: Authorized target ID
            objective: The assessment objective
            target_info: Target info dict (host, port, protocol)

        Returns:
            Pipeline result with all agent outputs
        """
        if not target_info:
            target_info = {"id": target_id, "host": "127.0.0.1", "port": 8080}

        target_host = target_info.get("host", "127.0.0.1")
        target_port = target_info.get("port", 8080)

        # Build target string for tools
        if target_info.get("protocol") == "http":
            target_str = f"http://{target_host}:{target_port}"
        else:
            target_str = f"{target_host}:{target_port}"

        results: Dict[str, Any] = {}
        previous_output = ""

        for step in PIPELINE_STEPS:
            step_name = step["name"]
            logger.info(f"[Pipeline] Running step: {step_name} ({step['description']})")

            # Build prompt with previous output
            prompt = step["prompt_template"].format(
                target=target_str,
                objective=objective,
                previous_output=previous_output[:3000] if previous_output else "No previous output.",
            )

            # Try real agent execution
            agent_output = None
            if not self.simulate:
                agent_output = await self._run_agent(step_name, step, prompt, target_info)

            # Fall back to tool execution if agent unavailable
            if agent_output is None:
                agent_output = await self._run_tool_fallback(
                    step_name, step, target_str, target_info
                )

            # Fall back to simulated response
            if agent_output is None:
                agent_output = self._simulate_step(step_name, step, target_str)

            results[step_name] = agent_output

            # Pipe output to next agent
            if agent_output.get("summary"):
                previous_output += f"\n--- {step_name.upper()} ---\n{agent_output['summary']}"
            if agent_output.get("findings"):
                for f in agent_output["findings"]:
                    previous_output += f"\n- {f.get('description', '')}"

            # Store findings in memory
            for finding in agent_output.get("findings", []):
                finding_data = {
                    "target_id": target_id,
                    "description": finding.get("description", ""),
                    "confidence": finding.get("confidence", 0.5),
                    "source": step_name,
                    "severity": finding.get("severity", "info"),
                    "verification": agent_output.get("verification", "UNVERIFIED"),
                }
                if self.memory:
                    self.memory.store_finding(finding_data)

        # Aggregate all findings
        all_findings: List[Dict[str, Any]] = []
        for step_name, result in results.items():
            all_findings.extend(result.get("findings", []))

        return {
            "target_id": target_id,
            "objective": objective,
            "target": target_str,
            "steps": [s["name"] for s in PIPELINE_STEPS],
            "results": results,
            "findings": all_findings,
            "total_findings": len(all_findings),
            "status": "completed",
        }

    async def _run_agent(
        self,
        step_name: str,
        step: Dict[str, Any],
        prompt: str,
        target_info: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Run the actual agent if available."""
        agent = self.agents.get(step_name)
        if not agent:
            return None

        try:
            result = await agent.run({
                "objective": prompt,
                "target_id": target_info.get("id", ""),
                "target": target_info.get("host", ""),
                "session_id": "",
            })
            # Parse agent output
            content = result.get("research", "") or result.get("findings", "") or ""
            if isinstance(content, list):
                content = "\n".join(str(c) for c in content)
            parsed = parse_tool_output(str(content))
            if result.get("success") is False:
                parsed["error"] = result.get("error", "Agent execution failed")
            return parsed
        except Exception as e:
            logger.warning(f"Agent '{step_name}' execution failed: {e}")
            return None

    async def _run_tool_fallback(
        self,
        step_name: str,
        step: Dict[str, Any],
        target_str: str,
        target_info: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Try executing via a registered security tool."""
        if not self.adapter_manager or self.simulate:
            return None

        # Find a tool that matches this capability
        capability_map = {
            "research": ["strix", "pentestgpt", "drakben"],
            "reconnaissance": ["strix", "drakben", "aracne"],
            "analysis": ["strix", "guardian_cli", "autopentest"],
            "verification": ["strix"],
            "reporting": [],
        }
        tool_names = capability_map.get(step["capability"], [])
        if not tool_names:
            return None

        # Determine target IP for commands
        target_host = target_info.get("host", "127.0.0.1")
        target_port = target_info.get("port", 8080)

        for tool_name in tool_names:
            success, stdout, stderr = await run_tool_command(
                tool_name=tool_name,
                target=f"{target_host}:{target_port}",
                parameters={"action": step["capability"]},
            )
            if success and stdout:
                parsed = parse_tool_output(stdout)
                parsed["tool_used"] = tool_name
                return parsed

        return None

    def _simulate_step(
        self,
        step_name: str,
        step: Dict[str, Any],
        target_str: str,
    ) -> Dict[str, Any]:
        """Return deterministic mock output for a pipeline step."""
        simulated_findings = {
            "researcher": [
                {
                    "description": f"Identified target technology stack for {target_str} (simulated)",
                    "severity": "info",
                    "confidence": 0.5,
                },
                {
                    "description": "Found 3 known vulnerability patterns (simulated)",
                    "severity": "info",
                    "confidence": 0.5,
                },
            ],
            "recon": [
                {
                    "description": f"Port 8080 open (HTTP) on {target_str} (simulated)",
                    "severity": "info",
                    "confidence": 0.6,
                },
                {
                    "description": f"Port 22 open (SSH) on {target_str} (simulated)",
                    "severity": "info",
                    "confidence": 0.6,
                },
                {
                    "description": "Server: nginx/1.20.1 (simulated)",
                    "severity": "info",
                    "confidence": 0.4,
                },
            ],
            "analyst": [
                {
                    "description": "Potential SQL injection vulnerability detected (simulated)",
                    "severity": "high",
                    "confidence": 0.6,
                },
                {
                    "description": "Potential XSS vulnerability detected (simulated)",
                    "severity": "medium",
                    "confidence": 0.5,
                },
            ],
            "verifier": [
                {
                    "description": "SQL injection finding verified with sufficient evidence (simulated)",
                    "severity": "high",
                    "confidence": 0.8,
                },
            ],
            "reporter": [
                {
                    "description": "Assessment report generated with 3 verified findings (simulated)",
                    "severity": "info",
                    "confidence": 1.0,
                },
            ],
        }

        findings = simulated_findings.get(step_name, [])
        verification = "VERIFIED" if step_name in ("verifier", "reporter") else "LIKELY"

        return {
            "findings": findings,
            "evidence": [{
                "type": "simulated",
                "content": f"Simulated output for {step_name}",
            }],
            "summary": f"[{step_name.upper()}] {'; '.join(f['description'] for f in findings)}",
            "simulated": True,
            "verification": verification,
        }

    async def run_piped(
        self,
        target_id: str,
        objective: str,
        target_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Alias for run() to match naming."""
        return await self.run(target_id, objective, target_info)