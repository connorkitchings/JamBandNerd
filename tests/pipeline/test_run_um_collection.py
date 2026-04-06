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
