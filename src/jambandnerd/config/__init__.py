"""Centralized configuration package for JamBandNerd.

This package consolidates all global configuration constants from its modules,
making them accessible from a single entry point. This approach allows for
organized, domain-specific configuration files while maintaining a simple
import path for consumers.

Example:
    from jambandnerd.config import SUPPORTED_BANDS, TOP_K_VALUES
"""

from __future__ import annotations

from .bands import BAND_DISPLAY_NAMES, BAND_ID_COLUMNS, EXCLUDED_SONGS, SUPPORTED_BANDS
from .data_collection import DATE_FORMATS, DEFAULT_CHUNK_SIZE, FETCH_CHUNK_SIZE
from .database import ACCURACY_TABLES, PREDICTION_TABLES, RAW_TABLE_SUFFIX
from .models import (
    BAND_EXCLUSION_WINDOWS,
    CKPLUS_ALPHA_DEFAULT,
    EXCLUSION_WINDOW_DEFAULT,
    MIN_PLAYS_THRESHOLD_DEFAULT,
    MODEL_VERSIONS,
    RETIREMENT_GAPS,
    TOP_K_VALUES,
)
from .pipeline import BACKOFF_FACTOR, DEFAULT_REQUEST_TIMEOUT, MAX_RETRIES
from .web import (
    EXCLUDED_SHOW_DATES,
    MAX_ACCURACY_SHOWS,
    STREAMLIT_CACHE_TTL,
    STREAMLIT_CACHE_TTL_LONG,
)

__all__ = [
    # bands.py
    "SUPPORTED_BANDS",
    "BAND_DISPLAY_NAMES",
    "BAND_ID_COLUMNS",
    "EXCLUDED_SONGS",
    # data_collection.py
    "DEFAULT_CHUNK_SIZE",
    "FETCH_CHUNK_SIZE",
    "DATE_FORMATS",
    # database.py
    "RAW_TABLE_SUFFIX",
    "PREDICTION_TABLES",
    "ACCURACY_TABLES",
    # models.py
    "TOP_K_VALUES",
    "EXCLUSION_WINDOW_DEFAULT",
    "BAND_EXCLUSION_WINDOWS",
    "MIN_PLAYS_THRESHOLD_DEFAULT",
    "CKPLUS_ALPHA_DEFAULT",
    "RETIREMENT_GAPS",
    "MODEL_VERSIONS",
    # pipeline.py
    "DEFAULT_REQUEST_TIMEOUT",
    "MAX_RETRIES",
    "BACKOFF_FACTOR",
    # web.py
    "STREAMLIT_CACHE_TTL",
    "STREAMLIT_CACHE_TTL_LONG",
    "EXCLUDED_SHOW_DATES",
    "MAX_ACCURACY_SHOWS",
]
