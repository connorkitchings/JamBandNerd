from src.jambandnerd.data_collection.wsp.orchestration import (
    _assign_show_ids,
    _dedupe_show_batch,
    _probe_everydaycompanion_setlist_status,
    classify_missing_recent_setlists,
)


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


def test_probe_everydaycompanion_routes_through_make_simple_request(monkeypatch):
    """Probe must use the Playwright-backed request path so CI gets correct diagnoses.

    A direct ``session.get`` would 403 in CI and misclassify every
    page-missing case as ``ec_request_failed`` (observed in run #27509635859).
    """
    from src.jambandnerd.data_collection.wsp import orchestration as wsp_orch

    calls: list[tuple] = []

    class _FakeSession:
        def close(self):
            pass

    class _FakeResponse:
        status_code = 200

        def __init__(self, text: str):
            self.text = text
            self.url = "https://www.everydaycompanion.com/setlists/20260613a.asp"

    def fake_make_simple_request(session, url, **kwargs):
        calls.append((url, kwargs))
        return _FakeResponse("<html>no set markers here</html>")

    def fake_decode(response):
        return response.text

    def fake_page_has_setlist_table(_html, _show_id):
        return False

    def fake_create_session():
        return _FakeSession()

    def fake_cleanup():
        return None

    monkeypatch.setattr(wsp_orch, "make_simple_request", fake_make_simple_request)
    monkeypatch.setattr(wsp_orch, "decode_ec_response", fake_decode)
    monkeypatch.setattr(
        wsp_orch, "_page_has_setlist_table", fake_page_has_setlist_table
    )
    monkeypatch.setattr(wsp_orch, "create_enhanced_session", fake_create_session)
    monkeypatch.setattr(wsp_orch, "cleanup_playwright", fake_cleanup)

    url = "https://www.everydaycompanion.com/setlists/20260613a.asp"
    diagnosis = _probe_everydaycompanion_setlist_status(url, "22464")

    assert diagnosis == "upstream_missing_setlist"
    assert len(calls) == 1
    assert calls[0][0] == url
    assert calls[0][1].get("allow_redirects") is True


def test_probe_everydaycompanion_returns_ec_request_failed_on_requestexception(
    monkeypatch,
):
    """When the Playwright-backed request raises, the probe still surfaces ec_request_failed."""
    import requests

    from src.jambandnerd.data_collection.wsp import orchestration as wsp_orch

    class _FakeSession:
        def close(self):
            pass

    def fake_make_simple_request(session, url, **kwargs):
        raise requests.exceptions.RequestException("boom")

    monkeypatch.setattr(wsp_orch, "make_simple_request", fake_make_simple_request)
    monkeypatch.setattr(wsp_orch, "create_enhanced_session", lambda: _FakeSession())
    monkeypatch.setattr(wsp_orch, "cleanup_playwright", lambda: None)

    diagnosis = _probe_everydaycompanion_setlist_status(
        "https://www.everydaycompanion.com/setlists/20260613a.asp", "22464"
    )

    assert diagnosis == "ec_request_failed"
