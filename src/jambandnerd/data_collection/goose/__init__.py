"""Goose data collection package.

Provides data collection capabilities for Goose from the elgoose.net API.
Includes shows, setlists, songs, and venue data with comprehensive
error handling and rate limiting.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .collector import GooseCollector

__all__ = [
    "GooseCollector",
    "collector",
]
