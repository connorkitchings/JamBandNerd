"""Run Goose transformations: compute show indices, gaps, and past-year aggregation.

This script fetches raw Goose shows and setlists from Supabase, computes the show index,
per-song current gaps, and the past-year aggregations required by the notebook model.
It prints a concise preview for validation.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

import pandas as pd

# Add the project root to the Python path (align with collection script pattern)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client  # noqa: E402
from src.jambandnerd.transformations.gaps import (  # noqa: E402
    aggregate_past_year_for_notebook,
)


def _fetch_table(table: str, select: str = "*") -> List[Dict[str, Any]]:
    client = get_supabase_client()
    res = client.table(table).select(select).execute()
    return res.data or []


def main() -> None:
    print("Loading Goose raw tables from Supabase...")
    shows_rows = _fetch_table("goose_shows_raw")
    setlists_rows = _fetch_table("goose_setlists_raw")
    shows_df = pd.DataFrame(shows_rows)
    setlists_df = pd.DataFrame(setlists_rows)
    print(f"Loaded shows={len(shows_df)}, setlists={len(setlists_df)}")

    if shows_df.empty or setlists_df.empty:
        print("Insufficient data to compute features.")
        return

    # Minimal columns check
    need_show_cols = {"show_id", "show_date"}
    need_set_cols = {"show_id", "song_name"}
    if not need_show_cols.issubset(shows_df.columns) or not need_set_cols.issubset(
        setlists_df.columns
    ):
        print("Missing required columns in raw tables; cannot compute features.")
        return

    agg = aggregate_past_year_for_notebook(shows_df=shows_df, setlists_df=setlists_df)

    print("Latest show index:", agg.latest_show_index)
    print("Latest show date:", agg.latest_show_date)
    print(
        "Excluded recent songs (played in last 3 shows):",
        len(agg.excluded_recent_songs),
    )

    preview = agg.features.head(25)
    print("Top 25 features preview:")
    print(preview.to_string(index=False))


if __name__ == "__main__":
    main()
