from src.jambandnerd.data_collection.billy.normalizer import (
    normalize_setlists,
    normalize_shows,
    normalize_songs,
)


class TestBillyNormalization:
    def test_normalize_songs(self):
        raw = [{"song_name": "Dust in a Baggie"}, {"song_name": "Away From the Mire"}]
        df = normalize_songs(raw)
        assert len(df) == 2
        assert "source_hash" in df.columns
        assert "created_at" in df.columns

    def test_normalize_songs_deduplicates(self):
        raw = [{"song_name": "Dust in a Baggie"}, {"song_name": "Dust in a Baggie"}]
        df = normalize_songs(raw)
        assert len(df) == 1

    def test_normalize_shows(self):
        raw = [
            {
                "source_uuid": "abc-123",
                "show_date": "2024-03-10",
                "venue_name": "Red Rocks",
                "venue_city": "Morrison",
            }
        ]
        df = normalize_shows(raw)
        assert len(df) == 1
        assert df["show_date"].iloc[0] == "2024-03-10"
        assert "source_hash" in df.columns

    def test_normalize_shows_drops_null_source_uuid(self):
        raw = [
            {"source_uuid": None, "show_date": "2024-03-10", "venue_name": "Red Rocks"}
        ]
        df = normalize_shows(raw)
        assert df.empty

    def test_normalize_setlists(self):
        raw = [
            {
                "show_id": "1",
                "song_name": "Meet Me at the Creek",
                "set_number": 1,
                "song_position": 1,
            }
        ]
        df = normalize_setlists(raw)
        assert len(df) == 1
        assert "source_hash" in df.columns
        assert df["set_number"].dtype.name == "Int64"
