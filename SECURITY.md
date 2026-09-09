# Security Policy

Cerberus is a security research platform that orchestrates offensive security tooling. Because of its nature, we take security — both of the platform itself and of the systems it touches — extremely seriously.

## 🔒 Scope & Authorized Use

Cerberus is designed **exclusively** for:

- Authorized penetration testing engagements (with written permission)
- Security research in isolated lab environments
- Training and education
- Defensive research (understanding attack techniques to build better defenses)

**Out of scope / prohibited:**

- Using Cerberus against any system without explicit written authorization from the system owner
- Using Cerberus to attack infrastructure you do not own or operate
- Any use that violates applicable computer crime laws (e.g., CFAA, Computer Misuse Act, or equivalents in your jurisdiction)

If you are unsure whether your use case is authorized, it isn't.

## 🛡️ Platform Security Controls

Cerberus enforces safety through several layers:

| Control | Location | Function |
|---|---|---|
| Policy Engine | `cyberai/security/` | Authorization gate — every tool action must pass `is_authorized()` before execution |
| Scope Enforcement | `cyberai/orchestrator/policy/` | Targets must be registered and in-scope before any adapter runs |
| Evidence Logging | `cyberai/orchestrator/evidence/` | All tool actions produce tamper-evident evidence records |
| Audit Trail | `logs/sessions/` | Append-only JSONL audit log of every action |
| Sandbox Execution | `adapters/drakben/` (Docker) | Dangerous tools run in isolated containers where available |

## 🐞 Reporting a Vulnerability

If you discover a security vulnerability **in Cerberus itself** (not in third-party tools it wraps):

1. **Do not** open a public GitHub issue.
2. **Do not** publicly disclose before a fix is released.
3. Contact the maintainer privately via GitHub security advisories:
   - Go to the [repository's Security tab](https://github.com/Mr-Nobody-Anonymous/Cerberus/security/advisories)
   - Click **"Report a vulnerability"**

Please include:

- Description of the vulnerability
- Steps to reproduce (or PoC)
- Affected version/commit
- Potential impact
- Suggested mitigation (if any)

### Response timeline

| Stage | Target |
|---|---|
| Acknowledgment | within 72 hours |
| Triage / severity assessment | within 7 days |
| Fix or mitigation | within 30 days (severity-dependent) |
| Public disclosure | after release, coordinated with reporter |

## 🔐 Secrets Handling

- Never commit API keys, tokens, or credentials. `.env` is gitignored; use `.env.example` as the template.
- LLM provider keys belong in `.env` (`LITELLM_MASTER_KEY`, `OPENAI_API_KEY`, etc.) and are never logged.
- If you accidentally commit a secret, rotate it immediately — removing it from git history does not un-leak it.

## ⚠️ Responsible Disclosure

We follow coordinated disclosure. Reports made in good faith will not result in legal action. We ask researchers to give us reasonable time to remediate before any public disclosure.
