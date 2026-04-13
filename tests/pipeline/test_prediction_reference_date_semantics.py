from __future__ import annotations

from datetime import date

import pandas as pd

from scripts.common import prepare_band_data
from scripts.run_backtest import build_scored_run_records
from src.jambandnerd.models.registry import (
    build_predictor,
    get_model_definition,
    serialize_model_predictions,
)
from src.jambandnerd.transformations.gaps import generate_model_data


def build_notebook_semantics_fixture() -> tuple[pd.DataFrame, pd.DataFrame]:
    shows = pd.DataFrame(
        [
            {"show_id": "show-1", "show_date": "2024-01-01"},
            {"show_id": "show-2", "show_date": "2024-01-02"},
            {"show_id": "show-3", "show_date": "2024-01-03"},
            {"show_id": "show-4", "show_date": "2024-01-04"},
            {"show_id": "show-5", "show_date": "2024-01-05"},
            {"show_id": "show-6", "show_date": "2024-01-10"},
            {"show_id": "show-7", "show_date": "2024-01-11"},
        ]
    )
    setlists = pd.DataFrame(
        [
            {"show_id": "show-1", "song_name": "Alpha"},
            {"show_id": "show-1", "song_name": "Beta"},
            {"show_id": "show-1", "song_name": "Gamma"},
            {"show_id": "show-2", "song_name": "Alpha"},
            {"show_id": "show-2", "song_name": "Beta"},
            {"show_id": "show-2", "song_name": "Delta"},
            {"show_id": "show-3", "song_name": "Alpha"},
            {"show_id": "show-3", "song_name": "Epsilon"},
            {"show_id": "show-3", "song_name": "Zeta"},
            {"show_id": "show-4", "song_name": "Theta"},
            {"show_id": "show-4", "song_name": "Iota"},
            {"show_id": "show-4", "song_name": "Kappa"},
            {"show_id": "show-5", "song_name": "Lambda"},
            {"show_id": "show-5", "song_name": "Mu"},
            {"show_id": "show-5", "song_name": "Nu"},
            {"show_id": "show-6", "song_name": "Alpha"},
            {"show_id": "show-6", "song_name": "Beta"},
            {"show_id": "show-6", "song_name": "Sigma"},
            {"show_id": "show-7", "song_name": "Omicron"},
            {"show_id": "show-7", "song_name": "Pi"},
            {"show_id": "show-7", "song_name": "Rho"},
        ]
    )
    return prepare_band_data(shows, setlists, band="goose")


def notebook_song_names_for_reference_date(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_date: date,
) -> list[str]:
    model_data = generate_model_data(
        shows_df,
        setlists_df,
        reference_date,
        exclusion_window=3,
        band="goose",
    )
    predictor = build_predictor("notebook", band="goose")
    prediction_output = predictor.predict(
        model_data=model_data,
        top_k=get_model_definition("notebook").default_top_k,
    )
    predictions = prediction_output[0] if isinstance(prediction_output, tuple) else prediction_output
    serialized = serialize_model_predictions("notebook", predictions)
    return [row["song_name"] for row in serialized]


def test_backtest_rows_use_previous_day_reference_date_for_completed_show() -> None:
    shows_df, setlists_df = build_notebook_semantics_fixture()

    direct_for_previous_day = notebook_song_names_for_reference_date(
        shows_df,
        setlists_df,
        date(2024, 1, 10),
    )
    direct_for_same_day = notebook_song_names_for_reference_date(
        shows_df,
        setlists_df,
        date(2024, 1, 11),
    )

    target_shows = shows_df[shows_df["show_date"] == date(2024, 1, 11)].copy()
    scored_runs = build_scored_run_records(
        band="goose",
        model="notebook",
        shows_df=shows_df,
        sets_df=setlists_df,
        target_shows=target_shows,
        exclusion_window=3,
    )

    assert len(scored_runs) == 1
    assert scored_runs[0]["target_show_date"] == "2024-01-11"
    assert scored_runs[0]["reference_date"] == "2024-01-10"
    assert [row["song_name"] for row in scored_runs[0]["predictions"]] == direct_for_previous_day
    assert direct_for_same_day != direct_for_previous_day

