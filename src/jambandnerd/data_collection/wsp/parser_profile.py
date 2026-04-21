"""Versioned DOM assumptions for everydaycompanion.com parsing.

When the site structure changes, update the relevant field(s) and bump
``version``.  Keep old profiles in this file for historical reference.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParserProfile:
    """Versioned DOM assumptions for everydaycompanion.com parsing.

    Update ``version`` and the relevant field(s) whenever the site structure
    changes. Keep old profiles in this file for historical reference.
    """

    version: str = "2026-04-06"

    song_table_index: int = 4
    song_table_min_tables: int = 5
    song_table_columns: tuple[str, ...] = (
        "code",
        "song_name",
        "first_played",
        "last_played",
        "times_played",
        "aka",
    )

    setlist_table_range: tuple[int, int] = (4, 8)
    # Markers that, when present in a table's text, indicate it is a setlist table.
    # Covers both the "1: Song, Song" text format and the "Set 1" / "Encore" row format.
    setlist_set_markers: tuple[str, ...] = (
        "0:",
        "1:",
        "2:",
        "3:",
        "E:",
        "Set 1",
        "Set 2",
        "Set 3",
        "Encore",
    )
    setlist_noise_markers: tuple[str, ...] = ("Song Stats",)

    tour_link_extension: str = ".asp"
    tour_link_href_patterns: tuple[str, ...] = ("setlist", "/setlists/")


DEFAULT_PROFILE = ParserProfile()


def fingerprint_page(
    soup: "object", profile: ParserProfile = DEFAULT_PROFILE
) -> dict[str, object]:
    """Return structural metadata about the page for validation."""
    from bs4 import BeautifulSoup

    assert isinstance(soup, BeautifulSoup)
    tables = soup.find_all("table")
    text = soup.get_text()
    return {
        "table_count": len(tables),
        "has_set_markers": any(m in text for m in profile.setlist_set_markers),
        "has_song_catalog_table": len(tables) > profile.song_table_index,
        "has_tour_links": any(
            p in (a.get("href", "") or "")
            for a in soup.find_all("a")
            for p in profile.tour_link_href_patterns
        ),
    }


def validate_fingerprint(
    fingerprint: dict[str, object], profile: ParserProfile = DEFAULT_PROFILE
) -> list[str]:
    """Return a list of warnings if the page structure does not match expectations."""
    warnings: list[str] = []
    if fingerprint["table_count"] < profile.song_table_min_tables:
        warnings.append(
            f"Expected >= {profile.song_table_min_tables} tables, "
            f"found {fingerprint['table_count']}"
        )
    return warnings


def validate_setlist_page_fingerprint(
    fingerprint: dict[str, object], profile: ParserProfile = DEFAULT_PROFILE
) -> list[str]:
    """Return warnings specific to setlist page structure.

    Use this in addition to ``validate_fingerprint`` when processing a page
    that should contain a setlist.  It checks for signals only meaningful on
    setlist pages, so it should not be used on tour index or song catalog pages.
    """
    warnings: list[str] = []
    if not fingerprint.get("has_set_markers"):
        sample = ", ".join(profile.setlist_set_markers[:4])
        warnings.append(
            f"No set markers found on setlist page (expected one of: {sample}, ...)"
        )
    return warnings


def validate_song_catalog_columns(
    columns: "list[str] | tuple[str, ...]",
    profile: ParserProfile = DEFAULT_PROFILE,
) -> list[str]:
    """Return warnings if the song catalog table column count does not match the profile.

    Call this before force-assigning ``profile.song_table_columns`` to a
    parsed DataFrame so that column renames or table shifts surface as explicit
    warnings rather than silently producing mis-labelled data.
    """
    actual_count = len(list(columns))
    expected_count = len(profile.song_table_columns)
    if actual_count != expected_count:
        return [
            f"Song catalog column count mismatch: "
            f"expected {expected_count}, got {actual_count} (columns: {list(columns)})"
        ]
    return []
