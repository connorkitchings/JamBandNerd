"""Band-specific configuration."""

from __future__ import annotations

from typing import Final

# Supported bands
SUPPORTED_BANDS: Final[tuple[str, ...]] = (
    "goose",
    "eggy",
    "phish",
    "wsp",
    "billy",
    "um",
)

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
