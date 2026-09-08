"""
Adapter for h4cker — Cybersecurity Knowledge Base & Reference.

Wraps the extensive h4cker security knowledge base into a SandboxedAdapter,
allowing agents to query vulnerability research, techniques, lab guides,
and security references.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from cyberai.orchestrator.adapters.base import (
    AdapterCapability,
    AdapterResult,
    SandboxedAdapter,
)

logger = logging.getLogger(__name__)

ORIGINAL_NAME = "h4cker"
ADAPTER_DIR = Path(__file__).resolve().parent


class Adapter(SandboxedAdapter):
    name = "h4cker"
    version = "1.0.0"
    description = "Cybersecurity knowledge base, CVEs, CWEs, and methodology reference"

    def __init__(self, config=None):
        super().__init__(config)
        self._doc_files: List[Path] = []
        self._index_built = False

    async def health_check(self) -> Dict[str, Any]:
        if not ADAPTER_DIR.exists():
            return {"status": "UNAVAILABLE", "message": "h4cker repository directory not found", "details": {}}
        readme = ADAPTER_DIR / "README.md"
        if not readme.exists():
            return {"status": "WARN", "message": "README.md missing in h4cker", "details": {}}
        return {
            "status": "AVAILABLE",
            "message": "h4cker knowledge base loaded and searchable",
            "details": {"path": str(ADAPTER_DIR)},
        }

    async def capabilities(self) -> List[AdapterCapability]:
        return [
            AdapterCapability("research", "Query CVEs, CWEs, and vulnerability research topics"),
            AdapterCapability("documentation", "Query security training and methodology references"),
        ]

    async def _do_execute(self, task: Dict[str, Any]) -> AdapterResult:
        action = task.get("action", "research")
        target = task.get("target", {})
        host = target.get("host") or target.get("id", "")
        params = task.get("parameters", {})
        query = params.get("query") or params.get("topic") or action or "security"

        # Search knowledge files in the repository
        results = await asyncio.to_thread(self._search_knowledge, query, limit=5)
        findings = [
            {
                "description": f"Knowledge reference: {r['title']}",
                "content": r["snippet"],
                "file": r["file"],
                "confidence": 0.85,
                "source": self.name,
            }
            for r in results
        ]

        evidence = {
            "type": "knowledge_retrieval",
            "tool": self.name,
            "target_host": host,
            "action": action,
            "query": query,
            "match_count": len(results),
            "matches": results,
        }

        return AdapterResult(
            success=True,
            output=f"Retrieved {len(results)} references for query '{query}'",
            evidence=evidence,
            metadata={
                "tool": self.name,
                "original": ORIGINAL_NAME,
                "action": action,
                "target_host": host,
                "findings": findings,
            },
        )

    def _search_knowledge(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        q_lower = query.lower()
        matches = []
        try:
            for md_file in ADAPTER_DIR.rglob("*.md"):
                if md_file.name.startswith("."):
                    continue
                try:
                    text = md_file.read_text(encoding="utf-8", errors="ignore")
                    if q_lower in text.lower():
                        rel = md_file.relative_to(ADAPTER_DIR)
                        # Extract first relevant sentence
                        lines = [line.strip() for line in text.splitlines() if q_lower in line.lower() and len(line.strip()) > 10]
                        snippet = lines[0] if lines else text[:200]
                        matches.append({
                            "title": md_file.stem.replace("-", " ").title(),
                            "file": str(rel),
                            "snippet": snippet[:300],
                        })
                        if len(matches) >= limit:
                            break
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Error scanning knowledge base: {e}")
        return matches

    async def collect_results(self) -> AdapterResult:
        return AdapterResult(True, metadata={"tool": self.name})

    async def shutdown(self) -> None:
        logger.info("Shutting down %s knowledge adapter", self.name)
