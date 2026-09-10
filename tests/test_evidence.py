"""Tests for the Evidence subsystem (cyberai.orchestrator.evidence).

Covers:
  - store_evidence: ID format, hashing determinism, file persistence
  - get_evidence / list_evidence round-trips
  - update_verification_status
  - unknown evidence types (warned but stored)
"""

import json

import pytest

from cyberai.orchestrator.evidence import EvidenceManager


@pytest.fixture
def manager(tmp_path):
    return EvidenceManager(evidence_dir=tmp_path / "evidence")


class TestStoreEvidence:
    def test_returns_hash_based_id(self, manager):
        ev_id = manager.store_evidence("sess-1234", "scan_output", "open ports: 22, 80")
        # ID = first 8 chars of session + type + 16-hex content hash.
        assert ev_id.startswith("sess-123")
        assert "scan_output" in ev_id
        # The trailing segment after the type is the 16-hex content hash.
        trailing = ev_id.split("scan_output_")[1]
        assert len(trailing) == 16
        int(trailing, 16)  # must be valid hex

    def test_persists_record_to_disk(self, manager):
        ev_id = manager.store_evidence("sess-1", "tool_response", {"ok": True},
                                       source="nmap", confidence=0.8)
        path = manager.evidence_dir / f"{ev_id}.json"
        assert path.exists()
        record = json.loads(path.read_text())
        assert record["session_id"] == "sess-1"
        assert record["type"] == "tool_response"
        assert record["source"] == "nmap"
        assert record["confidence"] == 0.8
        assert record["verification_status"] == "UNVERIFIED"
        assert record["content"] == {"ok": True}
        assert record["timestamp"]  # ISO timestamp present

    def test_same_content_same_id(self, manager):
        a = manager.store_evidence("sess-1", "manual_note", "note text")
        b = manager.store_evidence("sess-1", "manual_note", "note text")
        assert a == b  # deterministic content hash

    def test_different_content_different_id(self, manager):
        a = manager.store_evidence("sess-1", "manual_note", "note A")
        b = manager.store_evidence("sess-1", "manual_note", "note B")
        assert a != b

    def test_creates_gitkeep_and_dir(self, tmp_path):
        ev_dir = tmp_path / "nested" / "evidence"
        EvidenceManager(evidence_dir=ev_dir)
        assert ev_dir.is_dir()
        assert (ev_dir / ".gitkeep").exists()

    def test_custom_timestamp_respected(self, manager):
        ev_id = manager.store_evidence("s", "manual_note", "x",
                                       timestamp="2024-01-01T00:00:00+00:00")
        assert manager.get_evidence(ev_id)["timestamp"] == "2024-01-01T00:00:00+00:00"

    def test_unknown_type_stored_with_warning(self, manager, caplog):
        ev_id = manager.store_evidence("s", "bogus_type", "data")
        # Unknown types are warned about but still stored.
        assert manager.get_evidence(ev_id)["type"] == "bogus_type"
        assert any("Unknown evidence type" in r.message for r in caplog.records)


class TestGetAndList:
    def test_get_evidence_round_trip(self, manager):
        ev_id = manager.store_evidence("sess-1", "screenshot", "base64data",
                                       source="browser")
        record = manager.get_evidence(ev_id)
        assert record["id"] == ev_id
        assert record["content"] == "base64data"

    def test_get_missing_returns_none(self, manager):
        assert manager.get_evidence("does-not-exist") is None

    def test_list_evidence_filters_by_session(self, manager):
        manager.store_evidence("sess-A", "scan_output", "A1")
        manager.store_evidence("sess-A", "scan_output", "A2")
        manager.store_evidence("sess-B", "scan_output", "B1")
        items = manager.list_evidence("sess-A")
        assert len(items) == 2
        assert all(i["session_id"] == "sess-A" for i in items)

    def test_list_evidence_sorted_by_timestamp(self, manager):
        manager.store_evidence("s", "manual_note", "first",
                               timestamp="2024-01-01T00:00:00+00:00")
        manager.store_evidence("s", "manual_note", "second",
                               timestamp="2024-01-02T00:00:00+00:00")
        items = manager.list_evidence("s")
        assert items[0]["content"] == "first"
        assert items[1]["content"] == "second"

    def test_list_evidence_skips_corrupt_files(self, manager):
        manager.store_evidence("s", "manual_note", "good")
        (manager.evidence_dir / "corrupt.json").write_text("{broken",
                                                           encoding="utf-8")
        items = manager.list_evidence("s")
        assert len(items) == 1  # corrupt file skipped, no crash

    def test_list_evidence_empty_session(self, manager):
        assert manager.list_evidence("no-such-session") == []


class TestUpdateVerification:
    def test_update_status(self, manager):
        ev_id = manager.store_evidence("s", "scan_output", "data")
        assert manager.update_verification_status(ev_id, "VERIFIED", 0.95)
        record = manager.get_evidence(ev_id)
        assert record["verification_status"] == "VERIFIED"
        assert record["confidence"] == 0.95

    def test_update_status_without_confidence(self, manager):
        ev_id = manager.store_evidence("s", "scan_output", "data", confidence=0.5)
        manager.update_verification_status(ev_id, "LIKELY")
        record = manager.get_evidence(ev_id)
        assert record["verification_status"] == "LIKELY"
        assert record["confidence"] == 0.5  # unchanged

    def test_update_missing_returns_false(self, manager):
        assert manager.update_verification_status("ghost", "VERIFIED") is False

    def test_all_documented_types_accepted(self, manager):
        for ev_type in EvidenceManager.EVIDENCE_TYPES:
            ev_id = manager.store_evidence("s", ev_type, "x")
            assert manager.get_evidence(ev_id) is not None
