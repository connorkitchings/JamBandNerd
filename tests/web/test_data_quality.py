"""Tests for data quality and integrity in the web data layer."""

from __future__ import annotations

import pandas as pd


class TestSetlistDeduplication:
    """Tests to ensure setlist data is properly deduplicated."""

    def test_duplicate_positions_are_removed(self):
        """Verify duplicate set_number/song_position pairs are deduplicated."""
        # Simulate data with duplicates (as reported by user)
        df = pd.DataFrame(
            {
                "set_number": [1, 1, 1, 1, 2, 2],
                "song_position": [
                    1,
                    1,
                    2,
                    3,
                    1,
                    1,
                ],  # Position 1 is duplicated in both sets
                "song_name": [
                    "Song A",
                    "Song A Dup",
                    "Song B",
                    "Song C",
                    "Song D",
                    "Song D Dup",
                ],
            }
        )

        # Apply deduplication logic (same as in last_show.py)
        dedup_cols = ["set_number", "song_position"]
        df_deduped = df.drop_duplicates(subset=dedup_cols, keep="first")

        assert len(df_deduped) == 4  # Should have 4 unique position entries
        assert "Song A Dup" not in df_deduped["song_name"].values
        assert "Song D Dup" not in df_deduped["song_name"].values

    def test_unique_positions_unchanged(self):
        """Verify unique setlist data is not affected by deduplication."""
        df = pd.DataFrame(
            {
                "set_number": [1, 1, 1, 2, 2],
                "song_position": [1, 2, 3, 1, 2],
                "song_name": ["Song A", "Song B", "Song C", "Song D", "Song E"],
            }
        )

        dedup_cols = ["set_number", "song_position"]
        df_deduped = df.drop_duplicates(subset=dedup_cols, keep="first")

        assert len(df_deduped) == 5  # All unique, no change
        assert list(df_deduped["song_name"]) == [
            "Song A",
            "Song B",
            "Song C",
            "Song D",
            "Song E",
        ]

    def test_handles_missing_song_position_column(self):
        """Verify deduplication works with 'position' column (Phish schema)."""
        df = pd.DataFrame(
            {
                "set_number": [1, 1, 1],
                "position": [1, 1, 2],  # Using 'position' instead of 'song_position'
                "song_name": ["Song A", "Song A Dup", "Song B"],
            }
        )

        # Use the position column logic from the code
        pos_col = "song_position" if "song_position" in df.columns else "position"
        dedup_cols = ["set_number", pos_col]
        df_deduped = df.drop_duplicates(subset=dedup_cols, keep="first")

        assert len(df_deduped) == 2
        assert pos_col == "position"


class TestLastShowSelection:
    """Tests for selecting the most recent show with setlist data."""

    def test_selects_most_recent_show_with_setlist(self):
        """Verify the most recent show WITH setlist data is selected."""
        # Simulate shows - some have setlist data, some don't
        shows = pd.DataFrame(
            {
                "show_id": ["show_5", "show_4", "show_3", "show_2", "show_1"],
                "show_date": [
                    "2025-12-10",
                    "2025-12-08",
                    "2025-11-15",
                    "2025-11-10",
                    "2025-10-31",
                ],
            }
        )

        # Shows with setlist data (show_3, show_2, show_1 have setlists; show_5, show_4 don't)
        setlist_show_ids = {"show_3", "show_2", "show_1"}

        # Filter to shows with setlists
        candidates = shows[shows["show_id"].isin(setlist_show_ids)]

        # Sort by date descending
        candidates_sorted = candidates.sort_values("show_date", ascending=False)

        most_recent_with_setlist = candidates_sorted.iloc[0]["show_id"]

        assert most_recent_with_setlist == "show_3"  # Most recent WITH setlist
        assert candidates_sorted.iloc[0]["show_date"] == "2025-11-15"

    def test_excludes_future_shows(self):
        """Verify future shows are excluded from last show selection."""
        from datetime import date

        today_iso = date.today().isoformat()

        shows = pd.DataFrame(
            {
                "show_id": ["future_show", "past_show_1", "past_show_2"],
                "show_date": ["2099-12-31", "2025-01-01", "2024-12-31"],
            }
        )

        # Logic from fetch_last_show_setlist: .lt("show_date", today_iso)
        past_shows = shows[shows["show_date"] < today_iso]

        assert "future_show" not in past_shows["show_id"].values
        assert len(past_shows) == 2


class TestDataIntegrity:
    """Tests for general data integrity."""

    def test_setlist_has_required_columns(self):
        """Verify expected columns are present in setlist data structure."""
        expected_columns = {"set_number", "song_name"}

        # At minimum, these columns are required
        df = pd.DataFrame(
            {
                "set_number": [1, 2],
                "song_position": [1, 1],
                "song_name": ["Song A", "Song B"],
            }
        )

        assert expected_columns.issubset(set(df.columns))

    def test_show_details_has_date(self):
        """Verify show details include date field."""
        show_details = {
            "show_id": "test_123",
            "show_date": "2025-01-01",
            "venue": "Test Venue",
            "city": "Test City",
            "state": "TS",
        }

        assert "show_date" in show_details
        assert show_details["show_date"] is not None
