from src.jambandnerd.data_collection.wsp.orchestration import (
    _assign_show_ids,
    _dedupe_show_batch,
    classify_missing_recent_setlists,
)
from src.jambandnerd.data_collection.wsp.status import CollectionStatus


class _QueryStub:
    def __init__(self, response_data):
        self._response_data = response_data

    def select(self, *_args, **_kwargs):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def execute(self):
        return type("Resp", (), {"data": self._response_data})()


class _ClientStub:
    def __init__(self, max_id_rows, existing_rows):
        self._max_id_rows = max_id_rows
        self._existing_rows = existing_rows
        self._table_calls = 0

    def table(self, _name):
        self._table_calls += 1
        if self._table_calls == 1:
            return _QueryStub(self._max_id_rows)
        return _QueryStub(self._existing_rows)


def test_dedupe_show_batch_collapses_duplicate_source_urls():
    shows = [
        {
            "show_date": "2026-02-14",
            "venue_name": "Moody Center",
            "city": "Austin",
            "state": "TX",
            "source_url": "https://www.everydaycompanion.com/setlists/20260214a.asp",
        },
        {
            "show_date": "2026-02-14",
            "venue_name": "The Moody Theater",
            "city": "Austin",
            "state": "TX",
            "source_url": "https://www.everydaycompanion.com/setlists/20260214a.asp",
        },
    ]

    deduped, duplicate_count = _dedupe_show_batch(shows)

    assert duplicate_count == 1
    assert len(deduped) == 1
    assert deduped[0]["source_url"] == shows[0]["source_url"]


def test_assign_show_ids_reuses_existing_id_by_source_url_despite_venue_drift():
    client = _ClientStub(
        max_id_rows=[{"show_id": 30000}],
        existing_rows=[
            {
                "show_id": 22453,
                "show_date": "2026-02-14",
                "venue_name": "The Moody Theater",
                "source_url": "https://www.everydaycompanion.com/setlists/20260214a.asp",
            }
        ],
    )
    shows = [
        {
            "show_date": "2026-02-14",
            "venue_name": "Moody Center",
            "city": "Austin",
            "state": "TX",
            "source_url": "https://www.everydaycompanion.com/setlists/20260214a.asp",
        }
    ]

    resolved, stats = _assign_show_ids(
        shows,
        client=client,
        year_start=2025,
        year_end=2026,
        full_backfill=False,
    )

    assert resolved[0]["show_id"] == 22453
    assert stats["reused_by_source_url"] == 1
    assert stats["new_ids_assigned"] == 0


def test_assign_show_ids_falls_back_to_date_and_normalized_venue_when_url_missing():
    client = _ClientStub(
        max_id_rows=[{"show_id": 30000}],
        existing_rows=[
            {
                "show_id": 22454,
                "show_date": "2026-02-15",
                "venue_name": "The Fabulous Fox Theatre",
                "source_url": None,
            }
        ],
    )
    shows = [
        {
            "show_date": "2026-02-15",
            "venue_name": "Fabulous Fox Theatre",
            "city": "Atlanta",
            "state": "GA",
            "source_url": None,
        }
    ]

    resolved, stats = _assign_show_ids(
        shows,
        client=client,
        year_start=2025,
        year_end=2026,
        full_backfill=False,
    )

    assert resolved[0]["show_id"] == 22454
    assert stats["reused_by_fallback_key"] == 1
    assert stats["new_ids_assigned"] == 0


def test_classify_missing_recent_setlists_marks_upstream_missing(monkeypatch):
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration._probe_everydaycompanion_setlist_status",
        lambda source_url, show_id: "upstream_missing_setlist",
    )
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration._resolve_recent_wsp_fallback",
        lambda *_args, **_kwargs: ([], None, []),
    )

    diagnostics = classify_missing_recent_setlists(
        client=None,
        missing_shows=[
            {
                "show_id": 22455,
                "show_date": "2026-03-20",
                "city": "St. Augustine",
                "state": "FL",
                "source_url": "https://www.everydaycompanion.com/setlists/20260320a.asp",
            }
        ],
    )

    assert diagnostics == [
        {
            "show_id": "22455",
            "show_date": "2026-03-20",
            "diagnosis": "upstream_missing_setlist",
            "detail": "Everyday Companion page has no setlist table",
        }
    ]


