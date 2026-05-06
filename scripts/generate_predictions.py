"""
Unified script to generate predictions for any band and model combination.

This script replaces the individual `generate_<band>_<model>_predictions.py` files
by accepting `--band` and `--model` arguments.

Usage:
  # Generate Notebook predictions for Goose
  uv run python scripts/generate_predictions.py --band goose --model notebook

  # Generate Deal predictions for Phish for a specific date
  uv run python scripts/generate_predictions.py --band phish --model deal --date 2024-08-01

  # Batch two dates into one invocation (shares data download and training):
  uv run python scripts/generate_predictions.py --band goose --model deal \\
    --date default --date 2026-04-19
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from scripts.common import (
    NpEncoder,
    fetch_table,
    prepare_band_data,
    resolve_reference_date,
)
from src.jambandnerd.config.bands import get_repo_supported_bands
from src.jambandnerd.db.operations import (
    replace_prediction_projection,
    upsert_dataframe,
)
from src.jambandnerd.models.registry import (
    build_predictor,
    get_model_definition,
    list_model_slugs,
    serialize_model_predictions,
)
from src.jambandnerd.transformations.gaps import generate_model_data


def generate_predictions_batched(
    band: str,
    model: str,
    date_strs: list[str | None],
    exclusion_window: int | None,
    retrain: bool = False,
    require_output: bool = False,
) -> bool:
    """Generate predictions for one or more reference dates, sharing a single data fetch.

    When a training-capable model (e.g. Deal) is requested with two adjacent dates,
    this avoids a second full training pass.  The model is trained once on the earliest
    reference date; subsequent dates reuse the same weights while each getting their own
    reference-date-scoped feature set via ``generate_model_data``.

    Pass ``None`` (or the sentinel string ``"default"``) to resolve the next upcoming
    show date automatically.
    """
    band = band.lower()
    model = model.lower()
    log_prefix = f"[{band.upper()}/{model.upper()}]"

    # Normalise the "default" sentinel to None so resolve_reference_date uses its
    # standard upcoming-show lookup.
    normalised = [
        None if (d is None or (isinstance(d, str) and d.lower() == "default")) else d
        for d in date_strs
    ]

    # 1. Fetch and prepare data once
    print(f"{log_prefix} Fetching raw data...")
    shows_df = pd.DataFrame(fetch_table(f"{band}_shows_raw"))
    setlists_df = pd.DataFrame(fetch_table(f"{band}_setlists_raw"))

    upcoming_df: pd.DataFrame | None = None
    if band == "um" and None in normalised:
        try:
            upcoming_df = pd.DataFrame(fetch_table("um_upcoming_shows"))
        except Exception as exc:  # pragma: no cover - Supabase connectivity
            print(f"{log_prefix} Warning: could not load upcoming shows ({exc}).")

    if shows_df.empty or setlists_df.empty:
        message = f"{log_prefix} Error: Could not fetch raw data. Aborting."
        print(message)
        if require_output:
            raise RuntimeError(message)
        return False

    shows_df, setlists_df = prepare_band_data(shows_df, setlists_df, band=band)

    # Resolve all reference dates, deduplicate, and sort ascending so training
    # always uses the earliest (most conservative) snapshot.
    resolved: list[date] = [
        resolve_reference_date(d, shows_df, upcoming_df=upcoming_df) for d in normalised
    ]
    reference_dates = sorted(set(resolved))

    # 2. Build predictor once
    model_definition = get_model_definition(model)
    predictor_kwargs: dict[str, Any] = {}
    if model_definition.supports_training and not retrain:
        predictor_kwargs["persist_artifacts"] = False
        print(
            f"{log_prefix} Training-capable model will run with in-memory fresh training; "
            "cached artifacts are disabled for this prediction run."
        )
    predictor = build_predictor(model, band=band, **predictor_kwargs)

    # For training models, train once on the earliest reference date.  Predictions for
    # later dates reuse the same weights; their feature sets are computed independently
    # so the reference_date anti-leakage boundary is still respected for every date.
    train_data = None
    if model_definition.supports_training:
        earliest_date = reference_dates[0]
        train_data = generate_model_data(
            shows_df,
            setlists_df,
            earliest_date,
            exclusion_window=exclusion_window,
            band=band,
        )
        if retrain:
            print(f"{log_prefix} Force retrain enabled, clearing model cache...")
            get_model_path = getattr(predictor, "_get_model_path", None)
            if callable(get_model_path):
                model_path = get_model_path(band)
                if model_path.exists():
                    model_path.unlink()
        else:
            if len(reference_dates) > 1:
                reuse_label = ", ".join(d.isoformat() for d in reference_dates[1:])
                print(
                    f"{log_prefix} Training {model_definition.display_name} once on "
                    f"{earliest_date.isoformat()}; reusing weights for {reuse_label}."
                )
            else:
                print(
                    f"{log_prefix} Training {model_definition.display_name} from the "
                    "current reference-date snapshot."
                )
        predictor.train(train_data)

    # 3. Predict and write for each reference date
    any_success = False
    for reference_date in reference_dates:
        print(
            f"{log_prefix} Generating predictions for reference date: "
            f"{reference_date.isoformat()}"
        )

        # Reuse train_data for the earliest date to avoid a redundant model_data build.
        if train_data is not None and reference_date == reference_dates[0]:
            model_data = train_data
        else:
            model_data = generate_model_data(
                shows_df,
                setlists_df,
                reference_date,
                exclusion_window=exclusion_window,
                band=band,
            )

        prediction_output = predictor.predict(
            model_data=model_data,
            top_k=model_definition.default_top_k,
        )
        if isinstance(prediction_output, tuple):
            predictions, diagnostics = prediction_output
            print(
                f"{log_prefix} --- Model Diagnostics ({reference_date.isoformat()}) ---"
            )
            print(json.dumps(diagnostics, indent=2, cls=NpEncoder))
            print(
                f"{log_prefix} Recently played songs (excluded): "
                f"{model_data.recently_played_songs}"
            )
            print(f"{log_prefix} -------------------------")
        else:
            predictions = prediction_output

        if not predictions:
            message = (
                f"{log_prefix} No predictions were generated for "
                f"{reference_date.isoformat()}."
            )
            print(message)
            if require_output:
                raise RuntimeError(message)
            continue

        # Format and save
        predictions_list = serialize_model_predictions(model, predictions)
        table_name = model_definition.prediction_table
        model_version = model_definition.version
        predicted_at = datetime.now(timezone.utc).isoformat()
        output_row = {
            "band": band,
            "model_slug": model,
            "reference_date": reference_date.isoformat(),
            "model_version": model_version,
            "top_k": len(predictions_list),
            "predictions": json.loads(json.dumps(predictions_list, cls=NpEncoder)),
            "predicted_at": predicted_at,
        }
        output_df = pd.DataFrame([output_row])

        print(
            f"{log_prefix} Generated {len(predictions_list)} predictions for "
            f"{reference_date.isoformat()}. Saving to {table_name}..."
        )
        # Two-step write sequence:
        # 1. Upsert the canonical JSON row in the unified predictions table.
        #    This is the source-of-truth prediction record keyed on
        #    (band, model_slug, reference_date, model_version).
        # 2. Replace the derived prediction_songs projection for the same key.
        #    prediction_songs is a flat per-song table consumed by the website.
        #    The replace call also triggers stale-row cleanup for older
        #    reference_date entries (>30 days, never the most recent).
        upsert_dataframe(
            table_name=table_name,
            df=output_df,
            conflict_columns=["band", "model_slug", "reference_date", "model_version"],
        )
        replace_prediction_projection(
            band=band,
            model_slug=model,
            model_version=model_version,
            reference_date=reference_date.isoformat(),
            predicted_at=predicted_at,
            predictions=output_row["predictions"],
        )
        print(
            f"{log_prefix} Successfully saved predictions for {reference_date.isoformat()}."
        )
        any_success = True

    return any_success


def generate_predictions(
    band: str,
    model: str,
    date_str: str | None,
    exclusion_window: int | None,
    retrain: bool = False,
    require_output: bool = False,
) -> bool:
    """Generate and save predictions for a given band, model, and single reference date.

    Thin wrapper around ``generate_predictions_batched`` for single-date callers.
    """
    return generate_predictions_batched(
        band=band,
        model=model,
        date_strs=[date_str],
        exclusion_window=exclusion_window,
        retrain=retrain,
        require_output=require_output,
    )


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate predictions for a specific band and model."
    )
    parser.add_argument(
        "--band",
        type=str,
        required=True,
        choices=get_repo_supported_bands(),
        help="The band to process.",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=list_model_slugs(),
        help="The model to use for predictions.",
    )
    parser.add_argument(
        "--retrain",
        action="store_true",
        help="Force retrain for training-capable models.",
    )
    parser.add_argument(
        "--date",
        action="append",
        dest="dates",
        metavar="DATE",
        help=(
            "Reference date in YYYY-MM-DD format, or 'default' for the next upcoming "
            "show. May be passed multiple times to batch multiple dates into one "
            "invocation (shares data download and, for training models, training)."
        ),
    )
    parser.add_argument(
        "--exclusion-window",
        type=int,
        default=None,
        help="Number of recent shows to exclude songs from. Defaults to band-specific config.",
    )
    parser.add_argument(
        "--require-output",
        action="store_true",
        help="Exit non-zero if the run would otherwise finish without writing predictions.",
    )
    args = parser.parse_args()

    model_definition = get_model_definition(args.model)
    if args.retrain and not model_definition.supports_training:
        parser.error(
            f"--retrain is only supported for training-capable models; got {args.model}"
        )

    date_strs: list[str | None] = args.dates if args.dates else [None]

    generate_predictions_batched(
        band=args.band,
        model=args.model,
        date_strs=date_strs,
        exclusion_window=args.exclusion_window,
        retrain=args.retrain,
        require_output=args.require_output,
    )


if __name__ == "__main__":
    main()
