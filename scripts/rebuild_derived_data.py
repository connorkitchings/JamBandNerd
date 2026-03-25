#!/usr/bin/env python3
"""Rebuild derived prediction and accuracy outputs for one or more bands."""

from __future__ import annotations

import argparse
import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.generate_predictions import generate_predictions
from scripts.run_backtest import run_backtest
from scripts.save_aggregate_accuracy import save_aggregate_accuracy
from scripts.validate_accuracy_tables import validate_accuracy
from scripts.validate_prediction_tables import validate_predictions
from src.jambandnerd.config import (
    ACCURACY_TABLES,
    HISTORICAL_PREDICTION_RUNS_TABLE,
    MODEL_VERSIONS,
    PREDICTION_SONGS_TABLE,
    PREDICTION_TABLES,
    SUPPORTED_BANDS,
)
from src.jambandnerd.db.connection import get_supabase_client

MODELS: tuple[str, ...] = ("notebook", "ckplus")


def _selected_bands(band: str) -> list[str]:
    return list(SUPPORTED_BANDS) if band == "all" else [band]


def clear_model_outputs(
    *,
    band: str,
    model: str,
    clear_predictions: bool = True,
    clear_accuracy: bool = True,
) -> None:
    """Delete derived outputs for one band/model pair."""
    client = get_supabase_client()
    model_version = MODEL_VERSIONS[model]

    if clear_predictions:
        prediction_table = PREDICTION_TABLES[model]
        print(
            f"[{band.upper()}/{model.upper()}] Clearing existing predictions from {prediction_table}..."
        )
        (
            client.table(prediction_table)
            .delete()
            .eq("band", band)
            .eq("model_version", model_version)
            .execute()
        )
        (
            client.table(PREDICTION_SONGS_TABLE)
            .delete()
            .eq("band", band)
            .eq("model_version", model_version)
            .execute()
        )

    if clear_accuracy:
        aggregate_table = ACCURACY_TABLES[model]
        print(f"[{band.upper()}/{model.upper()}] Clearing existing accuracy rows...")
        (
            client.table(HISTORICAL_PREDICTION_RUNS_TABLE)
            .delete()
            .eq("band", band)
            .eq("model_slug", model)
            .eq("model_version", model_version)
            .execute()
        )
        (
            client.table("accuracy_per_show")
            .delete()
            .eq("band", band)
            .eq("model_version", model_version)
            .execute()
        )
        (
            client.table(aggregate_table)
            .delete()
            .eq("band", band)
            .eq("model_version", model_version)
            .execute()
        )


def clear_existing_outputs(
    *,
    bands: list[str],
    clear_predictions: bool = True,
    clear_accuracy: bool = True,
) -> None:
    """Delete existing derived outputs for the selected bands/models."""
    for band in bands:
        for model in MODELS:
            clear_model_outputs(
                band=band,
                model=model,
                clear_predictions=clear_predictions,
                clear_accuracy=clear_accuracy,
            )


def _rebuild_model_outputs(
    *,
    band: str,
    model: str,
    rebuild_predictions: bool,
    rebuild_accuracy: bool,
    clear_existing: bool,
    start: str | None,
    end: str | None,
    recent_shows: int | None,
    aggregate_shows: int,
) -> None:
    """Rebuild derived outputs for one band/model pair with explicit phase logging."""
    log_prefix = f"[{band.upper()}/{model.upper()}]"

    if clear_existing:
        print(
            f"{log_prefix} Pre-clearing selected derived rows immediately before rebuild."
        )
        clear_model_outputs(
            band=band,
            model=model,
            clear_predictions=rebuild_predictions,
            clear_accuracy=rebuild_accuracy,
        )

    if rebuild_predictions:
        print(f"{log_prefix} Phase 1/3: regenerate predictions")
        try:
            generate_predictions(
                band=band,
                model=model,
                date_str=None,
                exclusion_window=3,
            )
        except Exception as exc:
            state = (
                "after clearing existing prediction rows"
                if clear_existing
                else "with existing prediction rows left intact"
            )
            raise RuntimeError(
                f"{log_prefix} Prediction rebuild failed {state}: {exc}"
            ) from exc

    if rebuild_accuracy:
        print(f"{log_prefix} Phase 2/3: rebuild per-show accuracy")
        try:
            run_backtest(
                band=band,
                model=model,
                start=start,
                end=end,
                shows=recent_shows,
                exclusion_window=3,
                all_history=(recent_shows is None and start is None and end is None),
            )
        except Exception as exc:
            state = (
                "after clearing existing accuracy rows"
                if clear_existing
                else "with existing accuracy rows left intact"
            )
            raise RuntimeError(
                f"{log_prefix} Per-show accuracy rebuild failed {state}: {exc}"
            ) from exc

        print(f"{log_prefix} Phase 3/3: rebuild aggregate accuracy")
        try:
            save_aggregate_accuracy(
                band=band,
                model=model,
                shows=aggregate_shows,
            )
        except Exception as exc:
            raise RuntimeError(
                f"{log_prefix} Aggregate accuracy rebuild failed after per-show "
                f"accuracy completed: {exc}"
            ) from exc


