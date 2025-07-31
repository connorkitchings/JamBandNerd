#!/usr/bin/env python3
"""
Daily Pipeline Orchestrator for JamBandNerd

This script orchestrates the daily execution of data collection and prediction pipelines.
It's designed to be run in automated environments (GitHub Actions, cron, etc.).

Usage:
    python automation/daily_pipeline.py [--data-only] [--predictions-only] [--verbose]
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from jambandnerd.predictions.run_all_predictions import run_all_predictions


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory if it doesn't exist
    logs_dir = Path(__file__).parent.parent / "logs" / "automation"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    log_file = logs_dir / f"daily_pipeline_{datetime.now().strftime('%Y%m%d')}.log"
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def run_data_collection(logger: logging.Logger) -> bool:
    """
    Run the data collection pipeline.
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("🔄 Starting data collection pipeline...")
    start_time = time.time()
    
    try:
        # Run WSP data collection (Phish and Goose are API-based, no separate collection needed)
        logger.info("Running WSP data collection to Supabase...")
        
        # Import and run WSP pipeline
        from jambandnerd.data_collection.wsp.run_pipeline_supabase import main as run_wsp_collection
        
        success = run_wsp_collection()
        
        duration = time.time() - start_time
        
        if success:
            logger.info(f"✅ Data collection completed successfully in {duration:.2f} seconds")
            return True
        else:
            logger.error(f"❌ Data collection failed after {duration:.2f} seconds")
            return False
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ Data collection failed with exception after {duration:.2f} seconds: {e}")
        return False


def run_predictions(logger: logging.Logger) -> bool:
    """
    Run all prediction pipelines.
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("🔄 Starting prediction pipelines...")
    start_time = time.time()
    
    try:
        success = run_all_predictions()
        duration = time.time() - start_time
        
        if success:
            logger.info(f"✅ All prediction pipelines completed successfully in {duration:.2f} seconds")
            return True
        else:
            logger.error(f"❌ One or more prediction pipelines failed after {duration:.2f} seconds")
            return False
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"❌ Prediction pipelines failed with exception after {duration:.2f} seconds: {e}")
        return False


def generate_summary_report(
    data_collection_success: bool,
    predictions_success: bool,
    total_duration: float,
    logger: logging.Logger
) -> None:
    """Generate a summary report of the pipeline execution."""
    
    logger.info("\n" + "="*60)
    logger.info("📊 DAILY PIPELINE EXECUTION SUMMARY")
    logger.info("="*60)
    logger.info(f"⏰ Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    logger.info(f"⏱️  Total Duration: {total_duration:.2f} seconds")
    logger.info(f"📊 Data Collection: {'✅ SUCCESS' if data_collection_success else '❌ FAILED'}")
    logger.info(f"🔮 Predictions: {'✅ SUCCESS' if predictions_success else '❌ FAILED'}")
    
    overall_success = data_collection_success and predictions_success
    logger.info(f"🎯 Overall Status: {'✅ SUCCESS' if overall_success else '❌ FAILED'}")
    logger.info("="*60)


def main():
    """Main entry point for the daily pipeline orchestrator."""
    parser = argparse.ArgumentParser(description="Run JamBandNerd daily pipelines")
    parser.add_argument("--data-only", action="store_true", help="Run only data collection")
    parser.add_argument("--predictions-only", action="store_true", help="Run only predictions")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.verbose)
    
    logger.info("🚀 Starting JamBandNerd Daily Pipeline Orchestrator")
    logger.info(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    start_time = time.time()
    data_collection_success = True
    predictions_success = True
    
    try:
        # Run data collection (unless predictions-only)
        if not args.predictions_only:
            data_collection_success = run_data_collection(logger)
            
            if not data_collection_success:
                logger.warning("⚠️  Data collection failed, but continuing with predictions...")
        else:
            logger.info("⏭️  Skipping data collection (predictions-only mode)")
        
        # Run predictions (unless data-only)
        if not args.data_only:
            predictions_success = run_predictions(logger)
        else:
            logger.info("⏭️  Skipping predictions (data-only mode)")
        
        # Generate summary report
        total_duration = time.time() - start_time
        generate_summary_report(
            data_collection_success,
            predictions_success,
            total_duration,
            logger
        )
        
        # Exit with appropriate code
        overall_success = data_collection_success and predictions_success
        sys.exit(0 if overall_success else 1)
        
    except KeyboardInterrupt:
        logger.info("⏹️  Pipeline execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        total_duration = time.time() - start_time
        logger.error(f"💥 Unexpected error in pipeline orchestrator: {e}")
        generate_summary_report(False, False, total_duration, logger)
        sys.exit(1)


if __name__ == "__main__":
    main()
