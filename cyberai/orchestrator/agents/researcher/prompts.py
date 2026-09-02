"""Researcher agent prompt templates. Prompts live here, not in the gateway."""


def build_research_prompt(target: str, topic: str, target_id: str,
                          experiences_text: str) -> str:
    """Build the research prompt for the ResearcherAgent run loop."""
    return (
        f"You are a cybersecurity research agent. Research the following topic.\n\n"
        f"Target: {target}\n"
        f"Topic: {topic}\n"
        f"Target ID: {target_id}\n"
        f"\nPast relevant experiences:\n"
        f"{experiences_text if experiences_text else 'None found.'}\n"
        f"\nProvide a structured summary of:\n"
        f"1. What is known about this target/topic\n"
        f"2. Known vulnerabilities or weaknesses\n"
        f"3. Recommended next steps\n"
        f"4. Tools that would be useful for further investigation\n"
    )
