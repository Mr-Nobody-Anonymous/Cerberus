"""H2 — Hardware detection and execution-profile tests.

Covers:
- classify() mapping rules for all five profiles
- CERBERUS_PROFILE env override (valid + invalid values)
- detect_hardware() end-to-end on the real machine (smoke, no asserts on
  specific hardware — CI machines differ)
- format_report() output shape
- probes degrade gracefully (RAM unknown -> note, never a crash)

No external services required; nvidia-smi absence is expected on CI.
"""

import os

import pytest

from cyberai.llm_gateway.hardware import (
    HardwareProfile,
    PROFILE_ORDER,
    PROFILE_DESCRIPTIONS,
    classify,
    detect_hardware,
    format_report,
)


def make_hp(ram_gb, gpus=None):
    return HardwareProfile(
        os="Windows",
        cpu_count=8,
        ram_gb=ram_gb,
        gpus=gpus or [],
        total_vram_gb=sum(g["vram_gb"] for g in (gpus or [])),
    )


# ---------------------------------------------------------------------------
# classify() — the five profiles
# ---------------------------------------------------------------------------
def test_classify_minimal():
    assert classify(make_hp(4)) == "MINIMAL"
    assert classify(make_hp(6)) == "MINIMAL"


def test_classify_cloud():
    assert classify(make_hp(8)) == "CLOUD"
    assert classify(make_hp(12)) == "CLOUD"


def test_classify_hybrid_with_gpu():
    assert classify(make_hp(16, [{"name": "RTX 4060", "vram_gb": 8}])) == "HYBRID"
    assert classify(make_hp(32, [{"name": "RTX 5090", "vram_gb": 32}])) == "HYBRID"


def test_classify_hybrid_strong_cpu_box():
    # 32 GB RAM, no GPU -> still HYBRID (strong CPU-only workstation)
    assert classify(make_hp(32)) == "HYBRID"


def test_classify_local_with_gpu():
    assert classify(make_hp(64, [{"name": "A100", "vram_gb": 80}])) == "LOCAL"


def test_classify_local_big_ram_no_gpu():
    # 96 GB RAM without a GPU can still run large local models
    assert classify(make_hp(96)) == "LOCAL"


def test_classify_server():
    gpus = [{"name": "H100", "vram_gb": 80}, {"name": "H100", "vram_gb": 80}]
    assert classify(make_hp(128, gpus)) == "SERVER"
    assert classify(make_hp(256, gpus * 4)) == "SERVER"


def test_classify_128gb_single_gpu_is_local_not_server():
    # SERVER requires >=2 GPUs
    assert classify(make_hp(128, [{"name": "H100", "vram_gb": 80}])) == "LOCAL"


# ---------------------------------------------------------------------------
# CERBERUS_PROFILE env override
# ---------------------------------------------------------------------------
def test_env_override_valid(monkeypatch):
    monkeypatch.setenv("CERBERUS_PROFILE", "server")
    hp = detect_hardware()
    assert hp.profile == "SERVER"
    assert hp.profile_source == "env"


def test_env_override_invalid_falls_back_to_detection(monkeypatch):
    monkeypatch.setenv("CERBERUS_PROFILE", "TURBO")
    hp = detect_hardware()
    assert hp.profile in PROFILE_ORDER
    assert hp.profile_source == "detected"
    assert any("TURBO" in n for n in hp.notes)


def test_env_override_empty_uses_detection(monkeypatch):
    monkeypatch.setenv("CERBERUS_PROFILE", "")
    hp = detect_hardware()
    assert hp.profile_source == "detected"


# ---------------------------------------------------------------------------
# detect_hardware() smoke test on the real machine
# ---------------------------------------------------------------------------
def test_detect_hardware_smoke():
    hp = detect_hardware()
    assert hp.profile in PROFILE_ORDER
    assert hp.profile_source in ("detected", "env")
    assert hp.cpu_count >= 1
    assert hp.os  # non-empty OS string
    # as_dict round-trips cleanly for JSON output
    d = hp.as_dict()
    assert d["profile"] == hp.profile
    assert isinstance(d["gpus"], list)


def test_format_report_contains_profile():
    hp = detect_hardware()
    report = format_report(hp)
    assert "Execution profile" in report
    assert hp.profile in report
    assert PROFILE_DESCRIPTIONS[hp.profile] in report


def test_profile_order_covers_all_descriptions():
    assert set(PROFILE_ORDER) == set(PROFILE_DESCRIPTIONS.keys())
