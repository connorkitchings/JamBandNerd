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
