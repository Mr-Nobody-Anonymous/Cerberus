"""H3 — Profile-aware model routing tests.

Covers:
- attach_profile() stores the profile; route() stays unchanged without
  overrides or a serving-check
- profile_overrides from routing.yaml take precedence for the matching
  profile only
- _demote_unservable promotes the first servable fallback when the
  preferred alias is unservable (rich entries only)
- simple string entries are never demoted (nothing to demote to)
- route_with_fallback() reflects demotion
- Orchestrator attaches the detected profile on construction (smoke)
"""

import pytest

from cyberai.orchestrator.routing.model_router import ModelRouter


def make_router(tmp_path, routes=None, profile_overrides=None):
    """Build a router from an explicit routing.yaml."""
    import yaml

    cfg = {
        "routes": routes or {
            "planning": {
                "preferred": "local_reasoner",
                "fallback": "cloud_reasoner",
                "local_fallback": "local_fast",
            },
            "summarization": "local_fast",
        },
    }
    if profile_overrides:
        cfg["profile_overrides"] = profile_overrides
    p = tmp_path / "routing.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    return ModelRouter(config_path=p)


# ---------------------------------------------------------------------------
# attach_profile basics
# ---------------------------------------------------------------------------
def test_attach_profile_stored(tmp_path):
    r = make_router(tmp_path)
    assert r.profile is None
    r.attach_profile("CLOUD")
    assert r.profile == "CLOUD"


def test_route_unchanged_without_overrides(tmp_path):
    r = make_router(tmp_path)
    r.attach_profile("MINIMAL")
    # No override configured for MINIMAL -> normal route
    assert r.route("planning") == "local_reasoner"


# ---------------------------------------------------------------------------
# profile_overrides
# ---------------------------------------------------------------------------
def test_profile_override_applies(tmp_path):
    r = make_router(tmp_path, profile_overrides={
        "MINIMAL": {"planning": "cloud_reasoner"},
    })
    r.attach_profile("MINIMAL")
    assert r.route("planning") == "cloud_reasoner"


def test_profile_override_only_for_matching_profile(tmp_path):
    r = make_router(tmp_path, profile_overrides={
        "MINIMAL": {"planning": "cloud_reasoner"},
    })
    r.attach_profile("HYBRID")  # different profile -> override ignored
    assert r.route("planning") == "local_reasoner"


def test_profile_override_falls_through_for_other_task_types(tmp_path):
    r = make_router(tmp_path, profile_overrides={
        "MINIMAL": {"planning": "cloud_reasoner"},
    })
    r.attach_profile("MINIMAL")
    # summarization has no MINIMAL override -> normal route
    assert r.route("summarization") == "local_fast"


# ---------------------------------------------------------------------------
# serving-check demotion
# ---------------------------------------------------------------------------
def test_unservable_preferred_demotes_to_servable_fallback(tmp_path):
    r = make_router(tmp_path)
    r.attach_profile("CLOUD", alias_serving=lambda a: a != "local_reasoner")
    # local_reasoner unservable -> cloud_reasoner (first servable) promoted
    assert r.route("planning") == "cloud_reasoner"


def test_servable_preferred_not_demoted(tmp_path):
    r = make_router(tmp_path)
    r.attach_profile("CLOUD", alias_serving=lambda a: True)
    assert r.route("planning") == "local_reasoner"


def test_all_unservable_keeps_preferred(tmp_path):
    r = make_router(tmp_path)
    r.attach_profile("CLOUD", alias_serving=lambda a: False)
    # Nothing servable -> keep the configured preferred (gateway will report
    # the failure honestly rather than the router guessing)
    assert r.route("planning") == "local_reasoner"


def test_simple_string_entry_never_demoted(tmp_path):
    r = make_router(tmp_path)
    r.attach_profile("MINIMAL", alias_serving=lambda a: False)
    # summarization is a simple string entry — returned as-is
    assert r.route("summarization") == "local_fast"


def test_route_with_fallback_reflects_demotion(tmp_path):
    r = make_router(tmp_path)
    r.attach_profile("CLOUD", alias_serving=lambda a: a != "local_reasoner")
    chain = r.route_with_fallback("planning")
    assert chain[0] == "cloud_reasoner"
    assert "local_reasoner" not in chain


# ---------------------------------------------------------------------------
# Orchestrator integration (smoke)
# ---------------------------------------------------------------------------
def test_orchestrator_attaches_profile():
    pytest.importorskip("cyberai.orchestrator")
    from cyberai.orchestrator.orchestrator import Orchestrator

    orch = Orchestrator()
    try:
        assert orch.model_router.profile in (
            "MINIMAL", "CLOUD", "HYBRID", "LOCAL", "SERVER", None)
    finally:
        orch.memory.close()
        orch.policy.close()
