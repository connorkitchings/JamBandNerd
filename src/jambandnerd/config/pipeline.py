"""Pipeline and orchestration configuration."""

from __future__ import annotations

from typing import Final

# Default timeout for HTTP requests (seconds)
DEFAULT_REQUEST_TIMEOUT: Final[int] = 30

# Maximum retries for failed operations
MAX_RETRIES: Final[int] = 3

# Backoff factor for exponential retry delays
BACKOFF_FACTOR: Final[float] = 2.0
