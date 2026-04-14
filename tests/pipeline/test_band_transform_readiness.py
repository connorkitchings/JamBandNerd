from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from scripts.common import prepare_band_data
from src.jambandnerd.transformations.gaps import generate_model_data

from .fixtures import BANDS, band_raw_tables


@pytest.mark.parametrize("band", BANDS)
def test_band_raw_tables_prepare_and_transform_without_leakage(band):
    raw_shows, raw_setlists, reference_date = band_raw_tables(band)

    shows_df = pd.DataFrame(raw_shows)
    setlists_df = pd.DataFrame(raw_setlists)

    prepared_shows, prepared_setlists = prepare_band_data(shows_df, setlists_df)
    model_data = generate_model_data(
        prepared_shows,
        prepared_setlists,
        reference_date,
        band=band,
    )

    assert "show_id" in prepared_shows.columns
    assert "show_id" in prepared_setlists.columns
    assert prepared_shows["show_id"].map(type).eq(str).all()
    assert prepared_setlists["show_id"].map(type).eq(str).all()

    assert not model_data.historical_plays.empty
    assert not model_data.master_feature_set.empty
    assert model_data.reference_date == reference_date
    assert model_data.reference_index == 7
    assert model_data.diagnostics["reference_date"] == reference_date.isoformat()
    assert model_data.diagnostics["total_songs_in_history"] == len(
        model_data.master_feature_set
    )

    assert model_data.historical_plays["show_date"].max() < reference_date
    assert set(model_data.historical_plays["show_id"].unique()) == {
        str(show_id) for show_id in prepared_shows.loc[:5, "show_id"].tolist()
    }
    assert "Future Song" not in set(model_data.historical_plays["song_name"])
    assert len(model_data.recently_played_songs) > 0


def test_generate_model_data_honors_explicit_exclusion_window_override() -> None:
    shows_df = pd.DataFrame(
        [
            {"show_id": "um-show-1", "show_date": "2024-01-01"},
            {"show_id": "um-show-2", "show_date": "2024-01-02"},
            {"show_id": "um-show-3", "show_date": "2024-01-03"},
            {"show_id": "um-show-4", "show_date": "2024-01-04"},
            {"show_id": "um-show-5", "show_date": "2024-01-05"},
            {"show_id": "um-show-6", "show_date": "2024-01-06"},
        ]
    )
    setlists_df = pd.DataFrame(
        [
            {"show_id": "um-show-1", "song_name": "Song 1"},
            {"show_id": "um-show-2", "song_name": "Song 2"},
            {"show_id": "um-show-3", "song_name": "Song 3"},
            {"show_id": "um-show-4", "song_name": "Song 4"},
            {"show_id": "um-show-5", "song_name": "Song 5"},
            {"show_id": "um-show-6", "song_name": "Future Song"},
        ]
    )
    prepared_shows, prepared_setlists = prepare_band_data(
        shows_df,
        setlists_df,
        band="um",
    )

    explicit_model_data = generate_model_data(
        prepared_shows,
        prepared_setlists,
        date(2024, 1, 6),
        exclusion_window=1,
        band="um",
    )
    default_model_data = generate_model_data(
        prepared_shows,
        prepared_setlists,
        date(2024, 1, 6),
        band="um",
    )

    assert explicit_model_data.recently_played_songs == ["Song 5"]
    assert set(default_model_data.recently_played_songs) == {
        "Song 2",
        "Song 3",
        "Song 4",
        "Song 5",
    }
