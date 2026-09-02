"""Analyst agent prompt templates. Prompts live here, not in the gateway."""


def build_analysis_prompt(target_id: str, hypothesis: str, findings_text: str,
                          evidence_text: str, experiences_text: str) -> str:
    """Build the analysis prompt for the AnalystAgent run loop."""
    return (
        f"You are a vulnerability analyst. Analyze the following findings and "
        f"evidence to identify potential security issues and prioritize risks.\n\n"
        f"Target: {target_id}\n"
        f"Hypothesis: {hypothesis if hypothesis else 'None provided'}\n"
        f"\nFindings:\n{findings_text if findings_text else 'No findings provided.'}"
        f"\nEvidence:\n{evidence_text if evidence_text else 'No evidence provided.'}"
        f"\nPast relevant experiences:\n"
        f"{experiences_text if experiences_text else 'None found.'}"
        f"\n\nProvide:\n"
        f"1. Summary of identified risks\n"
        f"2. Risk priority (critical/high/medium/low)\n"
        f"3. Confidence level for each finding\n"
        f"4. Recommended verification steps"
    )
