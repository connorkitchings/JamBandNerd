from datetime import date, datetime, timezone

import pytest

from jambandnerd.utils.dates import current_show_date
from scripts import common as scripts_common
from scripts.common import (
    _source_health_url,
    completed_show_window,
    ensure_source_reachable,
)
from scripts.diagnose_band_data import (
    _completed_show_bounds,
    _fetch_setlist_ids_for_shows,
    _summarize_missing_setlist_diagnostics,
)


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


class _CollectorConfigStub:
    def __init__(self, base_url):
        self.base_url = base_url
        self.user_agent = "test-agent"


class _HttpResponseStub:
    def __init__(self, status_code):
        self.status_code = status_code


def test_completed_show_window_excludes_today():
    cutoff, end_date = completed_show_window(today=date(2026, 3, 17), days=7)
    assert cutoff == "2026-03-10"
    assert end_date == "2026-03-16"


def test_current_show_date_uses_us_eastern_after_utc_midnight():
    # 2026-11-21T00:31Z is 2026-11-20 19:31 EST (show in progress, not completed)
    assert current_show_date(
        datetime(2026, 11, 21, 0, 31, tzinfo=timezone.utc)
    ) == date(2026, 11, 20)
    # 2026-07-15T01:30Z is 2026-07-14 21:30 EDT
    assert current_show_date(datetime(2026, 7, 15, 1, 30, tzinfo=timezone.utc)) == date(
        2026, 7, 14
    )
    # 2026-11-21T05:00Z is 2026-11-21 00:00 EST
    assert current_show_date(datetime(2026, 11, 21, 5, 0, tzinfo=timezone.utc)) == date(
        2026, 11, 21
    )


def test_completed_show_window_defaults_to_us_eastern_date(monkeypatch):
    monkeypatch.setattr(
        scripts_common,
        "current_show_date",
        lambda: current_show_date(datetime(2026, 11, 21, 0, 31, tzinfo=timezone.utc)),
    )
    cutoff, end_date = completed_show_window(days=7)
    assert cutoff == "2026-11-13"
    assert end_date == "2026-11-19"


def test_source_health_url_uses_concrete_um_api_endpoint():
    url = _source_health_url(
        "um",
        _CollectorConfigStub("https://allthings.umphreys.com/api"),
        today=date(2026, 5, 14),
    )

    assert (
        url
        == "https://allthings.umphreys.com/api/v2/setlists/showyear/2026.json?order_by=showdate"
    )


def test_source_health_url_handles_um_site_root_config():
    url = _source_health_url(
        "um",
        _CollectorConfigStub("https://allthings.umphreys.com"),
        today=date(2026, 5, 14),
    )

    assert (
        url
        == "https://allthings.umphreys.com/api/v2/setlists/showyear/2026.json?order_by=showdate"
    )


def test_ensure_source_reachable_allows_um_when_concrete_endpoint_is_ok(monkeypatch):
    calls = []

    def fake_get(url, **_kwargs):
        calls.append(url)
        return _HttpResponseStub(200)

    monkeypatch.setattr("requests.get", fake_get)

    ensure_source_reachable("um")

    assert calls == [
        "https://allthings.umphreys.com/api/v2/setlists/showyear/"
        f"{date.today().year}.json?order_by=showdate"
    ]


def test_ensure_source_reachable_fails_when_um_concrete_endpoint_fails(monkeypatch):
    monkeypatch.setattr(
        "requests.get", lambda *_args, **_kwargs: _HttpResponseStub(500)
    )

    with pytest.raises(RuntimeError, match="Received status 500"):
        ensure_source_reachable("um")


def test_ensure_source_reachable_keeps_non_um_500_strict(monkeypatch):
    calls = []

    def fake_get(url, **_kwargs):
        calls.append(url)
        return _HttpResponseStub(500)

    monkeypatch.setattr("requests.get", fake_get)

    with pytest.raises(RuntimeError, match="Received status 500"):
        ensure_source_reachable("goose")

    assert calls == ["https://elgoose.net/api"]


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
