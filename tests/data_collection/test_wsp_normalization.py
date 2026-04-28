import pandas as pd

from src.jambandnerd.data_collection.wsp.normalizer import (
    normalize_setlists,
    normalize_shows,
    normalize_songs,
)

# Mock raw data for songs (EC collector format)
mock_raw_songs = [
    {
        "code": "TLIGHT",
        "song_name": "Travelin' Light",
        "first_played": "1986-04-17",
        "last_played": "2026-03-22",
        "times_played": 1047,
        "aka": None,
    },
    {
        "code": "GRAND",
        "song_name": "Ain't Life Grand",
        "first_played": "1993-07-26",
        "last_played": "2026-03-21",
        "times_played": 661,
        "aka": None,
    },
]

# Mock raw data for shows
mock_raw_shows = [
    {
        "show_id": 101,
        "showdate": "2023-03-10",
        "venuename": "The Tabernacle",
        "city": "Atlanta",
        "state": "GA",
        "country": "USA",
        "tourname": "Spring Tour 2023",
        "created_at": "2023-03-10T12:00:00Z",
        "updated_at": "2023-03-10T12:00:00Z",
    },
    {
        "show_id": 102,
        "showdate": "2023-03-11",
        "venuename": "The Tabernacle",
        "city": "Atlanta",
        "state": "GA",
        "country": "USA",
        "tourname": "Spring Tour 2023",
        "created_at": "2023-03-11T12:00:00Z",
        "updated_at": "2023-03-11T12:00:00Z",
    },
]

# Mock raw data for venues
mock_raw_venues = [
    {
        "venue_id": 1001,
        "name": "The Tabernacle",
        "city": "Atlanta",
        "state": "GA",
        "country": "USA",
        "zip": "30303",
        "capacity": 2600,
        "slug": "the-tabernacle-atlanta",
    },
    {
        "venue_id": 1002,
        "name": "Red Rocks Amphitheatre",
        "city": "Morrison",
        "state": "CO",
        "country": "USA",
        "zip": "80465",
        "capacity": 9525,
        "slug": "red-rocks-amphitheatre",
    },
]

# Mock raw data for setlists
mock_raw_setlists = [
    {
        "show_id": 101,
        "setnumber": 1,
        "position": 1,
        "songname": "Pigeons",
        "settype": "set",
        "footnote": "",
    },
    {
        "show_id": 101,
        "setnumber": 1,
        "position": 2,
        "songname": "Driving Song",
        "settype": "set",
        "footnote": "",
    },
    {
        "show_id": 101,
        "setnumber": "e",
        "position": 1,
        "songname": "Postcard",
        "settype": "encore",
        "footnote": "",
    },
]


class TestWSPNormalization:
    def test_normalize_songs(self):
        df = normalize_songs(mock_raw_songs)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "song_code" in df.columns
        assert "song_name" in df.columns
        assert len(df) == len(mock_raw_songs)
        assert df["song_name"].iloc[0] == "Travelin' Light"
        assert df["song_code"].iloc[0] == "TLIGHT"

    def test_normalize_shows(self):
        mock_show = {
            "show_id": 101,
            "showdate": "2023-03-10",
            "venuename": "The Tabernacle",
            "city": "Atlanta",
            "state": "GA",
            "country": "USA",
            "tourname": "Spring Tour 2023",
            "created_at": "2023-03-10T12:00:00Z",
            "updated_at": "2023-03-10T12:00:00Z",
        }
        df = normalize_shows([mock_show])
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "show_id" in df.columns
        assert "show_date" in df.columns
        assert df["show_date"].iloc[0] == "2023-03-10"
        assert df["show_id"].iloc[0] == "101"

    def test_normalize_shows_drops_rows_without_assigned_show_id(self):
        mock_show = {
            "show_date": "2026-02-14",
            "venue_name": "Moody Center",
            "city": "Austin",
            "state": "TX",
            "source_url": "https://www.everydaycompanion.com/setlists/20260214a.asp",
        }
        df = normalize_shows([mock_show])
        assert df.empty

    def test_normalize_setlists(self):
        df = normalize_setlists(mock_raw_setlists)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "show_id" in df.columns
        assert "set_number" in df.columns
        assert "song_position" in df.columns
        assert "song_name" in df.columns
        assert len(df) == len(mock_raw_setlists)
        assert df["set_number"].iloc[2] == 99  # Encore set number

    def test_normalize_setlists_drops_non_positive_song_positions(self):
        raw = [
            {"show_id": 101, "setnumber": 1, "position": 1, "songname": "Valid Song"},
            {"show_id": 101, "setnumber": 1, "position": 0, "songname": "Zero Pos"},
            {
                "show_id": 101,
                "setnumber": 1,
                "position": -3,
                "songname": "Negative Pos",
            },
        ]
        df = normalize_setlists(raw)
        assert len(df) == 1
        assert df["song_position"].iloc[0] == 1
        assert df["song_name"].iloc[0] == "Valid Song"

    def test_normalize_setlists_canonicalizes_c_brown(self):
        raw = [
            {
                "show_id": 101,
                "set_number": 1,
                "song_position": 1,
                "song_name": "C Brown",
            },
            {
                "show_id": 101,
                "set_number": 1,
                "song_position": 2,
                "song_name": "C.Brown",
            },
        ]
        df = normalize_setlists(raw)
        assert all(df["song_name"] == "C. Brown")

    def test_normalize_setlists_canonicalizes_mr_soul(self):
        raw = [
            {
                "show_id": 101,
                "set_number": "E",
                "song_position": 1,
                "song_name": "Mr Soul",
            },
        ]
        df = normalize_setlists(raw)
        assert df["song_name"].iloc[0] == "Mr. Soul"

    def test_normalize_setlists_canonicalizes_with_dynamic_lookup(self):
        raw = [
            {
                "show_id": 101,
                "set_number": 1,
                "song_position": 1,
                "song_name": "Coconut Image",
            },
        ]
        lookup = {"coconut image": "Coconut"}
        df = normalize_setlists(raw, canonical_lookup=lookup)
        assert df["song_name"].iloc[0] == "Coconut"

    def test_normalize_setlists_canonicalizes_panicstream_output(self):
        raw = [
            {
                "show_id": 101,
                "set_number": 1,
                "song_position": 1,
                "song_name": "Walkin'",
            },
            {
                "show_id": 101,
                "set_number": 1,
                "song_position": 2,
                "song_name": "Bowlegged Woman, Knock Kneed Man",
            },
        ]
        df = normalize_setlists(raw)
        assert df["song_name"].iloc[0] == "Walkin' (For Your Love)"
        assert df["song_name"].iloc[1] == "Bowlegged Woman"

    def test_normalize_setlists_preserves_unknown_songs(self):
        raw = [
            {
                "show_id": 101,
                "set_number": 1,
                "song_position": 1,
                "song_name": "New Unreleased Song",
            },
        ]
        df = normalize_setlists(raw)
        assert df["song_name"].iloc[0] == "New Unreleased Song"
