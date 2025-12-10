"""Web interface (Streamlit) configuration."""
from __future__ import annotations

from typing import Final

# Cache TTL for Streamlit data fetching (seconds)
STREAMLIT_CACHE_TTL: Final[int] = 60

# Long-lived cache TTL for less frequently changing data (seconds)
STREAMLIT_CACHE_TTL_LONG: Final[int] = 300

# Show dates to exclude from predictions (bad data, test shows, etc.)
EXCLUDED_SHOW_DATES: Final[set[str]] = {"2025-08-13"}

# Maximum number of recent shows to consider for accuracy charts
MAX_ACCURACY_SHOWS: Final[int] = 100
