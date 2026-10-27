"""Tests for the correction detector module."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.jambandnerd.config.bands import SUPPORTED_BANDS
from src.jambandnerd.data_collection.correction_detector import (
    KEY_KIND_COLUMNS,
    LIMITED_UPSTREAM_HISTORY,
    NATURAL_KEY_KINDS,
    SETLIST_SCHEMAS,
    SHOWS_TABLE_COLUMNS,
    CorrectionFetchError,
    CorrectionResult,
    _replacement_payload,
    canonical_song,
    compute_record_checksum,
    detect_setlist_corrections,
    diff_setlists,
    fetch_stored_setlists,
    fetch_upstream_setlists,
    match_upstream_shows,
    row_to_tuple,
    run_correction_sweep,
    show_match_columns,
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
                ("1", 2, "a", False),
            ),
            (
                "eggy",
                {"set_number": 99, "song_position": 1, "song_name": "B"},
                ("E", 1, "b", False),
            ),
            (
                "phish",
                {"set_number": "1", "position": 3, "song_name": "C", "transition": ">"},
                ("1", 3, "c", True),
            ),
            (
                "phish",
                {
                    "set_number": None,
                    "position": 1,
                    "song_name": "D",
                    "transition": ",",
                },
                (None, 1, "d", False),
            ),
            (
                "wsp",
                {
                    "set_number": 2,
                    "song_position": 4,
                    "song_name": "E",
                    "is_segue": True,
                },
                ("2", 4, "e", True),
            ),
            (
                "billy",
                {
                    "set_number": 1,
                    "song_position": 5,
                    "song_name": "F",
                    "is_segue": False,
                },
                ("1", 5, "f", False),
            ),
            (
                "um",
                {
                    "set_label": "E",
                    "show_position": 9,
                    "song_name": "G",
                    "is_segue": True,
                },
                ("E", 9, "g", True),
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


# ---------------------------------------------------------------------------
# Representation mismatches (stored "1.0" vs upstream 1)
# ---------------------------------------------------------------------------


class TestCanonicalization:
    def test_phish_float_stringified_set_matches_int_set(self):
        stored = [
            {
                "set_number": "1.0",
                "position": "1.0",
                "song_name": "Sand ",
                "transition": ">",
            },
            {
                "set_number": "2.0",
                "position": 2.0,
                "song_name": "Free",
                "transition": "",
            },
        ]
        upstream = [
            {"set_number": 1, "position": 1, "song_name": "Sand", "transition": "->"},
            {"set_number": 2, "position": 2, "song_name": "Free", "transition": None},
        ]
        diff = diff_setlists("phish", stored, upstream)
        assert diff == {"added": [], "removed": [], "changed": []}

    def test_phish_sweep_with_float_sets_reports_zero_corrections(self):
        stored = [
            {
                "api_unique_id": f"u{i}",
                "show_id": 9,
                "set_number": "1.0",
                "position": i,
                "song_name": f"S{i}",
                "transition": ",",
            }
            for i in (1, 2, 3, 4)
        ]
        client = FakeClient(
            {
                "phish_shows_raw": [
                    {"show_id": 9, "show_date": date.today().isoformat()}
                ],
                "phish_setlists_raw": stored,
            }
        )
        raw = [
            {
                "uniqueid": f"u{i}",
                "showid": 9,
                "showdate": "2026-01-01",
                "set": "1",
                "position": i,
                "song": f"S{i}",
                "trans_mark": ",",
            }
            for i in (1, 2, 3, 4)
        ]
        result = run_correction_sweep(
            "phish", client=client, collector=FakeCollector(raw)
        )["phish_setlists_raw"]
        assert result.corrections_found == 0
        assert result.errors == []

    def test_real_song_change_still_detected_despite_float_sets(self):
        stored = [
            {"set_number": "1.0", "position": 1, "song_name": "A", "transition": ","},
            {"set_number": "1.0", "position": 2, "song_name": "B", "transition": ","},
        ]
        upstream = [
            {"set_number": 1, "position": 1, "song_name": "A", "transition": ","},
            {"set_number": 1, "position": 2, "song_name": "C", "transition": ","},
        ]
        diff = diff_setlists("phish", stored, upstream)
        assert [c["to"]["song_name"] for c in diff["changed"]] == ["C"]
        assert diff["added"] == [] and diff["removed"] == []

    def test_string_booleans_are_parsed(self):
        row = {"set_number": 1, "song_position": 1, "song_name": "A"}
        stored = [dict(row, is_segue="false")]
        upstream = [dict(row, is_segue=False)]
        assert diff_setlists("billy", stored, upstream)["changed"] == []


# ---------------------------------------------------------------------------
# Natural-key matching for bands that assign their own show ids
# ---------------------------------------------------------------------------


def _stored_show(show_id, show_date, venue, url=None, uuid=None):
    return {
        "show_id": show_id,
        "show_date": show_date,
        "venue_name": venue,
        "source_url": url,
        "source_uuid": uuid,
    }


class TestNaturalKeyMatching:
    def test_billy_matches_on_date_and_normalized_venue(self):
        stored = [_stored_show(501, "2026-05-01", "The Fillmore!")]
        upstream = [
            {
                "show_date": "2026-05-01",
                "venue_name": "fillmore",
                "source_uuid": "slug-uuid",
                "source_url": "u",
            }
        ]
        (matched,) = match_upstream_shows("billy", upstream, stored)
        assert matched["show_id"] == 501

    def test_um_matches_on_source_url(self):
        stored = [_stored_show(7, "2026-05-01", "x", url="https://um/a")]
        upstream = [{"show_date": "2026-05-01", "source_url": "https://um/a"}]
        (matched,) = match_upstream_shows("um", upstream, stored)
        assert matched["show_id"] == 7

    def test_wsp_falls_back_to_date_venue_when_url_differs(self):
        stored = [_stored_show(3, "2026-05-01", "Fox Theatre", url="old")]
        upstream = [
            {
                "show_date": "2026-05-01",
                "venue_name": "fox theatre",
                "source_url": "new",
            }
        ]
        (matched,) = match_upstream_shows("wsp", upstream, stored)
        assert matched["show_id"] == 3

    def test_unmatched_and_ambiguous_shows_are_dropped(self):
        stored = [
            _stored_show(1, "2026-05-01", "Hall"),
            _stored_show(2, "2026-05-01", "Hall"),
        ]
        upstream = [
            {"show_date": "2026-05-01", "venue_name": "Hall"},
            {"show_date": "2026-06-01", "venue_name": "Elsewhere"},
        ]
        assert match_upstream_shows("billy", upstream, stored) == []

    @pytest.mark.parametrize("band", ["billy", "um", "wsp"])
    def test_sweep_compares_using_stored_id_not_upstream_id(self, band):
        today = date.today().isoformat()
        stored_show = _stored_show(
            501, today, "Venue", url="https://x/show", uuid="u-1"
        )
        stored_rows = [
            {
                "id": i,
                "show_id": 501,
                "set_number": 1,
                "set_label": "1",
                "song_position": i,
                "show_position": i,
                "song_name": f"S{i}",
                "is_segue": False,
            }
            for i in (1, 2, 3)
        ]
        client = FakeClient(
            {
                f"{band}_shows_raw": [stored_show],
                f"{band}_setlists_raw": stored_rows,
            }
        )
        upstream_show = {
            "show_id": 999,  # differs from the stored id
            "show_date": today,
            "venue_name": "Venue",
            "source_url": "https://x/show",
            "source_uuid": "u-1",
        }

        class Collector(FakeCollector):
            def collect_setlists(self, shows, *a, **kw):
                self.setlist_args = shows
                return [
                    {
                        "show_id": s["show_id"],
                        "set_number": 1,
                        "set_label": "1",
                        "song_position": i,
                        "show_position": i,
                        "song_name": name,
                        "is_segue": False,
                    }
                    for s in shows
                    for i, name in enumerate(("S1", "S2", "Changed"), start=1)
                ]

        collector = Collector([], shows=[upstream_show])
        result = run_correction_sweep(
            band,
            dry_run=True,
            client=client,
            collector=collector,
            normalizer=pd.DataFrame,
        )[f"{band}_setlists_raw"]

        assert [s["show_id"] for s in collector.setlist_args] == [501]
        assert result.skipped == []
        assert result.corrections_found == 1
        assert result.details[0]["show_id"] == "501"
        assert result.summary()["compared"] == 1


class TestBlindSweepGuard:
    def test_high_not_in_upstream_rate_is_an_error_and_summarized(self):
        today = date.today().isoformat()
        shows = [_stored_show(i, today, f"V{i}", url=f"u{i}") for i in (1, 2, 3)]
        rows = [
            {
                "id": i,
                "show_id": i,
                "set_label": "1",
                "show_position": p,
                "song_name": "S",
                "is_segue": False,
            }
            for i in (1, 2, 3)
            for p in (1, 2, 3)
        ]
        client = FakeClient({"um_shows_raw": shows, "um_setlists_raw": rows})
        # Upstream knows none of the stored urls.
        collector = FakeCollector(
            [], shows=[{"show_date": today, "source_url": "other"}]
        )
        result = run_correction_sweep(
            "um", client=client, collector=collector, normalizer=pd.DataFrame
        )["um_setlists_raw"]
        summary = result.to_dict()["summary"]
        assert summary["compared"] == 0
        assert summary["skipped_by_reason"] == {"not_in_upstream": 3}
        assert any("Blind sweep" in e for e in result.errors)

    def test_low_not_in_upstream_rate_is_not_an_error(self):
        result = _sweep(_goose_client(), _goose_upstream_raw())
        assert result.summary()["not_in_upstream_ratio"] == 0.0
        assert result.errors == []


class TestSongNameCanonicalization:
    @pytest.mark.parametrize(
        "stored,upstream",
        [
            ("I'm One Of Those", "I\u2019m One Of Those"),
            ("Dust in a Baggie", "Dust In A Baggie"),
            ("L.a. Woman", "L.A. Woman"),
            ("Lonesome L.A. Cowboy", "Lonesome LA Cowboy"),
            ("Don't Be Calling Me (At 4am)", "Don\u2019t Be Calling Me (at 4 AM)"),
            ("Ole Slew-Foot", "Ole Slew Foot"),
            (
                "Smoke! Smoke! Smoke! (That Cigarette)",
                "Smoke, Smoke, Smoke That Cigarette",
            ),
        ],
    )
    def test_cosmetic_name_differences_are_not_diffs(self, stored, upstream):
        row = {"set_number": 1, "song_position": 1}
        diff = diff_setlists(
            "billy",
            [dict(row, song_name=stored, is_segue=False)],
            [dict(row, song_name=upstream, is_segue=False)],
        )
        assert diff == {"added": [], "removed": [], "changed": []}

    def test_stored_trailing_segue_marker_folds_into_is_segue(self):
        row = {"set_number": 1, "song_position": 1}
        stored = [dict(row, song_name="Freeborn Man >", is_segue=False)]
        upstream = [dict(row, song_name="Freeborn Man", is_segue=True)]
        assert diff_setlists("billy", stored, upstream)["changed"] == []
        assert canonical_song("Freeborn Man ->") == ("freebornman", True)
        assert canonical_song("Freeborn Man") == ("freebornman", False)

    def test_segue_flag_difference_without_marker_is_still_a_diff(self):
        row = {"set_number": 1, "song_position": 1, "song_name": "Psycho"}
        diff = diff_setlists(
            "billy", [dict(row, is_segue=False)], [dict(row, is_segue=True)]
        )
        assert len(diff["changed"]) == 1

    def test_real_song_changes_survive_and_report_raw_names(self):
        row = {"set_number": 1, "is_segue": False}
        stored = [dict(row, song_position=1, song_name="Ruby Are You Mad")]
        upstream = [dict(row, song_position=1, song_name="Ruby")]
        (change,) = diff_setlists("billy", stored, upstream)["changed"]
        assert change["from"]["song_name"] == "Ruby Are You Mad"
        assert change["to"]["song_name"] == "Ruby"

    def test_genuinely_added_songs_are_still_reported(self):
        row = {"set_number": 1, "is_segue": False}
        stored = [dict(row, song_position=1, song_name="A")]
        upstream = [
            dict(row, song_position=1, song_name="A"),
            dict(row, song_position=2, song_name="Pigeon Roost"),
        ]
        diff = diff_setlists("billy", stored, upstream)
        assert [a["song_name"] for a in diff["added"]] == ["Pigeon Roost"]

    def test_replacement_payload_keeps_upstream_raw_names(self):
        client = _goose_client()
        raw = _goose_upstream_raw(songs=("Song 1", "Song 2", "Hot Tea", "Song 4"))
        _sweep(client, raw)
        names = [r["song_name"] for r in client.rpc_calls[0][1]["p_rows"]]
        assert names == ["Song 1", "Song 2", "Hot Tea", "Song 4"]


class TestShowsTableColumns:
    @pytest.mark.parametrize("band", sorted(NATURAL_KEY_KINDS))
    def test_selected_columns_exist_on_the_bands_shows_table(self, band):
        assert set(show_match_columns(band)) <= SHOWS_TABLE_COLUMNS[band]

    @pytest.mark.parametrize("band", sorted(NATURAL_KEY_KINDS))
    def test_every_key_kind_has_declared_columns_on_the_table(self, band):
        for kind in NATURAL_KEY_KINDS[band]:
            assert set(KEY_KIND_COLUMNS[kind]) <= SHOWS_TABLE_COLUMNS[band]

    def test_only_billy_selects_source_uuid(self):
        assert "source_uuid" in show_match_columns("billy")
        assert "source_uuid" not in show_match_columns("um")
        assert "source_uuid" not in show_match_columns("wsp")

    def test_stored_shows_select_is_limited_to_band_columns(self):
        selected = []

        class Q(_Query):
            def select(self, cols, *_):
                selected.append(cols)
                return self

        class C(FakeClient):
            def table(self, name):
                return Q(self, name)

        today = date.today().isoformat()
        client = C(
            {
                "um_shows_raw": [_stored_show(1, today, "V", url="u")],
                "um_setlists_raw": [],
            }
        )
        run_correction_sweep(
            "um", client=client, collector=FakeCollector([]), normalizer=pd.DataFrame
        )
        assert all("source_uuid" not in c for c in selected)


class TestLimitedUpstreamHistory:
    def _run(self, band, matched):
        today = date.today().isoformat()
        shows = [_stored_show(i, today, f"V{i}", url=f"u{i}") for i in (1, 2, 3, 4)]
        rows = [
            {
                "id": i * 10 + p,
                "show_id": i,
                "set_number": 1,
                "set_label": "1",
                "song_position": p,
                "show_position": p,
                "song_name": f"S{p}",
                "is_segue": False,
            }
            for i in (1, 2, 3, 4)
            for p in (1, 2, 3)
        ]
        client = FakeClient({f"{band}_shows_raw": shows, f"{band}_setlists_raw": rows})
        up = [
            {
                "show_id": i,
                "show_date": today,
                "venue_name": f"V{i}",
                "source_url": f"u{i}",
                "source_uuid": f"u{i}",
            }
            for i in matched
        ]

        class Collector(FakeCollector):
            def collect_setlists(self, shows, *a, **kw):
                return [
                    {
                        "show_id": s["show_id"],
                        "set_number": 1,
                        "set_label": "1",
                        "song_position": p,
                        "show_position": p,
                        "song_name": f"S{p}",
                        "is_segue": False,
                    }
                    for s in shows
                    for p in (1, 2, 3)
                ]

        return run_correction_sweep(
            band,
            client=client,
            collector=Collector([], shows=up),
            normalizer=pd.DataFrame,
        )[f"{band}_setlists_raw"]

    def test_billy_is_declared_limited_and_others_are_not(self):
        assert LIMITED_UPSTREAM_HISTORY == {"billy"}

    def test_limited_band_high_skip_rate_warns_but_does_not_fail(self):
        result = self._run("billy", matched=[1])
        assert result.errors == []
        assert any("Limited upstream history" in w for w in result.warnings)
        summary = result.summary()
        assert summary["compared"] == 1 and summary["skipped"] == 3

    def test_limited_band_fails_when_nothing_compared(self):
        result = self._run("billy", matched=[])
        assert any("nothing compared" in e for e in result.errors)

    def test_unlimited_band_high_skip_rate_still_fails(self):
        result = self._run("um", matched=[1])
        assert any("Blind sweep" in e for e in result.errors)


class TestEncoreAndChangedFields:
    def test_wsp_encore_e_vs_99_is_not_a_diff(self):
        stored = [
            {"set_number": "E", "song_position": 1, "song_name": "Big Wooly Mammoth"},
            {"set_number": "E", "song_position": 2, "song_name": "Porch Song"},
        ]
        upstream = [dict(r, set_number=99) for r in stored]
        diff = diff_setlists("wsp", stored, upstream)
        assert diff == {"added": [], "removed": [], "changed": []}

    @pytest.mark.parametrize("label", ["E", "E2", "Encore", "Encore 1", "e", 99, "99"])
    def test_encore_spellings_share_one_label(self, label):
        row = {"set_number": label, "song_position": 1, "song_name": "x"}
        assert row_to_tuple("wsp", row)[0] == "E"

    def test_changed_encore_song_is_still_a_diff(self):
        stored = [{"set_number": "E", "song_position": 1, "song_name": "Porch Song"}]
        upstream = [{"set_number": 99, "song_position": 1, "song_name": "Down"}]
        (change,) = diff_setlists("wsp", stored, upstream)["changed"]
        assert change["fields"] == ["song_name"]

    def test_changed_rows_name_the_differing_field(self):
        base = {"set_number": 1, "song_position": 1, "song_name": "Henry Parsons Died"}
        diff = diff_setlists(
            "wsp", [dict(base, is_segue=True)], [dict(base, is_segue=False)]
        )
        (change,) = diff["changed"]
        assert change["fields"] == ["is_segue"]
        assert change["from"]["is_segue"] is True
        assert change["to"]["is_segue"] is False
        assert set(change["from"]) == {
            "set_number",
            "position",
            "song_name",
            "is_segue",
        }

    def test_um_set_relabel_with_same_songs_is_still_a_diff(self):
        stored = [{"set_label": "1", "show_position": 9, "song_name": "Slacker"}]
        upstream = [{"set_label": "2", "show_position": 9, "song_name": "Slacker"}]
        diff = diff_setlists("um", stored, upstream)
        assert len(diff["added"]) == 1 and len(diff["removed"]) == 1


class TestReplacementPayloadColumns:
    """The RPC inserts every key of the first row, so server-managed keys must not be sent."""

    @staticmethod
    def _band_row(band, position, song):
        schema = SETLIST_SCHEMAS[band]
        return {
            schema.set_column: "1",
            schema.position_column: position,
            schema.song_column: song,
        }

    @pytest.mark.parametrize("band", sorted(SETLIST_SCHEMAS))
    def test_server_managed_keys_are_not_sent_and_other_fields_are_unchanged(
        self, band
    ):
        stored = [
            dict(self._band_row(band, i, f"Song {i}"), show_id="1") for i in (1, 2, 3)
        ]
        upstream = [
            dict(
                self._band_row(band, i, name),
                show_id="1",
                id=123,
                created_at=None,
                updated_at=None,
            )
            for i, name in ((1, "Song 1"), (2, "Hot Tea"), (3, "Song 3"))
        ]
        client = FakeClient({})

        result = detect_setlist_corrections(
            band,
            {"1": upstream},
            {"1": stored},
            dry_run=False,
            client=client,
        )

        assert result.corrections_applied == 1
        ((name, params),) = client.rpc_calls
        assert name == "replace_show_setlist"
        assert params["p_band"] == band and params["p_show_id"] == "1"
        sent = params["p_rows"]
        assert len(sent) == 3
        for sent_row, upstream_row in zip(sent, upstream):
            assert not {"id", "created_at", "updated_at"} & set(sent_row)
            assert sent_row == {
                k: v
                for k, v in upstream_row.items()
                if k not in {"id", "created_at", "updated_at"}
            }
        assert sent[1][SETLIST_SCHEMAS[band].song_column] == "Hot Tea"

    def test_non_server_managed_none_values_are_kept(self):
        upstream = [
            {
                "show_id": "1",
                "set_number": 1,
                "song_position": 1,
                "song_name": "Song 1",
                "song_notes": None,
            }
        ]
        assert _replacement_payload(upstream) == upstream

    def test_nan_values_become_json_safe_none(self):
        payload = _replacement_payload(
            [{"show_id": "1", "song_position": float("nan"), "song_name": "A"}]
        )
        assert payload == [{"show_id": "1", "song_position": None, "song_name": "A"}]
