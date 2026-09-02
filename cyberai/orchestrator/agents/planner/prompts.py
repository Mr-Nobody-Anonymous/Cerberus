"""Planner agent prompt templates. Prompts live here, not in the gateway."""


def build_planning_prompt(objective: str, target_id: str, constraints,
                          experiences_text: str) -> str:
    """Build the planning prompt for the PlannerAgent run loop."""
    return (
        f"You are a security planning agent. Create a detailed, step-by-step "
        f"security assessment plan for the following objective.\n\n"
        f"Objective: {objective}\n"
        f"Target: {target_id}\n"
        f"Constraints: {', '.join(constraints) if constraints else 'none'}\n"
        f"\nRelevant past experiences:\n"
        f"{experiences_text if experiences_text else 'None found.'}\n"
        f"\nGenerate a JSON plan with a 'steps' array. Each step should have:\n"
        f"  - step: integer step number\n"
        f"  - action: one of: recon, research, analysis, code_analysis, "
        f"code_generation, exploitation, verification, reporting\n"
        f"  - tool: suggested tool name from the registry\n"
        f"  - description: what to do in this step\n"
        f"  - model: the task type for model routing\n"
        f"\nRespond with valid JSON only."
    )
