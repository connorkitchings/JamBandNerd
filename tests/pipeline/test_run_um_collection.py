from __future__ import annotations

import pandas as pd

from scripts import run_um_collection


def test_sync_um_shows_matches_old_stored_url_to_new_scraped_url(monkeypatch):
    old = "https://allthings.umphreys.com/2026-05-01"
    new = "https://allthings.umphreys.com/setlists/2026-05-01"
    updated, inserted = [], []

    monkeypatch.setattr(
        run_um_collection,
        "fetch_rows_by_column_values",
        lambda *a, **k: [{"show_id": 7, "source_url": old}],
    )
    monkeypatch.setattr(run_um_collection, "_next_numeric_id", lambda *a: 100)
    monkeypatch.setattr(
        run_um_collection, "prepare_dataframe_for_upsert", lambda t, df, **k: df
    )

    class _Client:
        def table(self, _):
            return self

        def update(self, record):
            updated.append(record["show_id"])
            return self

        def eq(self, *a):
            return self

        def execute(self):
            return None

    monkeypatch.setattr(run_um_collection, "get_supabase_client", lambda: _Client())
    monkeypatch.setattr(
        run_um_collection,
        "bulk_insert_dataframe",
        lambda table, df: inserted.extend(df["show_id"]),
    )

    df = pd.DataFrame(
        [
            {"source_url": new, "show_date": "2026-05-01"},
            {"source_url": new + "-2", "show_date": "2026-05-01"},
        ]
    )
    run_um_collection._sync_um_shows_raw(df, skip_validation=True)

    assert updated == [7]
    assert inserted == [100]


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


def _run_sync_with_existing(monkeypatch, existing_rows, scraped_rows):
    """Run _sync_um_shows_raw against stubbed rows; return (updated, inserted ids)."""
    updated: list[int] = []
    inserted: list[int] = []

    def fake_fetch(_table, *, filter_column, values, **_kwargs):
        values = set(values)
        return [r for r in existing_rows if r[filter_column] in values]

    class _Client:
        def table(self, _):
            return self

        def update(self, record):
            updated.append(record["show_id"])
            return self

        def eq(self, *_a):
            return self

        def execute(self):
            return None

    monkeypatch.setattr(run_um_collection, "fetch_rows_by_column_values", fake_fetch)
    monkeypatch.setattr(run_um_collection, "_next_numeric_id", lambda *a: 100)
    monkeypatch.setattr(
        run_um_collection, "prepare_dataframe_for_upsert", lambda t, df, **k: df
    )
    monkeypatch.setattr(run_um_collection, "get_supabase_client", lambda: _Client())
    monkeypatch.setattr(
        run_um_collection,
        "bulk_insert_dataframe",
        lambda table, df: inserted.extend(df["show_id"]),
    )
    run_um_collection._sync_um_shows_raw(
        pd.DataFrame(scraped_rows), skip_validation=True
    )
    return updated, inserted


def _show(url, date="2026-08-21", venue="Wooly's"):
    return {"source_url": url, "show_date": date, "venue_name": venue}


def test_sync_um_shows_reuses_id_when_url_changes_but_date_and_venue_match(
    monkeypatch,
):
    existing = [
        {
            "show_id": 7,
            "source_url": "https://allthings.umphreys.com/2026-08-21-other-slug",
            "show_date": "2026-08-21",
            "venue_name": "Wooly's",
        }
    ]
    updated, inserted = _run_sync_with_existing(
        monkeypatch,
        existing,
        [_show("https://allthings.umphreys.com/setlists/2026-08-21-new-slug")],
    )
    assert updated == [7]
    assert inserted == []


def test_sync_um_shows_new_date_creates_new_id(monkeypatch):
    existing = [
        {
            "show_id": 7,
            "source_url": "https://example.com/a",
            "show_date": "2026-08-21",
            "venue_name": "Wooly's",
        }
    ]
    updated, inserted = _run_sync_with_existing(
        monkeypatch, existing, [_show("https://example.com/b", date="2026-08-22")]
    )
    assert updated == []
    assert inserted == [100]


def test_sync_um_shows_keeps_same_day_same_venue_second_show_separate(monkeypatch):
    base = "https://allthings.umphreys.com/2026-08-21-woolys"
    existing = [
        {
            "show_id": 7,
            "source_url": base,
            "show_date": "2026-08-21",
            "venue_name": "Wooly's",
        }
    ]
    updated, inserted = _run_sync_with_existing(
        monkeypatch, existing, [_show(base), _show(base + "-2")]
    )
    assert updated == [7]
    assert inserted == [100]


def test_sync_um_shows_does_not_merge_dash_two_into_unrelated_row(monkeypatch):
    existing = [
        {
            "show_id": 7,
            "source_url": "https://example.com/2026-08-21-old",
            "show_date": "2026-08-21",
            "venue_name": "Wooly's",
        }
    ]
    updated, inserted = _run_sync_with_existing(
        monkeypatch, existing, [_show("https://example.com/2026-08-21-new-2")]
    )
    assert updated == []
    assert inserted == [100]


def test_sync_um_shows_ambiguous_date_venue_candidates_create_new_row(monkeypatch):
    existing = [
        {
            "show_id": i,
            "source_url": f"https://example.com/old-{i}",
            "show_date": "2026-08-21",
            "venue_name": "Wooly's",
        }
        for i in (7, 8)
    ]
    updated, inserted = _run_sync_with_existing(
        monkeypatch, existing, [_show("https://example.com/new")]
    )
    assert updated == []
    assert inserted == [100]


def test_normalize_um_show_url_collapses_apostrophe_variants():
    base = "https://allthings.umphreys.com/2026-08-21-woolys-des-moines-ia"
    for variant in ("wooly039s", "wooly%27s", "wooly's"):
        url = base.replace("woolys", variant)
        assert run_um_collection.normalize_um_show_url(url) == base
    assert (
        run_um_collection.normalize_um_show_url(
            "https://allthings.umphreys.com/setlists/2026-08-21-woolys"
        )
        == "https://allthings.umphreys.com/2026-08-21-woolys"
    )
