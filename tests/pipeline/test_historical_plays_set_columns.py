"""Verify that gaps.py plumbs optional set columns through historical_plays."""

from __future__ import annotations

from datetime import date

import pandas as pd

from src.jambandnerd.transformations.gaps import generate_model_data


def _base_shows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"show_id": "g-1", "show_date": "2024-01-10"},
            {"show_id": "g-2", "show_date": "2024-01-11"},
            {"show_id": "g-3", "show_date": "2024-01-12"},
            {"show_id": "g-4", "show_date": "2024-02-01"},  # future
        ]
    )


def _setlists_with_set_cols() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "show_id": "g-1",
                "song_name": "Alpha",
                "set_number": 1,
                "song_position": 1,
                "encore": False,
            },
            {
                "show_id": "g-1",
                "song_name": "Beta",
                "set_number": 2,
                "song_position": 1,
                "encore": False,
            },
            {
                "show_id": "g-2",
                "song_name": "Alpha",
                "set_number": 1,
                "song_position": 3,
                "encore": False,
            },
            {
                "show_id": "g-2",
                "song_name": "Gamma",
                "set_number": 99,
                "song_position": 1,
                "encore": True,
            },
            {
                "show_id": "g-3",
                "song_name": "Beta",
                "set_number": 1,
                "song_position": 2,
                "encore": False,
            },
            {
                "show_id": "g-4",
                "song_name": "Future",
                "set_number": 1,
                "song_position": 1,
                "encore": False,
            },
        ]
    )


def _setlists_without_set_cols() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"show_id": "g-1", "song_name": "Alpha"},
            {"show_id": "g-2", "song_name": "Beta"},
            {"show_id": "g-3", "song_name": "Alpha"},
            {"show_id": "g-4", "song_name": "Future"},
        ]
    )


def test_set_columns_present_when_input_has_them() -> None:
    model_data = generate_model_data(
        _base_shows(), _setlists_with_set_cols(), date(2024, 1, 20), band="goose"
    )
    hp = model_data.historical_plays
    assert "set_number" in hp.columns
    assert "song_position" in hp.columns
    assert "encore" in hp.columns


def test_set_number_nullable_int64() -> None:
    model_data = generate_model_data(
        _base_shows(), _setlists_with_set_cols(), date(2024, 1, 20), band="goose"
    )
    dtype = model_data.historical_plays["set_number"].dtype
    assert pd.api.types.is_integer_dtype(dtype) or str(dtype) == "Int64"


def test_song_position_nullable_int64() -> None:
    model_data = generate_model_data(
        _base_shows(), _setlists_with_set_cols(), date(2024, 1, 20), band="goose"
    )
    dtype = model_data.historical_plays["song_position"].dtype
    assert pd.api.types.is_integer_dtype(dtype) or str(dtype) == "Int64"


def test_encore_bool() -> None:
    model_data = generate_model_data(
        _base_shows(), _setlists_with_set_cols(), date(2024, 1, 20), band="goose"
    )
    hp = model_data.historical_plays
    assert hp["encore"].dtype == bool or str(hp["encore"].dtype) == "bool"
    # Gamma was an encore
    gamma_rows = hp[hp["song_name"] == "Gamma"]
    assert gamma_rows["encore"].all()
    alpha_rows = hp[hp["song_name"] == "Alpha"]
    assert not alpha_rows["encore"].any()


def test_set_columns_absent_when_input_lacks_them() -> None:
    model_data = generate_model_data(
        _base_shows(), _setlists_without_set_cols(), date(2024, 1, 20), band="goose"
    )
    hp = model_data.historical_plays
    assert "set_number" not in hp.columns
    assert "song_position" not in hp.columns
    assert "encore" not in hp.columns


def test_reference_date_invariant_preserved_with_set_cols() -> None:
    ref = date(2024, 1, 20)
    model_data = generate_model_data(
        _base_shows(), _setlists_with_set_cols(), ref, band="goose"
    )
    max_date = pd.to_datetime(model_data.historical_plays["show_date"]).dt.date.max()
    assert max_date < ref


def test_future_song_excluded_with_set_cols() -> None:
    model_data = generate_model_data(
        _base_shows(), _setlists_with_set_cols(), date(2024, 1, 20), band="goose"
    )
    assert "Future" not in model_data.historical_plays["song_name"].values


def test_bands_without_set_cols_load_without_error() -> None:
    """Other bands using a minimal schema must still work cleanly."""
    shows = pd.DataFrame(
        [{"show_id": f"um-{i}", "show_date": f"2024-01-{i:02d}"} for i in range(1, 8)]
    )
    setlists = pd.DataFrame(
        [{"show_id": f"um-{i}", "song_name": f"Song {chr(65+i)}"} for i in range(1, 7)]
    )
    model_data = generate_model_data(shows, setlists, date(2024, 1, 7), band="um")
    assert not model_data.historical_plays.empty
    assert "set_number" not in model_data.historical_plays.columns
