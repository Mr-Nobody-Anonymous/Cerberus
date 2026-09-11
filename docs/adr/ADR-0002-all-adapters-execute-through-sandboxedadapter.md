# ADR-0002: All tool adapters execute through SandboxedAdapter

- **Status:** Accepted
- **Date:** 2026-09-11

## Context

Of the 17 vendored tool adapters, only 4–5 had real execution paths.
The rest were thin stubs: `_execute_via_docker()` and `_execute_via_api()`
returned the literal string `"not implemented"`, and `collect_results()`
returned `"stub implementation"`. The capability routing table advertised
tools the platform could reason about but not actually run — the largest
gap between the platform's promise and its behavior.

## Decision

Every adapter (`adapters/<name>/__init__.py`) now subclasses
`SandboxedAdapter` from `cyberai/orchestrator/adapters/base.py`:

- `execute()` is the **only public entry point**. It authorizes the
  target through the policy engine (`cyberai.security.policy_runner.authorize`,
  fails closed) and records evidence via `record_action` **before**
  delegating to the adapter-specific `_do_execute()`.
- `_do_execute()` implements the real integration per adapter:
  CLI subprocess in the sandbox, REST/GraphQL API call, MCP call,
  in-process library import, or documentation search.
- `health_check()` reports one of `AVAILABLE` / `WARN` / `UNAVAILABLE` /
  `ERROR` with the exact prerequisite and start command in the message.
- Dash-named adapter directories (`guardian-cli`, `kali-pentest`) are
  resolved by the `_HyphenAdapterFinder` MetaPathFinder in
  `adapters/__init__.py`.

The policy gate and evidence logging live in the base class and
**cannot be bypassed** by an individual adapter.

## Consequences

- All 17 tools registered in `cyberai/orchestrator/tools.yaml` are now
  backed by real execution paths; no stub patterns remain
  (`git grep 'stub implementation' adapters` returns nothing).
- Every adapter invocation is policy-authorized and evidence-logged
  uniformly, regardless of the underlying integration method.
- Per-adapter integration facts (contract, capabilities, health
  prerequisites, run commands, vendored-update procedure) are documented
  in each `adapters/<name>/INTEGRATION.md`, regenerable via
  `scripts/gen_integration_guides.py`.
- Adapters remain vendored copies (no nested `.git`); updating from
  upstream means re-cloning and re-applying the wrapper, not `git pull`.
