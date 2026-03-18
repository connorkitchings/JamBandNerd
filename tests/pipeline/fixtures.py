from __future__ import annotations

from datetime import date, timedelta
from typing import Any

BANDS = ("goose", "eggy", "phish", "wsp", "billy", "um")


def band_raw_tables(band: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], date]:
    """Return minimal but realistic raw rows for a band's transform path."""

    if band not in BANDS:
        raise ValueError(f"Unsupported band fixture: {band}")

    reference_date = date(2024, 4, 1)
    historical_dates = [
        reference_date - timedelta(days=91),
        reference_date - timedelta(days=77),
        reference_date - timedelta(days=60),
        reference_date - timedelta(days=45),
        reference_date - timedelta(days=31),
        reference_date - timedelta(days=14),
    ]

    raw_show_ids = [f"{band}-show-{index}" for index in range(1, 8)]
    show_id_key = "api_show_id" if band == "phish" else "show_id"

    shows_raw: list[dict[str, Any]] = []
    for index, show_date in enumerate(historical_dates, start=1):
        shows_raw.append(
            {
                show_id_key: raw_show_ids[index - 1],
                "show_date": show_date.isoformat(),
                "venue_name": f"{band.title()} Venue {index}",
            }
        )

    shows_raw.append(
        {
            show_id_key: raw_show_ids[-1],
            "show_date": reference_date.isoformat(),
            "venue_name": f"{band.title()} Future Venue",
        }
    )

    setlists_raw = [
        {show_id_key: raw_show_ids[0], "song_name": "Song A"},
        {show_id_key: raw_show_ids[0], "song_name": "Song B"},
        {show_id_key: raw_show_ids[1], "song_name": "Song A"},
        {show_id_key: raw_show_ids[1], "song_name": "Song C"},
        {show_id_key: raw_show_ids[2], "song_name": "Song D"},
        {show_id_key: raw_show_ids[2], "song_name": "Song E"},
        {show_id_key: raw_show_ids[3], "song_name": "Song F"},
        {show_id_key: raw_show_ids[3], "song_name": "Song G"},
        {show_id_key: raw_show_ids[4], "song_name": "Song H"},
        {show_id_key: raw_show_ids[4], "song_name": "Song I"},
        {show_id_key: raw_show_ids[5], "song_name": "Song J"},
        {show_id_key: raw_show_ids[5], "song_name": "Song K"},
        {show_id_key: raw_show_ids[6], "song_name": "Future Song"},
    ]

    return shows_raw, setlists_raw, reference_date
