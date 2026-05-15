from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from jambandnerd.db import operations


def test_prepare_dataframe_for_upsert_fails_on_missing_required_columns():
    df = pd.DataFrame([{"song_name": "Arcadia"}])

    with pytest.raises(RuntimeError, match="missing expected columns: set_number"):
        operations.prepare_dataframe_for_upsert(
            "goose_setlists_raw",
            df,
            required_columns=["set_number"],
            skip_validation=True,
        )


def test_prepare_dataframe_for_upsert_fails_on_nullable_violations(monkeypatch):
    schema = [
        {"column_name": "source_hash", "data_type": "text", "is_nullable": "NO"},
        {"column_name": "song_name", "data_type": "text", "is_nullable": "NO"},
    ]
    monkeypatch.setattr(
        operations, "get_table_schema", lambda *_args, **_kwargs: schema
    )

    df = pd.DataFrame([{"source_hash": None, "song_name": "Arcadia"}])

    with pytest.raises(RuntimeError, match="nullable violations: \\['source_hash'\\]"):
        operations.prepare_dataframe_for_upsert("goose_setlists_raw", df)


def test_prepare_dataframe_for_upsert_drops_extra_columns(monkeypatch):
    schema = [
        {"column_name": "song_name", "data_type": "text", "is_nullable": "NO"},
        {"column_name": "song_slug", "data_type": "text", "is_nullable": "NO"},
    ]
    monkeypatch.setattr(
        operations, "get_table_schema", lambda *_args, **_kwargs: schema
    )

    df = pd.DataFrame(
        [
            {
                "song_name": "In The Kitchen",
                "song_slug": "in-the-kitchen",
                "avg_show_gap": 5.5,
            }
        ]
    )

    prepared = operations.prepare_dataframe_for_upsert("um_songs_raw", df)

    assert list(prepared.columns) == ["song_name", "song_slug"]


def test_validate_and_upsert_dataframe_does_not_send_extra_columns(monkeypatch):
    schema = [
        {"column_name": "song_name", "data_type": "text", "is_nullable": "NO"},
        {"column_name": "song_slug", "data_type": "text", "is_nullable": "NO"},
    ]
    monkeypatch.setattr(
        operations, "get_table_schema", lambda *_args, **_kwargs: schema
    )

    captured: dict[str, pd.DataFrame] = {}
    monkeypatch.setattr(
        operations,
        "upsert_dataframe",
        lambda table_name, df, conflict_columns, chunk_size=500: captured.update(  # noqa: ARG005
            {"df": df.copy()}
        ),
    )

    df = pd.DataFrame(
        [
            {
                "song_name": "In The Kitchen",
                "song_slug": "in-the-kitchen",
                "avg_show_gap": 5.5,
            }
        ]
    )

    operations.validate_and_upsert_dataframe(
        "um_songs_raw",
        df,
        conflict_columns=["song_name"],
    )

    assert list(captured["df"].columns) == ["song_name", "song_slug"]


def test_dedupe_dataframe_on_conflict_removes_duplicate_rows():
    df = pd.DataFrame(
        [
            {"source_url": "https://example.com/show", "show_date": "2026-04-01"},
            {"source_url": "https://example.com/show", "show_date": "2026-04-02"},
        ]
    )

    deduped = operations.dedupe_dataframe_on_conflict(
        df,
        conflict_columns=["source_url"],
        table_name="um_shows_raw",
    )

    assert len(deduped) == 1
    assert deduped.iloc[0]["show_date"] == "2026-04-02"


def test_upsert_dataframe_preserves_structured_json_payload(monkeypatch):
    client = MagicMock()
    table = MagicMock()
    client.table.return_value = table
    table.upsert.return_value = table
    table.execute.return_value = MagicMock()
    monkeypatch.setattr(operations, "get_supabase_client", lambda: client)

    df = pd.DataFrame(
        [
            {
                "band": "goose",
                "reference_date": "2026-03-20",
                "predictions": [{"rank": 1, "song_name": "Arcadia"}],
            }
        ]
    )

    operations.upsert_dataframe(
        "predictions",
        df,
        conflict_columns=["band", "reference_date"],
    )

    payload = table.upsert.call_args.args[0]
    assert payload[0]["predictions"] == [{"rank": 1, "song_name": "Arcadia"}]


