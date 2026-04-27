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

    def test_collect_shows_uses_api(self, collector):
        # Arrange
        mock_api_response = {
            "error": False,
            "data": [
                {
                    "show_id": 123,
                    "showdate": "2023-12-31",
                    "permalink": "nye-2023.html",
                    "venuename": "Riviera Theatre",
                    "city": "Chicago",
                    "state": "IL",
                    "country": "USA",
                    "tourname": "NYE Run"
                }
            ]
        }

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_api_response
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Act
            shows = collector.collect_shows(
                start_date=date(2023, 1, 1), end_date=date(2023, 12, 31)
            )

            # Assert
            assert len(shows) == 1
            assert shows[0]["show_id"] == 123
            assert shows[0]["show_date"] == "2023-12-31"
            assert shows[0]["venue_name"] == "Riviera Theatre"

    def test_collect_setlists_uses_api(self, collector):
        # Arrange
        mock_api_response = {
            "error": False,
            "data": [
                {
                    "show_id": 123,
                    "song_id": 456,
                    "songname": "In The Kitchen",
                    "settype": "Set 1",
                    "setnumber": "1",
                    "position": 1,
                    "showorder": 1,
                    "transition": "->",
                    "showdate": "2023-12-31"
                }
            ]
        }

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_api_response
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            shows_to_process = [{"show_id": 123, "show_date": "2023-12-31"}]

            # Act
            setlists = collector.collect_setlists(shows_to_process)

            # Assert
            assert len(setlists) == 1
            assert setlists[0]["song_name"] == "In The Kitchen"
            assert setlists[0]["show_id"] == "123"
            assert setlists[0]["set_label"] == "Set 1"
            assert setlists[0]["song_position"] == 1
            assert setlists[0]["show_position"] == 1
