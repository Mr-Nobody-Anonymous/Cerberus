import { describe, it, expect } from "vitest";
import { parseTrivyFindings } from "../src/scanners/trivy-scanner.js";
import { parseSemgrepFindings } from "../src/scanners/semgrep-scanner.js";
import { parseNucleiOutput } from "../src/dynamic/nuclei-scanner.js";

describe("parseTrivyFindings", () => {
  it("maps vulnerabilities, secrets, and misconfigurations to RawFindings", () => {
    const findings = parseTrivyFindings({
      Results: [
        {
          Target: "package-lock.json",
          Vulnerabilities: [
            {
              VulnerabilityID: "CVE-2021-23337",
              Title: "Prototype pollution in lodash",
              Description: "Command injection via template.",
              Severity: "CRITICAL",
              PrimaryURL: "https://example.com/CVE-2021-23337",
              PkgName: "lodash",
              InstalledVersion: "4.17.20",
            },
          ],
          Secrets: [
            {
              RuleID: "aws-access-key-id",
              Title: "AWS Access Key",
              Severity: "HIGH",
              StartLine: 12,
              EndLine: 12,
              Match: "AKIA...",
            },
          ],
          Misconfigurations: [
            {
              ID: "DS002",
              Title: "Image user should not be root",
              Description: "Running as root is dangerous.",
              Severity: "MEDIUM",
              PrimaryURL: "https://example.com/DS002",
            },
          ],
        },
      ],
    });

    expect(findings).toHaveLength(3);
    expect(findings.every((f) => f.source === "trivy")).toBe(true);

    const vuln = findings.find((f) => f.category === "dependency");
    expect(vuln).toBeDefined();
    expect(vuln?.severity).toBe("critical");
    expect(vuln?.ruleId).toBe("CVE-2021-23337");
    expect(vuln?.metadata?.packageName).toBe("lodash");
    expect(vuln?.metadata?.installedVersion).toBe("4.17.20");
    expect(vuln?.locations[0]?.path).toBe("package-lock.json");

    const secret = findings.find((f) => f.category === "secret");
    expect(secret).toBeDefined();
    expect(secret?.severity).toBe("high");
    expect(secret?.locations[0]?.line).toBe(12);

    const misconfig = findings.find((f) => f.category === "misconfiguration");
    expect(misconfig).toBeDefined();
    expect(misconfig?.severity).toBe("medium");
    expect(misconfig?.ruleId).toBe("DS002");
  });

  it("returns no findings for an empty result", () => {
    expect(parseTrivyFindings({})).toEqual([]);
  });
});

describe("parseSemgrepFindings", () => {
  it("maps a result and aliases ERROR severity to high", () => {
    const findings = parseSemgrepFindings({
      results: [
        {
          check_id: "javascript.express.security.audit.xss",
          path: "src/app.js",
          start: { line: 42, col: 7 },
          extra: {
            message: "Detected potential XSS.",
            lines: "res.send(userInput)",
            severity: "ERROR",
            metadata: {
              category: "security",
              confidence: "HIGH",
              references: ["https://owasp.org/xss"],
            },
          },
        },
      ],
    });

    expect(findings).toHaveLength(1);
    const finding = findings[0]!;
    expect(finding.source).toBe("semgrep");
    // Task 9 alias mapping: semgrep "ERROR" -> "high"
    expect(finding.severity).toBe("high");
    expect(finding.ruleId).toBe("javascript.express.security.audit.xss");
    expect(finding.locations[0]?.line).toBe(42);
    expect(finding.locations[0]?.column).toBe(7);
    expect(finding.category).toBe("security");
  });
});

describe("parseNucleiOutput", () => {
  it("parses a JSONL line into a RawFinding", () => {
    const line = JSON.stringify({
      "template-id": "CVE-2021-44228",
      info: {
        name: "Apache Log4j RCE",
        description: "Log4Shell remote code execution.",
        severity: "critical",
        reference: ["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"],
        tags: ["cve", "rce", "log4j"],
      },
      "matched-at": "https://target.example.com/api",
      "matcher-name": "status",
      "extracted-results": ["payload-echo"],
      host: "target.example.com",
      type: "http",
      timestamp: "2026-07-25T00:00:00Z",
    });

    const findings = parseNucleiOutput(line);

    expect(findings).toHaveLength(1);
    const finding = findings[0]!;
    expect(finding.source).toBe("nuclei");
    expect(finding.severity).toBe("critical");
    expect(finding.ruleId).toBe("CVE-2021-44228");
    expect(finding.category).toBe("dependency"); // cve tag
    expect(finding.locations[0]?.path).toBe("https://target.example.com/api");
    expect(finding.references).toContain("https://nvd.nist.gov/vuln/detail/CVE-2021-44228");
  });

  it("skips malformed JSON lines and empty output", () => {
    expect(parseNucleiOutput("")).toEqual([]);
    expect(parseNucleiOutput("not-json\n{broken")).toEqual([]);
  });
});
