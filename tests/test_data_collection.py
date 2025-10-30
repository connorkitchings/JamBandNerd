"""Tests for data collection modules."""

import pytest
from datetime import date

from jambandnerd.data_collection.base import BandCollector


class TestBandCollectorBase:
    """Tests for the abstract BandCollector base class."""

    def test_band_collector_is_abstract(self):
        """Test that BandCollector cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BandCollector()

    def test_band_collector_interface(self):
        """Test that BandCollector defines the expected interface."""
        # Check that the abstract methods exist
        assert hasattr(BandCollector, 'collect_shows')
        assert hasattr(BandCollector, 'collect_setlists')
        assert hasattr(BandCollector, 'collect_songs')
        assert hasattr(BandCollector, 'collect_venues')

        # Check that they are marked as abstract methods
        assert BandCollector.collect_shows.__isabstractmethod__
        assert BandCollector.collect_setlists.__isabstractmethod__
        assert BandCollector.collect_songs.__isabstractmethod__
        assert BandCollector.collect_venues.__isabstractmethod__


class MockBandCollector(BandCollector):
    """Mock implementation of BandCollector for testing."""

    def __init__(self):
        # Create a minimal config for testing
        from jambandnerd.data_collection.base import CollectorConfig
        config = CollectorConfig(base_url="https://test.example.com")
        super().__init__(config)

    def collect_shows(self, start_date: date, end_date: date):
        return [{"show_id": "test_show_1", "date": start_date.isoformat()}]

    def collect_setlists(self, show_ids):
        return [{"show_id": show_ids[0], "song": "Test Song"}]

    def collect_songs(self):
        return [{"song_id": "test_song_1", "name": "Test Song"}]

    def collect_venues(self):
        return [{"venue_id": "test_venue_1", "name": "Test Venue"}]


class TestMockBandCollector:
    """Tests for the mock BandCollector implementation."""

    def test_mock_collector_instantiation(self):
        """Test that the mock collector can be instantiated."""
        collector = MockBandCollector()
        assert isinstance(collector, BandCollector)

    def test_collect_shows(self):
        """Test the collect_shows method."""
        collector = MockBandCollector()
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)
        
        shows = collector.collect_shows(start_date, end_date)
        
        assert len(shows) == 1
        assert shows[0]["show_id"] == "test_show_1"
        assert shows[0]["date"] == "2025-01-01"

    def test_collect_setlists(self):
        """Test the collect_setlists method."""
        collector = MockBandCollector()
        show_ids = ["test_show_1"]
        
        setlists = collector.collect_setlists(show_ids)
        
        assert len(setlists) == 1
        assert setlists[0]["show_id"] == "test_show_1"
        assert setlists[0]["song"] == "Test Song"

    def test_collect_songs(self):
        """Test the collect_songs method."""
        collector = MockBandCollector()
        
        songs = collector.collect_songs()
        
        assert len(songs) == 1
        assert songs[0]["song_id"] == "test_song_1"
        assert songs[0]["name"] == "Test Song"

    def test_collect_venues(self):
        """Test the collect_venues method."""
        collector = MockBandCollector()

        venues = collector.collect_venues()

        assert len(venues) == 1
        assert venues[0]["venue_id"] == "test_venue_1"
        assert venues[0]["name"] == "Test Venue"

        venues = collector.collect_venues()

        assert len(venues) == 1
        assert venues[0]["venue_id"] == "test_venue_1"
        assert venues[0]["name"] == "Test Venue"


        assert len(venues) == 1
        assert venues[0]["venue_id"] == "test_venue_1"
        assert venues[0]["name"] == "Test Venue"

