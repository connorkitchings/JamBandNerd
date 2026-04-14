"""Widespread Panic data collection package.

Provides data collection capabilities for Widespread Panic from
everydaycompanion.com with Playwright-based Cloudflare bypass support.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .collector import WSPCollector

__all__ = [
    "WSPCollector",
    "collector",
]
