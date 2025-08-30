"""Widespread Panic data collection package.

Provides data collection capabilities for Widespread Panic from 
everydaycompanion.com through web scraping. Includes comprehensive
HTML parsing, data validation, and robust error handling.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .collector import WSPCollector

__all__ = [
    "WSPCollector",
    "collector",
]
