from __future__ import annotations

from datetime import date

import pandas as pd

from scripts.common import prepare_band_data
from src.jambandnerd.transformations.normalization import sort_normalized_shows


def test_prepare_band_data_normalizes_band_specific_show_id_columns():
    shows_df = pd.DataFrame(
        [
            {"api_show_id": 2002, "show_date": "2024-03-02"},
            {"api_show_id": 2001, "show_date": "2024-03-01"},
        ]
    )
    setlists_df = pd.DataFrame(
        [
            {"api_show_id": 2002, "song": "Tweezer"},
            {"api_show_id": 2001, "song": "Bathtub Gin"},
        ]
    )

    prepared_shows, prepared_setlists = prepare_band_data(
        shows_df, setlists_df, band="phish"
    )

    assert list(prepared_shows["show_id"]) == ["2002", "2001"]
    assert list(prepared_setlists["show_id"]) == ["2002", "2001"]
    assert list(prepared_setlists["song_name"]) == ["Tweezer", "Bathtub Gin"]
    assert prepared_shows["show_date"].tolist() == [
        date(2024, 3, 2),
        date(2024, 3, 1),
    ]


def test_sort_normalized_shows_uses_show_id_as_same_day_tiebreaker():
    shows_df = pd.DataFrame(
        [
            {"show_id": "show-b", "show_date": "2024-03-01"},
            {"show_id": "show-a", "show_date": "2024-03-01"},
            {"show_id": "show-c", "show_date": "2024-03-02"},
        ]
    )

    sorted_shows = sort_normalized_shows(shows_df)

    assert sorted_shows["show_id"].tolist() == ["show-a", "show-b", "show-c"]


def test_prepare_band_data_excludes_configured_prediction_show_ids():
    shows_df = pd.DataFrame(
        [
            {"show_id": "1755099318", "show_date": "2025-08-13"},
            {"show_id": "1748090458", "show_date": "2025-05-25"},
            {"show_id": "1736785860", "show_date": "2025-05-25"},
            {"show_id": "goose-real", "show_date": "2025-08-14"},
        ]
    )
    setlists_df = pd.DataFrame(
        [
            {"show_id": "1755099318", "song_name": "TV Song"},
            {"show_id": "1748090458", "song_name": "Short Set Song"},
            {"show_id": "1736785860", "song_name": "Full Set Song"},
            {"show_id": "goose-real", "song_name": "Real Song"},
        ]
    )

    prepared_shows, prepared_setlists = prepare_band_data(
        shows_df, setlists_df, band="goose"
    )

    result_ids = prepared_shows["show_id"].tolist()
    assert "goose-real" in result_ids
    assert "1736785860" in result_ids
    assert "1755099318" not in result_ids
    assert "1748090458" not in result_ids
    assert prepared_setlists["show_id"].tolist() == prepared_shows["show_id"].tolist()
