# 🦀 PenClaw

**AI-powered penetration testing CLI.** One command → real pentest report with only proven, exploitable findings.

PenClaw combines static analysis, dynamic scanning, and AI-assisted triage into a single tool. Point it at source code or a live URL and get an actionable security report — not a wall of CVE numbers.

> *"Snyk finds CVEs. PenClaw finds exploits."*

---

## Features

### Static Analysis
- **Trivy** filesystem scanning (CVEs, misconfigs)
- **Semgrep** with security rulesets (code patterns)
- **Secret detection** — regex + entropy-based (API keys, tokens, credentials)
- **Target profiling** — auto-detect languages, frameworks, package managers

### Dynamic Scanning
- **Nuclei** vulnerability templates (5,600+ checks)
- **Playwright** browser automation — crawling, form discovery, XSS verification
- **API fuzzing** — SQLi, NoSQLi, command injection, path traversal, IDOR, auth bypass
- **OWASP Top 10** checks — headers, CORS, CSRF, open redirects, SSRF
- **Directory bruteforcing** — common paths, admin panels, backups
- **JWT attacks** — none/alg confusion, weak secret brute-force, claim validation

### AI Triage
- Multi-provider: **Anthropic Claude**, **OpenAI GPT**, **Ollama** (local models)
- AI-generated **reasoning, proof-of-concept, and fix suggestions** for each finding
- Static ↔ dynamic finding correlation

> Severity, confidence, and false-positive likelihood are computed **deterministically** by PenClaw — not by the model. The AI only fills in the reasoning, proof-of-concept, and fix-suggestion text. Active-confirmation results (see below) drive whether a finding is reported at high/critical severity or suppressed.

### Reports
- **Markdown** — human-readable, great for PRs
- **JSON** — machine-parseable, pipe into other tools
- **SARIF** — GitHub Code Scanning integration
- **HTML** — interactive dark-theme dashboard with filtering and confidence bars

---

## Quick Start

```bash
# Install
git clone https://github.com/andupetcu/penclaw.git
cd penclaw
npm install
npm run build

# Scan source code (static)
npx penclaw scan ./my-project --output report.md

# Scan a live URL (dynamic)
npx penclaw scan https://example.com --dynamic --format html -o report.html

# Full scan (static + dynamic)
npx penclaw scan ./my-project https://example.com --full -o report.html
```

### Prerequisites

