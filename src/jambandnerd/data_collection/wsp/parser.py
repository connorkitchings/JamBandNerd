"""Helpers for parsing WSP setlists from everydaycompanion.com HTML."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Sequence

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

STAT_PATTERNS: Sequence[str] = (
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
    "ALONE 12/31/23",
    "BEAR 03/24/24",
    "APLANE 03/22/24",
)

SONGS_WITH_COMMAS: Sequence[str] = (
    "Baby, Let Me Follow You Down",
    "Baby, Let Me Hold Your Hand",
    "Lawyers, Guns, And Money",
    "Baby, Please Don't Go",
    "Weak Brain, Narrow Mind",
    "Man Smart, Woman Smarter",
    "Shake, Rattle, And Roll",
)

COMMA_PLACEHOLDER = "||COMMA||"

IGNORE_PATTERNS = [
    re.compile(r"Copyright\s+\xa9", re.IGNORECASE),
    re.compile(r"Additions/Comments\s+to:", re.IGNORECASE),
    re.compile(r"previous\s+show\s+\(", re.IGNORECASE),
    re.compile(r"next\s+show\s+\(", re.IGNORECASE),
    re.compile(r"Songs\s+By\s+Album", re.IGNORECASE),
    re.compile(r"Listen\s+at\s+Relisten", re.IGNORECASE),
    re.compile(r"Words/Music:", re.IGNORECASE),
    re.compile(r"Original\s+by:", re.IGNORECASE),
    re.compile(r"Credit:", re.IGNORECASE),
    re.compile(r"Vocal:", re.IGNORECASE),
    re.compile(r"^[\[\(][A-Z]{2,3}:", re.IGNORECASE),
]

SETLIST_REGEX = re.compile(
    r"(?:<b[^>]*>)?\s*(?P<label>\d+|E\d?|Encore(?:\s*\d+)?)\s*:\s*(?:</b>)?\s*(?P<songs>[^<]+)",
    flags=re.IGNORECASE,
)


def _validate_song_name(song_name: str) -> bool:
    """Validate that a token looks like a real song title, not page metadata."""
    if not song_name or len(song_name.strip()) == 0:
        return False

    if len(song_name) > 80:
        logger.debug("Rejecting long song token: %s...", song_name[:50])
        return False

    upper_name = song_name.upper()
    if any(pattern.upper() in upper_name for pattern in STAT_PATTERNS):
        logger.debug("Rejecting statistics token: %s...", song_name[:50])
        return False

    if "SOUNDCHECK" in upper_name and "JAM" not in upper_name:
        return False

    if upper_name.startswith(tuple(f"{month:02d}/" for month in range(1, 13))):
        logger.debug("Rejecting show-header token: %s...", song_name[:50])
        return False

    if len(re.findall(r"\b\d+\b", song_name)) > 5:
        logger.debug("Rejecting numeric token: %s...", song_name[:50])
        return False

    return True


def _protect_commas(text: str) -> str:
    protected = text
    for song in SONGS_WITH_COMMAS:
        protected = protected.replace(song, song.replace(",", COMMA_PLACEHOLDER))
    return protected


def _restore_commas(text: str) -> str:
    return text.replace(COMMA_PLACEHOLDER, ",")


def _normalize_set_label(raw_label: str) -> str:
    label = raw_label.upper().strip()
    if label == "0":
        return "1"
    if label in {"E", "ENCORE", "E1", "ENCORE 1", "ENCORE1"}:
        return "E"
    if re.fullmatch(r"E\d", label):
        return label
    encore_match = re.fullmatch(r"ENCORE\s*(\d+)", label)
    if encore_match:
        encore_num = encore_match.group(1)
        return "E" if encore_num == "1" else f"E{encore_num}"
    return label


def _normalize_song(song_text: str) -> tuple[str, bool]:
    stripped = song_text.strip()
    segue = stripped.endswith((">", "»"))
    if segue:
        stripped = stripped[:-1].strip()
    return stripped, segue


def _extract_marker(text: str) -> tuple[str, str | None]:
    bracketed_match = re.search(r"\s*\[(\d+)\]$", text)
    if bracketed_match:
        return text[: bracketed_match.start()].strip(), bracketed_match.group(1)

    if text.endswith("*"):
        asterisk_count = len(text) - len(text.rstrip("*"))
        marker = "*" * asterisk_count
        return text.rstrip("*").strip(), marker

    return text, None


def _append_song_entries(
    setlist_data: List[Dict[str, Any]],
    *,
    show_id: str,
    set_label: str,
    songs_part: str,
    notes_map: dict[str, str],
) -> None:
    protected = _protect_commas(songs_part)
    song_position = (
        max(
            (
                entry["song_position"]
                for entry in setlist_data
                if entry["set_number"] == set_label
            ),
            default=0,
        )
        + 1
    )

    for chunk in protected.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue

        normalized_chunk = (
            chunk.replace("->", ">").replace("→", ">").replace("&gt;", ">")
        )
        sub_songs = [
            segment.strip()
            for segment in normalized_chunk.split(">")
            if segment.strip()
        ]

        for idx, song_text in enumerate(sub_songs):
            song_text = _restore_commas(song_text)
            normalized_title, explicit_segue = _normalize_song(song_text)
            title, marker = _extract_marker(normalized_title)
            if not _validate_song_name(title):
                continue

            song_notes = notes_map.get(marker or "", "")
            setlist_data.append(
                {
                    "show_id": show_id,
                    "set_number": set_label,
                    "song_position": song_position,
                    "song_name": title,
                    "is_segue": explicit_segue or idx < len(sub_songs) - 1,
                    "song_notes": song_notes,
                }
            )
            song_position += 1


def _extract_notes_map(soup: BeautifulSoup) -> tuple[dict[str, str], list[str]]:
    notes_map: dict[str, str] = {}
    ordered_notes: list[str] = []
    split_pattern = re.compile(r"(\*+|\[\d+\]|\[(?!\d+\])[^]]+\])")
    set_pattern = re.compile(
        r"^(0:|1:|2:|3:|4:|E:|E1:|E2:|E3:|Encore(?:\s*\d+)?:)",
        re.IGNORECASE,
    )

    for tag in soup.find_all(["p", "font"]):
        tag_text = tag.get_text(strip=True)
        if not tag_text:
            continue
        if set_pattern.match(tag_text):
            continue
        if not split_pattern.search(tag_text):
            continue
        if any(pattern.search(tag_text) for pattern in IGNORE_PATTERNS):
            continue

        tokens = split_pattern.split(tag_text)
        current_marker: str | None = None
        for token in tokens:
            if not token or not token.strip():
                continue
            token = token.strip()

            if re.fullmatch(r"\*+", token):
                current_marker = token
                continue
            if re.fullmatch(r"\[\d+\]", token):
                current_marker = token.strip("[]")
                continue
            if re.fullmatch(r"\[(?!\d+\])[^]]+\]", token):
                ordered_notes.append(token)
                current_marker = None
                continue

            if current_marker:
                notes_map[current_marker] = token
                if current_marker.isdigit():
                    ordered_notes.append(f"[{current_marker}] {token}")
                else:
                    ordered_notes.append(f"{current_marker} {token}")
                current_marker = None
            elif len(token) > 2:
                ordered_notes.append(token)

    return notes_map, ordered_notes


def _parse_table_style_setlist(
    soup: BeautifulSoup, show_id: str
) -> tuple[List[Dict[str, Any]], list[str]]:
    html = soup.decode()
    notes_map, ordered_notes = _extract_notes_map(soup)
    setlist_data: List[Dict[str, Any]] = []

    for match in SETLIST_REGEX.finditer(html):
        set_label = _normalize_set_label(match.group("label"))
        songs_part = match.group("songs")
        if any(pattern.upper() in songs_part.upper() for pattern in STAT_PATTERNS):
            continue
        _append_song_entries(
            setlist_data,
            show_id=show_id,
            set_label=set_label,
            songs_part=songs_part,
            notes_map=notes_map,
        )

    return setlist_data, ordered_notes


def _parse_legacy_paragraph_setlist(
    soup: BeautifulSoup, show_id: str
) -> tuple[List[Dict[str, Any]], list[str]]:
    notes_map: dict[str, str] = {}
    ordered_notes: list[str] = []
    setlist_data: List[Dict[str, Any]] = []

    set_pattern = re.compile(
        r"^(0:|1:|2:|3:|E:|E1:|E2:|E3:|Encore(?:\s*\d+)?:)",
        re.IGNORECASE,
    )
    note_pattern = re.compile(r"^((\*+)|\[(\d+)\])\s+(.+)")

    for p_tag in soup.find_all("p"):
        tag_text = p_tag.get_text(strip=True)
        if not tag_text:
            continue

        if set_pattern.match(tag_text) and ":" in tag_text:
            label_part, songs_part = tag_text.split(":", 1)
            set_label = _normalize_set_label(label_part)
            _append_song_entries(
                setlist_data,
                show_id=show_id,
                set_label=set_label,
                songs_part=songs_part,
                notes_map=notes_map,
            )
            continue

        if any(pattern.search(tag_text) for pattern in IGNORE_PATTERNS):
            continue

        note_match = note_pattern.match(tag_text)
        if note_match:
            marker = note_match.group(3) if note_match.group(3) else note_match.group(2)
            body = note_match.group(4)
            notes_map[marker] = body
            ordered_notes.append(
                f"[{marker}] {body}" if note_match.group(3) else f"{marker} {body}"
            )
            continue

        general_note_match = re.match(r"^\[(?!\d+\])([^]]+)\]\s*(.*)", tag_text)
        if general_note_match:
            ordered_notes.append(tag_text)

    for entry in setlist_data:
        marker_match = re.search(r"(\*+|\[\d+\])$", entry["song_name"])
        if marker_match:
            marker = marker_match.group(1).strip("[]")
            entry["song_name"] = entry["song_name"][: marker_match.start()].strip()
            entry["song_notes"] = notes_map.get(marker, "")

    return setlist_data, ordered_notes


def parse_setlist_from_text(soup: BeautifulSoup, show_id: str) -> List[Dict[str, Any]]:
    """Parse a WSP EC setlist from the page HTML into collector row dictionaries."""
    parsed_table, _ = _parse_table_style_setlist(soup, show_id)
    if parsed_table:
        return parsed_table

    parsed_legacy, _ = _parse_legacy_paragraph_setlist(soup, show_id)
    return parsed_legacy


def parsed_output_has_fragmented_comma_titles(
    parsed_rows: Sequence[Dict[str, Any]], page_text: str
) -> bool:
    """Detect when a comma-titled song was split into fragments by the parser."""
    parsed_names = [str(row.get("song_name", "")).strip() for row in parsed_rows]
    lower_page_text = page_text.lower()

    for full_title in SONGS_WITH_COMMAS:
        if full_title.lower() not in lower_page_text:
            continue
        if full_title in parsed_names:
            continue

        fragments = [fragment.strip() for fragment in full_title.split(",")]
        for start_index in range(0, len(parsed_names) - len(fragments) + 1):
            if parsed_names[start_index : start_index + len(fragments)] == fragments:
                return True

    return False
