"""
Orchestration script to run all prediction pipelines.

This script runs both CK+ and Notebook models for all bands (Phish and Goose).
"""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Callable

from .phish.ckplus_pipeline import run_phish_ckplus_predictions
from .phish.notebook_pipeline import run_phish_notebook_predictions
from .goose.ckplus_pipeline import run_goose_ckplus_predictions
from .goose.notebook_pipeline import run_goose_notebook_predictions
from .wsp.ckplus_pipeline import main as run_wsp_ckplus_predictions
from .wsp.notebook_pipeline import main as run_wsp_notebook_predictions

logger = logging.getLogger(__name__)


def run_pipeline_with_logging(pipeline_func: Callable[[], bool], pipeline_name: str) -> Tuple[str, bool]:
    """
    Run a pipeline function with proper logging.
    
    Args:
        pipeline_func: Function to execute
        pipeline_name: Name for logging purposes
        
    Returns:
        Tuple of (pipeline_name, success_status)
    """
    try:
        logger.info(f"Starting {pipeline_name}...")
        success = pipeline_func()
        if success:
            logger.info(f"✅ {pipeline_name} completed successfully")
        else:
            logger.error(f"❌ {pipeline_name} failed")
        return pipeline_name, success
    except Exception as e:
        logger.error(f"❌ {pipeline_name} failed with exception: {e}")
        return pipeline_name, False


def run_all_predictions(parallel: bool = True) -> bool:
    """
    Run all prediction pipelines.
    
    Args:
        parallel: If True, run pipelines in parallel. If False, run sequentially.
        
    Returns:
        bool: True if all pipelines succeeded, False otherwise
    """
    pipelines = [
        (run_phish_ckplus_predictions, "Phish CK+ Pipeline"),
        (run_phish_notebook_predictions, "Phish Notebook Pipeline"),
        (run_goose_ckplus_predictions, "Goose CK+ Pipeline"),
        (run_goose_notebook_predictions, "Goose Notebook Pipeline"),
        (run_wsp_ckplus_predictions, "WSP CK+ Pipeline"),
        (run_wsp_notebook_predictions, "WSP Notebook Pipeline"),
    ]
    
    results = []
    
    if parallel:
        logger.info("Running all prediction pipelines in parallel...")
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_pipeline = {
                executor.submit(run_pipeline_with_logging, func, name): name
                for func, name in pipelines
            }
            
            for future in as_completed(future_to_pipeline):
                pipeline_name, success = future.result()
                results.append((pipeline_name, success))
    else:
        logger.info("Running all prediction pipelines sequentially...")
        for func, name in pipelines:
            pipeline_name, success = run_pipeline_with_logging(func, name)
            results.append((pipeline_name, success))
    
    # Summary
    successful = [name for name, success in results if success]
    failed = [name for name, success in results if not success]
    
    logger.info(f"\n=== PREDICTION PIPELINE SUMMARY ===")
    logger.info(f"Total pipelines: {len(results)}")
    logger.info(f"Successful: {len(successful)}")
    logger.info(f"Failed: {len(failed)}")
    
    if successful:
        logger.info(f"✅ Successful pipelines: {', '.join(successful)}")
    
    if failed:
        logger.error(f"❌ Failed pipelines: {', '.join(failed)}")
    
    return len(failed) == 0


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Parse command line arguments
    parallel = "--sequential" not in sys.argv
    
    if parallel:
        logger.info("Running in parallel mode (use --sequential for sequential execution)")
    else:
        logger.info("Running in sequential mode")
    
    success = run_all_predictions(parallel=parallel)
    exit(0 if success else 1)