def rebuild_band_outputs(
    *,
    band: str,
    rebuild_predictions: bool,
    rebuild_accuracy: bool,
    clear_existing: bool,
    start: str | None,
    end: str | None,
    recent_shows: int | None,
    aggregate_shows: int,
    max_age_hours: int,
) -> None:
    """Rebuild derived outputs for a single band."""
    for model in MODELS:
        _rebuild_model_outputs(
            band=band,
            model=model,
            rebuild_predictions=rebuild_predictions,
            rebuild_accuracy=rebuild_accuracy,
            clear_existing=clear_existing,
            start=start,
            end=end,
            recent_shows=recent_shows,
            aggregate_shows=aggregate_shows,
        )

    if rebuild_predictions:
        failures = validate_predictions(bands=[band], max_age_hours=max_age_hours)
        if failures:
            raise RuntimeError(
                f"Prediction validation failed for {band}: {failures} issue(s)"
            )

    if rebuild_accuracy:
        failures = validate_accuracy(bands=[band], max_age_hours=max_age_hours)
        if failures:
            raise RuntimeError(
                f"Accuracy validation failed for {band}: {failures} issue(s)"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild derived prediction and accuracy outputs."
    )
    parser.add_argument(
        "--band",
        choices=[*SUPPORTED_BANDS, "all"],
        default="all",
        help="Band to rebuild (default: all supported bands).",
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Delete existing prediction and accuracy rows before rebuilding.",
    )
    parser.add_argument(
        "--skip-predictions",
        action="store_true",
        help="Skip prediction regeneration.",
    )
    parser.add_argument(
        "--skip-accuracy",
        action="store_true",
        help="Skip backtest and aggregate accuracy rebuild.",
    )
    parser.add_argument(
        "--start",
        help="Optional backtest start date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end",
        help="Optional backtest end date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--recent-shows",
        type=int,
        help="Limit accuracy rebuild to the last N completed shows.",
    )
    parser.add_argument(
        "--aggregate-shows",
        type=int,
        default=100,
        help="Number of recent per-show rows to use for aggregate accuracy.",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=72,
        help="Prediction freshness threshold for post-rebuild validation.",
    )
    args = parser.parse_args()

    bands = _selected_bands(args.band)
    rebuild_predictions = not args.skip_predictions
    rebuild_accuracy = not args.skip_accuracy

    if not rebuild_predictions and not rebuild_accuracy:
        raise SystemExit("Nothing to do: predictions and accuracy are both skipped")

    for band in bands:
        print("=" * 60)
        print(f"Rebuilding derived outputs for {band.upper()}")
        print("=" * 60)
        rebuild_band_outputs(
            band=band,
            rebuild_predictions=rebuild_predictions,
            rebuild_accuracy=rebuild_accuracy,
            clear_existing=args.clear_existing,
            start=args.start,
            end=args.end,
            recent_shows=args.recent_shows,
            aggregate_shows=args.aggregate_shows,
            max_age_hours=args.max_age_hours,
        )


if __name__ == "__main__":
    main()
