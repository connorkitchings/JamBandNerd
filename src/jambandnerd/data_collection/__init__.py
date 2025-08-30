"""Data collection package for band-specific collectors and utilities.

This package provides abstract base classes and concrete implementations for
collecting data from various jam band APIs and websites.

Supported bands:
- goose: Goose data from elgoose.net API
- phish: Phish data from phish.net API  
- wsp: Widespread Panic data from everydaycompanion.com

Core components:
- base: Abstract BandCollector base class with rate limiting and error handling
- config: Band-specific configuration management
- collect_data: Enhanced collection manager with comprehensive error handling
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BandCollector, CollectorConfig
    from .goose.collector import GooseCollector
    from .phish.collector import PhishCollector
    from .wsp.collector import WSPCollector

__all__ = [
    "BandCollector",
    "CollectorConfig", 
    "GooseCollector",
    "PhishCollector",
    "WSPCollector",
    "goose",
    "phish",
    "wsp",
    "base",
    "config",
    "collect_data",
]



