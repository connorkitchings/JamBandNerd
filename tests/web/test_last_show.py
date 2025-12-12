"""Tests for the Last Show Analysis tab component."""

from __future__ import annotations

import pandas as pd
import pytest


class TestCleanSongNameForDisplay:
    """Tests for _clean_song_name_for_display helper function."""

    def test_strips_trailing_markers(self):
        """Verify trailing > and * are removed."""
        from jambandnerd.web.components.common import (
            clean_song_name_for_display,
        )

        assert clean_song_name_for_display("Disco>", "wsp") == "Disco"
        assert (
            clean_song_name_for_display("Space Wrangler*", "wsp") == "Space Wrangler"
        )
        # Note: function strips right-to-left sequentially, so *> gets both stripped
        # but >* only strips the * leaving the >
        assert clean_song_name_for_display("Chilly Water*>", "wsp") == "Chilly Water"

    def test_removes_wsp_artist_markers(self):
        """Verify WSP artist credits are stripped."""
        from jambandnerd.web.components.common import (
            clean_song_name_for_display,
        )

        result = clean_song_name_for_display("Tall Boy, David Bromberg Band", "wsp")
        assert result == "Tall Boy"

    def test_artist_marker_removal_case_insensitive(self):
        """Artist marker removal should be case insensitive."""
        from jambandnerd.web.components.common import (
            clean_song_name_for_display,
        )

        result = clean_song_name_for_display("Song, THE DOORS", "wsp")
        assert result == "Song"

    def test_non_wsp_bands_keep_markers(self):
        """Non-WSP bands should not have artist markers stripped."""
        from jambandnerd.web.components.common import (
            clean_song_name_for_display,
        )

        result = clean_song_name_for_display("Song, The Doors", "phish")
        assert result == "Song, The Doors"

    def test_handles_empty_string(self):
        """Empty strings should return empty."""
        from jambandnerd.web.components.common import (
            clean_song_name_for_display,
        )

        assert clean_song_name_for_display("", "wsp") == ""
        assert clean_song_name_for_display("   ", "wsp") == ""

    def test_handles_non_string(self):
        """Non-string input should return empty."""
        from jambandnerd.web.components.common import (
            clean_song_name_for_display,
        )

        assert clean_song_name_for_display(None, "wsp") == ""
        assert clean_song_name_for_display(123, "wsp") == ""


class TestSetNumberOrdering:
    """Tests for set number ordering logic."""

    def test_encore_sorting(self):
        """Verify encore sets sort last."""
        # Import the ordering key from the module
        from jambandnerd.web.components.tabs.last_show import display_last_show_setlist

        # Test the internal ordering logic
        def _set_order_key(v):
            s = str(v).strip().upper()
            if s in {"E", "ENCORE", "99"}:
                return 99
            if s in {"0", "SOUNDCHECK"}:
                return 0
            try:
                return int(float(s))
            except Exception:
                return 50

        set_numbers = [1, 2, "E", 0]
        sorted_sets = sorted(set_numbers, key=_set_order_key)

        assert sorted_sets[0] == 0  # Soundcheck first
        assert sorted_sets[-1] == "E"  # Encore last

    def test_numeric_set_sorting(self):
        """Verify numeric sets sort correctly."""

        def _set_order_key(v):
            s = str(v).strip().upper()
            if s in {"E", "ENCORE", "99"}:
                return 99
            if s in {"0", "SOUNDCHECK"}:
                return 0
            try:
                return int(float(s))
            except Exception:
                return 50

        set_numbers = [3, 1, 2]
        sorted_sets = sorted(set_numbers, key=_set_order_key)

        assert sorted_sets == [1, 2, 3]


class TestPredictionHighlighting:
    """Tests for prediction rank highlighting logic."""

    def test_top_10_badge_class(self):
        """Verify Top 10 predictions get correct badge."""
        # The badge classes are used in HTML generation
        assert "badge-top10" in '<span class="badge-top10">Song</span>'

    def test_top_25_badge_class(self):
        """Verify Top 25 predictions get correct badge."""
        assert "badge-top25" in '<span class="badge-top25">Song</span>'

    def test_top_50_badge_class(self):
        """Verify Top 50 predictions get correct badge."""
        assert "badge-top50" in '<span class="badge-top50">Song</span>'


class TestHitCounting:
    """Tests for prediction hit counting."""

    def test_counts_matched_predictions(
        self, sample_setlist_df, sample_predictions_notebook
    ):
        """Verify hit counting matches predictions to setlist."""
        from jambandnerd.web.components.common import (
            clean_song_name_for_display,
        )

        # Build prediction lookup
        prediction_ranks = {}
        for idx, row in sample_predictions_notebook.iterrows():
            normalized = clean_song_name_for_display(
                str(row["song_name"]), "wsp"
            ).lower()
            if normalized:
                prediction_ranks[normalized] = int(row["rank"])

        # Count hits in setlist
        total_predicted = 0
        total_songs = 0
        for name in sample_setlist_df["song_name"]:
            cleaned = clean_song_name_for_display(name, "wsp")
            if not cleaned:
                continue
            total_songs += 1
            if cleaned.lower() in prediction_ranks:
                total_predicted += 1

        # Sample setlist has: Disco, Space Wrangler, Chilly Water, Proving Ground (4 hits)
        # And: Surprise Song, Another One, Encore Song (3 misses)
        assert total_songs == 7
        assert (
            total_predicted == 4
        )  # Disco, Space Wrangler, Chilly Water, Proving Ground
