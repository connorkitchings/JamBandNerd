import pandas as pd

from src.jambandnerd.data_collection.goose.normalizer import (
    normalize_setlists,
    normalize_shows,
    normalize_songs,
    normalize_venues,
)


class TestGooseNormalization:
    def test_normalize_songs(self):
        raw = [{"id": 1, "name": "Arcadia"}, {"id": 2, "name": "Hungersite"}]
        df = normalize_songs(raw)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "api_song_id" in df.columns
        assert df["song_name"].iloc[0] == "Arcadia"

    def test_normalize_songs_skips_missing_id(self):
        raw = [{"name": "No ID Song"}, {"id": 1, "name": "Valid"}]
        df = normalize_songs(raw)
        assert len(df) == 1

    def test_normalize_shows(self):
        raw = [{"show_id": 101, "showdate": "2024-06-01", "venuename": "Red Rocks"}]
        df = normalize_shows(raw)
        assert len(df) == 1
        assert df["show_id"].iloc[0] == "101"
        assert df["show_date"].iloc[0] == "2024-06-01"

    def test_normalize_shows_skips_missing_id(self):
        raw = [{"showdate": "2024-06-01"}]
        df = normalize_shows(raw)
        assert df.empty

    def test_normalize_venues(self):
        raw = [{"venue_id": 5, "venuename": "The Tabernacle", "city": "Atlanta"}]
        df = normalize_venues(raw)
        assert len(df) == 1
        assert df["venue_id"].iloc[0] == "5"

    def test_normalize_setlists_encore_maps_to_99(self):
        raw = [
            {"show_id": 1, "setnumber": "e", "position": 1, "songname": "So Ready"},
        ]
        df = normalize_setlists(raw)
        assert len(df) == 1
        assert df["set_number"].iloc[0] == 99

    def test_normalize_setlists_skips_incomplete_rows(self):
        raw = [
            {"show_id": 1, "setnumber": 1, "songname": "Missing Position"},
        ]
        df = normalize_setlists(raw)
        assert df.empty
