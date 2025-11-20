
import pandas as pd

from src.jambandnerd.data_collection.wsp.normalizer import (
    normalize_setlists,
    normalize_shows,
    normalize_songs,
)

# Mock raw data for songs
mock_raw_songs = [
    {"id": 1, "name": "Travelin' Light", "created_at": "2023-01-01T12:00:00Z", "updated_at": "2023-01-01T12:00:00Z"},
    {"id": 2, "name": "Ain't Life Grand", "created_at": "2023-01-02T12:00:00Z", "updated_at": "2023-01-02T12:00:00Z"},
]

# Mock raw data for shows
mock_raw_shows = [
    {"show_id": 101, "showdate": "2023-03-10", "venuename": "The Tabernacle", "city": "Atlanta", "state": "GA", "country": "USA", "tourname": "Spring Tour 2023", "created_at": "2023-03-10T12:00:00Z", "updated_at": "2023-03-10T12:00:00Z"},
    {"show_id": 102, "showdate": "2023-03-11", "venuename": "The Tabernacle", "city": "Atlanta", "state": "GA", "country": "USA", "tourname": "Spring Tour 2023", "created_at": "2023-03-11T12:00:00Z", "updated_at": "2023-03-11T12:00:00Z"},
]

# Mock raw data for venues
mock_raw_venues = [
    {"venue_id": 1001, "name": "The Tabernacle", "city": "Atlanta", "state": "GA", "country": "USA", "zip": "30303", "capacity": 2600, "slug": "the-tabernacle-atlanta"},
    {"venue_id": 1002, "name": "Red Rocks Amphitheatre", "city": "Morrison", "state": "CO", "country": "USA", "zip": "80465", "capacity": 9525, "slug": "red-rocks-amphitheatre"},
]

# Mock raw data for setlists
mock_raw_setlists = [
    {"show_id": 101, "setnumber": 1, "position": 1, "songname": "Pigeons", "settype": "set", "footnote": ""},
    {"show_id": 101, "setnumber": 1, "position": 2, "songname": "Driving Song", "settype": "set", "footnote": ""},
    {"show_id": 101, "setnumber": "e", "position": 1, "songname": "Postcard", "settype": "encore", "footnote": ""},
]

class TestWSPNormalization:

    def test_normalize_songs(self):
        df = normalize_songs(mock_raw_songs)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "api_song_id" in df.columns
        assert "song_name" in df.columns
        assert len(df) == len(mock_raw_songs)
        assert df["song_name"].iloc[0] == "Travelin' Light"

    def test_normalize_shows(self):
        mock_show = {"show_id": 101, "showdate": "2023-03-10", "venuename": "The Tabernacle", "city": "Atlanta", "state": "GA", "country": "USA", "tourname": "Spring Tour 2023", "created_at": "2023-03-10T12:00:00Z", "updated_at": "2023-03-10T12:00:00Z"}
        df = normalize_shows([mock_show])
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "show_id" in df.columns
        assert "show_date" in df.columns
        assert df["show_date"].iloc[0] == "2023-03-10"

    def test_normalize_setlists(self):
        df = normalize_setlists(mock_raw_setlists)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "show_id" in df.columns
        assert "set_number" in df.columns
        assert "song_position" in df.columns
        assert "song_name" in df.columns
        assert len(df) == len(mock_raw_setlists)
        assert df["set_number"].iloc[2] == 99 # Encore set number
