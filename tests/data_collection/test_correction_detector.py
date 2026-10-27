"""Tests for the correction detector module."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.jambandnerd.config.bands import SUPPORTED_BANDS
from src.jambandnerd.data_collection.correction_detector import (
    SETLIST_SCHEMAS,
    CorrectionFetchError,
    CorrectionResult,
    compute_record_checksum,
    detect_setlist_corrections,
    diff_setlists,
    fetch_stored_setlists,
    fetch_upstream_setlists,
    row_to_tuple,
    run_correction_sweep,
)

WINDOW = (date(2020, 1, 1), date(2100, 1, 1))
HOT_TEA = ("Song 1", "Song 2", "Hot Tea", "Song 4")


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


# ---------------------------------------------------------------------------
# Sweep behavior (fake Supabase client + fake collector)
# ---------------------------------------------------------------------------


class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, client, name):
        self.client, self.name = client, name
        self.filters = []
        self.window = (0, 999)

    def select(self, *_):
        return self

    def gte(self, col, val):
        self.filters.append(("gte", col, val))
        return self

    def lte(self, col, val):
        self.filters.append(("lte", col, val))
        return self

    def in_(self, col, vals):
        self.filters.append(("in", col, vals))
        return self

    def order(self, *_):
        return self

    def range(self, lo, hi):
        self.window = (lo, hi)
        return self

    def execute(self):
        if self.client.fail_on == self.name:
            raise RuntimeError("42703 column show_date does not exist")
        rows = self.client.tables.get(self.name, [])
        for op, col, val in self.filters:
            if op == "in":
                rows = [r for r in rows if str(r[col]) in val]
            elif op == "gte":
                rows = [r for r in rows if r[col] >= val]
            else:
                rows = [r for r in rows if r[col] <= val]
        lo, hi = self.window
        return _Resp(rows[lo : hi + 1])


class _Rpc:
    def __init__(self, client, name, params):
        self.client, self.name, self.params = client, name, params

    def execute(self):
        if self.client.rpc_error:
            raise RuntimeError(self.client.rpc_error)
        self.client.rpc_calls.append((self.name, self.params))
        return _Resp(None)


class FakeClient:
    def __init__(self, tables, fail_on=None, rpc_error=None):
        self.tables = tables
        self.fail_on = fail_on
        self.rpc_error = rpc_error
        self.rpc_calls = []

    def table(self, name):
        return _Query(self, name)

    def rpc(self, name, params):
        return _Rpc(self, name, params)


class FakeCollector:
    def __init__(self, setlists, shows=None):
        self.setlists = setlists
        self.shows = shows or []
        self.setlist_args = None

    def collect_shows(self, start_date=None, end_date=None):
        return self.shows

    def collect_setlists(self, *args, **kwargs):
        self.setlist_args = (args, kwargs)
        return self.setlists


def _goose_row(show_id, set_number, pos, song, pk=None):
    return {
        "id": pk or pos,
        "show_id": show_id,
        "set_number": set_number,
        "song_position": pos,
        "song_name": song,
    }


def _goose_stored(show_id="1"):
    return [_goose_row(show_id, 1, i, f"Song {i}") for i in (1, 2, 3, 4)]


def _goose_upstream_raw(show_id="1", songs=("Song 1", "Song 2", "Song 3", "Song 4")):
    return [
        {
            "show_id": show_id,
            "setnumber": 1,
            "position": i,
            "songname": name,
            "artist": "Goose",
        }
        for i, name in enumerate(songs, start=1)
    ]


def _goose_client(stored=None):
    return FakeClient(
        {
            "goose_shows_raw": [
                {"show_id": "1", "show_date": date.today().isoformat()}
            ],
            "goose_setlists_raw": stored if stored is not None else _goose_stored(),
        }
    )


def _sweep(client, upstream, dry_run=False):
    results = run_correction_sweep(
        "goose", dry_run=dry_run, client=client, collector=FakeCollector(upstream)
    )
    return results["goose_setlists_raw"]


class TestSweepEndToEnd:
    def test_unchanged_setlist_produces_no_corrections(self):
        client = _goose_client()
        result = _sweep(client, _goose_upstream_raw())
        assert result.records_checked == 1
        assert result.corrections_found == 0
        assert result.errors == []
        assert client.rpc_calls == []

    def test_changed_song_is_reported_and_applied_via_rpc(self):
        client = _goose_client()
        result = _sweep(client, _goose_upstream_raw(songs=HOT_TEA))
        assert result.corrections_found == 1
        assert result.corrections_applied == 1
        change = result.details[0]["changed"][0]
        assert change["from"]["song_name"] == "Song 3"
        assert change["to"]["song_name"] == "Hot Tea"
        ((name, params),) = client.rpc_calls
        assert name == "replace_show_setlist"
        assert params["p_band"] == "goose" and params["p_show_id"] == "1"
        assert params["p_rows"][2]["song_name"] == "Hot Tea"

    def test_dry_run_reports_but_never_writes(self):
        client = _goose_client()
        result = _sweep(client, _goose_upstream_raw(songs=HOT_TEA), dry_run=True)
        assert result.corrections_found == 1
        assert result.corrections_applied == 0
        assert client.rpc_calls == []

    def test_upstream_below_minimum_rows_is_skipped_not_applied(self):
        client = _goose_client()
        result = _sweep(client, _goose_upstream_raw(songs=("Only", "Two")))
        assert result.corrections_found == 0
        assert result.skipped[0]["reason"] == "upstream_below_minimum"
        assert client.rpc_calls == []

    def test_show_missing_upstream_is_skipped(self):
        client = _goose_client()
        result = _sweep(client, [])
        assert result.skipped[0]["reason"] == "not_in_upstream"
        assert client.rpc_calls == []

    def test_shrink_guard_refusal_is_recorded_as_error(self):
        client = _goose_client()
        client.rpc_error = "replacement shrinks setlist by more than 50%"
        result = _sweep(client, _goose_upstream_raw(songs=HOT_TEA))
        assert result.corrections_applied == 0
        assert len(result.errors) == 1 and "shrinks" in result.errors[0]
        assert result.details[0]["action"] == "error"

    @pytest.mark.parametrize("failing", ["goose_shows_raw", "goose_setlists_raw"])
    def test_query_errors_are_reported_not_swallowed(self, failing):
        client = _goose_client()
        client.fail_on = failing
        result = _sweep(client, _goose_upstream_raw())
        assert result.errors and "42703" in result.errors[0]
        assert client.rpc_calls == []

    def test_fetch_stored_setlists_raises_on_query_error(self):
        client = _goose_client()
        client.fail_on = "goose_shows_raw"
        with pytest.raises(CorrectionFetchError):
            fetch_stored_setlists("goose", *WINDOW, client=client)

    def test_stored_fetch_paginates_past_one_page(self):
        rows = [_goose_row("1", 1, i, f"S{i}", pk=i) for i in range(1, 1501)]
        grouped = fetch_stored_setlists(
            "goose", *WINDOW, client=_goose_client(stored=rows)
        )
        assert len(grouped["1"]) == 1500

    def test_collector_failure_is_reported_as_error(self):
        class Boom(FakeCollector):
            def collect_setlists(self, *args, **kwargs):
                raise RuntimeError("upstream down")

        results = run_correction_sweep(
            "goose", dry_run=False, client=_goose_client(), collector=Boom([])
        )
        assert "upstream down" in results["goose_setlists_raw"].errors[0]


class TestMigration:
    def test_enforces_whitelist_shrink_guard_and_service_role_only(self):
        sql = Path(
            "supabase/migrations/20261027000000_add_replace_show_setlist_function.sql"
        ).read_text()
        assert "v_new_count * 2 < v_old_count" in sql
        assert "unsupported band" in sql
        assert "from anon" in sql and "from authenticated" in sql
        assert "to service_role" in sql and "to anon" not in sql


class TestDiff:
    def test_added_removed_changed(self):
        stored = [_goose_row("1", 1, i, f"S{i}") for i in (1, 2, 3)]
        upstream = [
            _goose_row("1", 1, 1, "S1"),
            _goose_row("1", 1, 2, "Changed"),
            _goose_row("1", 1, 4, "New"),
        ]
        diff = diff_setlists("goose", stored, upstream)
        assert [c["to"]["song_name"] for c in diff["changed"]] == ["Changed"]
        assert [r["song_name"] for r in diff["removed"]] == ["S3"]
        assert [a["song_name"] for a in diff["added"]] == ["New"]

    def test_row_order_does_not_matter(self):
        stored = _goose_stored()
        diff = diff_setlists("goose", stored, list(reversed(stored)))
        assert not any(diff.values())

    def test_metadata_columns_are_ignored(self):
        stored = _goose_stored()
        upstream = [dict(r, created_at="x", source_hash="y", id=None) for r in stored]
        assert not any(diff_setlists("goose", stored, upstream).values())


class TestBandColumnMapping:
    @pytest.mark.parametrize(
        "band,row,expected",
        [
            (
                "goose",
                {"set_number": 1, "song_position": 2, "song_name": " A "},
                ("1", 2, "A", False),
            ),
            (
                "eggy",
                {"set_number": 99, "song_position": 1, "song_name": "B"},
                ("99", 1, "B", False),
            ),
            (
                "phish",
                {"set_number": "1", "position": 3, "song_name": "C", "transition": ">"},
                ("1", 3, "C", True),
            ),
            (
                "phish",
                {
                    "set_number": None,
                    "position": 1,
                    "song_name": "D",
                    "transition": ",",
                },
                (None, 1, "D", False),
            ),
            (
                "wsp",
                {
                    "set_number": 2,
                    "song_position": 4,
                    "song_name": "E",
                    "is_segue": True,
                },
                ("2", 4, "E", True),
            ),
            (
                "billy",
                {
                    "set_number": 1,
                    "song_position": 5,
                    "song_name": "F",
                    "is_segue": False,
                },
                ("1", 5, "F", False),
            ),
            (
                "um",
                {
                    "set_label": "E",
                    "show_position": 9,
                    "song_name": "G",
                    "is_segue": True,
                },
                ("E", 9, "G", True),
            ),
        ],
    )
    def test_row_maps_to_comparison_tuple(self, band, row, expected):
        assert row_to_tuple(band, row) == expected

    def test_every_supported_band_has_a_schema(self):
        assert set(SETLIST_SCHEMAS) == set(SUPPORTED_BANDS)

    def test_phish_segue_difference_is_a_correction(self):
        base = {"set_number": "1", "position": 1, "song_name": "A", "transition": ","}
        diff = diff_setlists("phish", [base], [dict(base, transition=">")])
        assert len(diff["changed"]) == 1


class TestUpstreamAdapters:
    def test_show_id_bands_pass_stored_ids(self):
        collector = FakeCollector(_goose_upstream_raw())
        out = fetch_upstream_setlists("goose", ["1"], *WINDOW, collector=collector)
        assert collector.setlist_args == ((), {"show_ids": ["1"]})
        assert len(out["1"]) == 4

    def test_show_dict_bands_collect_shows_first_and_filter_to_stored(self):
        shows = [
            {"show_id": "7", "source_url": "u7"},
            {"show_id": "8", "source_url": "u8"},
        ]
        rows = [
            {"show_id": "7", "song_name": "A", "set_number": 1, "song_position": i}
            for i in (1, 2, 3)
        ]
        collector = FakeCollector(rows, shows=shows)
        out = fetch_upstream_setlists(
            "billy", ["7"], *WINDOW, collector=collector, normalizer=pd.DataFrame
        )
        args, _ = collector.setlist_args
        assert [s["show_id"] for s in args[0]] == ["7"]
        assert len(out["7"]) == 3

    def test_na_values_become_none(self):
        out = fetch_upstream_setlists(
            "phish",
            ["5"],
            *WINDOW,
            collector=FakeCollector([{"x": 1}]),
            normalizer=lambda raw: pd.DataFrame(
                [{"show_id": 5, "set_number": pd.NA, "position": float("nan")}]
            ),
        )
        assert out["5"][0]["set_number"] is None
        assert out["5"][0]["position"] is None

    def test_detect_rejects_unknown_band(self):
        with pytest.raises(ValueError):
            detect_setlist_corrections("nope", {}, {})
