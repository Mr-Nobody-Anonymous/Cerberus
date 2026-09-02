"""Reporter agent prompt templates. Prompts live here, not in the gateway."""


def build_report_prompt(objective: str, target_id: str, now: str,
                        findings_summary: str, analysis: str,
                        evidence_summary: str) -> str:
    """Build the report-generation prompt for the ReporterAgent run loop."""
    return (
        f"You are a security report writer. Generate a professional penetration "
        f"testing report based on the following assessment data.\n\n"
        f"Objective: {objective}\n"
        f"Target: {target_id}\n"
        f"Date: {now}\n"
        f"\n--- FINDINGS ---\n{findings_summary}"
        f"\n--- ANALYSIS ---\n{analysis if analysis else 'No analysis provided.'}"
        f"\n--- EVIDENCE ---\n{evidence_summary}"
        f"\n\nGenerate a structured report with:\n"
        f"1. Executive Summary\n"
        f"2. Methodology\n"
        f"3. Findings (with severity, evidence, and verification status)\n"
        f"4. Recommendations\n"
        f"5. Conclusion\n"
        f"\nUse markdown formatting."
    )
