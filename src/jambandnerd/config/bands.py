"""Band-specific configuration."""

from __future__ import annotations

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


def get_active_bands() -> Sequence[str]:
    """Get active bands from the DB registry, falling back to static config."""
    global _cached_active_bands
    if _cached_active_bands is not None:
        return _cached_active_bands

    try:
        from src.jambandnerd.db.operations import fetch_active_bands

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
            from src.jambandnerd.db.operations import fetch_active_bands

            db_bands = fetch_active_bands()
            if db_bands:
                _cached_band_id_columns = {b["slug"]: b["id_column"] for b in db_bands}
            else:
                _cached_band_id_columns = dict(BAND_ID_COLUMNS)
        except ImportError:
            _cached_band_id_columns = dict(BAND_ID_COLUMNS)

    return _cached_band_id_columns.get(band, BAND_ID_COLUMNS.get(band, "show_id"))


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


def get_excluded_songs(band: str) -> frozenset[str]:
    """Get case-insensitive excluded songs for a band.

    Args:
        band: Band name

    Returns:
        Frozenset of lowercase song names to exclude
    """
    return EXCLUDED_SONGS_LOWER.get(band, frozenset())
