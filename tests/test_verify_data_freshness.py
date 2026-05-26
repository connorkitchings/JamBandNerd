from __future__ import annotations

from unittest import mock
from unittest.mock import patch

from scripts.verify_data_freshness import (
    RecentSetlistCompletenessResult,
    _fetch_song_counts_per_show,
    audit_recent_setlist_completeness,
)


class TestRecentSetlistCompletenessResult:
    def test_ok_true_when_no_missing_and_no_partial(self):
        result = RecentSetlistCompletenessResult(
            band="goose",
            cutoff="2026-05-19",
            end_date="2026-05-25",
            recent_show_count=2,
            missing_show_count=0,
            missing_show_ids=(),
            partial_show_count=0,
            partial_show_ids=(),
            min_unique_songs=3,
        )
        assert result.ok is True

    def test_ok_false_when_missing(self):
        result = RecentSetlistCompletenessResult(
            band="goose",
            cutoff="2026-05-19",
            end_date="2026-05-25",
            recent_show_count=2,
            missing_show_count=1,
            missing_show_ids=("1",),
            partial_show_count=0,
            partial_show_ids=(),
            min_unique_songs=3,
        )
        assert result.ok is False

    def test_ok_false_when_partial(self):
        result = RecentSetlistCompletenessResult(
            band="goose",
            cutoff="2026-05-19",
            end_date="2026-05-25",
            recent_show_count=2,
            missing_show_count=0,
            missing_show_ids=(),
            partial_show_count=1,
            partial_show_ids=("2",),
            min_unique_songs=3,
        )
        assert result.ok is False

    def test_ok_false_when_both_missing_and_partial(self):
        result = RecentSetlistCompletenessResult(
            band="goose",
            cutoff="2026-05-19",
            end_date="2026-05-25",
            recent_show_count=3,
            missing_show_count=1,
            missing_show_ids=("1",),
            partial_show_count=2,
            partial_show_ids=("2", "3"),
            min_unique_songs=3,
        )
        assert result.ok is False

    def test_as_dict_includes_all_fields(self):
        result = RecentSetlistCompletenessResult(
            band="goose",
            cutoff="2026-05-19",
            end_date="2026-05-25",
            recent_show_count=2,
            missing_show_count=0,
            missing_show_ids=(),
            partial_show_count=1,
            partial_show_ids=("3",),
            min_unique_songs=3,
        )
        d = result.as_dict()
        assert d["band"] == "goose"
        assert d["ok"] is False
        assert d["missing_show_ids"] == []
        assert d["partial_show_ids"] == ["3"]
        assert d["min_unique_songs"] == 3

    def test_defaults_produce_empty_partial(self):
        result = RecentSetlistCompletenessResult(
            band="goose",
            cutoff="2026-05-19",
            end_date="2026-05-25",
            recent_show_count=2,
            missing_show_count=0,
            missing_show_ids=(),
        )
        assert result.partial_show_count == 0
        assert result.partial_show_ids == ()
        assert result.min_unique_songs == 3
        assert result.ok is True


