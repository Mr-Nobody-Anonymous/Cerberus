# Architecture Decision Records

ADRs capture the *why* behind significant architectural decisions in
Cerberus. Each record is immutable once accepted; a superseded decision
gets a new ADR that references the old one.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-0001](ADR-0001-extract-vendored-litellm-a-evolve.md) | Extract vendored LiteLLM and A-Evolve into pinned dependencies | Accepted |
| [ADR-0002](ADR-0002-all-adapters-execute-through-sandboxedadapter.md) | All tool adapters execute through SandboxedAdapter | Accepted |

## Writing a new ADR

1. Copy the numbering scheme: `ADR-NNNN-short-slug.md`.
2. Sections: **Context** (the forces at play), **Decision** (what we
   chose), **Consequences** (what changes, including drawbacks).
3. Status starts as `Proposed`; flip to `Accepted` once merged, or
   `Superseded by ADR-NNNN` if replaced.
4. Add the entry to the index above.
