"""Centralized logging configuration for JamBandNerd.

This module provides a consistent logging setup across all components of the
application, including formatters, handlers, and log levels.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

# Default log format with timestamp, level, name, and message
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DETAILED_LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
)
SIMPLE_LOG_FORMAT = "%(levelname)s: %(message)s"

# Date format for timestamps
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str | Path] = None,
    detailed: bool = False,
    console: bool = True,
) -> None:
    """Configure logging for the entire application.

    Args:
        level: The minimum log level to capture (default: INFO)
        log_file: Optional file path for log output. If None, logs only to console
        detailed: Whether to use detailed log format with file/line info
        console: Whether to output logs to console (default: True)

    Example:
        >>> setup_logging(level=logging.DEBUG, log_file="jambandnerd.log", detailed=True)
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Choose format
    log_format = DETAILED_LOG_FORMAT if detailed else DEFAULT_LOG_FORMAT
    formatter = logging.Formatter(log_format, datefmt=DATE_FORMAT)

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Set levels for noisy third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Get a logger with the specified name and optional level.

    Args:
        name: Name of the logger (typically __name__)
        level: Optional log level override for this specific logger

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting data collection")
    """
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger


def setup_script_logging(script_name: str, verbose: bool = False) -> logging.Logger:
    """Set up logging for standalone scripts with sensible defaults.

    This is a convenience function for scripts that want consistent logging
    without needing to call setup_logging() manually.

    Args:
        script_name: Name of the script (typically __name__ or script filename)
        verbose: Whether to enable DEBUG level logging

    Returns:
        Configured logger for the script

    Example:
        >>> logger = setup_script_logging(__name__, verbose=True)
        >>> logger.debug("Detailed debug information")
    """
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level=level, console=True, detailed=verbose)
    return get_logger(script_name)


class PipelineLogger:
    """Context manager for pipeline execution logging with progress tracking.

    Provides structured logging for multi-step pipelines with automatic
    timing and success/failure reporting.

    Example:
        >>> logger = get_logger(__name__)
        >>> with PipelineLogger(logger, "Data Collection", "goose") as pl:
        ...     pl.step("Fetching shows")
        ...     # do work
        ...     pl.step("Fetching setlists")
        ...     # do work
    """

    def __init__(self, logger: logging.Logger, operation: str, context: str = ""):
        """Initialize pipeline logger.

        Args:
            logger: Logger instance to use
            operation: Name of the operation (e.g., "Data Collection")
            context: Optional context info (e.g., band name)
        """
        self.logger = logger
        self.operation = operation
        self.context = f" [{context}]" if context else ""
        self.current_step: Optional[str] = None
        self.step_count = 0

    def __enter__(self) -> PipelineLogger:
        """Start the pipeline operation."""
        self.logger.info(f"🚀 Starting: {self.operation}{self.context}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Complete the pipeline operation."""
        if exc_type is None:
            self.logger.info(f"✅ Completed: {self.operation}{self.context}")
            return True
        else:
            self.logger.error(
                f"❌ Failed: {self.operation}{self.context} - {exc_type.__name__}: {exc_val}"
            )
            return False  # Re-raise the exception

    def step(self, description: str) -> None:
        """Log a pipeline step.

        Args:
            description: Description of the current step
        """
        self.step_count += 1
        self.current_step = description
        self.logger.info(f"  Step {self.step_count}: {description}")

    def progress(self, message: str) -> None:
        """Log progress within the current step.

        Args:
            message: Progress message
        """
        self.logger.debug(f"    → {message}")

    def warning(self, message: str) -> None:
        """Log a warning without failing the pipeline.

        Args:
            message: Warning message
        """
        self.logger.warning(f"  ⚠️  {message}")


# Configure basic logging on module import with sensible defaults
# This ensures logs are visible even if setup_logging() isn't called
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, format=DEFAULT_LOG_FORMAT, datefmt=DATE_FORMAT
    )
