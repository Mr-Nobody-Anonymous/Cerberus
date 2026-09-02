"""Recon agent prompt templates. Prompts live here, not in the gateway."""


def build_recon_analysis_prompt(target: str, scope: str, depth: str,
                                recon_tools, tool_output: str) -> str:
    """Build the recon-analysis prompt for the ReconAgent run loop."""
    tools = ", ".join(recon_tools) if recon_tools else "none registered"
    prompt = (
        f"You are a reconnaissance analyst. Analyze the following recon "
        f"data and extract key findings.\n\n"
        f"Target: {target}\n"
        f"Scope: {scope}\n"
        f"Depth: {depth}\n"
        f"Available tools: {tools}\n"
        f"\nProvide a structured summary of potential attack surfaces, "
        f"open ports, services, and interesting findings."
    )
    if tool_output:
        prompt += f"\n\nTool output:\n{tool_output[:3000]}"
    else:
        prompt += ("\n\nNo automated tool output available "
                   "(tools may not be configured).")
    return prompt
