"""
Centralized logging configuration for the JamBandNerd project.
"""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger with a standardized format.

    Args:
        name (str): The name for the logger, typically __name__.

    Returns:
        logging.Logger: An initialized logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
