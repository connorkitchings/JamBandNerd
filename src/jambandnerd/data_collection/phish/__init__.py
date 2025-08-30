"""Phish data collection package.

Provides data collection capabilities for Phish from the phish.net API.
Includes shows, setlists, songs, and venue data with API key authentication
and sophisticated error handling.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .collector import PhishCollector

__all__ = [
    "PhishCollector",
    "collector",
]
