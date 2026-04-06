"""Band-specific configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Sequence

# Supported bands (Fallback)
SUPPORTED_BANDS: Final[tuple[str, ...]] = (
    "goose",
    "eggy",
    "phish",
    "wsp",
    "billy",
    "um",
)

# Band display names (Fallback)
BAND_DISPLAY_NAMES: Final[dict[str, str]] = {
    "goose": "Goose",
    "eggy": "Eggy",
    "phish": "Phish",
    "wsp": "Widespread Panic",
    "billy": "Billy Strings",
    "um": "Umphrey's McGee",
}

# Primary key column names by band (Fallback)
BAND_ID_COLUMNS: Final[dict[str, str]] = {
    "goose": "show_id",
    "eggy": "show_id",
    "phish": "api_show_id",
    "wsp": "show_id",
    "billy": "show_id",
    "um": "show_id",
}

# In-memory cache for dynamic registry
_cached_active_bands: list[str] | None = None
_cached_band_id_columns: dict[str, str] | None = None


@dataclass(frozen=True)
class CollectionPolicy:
    """Policy for how a band's daily ingestion should behave."""

    collection_mode: str
    rolling_window_days: int | None = None
    upcoming_lookahead_days: int = 14
    supports_upstream_update_timestamp: bool = False
    skip_existing_setlists: bool = False
    allows_verify_only_when_idle: bool = False


COLLECTION_POLICIES: Final[dict[str, CollectionPolicy]] = {
    "goose": CollectionPolicy(
        collection_mode="always_refresh",
        supports_upstream_update_timestamp=False,
    ),
    "eggy": CollectionPolicy(
        collection_mode="always_refresh",
        supports_upstream_update_timestamp=True,
    ),
    "phish": CollectionPolicy(
        collection_mode="window_refresh",
        rolling_window_days=730,
        supports_upstream_update_timestamp=True,
        skip_existing_setlists=False,
    ),
    "wsp": CollectionPolicy(
        collection_mode="window_refresh",
        rolling_window_days=730,
        skip_existing_setlists=True,
    ),
    "billy": CollectionPolicy(
        collection_mode="window_refresh",
        rolling_window_days=60,
        skip_existing_setlists=True,
    ),
    "um": CollectionPolicy(
        collection_mode="window_refresh",
        rolling_window_days=730,
        skip_existing_setlists=True,
    ),
}


def get_active_bands() -> Sequence[str]:
    """Get active bands from the DB registry, falling back to static config."""
    global _cached_active_bands
    if _cached_active_bands is not None:
        return _cached_active_bands

    try:
        from jambandnerd.db.operations import fetch_active_bands

        db_bands = fetch_active_bands()
        if db_bands:
            _cached_active_bands = [b["slug"] for b in db_bands]
            return _cached_active_bands
    except ImportError:
        pass

    return SUPPORTED_BANDS


def get_band_id_column(band: str) -> str:
    """Get the primary key column name for a band from the DB registry."""
    global _cached_band_id_columns
    if _cached_band_id_columns is None:
        try:
            from jambandnerd.db.operations import fetch_active_bands

            db_bands = fetch_active_bands()
            if db_bands:
                _cached_band_id_columns = {b["slug"]: b["id_column"] for b in db_bands}
            else:
                _cached_band_id_columns = dict(BAND_ID_COLUMNS)
        except ImportError:
            _cached_band_id_columns = dict(BAND_ID_COLUMNS)

    return _cached_band_id_columns.get(band, BAND_ID_COLUMNS.get(band, "show_id"))


def get_collection_policy(band: str) -> CollectionPolicy:
    """Get the collection policy for a band."""
    return COLLECTION_POLICIES.get(
        band,
        CollectionPolicy(collection_mode="always_refresh"),
    )


# Songs to exclude from predictions (noise, not actual songs)
EXCLUDED_SONGS: Final[dict[str, list[str]]] = {
    "wsp": [
        "jam",
        "drums",
        "David Bromberg Band",
        "New Riders of the Purple Sage",
        "J.J. Cale",
        "The Doors",
    ],
    "goose": [],
    "eggy": [],
    "phish": [],
    "billy": [],
    "um": [],
}

# Case-insensitive excluded songs for faster lookup
EXCLUDED_SONGS_LOWER: Final[dict[str, frozenset[str]]] = {
    band: frozenset(song.lower().strip() for song in songs)
    for band, songs in EXCLUDED_SONGS.items()
}

# Show dates to exclude from prediction/backtest windows.
# Prefer EXCLUDED_PREDICTION_SHOW_IDS when a date has multiple shows and only
# some should be excluded.
EXCLUDED_PREDICTION_SHOW_DATES: Final[dict[str, list[str]]] = {
    "goose": [],
    "eggy": [],
    "phish": [],
    "wsp": [],
    "billy": [],
    "um": [],
}

EXCLUDED_PREDICTION_SHOW_DATES_SET: Final[dict[str, frozenset[str]]] = {
    band: frozenset(date_str.strip() for date_str in dates)
    for band, dates in EXCLUDED_PREDICTION_SHOW_DATES.items()
}

# Show IDs to exclude from prediction/backtest windows. Prefer this over
# date-based exclusions when a date has multiple shows and only some should
# be excluded (e.g., a festival promo set on the same day as a full show).
EXCLUDED_PREDICTION_SHOW_IDS: Final[dict[str, list[str]]] = {
    "goose": [
        "1755099318",  # 2025-08-13 TV appearance
        "1748090458",  # 2025-05-25 Napa short set (4 songs; full show same day)
        "1745685585",  # 2025-04-25 short set (3 songs)
        "1741108426",  # 2025-03-11 promo (1 song)
        "1730168333",  # 2024-11-24 MSG short set (5 songs)
    ],
    "eggy": [],
    "phish": [],
    "wsp": [],
    "billy": [],
    "um": [],
}

EXCLUDED_PREDICTION_SHOW_IDS_SET: Final[dict[str, frozenset[str]]] = {
    band: frozenset(str(sid).strip() for sid in ids)
    for band, ids in EXCLUDED_PREDICTION_SHOW_IDS.items()
}


def get_excluded_songs(band: str) -> frozenset[str]:
    """Get case-insensitive excluded songs for a band.

    Args:
        band: Band name

    Returns:
        Frozenset of lowercase song names to exclude
    """
    return EXCLUDED_SONGS_LOWER.get(band, frozenset())


def get_excluded_prediction_show_dates(band: str) -> frozenset[str]:
    """Get ISO show dates that should be excluded from prediction windows."""
    return EXCLUDED_PREDICTION_SHOW_DATES_SET.get(band, frozenset())


def get_excluded_prediction_show_ids(band: str) -> frozenset[str]:
    """Get show IDs that should be excluded from prediction windows."""
    return EXCLUDED_PREDICTION_SHOW_IDS_SET.get(band, frozenset())
