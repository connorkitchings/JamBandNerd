from datetime import date

from scripts.diagnose_band_data import (
    _completed_show_bounds,
    _fetch_setlist_ids_for_shows,
    _summarize_missing_setlist_diagnostics,
)
from scripts.verify_data_freshness import _completed_show_window


class _ResponseStub:
    def __init__(self, data):
        self.data = data


class _QueryStub:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []

    def select(self, *_args, **_kwargs):
        return self

    def in_(self, column, values):
        self._filters.append((column, set(values)))
        return self

    def execute(self):
        rows = list(self._rows)
        for column, values in self._filters:
            rows = [row for row in rows if row.get(column) in values]
        return _ResponseStub(rows)


class _ClientStub:
    def __init__(self, rows):
        self._rows = rows
        self.calls = []

    def table(self, name):
        self.calls.append(name)
        return _QueryStub(self._rows)


def test_completed_show_window_excludes_today():
    cutoff, end_date = _completed_show_window(today=date(2026, 3, 17), days=7)
    assert cutoff == "2026-03-10"
    assert end_date == "2026-03-16"


def test_completed_show_bounds_excludes_today():
    cutoff, end_date = _completed_show_bounds(today=date(2026, 3, 17), days=30)
    assert cutoff == "2026-02-15"
    assert end_date == "2026-03-16"


def test_fetch_setlist_ids_for_shows_limits_lookup_to_target_ids():
    client = _ClientStub(
        [
            {"show_id": "1"},
            {"show_id": "2"},
            {"show_id": "999"},
        ]
    )

    result = _fetch_setlist_ids_for_shows(
        client,
        "um_setlists_raw",
        "show_id",
        {"1", "2", "3"},
    )

    assert result == {"1", "2"}
    assert client.calls == ["um_setlists_raw"]


def test_summarize_missing_setlist_diagnostics_treats_wsp_upstream_lag_as_warning():
    issue, warning = _summarize_missing_setlist_diagnostics(
        "wsp",
        [
            {
                "diagnosis": "upstream_missing_setlist",
                "detail": "Everyday Companion page has no setlist table",
            }
        ],
    )

    assert issue is None
    assert warning == (
        "1 WSP shows are blocked by upstream setlist pages that have not "
        "published a setlist yet"
    )


def test_summarize_missing_setlist_diagnostics_treats_wsp_collector_gap_as_issue():
    issue, warning = _summarize_missing_setlist_diagnostics(
        "wsp",
        [{"diagnosis": "collector_missed_setlist"}],
    )

    assert issue == "1 WSP shows without setlist data (collector_missed_setlist=1)"
    assert warning is None