def test_replace_prediction_projection_rewrites_rows(monkeypatch):
    events: list[tuple[str, object]] = []

    class _QueryStub:
        def __init__(self, table_name: str):
            self.table_name = table_name

        def select(self, *columns):
            events.append(("select", self.table_name))
            return self

        def delete(self):
            events.append(("delete", self.table_name))
            return self

        def eq(self, column: str, value: object):
            events.append((f"filter:{column}", value))
            return self

        def lt(self, column: str, value: object):
            events.append((f"lt:{column}", value))
            return self

        def neq(self, column: str, value: object):
            events.append((f"neq:{column}", value))
            return self

        def order(self, column: str, *, desc: bool = False):
            return self

        def limit(self, n: int):
            return self

        def execute(self):
            events.append(("execute", self.table_name))
            return MagicMock(data=[])

    class _ClientStub:
        def table(self, name: str):
            return _QueryStub(name)

    monkeypatch.setattr(operations, "get_supabase_client", lambda: _ClientStub())
    inserted: list[dict[str, object]] = []
    monkeypatch.setattr(
        operations,
        "bulk_insert_dataframe",
        lambda table_name, df, chunk_size=500: inserted.extend(  # noqa: ARG005
            df.to_dict(orient="records")
        ),
    )

    operations.replace_prediction_projection(
        band="goose",
        model_slug="notebook",
        model_version="notebook_v1",
        reference_date="2026-03-20",
        predicted_at="2026-03-20T12:00:00+00:00",
        predictions=[
            {"rank": 1, "song_name": "Arcadia", "plays_past_year": 7},
            {"rank": 2, "song_name": "Madhuvan", "plays_past_year": 6},
        ],
    )

    assert ("delete", "prediction_songs") in events
    assert ("filter:band", "goose") in events
    assert ("filter:model_version", "notebook_v1") in events
    assert ("filter:reference_date", "2026-03-20") in events
    assert inserted == [
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "reference_date": "2026-03-20",
            "predicted_at": "2026-03-20T12:00:00+00:00",
            "rank": 1,
            "song_name": "Arcadia",
            "top_k": 2,
            "prediction_payload": {
                "rank": 1,
                "song_name": "Arcadia",
                "plays_past_year": 7,
            },
        },
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "reference_date": "2026-03-20",
            "predicted_at": "2026-03-20T12:00:00+00:00",
            "rank": 2,
            "song_name": "Madhuvan",
            "top_k": 2,
            "prediction_payload": {
                "rank": 2,
                "song_name": "Madhuvan",
                "plays_past_year": 6,
            },
        },
    ]