class TestFetchSongCountsPerShow:
    def test_counts_unique_songs_per_show(self):
        rows = [
            {"show_id": "1", "song_name": "Animal"},
            {"show_id": "1", "song_name": "Arcadia"},
            {"show_id": "1", "song_name": "Animal"},  # duplicate
            {"show_id": "2", "song_name": "Borne"},
            {"show_id": "2", "song_name": "Butter Rum"},
            {"show_id": "2", "song_name": "Creatures"},
            {"show_id": "2", "song_name": "Dripfield"},
        ]
        with patch("scripts.verify_data_freshness.fetch_table_rows", return_value=rows):
            result = _fetch_song_counts_per_show(
                None, "goose_setlists_raw", "show_id", {"1", "2"}
            )
        assert result == {"1": 2, "2": 4}

    def test_returns_empty_for_empty_ids(self):
        with patch("scripts.verify_data_freshness.fetch_table_rows", return_value=[]):
            result = _fetch_song_counts_per_show(
                None, "goose_setlists_raw", "show_id", set()
            )
        assert result == {}

    def test_returns_empty_for_no_rows(self):
        with patch("scripts.verify_data_freshness.fetch_table_rows", return_value=[]):
            result = _fetch_song_counts_per_show(
                None, "goose_setlists_raw", "show_id", {"99"}
            )
        assert result == {}

    def test_skips_rows_missing_song_name(self):
        rows = [
            {"show_id": "1", "song_name": None},
            {"show_id": "1", "song_name": "Arcadia"},
        ]
        with patch("scripts.verify_data_freshness.fetch_table_rows", return_value=rows):
            result = _fetch_song_counts_per_show(
                None, "goose_setlists_raw", "show_id", {"1"}
            )
        assert result == {"1": 1}

    def test_skips_rows_missing_id_column(self):
        rows = [
            {"show_id": None, "song_name": "Arcadia"},
            {"show_id": "1", "song_name": "Borne"},
        ]
        with patch("scripts.verify_data_freshness.fetch_table_rows", return_value=rows):
            result = _fetch_song_counts_per_show(
                None, "goose_setlists_raw", "show_id", {"1"}
            )
        assert result == {"1": 1}


