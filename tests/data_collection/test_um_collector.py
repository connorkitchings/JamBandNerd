"""Tests for the Umphrey's McGee collector."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict

import pytest

from src.jambandnerd.data_collection.base import CollectorConfig
from src.jambandnerd.data_collection.um.collector import UmCollector


class _DummyResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:  # pragma: no cover - mirrors requests.Response
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


SONGS_HTML = """
<html>
  <body>
    <table>
      <thead>
        <tr>
          <th>Song Name</th>
          <th>Original Artist</th>
          <th>Debut Date</th>
          <th>Last Played</th>
          <th>Times Played Live</th>
          <th>Avg Show Gap</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>JaJunk</td>
          <td>Umphrey's McGee</td>
          <td>1998-05-09</td>
          <td>2024-12-31</td>
          <td>452</td>
          <td>7.4</td>
        </tr>
        <tr>
          <td>Glory</td>
          <td>N/A</td>
          <td></td>
          <td>2024-01-05</td>
          <td>180</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


VENUES_HTML = """
<html>
  <body>
    <table>
      <thead>
        <tr>
          <th>Venue Name</th>
          <th>City</th>
          <th>State</th>
          <th>Country</th>
          <th>Times Played</th>
          <th>Last Played</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>The Fillmore</td>
          <td>Charlotte</td>
          <td>NC</td>
          <td>USA</td>
          <td>8</td>
          <td>2024-01-11</td>
        </tr>
        <tr>
          <td>Red Rocks</td>
          <td>Morrison</td>
          <td>CO</td>
          <td>USA</td>
          <td>12</td>
          <td>2023-06-16</td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


YEAR_ARCHIVE_HTML = """
<html>
  <body>
    <section class="setlist-artist-1">
      <div class="setlist setlist-container" id="2024-01-11">
        <div class="setlist-header">
          <div class="setlist-date-long">
            <span class="setlist-date">
              <a href="/setlists/umphreys-mcgee-january-11-2024-the-fillmore-charlotte-nc-usa.html"><i class="fa fa-link"></i></a>
              <a href="/setlists/umphreys-mcgee-january-11-2024-the-fillmore-charlotte-nc-usa.html">January 11, 2024</a>
              <a href="/setlists/umphreys-mcgee">Umphrey's McGee</a> &mdash;
              <a class="venue" href="/venues/the-fillmore-charlotte-nc-usa">The Fillmore</a> &mdash;
              <a href="/venues/city/Charlotte/NC">Charlotte</a>, <a href="/venues/state/NC/USA">NC</a>, <a href="/venues/country/USA">USA</a>
            </span>
          </div>
        </div>
        <div class="setlist-body"><br>
          <p><b class="setlabel set-1">Set 1:</b>
            <span class="setlist-songbox"><a href="/song/jajunk">JaJunk</a>, </span>
            <span class="setlist-songbox"><a href="/song/resolution">Resolution</a> > </span>
          </p>
          <p><b class="setlabel set-e">Encore:</b>
            <span class="setlist-songbox"><a href="/song/glory">Glory</a><sup title="with guest singer">[1]</sup></span>
          </p>
        </div>
        <div class="setlist-footer">
          <p class="setlist-footnotes"><b>Footnotes</b>:<br>&nbsp;&nbsp;&nbsp;&nbsp;[1] with guest singer</p>
          <p><b class="shownotes-label">Show Notes:</b> Taped by the UM crew</p>
        </div>
      </div>
    </section>
  </body>
</html>
"""


@pytest.fixture(autouse=True)
def _patch_collector_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a stable collector config for tests."""

    def _fake_get_config(band: str) -> CollectorConfig:
        assert band == "um"
        return CollectorConfig(base_url="https://allthings.umphreys.com", timeout=10)

    monkeypatch.setattr(
        "src.jambandnerd.data_collection.um.collector.get_collector_config",
        _fake_get_config,
    )


def test_collect_songs_parses_table(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = UmCollector()

    def _fake_get(url: str, timeout: int | None = None) -> _DummyResponse:
        assert url.endswith("/song/")
        return _DummyResponse(SONGS_HTML)

    monkeypatch.setattr(collector.session, "get", _fake_get)

    songs = collector.collect_songs()
    assert len(songs) == 2

    first = songs[0]
    assert first["song_name"] == "JaJunk"
    assert first["original_artist"] == "Umphrey's McGee"
    assert first["debut_date"] == "1998-05-09"
    assert first["times_played_live"] == 452
    assert isinstance(first["avg_show_gap"], float)

    second = songs[1]
    assert second["original_artist"] is None
    assert second["debut_date"] is None


def test_collect_venues_parses_table(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = UmCollector()

    def _fake_get(url: str, timeout: int | None = None) -> _DummyResponse:
        assert url.endswith("/venues/")
        return _DummyResponse(VENUES_HTML)

    monkeypatch.setattr(collector.session, "get", _fake_get)

    venues = collector.collect_venues()
    assert len(venues) == 2

    first = venues[0]
    assert first["venue_name"] == "The Fillmore"
    assert first["times_played"] == 8
    assert first["last_played"] == "2024-01-11"


def test_collect_shows_and_setlists(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = UmCollector()
    responses: Dict[str, _DummyResponse] = {}
    responses["https://allthings.umphreys.com/setlists/2024"] = _DummyResponse(YEAR_ARCHIVE_HTML)

    def _fake_get(url: str, timeout: int | None = None) -> _DummyResponse:
        if url in responses:
            return responses[url]
        raise AssertionError(f"Unexpected URL fetch: {url}")

    monkeypatch.setattr(collector.session, "get", _fake_get)

    shows = collector.collect_shows(start_date=date(2024, 1, 1), end_date=date(2024, 12, 31))
    assert len(shows) == 1
    show = shows[0]
    assert show["source_url"] == "https://allthings.umphreys.com/setlists/umphreys-mcgee-january-11-2024-the-fillmore-charlotte-nc-usa.html"
    assert show["show_date"] == "2024-01-11"
    assert show["venue_name"] == "The Fillmore"
    assert show["venue_city"] == "Charlotte"
    assert show["venue_state"] == "NC"
    assert show["venue_country"] == "USA"
    assert show["show_notes"] == "Taped by the UM crew"

    db_rows = [
        {
            "show_id": 321,
            "source_url": show["source_url"],
        }
    ]
    setlists = collector.collect_setlists(db_rows)

    assert len(setlists) == 3
    first_song = setlists[0]
    assert first_song["song_name"] == "JaJunk"
    assert first_song["set_label"] == "1"
    assert first_song["song_position"] == 1
    assert first_song["show_position"] == 1
    assert first_song["is_segue"] is False
    assert first_song["encore"] is False

    second_song = setlists[1]
    assert second_song["song_name"] == "Resolution"
    assert second_song["is_segue"] is True

    encore_song = setlists[2]
    assert encore_song["encore"] is True
    assert encore_song["footnote_symbol"] == "1"
    assert encore_song["footnote_text"] == "with guest singer"
    assert encore_song["song_notes"] == "with guest singer"