def test_cleanup_stale_prediction_songs_uses_predicted_at_not_reference_date(
    monkeypatch,
):
    deleted_refs: list[str] = []

    class _ResponseStub:
        def __init__(self, data):
            self.data = data

    class _QueryStub:
        def __init__(self, rows):
            self._rows = rows
            self._filters: list[tuple[str, object]] = []
            self._mode = "select"
            self._orders: list[tuple[str, bool]] = []

        def select(self, *_args, **_kwargs):
            self._mode = "select"
            return self

        def delete(self):
            self._mode = "delete"
            return self

        def eq(self, column, value):
            self._filters.append((column, value))
            return self

        def order(self, *_args, **_kwargs):
            column = _args[0]
            desc = _kwargs.get("desc", False)
            self._orders.append((column, desc))
            return self

        def limit(self, *_args, **_kwargs):
            return self

        def execute(self):
            rows = list(self._rows)
            for column, value in self._filters:
                rows = [row for row in rows if row.get(column) == value]
            for column, desc in reversed(self._orders):
                rows.sort(key=lambda row: row.get(column), reverse=desc)
            if self._mode == "delete":
                if rows:
                    deleted_refs.append(rows[0]["reference_date"])
                return _ResponseStub(rows)
            return _ResponseStub(rows)

    class _ClientStub:
        def __init__(self, rows):
            self._rows = rows

        def table(self, _name):
            return _QueryStub(self._rows)

    rows = [
        {
            "band": "goose",
            "model_version": "notebook_v1",
            "reference_date": "2026-04-16",
            "predicted_at": "2026-03-20T12:00:00+00:00",
        },
        {
            "band": "goose",
            "model_version": "notebook_v1",
            "reference_date": "2026-01-31",
            "predicted_at": "2026-04-06T19:24:08+00:00",
        },
    ]
    monkeypatch.setattr(operations, "get_supabase_client", lambda: _ClientStub(rows))

    operations._cleanup_stale_prediction_songs(
        band="goose",
        model_version="notebook_v1",
        max_age_days=7,
    )

    assert deleted_refs == ["2026-04-16"]


def test_fetch_latest_prediction_songs_returns_ranked_rows(monkeypatch):
    class _ResponseStub:
        def __init__(self, data):
            self.data = data

    class _QueryStub:
        def __init__(self, rows):
            self._rows = rows
            self._filters = []
            self._orders = []
            self._limit = None

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, column, value):
            self._filters.append((column, value))
            return self

        def order(self, column, desc=False):
            self._orders.append((column, desc))
            return self

        def limit(self, value):
            self._limit = value
            return self

        def execute(self):
            rows = list(self._rows)
            for column, value in self._filters:
                rows = [row for row in rows if row.get(column) == value]
            for column, desc in reversed(self._orders):
                rows.sort(key=lambda row: row.get(column), reverse=desc)
            if self._limit is not None:
                rows = rows[: self._limit]
            return _ResponseStub(rows)

    class _ClientStub:
        def __init__(self, rows):
            self._rows = rows

        def table(self, _name: str):
            return _QueryStub(self._rows)

    rows = [
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "reference_date": "2026-03-10",
            "predicted_at": "2026-03-10T12:00:00+00:00",
            "rank": 1,
            "song_name": "Old Song",
        },
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "reference_date": "2026-03-20",
            "predicted_at": "2026-03-20T12:00:00+00:00",
            "rank": 2,
            "song_name": "Song Two",
        },
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "reference_date": "2026-03-20",
            "predicted_at": "2026-03-20T12:00:00+00:00",
            "rank": 1,
            "song_name": "Song One",
        },
    ]
    monkeypatch.setattr(operations, "get_supabase_client", lambda: _ClientStub(rows))

    latest = operations.fetch_latest_prediction_songs(
        band="goose", model_slug="notebook"
    )

    assert [row["song_name"] for row in latest] == ["Song One", "Song Two"]


def test_fetch_prediction_songs_for_date_returns_exact_reference_date(monkeypatch):
    class _ResponseStub:
        def __init__(self, data):
            self.data = data

    class _QueryStub:
        def __init__(self, rows):
            self._rows = rows
            self._filters = []
            self._orders = []
            self._limit = None

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, column, value):
            self._filters.append((column, value))
            return self

        def order(self, column, desc=False):
            self._orders.append((column, desc))
            return self

        def limit(self, value):
            self._limit = value
            return self

        def execute(self):
            rows = list(self._rows)
            for column, value in self._filters:
                rows = [row for row in rows if row.get(column) == value]
            for column, desc in reversed(self._orders):
                rows.sort(key=lambda row: row.get(column), reverse=desc)
            if self._limit is not None:
                rows = rows[: self._limit]
            return _ResponseStub(rows)

    class _ClientStub:
        def __init__(self, rows):
            self._rows = rows

        def table(self, _name: str):
            return _QueryStub(self._rows)

    rows = [
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "reference_date": "2026-03-20",
            "rank": 2,
            "song_name": "Song Two",
        },
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "reference_date": "2026-03-20",
            "rank": 1,
            "song_name": "Song One",
        },
        {
            "band": "goose",
            "model_slug": "notebook",
            "model_version": "notebook_v1",
            "reference_date": "2026-03-21",
            "rank": 1,
            "song_name": "Wrong Date",
        },
    ]
    monkeypatch.setattr(operations, "get_supabase_client", lambda: _ClientStub(rows))

    matched = operations.fetch_prediction_songs_for_date(
        band="goose",
        model_slug="notebook",
        reference_date="2026-03-20",
    )

    assert [row["song_name"] for row in matched] == ["Song One", "Song Two"]


