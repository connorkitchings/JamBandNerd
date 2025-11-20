import os
from unittest.mock import patch

import pytest

from src.jambandnerd.data_collection.phish.collector import PhishCollector


class TestPhishCollector:
    @pytest.fixture
    def collector(self):
        with patch.dict(os.environ, {"PHISH_API_KEY": "fake_key"}):
            return PhishCollector()

    def test_init_raises_error_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="PHISH_API_KEY environment variable not set"
            ):
                PhishCollector()

    def test_collect_songs(self, collector):
        # Arrange
        mock_data = {"data": [{"songid": 1, "song": "YEM"}]}

        with patch.object(
            collector, "_fetch_from_endpoint", return_value=mock_data
        ) as mock_fetch:
            # Act
            result = collector.collect_songs()

            # Assert
            # Check that apikey is appended
            mock_fetch.assert_called_once()
            args, _ = mock_fetch.call_args
            assert args[0].startswith("songs.json?apikey=fake_key")
            assert result == [{"songid": 1, "song": "YEM"}]

    def test_collect_shows(self, collector):
        # Arrange
        mock_data = {"data": [{"showid": 1, "showdate": "2023-01-01"}]}

        with patch.object(
            collector, "_fetch_from_endpoint", return_value=mock_data
        ) as mock_fetch:
            # Act
            result = collector.collect_shows()

            # Assert
            mock_fetch.assert_called_once()
            assert result == [{"showid": 1, "showdate": "2023-01-01"}]

    def test_collect_venues_extracts_from_shows(self, collector):
        # Arrange
        mock_shows = [
            {
                "venueid": 1,
                "venue": "MSG",
                "city": "NYC",
                "state": "NY",
                "country": "USA",
            },
            {
                "venueid": 1,
                "venue": "MSG",
                "city": "NYC",
                "state": "NY",
                "country": "USA",
            },  # Duplicate
            {
                "venueid": 2,
                "venue": "Hampton",
                "city": "Hampton",
                "state": "VA",
                "country": "USA",
            },
        ]

        with patch.object(collector, "collect_shows", return_value=mock_shows):
            # Act
            result = collector.collect_venues()

            # Assert
            assert len(result) == 2
            assert result[0]["api_venue_id"] == 1
            assert result[1]["api_venue_id"] == 2

    def test_collect_setlists(self, collector):
        # Arrange
        show_ids = ["1", "2"]
        mock_setlist_data = [{"setlistdata": "..."}]

        with patch.object(
            collector, "_fetch_from_endpoint", return_value=mock_setlist_data
        ) as mock_fetch:
            # Act
            result = collector.collect_setlists(show_ids)

            # Assert
            assert mock_fetch.call_count == 2
            assert len(result) == 2
