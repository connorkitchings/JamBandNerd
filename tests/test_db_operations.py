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
        "predictions_notebook",
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

        def delete(self):
            events.append(("delete", self.table_name))
            return self

        def eq(self, column: str, value: object):
            events.append((f"filter:{column}", value))
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
