"""
Capability Registry for the Cyber AI platform.

Maps capabilities to providers (agents, tools, models) so the
orchestrator can reason about what it needs rather than which
specific repository to use.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CapabilityProvider:
    """A provider that can fulfill a capability."""

    name: str
    type: str  # "agent", "tool", "model"
    description: str = ""
    priority: int = 100  # Lower = higher priority
    status: str = "UNKNOWN"  # AVAILABLE, UNAVAILABLE, UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapabilityRegistry:
    """
    Maps capabilities to providers.

    The orchestrator asks "I need reconnaissance" and the registry
    returns the best available providers for that capability.
    """

    # Default capability -> provider mappings
    DEFAULT_CAPABILITIES: Dict[str, List[Dict[str, Any]]] = {
        "reconnaissance": [
            {"name": "strix", "type": "tool", "priority": 10},
            {"name": "pentagi", "type": "tool", "priority": 20},
            {"name": "recon", "type": "agent", "priority": 30},
        ],
        "source_analysis": [
            {"name": "cai", "type": "tool", "priority": 10},
            {"name": "local-coder", "type": "model", "priority": 20},
            {"name": "analyst", "type": "agent", "priority": 30},
        ],
        "web_testing": [
            {"name": "darkmoon", "type": "tool", "priority": 10},
            {"name": "pentagi", "type": "tool", "priority": 20},
        ],
        "tool_execution": [
            {"name": "hexstrike", "type": "tool", "priority": 10},
            {"name": "mcpstrike", "type": "tool", "priority": 20},
            {"name": "cyberstrikeai", "type": "tool", "priority": 30},
        ],
        "research": [
            {"name": "pentestgpt", "type": "tool", "priority": 10},
            {"name": "researcher", "type": "agent", "priority": 20},
            {"name": "research_model", "type": "model", "priority": 30},
            {"name": "autopentest", "type": "tool", "priority": 40},
            {"name": "luan1aoagent", "type": "tool", "priority": 50},
            {"name": "guardian_cli", "type": "tool", "priority": 60},
            {"name": "h4cker", "type": "tool", "priority": 70},
            {"name": "kali_pentest", "type": "tool", "priority": 80},
        ],
        "planning": [
            {"name": "planner", "type": "agent", "priority": 10},
            {"name": "local_reasoner", "type": "model", "priority": 20},
            {"name": "autopentest", "type": "tool", "priority": 30},
            {"name": "pentestgpt", "type": "tool", "priority": 40},
            {"name": "luan1aoagent", "type": "tool", "priority": 50},
        ],
        "verification": [
            {"name": "verifier", "type": "agent", "priority": 10},
            {"name": "local_reasoner", "type": "model", "priority": 20},
        ],
        "code_generation": [
            {"name": "local_coder", "type": "model", "priority": 10},
            {"name": "coder", "type": "agent", "priority": 20},
        ],
        "analysis": [
            {"name": "analyst", "type": "agent", "priority": 10},
            {"name": "pentagi", "type": "tool", "priority": 20},
            {"name": "local_reasoner", "type": "model", "priority": 30},
            {"name": "drakben", "type": "tool", "priority": 40},
            {"name": "luan1aoagent", "type": "tool", "priority": 50},
            {"name": "guardian_cli", "type": "tool", "priority": 60},
        ],
        "reporting": [
            {"name": "reporter", "type": "agent", "priority": 10},
            {"name": "local_fast", "type": "model", "priority": 20},
            {"name": "guardian_cli", "type": "tool", "priority": 30},
        ],
        "exploitation": [
            {"name": "pentagi", "type": "tool", "priority": 10},
            {"name": "darkmoon", "type": "tool", "priority": 20},
            {"name": "pentestagent", "type": "tool", "priority": 30},
            {"name": "aracne", "type": "tool", "priority": 40},
            {"name": "drakben", "type": "tool", "priority": 50},
        ],
        "vulnerability_scanning": [
            {"name": "strix", "type": "tool", "priority": 10},
            {"name": "pentagi", "type": "tool", "priority": 20},
        ],
        "static_analysis": [
            {"name": "penclaw", "type": "tool", "priority": 10},
            {"name": "cai", "type": "tool", "priority": 20},
        ],
        "secret_detection": [
            {"name": "penclaw", "type": "tool", "priority": 10},
        ],
        "dynamic_scanning": [
            {"name": "penclaw", "type": "tool", "priority": 10},
            {"name": "strix", "type": "tool", "priority": 20},
        ],
        "summarization": [
            {"name": "local_fast", "type": "model", "priority": 10},
            {"name": "reporter", "type": "agent", "priority": 20},
        ],
        "reasoning": [
            {"name": "local_reasoner", "type": "model", "priority": 10},
            {"name": "planner", "type": "agent", "priority": 20},
        ],
    }

    def __init__(self):
        self._capabilities: Dict[str, List[CapabilityProvider]] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default capability mappings."""
        for capability, providers in self.DEFAULT_CAPABILITIES.items():
            self._capabilities[capability] = [
                CapabilityProvider(
                    name=p["name"],
                    type=p["type"],
                    priority=p.get("priority", 100),
                    status=p.get("status", "UNKNOWN"),
                )
                for p in providers
            ]

    def get_providers(self, capability: str) -> List[CapabilityProvider]:
        """Get all providers for a capability, sorted by priority."""
        providers = self._capabilities.get(capability, [])
        return sorted(providers, key=lambda p: p.priority)

    def get_best_provider(self, capability: str) -> Optional[CapabilityProvider]:
        """Get the highest-priority provider for a capability."""
        providers = self.get_providers(capability)
        return providers[0] if providers else None

    def get_available_providers(self, capability: str) -> List[CapabilityProvider]:
        """Get only available providers for a capability."""
        return [
            p for p in self.get_providers(capability)
            if p.status in ("AVAILABLE", "UNKNOWN")
        ]

    def register_provider(self, capability: str, provider: CapabilityProvider) -> None:
        """Register a provider for a capability."""
        if capability not in self._capabilities:
            self._capabilities[capability] = []
        self._capabilities[capability].append(provider)
        logger.info(f"Registered provider {provider.name} for capability {capability}")

    def update_provider_status(self, capability: str, provider_name: str, status: str) -> None:
        """Update the status of a provider for a capability."""
        for provider in self._capabilities.get(capability, []):
            if provider.name == provider_name:
                provider.status = status
                return

    def list_capabilities(self) -> List[str]:
        """List all registered capabilities."""
        return sorted(self._capabilities.keys())

    def to_dict(self) -> Dict[str, Any]:
        """Return the registry as a dict."""
        return {
            capability: [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "priority": p.priority,
                    "status": p.status,
                }
                for p in providers
            ]
            for capability, providers in self._capabilities.items()
        }