from unittest.mock import patch

import pytest

from src.jambandnerd.data_collection.goose.collector import GooseCollector


class TestGooseCollector:
    @pytest.fixture
    def collector(self):
        return GooseCollector()

    def test_collect_shows_filters_artist(self, collector):
        # Arrange
        mock_data = [
            {"artist": "Goose", "showdate": "2023-01-01"},
            {"artist": "Orebolo", "showdate": "2023-01-02"},
            {"artist": "goose", "showdate": "2023-01-03"},  # Case insensitive check
        ]

        with patch.object(
            collector, "_fetch_from_endpoint", return_value=mock_data
        ) as mock_fetch:
            # Act
            result = collector.collect_shows()

            # Assert
            mock_fetch.assert_called_once_with("v2/shows.json")
            assert len(result) == 2
            assert result[0]["showdate"] == "2023-01-01"
            assert result[1]["showdate"] == "2023-01-03"

    def test_collect_setlists_filters_artist(self, collector):
        # Arrange
        mock_data = [
            {"artist": "Goose", "show_id": 1},
            {"artist": "Vasudo", "show_id": 2},
        ]

        with patch.object(
            collector, "_fetch_from_endpoint", return_value=mock_data
        ) as mock_fetch:
            # Act
            result = collector.collect_setlists()

            # Assert
            mock_fetch.assert_called_once_with("v1/setlists.json")
            assert len(result) == 1
            assert result[0]["show_id"] == 1

    def test_collect_songs(self, collector):
        # Arrange
        mock_data = [{"id": 1, "name": "Arcadia"}]

        with patch.object(
            collector, "_fetch_from_endpoint", return_value=mock_data
        ) as mock_fetch:
            # Act
            result = collector.collect_songs()

            # Assert
            mock_fetch.assert_called_once_with("v2/songs.json")
            assert result == mock_data

    def test_collect_venues(self, collector):
        # Arrange
        mock_data = [{"id": 1, "name": "The Capitol Theatre"}]

        with patch.object(
            collector, "_fetch_from_endpoint", return_value=mock_data
        ) as mock_fetch:
            # Act
            result = collector.collect_venues()

            # Assert
            mock_fetch.assert_called_once_with("v2/venues.json")
            assert result == mock_data
