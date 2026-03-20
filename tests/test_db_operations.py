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
