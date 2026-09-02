"""
Knowledge Base Loader for the Cyber AI Orchestrator.

Loads and indexes security knowledge from:
- CVE database (knowledge/cve/)
- CWE reference (knowledge/cwe/)
- Security advisories (knowledge/advisories/)
- Techniques (knowledge/techniques/)
- Research papers (knowledge/research/)
- Documentation (knowledge/documentation/)
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from cyberai.config import WORKSPACE_ROOT
KNOWLEDGE_DIR = WORKSPACE_ROOT / "knowledge"


class KnowledgeBase:
    """
    Security knowledge base loader and indexer.

    Provides search capabilities across all knowledge sources.
    """

    def __init__(self, knowledge_dir: Optional[Path] = None):
        self.knowledge_dir = knowledge_dir or KNOWLEDGE_DIR
        self._index: Dict[str, List[Dict[str, Any]]] = {}
        self._load()

    def _load(self) -> None:
        """Load and index all knowledge sources."""
        for category in ["cve", "cwe", "advisories", "techniques", "research", "documentation"]:
            cat_dir = self.knowledge_dir / category
            if cat_dir.exists():
                self._index[category] = []
                for f in cat_dir.rglob("*"):
                    if f.is_file() and f.suffix in (".md", ".txt", ".json", ".yaml", ".yml"):
                        try:
                            if f.suffix == ".json":
                                data = json.loads(f.read_text())
                                self._index[category].append({
                                    "source": str(f.relative_to(self.knowledge_dir)),
                                    "data": data,
                                    "type": "structured",
                                })
                            else:
                                self._index[category].append({
                                    "source": str(f.relative_to(self.knowledge_dir)),
                                    "title": f.stem,
                                    "content": f.read_text()[:2000],
                                    "type": "document",
                                })
                        except Exception as e:
                            logger.warning(f"Failed to load {f}: {e}")

        total = sum(len(v) for v in self._index.values())
        logger.info(f"Loaded {total} knowledge items from {len(self._index)} categories")

    def search(self, query: str, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search the knowledge base.

        Args:
            query: Search query
            categories: Optional list of categories to search (default: all)

        Returns:
            List of matching knowledge items
        """
        if categories is None:
            categories = list(self._index.keys())

        results = []
        query_lower = query.lower()
        for cat in categories:
            for item in self._index.get(cat, []):
                content = ""
                if item.get("type") == "document":
                    content = item.get("content", "")
                elif item.get("type") == "structured":
                    content = json.dumps(item.get("data", {}))

                if query_lower in content.lower():
                    results.append({
                        "category": cat,
                        "source": item.get("source", ""),
                        "title": item.get("title", item.get("source", "")),
                        "content": content[:1000],
                    })

        return results

    def get_categories(self) -> List[str]:
        """Return all available knowledge categories."""
        return sorted(self._index.keys())

    def get_category_items(self, category: str) -> List[Dict[str, Any]]:
        """Get all items in a category."""
        return self._index.get(category, [])

    def get_summary(self) -> Dict[str, int]:
        """Return a summary of knowledge base contents."""
        return {cat: len(items) for cat, items in self._index.items()}