class TestAuditRecentSetlistCompleteness:
    @staticmethod
    def _patch_helpers(
        shows=None,
        setlist_ids=None,
        setlist_rows=None,
        cutoff="2026-05-19",
        end_date="2026-05-25",
    ):
        def _ftr(table_name, filters=None, client=None, **__):
            if setlist_rows is not None and "setlists" in table_name:
                return setlist_rows
            return shows or []

        def _fcv(table_name, id_column, ids, client=None, select_column=None, **__):
            return setlist_ids or set()

        return mock.patch.multiple(
            "scripts.verify_data_freshness",
            completed_show_window=mock.Mock(return_value=(cutoff, end_date)),
            fetch_table_rows=mock.Mock(side_effect=_ftr),
            fetch_column_values_for_ids=mock.Mock(side_effect=_fcv),
            get_supabase_client=mock.Mock(return_value=None),
        )

    def test_no_shows_in_window(self):
        with self._patch_helpers(shows=[]):
            result = audit_recent_setlist_completeness(
                "goose", client=None, emit_text=False
            )
        assert result.ok is True
        assert result.recent_show_count == 0
        assert result.missing_show_count == 0
        assert result.partial_show_count == 0

    def test_all_shows_have_complete_setlists(self):
        shows = [
            {"show_id": 1, "show_date": "2026-05-21", "venue": "Capitol"},
            {"show_id": 2, "show_date": "2026-05-22", "venue": "Capitol"},
        ]
        setlist_rows = [
            {"show_id": 1, "song_name": "Animal"},
            {"show_id": 1, "song_name": "Arcadia"},
            {"show_id": 1, "song_name": "Borne"},
            {"show_id": 2, "song_name": "Animal"},
            {"show_id": 2, "song_name": "Butter Rum"},
            {"show_id": 2, "song_name": "Creatures"},
            {"show_id": 2, "song_name": "Dripfield"},
        ]
        with self._patch_helpers(
            shows=shows,
            setlist_ids={"1", "2"},
            setlist_rows=setlist_rows,
        ):
            result = audit_recent_setlist_completeness(
                "goose", client=None, emit_text=False
            )
        assert result.ok is True
        assert result.recent_show_count == 2
        assert result.missing_show_count == 0
        assert result.partial_show_count == 0

    def test_show_with_no_setlist_rows_is_missing(self):
        shows = [
            {"show_id": 1, "show_date": "2026-05-21"},
            {"show_id": 2, "show_date": "2026-05-22"},
        ]
        setlist_rows = [
            {"show_id": 1, "song_name": "Animal"},
            {"show_id": 1, "song_name": "Arcadia"},
            {"show_id": 1, "song_name": "Borne"},
        ]
        with self._patch_helpers(
            shows=shows,
            setlist_ids={"1"},
            setlist_rows=setlist_rows,
        ):
            result = audit_recent_setlist_completeness(
                "goose", client=None, emit_text=False
            )
        assert result.ok is False
        assert result.missing_show_count == 1
        assert result.missing_show_ids == ("2",)
        assert result.partial_show_count == 0

    def test_show_with_below_threshold_songs_is_partial(self):
        shows = [
            {"show_id": 1, "show_date": "2026-05-21"},
            {"show_id": 2, "show_date": "2026-05-22"},
        ]
        setlist_rows = [
            {"show_id": 1, "song_name": "Animal"},
            {"show_id": 1, "song_name": "Arcadia"},
            {"show_id": 1, "song_name": "Borne"},
            {"show_id": 1, "song_name": "Butter Rum"},
            {"show_id": 2, "song_name": "Creatures"},
            {"show_id": 2, "song_name": "Dripfield"},
        ]
        with self._patch_helpers(
            shows=shows,
            setlist_ids={"1", "2"},
            setlist_rows=setlist_rows,
        ):
            result = audit_recent_setlist_completeness(
                "goose", client=None, emit_text=False
            )
        assert result.ok is False
        assert result.missing_show_count == 0
        assert result.partial_show_count == 1
        assert result.partial_show_ids == ("2",)

    def test_show_with_exactly_threshold_songs_is_not_partial(self):
        shows = [
            {"show_id": 1, "show_date": "2026-05-21"},
            {"show_id": 2, "show_date": "2026-05-22"},
        ]
        setlist_rows = [
            {"show_id": 1, "song_name": "Animal"},
            {"show_id": 1, "song_name": "Arcadia"},
            {"show_id": 1, "song_name": "Borne"},
            {"show_id": 2, "song_name": "Animal"},
            {"show_id": 2, "song_name": "Butter Rum"},
            {"show_id": 2, "song_name": "Creatures"},
        ]
        with self._patch_helpers(
            shows=shows,
            setlist_ids={"1", "2"},
            setlist_rows=setlist_rows,
        ):
            result = audit_recent_setlist_completeness(
                "goose",
                client=None,
                emit_text=False,
                min_unique_songs=3,
            )
        assert result.ok is True
        assert result.partial_show_count == 0

    def test_custom_min_unique_songs_threshold(self):
        shows = [
            {"show_id": 1, "show_date": "2026-05-21"},
        ]
        setlist_rows = [
            {"show_id": 1, "song_name": "Animal"},
            {"show_id": 1, "song_name": "Arcadia"},
            {"show_id": 1, "song_name": "Borne"},
            {"show_id": 1, "song_name": "Butter Rum"},
        ]
        with self._patch_helpers(
            shows=shows,
            setlist_ids={"1"},
            setlist_rows=setlist_rows,
        ):
            result = audit_recent_setlist_completeness(
                "goose",
                client=None,
                emit_text=False,
                min_unique_songs=5,
            )
        assert result.ok is False
        assert result.partial_show_count == 1

    def test_mixed_missing_and_partial(self):
        shows = [
            {"show_id": "a", "show_date": "2026-05-20"},
            {"show_id": "b", "show_date": "2026-05-21"},
            {"show_id": "c", "show_date": "2026-05-22"},
        ]
        setlist_rows = [
            {"show_id": "a", "song_name": "Animal"},
            {"show_id": "a", "song_name": "Arcadia"},
            {"show_id": "a", "song_name": "Borne"},
            {"show_id": "a", "song_name": "Butter Rum"},
            {"show_id": "b", "song_name": "Creatures"},
        ]
        with self._patch_helpers(
            shows=shows,
            setlist_ids={"a", "b"},
            setlist_rows=setlist_rows,
        ):
            result = audit_recent_setlist_completeness(
                "goose", client=None, emit_text=False
            )
        assert result.ok is False
        assert result.missing_show_count == 1
        assert result.missing_show_ids == ("c",)
        assert result.partial_show_count == 1
        assert result.partial_show_ids == ("b",)