def test_fetch_setlist_prediction_songs_for_date_uses_matching_run(monkeypatch):
    class _ResponseStub:
        def __init__(self, data):
            self.data = data

    class _QueryStub:
        def __init__(self, rows):
            self._rows = rows
            self._filters = []
            self._orders = []
            self._limit = None

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, column, value):
            self._filters.append((column, value))
            return self

        def order(self, column, desc=False):
            self._orders.append((column, desc))
            return self

        def limit(self, value):
            self._limit = value
            return self

        def execute(self):
            rows = list(self._rows)
            for column, value in self._filters:
                rows = [row for row in rows if row.get(column) == value]
            for column, desc in reversed(self._orders):
                rows.sort(key=lambda row: row.get(column), reverse=desc)
            if self._limit is not None:
                rows = rows[: self._limit]
            return _ResponseStub(rows)

    class _ClientStub:
        def __init__(self, tables):
            self._tables = tables

        def table(self, name: str):
            return _QueryStub(self._tables[name])

    tables = {
        "setlist_predictions": [
            {
                "band": "goose",
                "model_version": "goose_v1",
                "reference_date": "2026-03-20",
                "target_show_key": "show-1",
                "generated_at": "2026-03-20T12:00:00+00:00",
            },
            {
                "band": "goose",
                "model_version": "goose_v1",
                "reference_date": "2026-03-21",
                "target_show_key": "show-2",
                "generated_at": "2026-03-21T12:00:00+00:00",
            },
        ],
        "setlist_prediction_songs": [
            {
                "band": "goose",
                "model_version": "goose_v1",
                "target_show_key": "show-1",
                "rank": 2,
                "song_name": "Song Two",
            },
            {
                "band": "goose",
                "model_version": "goose_v1",
                "target_show_key": "show-1",
                "rank": 1,
                "song_name": "Song One",
            },
            {
                "band": "goose",
                "model_version": "goose_v1",
                "target_show_key": "show-2",
                "rank": 1,
                "song_name": "Wrong Date",
            },
        ],
    }
    monkeypatch.setattr(operations, "get_supabase_client", lambda: _ClientStub(tables))

    matched = operations.fetch_setlist_prediction_songs_for_date(
        band="goose",
        reference_date="2026-03-20",
    )

    assert [row["song_name"] for row in matched] == ["Song One", "Song Two"]


