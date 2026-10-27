"""Collection reliability: failure surfacing, partial refetch, paging, normalization."""

from __future__ import annotations

import sys
import types
from datetime import date

import pandas as pd
import pytest

import scripts.common as common
import scripts.run_eggy_collection as eggy_script
import scripts.run_goose_collection as goose_script
import scripts.run_wsp_collection as wsp_script
from jambandnerd.data_collection.wsp import orchestration
from jambandnerd.data_collection.wsp.status import CollectionStatus
from jambandnerd.transformations.normalization import normalize_prediction_inputs

TODAY = date(2026, 10, 27)


class _FakeTimer:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def log(self, band, **kwargs):
        self.calls.append({"band": band, **kwargs})


class _FakeCollector:
    def __init__(self, fail: bool) -> None:
        self.fail = fail

    def _get(self):
        if self.fail:
            raise ConnectionError("boom")
        return []

    collect_songs = collect_shows = collect_venues = collect_setlists = _get


def _patch_run_script(monkeypatch, module, collector_attr, *, fail, timer):
    monkeypatch.setattr(module, "CollectionTimer", lambda: timer)
    monkeypatch.setattr(module, "ensure_source_reachable", lambda _b: None)
    monkeypatch.setattr(module, "get_supabase_client", lambda: None)
    monkeypatch.setattr(module, collector_attr, lambda: _FakeCollector(fail=fail))
    if hasattr(module, "CloudflareBypass"):
        monkeypatch.setattr(module.CloudflareBypass, "cleanup", lambda: None)


@pytest.mark.parametrize(
    ("module", "run", "collector_attr", "band"),
    [
        (goose_script, "run_goose_collection", "GooseCollector", "goose"),
        (eggy_script, "run_eggy_collection", "EggyCollector", "eggy"),
    ],
)
def test_collector_error_reraises_and_logs_failed(
    monkeypatch, module, run, collector_attr, band
):
    timer = _FakeTimer()
    _patch_run_script(monkeypatch, module, collector_attr, fail=True, timer=timer)

    with pytest.raises(ConnectionError):
        getattr(module, run)()

    assert timer.calls == [{"band": band, "status": "failed"}]


@pytest.mark.parametrize(
    ("module", "run", "collector_attr"),
    [
        (goose_script, "run_goose_collection", "GooseCollector"),
        (eggy_script, "run_eggy_collection", "EggyCollector"),
    ],
)
def test_upsert_error_reraises(monkeypatch, module, run, collector_attr):
    _patch_run_script(
        monkeypatch, module, collector_attr, fail=False, timer=_FakeTimer()
    )
    monkeypatch.setattr(module, "normalize_songs", lambda _r: pd.DataFrame([{"a": 1}]))

    def failing_upsert(**_kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(module, "validate_and_upsert_dataframe", failing_upsert)

    with pytest.raises(RuntimeError, match="db down"):
        getattr(module, run)()


def test_wsp_fallback_error_path_returns_zero_pair():
    class ExplodingClient:
        def table(self, _name):
            raise RuntimeError("supabase unavailable")

    assert orchestration.tourwrangler_fallback(ExplodingClient()) == (0, 0)


def test_wsp_failure_outputs_honor_status_retry(tmp_path, monkeypatch):
    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    degraded = CollectionStatus()
    degraded.upstream_missing_setlists = 1  # degraded -> not retryable

    wsp_script._write_failure_github_outputs("x", status=degraded)
    assert "should_retry_collection=false" in out.read_text()

    out.write_text("")
    wsp_script._write_failure_github_outputs("x")
    assert "should_retry_collection=true" in out.read_text()


def test_recent_and_partial_setlists_are_refetched_old_complete_skipped():
    show_dates = {
        "old_complete": "2020-01-01",
        "old_partial": "2020-01-02",
        "old_missing": "2020-01-03",
        "recent_complete": "2026-10-24",
    }
    counts = {"old_complete": 12, "old_partial": 2, "recent_complete": 15}

    selected = common.select_shows_needing_setlist_fetch(
        show_dates, counts, today=TODAY
    )

    assert selected == {"old_partial", "old_missing", "recent_complete"}


class _Resp:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _CappedClient:
    """Fake Supabase client whose server caps every page at ``cap`` rows."""

    def __init__(self, total: int, cap: int = 1000, fail_after: int | None = None):
        self.rows = [{"id": i} for i in range(total)]
        self.cap = cap
        self.fail_after = fail_after
        self.requests = 0
        self._range = (0, 0)
        self._count = None

    def table(self, _name):
        self._range, self._count = (0, 0), None
        return self

    def select(self, _cols, count=None):
        self._count = count
        return self

    def limit(self, _n):
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        if self._count:
            return _Resp([], count=len(self.rows))
        self.requests += 1
        if self.fail_after is not None and self.requests > self.fail_after:
            raise RuntimeError("network")
        start, end = self._range
        end = min(end, start + self.cap - 1)
        return _Resp(self.rows[start : end + 1])


def _patch_client(monkeypatch, client):
    fake = types.ModuleType("src.jambandnerd.db.connection")
    fake.get_supabase_client = lambda: client
    monkeypatch.setitem(sys.modules, "src.jambandnerd.db.connection", fake)


def test_fetch_table_pages_through_server_row_cap(monkeypatch):
    client = _CappedClient(total=2500, cap=1000)
    _patch_client(monkeypatch, client)

    rows = common.fetch_table("t", chunk_size=10000)

    assert len(rows) == 2500
    assert client.requests == 3


def test_fetch_table_raises_instead_of_returning_partial_data(monkeypatch):
    client = _CappedClient(total=2500, cap=1000, fail_after=1)
    _patch_client(monkeypatch, client)

    with pytest.raises(RuntimeError, match="network"):
        common.fetch_table("t")


def test_normalization_drops_null_ids_and_songs_instead_of_stringifying():
    shows = pd.DataFrame(
        {"show_id": ["1", None], "show_date": ["2024-01-01", "2024-01-02"]}
    )
    setlists = pd.DataFrame(
        {
            "show_id": ["1", "1", None],
            "song_name": ["A", None, "B"],
            "set_number": [1, 1, 1],
            "song_position": [1, 2, 1],
        }
    )

    out_shows, out_setlists = normalize_prediction_inputs(shows, setlists)

    assert out_shows["show_id"].tolist() == ["1"]
    assert out_setlists["song_name"].tolist() == ["A"]


def test_normalization_dedupes_setlist_positions():
    shows = pd.DataFrame({"show_id": ["1"], "show_date": ["2024-01-01"]})
    setlists = pd.DataFrame(
        {
            "show_id": ["1", "1", "1"],
            "song_name": ["A", "A2", "B"],
            "set_number": [1, 1, 1],
            "song_position": [1, 1, 2],
        }
    )

    _, out = normalize_prediction_inputs(shows, setlists)

    assert len(out) == 2
    assert out["song_name"].tolist() == ["A2", "B"]
