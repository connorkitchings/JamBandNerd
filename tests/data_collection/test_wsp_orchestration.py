from src.jambandnerd.data_collection.wsp.orchestration import (
    _assign_show_ids,
    _dedupe_show_batch,
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
