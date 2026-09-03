"""
Adapter for Guardian (guardian-cli).
Implements the SecurityToolAdapter interface using SandboxedAdapter for safety.
"""

import asyncio
import logging
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.orchestrator.adapters.base import (
    AdapterCapability,
    AdapterResult,
    SandboxedAdapter,
)
from cyberai.security.sandbox import run_subprocess

logger = logging.getLogger(__name__)


class Adapter(SandboxedAdapter):
    """
    Real implementation of the Guardian CLI adapter.
    Uses SandboxedAdapter for policy enforcement and sandboxed execution.
    """

    name = "guardian-cli"
    version = "0.1.0"
    description = "AI-Powered Penetration Testing Automation CLI Tool"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # The directory where the guardian-cli source code resides
        self._adapter_dir = Path(__file__).resolve().parent
        # Command to run the CLI. We assume it's run as a module.
        self._cli_command = ["python", "-m", "cli.main"]