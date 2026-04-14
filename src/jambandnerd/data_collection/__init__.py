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
- cache: Disk-based HTTP response caching with TTL support
- config: Band-specific configuration management
- utils: Shared collection helpers such as source hashing and run timers
- browser: Playwright-based Cloudflare bypass for protected sources
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BandCollector, CollectorConfig
    from .billy.collector import BillyCollector
    from .eggy.collector import EggyCollector
    from .goose.collector import GooseCollector
    from .phish.collector import PhishCollector
    from .um.collector import UmCollector
    from .wsp.collector import WSPCollector

__all__ = [
    "BandCollector",
    "CollectorConfig",
    "GooseCollector",
    "EggyCollector",
    "PhishCollector",
    "WSPCollector",
    "BillyCollector",
    "UmCollector",
    "goose",
    "eggy",
    "phish",
    "wsp",
    "billy",
    "um",
    "base",
    "browser",
    "cache",
    "config",
    "utils",
]