def test_classify_missing_recent_setlists_marks_fallback_available(monkeypatch):
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration._probe_everydaycompanion_setlist_status",
        lambda source_url, show_id: "ec_request_failed",
    )
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration._resolve_recent_wsp_fallback",
        lambda *_args, **_kwargs: (
            [{"song_name": "Surprise Valley"}],
            "panicstream",
            [],
        ),
    )

    diagnostics = classify_missing_recent_setlists(
        client=None,
        missing_shows=[
            {
                "show_id": 22455,
                "show_date": "2026-03-20",
                "city": "St. Augustine",
                "state": "FL",
                "source_url": "https://www.everydaycompanion.com/setlists/20260320a.asp",
            }
        ],
    )

    assert diagnostics[0]["diagnosis"] == "fallback_data_available"
    assert diagnostics[0]["detail"] == "PanicStream returned backup rows for this show"


def test_classify_missing_recent_setlists_uses_tourwrangler_after_empty_panicstream(
    monkeypatch,
):
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration._probe_everydaycompanion_setlist_status",
        lambda source_url, show_id: "ec_request_failed",
    )
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration._resolve_recent_wsp_fallback",
        lambda *_args, **_kwargs: (
            [{"song_name": "Surprise Valley"}],
            "tourwrangler",
            [],
        ),
    )

    diagnostics = classify_missing_recent_setlists(
        client=None,
        missing_shows=[
            {
                "show_id": 22456,
                "show_date": "2026-03-21",
                "city": "St. Augustine",
                "state": "FL",
                "source_url": "https://www.everydaycompanion.com/setlists/20260321a.asp",
            }
        ],
    )

    assert diagnostics[0]["diagnosis"] == "fallback_data_available"
    assert diagnostics[0]["detail"] == "TourWrangler returned backup rows for this show"


def test_classify_missing_recent_setlists_keeps_request_failed_when_all_fallbacks_empty(
    monkeypatch,
):
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration._probe_everydaycompanion_setlist_status",
        lambda source_url, show_id: "ec_request_failed",
    )
    monkeypatch.setattr(
        "src.jambandnerd.data_collection.wsp.orchestration._resolve_recent_wsp_fallback",
        lambda *_args, **_kwargs: ([], None, []),
    )

    diagnostics = classify_missing_recent_setlists(
        client=None,
        missing_shows=[
            {
                "show_id": 22457,
                "show_date": "2026-03-22",
                "city": "St. Augustine",
                "state": "FL",
                "source_url": "https://www.everydaycompanion.com/setlists/20260322a.asp",
            }
        ],
    )

    assert diagnostics == [
        {
            "show_id": "22457",
            "show_date": "2026-03-22",
            "diagnosis": "ec_request_failed",
            "detail": "Everyday Companion request failed and fallback was empty",
        }
    ]


class TestCollectionStatusOutcomeCode:
    def test_success_when_no_issues(self):
        status = CollectionStatus()
        status.songs_collected = 100
        status.shows_collected = 10
        assert status.outcome_code() == "success"

    def test_failed_upstream_stale_when_no_data_and_request_blocked(self):
        status = CollectionStatus()
        status.request_blocked_missing_setlists = 1
        assert status.outcome_code() == "failed_upstream_stale"

    def test_degraded_upstream_stale_when_shows_collected_and_request_blocked(self):
        status = CollectionStatus()
        status.request_blocked_missing_setlists = 1
        status.shows_collected = 74
        assert status.outcome_code() == "degraded_upstream_stale"

    def test_degraded_upstream_stale_when_songs_collected_and_request_blocked(self):
        status = CollectionStatus()
        status.request_blocked_missing_setlists = 1
        status.songs_collected = 708
        assert status.outcome_code() == "degraded_upstream_stale"

    def test_workflow_state_degraded_when_upstream_stale_with_data(self):
        status = CollectionStatus()
        status.request_blocked_missing_setlists = 1
        status.shows_collected = 74
        assert status.workflow_state() == "degraded"

    def test_should_not_retry_when_degraded(self):
        status = CollectionStatus()
        status.request_blocked_missing_setlists = 1
        status.shows_collected = 74
        assert status.should_retry_collection() is False
