"""Tests for the Billy Strings collector."""

from __future__ import annotations

from typing import Any, Dict

import pytest
from bs4 import BeautifulSoup

from src.jambandnerd.data_collection.billy.collector import BillyCollector


class _DummyResponse:
    def __init__(self, text: str) -> None:
        self.text = text
        self.status_code = 200

    def raise_for_status(self) -> None:  # pragma: no cover - mirrors requests.Response signature
        return None


SAMPLE_SONGS_HTML = """
<html>
  <body>
    <div wire:id="songs123" wire:snapshot='{"memo":{"name":"songs-index"}}'>
      <table class="table table-hover">
        <tbody>
          <tr>
            <td><a href="https://bmfsdb.com/song/first-uuid">Dust in a Baggie</a></td>
            <td><a href="https://bmfsdb.com/artist/288">Billy Strings</a></td>
            <td>498</td>
            <td>0</td>
            <td>2012-08-30</td>
            <td>2025-10-24</td>
          </tr>
          <tr>
            <td><a href="https://bmfsdb.com/song/second-uuid">New Jam</a></td>
            <td>N/A</td>
            <td>12</td>
            <td>N/A</td>
            <td>N/A</td>
            <td>2024-05-01</td>
          </tr>
          <tr>
            <td>Unnamed</td>
            <td><a href="https://bmfsdb.com/artist/42">Side Project</a></td>
            <td>--</td>
            <td>--</td>
            <td>2023-01-01</td>
            <td>2023-02-01</td>
          </tr>
        </tbody>
      </table>
    </div>
  </body>
</html>
"""


def test_collect_songs_parses_table(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure collect_songs parses bmfsdb song table rows."""

    collector = BillyCollector()

    def fake_get(url: str, params: Dict[str, Any] | None = None, timeout: int | None = None) -> _DummyResponse:
        assert "songs" in url
        assert params is not None
        assert params.get("showAll") == "1"
        return _DummyResponse(SAMPLE_SONGS_HTML)

    monkeypatch.setattr(collector.session, "get", fake_get)

    songs = collector.collect_songs()

    assert len(songs) == 3

    first, second, third = songs

    assert first["song_name"] == "Dust in a Baggie"
    assert first["original_artist"] == "Billy Strings"
    assert first["song_uuid"] == "first-uuid"
    assert first["times_played"] == 498
    assert first["times_teased"] == 0
    assert first["first_played"] == "2012-08-30"
    assert first["last_played"] == "2025-10-24"

    assert second["song_name"] == "New Jam"
    assert second["original_artist"] is None
    assert second["times_teased"] == 0
    assert second["first_played"] is None

    assert third["song_name"] == "Unnamed"
    assert third["original_artist"] == "Side Project"
    assert third["original_artist_id"] == "42"
    assert third["times_played"] == 0


def test_extract_show_uuid_handles_nonnumeric_ids() -> None:
    collector = BillyCollector()
    soup = BeautifulSoup('<a class="link-unstyled" href="https://bmfsdb.com/setlist/80267152"><div></div></a>', "html.parser")
    anchor = soup.find("a")
    assert anchor is not None

    show_uuid = collector._extract_show_uuid(anchor)
    # Should be a valid UUID string
    assert show_uuid is not None
    assert len(show_uuid) == 36
