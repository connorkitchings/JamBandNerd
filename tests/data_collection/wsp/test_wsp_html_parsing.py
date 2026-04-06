"""Fixture-based regression tests for WSP HTML parsing.

These tests load static HTML fixtures and verify that the parser and profile
infrastructure work against a known page structure. No network or DB access.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from jambandnerd.data_collection.wsp.parser import parse_setlist_from_text
from jambandnerd.data_collection.wsp.parser_profile import (
    DEFAULT_PROFILE,
    fingerprint_page,
    validate_fingerprint,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _soup(filename: str) -> BeautifulSoup:
    html = (FIXTURES / filename).read_text()
    return BeautifulSoup(html, "html.parser")


def test_parse_song_catalog_from_fixture():
    soup = _soup("song_catalog.html")
    tables = soup.find_all("table")
    assert len(tables) > DEFAULT_PROFILE.song_table_index

    df = pd.read_html(StringIO(str(tables[DEFAULT_PROFILE.song_table_index])))[0]
    assert df.shape[1] == 6
    assert df.shape[0] >= 1


def test_parse_setlist_from_fixture():
    soup = _soup("setlist_page.html")
    data = parse_setlist_from_text(soup, show_id="42")
    assert len(data) > 0
    for entry in data:
        assert "song_name" in entry
        assert entry["show_id"] == "42"


def test_parse_tour_page_from_fixture():
    soup = _soup("tour_page.html")
    links = soup.find_all(
        "a",
        href=lambda href: href
        and (
            DEFAULT_PROFILE.tour_link_extension in href
            and any(p in href for p in DEFAULT_PROFILE.tour_link_href_patterns)
        ),
    )
    assert len(links) >= 3
    for link in links:
        text = link.get_text().strip()
        assert "/" in text


def test_fingerprint_matches_default_profile():
    for filename in ("song_catalog.html", "setlist_page.html", "tour_page.html"):
        soup = _soup(filename)
        fp = fingerprint_page(soup, DEFAULT_PROFILE)
        warnings = validate_fingerprint(fp, DEFAULT_PROFILE)
        assert warnings == [], f"{filename} produced warnings: {warnings}"


def test_fingerprint_detects_layout_change():
    minimal_html = "<html><body><table><tr><td>x</td></tr></table></body></html>"
    soup = BeautifulSoup(minimal_html, "html.parser")
    fp = fingerprint_page(soup, DEFAULT_PROFILE)
    warnings = validate_fingerprint(fp, DEFAULT_PROFILE)
    assert len(warnings) > 0
