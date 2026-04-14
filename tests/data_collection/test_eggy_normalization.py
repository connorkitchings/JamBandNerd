from src.jambandnerd.data_collection.eggy.normalizer import (
    normalize_setlists,
    normalize_shows,
    normalize_songs,
    normalize_venues,
)


class TestEggyNormalization:
    def test_normalize_songs(self):
        raw = [{"id": "1", "name": "Bright Blue"}, {"id": "2", "name": "On My Way"}]
        df = normalize_songs(raw)
        assert len(df) == 2
        assert df["api_song_id"].iloc[0] == "1"

    def test_normalize_songs_skips_missing_id(self):
        raw = [{"name": "No ID"}]
        df = normalize_songs(raw)
        assert df.empty

    def test_normalize_shows(self):
        raw = [{"show_id": "10", "show_date": "2024-01-15", "venue_name": "Elsewhere"}]
        df = normalize_shows(raw)
        assert len(df) == 1
        assert df["show_date"].iloc[0] == "2024-01-15"

    def test_normalize_venues(self):
        raw = [{"venue_id": "5", "name": "Elsewhere", "city": "Brooklyn"}]
        df = normalize_venues(raw)
        assert len(df) == 1
        assert df["venue_id"].iloc[0] == "5"

    def test_normalize_setlists_encore_maps_to_99(self):
        raw = [
            {
                "show_id": "1",
                "setnumber": "e",
                "position": 1,
                "songname": "Bright Blue",
            },
        ]
        df = normalize_setlists(raw)
        assert len(df) == 1
        assert df["set_number"].iloc[0] == 99

    def test_normalize_setlists_skips_incomplete_rows(self):
        raw = [{"show_id": "1", "setnumber": 1, "songname": "Missing Position"}]
        df = normalize_setlists(raw)
        assert df.empty
