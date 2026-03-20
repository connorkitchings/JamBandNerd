from __future__ import annotations

from types import SimpleNamespace

import pandas as pd

from scripts import run_billy_collection
from src.jambandnerd.data_collection.wsp import orchestration as wsp_orchestration


class _BillyCollectorStub:
    def __init__(self):
        self.setlist_calls = []

    def collect_songs(self):
        return []

    def collect_shows(self, start_date=None, end_date=None):
        return [
            {
                "source_uuid": "existing-show",
                "show_date": "2024-03-01",
                "venue_name": "Venue 1",
                "source_url": "https://bmfsdb.com/setlist/existing-show",
            },
            {
                "source_uuid": "new-show",
                "show_date": "2024-03-02",
                "venue_name": "Venue 2",
                "source_url": "https://bmfsdb.com/setlist/new-show",
            },
        ]

    def collect_setlists(self, shows_to_process):
        self.setlist_calls.append(shows_to_process)
        return [
            {
                "show_id": shows_to_process[0]["show_id"],
                "set_number": 1,
                "song_position": 1,
                "song_name": "Song A",
            }
        ]


class _WSPCollectorStub:
    def __init__(self, status=None):
        self.status = status
        self.records_for_scrape = None

    def collect_songs(self):
        return [{"api_song_id": 1, "song_name": "Song A"}]

    def collect_shows(self, start_date=None, end_date=None):
        return [
            {
                "show_id": 1,
                "show_date": "2024-03-01",
                "venue_name": "Venue 1",
                "source_url": "https://ec.example/show-1",
            },
            {
                "show_id": 2,
                "show_date": "2024-03-02",
                "venue_name": "Venue 2",
                "source_url": "https://ec.example/show-2",
            },
        ]

    def collect_venues(self):
        return [{"venue_id": "venue-1", "venue_name": "Venue 1"}]

    def collect_setlists(self, records_for_scrape):
        self.records_for_scrape = records_for_scrape
        return [
            {
                "show_id": 2,
                "set_number": 1,
                "song_position": 1,
                "song_name": "Song A",
            }
        ]


