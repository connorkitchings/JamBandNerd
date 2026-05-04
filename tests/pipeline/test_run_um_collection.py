from __future__ import annotations

import pandas as pd

from jambandnerd.db import connection as db_connection
from scripts import run_um_collection


def test_um_upsert_dedupes_duplicate_conflict_keys(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        run_um_collection,
        "validate_and_upsert_dataframe",
        lambda table_name, df, conflict_columns, **kwargs: captured.update(
            {
                "table_name": table_name,
                "df": df.copy(),
                "conflict_columns": conflict_columns,
                "kwargs": kwargs,
            }
        ),
    )

    df = pd.DataFrame(
        [
            {"source_url": "https://example.com/show", "show_date": "2026-04-01"},
            {"source_url": "https://example.com/show", "show_date": "2026-04-02"},
        ]
    )

    run_um_collection._upsert(
        "um_shows_raw",
        df,
        conflict_columns=["source_url"],
        skip_validation=False,
    )

    assert captured["table_name"] == "um_shows_raw"
    assert len(captured["df"]) == 1
    assert captured["df"].iloc[0]["show_date"] == "2026-04-02"


def test_um_collection_refreshes_upcoming_when_setlists_already_ingested(monkeypatch):
    upserted_tables = []

    class FakeCollector:
        EARLIEST_YEAR = 1998

        def collect_songs(self):
            return []

        def collect_venues(self):
            return []

        def collect_shows(self, **_kwargs):
            return [{"show_id": 1, "show_date": "2026-04-01"}]

        def collect_setlists(self, _shows_to_process):
            raise AssertionError("setlists should not be fetched")

    monkeypatch.setattr(
        run_um_collection, "ensure_source_reachable", lambda _band: None
    )
    monkeypatch.setattr(run_um_collection, "UmCollector", FakeCollector)
    monkeypatch.setattr(
        run_um_collection,
        "fetch_existing_values",
        lambda *_args, **_kwargs: {"1"},
    )
    monkeypatch.setattr(
        run_um_collection,
        "collect_upcoming_shows",
        lambda: [{"source_uuid": "38328e2c-56c6-463f-aa18-1641e417c49c"}],
    )
    monkeypatch.setattr(
        run_um_collection,
        "_upsert",
        lambda table_name, *_args, **_kwargs: upserted_tables.append(table_name),
    )
    monkeypatch.setattr(
        run_um_collection,
        "fetch_last_collection_timestamp",
        lambda *_args, **_kwargs: None,
    )
    # Mock get_supabase_client to avoid requiring environment variables in tests
    monkeypatch.setattr(
        db_connection,
        "get_supabase_client",
        lambda: None,
    )

    run_um_collection.run_um_collection()

    assert upserted_tables == ["um_shows_raw", "um_upcoming_shows"]
