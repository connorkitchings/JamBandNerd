from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.jambandnerd.data_collection.billy.collector import BillyCollector


class TestBillyCollector:
    @pytest.fixture
    def collector(self):
        return BillyCollector()

    def test_collect_shows_parses_html(self, collector):
        # Arrange
        # Use <br> to ensure stripped_strings separates the lines
        mock_html = """
        <html>
            <a class="link-unstyled" href="/setlist/uuid1">
                <div class="badge">
                    <span>Oct 31</span>
                    <span></span>
                    <span>2023</span>
                </div>
                <div class="col-8">
                    Van Andel Arena<br>
                    Grand Rapids, MI, USA
                </div>
            </a>
        </html>
        """

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Act
            # Limit pages to 1 for testing
            with patch.object(collector, "MAX_PAGES", 1):
                shows = collector.collect_shows(
                    start_date=date(2023, 10, 30), end_date=date(2023, 11, 1)
                )

            # Assert
            assert len(shows) == 1
            assert shows[0]["show_date"] == "2023-10-31"
            assert shows[0]["venue_name"] == "Van Andel Arena"
            assert shows[0]["venue_city"] == "Grand Rapids"
            assert shows[0]["venue_state"] == "MI"

    def test_collect_setlists_parses_html(self, collector):
        # Arrange
        # Code expects child to have 'song-stripe' and contain a 'div.row.mb-2'
        mock_html = """
        <div id="shows-panel">
            <div class="alert alert-info">Set 1:</div>
            <div class="song-stripe">
                <div class="row mb-2">
                    <div class="col-12">
                        <a href="/song/dust-in-a-baggie">Dust in a Baggie</a>
                    </div>
                </div>
            </div>
            <div class="alert alert-info">Encore:</div>
            <div class="song-stripe">
                <div class="row mb-2">
                    <div class="col-12">
                        <a href="/song/meet-me-at-the-creek">Meet Me At The Creek</a>
                    </div>
                </div>
            </div>
        </div>
        """

        shows_to_process = [
            {
                "show_id": "1",
                "source_url": "http://mock",
                "source_uuid": "uuid1",
                "show_date": "2023-10-31",
            }
        ]

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Act
            setlists = collector.collect_setlists(shows_to_process)

            # Assert
            assert len(setlists) == 2
            assert setlists[0]["song_name"] == "Dust in a Baggie"
            assert setlists[0]["set_number"] == 1
            assert setlists[1]["song_name"] == "Meet Me At The Creek"
            assert setlists[1]["set_number"] == 99  # Encore default

    def test_collect_songs_parses_table(self, collector):
        # Arrange
        mock_html = """
        <div wire:id="1" wire:snapshot='{"memo":{"id":"1","name":"songs-index"}}'>
            <table class="table-hover">
                <tbody>
                    <tr>
                        <td><a href="/song/dust-in-a-baggie">Dust in a Baggie</a></td>
                        <td>Original</td>
                        <td>100</td>
                        <td>5</td>
                        <td>2017-01-01</td>
                        <td>2023-10-31</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Act
            songs = collector.collect_songs()

            # Assert
            assert len(songs) == 1
            assert songs[0]["song_name"] == "Dust in a Baggie"
            assert songs[0]["times_played"] == 100

    def test_collect_songs_uses_canonical_trailing_slash_url(self, collector):
        mock_html = """
        <div wire:id="1" wire:snapshot='{"memo":{"id":"1","name":"songs-index"}}'>
            <table class="table-hover">
                <tbody>
                    <tr>
                        <td><a href="/song/dust-in-a-baggie">Dust in a Baggie</a></td>
                        <td>Original</td>
                        <td>100</td>
                        <td>5</td>
                        <td>2017-01-01</td>
                        <td>2023-10-31</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            collector.collect_songs()

            assert mock_get.call_args.args[0] == "https://bmfsdb.com/songs/"

    def test_parse_upcoming_cards_extracts_show(self, collector):
        from bs4 import BeautifulSoup

        # bmfsdb card structure: a.link-unstyled > div.badge (3 spans) + venue block.
        html = """
        <html>
            <a class="link-unstyled" href="/setlist/uuid-future-1">
                <div class="badge">
                    <span>Aug 15</span>
                    <span></span>
                    <span>2026</span>
                </div>
                <div class="col-8">
                    Red Rocks Amphitheatre<br>
                    Morrison, CO, USA
                </div>
            </a>
            <a class="link-unstyled" href="/setlist/uuid-past-1">
                <div class="badge">
                    <span>Jul 1</span>
                    <span></span>
                    <span>2026</span>
                </div>
                <div class="col-8">
                    Past Venue<br>
                    Somewhere, ST, USA
                </div>
            </a>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")

        upcoming = collector._parse_upcoming_cards(soup, min_date=date(2026, 7, 30))

        # Past-dated card is filtered out by min_date; future card is kept.
        assert len(upcoming) == 1
        show = upcoming[0]
        assert show["show_date"] == "2026-08-15"
        assert show["venue_name"] == "Red Rocks Amphitheatre"
        assert show["venue_city"] == "Morrison"
        assert show["venue_state"] == "CO"
        assert show["source_url"] == "https://bmfsdb.com/setlist/uuid-future-1"

    def test_collect_upcoming_shows_falls_back_to_browser_when_ssr_empty(
        self, collector
    ):
        # SSR response has the page shell but zero link-unstyled cards (Livewire).
        ssr_html = "<html><body><div>No server-rendered cards</div></body></html>"
        hydrated_html = """
        <html>
            <a class="link-unstyled" href="/setlist/uuid-future-1">
                <div class="badge">
                    <span>Sep 5</span><span></span><span>2026</span>
                </div>
                <div class="col-8">The Capitol Theatre<br>Pelham, NY, USA</div>
            </a>
        </html>
        """

        with patch.object(collector.session, "get") as mock_get:
            ssr_response = MagicMock()
            ssr_response.text = ssr_html
            ssr_response.status_code = 200
            mock_get.return_value = ssr_response

            with patch(
                "src.jambandnerd.data_collection.browser.CloudflareBypass.render_html"
            ) as mock_render:
                rendered = MagicMock()
                rendered.text = hydrated_html
                rendered.status_code = 200
                mock_render.return_value = rendered

                upcoming = collector._collect_upcoming_shows(min_date=date(2026, 7, 30))

        assert len(upcoming) == 1
        assert upcoming[0]["show_date"] == "2026-09-05"
        assert upcoming[0]["venue_name"] == "The Capitol Theatre"
        # The browser fallback must have been invoked because SSR had no cards.
        mock_render.assert_called_once()
        call_kwargs = mock_render.call_args.kwargs
        assert call_kwargs["wait_for_selector"] == "a.link-unstyled"
        assert call_kwargs["wait_until"] == "networkidle"

    def test_collect_upcoming_shows_uses_ssr_when_cards_present(self, collector):
        # If SSR returns cards, the browser fallback must NOT be used.
        ssr_html = """
        <html>
            <a class="link-unstyled" href="/setlist/uuid-future-1">
                <div class="badge">
                    <span>Oct 10</span><span></span><span>2026</span>
                </div>
                <div class="col-8">Mock Venue<br>Asheville, NC, USA</div>
            </a>
        </html>
        """

        with patch.object(collector.session, "get") as mock_get:
            ssr_response = MagicMock()
            ssr_response.text = ssr_html
            ssr_response.status_code = 200
            mock_get.return_value = ssr_response

            with patch(
                "src.jambandnerd.data_collection.browser.CloudflareBypass.render_html"
            ) as mock_render:
                upcoming = collector._collect_upcoming_shows(min_date=date(2026, 7, 30))

        assert len(upcoming) == 1
        assert upcoming[0]["show_date"] == "2026-10-10"
        mock_render.assert_not_called()
