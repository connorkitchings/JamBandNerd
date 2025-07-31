#!/usr/bin/env python3
"""
JamBandNerd Pipeline Scheduler

This script provides a long-running scheduler service for executing the daily pipeline
at specified intervals. Useful for Docker deployments or local development.

Usage:
    python automation/scheduler.py [--cron CRON_EXPRESSION] [--verbose]
"""

import argparse
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import schedule
    from croniter import croniter
except ImportError:
    print("Missing dependencies. Install with: pip install schedule croniter")
    sys.exit(1)

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from automation.daily_pipeline import main as run_daily_pipeline


class PipelineScheduler:
    """Scheduler service for JamBandNerd pipelines."""
    
    def __init__(self, cron_expression: str = "0 20 * * *", verbose: bool = False):
        self.cron_expression = cron_expression
        self.verbose = verbose
        self.running = True
        self.logger = self._setup_logging()
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO
        
        # Create logs directory if it doesn't exist
        logs_dir = Path(__file__).parent.parent / "logs" / "automation"
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        log_file = logs_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        return logging.getLogger(__name__)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def _run_pipeline(self):
        """Execute the daily pipeline."""
        self.logger.info("🚀 Scheduled pipeline execution starting...")
        
        try:
            # Import and run the daily pipeline
            import subprocess
            import sys
            
            # Run the daily pipeline as a subprocess to isolate execution
            result = subprocess.run([
                sys.executable, 
                str(Path(__file__).parent / "daily_pipeline.py"),
                "--verbose" if self.verbose else ""
            ], capture_output=False, text=True)
            
            if result.returncode == 0:
                self.logger.info("✅ Scheduled pipeline execution completed successfully")
            else:
                self.logger.error(f"❌ Scheduled pipeline execution failed with code {result.returncode}")
                
        except Exception as e:
            self.logger.error(f"💥 Error during scheduled pipeline execution: {e}")
    
    def _get_next_run_times(self, count: int = 3) -> list:
        """Get the next N scheduled run times."""
        try:
            cron = croniter(self.cron_expression, datetime.now())
            return [cron.get_next(datetime) for _ in range(count)]
        except Exception:
            return []
    
    def start(self):
        """Start the scheduler service."""
        self.logger.info("🕐 JamBandNerd Pipeline Scheduler Starting")
        self.logger.info(f"📅 Schedule: {self.cron_expression}")
        
        # Display next run times
        next_runs = self._get_next_run_times()
        if next_runs:
            self.logger.info("📋 Next scheduled runs:")
            for i, run_time in enumerate(next_runs, 1):
                self.logger.info(f"   {i}. {run_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Set up the schedule using the cron expression
        try:
            # Parse cron expression and set up schedule
            cron = croniter(self.cron_expression)
            
            # For simplicity, we'll check every minute if it's time to run
            schedule.every().minute.do(self._check_and_run)
            
            self.logger.info("✅ Scheduler started successfully")
            
            # Main scheduler loop
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except Exception as e:
            self.logger.error(f"💥 Error in scheduler: {e}")
            return False
        
        self.logger.info("🛑 Scheduler stopped")
        return True
    
    def _check_and_run(self):
        """Check if it's time to run the pipeline based on cron expression."""
        try:
            cron = croniter(self.cron_expression, datetime.now())
            # Check if the current time matches the cron schedule (within the last minute)
            prev_run = cron.get_prev(datetime)
            if (datetime.now() - prev_run).total_seconds() < 60:
                self._run_pipeline()
        except Exception as e:
            self.logger.error(f"Error checking schedule: {e}")


def main():
    """Main entry point for the scheduler service."""
    parser = argparse.ArgumentParser(description="JamBandNerd Pipeline Scheduler")
    parser.add_argument(
        "--cron", 
        default=os.getenv("SCHEDULE_CRON", "0 20 * * *"),
        help="Cron expression for scheduling (default: 0 20 * * * = 3 PM ET)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Create and start the scheduler
    scheduler = PipelineScheduler(args.cron, args.verbose)
    
    try:
        success = scheduler.start()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Scheduler interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