class _WSPQueryStub:
    def __init__(self, response_data):
        self.response_data = response_data

    def select(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def lt(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self.response_data)


class _WSPClientStub:
    def __init__(self):
        self.responses = {
            "wsp_shows_raw": [
                {
                    "show_id": 1,
                    "show_date": "2024-03-01",
                    "venue_name": "Venue 1",
                    "source_url": "https://ec.example/show-1",
                },
                {
                    "show_id": 2,
                    "show_date": "2024-03-02",
                    "venue_name": "Venue 2",
                    "source_url": "https://ec.example/show-2",
                },
            ],
            "wsp_setlists_raw": [],
        }

    def table(self, name):
        return _WSPQueryStub(self.responses.get(name, []))


def test_run_billy_collection_uses_paginated_existing_setlist_reads(monkeypatch):
    collector = _BillyCollectorStub()
    lookup_calls = []

    def fake_fetch_rows_by_column_values(
        table_name, *, select_columns, filter_column, values, chunk_size=200
    ):
        lookup_calls.append(
            (
                "rows",
                table_name,
                tuple(select_columns),
                filter_column,
                tuple(values),
                chunk_size,
            )
        )
        if table_name == "billy_shows_raw":
            return [
                {
                    "show_id": 1001,
                    "source_uuid": "existing-show",
                    "source_url": "https://bmfsdb.com/setlist/existing-show",
                    "show_date": "2024-03-01",
                },
                {
                    "show_id": 1002,
                    "source_uuid": "new-show",
                    "source_url": "https://bmfsdb.com/setlist/new-show",
                    "show_date": "2024-03-02",
                },
            ]
        raise AssertionError(f"unexpected lookup for {table_name}")

    def fake_fetch_existing_values(
        table_name, *, value_column, candidate_values, chunk_size=200
    ):
        lookup_calls.append(
            (
                "existing",
                table_name,
                value_column,
                tuple(candidate_values),
                chunk_size,
            )
        )
        assert table_name == "billy_setlists_raw"
        assert value_column == "show_id"
        return {"1001"}

    monkeypatch.setattr(
        run_billy_collection, "ensure_source_reachable", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(run_billy_collection, "BillyCollector", lambda: collector)
    monkeypatch.setattr(
        run_billy_collection,
        "fetch_rows_by_column_values",
        fake_fetch_rows_by_column_values,
    )
    monkeypatch.setattr(
        run_billy_collection,
        "fetch_existing_values",
        fake_fetch_existing_values,
    )
    monkeypatch.setattr(
        run_billy_collection,
        "validate_and_upsert_dataframe",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        run_billy_collection, "_log_collection_run", lambda *_args, **_kwargs: None
    )

    run_billy_collection.run_billy_collection(skip_validation=True)

    assert lookup_calls == [
        (
            "rows",
            "billy_shows_raw",
            ("show_id", "source_uuid", "source_url", "show_date"),
            "source_uuid",
            ("existing-show", "new-show"),
            200,
        ),
        ("existing", "billy_setlists_raw", "show_id", (1001, 1002), 200),
    ]
    assert collector.setlist_calls == [
        [
            {
                "show_id": 1002,
                "source_url": "https://bmfsdb.com/setlist/new-show",
                "source_uuid": "new-show",
                "show_date": "2024-03-02",
            }
        ]
    ]


def test_wsp_process_uses_paginated_existing_setlist_reads(monkeypatch):
    collector = _WSPCollectorStub()
    client = _WSPClientStub()
    lookup_calls = []

    def fake_fetch_existing_values(
        table_name, *, value_column, candidate_values, chunk_size=200
    ):
        lookup_calls.append(
            (
                table_name,
                value_column,
                tuple(candidate_values),
                chunk_size,
            )
        )
        assert table_name == "wsp_setlists_raw"
        assert value_column == "show_id"
        return {"1"}

    monkeypatch.setattr(
        wsp_orchestration, "ensure_source_reachable", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        wsp_orchestration, "WSPCollector", lambda status=None: collector
    )
    monkeypatch.setattr(wsp_orchestration, "get_supabase_client", lambda: client)
    monkeypatch.setattr(
        wsp_orchestration,
        "fetch_existing_values",
        fake_fetch_existing_values,
    )
    monkeypatch.setattr(
        wsp_orchestration, "get_table_schema", lambda *_args, **_kwargs: []
    )
    monkeypatch.setattr(
        wsp_orchestration,
        "validate_and_upsert_dataframe",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        wsp_orchestration, "tourwrangler_fallback", lambda *_args, **_kwargs: (0, 0)
    )
    monkeypatch.setattr(
        wsp_orchestration,
        "_assign_show_ids",
        lambda shows_data, **_kwargs: (
            shows_data,
            {
                "deduped_in_batch": 0,
                "reused_by_source_url": 0,
                "reused_by_fallback_key": 0,
                "new_ids_assigned": 0,
            },
        ),
    )
    monkeypatch.setattr(
        wsp_orchestration, "_validate_resolved_shows", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        wsp_orchestration,
        "normalize_songs",
        lambda rows: pd.DataFrame(rows),
    )
    monkeypatch.setattr(
        wsp_orchestration,
        "normalize_shows",
        lambda rows: pd.DataFrame(rows),
    )
    monkeypatch.setattr(
        wsp_orchestration,
        "normalize_venues",
        lambda rows: pd.DataFrame(rows),
    )
    monkeypatch.setattr(
        wsp_orchestration,
        "normalize_setlists",
        lambda rows: pd.DataFrame(rows),
    )

    wsp_orchestration.process_wsp_data(
        skip_existing_setlists=True,
        year_start=2024,
        year_end=2024,
    )

    assert lookup_calls == [("wsp_setlists_raw", "show_id", (1, 2), 200)]
    assert collector.records_for_scrape == [
        {
            "show_id": 2,
            "show_date": "2024-03-02",
            "venue_name": "Venue 2",
            "source_url": "https://ec.example/show-2",
        }
    ]
