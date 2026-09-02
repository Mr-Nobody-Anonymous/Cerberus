"""Coder agent prompt templates. Prompts live here, not in the gateway."""


def build_code_analysis_prompt(language: str, target_id: str, code: str) -> str:
    """Build the code-analysis prompt for the CoderAgent run loop."""
    return (
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


def build_code_generation_prompt(description: str, language: str,
                                 target_id: str) -> str:
    """Build the code-generation prompt for the CoderAgent run loop."""
    return (
        f"You are a code generation agent. Generate secure code for "
        f"the following specification.\n\n"
        f"Description: {description}\n"
        f"Language: {language}\n"
        f"Target: {target_id}\n"
        f"\nGenerate clean, well-commented code that follows security best practices."
    )
