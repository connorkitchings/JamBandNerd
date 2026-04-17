"""Fixture-based regression tests for WSP HTML parsing.

These tests load static HTML fixtures and verify that the parser and profile
infrastructure work against a known page structure. No network or DB access.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

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


def test_parse_setlist_preserves_comma_title_song():
    soup = _soup("setlist_page_with_comma_title.html")
    data = parse_setlist_from_text(soup, show_id="43")

    names = [entry["song_name"] for entry in data]
    assert "Lawyers, Guns, And Money" in names
    assert "Lawyers" not in names
    assert "Guns" not in names
    assert "And Money" not in names


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


@patch("jambandnerd.data_collection.wsp.collector.get_supabase_client")
@patch("jambandnerd.data_collection.wsp.collector.parse_setlist_from_text")
@patch("jambandnerd.data_collection.wsp.collector.make_request")
@patch("jambandnerd.data_collection.wsp.collector.decode_ec_response")
def test_html_table_parser_stops_at_stats_section(
    mock_decode, mock_make_request, mock_parse_text, mock_supabase
):
    """Regression: stats section after setlist songs must not produce duplicate positions.

    When the page text parser returns empty (e.g., inline stats contaminate song
    names) the HTML table fallback runs.  If the table contains a stats section
    header ('StatsSongLTPDateL3TP') followed by repeated song names, the parser
    must stop at that header rather than appending the stats songs to the set.
    """
    from jambandnerd.data_collection.wsp.collector import WSPCollector

    fixture_html = (FIXTURES / "setlist_page_with_stats.html").read_text().encode()

    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = (
        []
    )
    mock_response = MagicMock()
    mock_response.url = "https://example.com/setlists/20250726a.asp"
    mock_make_request.return_value = mock_response
    mock_decode.return_value = fixture_html.decode()
    mock_parse_text.return_value = []  # force HTML table fallback

    collector = WSPCollector()
    result = collector._scrape_single_setlist(
        {"show_id": "999", "source_url": "https://example.com/setlists/20250726a.asp"}
    )

    set1 = [s for s in result if s["set_number"] == "1"]
    set2 = [s for s in result if s["set_number"] == "2"]
    set_e = [s for s in result if s["set_number"] == "E"]

    # Correct counts: Set 1 has 6 songs, Set 2 has 7, Encore has 3
    assert len(set1) == 6, f"Set 1 should have 6 songs, got {len(set1)}: {set1}"
    assert len(set2) == 7, f"Set 2 should have 7 songs, got {len(set2)}: {set2}"
    assert len(set_e) == 3, f"Encore should have 3 songs, got {len(set_e)}: {set_e}"

    # No duplicate song names within the same set
    for set_songs, label in [(set1, "Set 1"), (set2, "Set 2")]:
        names = [s["song_name"] for s in set_songs]
        assert len(names) == len(
            set(names)
        ), f"{label} has duplicate song names: {names}"


@patch("jambandnerd.data_collection.wsp.collector.get_supabase_client")
@patch("jambandnerd.data_collection.wsp.collector.make_request")
@patch("jambandnerd.data_collection.wsp.collector.decode_ec_response")
@patch("jambandnerd.data_collection.wsp.collector.parse_setlist_from_text")
def test_collector_falls_back_when_primary_parser_fragments_comma_title(
    mock_parse_text, mock_decode, mock_make_request, mock_supabase
):
    from jambandnerd.data_collection.wsp.collector import WSPCollector

    fixture_html = (FIXTURES / "setlist_table_rows_with_comma_title.html").read_text()

    mock_supabase.return_value.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = (
        []
    )
    mock_response = MagicMock()
    mock_response.url = "https://example.com/setlists/20200124a.asp"
    mock_make_request.return_value = mock_response
    mock_decode.return_value = fixture_html
    mock_parse_text.return_value = [
        {
            "show_id": "43",
            "set_number": "1",
            "song_position": 1,
            "song_name": "Lawyers",
            "is_segue": False,
            "song_notes": "",
        },
        {
            "show_id": "43",
            "set_number": "1",
            "song_position": 2,
            "song_name": "Guns",
            "is_segue": False,
            "song_notes": "",
        },
        {
            "show_id": "43",
            "set_number": "1",
            "song_position": 3,
            "song_name": "And Money",
            "is_segue": False,
            "song_notes": "",
        },
    ]

    collector = WSPCollector()
    result = collector._scrape_single_setlist(
        {"show_id": "43", "source_url": "https://example.com/setlists/20200124a.asp"}
    )

    names = [entry["song_name"] for entry in result]
    assert "Lawyers, Guns, And Money" in names
    assert "Lawyers" not in names
    assert "Guns" not in names
    assert "And Money" not in names


def test_fingerprint_detects_layout_change():
    minimal_html = "<html><body><table><tr><td>x</td></tr></table></body></html>"
    soup = BeautifulSoup(minimal_html, "html.parser")
    fp = fingerprint_page(soup, DEFAULT_PROFILE)
    warnings = validate_fingerprint(fp, DEFAULT_PROFILE)
    assert len(warnings) > 0
