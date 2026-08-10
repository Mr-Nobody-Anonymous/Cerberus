import type { ScanReport, TriageFinding } from "../types/index.js";

export function renderMarkdownReport(report: ScanReport): string {
  const lines: string[] = [];
  lines.push("# PenClaw Security Report");
  lines.push(`**Target:** \`${report.targetProfile.target}\``);
  lines.push(`**Date:** ${report.generatedAt}`);
  lines.push(`**Duration:** ${formatDuration(report.durationMs)}`);
  lines.push("");
  lines.push("## Summary");
  lines.push(`- Critical: ${report.counts.critical}`);
  lines.push(`- High: ${report.counts.high}`);
  lines.push(`- Medium: ${report.counts.medium}`);
  lines.push(`- Low: ${report.counts.low}`);
  lines.push(`- Informational: ${report.counts.info}`);
  lines.push("");
  lines.push("## Target Profile");
  lines.push(`- Languages: ${report.targetProfile.languages.map((language) => `${language.name} (${language.files})`).join(", ") || "Unknown"}`);
  lines.push(`- Frameworks: ${report.targetProfile.frameworks.join(", ") || "None detected"}`);
  lines.push(`- Package managers: ${report.targetProfile.packageManagers.join(", ") || "None detected"}`);
  lines.push(`- Files analyzed: ${report.targetProfile.fileCount}`);
  lines.push("");

  if (report.findings.length === 0) {
    lines.push("## Findings");
    lines.push("No actionable findings survived triage.");
  } else {
    lines.push("## Findings");
    for (const finding of report.findings) {
      lines.push(renderFinding(finding));
    }
  }

  if (report.warnings.length > 0) {
    lines.push("");
    lines.push("## Warnings");
    for (const warning of report.warnings) {
      lines.push(`- ${warning}`);
    }
  }

  lines.push("");
  return lines.join("\n");
}

/** Wrap untrusted content in a fence longer than any backtick run inside it. */
function safeFence(content: string, lang = "text"): string {
  const longestRun = (content.match(/`+/g) ?? [""]).reduce((m, r) => Math.max(m, r.length), 0);
  const fence = "`".repeat(Math.max(3, longestRun + 1));
  return `${fence}${lang}\n${content}\n${fence}`;
}

/** Escape characters that break out of inline Markdown/HTML contexts. */
function inlineSafe(text: string): string {
  return text.replace(/[<>`]/g, (c) => ({ "<": "&lt;", ">": "&gt;", "`": "\\`" }[c] ?? c));
}

/** Neutralize content placed inside an inline `code span`. Backslashes are literal
 *  inside code spans, so a backtick would still close the span — replace it. */
function codeSpanSafe(text: string): string {
  return text.replace(/`/g, "ʼ").replace(/[\r\n]+/g, " ");
}

function renderFinding(finding: TriageFinding): string {
  const location = finding.locations[0];
  const sections = [
    `### [${finding.severity.toUpperCase()}] ${inlineSafe(finding.title)}`,
    `**Rule:** \`${codeSpanSafe(finding.ruleId)}\``,
    `**Source:** ${inlineSafe(finding.source)}`,
    `**Location:** \`${codeSpanSafe(location?.path ?? "unknown")}${location?.line ? `:${location.line}` : ""}\``,
    `**Confidence:** ${Math.round(finding.confidence * 100)}%`,
    "",
    `**Description:** ${inlineSafe(finding.description)}`,
    "",
    `**Triage:** ${inlineSafe(finding.reasoning)}`,
    "",
    "**Proof of Concept:**",
    safeFence(finding.proofOfConcept),
    "",
    "**Fix Suggestion:**",
    safeFence(finding.fixSuggestion),
  ];

  if (location?.snippet) {
    sections.push("", "**Evidence:**", safeFence(location.snippet));
  }

  return sections.join("\n");
}

function formatDuration(durationMs: number): string {
  const seconds = Math.round(durationMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`;
}
