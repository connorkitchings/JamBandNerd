from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.jambandnerd.data_collection.um.collector import UmCollector


class TestUmCollector:
    @pytest.fixture
    def collector(self):
        return UmCollector()

    def test_collect_songs_parses_table(self, collector):
        # Arrange
        mock_html = """
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
                    <td>In The Kitchen</td>
                    <td>Umphrey's McGee</td>
                    <td>1998-01-21</td>
                    <td>2023-12-31</td>
                    <td>500</td>
                    <td>5.5</td>
                </tr>
            </tbody>
        </table>
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
            assert songs[0]["song_name"] == "In The Kitchen"
            assert songs[0]["original_artist"] == "Umphrey's McGee"
            assert songs[0]["times_played_live"] == 500

    def test_collect_shows_parses_archive(self, collector):
        # Arrange
        mock_html = """
        <section class="setlist-artist-1">
            <div class="setlist">
                <div class="setlist-date-long">
                    <a href="/setlists/um20231231.html">December 31, 2023</a>
                    <a class="venue">Riviera Theatre</a>
                    <a href="/venues/city/Chicago">Chicago</a>, 
                    <a href="/venues/state/IL">IL</a>
                </div>
                <div class="setlist-body">
                    <p>
                        <b>Set 1:</b>
                        <span class="setlist-songbox"><a>Song A</a></span>
                    </p>
                </div>
            </div>
        </section>
        """

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Act
            # Limit to one year
            shows = collector.collect_shows(
                start_date=date(2023, 1, 1), end_date=date(2023, 12, 31)
            )

            # Assert
            assert len(shows) == 1
            assert shows[0]["show_date"] == "2023-12-31"
            assert shows[0]["venue_name"] == "Riviera Theatre"
            assert shows[0]["venue_city"] == "Chicago"
            assert shows[0]["venue_state"] == "IL"

    def test_collect_setlists_uses_cached_data(self, collector):
        # Arrange
        # Pre-populate cache (simulating collect_shows having run)
        mock_metadata = MagicMock()
        mock_metadata.show_date = date(2023, 12, 31)
        mock_metadata.venue_name = "Riviera Theatre"

        mock_rows = [
            {
                "set_label": "1",
                "set_sequence": 1,
                "song_position": 1,
                "show_position": 1,
                "song_name": "Song A",
                "is_segue": False,
                "encore": False,
            }
        ]

        collector._shows_by_url["http://mock/show"] = mock_metadata
        collector._setlists_by_url["http://mock/show"] = mock_rows

        shows_to_process = [{"show_id": "1", "source_url": "http://mock/show"}]

        # Act
        setlists = collector.collect_setlists(shows_to_process)

        # Assert
        assert len(setlists) == 1
        assert setlists[0]["song_name"] == "Song A"
        assert setlists[0]["venue_name"] == "Riviera Theatre"

    def test_collect_setlists_fetches_missing(self, collector):
        # Arrange
        mock_html = """
        <section class="setlist-artist-1">
            <div class="setlist">
                <div class="setlist-date-long">
                    <a href="/setlists/um20231231.html">December 31, 2023</a>
                    <a class="venue">Riviera Theatre</a>
                </div>
                <div class="setlist-body">
                    <p>
                        <b>Set 1:</b>
                        <span class="setlist-songbox"><a>Song B</a></span>
                    </p>
                </div>
            </div>
        </section>
        """

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            shows_to_process = [
                {"show_id": "2", "source_url": "http://mock/missing_show"}
            ]

            # Act
            setlists = collector.collect_setlists(shows_to_process)

            # Assert
            assert len(setlists) == 1
            assert setlists[0]["song_name"] == "Song B"
