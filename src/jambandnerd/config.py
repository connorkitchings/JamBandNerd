"""Centralized configuration for JamBandNerd.

This module contains all global configuration constants and settings used
throughout the application to avoid magic numbers and hardcoded values.
"""
from __future__ import annotations

from typing import Final

# ==================== Model Configuration ====================

# Top-K values for accuracy evaluation
TOP_K_VALUES: Final[list[int]] = [10, 25, 50]

# Default number of recent shows to exclude songs from predictions
EXCLUSION_WINDOW_DEFAULT: Final[int] = 3

# Band-specific exclusion windows (overrides default)
BAND_EXCLUSION_WINDOWS: Final[dict[str, int]] = {
    "um": 4,  # UM uses 4-show exclusion window instead of default 3
}

# Minimum number of plays required for a song to be considered by CK+ model
MIN_PLAYS_THRESHOLD_DEFAULT: Final[int] = 5

# Alpha parameter for CK+ model (weight for gap ratio vs z-score)
CKPLUS_ALPHA_DEFAULT: Final[float] = 0.7

# Retirement gap thresholds by band (shows without a play before considered "retired")
RETIREMENT_GAPS: Final[dict[str, int]] = {
    "goose": 100,   # Smaller gap for a band with more regular rotation
    "eggy": 120,    # Smaller catalog but still rotating regularly
    "phish": 150,   # Larger gap for a band with deeper catalog
    "wsp": 150,     # Similar to Phish
    "billy": 150,
    "um": 150,
    "default": 250  # Safe fallback for other bands
}

# ==================== Data Collection Configuration ====================

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

# ==================== Band-Specific Configuration ====================

# Supported bands
SUPPORTED_BANDS: Final[tuple[str, ...]] = ("goose", "eggy", "phish", "wsp", "billy", "um")

# Band display names
BAND_DISPLAY_NAMES: Final[dict[str, str]] = {
    "goose": "Goose",
    "eggy": "Eggy",
    "phish": "Phish",
    "wsp": "Widespread Panic",
    "billy": "Billy Strings",
    "um": "Umphrey's McGee",
}

# Primary key column names by band (for ID normalization)
BAND_ID_COLUMNS: Final[dict[str, str]] = {
    "goose": "show_id",
    "eggy": "show_id",
    "phish": "api_show_id",
    "wsp": "show_id",
    "billy": "show_id",
    "um": "show_id",
}

# Songs to exclude from predictions (noise, not actual songs)
EXCLUDED_SONGS: Final[dict[str, list[str]]] = {
    "wsp": [
        "jam",
        "drums",
        "David Bromberg Band",
        "New Riders of the Purple Sage",
        "J.J. Cale",
        "The Doors",
    ],  # WSP-specific exclusions
    "goose": [],
    "eggy": [],
    "phish": [],
    "billy": [],
    "um": [],
}

# ==================== Web Interface Configuration ====================

# Cache TTL for Streamlit data fetching (seconds)
STREAMLIT_CACHE_TTL: Final[int] = 60

# Long-lived cache TTL for less frequently changing data (seconds)
STREAMLIT_CACHE_TTL_LONG: Final[int] = 300

# Show dates to exclude from predictions (bad data, test shows, etc.)
EXCLUDED_SHOW_DATES: Final[set[str]] = {"2025-08-13"}

# Maximum number of recent shows to consider for accuracy charts
MAX_ACCURACY_SHOWS: Final[int] = 100

# ==================== Pipeline Configuration ====================

# Default timeout for HTTP requests (seconds)
DEFAULT_REQUEST_TIMEOUT: Final[int] = 30

# Maximum retries for failed operations
MAX_RETRIES: Final[int] = 3

# Backoff factor for exponential retry delays
BACKOFF_FACTOR: Final[float] = 2.0

# ==================== Database Configuration ====================

# Tables suffix for raw data
RAW_TABLE_SUFFIX: Final[str] = "_raw"

# Unified prediction table names
PREDICTION_TABLES: Final[dict[str, str]] = {
    "notebook": "predictions_notebook",
    "ckplus": "predictions_ckplus"
}

# Unified accuracy table names
ACCURACY_TABLES: Final[dict[str, str]] = {
    "notebook": "notebook_accuracy",
    "ckplus": "accuracy_ckplus",
    "per_show": "accuracy_per_show"
}

# Model version identifiers
MODEL_VERSIONS: Final[dict[str, str]] = {
    "notebook": "notebook_v1",
    "ckplus": "ckplus_v1"
}
MODEL_VERSIONS: Final[dict[str, str]] = {
    "notebook": "notebook_v1",
    "ckplus": "ckplus_v1"
}

