# ADR-0001: Extract vendored LiteLLM and A-Evolve into pinned dependencies

- **Status:** Accepted
- **Date:** 2026-09-11
- **Supersedes:** the pre-2.0 vendoring approach

## Context

The repository previously vendored the **entire LiteLLM repository**
(including its own test suite, cookbooks, Terraform, and dashboard UI)
under `cyberai/llm_gateway/litellm`, and the full **A-Evolve** framework
under `cyberai/evolution/a-evolve`. Together they added ~8,600 files and
~3M lines that:

- dominated TODO/FIXME search noise (401 of 401 hits in `cyberai/**`),
- inflated the repo and every clone/checkout,
- complicated upgrades (no clear boundary between our code and theirs),
- were only used through narrow import surfaces.

## Decision

Remove both vendored trees and replace them with pinned dependencies:

- `litellm==1.97.0` (pinned exact version in `pyproject.toml`)
- A-Evolve consumed through its published package interface

The LLM gateway talks to providers over its own transport chain
(LiteLLM proxy → direct Ollama → direct provider API over raw
`httpx`); no provider SDKs are imported anywhere, so the `cloud`
extra in `pyproject.toml` remains an intentionally empty,
self-documenting placeholder.

## Consequences

- **Repo shrinks by ~8,600 files / ~3M lines**; TODO/FIXME searches now
  only surface real first-party items.
- Upgrades become a version-bump in `pyproject.toml` instead of a
  tree re-vendor.
- Reproducibility is preserved via the exact pin.
- The dash-named legacy directory `cyberai/llm-gateway/` (kebab→snake
  rename leftover) was deleted as part of this work.
