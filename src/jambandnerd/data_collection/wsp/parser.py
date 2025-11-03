"This module contains functions for parsing data from everydaycompanion.com."

import logging
from typing import Any, Dict, List

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def _validate_song_name(song_name: str) -> bool:
    """Validate that this looks like a real song name, not statistics or metadata."""
    if not song_name or len(song_name.strip()) == 0:
        return False

    # Skip very long entries (likely statistics) - tightened threshold
    if len(song_name) > 80:
        logger.debug(
            f"Rejecting long song name (>{len(song_name)} chars): {song_name[:50]}..."
        )
        return False

    # Enhanced statistics detection - more comprehensive patterns
    stats_indicators = [
        "Song Stats",
        "LTP Date",
        "L3TP",
        "#/10",
        "#/100",
        "#/Ever",
        "StatsSong",
        "Last Time Played",
        "Average of last",
        "LTPL3TP",
        "DateLTP",
        "LTP (Last Time Played)",
        "Number of shows since",
        "Number of times played",
        "Total number of times",
        "Average of last 3",
        # Common contamination patterns from actual data
        "ALONE 12/31/23",
        "BEAR 03/24/24",
        "APLANE 03/22/24",
    ]

    for indicator in stats_indicators:
        if indicator in song_name:
            logger.debug(f"Rejecting statistics entry: {song_name[:50]}...")
            return False

    # Reject entries that look like show headers or metadata
    if song_name.startswith(
        (
            "01/",
            "02/",
            "03/",
            "04/",
            "05/",
            "06/",
            "07/",
            "08/",
            "09/",
            "10/",
            "11/",
            "12/",
        )
    ):
        if "Hard Rock Hotel" in song_name or "Casino" in song_name:
            logger.debug(f"Rejecting show header: {song_name[:50]}...")
            return False

    # Reject entries with too many numbers/codes (likely statistics)
    import re

    if len(re.findall(r"\b\d+\b", song_name)) > 5:
        logger.debug(f"Rejecting numeric data: {song_name[:50]}...")
        return False

    return True

def parse_setlist_from_text(
    soup: BeautifulSoup,
    show_id: str
) -> List[Dict[str, Any]]:
    """Parse setlist directly from text content, looking for 0:, 1:, 2:, E: patterns."""
    setlist_data = []

    # Get all text and look for setlist lines
    page_text = soup.get_text()
    lines = page_text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Look for set indicators: "0:" (soundcheck), "1:", "2:", "E:", etc.
        if ":" in line and (
            line.startswith("0:")
            or line.startswith("1:")
            or line.startswith("2:")
            or line.startswith("3:")
            or line.startswith("E:")
            or line.startswith("Encore")
        ):
            # Extract set number
            if line.startswith("E:") or line.startswith("Encore"):
                set_number = "E"
                songs_part = (
                    line[2:].strip() if line.startswith("E:") else line[6:].strip()
                )
            elif line.startswith("0:"):
                set_number = "0"  # Soundcheck
                songs_part = line[2:].strip()
            else:
                set_number = line[0]
                songs_part = line[2:].strip()

            # Parse individual songs
            # Split by comma first, then handle segues (>)
            song_parts = songs_part.split(",")

            song_position = 1
            for song_part in song_parts:
                song_part = song_part.strip()
                if not song_part:
                    continue

                # Handle segues within a song part (e.g., "Song A > Song B")
                if '>' in song_part:
                    segued_songs = song_part.split('>')
                    for i, segued_song in enumerate(segued_songs):
                        segued_song = segued_song.strip().rstrip('*').strip()
                        if segued_song and _validate_song_name(segued_song):
                            setlist_data.append({
                                "show_id": show_id,
                                "set_number": set_number,
                                "song_position": song_position,
                                "song_name": segued_song,
                                "is_segue": i < len(segued_songs) - 1,  # All but last are segues
                                "song_notes": ""
                            })
                            song_position += 1
                else:
                    # Regular song
                    song_name = song_part.rstrip('*').strip()
                    if _validate_song_name(song_name):
                        setlist_data.append({
                            "show_id": show_id,
                            "set_number": set_number,
                            "song_position": song_position,
                            "song_name": song_name,
                            "is_segue": False,
                            "song_notes": ""
                        })
                        song_position += 1

    return setlist_data
