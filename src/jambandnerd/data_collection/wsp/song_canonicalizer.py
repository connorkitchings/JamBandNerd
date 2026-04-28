"""Centralized WSP song name canonicalization.

Normalizes song names from all WSP data sources (Everyday Companion,
PanicStream, TourWrangler) to the canonical forms recorded on the
Everyday Companion song catalog (songcode.asp).

The canonicalizer uses a hybrid approach:
  1. A static alias map covers punctuation variants and known aka entries.
  2. A dynamic lookup (built from wsp_songs_raw) provides exact-match
     validation against the live EC catalog.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

CANONICAL_SONG_ALIASES: dict[str, str] = {
    "c brown": "C. Brown",
    "c.brown": "C. Brown",
    "c. brown": "C. Brown",
    "mr soul": "Mr. Soul",
    "mr. soul": "Mr. Soul",
    "mr crowley": "Mr. Crowley",
    "mr. crowley": "Mr. Crowley",
    "walkin'": "Walkin' (For Your Love)",
    "walkin": "Walkin' (For Your Love)",
    "plains hopping": "Walkin' (For Your Love)",
    "bowlegged woman knock kneed man": "Bowlegged Woman",
    "bowlegged woman, knock kneed man": "Bowlegged Woman",
    "knock kneed man": "Bowlegged Woman",
    "bowlegged woman": "Bowlegged Woman",
    "coconut image": "Coconut",
    "older souls": "Holden Oversoul",
    "moon time": "Porch Song",
    "panic's theme": "Porch Song",
    "kiss on tuesday": "Gimme",
    "micheal": "Gimme",
    "pilgrim radio": "Pilgrims",
    "brass shoes walking blues": "Rock",
    "untitled instrumental 2": "Bear's Gone Fishin'",
    "a hog's eternity": "Pigeons",
    "feeling lucky": "The Big Lagoon",
    "eliza's apartment": "L.a.",
    "liza's apartment": "L.a.",
    "geraldine": "Geraldine And The Honeybee",
    "i told her i'd be ready": "I Told Her I'd Be Early",
    "turn on your lovelight": "Turn On Your Love Light",
    "drug deal": "Proving Ground",
    "big sex": "Proving Ground",
    "naked in the mud": "Tall Boy",
    "blue girl": "Little Lilly",
    "first snow": "Little Lilly",
    "that thang": "Paymh",
    "untitled instrumental": "Paymh",
    "mellow jam": "West Virginia",
    "storm watch": "Disco",
    "tacos are cheap but pizza is expensive": "Tacos",
    "schoolgirl": "Good Morning Little Schoolgirl",
    "bookends": "Stop-Go",
    "seen your sister naked": "Ribs And Whiskey",
    "burned faceless": "Smoke And Burn",
    "eating the beat": "A of D",
    "morning daydream": "A of D",
    "giving": "B of D",
    "worried": "Worry",
    "worryin'": "Worry",
    "worries": "Worry",
    "worryin": "Worry",
    "worryin' about my worries": "Worry",
    "junko partner": "Junco Partner",
    "i believe my baby's gone": "I Wish You Would",
    "my baby's gone": "I Wish You Would",
    "baby come back": "I Wish You Would",
    "minglewood blues": "New Minglewood Blues",
    "st. louis": "St. Louis",
    "st louis": "St. Louis",
    "i got my way": "You Got Yours",
    "it's alright mama": "That's All Right Mama",
    "crossroad blues": "Crossroads",
    "guilded splinters": "I Walk On Guilded Splinters",
    "walk on guilded splinters": "I Walk On Guilded Splinters",
    "phuck truck": "Love Tractor",
    "early": "Get Up Early In The Morning",
    "misery": "Get Up Early In The Morning",
    "tipitina's": "Get Up Early In The Morning",
    "longhair jam": "Get Up Early In The Morning",
    "new mother nature": "No Sugar Tonight/New Mother Nature",
    "no sugar tonight/new mother nature": "No Sugar Tonight/New Mother Nature",
    "the reefer song": "If You'se A Viper",
    "viper jive": "If You'se A Viper",
    "trimmed and burning": "Keep Your Lamps Trimmed and Burning",
    "monkey": "Sleepy Monkey",
    "monkey image": "Sleepy Monkey",
    "aiko aiko": "Iko Iko",
    "aiko, iko": "Iko Iko",
    "arlene": "Arleen",
    "me and the devil": "Me And The Devil Blues",
    "waitin' for the bus": "Waitin' For The Bus",
    "hound dog": "Hound Dog",
    "women are smarter": "Man Smart, Woman Smarter",
    "shoot out": "Shoot Out At The Fantasy Factory",
    "black-out blues": "Blackout Blues",
    "papa's home": "Papa's Home",
    "dying man": "Dyin' Man",
}


def _normalize_for_lookup(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()


def canonicalize_song_name(
    raw_name: str,
    canonical_lookup: Optional[Dict[str, str]] = None,
) -> str:
    """Canonicalize a WSP song name using static aliases and optional dynamic lookup.

    Args:
        raw_name: The raw song name from any source.
        canonical_lookup: Optional dict mapping lowercase name -> canonical name,
            typically built from wsp_songs_raw via build_canonical_lookup().

    Returns:
        The canonical song name, or the cleaned original if no mapping found.
    """
    cleaned = raw_name.strip()
    if not cleaned:
        return cleaned

    lookup_key = _normalize_for_lookup(cleaned)

    if lookup_key in CANONICAL_SONG_ALIASES:
        return CANONICAL_SONG_ALIASES[lookup_key]

    if canonical_lookup and lookup_key in canonical_lookup:
        return canonical_lookup[lookup_key]

    return cleaned


def _parse_aka_field(aka_text: str | None) -> list[str]:
    if not aka_text:
        return []
    parts = [p.strip() for p in aka_text.split(",")]
    return [p for p in parts if p]


def build_canonical_lookup(rows: Iterable[Dict[str, Any]]) -> Dict[str, str]:
    """Build a lowercase -> canonical name lookup from wsp_songs_raw rows.

    Each row should have at least ``song_name`` and optionally ``aka``.
    The returned dict maps every known alias (lowercased) to the canonical
    ``song_name`` value.
    """
    lookup: dict[str, str] = {}
    for row in rows:
        song_name = row.get("song_name")
        if not song_name:
            continue
        canonical = song_name.strip()
        lookup[_normalize_for_lookup(canonical)] = canonical
        for alias in _parse_aka_field(row.get("aka")):
            lookup[_normalize_for_lookup(alias)] = canonical
    return lookup


def build_canonical_lookup_from_db(client: Any) -> Dict[str, str]:
    """Build the canonical lookup by paging through wsp_songs_raw."""
    rows: List[Dict[str, Any]] = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("wsp_songs_raw")
            .select("song_name,aka")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    logging.info("Built WSP canonical lookup from %s songs.", len(rows))
    return build_canonical_lookup(rows)
