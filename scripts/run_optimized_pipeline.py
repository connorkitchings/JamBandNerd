#!/usr/bin/env python3
"""
Local pipeline runner to orchestrate the execution of consolidated scripts.

This script provides a way to run the entire pipeline for a band locally,
mirroring the logic in the GitHub Actions workflow.

Usage:
    # Run the full pipeline for Goose
    uv run python scripts/run_optimized_pipeline.py --band goose

    # Run the pipeline for all bands, but skip accuracy calculation
    uv run python scripts/run_optimized_pipeline.py --band all --skip-accuracy
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import traceback

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

# Import the functions from the refactored scripts
from scripts.generate_predictions import generate_predictions
from scripts.rebuild_prediction_songs import rebuild_prediction_songs
from scripts.run_backtest import run_backtest
from scripts.run_billy_collection import run_billy_collection
from scripts.run_eggy_collection import run_eggy_collection
from scripts.run_goose_collection import run_goose_collection
from scripts.run_phish_collection import run_phish_collection
from scripts.run_um_collection import run_um_collection
from scripts.run_wsp_collection import run_wsp_collection
from scripts.validate_accuracy_tables import validate_accuracy
from scripts.validate_prediction_tables import validate_predictions
from src.jambandnerd.config.bands import get_active_bands
from src.jambandnerd.models.registry import list_backfill_models, list_pipeline_models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

try:
    from scripts.backfill_predictions import backfill_band

    HAS_BACKFILL = True
except ImportError:
    HAS_BACKFILL = False

from scripts.collection_preflight import CollectionPreflight, compute_band_preflight

# Suppress noisy httpx logs
logging.getLogger("httpx").setLevel(logging.WARNING)


def log_with_timestamp(message: str) -> None:
    """Log a message with a timestamp. (Deprecated: use logger directly)"""
    logger.info(message)


def run_step(func, band: str, step_name: str, *args, **kwargs) -> bool:
    """Run a pipeline step and handle logging and errors."""

    log_with_timestamp(f"[{band.upper()}] Starting: {step_name}")

    try:
        func(band=band, *args, **kwargs)

        log_with_timestamp(f"[{band.upper()}] Finished: {step_name}")

        return True

    except Exception as e:
        log_with_timestamp(f"[{band.upper()}] FAILED: {step_name} with error: {e}")

        traceback.print_exc()

        return False


def _validate_band_predictions(*, band: str, max_age_hours: int = 72) -> None:
    failures = validate_predictions(bands=[band], max_age_hours=max_age_hours)

    if failures:
        raise RuntimeError(
            f"Prediction validation failed for {band}: {failures} issue(s)"
        )


def _validate_band_accuracy(*, band: str, max_age_hours: int = 72) -> None:
    failures = validate_accuracy(bands=[band], max_age_hours=max_age_hours)

    if failures:
        raise RuntimeError(
            f"Accuracy validation failed for {band}: {failures} issue(s)"
        )


def _rebuild_band_prediction_projection(
    *,
    band: str,
    preflight: CollectionPreflight | None,
) -> None:
    reference_date_from = None
    reference_date_to = None
    if preflight is not None:
        reference_date_from = preflight.recent_window_start
        reference_date_to = preflight.lookahead_end

    rebuild_prediction_songs(
        band=band,
        model=None,
        reference_date_from=reference_date_from,
        reference_date_to=reference_date_to,
    )


def run_band_pipeline(band: str, skip_accuracy: bool = False) -> bool:
    """Run the complete, orchestrated pipeline for a single band."""

    log_prefix = f"[{band.upper()}]"

    log_with_timestamp(f"{log_prefix} Starting full pipeline...")

    try:
        preflight = compute_band_preflight(band)
        log_with_timestamp(
            f"{log_prefix} Preflight: mode={preflight.collection_mode} "
            f"execution={preflight.execution_mode} "
            f"recent_completed={preflight.recent_completed_show_count} "
            f"missing_recent_setlists={preflight.missing_recent_setlist_count} "
            f"upcoming_soon={preflight.upcoming_show_count}"
        )
    except Exception as exc:
        log_with_timestamp(f"{log_prefix} WARNING: preflight failed: {exc}")
        preflight = None

    # Step 1: Data Collection

    collection_runners = {
        "goose": run_goose_collection,
        "eggy": run_eggy_collection,
        "phish": run_phish_collection,
        "wsp": run_wsp_collection,
        "billy": run_billy_collection,
        "um": run_um_collection,
    }

    log_with_timestamp(f"[{band.upper()}] Starting: Data Collection")

    try:
        if preflight is not None and not preflight.should_run_collection:
            log_with_timestamp(
                f"{log_prefix} Skipping collection after preflight "
                f"({preflight.execution_mode})."
            )
        else:
            collection_runners[band]()

        log_with_timestamp(f"[{band.upper()}] Finished: Data Collection")

    except Exception as e:
        log_with_timestamp(f"[{band.upper()}] FAILED: Data Collection with error: {e}")

        traceback.print_exc()

        return False

    # Step 2: Generate Predictions, Backtest, and Calculate Accuracy for each model
    models = [definition.slug for definition in list_pipeline_models()]
    for model in models:
        if not run_step(
            generate_predictions,
            band,
            f"{model.title()} Predictions",
            model=model,
            date_str=None,
            exclusion_window=None,
        ):
            return False

        if not skip_accuracy:
            if not run_step(
                run_backtest,
                band,
                f"{model.title()} Backtest",
                model=model,
                start=None,
                end=None,
                shows=100,
                exclusion_window=None,
            ):
                return False

    if skip_accuracy:
        log_with_timestamp(f"{log_prefix} Skipping accuracy calculations.")

    # Step 3: Backfill stale predictions
    if HAS_BACKFILL:
        backfill_models = [definition.slug for definition in list_backfill_models()]
        for model in backfill_models:
            log_with_timestamp(f"[{band.upper()}] Starting: {model.title()} Backfill")
            try:
                result = backfill_band(band, model, dry_run=False)
                log_with_timestamp(
                    f"[{band.upper()}] Finished: {model.title()} Backfill "
                    f"({result['regenerated']} regenerated)"
                )
            except Exception as e:
                log_with_timestamp(
                    f"[{band.upper()}] WARNING: {model.title()} Backfill failed: {e}"
                )

    if not run_step(
        _rebuild_band_prediction_projection,
        band,
        "Prediction Projection Rebuild",
        preflight=preflight,
    ):
        return False

    if not run_step(
        _validate_band_predictions, band, "Prediction Validation", max_age_hours=72
    ):
        return False

    if not skip_accuracy and not run_step(
        _validate_band_accuracy, band, "Accuracy Validation", max_age_hours=72
    ):
        return False

    log_with_timestamp(f"{log_prefix} ✅ Successfully completed pipeline.")

    return True


def main():
    """Main pipeline orchestrator."""
    parser = argparse.ArgumentParser(
        description="Run the JamBandNerd pipeline for one or more bands."
    )
    parser.add_argument(
        "--band",
        choices=[*get_active_bands(), "all"],
        default="all",
        help="Band to process (default: all)",
    )
    parser.add_argument(
        "--skip-accuracy",
        action="store_true",
        help="Skip all accuracy-related calculations",
    )
    args = parser.parse_args()

    overall_start_time = time.time()
    log_with_timestamp("🚀 Starting JamBandNerd Pipeline Orchestrator")

    all_bands = list(get_active_bands())
    bands_to_process = all_bands if args.band == "all" else [args.band]
    results = {}

    for band in bands_to_process:
        band_start_time = time.time()
        success = run_band_pipeline(band, skip_accuracy=args.skip_accuracy)
        band_total_time = time.time() - band_start_time
        results[band] = {"success": success, "time": band_total_time}

    overall_total_time = time.time() - overall_start_time
    log_with_timestamp(f"📊 Pipeline Summary (Total Time: {overall_total_time:.1f}s)")

    failed_bands = []
    for band, result in results.items():
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        log_with_timestamp(f"  {band.upper()}: {status} (took {result['time']:.1f}s)")
        if not result["success"]:
            failed_bands.append(band)

    if failed_bands:
        log_with_timestamp(
            f"❌ Pipeline finished with failures in: {', '.join(failed_bands)}"
        )
        sys.exit(1)
    else:
        log_with_timestamp("🎉 All pipelines completed successfully!")


if __name__ == "__main__":
    main()