def test_replace_next_show_prediction_projection_rejects_empty_predictions(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(operations, "get_supabase_client", lambda: client)

    with pytest.raises(RuntimeError, match="Refusing to replace"):
        operations.replace_next_show_prediction_projection(
            band="goose",
            model_slug="notebook",
            model_version="notebook_v1",
            target_show_key="show-1",
            target_show_date="2026-04-25",
            reference_date="2026-04-25",
            generated_at="2026-04-24T12:00:00+00:00",
            predictions=[],
        )

    client.table.assert_not_called()


def test_replace_setlist_prediction_projection_writes_show_metadata(monkeypatch):
    captured: dict[str, pd.DataFrame] = {}
    client = MagicMock()
    monkeypatch.setattr(operations, "get_supabase_client", lambda: client)
    monkeypatch.setattr(
        operations,
        "bulk_insert_dataframe",
        lambda table_name, df: captured.update({"table": table_name, "df": df}),
    )

    operations.replace_setlist_prediction_projection(
        band="goose",
        model_version="goose_fast_rank_v1",
        target_show_key="show-1",
        target_show_date="2026-04-25",
        reference_date="2026-04-24",
        generated_at="2026-04-24T12:00:00+00:00",
        predictions=[{"rank": 1, "song_name": "Arcadia", "probability": 0.42}],
        prediction_run_id=123,
    )

    row = captured["df"].iloc[0].to_dict()
    assert captured["table"] == "setlist_prediction_songs"
    assert row["prediction_run_id"] == 123
    assert row["target_show_date"] == "2026-04-25"
    assert row["reference_date"] == "2026-04-24"
    assert row["generated_at"] == "2026-04-24T12:00:00+00:00"
    assert row["top_k"] == 1


def test_replace_setlist_prediction_projection_filters_missing_legacy_columns(
    monkeypatch,
):
    captured: dict[str, pd.DataFrame] = {}
    client = MagicMock()
    monkeypatch.setattr(operations, "get_supabase_client", lambda: client)
    monkeypatch.setattr(
        operations,
        "get_table_schema",
        lambda table_name: [
            {"column_name": "prediction_run_id"},
            {"column_name": "band"},
            {"column_name": "model_version"},
            {"column_name": "target_show_key"},
            {"column_name": "rank"},
            {"column_name": "song_name"},
            {"column_name": "score"},
            {"column_name": "prediction_payload"},
        ],
    )
    monkeypatch.setattr(
        operations,
        "bulk_insert_dataframe",
        lambda table_name, df: captured.update({"table": table_name, "df": df}),
    )

    operations.replace_setlist_prediction_projection(
        band="goose",
        model_version="goose_fast_rank_v1",
        target_show_key="show-1",
        target_show_date="2026-04-25",
        reference_date="2026-04-24",
        generated_at="2026-04-24T12:00:00+00:00",
        predictions=[{"rank": 1, "song_name": "Arcadia", "probability": 0.42}],
        prediction_run_id=123,
    )

    row = captured["df"].iloc[0].to_dict()
    assert captured["table"] == "setlist_prediction_songs"
    assert row["prediction_run_id"] == 123
    assert row["target_show_key"] == "show-1"
    assert "target_show_date" not in row
    assert "reference_date" not in row
    assert "generated_at" not in row
    assert "top_k" not in row


def test_upsert_setlist_accuracy_dataframe_filters_missing_legacy_columns(
    monkeypatch,
):
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        operations,
        "get_table_schema",
        lambda table_name: [
            {"column_name": "band"},
            {"column_name": "model_version"},
            {"column_name": "show_id"},
            {"column_name": "target_show_key"},
            {"column_name": "show_date"},
            {"column_name": "reference_date"},
            {"column_name": "prediction_run_id"},
            {"column_name": "actual_song_count"},
            {"column_name": "evaluated_at"},
        ],
    )
    monkeypatch.setattr(
        operations,
        "upsert_dataframe",
        lambda table_name, df, conflict_columns: captured.update(
            {
                "table": table_name,
                "df": df,
                "conflict_columns": conflict_columns,
            }
        ),
    )
    df = pd.DataFrame(
        [
            {
                "band": "goose",
                "model_version": "goose_v1",
                "show_id": "show-1",
                "target_show_key": "show-1",
                "show_date": "2026-04-25",
                "target_show_date": "2026-04-25",
                "reference_date": "2026-04-24",
                "prediction_run_id": 123,
                "actual_song_count": 12,
                "evaluated_at": "2026-04-24T12:00:00+00:00",
            }
        ]
    )

    operations.upsert_setlist_accuracy_dataframe(df)

    written = captured["df"]
    assert captured["table"] == "setlist_accuracy"
    assert captured["conflict_columns"] == ["band", "model_version", "target_show_key"]
    assert "target_show_date" not in written.columns
    assert written.iloc[0]["show_date"] == "2026-04-25"


