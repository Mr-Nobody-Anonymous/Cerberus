"""Adapters package for the Cyber AI Orchestrator.

Provides dynamic import resolution for vendored adapter directories containing
hyphens (e.g. adapters/guardian-cli -> adapters.guardian_cli,
adapters/kali-pentest -> adapters.kali_pentest).
"""

import importlib.util
import sys
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent


class _HyphenAdapterFinder:
    """MetaPathFinder that resolves adapters with hyphens in their directory names."""

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if not fullname.startswith("adapters."):
            return None
        subname = fullname.split(".", 1)[1]
        if "." in subname:
            return None
        hyphen_name = subname.replace("_", "-")
        target_dir = _PKG_DIR / hyphen_name
        init_file = target_dir / "__init__.py"
        if target_dir.is_dir() and init_file.exists():
            return importlib.util.spec_from_file_location(
                fullname,
                str(init_file),
                submodule_search_locations=[str(target_dir)],
            )
        return None


if not any(getattr(finder, "__name__", "") == "_HyphenAdapterFinder" for finder in sys.meta_path):
    sys.meta_path.insert(0, _HyphenAdapterFinder)
