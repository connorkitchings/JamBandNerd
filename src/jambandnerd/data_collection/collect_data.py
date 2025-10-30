#!/usr/bin/env python3
"""
Enhanced data collection script for JamBandNerd.

This script provides a robust entry point for collecting data from various band APIs,
with comprehensive error handling, recovery mechanisms, and progress tracking.
"""
import logging
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, date

from .goose.collector import GooseCollector
from .eggy.collector import EggyCollector
from .phish.collector import PhishCollector

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Path(__file__).parent / f"collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)


class CollectionManager:
    """Manages the data collection process with error handling and recovery."""
    
    def __init__(self):
        self.collectors = {
            'goose': GooseCollector,
            'eggy': EggyCollector,
            'phish': PhishCollector
        }
        self.results = {}
        self.errors = {}
    
    def collect_all_data(self, bands: Optional[List[str]] = None, data_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Collect data from all specified bands with robust error handling.
        
        Args:
            bands: List of band names to collect from. If None, collects from all available bands.
            data_types: List of data types to collect ('shows', 'setlists', 'songs', 'venues').
                       If None, collects all types.
        
        Returns:
            Dictionary with collection results and error information.
        """
        if bands is None:
            bands = list(self.collectors.keys())
        
        if data_types is None:
            data_types = ['shows', 'setlists', 'songs', 'venues']
        
        logger.info(f"Starting data collection for bands: {bands}, data types: {data_types}")
        
        for band_name in bands:
            if band_name not in self.collectors:
                logger.warning(f"Unknown band: {band_name}. Available bands: {list(self.collectors.keys())}")
                continue
                
            self._collect_band_data(band_name, data_types)
        
        # Generate summary report
        self._generate_summary_report()
        
        return {
            'results': self.results,
            'errors': self.errors,
            'timestamp': datetime.now().isoformat()
        }
    
    def _collect_band_data(self, band_name: str, data_types: List[str]) -> None:
        """Collect data for a specific band with comprehensive error handling."""
        logger.info(f"Collecting data for {band_name}...")
        
        try:
            # Initialize collector
            collector_class = self.collectors[band_name]
            collector = collector_class()
            
            self.results[band_name] = {}
            self.errors[band_name] = {}
            
            # Collect each data type
            for data_type in data_types:
                self._collect_data_type(collector, band_name, data_type)
                
        except Exception as e:
            error_msg = f"Failed to initialize collector for {band_name}: {str(e)}"
            logger.error(error_msg)
            self.errors[band_name] = {'initialization': error_msg}
    
    def _collect_data_type(self, collector: Any, band_name: str, data_type: str) -> None:
        """Collect a specific data type with error handling and retry logic."""
        method_name = f"collect_{data_type}"
        
        if not hasattr(collector, method_name):
            error_msg = f"Collector for {band_name} does not support {data_type} collection"
            logger.warning(error_msg)
            self.errors[band_name][data_type] = error_msg
            return
        
        logger.info(f"Collecting {data_type} for {band_name}...")
        
        try:
            # Get the collection method
            collect_method = getattr(collector, method_name)
            
            # Handle different method signatures
            if data_type == 'setlists' and band_name == 'phish':
                # Phish setlists need show IDs, so collect shows first if not already done
                if 'shows' not in self.results.get(band_name, {}):
                    logger.info(f"Collecting shows first to get show IDs for {band_name} setlists...")
                    shows_data = collector.collect_shows()
                    self.results[band_name]['shows'] = shows_data
                    logger.info(f"Collected {len(shows_data)} shows for {band_name}")
                
                # Extract show IDs for setlist collection
                shows_data = self.results[band_name]['shows']
                show_ids = [str(show.get('showid', show.get('id', ''))) for show in shows_data if show.get('showid') or show.get('id')]
                show_ids = [sid for sid in show_ids if sid]  # Filter out empty IDs
                
                logger.info(f"Collected {len(show_ids)} show IDs for setlist collection")
                data = collect_method(show_ids[:100])  # Limit to first 100 shows for demo
            else:
                # Standard collection method call
                data = collect_method()
            
            # Store results
            self.results[band_name][data_type] = data
            logger.info(f"Successfully collected {len(data)} {data_type} records for {band_name}")
            
        except Exception as e:
            error_msg = f"Failed to collect {data_type} for {band_name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.errors[band_name][data_type] = error_msg
    
    def _generate_summary_report(self) -> None:
        """Generate a summary report of the collection process."""
        logger.info("=" * 60)
        logger.info("COLLECTION SUMMARY REPORT")
        logger.info("=" * 60)
        
        total_records = 0
        total_errors = 0
        
        for band_name in self.results:
            logger.info(f"\n{band_name.upper()}:")
            
            for data_type, data in self.results[band_name].items():
                count = len(data) if data else 0
                total_records += count
                logger.info(f"  {data_type}: {count} records")
            
            # Report errors for this band
            if band_name in self.errors and self.errors[band_name]:
                logger.warning(f"  Errors:")
                for error_type, error_msg in self.errors[band_name].items():
                    logger.warning(f"    {error_type}: {error_msg}")
                    total_errors += 1
        
        logger.info(f"\nTOTAL RECORDS COLLECTED: {total_records}")
        logger.info(f"TOTAL ERRORS: {total_errors}")
        
        if total_errors == 0:
            logger.info("✅ Collection completed successfully!")
        else:
            logger.warning(f"⚠️  Collection completed with {total_errors} errors. Check logs for details.")


def main():
    """Main entry point for the data collection script."""
    parser = argparse.ArgumentParser(description="Collect data from band APIs with enhanced error handling")
    parser.add_argument(
        '--bands', 
        nargs='+', 
        choices=['goose', 'eggy', 'phish'], 
        help='Bands to collect data from (default: all)',
        default=None
    )
    parser.add_argument(
        '--data-types', 
        nargs='+', 
        choices=['shows', 'setlists', 'songs', 'venues'], 
        help='Types of data to collect (default: all)',
        default=None
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set the logging level'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    try:
        # Initialize collection manager
        manager = CollectionManager()
        
        # Run collection
        results = manager.collect_all_data(bands=args.bands, data_types=args.data_types)
        
        # Exit with appropriate code
        if results['errors'] and any(results['errors'].values()):
            logger.warning("Collection completed with errors")
            sys.exit(1)
        else:
            logger.info("Collection completed successfully")
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error during collection: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
