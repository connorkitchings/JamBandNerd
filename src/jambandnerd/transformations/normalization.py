"""Shared normalization helpers for prediction inputs.

These helpers define the normalized show/setlist contract that shared
transforms, predictors, and backtests consume.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from jambandnerd.config.bands import BAND_ID_COLUMNS

SHOW_DATE_CANDIDATES = ("show_date", "showdate")
SONG_NAME_CANDIDATES = ("song_name", "song")


def _copy_first_available_column(
    df: pd.DataFrame, *, target: str, candidates: Iterable[str]
) -> pd.DataFrame:
    """Copy the first present candidate column to the target name."""
    if target in df.columns:
        return df

    for candidate in candidates:
        if candidate in df.columns:
            df[target] = df[candidate]
            return df

    return df


def _require_columns(
    df: pd.DataFrame, *, label: str, required_columns: Iterable[str]
) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"{label} missing normalized columns: {joined}")


def normalize_prediction_inputs(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    *,
    band: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize raw show/setlist inputs for shared prediction code.

    The normalized contract is:

    - shows: `show_id`, `show_date`
    - setlists: `show_id`, `song_name`
    """
    shows = shows_df.copy()
    setlists = setlists_df.copy()

    band_id_column = BAND_ID_COLUMNS.get(band) if band else None
    show_id_candidates = tuple(
        dict.fromkeys(
            column
            for column in (band_id_column, "show_id", "api_show_id")
            if column is not None
        )
    )

    shows = _copy_first_available_column(
        shows, target="show_id", candidates=show_id_candidates
    )
    setlists = _copy_first_available_column(
        setlists, target="show_id", candidates=show_id_candidates
    )
    shows = _copy_first_available_column(
        shows, target="show_date", candidates=SHOW_DATE_CANDIDATES
    )
    setlists = _copy_first_available_column(
        setlists, target="song_name", candidates=SONG_NAME_CANDIDATES
    )

    _require_columns(shows, label="shows", required_columns=("show_id", "show_date"))
    _require_columns(
        setlists, label="setlists", required_columns=("show_id", "song_name")
    )

    shows["show_date"] = pd.to_datetime(shows["show_date"], errors="coerce").dt.date
    shows["show_id"] = shows["show_id"].astype(str).str.strip()
    setlists["show_id"] = setlists["show_id"].astype(str).str.strip()
    setlists["song_name"] = setlists["song_name"].astype(str).str.strip()

    shows = shows.loc[shows["show_date"].notna() & shows["show_id"].ne("")].copy()
    setlists = setlists.loc[
        setlists["show_id"].ne("") & setlists["song_name"].ne("")
    ].copy()

    return shows, setlists


def sort_normalized_shows(shows_df: pd.DataFrame) -> pd.DataFrame:
    """Return shows sorted by the canonical historical sequence contract."""
    _require_columns(shows_df, label="shows", required_columns=("show_id", "show_date"))
    shows = shows_df.copy()
    shows["show_id"] = shows["show_id"].astype(str).str.strip()
    shows["show_date"] = pd.to_datetime(shows["show_date"], errors="coerce").dt.date
    shows = shows.loc[shows["show_date"].notna() & shows["show_id"].ne("")].copy()
    return shows.sort_values(by=["show_date", "show_id"]).reset_index(drop=True)
