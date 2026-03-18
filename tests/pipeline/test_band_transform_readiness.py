from __future__ import annotations

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