def test_prune_completed_show_corpus_rejects_empty_retained_keys(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr(operations, "get_supabase_client", lambda: client)

    with pytest.raises(RuntimeError, match="empty retained key set"):
        operations.prune_completed_show_corpus(
            band="goose",
            model_slug="notebook",
            model_version="notebook_v1",
            retained_target_show_keys=[],
        )

    client.table.assert_not_called()


def test_upsert_historical_prediction_run_returns_inserted_id(monkeypatch):
    class _ResponseStub:
        def __init__(self, data):
            self.data = data

    class _QueryStub:
        def __init__(self):
            self.upsert_payload = None
            self.upsert_conflict = None

        def upsert(self, payload, on_conflict=None):
            self.upsert_payload = payload
            self.upsert_conflict = on_conflict
            return self

        def execute(self):
            return _ResponseStub([{"id": 42}])

    class _ClientStub:
        def __init__(self):
            self.query = _QueryStub()

        def table(self, _name: str):
            return self.query

    client = _ClientStub()
    monkeypatch.setattr(operations, "get_supabase_client", lambda: client)

    run_id = operations.upsert_historical_prediction_run(
        band="goose",
        model_slug="notebook",
        model_version="notebook_v1",
        reference_date="2026-03-20",
        target_show_id="goose-show-1",
        target_show_date="2026-03-21",
        generated_at="2026-03-20T12:00:00+00:00",
        predictions=[{"rank": 1, "song_name": "Arcadia"}],
        actual_songs=["Arcadia", "Madhuvan"],
    )

    assert run_id == 42
    assert client.query.upsert_conflict == (
        "band,model_slug,model_version,reference_date,target_show_id"
    )
    assert client.query.upsert_payload["top_k"] == 1
    assert client.query.upsert_payload["actual_song_count"] == 2


def test_upsert_historical_prediction_run_falls_back_to_lookup(monkeypatch):
    class _ResponseStub:
        def __init__(self, data):
            self.data = data

    class _QueryStub:
        def __init__(self, rows):
            self._rows = rows
            self._filters = []
            self._mode = "upsert"

        def upsert(self, payload, on_conflict=None):  # noqa: ARG002
            self._mode = "upsert"
            return self

        def select(self, *_args, **_kwargs):
            self._mode = "select"
            return self

        def eq(self, column, value):
            self._filters.append((column, value))
            return self

        def limit(self, _value):
            return self

        def execute(self):
            if self._mode == "upsert":
                return _ResponseStub([])
            rows = list(self._rows)
            for column, value in self._filters:
                rows = [row for row in rows if row.get(column) == value]
            return _ResponseStub(rows[:1])

    class _ClientStub:
        def __init__(self, rows):
            self.rows = rows

        def table(self, _name: str):
            return _QueryStub(self.rows)

    monkeypatch.setattr(
        operations,
        "get_supabase_client",
        lambda: _ClientStub(
            [
                {
                    "id": 77,
                    "band": "goose",
                    "model_slug": "notebook",
                    "model_version": "notebook_v1",
                    "reference_date": "2026-03-20",
                    "target_show_id": "goose-show-1",
                }
            ]
        ),
    )

    run_id = operations.upsert_historical_prediction_run(
        band="goose",
        model_slug="notebook",
        model_version="notebook_v1",
        reference_date="2026-03-20",
        target_show_id="goose-show-1",
        target_show_date="2026-03-21",
        generated_at="2026-03-20T12:00:00+00:00",
        predictions=[{"rank": 1, "song_name": "Arcadia"}],
        actual_songs=["Arcadia", "Madhuvan"],
    )

    assert run_id == 77
