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
import subprocess
import sys
import os
import time
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

def log_with_timestamp(message: str) -> None:
    """Log a message with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def run_command(command: list[str], band: str, step: str) -> bool:
    """Run a shell command and return True on success."""
    log_with_timestamp(f"[{band.upper()}] Starting: {step}")
    try:
        process = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding='utf-8'
        )
        if process.stdout:
            print(process.stdout)
        if process.stderr:
            print(process.stderr)
        log_with_timestamp(f"[{band.upper()}] Finished: {step}")
        return True
    except subprocess.CalledProcessError as e:
        log_with_timestamp(f"[{band.upper()}] FAILED: {step}")
        print(e.stdout)
        print(e.stderr)
        return False
    except Exception as e:
        log_with_timestamp(f"[{band.upper()}] FAILED: {step} with unexpected error: {e}")
        return False

def run_band_pipeline(band: str, skip_accuracy: bool = False) -> bool:
    """Run the complete, orchestrated pipeline for a single band."""
    log_prefix = f"[{band.upper()}]"
    log_with_timestamp(f"{log_prefix} Starting full pipeline...")
    
    # Step 1: Data Collection
    collection_script = f"scripts/run_{band}_collection.py"
    if not run_command(["python", collection_script], band, "Data Collection"):
        return False

    # Step 2: Generate Predictions
    if not run_command(["python", "scripts/generate_predictions.py", "--band", band, "--model", "notebook"], band, "Notebook Predictions"):
        return False
    if not run_command(["python", "scripts/generate_predictions.py", "--band", band, "--model", "ckplus"], band, "CK+ Predictions"):
        return False

    # Step 3: Accuracy Calculations
    if not skip_accuracy:
        # Run backtests to populate per-show data
        if not run_command(["python", "scripts/run_backtest.py", "--band", band, "--model", "notebook", "--shows", "100"], band, "Notebook Backtest"):
            return False
        if not run_command(["python", "scripts/run_backtest.py", "--band", band, "--model", "ckplus", "--shows", "100"], band, "CK+ Backtest"):
            return False
        
        # Run aggregate accuracy calculations
        if not run_command(["python", "scripts/save_aggregate_accuracy.py", "--band", band, "--model", "notebook", "--shows", "100"], band, "Notebook Aggregate Accuracy"):
            return False
        if not run_command(["python", "scripts/save_aggregate_accuracy.py", "--band", band, "--model", "ckplus", "--shows", "100"], band, "CK+ Aggregate Accuracy"):
            return False
    else:
        log_with_timestamp(f"{log_prefix} Skipping accuracy calculations.")

    log_with_timestamp(f"{log_prefix} ✅ Successfully completed pipeline.")
    return True

def main():
    """Main pipeline orchestrator."""
    parser = argparse.ArgumentParser(
        description="Run the JamBandNerd pipeline for one or more bands."
    )
    parser.add_argument(
        "--band", 
        choices=["goose", "phish", "wsp", "all"], 
        default="all",
        help="Band to process (default: all)"
    )
    parser.add_argument(
        "--skip-accuracy", 
        action="store_true",
        help="Skip all accuracy-related calculations"
    )
    args = parser.parse_args()
    
    overall_start_time = time.time()
    log_with_timestamp("🚀 Starting JamBandNerd Pipeline Orchestrator")
    
    bands_to_process = ["goose", "phish", "wsp"] if args.band == "all" else [args.band]
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
        log_with_timestamp(f"❌ Pipeline finished with failures in: {', '.join(failed_bands)}")
        sys.exit(1)
    else:
        log_with_timestamp("🎉 All pipelines completed successfully!")

if __name__ == "__main__":
    main()