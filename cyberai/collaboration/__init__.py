"""
Multi-Agent Collaboration for the Cyber AI platform.

Agents contribute to the same task in a pipeline:
Planner -> Researcher -> Recon -> Analysis -> Verifier -> Reporter

Each agent receives only relevant context, not every previous output.
"""

from .pipeline import AgentPipeline, PipelineStep

__all__ = ["AgentPipeline", "PipelineStep"]