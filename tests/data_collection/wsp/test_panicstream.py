from __future__ import annotations

from datetime import date
from pathlib import Path

import requests

from src.jambandnerd.data_collection.wsp import panicstream

FIXTURES = Path(__file__).parent / "fixtures"


def _fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text()


class _Response:
    def __init__(self, text: str):
        self.text = text
        self.content = text.encode()

    def raise_for_status(self) -> None:
        return None


def test_parse_show_page_html_handles_two_sets_encore_and_segues():
    html = _fixture_text("panicstream_show_two_set.html")

    rows = panicstream.parse_show_page_html(html, show_id="22458")

    assert [row["set_number"] for row in rows[:8]] == ["1"] * 8
    assert rows[2]["song_name"] == "Machine"
    assert rows[2]["is_segue"] is True
    assert rows[3]["song_name"] == "Barstools and Dreamers"
    assert rows[3]["is_segue"] is False
    assert rows[-2]["set_number"] == "E"
    assert rows[-2]["song_name"] == "Down"
    assert rows[-1]["song_name"] == "Mr Soul"
    assert all(row["source"] == "panicstream" for row in rows)


def test_parse_show_page_html_strips_track_numbers_and_normalizes_titles():
    html = _fixture_text("panicstream_show_single_set.html")

    rows = panicstream.parse_show_page_html(html, show_id="22459")

    assert [row["song_name"] for row in rows] == [
        "Holden Oversoul",
        "Bust It Big",
        "Greta",
        "Lawyers, Guns, And Money",
        "Walkin' (For Your Love)",
        "Bowlegged Woman",
    ]
    assert rows[1]["is_segue"] is True
    assert rows[2]["is_segue"] is False
    assert all(row["set_number"] == "1" for row in rows)


def test_find_show_on_year_index_matches_date_and_location(monkeypatch):
    fixture_html = _fixture_text("panicstream_year_2026.html")

    monkeypatch.setattr(
        panicstream.session,
        "get",
        lambda *_args, **_kwargs: _Response(fixture_html),
    )

    url = panicstream.find_show_on_year_index(
        date(2026, 4, 17), city="Birmingham", state="AL"
    )

    assert (
        url
        == "https://www.panicstream.com/vault/widespread-panic-04-17-2026-birmingham-al/"
    )


def test_fetch_setlist_from_panicstream_uses_index_then_show_page(monkeypatch):
    fixture_index = _fixture_text("panicstream_year_2026.html")
    fixture_show = _fixture_text("panicstream_show_two_set.html")
    seen_urls: list[str] = []

    def fake_get(url: str, **_kwargs):
        seen_urls.append(url)
        if url.endswith("/category/2026/"):
            return _Response(fixture_index)
        if url.endswith("/widespread-panic-04-17-2026-birmingham-al/"):
            return _Response(fixture_show)
        raise requests.HTTPError(url)

    monkeypatch.setattr(panicstream.session, "get", fake_get)

    rows = panicstream.fetch_setlist_from_panicstream(
        date(2026, 4, 17), "22458", "Birmingham", "AL"
    )

    assert rows
    assert seen_urls == [
        "https://www.panicstream.com/vault/category/2026/",
        "https://www.panicstream.com/vault/widespread-panic-04-17-2026-birmingham-al/",
    ]
