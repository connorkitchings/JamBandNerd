from src.jambandnerd.data_collection.phish.normalizer import (
    normalize_setlists,
    normalize_shows,
    normalize_songs,
    normalize_venues,
)


class TestPhishNormalization:
    def test_normalize_songs(self):
        raw = [
            {"songid": "101", "song": "Tweezer"},
            {"songid": "102", "song": "Bathtub Gin"},
        ]
        df = normalize_songs(raw)
        assert len(df) == 2
        assert "api_song_id" in df.columns
        assert df["song_name"].iloc[0] == "Tweezer"

    def test_normalize_songs_skips_missing_songid(self):
        raw = [{"song": "No ID"}, {"songid": "1", "song": "Valid"}]
        df = normalize_songs(raw)
        assert len(df) == 1

    def test_normalize_shows(self):
        raw = [
            {
                "showid": "abc",
                "showdate": "2024-07-04",
                "venue": "MSG",
                "showyear": 2024,
            }
        ]
        df = normalize_shows(raw)
        assert len(df) == 1
        assert df["show_id"].iloc[0] == "abc"
        assert df["show_date"].iloc[0] == "2024-07-04"

    def test_normalize_venues_deduplicates(self):
        raw = [
            {"venueid": "1", "venue": "MSG", "city": "NYC"},
            {"venueid": "1", "venue": "MSG", "city": "NYC"},
        ]
        df = normalize_venues(raw)
        assert len(df) == 1

    def test_normalize_setlists(self):
        raw = [
            {
                "uniqueid": "x1",
                "showid": "1",
                "song": "Tweezer",
                "set": "1",
                "position": 3,
            }
        ]
        df = normalize_setlists(raw)
        assert len(df) == 1
        assert df["song_name"].iloc[0] == "Tweezer"

    def test_normalize_setlists_skips_missing_uniqueid(self):
        raw = [{"showid": "1", "song": "No ID"}]
        df = normalize_setlists(raw)
        assert df.empty
