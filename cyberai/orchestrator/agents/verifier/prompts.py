"""Verifier agent prompt templates. Prompts live here, not in the gateway."""


def build_verification_challenge_prompt(conclusion: str, evidence_text: str,
                                        tool_output: str) -> str:
    """Build the LLM challenge prompt used by VerifierAgent.challenge_conclusion."""
    output_section = tool_output[:2000] if tool_output else "None provided"
    return (
        f"You are an independent verification agent. Challenge the following "
        f"conclusion strictly on the evidence provided.\n\n"
        f"Conclusion: {conclusion}\n"
        f"\nEvidence:\n{evidence_text if evidence_text else 'None provided.'}\n"
        f"\nTool output:\n{output_section}\n"
        f"\nAnswer with valid JSON only:\n"
        f'{{"verified": true|false, "challenges": ["..."], '
        f'"reasoning": "..."}}\n'
        f"A finding is only verified if the evidence directly demonstrates it. "
        f"List concrete objections otherwise."
    )
