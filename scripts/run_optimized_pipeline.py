#!/usr/bin/env python3
"""
Local helper to run the consolidated pipeline scripts for one or more bands.

This script mirrors the promoted daily workflow sequence for local use, but the
canonical orchestration contract lives in `.github/workflows/daily-pipeline.yml`.

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
from scripts.audit_supabase_tables import run_supabase_audit
from scripts.collection_preflight import compute_band_preflight
from scripts.generate_live_predictions import generate_live_predictions
from scripts.run_billy_collection import run_billy_collection
from scripts.run_eggy_collection import run_eggy_collection
from scripts.run_goose_collection import run_goose_collection
from scripts.run_phish_collection import run_phish_collection
from scripts.run_um_collection import run_um_collection
from scripts.run_wsp_collection import run_wsp_collection
from scripts.validate_accuracy_tables import validate_accuracy
from scripts.validate_prediction_tables import validate_predictions
from src.jambandnerd.models.registry import list_active_bands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

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


def _validate_band_accuracy_skip_freshness(
    *, band: str, max_age_hours: int = 72
) -> None:
    failures = validate_accuracy(
        bands=[band],
        max_age_hours=max_age_hours,
        skip_freshness=True,
    )

    if failures:
        raise RuntimeError(
            f"Accuracy validation failed for {band}: {failures} issue(s)"
        )


def _audit_band_supabase(
    *,
    band: str,
    max_age_hours: int = 72,
    skip_accuracy: bool = False,
) -> None:
    report = run_supabase_audit(
        bands=[band],
        max_age_hours=max_age_hours,
        skip_accuracy=skip_accuracy,
    )
    if report.state == "failed":
        raise RuntimeError(
            f"Supabase audit failed for {band}: {len(report.blockers)} blocker(s)"
        )


def _generate_band_predictions(*, band: str) -> None:
    generate_live_predictions(
        band=band,
        exclusion_window=None,
    )


def _run_band_backtest(*, band: str) -> int:
    from scripts.run_backtest import run_backtest

    return run_backtest(
        band=band,
        model=None,
        start=None,
        end=None,
        shows=50,
        exclusion_window=None,
        incremental=True,
        require_results=True,
    )


def run_band_pipeline(
    band: str,
    skip_accuracy: bool = False,
    force: bool = False,
) -> bool:
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
            if not force:
                log_with_timestamp(
                    f"{log_prefix} Verify-only preflight selected; skipping "
                    "prediction and backtest work. Pass --force to run anyway."
                )
                return True
            log_with_timestamp(
                f"{log_prefix} Force enabled; continuing with prediction and "
                "backtest work after verify-only preflight."
            )
        else:
            collection_runners[band]()

        log_with_timestamp(f"[{band.upper()}] Finished: Data Collection")

    except Exception as e:
        log_with_timestamp(f"[{band.upper()}] FAILED: Data Collection with error: {e}")

        traceback.print_exc()

        return False

    # Step 2: Generate Predictions, Backtest, and Calculate Accuracy
    backtest_incremental_all_scored = True
    if not run_step(_generate_band_predictions, band, "Live Predictions"):
        return False

    if not skip_accuracy:
        log_with_timestamp(f"[{band.upper()}] Starting: Retained Corpus Backtest")
        try:
            scored_count = _run_band_backtest(band=band)
        except Exception as e:
            log_with_timestamp(
                f"[{band.upper()}] FAILED: Retained Corpus Backtest with error: {e}"
            )
            traceback.print_exc()
            return False
        if scored_count:
            backtest_incremental_all_scored = False
        log_with_timestamp(f"[{band.upper()}] Finished: Retained Corpus Backtest")

    audit_skip_accuracy = skip_accuracy or backtest_incremental_all_scored

    if not skip_accuracy and backtest_incremental_all_scored:
        log_with_timestamp(
            f"{log_prefix} Active model had an already-scored backtest window; "
            "accuracy freshness will be treated as immutable drift."
        )

    if skip_accuracy:
        log_with_timestamp(f"{log_prefix} Skipping accuracy calculations.")

    if not run_step(
        _validate_band_predictions, band, "Prediction Validation", max_age_hours=72
    ):
        return False

    if not skip_accuracy:
        accuracy_validator = (
            _validate_band_accuracy_skip_freshness
            if backtest_incremental_all_scored
            else _validate_band_accuracy
        )
        if not run_step(
            accuracy_validator, band, "Accuracy Validation", max_age_hours=72
        ):
            return False

    if not run_step(
        _audit_band_supabase,
        band,
        "Supabase Audit",
        max_age_hours=72,
        skip_accuracy=audit_skip_accuracy,
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
        choices=[*list_active_bands(), "all"],
        default="all",
        help="Band to process (default: all)",
    )
    parser.add_argument(
        "--skip-accuracy",
        action="store_true",
        help="Skip all accuracy-related calculations",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run prediction/backtest work even when preflight selects verify-only mode.",
    )
    args = parser.parse_args()

    overall_start_time = time.time()
    log_with_timestamp("🚀 Starting JamBandNerd Pipeline Orchestrator")

    all_bands = list_active_bands()
    bands_to_process = all_bands if args.band == "all" else [args.band]
    results = {}

    for band in bands_to_process:
        band_start_time = time.time()
        success = run_band_pipeline(
            band,
            skip_accuracy=args.skip_accuracy,
            force=args.force,
        )
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
