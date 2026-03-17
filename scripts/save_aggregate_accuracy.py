"""
Unified script to compute and save aggregate accuracy for a given model.

This script replaces `save_notebook_accuracy.py` and `save_ckplus_accuracy.py`.

Crucially, it improves efficiency by calculating aggregate metrics from the
`accuracy_per_show` table, which is populated by the `run_backtest.py` script.
This avoids re-running predictions.

Usage:
  # Calculate and save aggregate accuracy for the Goose Notebook model
  uv run python scripts/save_aggregate_accuracy.py --band goose --model notebook --shows 100
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import timezone

import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.models.accuracy import aggregate_metrics


def save_aggregate_accuracy(band: str, model: str, shows: int) -> None:
    """Fetch per-show metrics and save an aggregate accuracy summary."""
    log_prefix = f"[{band.upper()}/{model.upper()}]"

    client = get_supabase_client()
    model_version = f"{model}_v1"

    print(f"{log_prefix} Fetching last {shows} per-show accuracy records...")

    # 1. Fetch per-show accuracy data
    response = (
        client.table("accuracy_per_show")
        .select("*")
        .eq("band", band)
        .eq("model_version", model_version)
        .order("show_date", desc=True)
        .limit(shows)
        .execute()
    )

    if not response.data:
        print(f"{log_prefix} No per-show accuracy data found. Aborting.")
        return

    per_show_df = pd.DataFrame(response.data)
    print(f"{log_prefix} Found {len(per_show_df)} records to aggregate.")

    # 2. Aggregate metrics for each K
    window_start = per_show_df["show_date"].min()
    window_end = per_show_df["show_date"].max()

    record = {
        "band": band,
        "model_version": model_version,
        "window_start": window_start,
        "window_end": window_end,
        "num_shows": len(per_show_df),
        "evaluated_at": pd.Timestamp.now(tz=timezone.utc).isoformat(),
    }

    for k in [10, 25, 50]:
        # Extract the per-show metrics for this k from the DataFrame
        per_k_metrics = (
            per_show_df[
                [
                    f"k{k}_hit",
                    f"k{k}_matches",
                    f"k{k}_precision",
                    f"k{k}_recall",
                    f"k{k}_f1",
                ]
            ]
            .rename(
                columns={
                    f"k{k}_hit": "hit",
                    f"k{k}_matches": "matches",
                    f"k{k}_precision": "precision",
                    f"k{k}_recall": "recall",
                    f"k{k}_f1": "f1",
                }
            )
            .to_dict("records")
        )

        agg = aggregate_metrics(per_k_metrics, k)
        record[f"k{k}_hit_rate"] = agg.hit_rate
        record[f"k{k}_avg_matches"] = agg.avg_matches
        record[f"k{k}_precision"] = agg.precision
        record[f"k{k}_recall"] = agg.recall
        record[f"k{k}_f1"] = agg.f1

    # 3. Upsert the aggregated record
    # Use correct table naming convention based on what exists in database
    table_mapping = {"notebook": "notebook_accuracy", "ckplus": "accuracy_ckplus"}
    table_name = table_mapping.get(model, f"accuracy_{model}")
    print(f"{log_prefix} Saving aggregate accuracy summary to {table_name}...")

    try:
        client.table(table_name).upsert(
            record, on_conflict="band,model_version,window_start,window_end"
        ).execute()
        print(f"{log_prefix} Successfully saved aggregate accuracy.")

        # Print summary for verification
        print(
            f"{log_prefix} Summary: {record['num_shows']} shows from {record['window_start']} to {record['window_end']}"
        )
        for k in [10, 25, 50]:
            print(
                f"{log_prefix} K={k}: hit_rate={record[f'k{k}_hit_rate']:.3f} precision={record[f'k{k}_precision']:.3f} recall={record[f'k{k}_recall']:.3f}"
            )

    except Exception as e:
        print(f"{log_prefix} Error saving to {table_name}: {e}")
        print(f"{log_prefix} Record data: {record}")
        raise


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Save aggregate model accuracy from per-show backtest results."
    )
    parser.add_argument(
        "--band",
        type=str,
        required=True,
        choices=["goose", "eggy", "phish", "wsp", "billy", "um"],
        help="The band to process.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=["notebook", "ckplus"],
        help="The model to aggregate accuracy for.",
    )
    parser.add_argument(
        "--shows",
        type=int,
        default=100,
        help="Number of recent shows to average over.",
    )
    args = parser.parse_args()

    save_aggregate_accuracy(band=args.band, model=args.model, shows=args.shows)


if __name__ == "__main__":
    main()
