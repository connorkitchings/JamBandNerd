#!/usr/bin/env python3
"""
Optimized pipeline runner that minimizes data fetching and maximizes reuse.

This script coordinates the full pipeline for one or more bands:
1. Data Collection (once per band)
2. Both Model Predictions (reusing loaded data)
3. Both Accuracy Calculations (reusing loaded data)

Usage:
    python scripts/run_optimized_pipeline.py --band goose
    python scripts/run_optimized_pipeline.py --band phish  
    python scripts/run_optimized_pipeline.py --band all
    python scripts/run_optimized_pipeline.py --band all --skip-accuracy
"""
from __future__ import annotations

import argparse
import sys
import os
import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.data_collection.goose.collector import GooseCollector
from src.jambandnerd.data_collection.phish.collector import PhishCollector
from src.jambandnerd.models.notebook.model import NotebookPredictor
from src.jambandnerd.models.ckplus.model import CKPlusPredictor
from src.jambandnerd.models.accuracy import compute_per_show_metrics, aggregate_metrics
from src.jambandnerd.transformations.gaps import generate_model_data
from src.jambandnerd.db.operations import upsert_dataframe
from src.jambandnerd.db.connection import get_supabase_client
from scripts.common import resolve_reference_date, fetch_table, prepare_band_data
import json


