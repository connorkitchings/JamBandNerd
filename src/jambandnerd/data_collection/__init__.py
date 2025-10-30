"""Data collection package for band-specific collectors and utilities.

This package provides abstract base classes and concrete implementations for
collecting data from various jam band APIs and websites.

Supported bands:
- goose: Goose data from elgoose.net API
- eggy: Eggy data from thecarton.net API
- phish: Phish data from phish.net API
- wsp: Widespread Panic data from everydaycompanion.com
- billy: Billy Strings data from bmfsdb.com
- um: Umphrey's McGee data from allthings.umphreys.com

Core components:
- base: Abstract BandCollector base class with rate limiting and error handling
- config: Band-specific configuration management
- collect_data: Enhanced collection manager with comprehensive error handling
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BandCollector, CollectorConfig
    from .goose.collector import GooseCollector
    from .eggy.collector import EggyCollector
    from .phish.collector import PhishCollector
    from .wsp.collector import WSPCollector
    from .billy.collector import BillyCollector
    from .um.collector import UmCollector
    from .cosmic.collector import CosmicCollector

__all__ = [
    "BandCollector",
    "CollectorConfig",
    "GooseCollector",
    "EggyCollector",
    "PhishCollector",
    "WSPCollector",
    "BillyCollector",
    "UmCollector",
    "CosmicCollector",
    "goose",
    "eggy",
    "phish",
    "wsp",
    "billy",
    "um",
    "cosmic",
    "base",
    "config",
    "collect_data",
]
