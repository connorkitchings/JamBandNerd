from __future__ import annotations

import pandas as pd

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


def test_sync_um_songs_updates_existing_and_inserts_new(monkeypatch):
    events: list[tuple[str, object]] = []

    class _TableStub:
        def update(self, record):
            events.append(("update", record["song_name"]))
            return self

        def eq(self, column, value):
            events.append((f"eq:{column}", value))
            return self

        def execute(self):
            events.append(("execute", None))
            return None

    class _ClientStub:
        def table(self, table_name):
            events.append(("table", table_name))
            return _TableStub()

    inserted: list[dict[str, object]] = []
    monkeypatch.setattr(run_um_collection, "get_supabase_client", lambda: _ClientStub())
    monkeypatch.setattr(
        run_um_collection,
        "prepare_dataframe_for_upsert",
        lambda _table, df, **_kwargs: df,
    )
    monkeypatch.setattr(
        run_um_collection,
        "fetch_existing_values",
        lambda *_args, **_kwargs: {"Existing Song"},
    )
    monkeypatch.setattr(
        run_um_collection,
        "bulk_insert_dataframe",
        lambda _table, df: inserted.extend(df.to_dict(orient="records")),
    )
    monkeypatch.setattr(run_um_collection, "_next_um_song_id", lambda: 42)

    df = pd.DataFrame(
        [
            {"song_name": "Existing Song", "song_slug": "existing-song"},
            {"song_name": "New Song", "song_slug": "new-song"},
        ]
    )

    run_um_collection._sync_um_songs_raw(df, skip_validation=False)

    assert ("update", "Existing Song") in events
    assert ("eq:song_name", "Existing Song") in events
    assert [row["song_name"] for row in inserted] == ["New Song"]
    assert [row["song_id"] for row in inserted] == [42]


def test_sync_um_venues_updates_existing_and_inserts_new(monkeypatch):
    events: list[tuple[str, object]] = []

    class _TableStub:
        def update(self, record):
            events.append(("update", record["venue_id"]))
            return self

        def eq(self, column, value):
            events.append((f"eq:{column}", value))
            return self

        def execute(self):
            events.append(("execute", None))
            return None

    class _ClientStub:
        def table(self, table_name):
            events.append(("table", table_name))
            return _TableStub()

    inserted: list[dict[str, object]] = []
    monkeypatch.setattr(run_um_collection, "get_supabase_client", lambda: _ClientStub())
    monkeypatch.setattr(
        run_um_collection,
        "prepare_dataframe_for_upsert",
        lambda _table, df, **_kwargs: df.drop(columns=["_is_existing"]),
    )
    monkeypatch.setattr(
        run_um_collection,
        "fetch_rows_by_column_values",
        lambda *_args, **_kwargs: [
            {
                "venue_id": 7,
                "venue_name": "Existing Room",
                "venue_city": "Chicago",
                "venue_state": "IL",
                "venue_country": "USA",
            }
        ],
    )
    monkeypatch.setattr(run_um_collection, "_next_numeric_id", lambda *_args: 42)
    monkeypatch.setattr(
        run_um_collection,
        "bulk_insert_dataframe",
        lambda _table, df: inserted.extend(df.to_dict(orient="records")),
    )

    df = pd.DataFrame(
        [
            {
                "venue_name": "Existing Room",
                "venue_city": "Chicago",
                "venue_state": "IL",
                "venue_country": "USA",
            },
            {
                "venue_name": "New Room",
                "venue_city": "Milwaukee",
                "venue_state": "WI",
                "venue_country": "USA",
            },
        ]
    )

    run_um_collection._sync_um_venues_raw(df, skip_validation=False)

    assert ("update", 7) in events
    assert ("eq:venue_id", 7) in events
    assert [row["venue_name"] for row in inserted] == ["New Room"]
    assert [row["venue_id"] for row in inserted] == [42]


def test_sync_um_shows_updates_existing_and_inserts_new(monkeypatch):
    events: list[tuple[str, object]] = []

    class _TableStub:
        def update(self, record):
            events.append(("update", record["show_id"]))
            return self

        def eq(self, column, value):
            events.append((f"eq:{column}", value))
            return self

        def execute(self):
            events.append(("execute", None))
            return None

    class _ClientStub:
        def table(self, table_name):
            events.append(("table", table_name))
            return _TableStub()

    inserted: list[dict[str, object]] = []
    monkeypatch.setattr(run_um_collection, "get_supabase_client", lambda: _ClientStub())
    monkeypatch.setattr(
        run_um_collection,
        "prepare_dataframe_for_upsert",
        lambda _table, df, **_kwargs: df.drop(columns=["_is_existing"]),
    )
    monkeypatch.setattr(
        run_um_collection,
        "fetch_rows_by_column_values",
        lambda *_args, **_kwargs: [
            {"show_id": 9, "source_url": "https://example.com/existing"}
        ],
    )
    monkeypatch.setattr(run_um_collection, "_next_numeric_id", lambda *_args: 50)
    monkeypatch.setattr(
        run_um_collection,
        "bulk_insert_dataframe",
        lambda _table, df: inserted.extend(df.to_dict(orient="records")),
    )

    df = pd.DataFrame(
        [
            {
                "source_url": "https://example.com/existing",
                "show_date": "2026-01-01",
            },
            {"source_url": "https://example.com/new", "show_date": "2026-01-02"},
        ]
    )

    run_um_collection._sync_um_shows_raw(df, skip_validation=False)

    assert ("update", 9) in events
    assert ("eq:show_id", 9) in events
    assert [row["source_url"] for row in inserted] == ["https://example.com/new"]
    assert [row["show_id"] for row in inserted] == [50]
