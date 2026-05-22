from __future__ import annotations

import pandas as pd

from src.jambandnerd.models.evaluation import list_completed_shows


def test_list_completed_shows_excludes_partial_setlists() -> None:
    shows_df = pd.DataFrame(
        [
            {"show_id": "full", "show_date": "2026-05-21"},
            {"show_id": "partial", "show_date": "2026-05-22"},
        ]
    )
    setlists_df = pd.DataFrame(
        [
            {"show_id": "full", "song_name": "Song A"},
            {"show_id": "full", "song_name": "Song B"},
            {"show_id": "full", "song_name": "Song C"},
            {"show_id": "partial", "song_name": "Song A"},
            {"show_id": "partial", "song_name": "Song B"},
        ]
    )

    completed = list_completed_shows(shows_df, setlists_df)

    assert completed["show_id"].tolist() == ["full"]