| Tool | Required For | Install |
|------|-------------|---------|
| Node.js 20+ | Core | [nodejs.org](https://nodejs.org) |
| Trivy | Static CVE scanning | `brew install trivy` |
| Semgrep | Static code analysis | `pip install semgrep` |
| Nuclei | Dynamic vuln templates | `brew install nuclei` |
| Playwright | Browser crawling/XSS | Bundled via npm |

PenClaw gracefully degrades — if a tool is missing, it skips that scanner and reports a warning.

---

## CLI Reference

```
penclaw scan [options] <target...>

Arguments:
  target              Filesystem path(s) or URL(s) to scan

Options:
  -o, --output          Write report to file
  -f, --format          Output format: markdown, json, sarif, html
  --dynamic             Enable dynamic scanning (URL targets)
  --full                Enable both static and dynamic scanning
  --ci                  CI mode with severity-based exit codes
  --fail-on             Min severity to fail in CI (default: high)
  --provider            AI provider: anthropic, openai, ollama
  --model               AI model identifier
  --config              Path to .penclaw.yml config file
  --insecure            Disable TLS certificate verification during crawling (DANGEROUS)
  --allow-private       Allow scanning private/internal/loopback hosts
  --auth-bearer <token> Bearer token for authenticated dynamic scanning
  --auth-cookie <hdr>   Cookie header value for authenticated dynamic scanning
  --auth-bearer-b <tok> Second identity bearer token (enables two-identity IDOR confirmation)
```

### Security & Authentication Flags

| Flag | Description |
|------|-------------|
| `--insecure` | Disables TLS certificate verification during crawling. **DANGEROUS** — may expose credentials to on-path attackers. Certificate verification is **ON** by default. Note: `--insecure` currently affects browser-based crawling only; other HTTP requests always verify TLS. |
| `--allow-private` | Allows scanning private / internal / loopback hosts. The SSRF guard is **ON** by default and blocks these hosts. |
| `--auth-bearer <token>` | Bearer token used for authenticated dynamic scanning. |
| `--auth-cookie <header>` | Cookie header value used for authenticated dynamic scanning. |
| `--auth-bearer-b <token>` | A second identity's bearer token, which enables two-identity IDOR confirmation. |

### Active Confirmation

PenClaw does not report JWT and IDOR issues on suspicion alone — it **actively confirms them against the target** before reporting them at high/critical severity:

- **JWT `alg:none` / expired tokens** — a forged `alg:none` token and any expired token are replayed against protected endpoints. A finding is only escalated (critical/high) if the server actually accepts the crafted/expired token where an unauthenticated request was rejected.
- **IDOR** — confirmation is strongest with two identities: supply `--auth-bearer` and `--auth-bearer-b`, and PenClaw confirms IDOR when identity B can read identity A's resource. With a single identity it can only flag a likely IDOR and nudges you to re-run with `--auth-bearer-b`.

Candidates that cannot be confirmed are marked unconfirmed and suppressed during triage rather than reported as real findings.

### CI Mode

```bash
# Fail the build on high+ severity findings
npx penclaw scan ./src --ci --fail-on high

# Exit codes:
#   0 = clean
#   1 = findings above threshold
#   2 = critical findings
```

---

## Configuration

Create `.penclaw.yml` in your project root:

```yaml
ai:
  provider: anthropic          # anthropic | openai | ollama
  model: claude-sonnet-4-20250514

scan:
  static: true
  dynamic: false
  excludePaths:
    - node_modules/
    - dist/
    - "**/*.test.ts"
  skipDirectoryScan: false
  skipJwtTests: false
  maxConcurrentRequests: 10
  requestDelayMs: 100

output:
  format: markdown
  path: ./report.md
```

AI credentials are read from environment variables:
- `ANTHROPIC_API_KEY` for Claude
- `OPENAI_API_KEY` for GPT
- Ollama runs locally (no key needed)

---

## Architecture

```
src/
├── cli/              # Commander.js CLI entry point
├── config/           # cosmiconfig loader (.penclaw.yml)
├── profiler/         # Target profiling (filesystem + URL fingerprinting)
├── scanners/         # Static scanners (Trivy, Semgrep, secrets)
├── dynamic/          # Dynamic scanners (Nuclei, OWASP, directory, JWT)
├── crawl/            # Playwright browser crawler + API fuzzer
├── triage/           # AI-powered finding triage + PoC generation
├── reporters/        # Output formatters (MD, JSON, SARIF, HTML)
├── types/            # TypeScript interfaces
└── utils/            # Shared utilities
```

### How It Works

1. **Profile** — detect target type (filesystem vs URL), identify stack
2. **Scan** — run applicable scanners in parallel
3. **Triage** — AI reviews raw findings, generates PoCs, suggests fixes
4. **Correlate** — match static findings with dynamic evidence
5. **Report** — render actionable report in chosen format

---

## Examples

### Scan a Node.js project
```bash
npx penclaw scan ./my-api --output security-report.md
```

### Full pentest of a live app
```bash
npx penclaw scan https://staging.myapp.com --full --format html -o pentest.html
```

### CI pipeline (GitHub Actions)
```yaml
- name: Security scan
  run: npx penclaw scan ./src --ci --fail-on high --format sarif -o results.sarif

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```

---

## Roadmap

- [x] **Phase 1** — Static analysis + AI triage MVP
- [x] **Phase 2** — Dynamic testing (Nuclei, Playwright, API fuzzing, OWASP)
- [x] **Phase 2.5** — Real-world pentest parity (payload packs, blind SQLi, JWT attacks, directory brute)
- [ ] **Phase 3** — GitHub Action (`uses: penclaw/scan@v1`)
- [ ] **Phase 4** — Negative-day dependency monitor
- [ ] **Phase 5** — SaaS dashboard

---

## License

MIT

---

## Contributing

PRs welcome. Run `npm test` before submitting.

```bash
npm install
npm run build
npm test
```

---

Built by [Andrei Petcu](https://github.com/andupetcu) and [Kai](https://github.com/andupetcu/penclaw) ⚡
