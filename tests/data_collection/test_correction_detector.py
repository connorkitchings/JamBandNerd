"""Tests for the correction detector module."""

from __future__ import annotations

from src.jambandnerd.data_collection.correction_detector import (
    CorrectionResult,
    compute_record_checksum,
)


class TestComputeRecordChecksum:
    """Tests for compute_record_checksum function."""

    def test_deterministic_checksum(self):
        """Checksum should be deterministic for the same data."""
        record = {"song_name": "Test Song", "set_number": 1, "song_position": 2}
        checksum1 = compute_record_checksum(record)
        checksum2 = compute_record_checksum(record)
        assert checksum1 == checksum2

    def test_different_data_different_checksum(self):
        """Different data should produce different checksums."""
        record1 = {"song_name": "Song A", "set_number": 1}
        record2 = {"song_name": "Song B", "set_number": 1}
        checksum1 = compute_record_checksum(record1)
        checksum2 = compute_record_checksum(record2)
        assert checksum1 != checksum2

    def test_excludes_metadata_fields(self):
        """Metadata fields should be excluded from checksum."""
        record_with_metadata = {
            "song_name": "Test Song",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
            "id": 123,
        }
        record_without_metadata = {
            "song_name": "Test Song",
        }
        checksum1 = compute_record_checksum(record_with_metadata)
        checksum2 = compute_record_checksum(record_without_metadata)
        assert checksum1 == checksum2

    def test_handles_none_values(self):
        """Should handle None values gracefully."""
        record = {"song_name": "Test", "notes": None, "position": 1}
        checksum = compute_record_checksum(record)
        assert checksum is not None
        assert len(checksum) == 64  # SHA-256 hex string length


class TestCorrectionResult:
    """Tests for CorrectionResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = CorrectionResult(
            band="goose",
            table_name="goose_setlists_raw",
            records_checked=100,
            corrections_found=5,
            corrections_applied=3,
            errors=["error1"],
            details=[{"show_id": "123", "action": "applied"}],
        )
        d = result.to_dict()
        assert d["band"] == "goose"
        assert d["table_name"] == "goose_setlists_raw"
        assert d["records_checked"] == 100
        assert d["corrections_found"] == 5
        assert d["corrections_applied"] == 3
        assert d["errors"] == ["error1"]
        assert len(d["details"]) == 1

    def test_empty_result(self):
        """Test empty result initialization."""
        result = CorrectionResult(
            band="phish",
            table_name="phish_setlists_raw",
            records_checked=0,
            corrections_found=0,
            corrections_applied=0,
        )
        assert result.errors == []
        assert result.details == []
