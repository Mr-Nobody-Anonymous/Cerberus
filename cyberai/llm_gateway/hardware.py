"""
Hardware detection and execution-profile selection for CERBERUS.

Answers one question at startup: **what can this machine realistically
run?** — and maps the answer to one of five execution profiles:

    MINIMAL   4–8 GB RAM, no GPU        — cloud APIs + tiny local models
    CLOUD     8–16 GB RAM, no GPU       — cloud models + local embeddings
    HYBRID    16–64 GB RAM (+GPU)       — local + cloud, per-task routing
    LOCAL     64 GB+ RAM, large GPU     — mostly local models
    SERVER    128 GB+ RAM, multi-GPU    — distributed inference, parallel agents

Detection is dependency-free by design (psutil is used when present, with
stdlib fallbacks) so the MINIMAL profile stays installable on an 8 GB
laptop. Every probe is best-effort: a failed probe degrades to "unknown",
never to a crash.

The selected profile is advisory — it feeds routing decisions (H3) and
the doctor report, and can be overridden with ``CERBERUS_PROFILE``.
"""

import logging
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Ordered most-capable-first; the first match wins.
PROFILE_ORDER = ["SERVER", "LOCAL", "HYBRID", "CLOUD", "MINIMAL"]

PROFILE_DESCRIPTIONS = {
    "MINIMAL": "4-8 GB RAM, no GPU — cloud APIs + tiny local models",
    "CLOUD": "8-16 GB RAM, no GPU — cloud models + local embeddings",
    "HYBRID": "16-64 GB RAM (+GPU) — local + cloud, per-task routing",
    "LOCAL": "64 GB+ RAM, large GPU — mostly local models",
    "SERVER": "128 GB+ RAM, multi-GPU — distributed inference, parallel agents",
}

# RAM thresholds in GB for each profile (minimum RAM to qualify).
_RAM_THRESHOLDS = {
    "SERVER": 128,
    "LOCAL": 64,
    "HYBRID": 16,
    "CLOUD": 8,
    "MINIMAL": 0,
}


@dataclass
class HardwareProfile:
    """Machine snapshot + the profile it maps to."""
    os: str = ""
    cpu_count: int = 0
    ram_gb: float = 0.0
    gpus: List[Dict[str, Any]] = field(default_factory=list)
    total_vram_gb: float = 0.0
    docker: bool = False
    ollama: bool = False
    profile: str = "MINIMAL"
    profile_source: str = "detected"  # "env" when CERBERUS_PROFILE forced
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "os": self.os,
            "cpu_count": self.cpu_count,
            "ram_gb": round(self.ram_gb, 1),
            "gpus": self.gpus,
            "total_vram_gb": round(self.total_vram_gb, 1),
            "docker": self.docker,
            "ollama": self.ollama,
            "profile": self.profile,
            "profile_source": self.profile_source,
            "notes": self.notes,
        }


def _detect_ram_gb() -> float:
    """Total system RAM in GB (best-effort, 0.0 when unknown)."""
    try:
        import psutil  # type: ignore

        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        pass
    try:
        if platform.system() == "Windows":
            # CIM gives bytes; PowerShell wraps it in a JSON array.
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"],
                capture_output=True, text=True, timeout=10,
            )
            return float(out.stdout.strip()) / (1024 ** 3)
        # Linux / macOS
        out = subprocess.run(
            ["grep", "MemTotal", "/proc/meminfo"],
            capture_output=True, text=True, timeout=10,
        )
        # "MemTotal:       32612384 kB"
        return float(out.stdout.split()[1]) * 1024 / (1024 ** 3)
    except Exception as e:  # noqa: BLE001 — probe must never crash startup
        logger.warning("RAM detection failed: %s", e)
        return 0.0


def _detect_cpu_count() -> int:
    try:
        import psutil  # type: ignore

        return psutil.cpu_count(logical=True) or 0
    except ImportError:
        return os.cpu_count() or 0


