from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.jambandnerd.data_collection.um.collector import UmCollector


class TestUmCollector:
    @pytest.fixture
    def collector(self):
        return UmCollector()

    def test_collect_songs_uses_api(self, collector):
        # Arrange
        mock_api_response = {
            "error": False,
            "data": [
                {
                    "id": 456,
                    "name": "In The Kitchen",
                    "slug": "in-the-kitchen",
                    "isoriginal": 1,
                    "original_artist": "Umphrey's McGee",
                    "created_at": "1000-01-01 00:00:00",
                    "updated_at": "2023-12-31 04:29:59",
                }
            ],
        }

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_api_response
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Act
            songs = collector.collect_songs()

            # Assert
            assert len(songs) == 1
            assert songs[0]["song_name"] == "In The Kitchen"
            assert songs[0]["original_artist"] == "Umphrey's McGee"
            assert songs[0]["song_id"] == 456
            assert songs[0]["song_slug"] == "in-the-kitchen"
            assert songs[0]["is_original"] is True
            assert songs[0]["api_updated_at"] == "2023-12-31 04:29:59"

    def test_collect_venues_uses_api(self, collector):
        # Arrange
        mock_api_response = {
            "error": False,
            "data": [
                {
                    "venue_id": 7,
                    "venuename": "The Tabernacle",
                    "city": "Atlanta",
                    "state": "GA",
                    "country": "USA",
                    "zip": "30303",
                    "capacity": 2600,
                    "slug": "the-tabernacle-atlanta-ga-usa",
                }
            ],
        }

        with patch.object(collector.session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_api_response
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Act
            venues = collector.collect_venues()

            # Assert
            assert len(venues) == 1
            assert venues[0]["venue_id"] == 7
            assert venues[0]["venue_name"] == "The Tabernacle"
            assert venues[0]["venue_zip"] == "30303"
            assert venues[0]["capacity"] == 2600
            assert venues[0]["venue_slug"] == "the-tabernacle-atlanta-ga-usa"

    def test_collect_shows_uses_api(self, collector):
        # Arrange
        mock_api_response = {
            "error": False,
            "data": [
                {
                    "show_id": 123,
                    "showdate": "2023-12-31",
                    "permalink": "nye-2023.html",
                    "artist_id": 1,
                    "artist": "Umphrey's McGee",
                    "venuename": "Riviera Theatre",
                    "city": "Chicago",
                    "state": "IL",
                    "country": "USA",
                    "tourname": "NYE Run",
                },
                {
                    "show_id": 999,
                    "showdate": "2023-12-31",
                    "permalink": "support-act.html",
                    "artist_id": 2,
                    "artist": "Support Act",
                    "venuename": "Riviera Theatre",
                    "city": "Chicago",
                    "state": "IL",
                    "country": "USA",
                },
            ],
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
                    "artist_id": 1,
                    "artist": "Umphrey's McGee",
                    "settype": "Set 1",
                    "setnumber": "1",
                    "position": 1,
                    "showorder": 1,
                    "transition": "->",
                    "showdate": "2023-12-31",
                },
                {
                    "show_id": 123,
                    "song_id": 999,
                    "songname": "Support Song",
                    "artist_id": 2,
                    "artist": "Support Act",
                    "settype": "Set 1",
                    "setnumber": "1",
                    "position": 2,
                    "showdate": "2023-12-31",
                },
            ],
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