def log_with_timestamp(message: str) -> None:
    """Log message with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def run_band_pipeline(band: str, skip_accuracy: bool = False) -> dict:
    """
    Run the complete pipeline for a single band with optimized data reuse.
    
    Returns:
        dict: Pipeline results and timing information
    """
    results = {
        "band": band,
        "start_time": time.time(),
        "collection_success": False,
        "notebook_prediction_success": False,
        "ckplus_prediction_success": False,
        "notebook_accuracy_success": False,
        "ckplus_accuracy_success": False,
    }
    
    log_with_timestamp(f"Starting optimized pipeline for {band.upper()}")
    
    try:
        # Step 1: Data Collection
        log_with_timestamp(f"Step 1: Collecting {band} data...")
        collection_start = time.time()
        
        if band == "goose":
            from scripts.run_goose_collection import run_goose_collection
            run_goose_collection(skip_validation=True)
        elif band == "phish":
            from scripts.run_phish_collection import run_phish_collection
            run_phish_collection(
                skip_validation=True, 
                only_setlists=True, 
                year_start=2024, 
                year_end=2025
            )
        else:
            raise ValueError(f"Unknown band: {band}")
            
        results["collection_success"] = True
        collection_time = time.time() - collection_start
        log_with_timestamp(f"✅ Data collection completed in {collection_time:.1f}s")
        
        # Step 2: Load and prepare data once for both models
        log_with_timestamp(f"Step 2: Loading and preparing {band} data for predictions...")
        data_prep_start = time.time()
        
        # Fetch raw data
        shows_df = pd.DataFrame(fetch_table(f"{band}_shows_raw"))
        setlists_df = pd.DataFrame(fetch_table(f"{band}_setlists_raw"))
        
        if shows_df.empty or setlists_df.empty:
            log_with_timestamp(f"❌ No data available for {band}, skipping predictions")
            return results
            
        # Prepare data
        shows_df, setlists_df = prepare_band_data(shows_df, setlists_df)
        reference_date = resolve_reference_date(None, shows_df)
        model_data = generate_model_data(shows_df, setlists_df, reference_date, debug=False)
        
        data_prep_time = time.time() - data_prep_start
        log_with_timestamp(f"✅ Data preparation completed in {data_prep_time:.1f}s")
        
        # Step 3: Generate predictions for both models
        log_with_timestamp(f"Step 3: Generating predictions for both models...")
        
        # Notebook predictions
        notebook_start = time.time()
        try:
            predictor = NotebookPredictor()
            predictions, diagnostics = predictor.predict(model_data=model_data, top_k=50)
            
            if predictions:
                # Format for Supabase
                predictions_list = []
                for i, p in enumerate(predictions):
                    predictions_list.append({
                        "rank": i + 1,
                        "song_name": p.song_name,
                        "plays_past_year": p.plays_past_year,
                        "current_gap": p.current_gap,
                        "last_played_date": p.last_played_date,
                    })
                
                output_row = {
                    "band": band,
                    "reference_date": reference_date.isoformat(),
                    "model_version": "notebook_v1",
                    "top_k": len(predictions_list),
                    "predictions": json.dumps(predictions_list),
                    "predicted_at": datetime.now(timezone.utc).isoformat(),
                }
                
                upsert_dataframe(
                    table_name="predictions_notebook",
                    df=pd.DataFrame([output_row]),
                    conflict_columns=["band", "reference_date", "model_version"],
                )
                results["notebook_prediction_success"] = True
                log_with_timestamp(f"✅ Notebook predictions saved ({len(predictions)} songs)")
            
        except Exception as e:
            log_with_timestamp(f"❌ Notebook predictions failed: {e}")
        
        notebook_time = time.time() - notebook_start
        
        # CK+ predictions
        ckplus_start = time.time()
        try:
            CKPLUS_RETIREMENT_GAPS = {
                "goose": 100,
                "phish": 150,
            }
            retirement_gap = CKPLUS_RETIREMENT_GAPS.get(band, 250)
            predictor = CKPlusPredictor(retired_gap_threshold=retirement_gap)
            predictions = predictor.predict(model_data=model_data, top_k=50)
            
            if predictions:
                # Format for Supabase
                predictions_list = []
                for i, p in enumerate(predictions):
                    predictions_list.append({
                        "rank": i + 1,
                        "song_name": p.song_name,
                        "times_played": p.times_played,
                        "current_gap": p.current_gap,
                        "avg_gap": p.avg_gap,
                        "gap_ratio": p.gap_ratio,
                        "gap_z_score": p.gap_z_score,
                        "ckplus_score": p.ckplus_score,
                        "LTP": p.LTP,
                    })
                
                output_row = {
                    "band": band,
                    "reference_date": reference_date.isoformat(),
                    "model_version": "ckplus_v1",
                    "top_k": len(predictions_list),
                    "predictions": json.dumps(predictions_list),
                    "predicted_at": datetime.now(timezone.utc).isoformat(),
                }
                
                upsert_dataframe(
                    table_name="predictions_ckplus",
                    df=pd.DataFrame([output_row]),
                    conflict_columns=["band", "reference_date", "model_version"],
                )
                results["ckplus_prediction_success"] = True
                log_with_timestamp(f"✅ CK+ predictions saved ({len(predictions)} songs)")
                
        except Exception as e:
            log_with_timestamp(f"❌ CK+ predictions failed: {e}")
            
        ckplus_time = time.time() - ckplus_start
        log_with_timestamp(f"Prediction timing: Notebook={notebook_time:.1f}s, CK+={ckplus_time:.1f}s")
        
        # Step 4: Calculate accuracy (if requested)
        if not skip_accuracy:
            log_with_timestamp(f"Step 4: Calculating accuracy metrics...")
            accuracy_start = time.time()
            
            # Notebook accuracy
            try:
                from scripts.save_notebook_accuracy import main as save_notebook_accuracy
                # We can't easily call this directly, so use the existing script approach
                # This could be optimized further by inlining the logic
                os.system(f"cd {project_root} && python scripts/save_notebook_accuracy.py --band {band} --shows 50")
                results["notebook_accuracy_success"] = True
                log_with_timestamp(f"✅ Notebook accuracy calculated")
            except Exception as e:
                log_with_timestamp(f"❌ Notebook accuracy failed: {e}")
            
            # CK+ accuracy  
            try:
                os.system(f"cd {project_root} && python scripts/save_ckplus_accuracy.py --band {band} --shows 50")
                results["ckplus_accuracy_success"] = True
                log_with_timestamp(f"✅ CK+ accuracy calculated")
            except Exception as e:
                log_with_timestamp(f"❌ CK+ accuracy failed: {e}")
                
            accuracy_time = time.time() - accuracy_start
            log_with_timestamp(f"Accuracy calculation completed in {accuracy_time:.1f}s")
        else:
            log_with_timestamp("Step 4: Skipping accuracy calculations")
        
        # Final timing
        total_time = time.time() - results["start_time"]
        log_with_timestamp(f"🎉 {band.upper()} pipeline completed in {total_time:.1f}s total")
        
        results["total_time"] = total_time
        return results
        
    except Exception as e:
        log_with_timestamp(f"❌ {band.upper()} pipeline failed: {e}")
        results["error"] = str(e)
        results["total_time"] = time.time() - results["start_time"]
        return results


def main():
    """Main pipeline orchestrator."""
    parser = argparse.ArgumentParser(
        description="Run optimized JamBandNerd pipeline with minimal data fetching"
    )
    parser.add_argument(
        "--band", 
        choices=["goose", "phish", "all"], 
        default="all",
        help="Band to process (default: all)"
    )
    parser.add_argument(
        "--skip-accuracy", 
        action="store_true",
        help="Skip accuracy calculations to speed up pipeline"
    )
    args = parser.parse_args()
    
    start_time = time.time()
    log_with_timestamp("🚀 Starting JamBandNerd Optimized Pipeline")
    
    # Determine bands to process
    bands = ["goose", "phish"] if args.band == "all" else [args.band]
    
    # Run pipeline for each band
    all_results = []
    for band in bands:
        result = run_band_pipeline(band, skip_accuracy=args.skip_accuracy)
        all_results.append(result)
    
    # Summary
    total_pipeline_time = time.time() - start_time
    log_with_timestamp(f"📊 Pipeline Summary (Total: {total_pipeline_time:.1f}s)")
    
    for result in all_results:
        band = result["band"].upper()
        time_taken = result.get("total_time", 0)
        
        if "error" in result:
            log_with_timestamp(f"  {band}: ❌ FAILED ({time_taken:.1f}s) - {result['error']}")
        else:
            successes = []
            if result["collection_success"]: successes.append("Collection")
            if result["notebook_prediction_success"]: successes.append("Notebook")
            if result["ckplus_prediction_success"]: successes.append("CK+")
            if not args.skip_accuracy:
                if result["notebook_accuracy_success"]: successes.append("NB-Acc")
                if result["ckplus_accuracy_success"]: successes.append("CK+-Acc")
            
            success_str = ", ".join(successes) if successes else "None"
            log_with_timestamp(f"  {band}: ✅ SUCCESS ({time_taken:.1f}s) - {success_str}")
    
    # Exit with error code if any band failed completely
    failed_bands = [r for r in all_results if "error" in r]
    if failed_bands:
        log_with_timestamp(f"❌ {len(failed_bands)} band(s) failed completely")
        sys.exit(1)
    else:
        log_with_timestamp("🎉 All bands completed successfully!")


if __name__ == "__main__":
    main()