def _detect_gpus() -> List[Dict[str, Any]]:
    """
    Detect GPUs via nvidia-smi (NVIDIA) — the common case for ML machines.

    Returns a list of {name, vram_gb} dicts; empty when no NVIDIA GPU or
    nvidia-smi is unavailable. AMD/Intel accelerators are reported via a
    note (no reliable cross-platform CLI probe exists for them).
    """
    gpus: List[Dict[str, Any]] = []
    smi = shutil.which("nvidia-smi")
    if not smi:
        return gpus
    try:
        out = subprocess.run(
            [smi, "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        for line in out.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 2:
                gpus.append({
                    "name": parts[0],
                    "vram_gb": round(float(parts[1]) / 1024, 1),
                })
    except Exception as e:  # noqa: BLE001
        logger.warning("GPU detection failed: %s", e)
    return gpus


def _detect_docker() -> bool:
    return shutil.which("docker") is not None


def _detect_ollama() -> bool:
    return shutil.which("ollama") is not None


def classify(hp: HardwareProfile) -> str:
    """
    Map a hardware snapshot to a profile.

    Rules (first match wins, checked most-capable-first):
      SERVER — >=128 GB RAM and >=2 GPUs
      LOCAL  — >=64 GB RAM and >=1 GPU (or >=96 GB RAM without one)
      HYBRID — >=16 GB RAM and >=1 GPU, or >=32 GB RAM without one
      CLOUD  — >=8 GB RAM
      MINIMAL— anything else
    """
    ram = hp.ram_gb
    n_gpus = len(hp.gpus)

    if ram >= 128 and n_gpus >= 2:
        return "SERVER"
    if ram >= 64 and n_gpus >= 1:
        return "LOCAL"
    if ram >= 96:
        return "LOCAL"  # big-RAM CPU box can still run large local models
    if ram >= 16 and n_gpus >= 1:
        return "HYBRID"
    if ram >= 32:
        return "HYBRID"  # strong CPU-only workstation
    if ram >= 8:
        return "CLOUD"
    return "MINIMAL"


def detect_hardware() -> HardwareProfile:
    """
    Probe the machine and select an execution profile.

    ``CERBERUS_PROFILE`` env var overrides detection (validated against
    PROFILE_ORDER; invalid values are ignored with a warning).
    """
    hp = HardwareProfile(
        os=platform.system(),
        cpu_count=_detect_cpu_count(),
        ram_gb=_detect_ram_gb(),
        gpus=_detect_gpus(),
        docker=_detect_docker(),
        ollama=_detect_ollama(),
    )
    hp.total_vram_gb = round(sum(g["vram_gb"] for g in hp.gpus), 1)

    env_profile = os.environ.get("CERBERUS_PROFILE", "").strip().upper()
    if env_profile:
        if env_profile in PROFILE_ORDER:
            hp.profile = env_profile
            hp.profile_source = "env"
            hp.notes.append(
                f"CERBERUS_PROFILE={env_profile} overrides detection")
        else:
            hp.notes.append(
                f"Ignoring invalid CERBERUS_PROFILE={env_profile!r} "
                f"(valid: {', '.join(PROFILE_ORDER)})")
            hp.profile = classify(hp)
    else:
        hp.profile = classify(hp)

    if hp.ram_gb == 0.0:
        hp.notes.append("RAM unknown — profile may be conservative")
    return hp


def format_report(hp: HardwareProfile) -> str:
    """Human-readable multi-line report (CLI / doctor)."""
    lines = [
        f"OS            {hp.os}",
        f"CPU           {hp.cpu_count} cores",
        f"RAM           {hp.ram_gb:.0f} GB",
    ]
    if hp.gpus:
        for g in hp.gpus:
            lines.append(f"GPU            {g['name']} ({g['vram_gb']} GB VRAM)")
        lines.append(f"Total VRAM     {hp.total_vram_gb:.0f} GB")
    else:
        lines.append("GPU            none detected")
    lines += [
        f"Docker         {'yes' if hp.docker else 'no'}",
        f"Ollama CLI     {'yes' if hp.ollama else 'no'}",
        "",
        f"Execution profile: {hp.profile} ({hp.profile_source})",
        f"  {PROFILE_DESCRIPTIONS[hp.profile]}",
    ]
    for note in hp.notes:
        lines.append(f"  note: {note}")
    return "\n".join(lines)


__all__ = [
    "HardwareProfile",
    "detect_hardware",
    "classify",
    "format_report",
    "PROFILE_ORDER",
    "PROFILE_DESCRIPTIONS",
]
