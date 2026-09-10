"""Tests for the Knowledge subsystem (cyberai.orchestrator.knowledge).

Covers KnowledgeBase:
  - loading documents (.md/.txt/.yaml) and structured (.json) sources
  - category indexing and summaries
  - content search across categories
  - corrupt-file resilience
"""

import json

import pytest

from cyberai.orchestrator.knowledge import KnowledgeBase


@pytest.fixture
def kb_dir(tmp_path):
    (tmp_path / "cve").mkdir()
    (tmp_path / "cwe").mkdir()
    (tmp_path / "techniques").mkdir()
    (tmp_path / "empty-cat").mkdir()  # dir with no loadable files
    return tmp_path


@pytest.fixture
def kb(kb_dir):
    (kb_dir / "cve" / "CVE-2024-0001.md").write_text(
        "CVE-2024-0001: SQL injection in example app", encoding="utf-8")
    (kb_dir / "cve" / "CVE-2024-0002.md").write_text(
        "CVE-2024-0002: XSS in admin panel", encoding="utf-8")
    (kb_dir / "cwe" / "CWE-89.txt").write_text(
        "CWE-89: Improper Neutralization of SQL commands", encoding="utf-8")
    (kb_dir / "techniques" / "sqli.json").write_text(
        json.dumps({"id": "T1190", "name": "SQL Injection",
                    "pattern": "' OR 1=1 --"}),
        encoding="utf-8")
    return KnowledgeBase(knowledge_dir=kb_dir)


class TestLoading:
    def test_categories_indexed(self, kb):
        cats = kb.get_categories()
        assert "cve" in cats
        assert "cwe" in cats
        assert "techniques" in cats

    def test_summary_counts(self, kb):
        summary = kb.get_summary()
        assert summary["cve"] == 2
        assert summary["cwe"] == 1
        assert summary["techniques"] == 1

    def test_documents_loaded_with_content(self, kb):
        items = kb.get_category_items("cve")
        sources = {i["source"].replace("\\", "/") for i in items}
        assert sources == {"cve/CVE-2024-0001.md", "cve/CVE-2024-0002.md"}
        doc = items[0]
        assert doc["type"] == "document"
        assert "SQL injection" in doc["content"]

    def test_structured_json_loaded(self, kb):
        items = kb.get_category_items("techniques")
        assert items[0]["type"] == "structured"
        assert items[0]["data"]["id"] == "T1190"

    def test_empty_category_not_indexed(self, kb):
        # Directories with no loadable files are skipped entirely.
        assert "empty-cat" not in kb.get_categories()

    def test_unsupported_extensions_skipped(self, kb, kb_dir):
        # 'kb' fixture created the loadable files; add a png on top.
        (kb_dir / "cve" / "image.png").write_bytes(b"\x89PNG")
        kb2 = KnowledgeBase(knowledge_dir=kb_dir)
        assert kb2.get_summary()["cve"] == 2  # png not counted

    def test_corrupt_json_skipped(self, kb, kb_dir):
        (kb_dir / "techniques" / "bad.json").write_text("{broken",
                                                        encoding="utf-8")
        kb2 = KnowledgeBase(knowledge_dir=kb_dir)
        assert kb2.get_summary()["techniques"] == 1  # only sqli.json

    def test_missing_directory_tolerated(self, kb_dir):
        # advisories/research/documentation dirs don't exist — no crash.
        kb2 = KnowledgeBase(knowledge_dir=kb_dir)
        assert "advisories" not in kb2.get_categories()


class TestSearch:
    def test_search_matches_content(self, kb):
        results = kb.search("SQL injection")
        # Both the CVE doc and the structured technique JSON mention it.
        cats = {r["category"] for r in results}
        assert cats == {"cve", "techniques"}
        cve_hits = [r for r in results if r["category"] == "cve"]
        assert cve_hits[0]["source"].replace("\\", "/") == "cve/CVE-2024-0001.md"

    def test_search_case_insensitive(self, kb):
        assert len(kb.search("sql injection")) == 2

    def test_search_matches_structured_json(self, kb):
        results = kb.search("T1190")
        assert len(results) == 1
        assert results[0]["category"] == "techniques"

    def test_search_restricted_to_categories(self, kb):
        results = kb.search("SQL", categories=["cwe"])
        assert len(results) == 1
        assert results[0]["source"].replace("\\", "/") == "cwe/CWE-89.txt"

    def test_search_no_results(self, kb):
        assert kb.search("nothing-matches-this") == []

    def test_search_result_shape(self, kb):
        results = kb.search("XSS")
        assert len(results) == 1
        r = results[0]
        assert set(r) == {"category", "source", "title", "content"}
        assert r["title"] == "CVE-2024-0002"  # file stem for documents
        assert len(r["content"]) <= 1000  # truncated snippet

    def test_search_unknown_category_ignored(self, kb):
        assert kb.search("SQL", categories=["no-such-cat"]) == []


class TestRealKnowledgeDir:
    def test_workspace_knowledge_base_loads(self):
        """The real knowledge/ dir loads without error (may be sparse)."""
        kb = KnowledgeBase()
        assert isinstance(kb.get_summary(), dict)
