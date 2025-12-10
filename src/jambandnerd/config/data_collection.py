"""Data collection and parsing configuration."""
from __future__ import annotations

from typing import Final

# Default chunk size for bulk database operations
DEFAULT_CHUNK_SIZE: Final[int] = 500

# Pagination chunk size for table fetching
FETCH_CHUNK_SIZE: Final[int] = 1000

# Date formats to try when parsing dates
DATE_FORMATS: Final[tuple[str, ...]] = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d-%m-%Y"
)
