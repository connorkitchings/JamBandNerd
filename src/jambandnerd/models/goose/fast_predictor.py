"""Goose fast predictor — compact vectorized ranker experiment."""

from __future__ import annotations

from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from jambandnerd.config import BAND_EXCLUSION_WINDOWS, EXCLUSION_WINDOW_DEFAULT
from jambandnerd.config.bands import get_excluded_songs
from jambandnerd.models.base import PredictionModel
from jambandnerd.models.deal.model import DealPrediction
from jambandnerd.transformations.gaps import ModelData
from jambandnerd.transformations.run_context import (
    normalize_target_show_context,
    normalized_venue_key,
    same_venue_run_show_indices,
)
from jambandnerd.transformations.set_position import (
    SET_POSITION_FEATURES,
)

from .features import _run_position, _tour_position

_MIN_PLAYS = 3
_RETIRED_GAP = 90
_TRAINING_WINDOW = 60

GOOSE_FAST_FEATURE_COLS: list[str] = [
    "current_gap",
    "plays_past_3",
    "plays_past_5",
    "plays_past_10",
    "plays_past_25",
    "plays_past_50",
    "career_play_pct",
    "month_play_rate",
    "diff_25_to_50",
    "show_position_in_run",
    "tour_position",
    "same_venue_run_position",
    "overdue_ratio",
    "avg_ltp_recent",
    "ltp_diff_recent",
]

GOOSE_MATRIX_EXTRA_FEATURE_COLS: list[str] = [
    "avg_ltp",
    "recent_avg_ltp",
    "gap_z_score",
    "pct_shows_1yr",
    "pct_shows_all_time",
    "diff_1yr_to_alltime",
    *SET_POSITION_FEATURES,
]

GOOSE_MATRIX_FEATURE_COLS: list[str] = [
    *GOOSE_FAST_FEATURE_COLS,
    *GOOSE_MATRIX_EXTRA_FEATURE_COLS,
]

GOOSE_MATRIX_V2_EXTRA_FEATURE_COLS: list[str] = [
    "plays_past_year",
    "plays_past_2yr",
    "pct_shows_6mo",
    "diff_6mo_to_1yr",
    "n_shows_same_venue",
    "n_shows_same_state",
    "debut_age_shows",
    "novelty_rank",
    "recent_anchor_cooc_mean",
    "recent_anchor_cooc_max",
    "last_show_cooc_mean",
    "last_show_cooc_max",
]

GOOSE_MATRIX_V2_FEATURE_COLS: list[str] = [
    *GOOSE_MATRIX_FEATURE_COLS,
    *GOOSE_MATRIX_V2_EXTRA_FEATURE_COLS,
]

_LGB_PARAMS: dict[str, Any] = {
    "objective": "rank_xendcg",
    "metric": "ndcg",
    "eval_at": [10, 25, 50],
    "num_leaves": 31,
    "learning_rate": 0.05,
    "min_data_in_leaf": 5,
    "verbose": -1,
    "seed": 42,
}
_LGB_ROUNDS = 200


def _clean_plays(plays: pd.DataFrame) -> pd.DataFrame:
    base_columns = ["song_name", "show_index", "show_date"]
    context_columns = [
        column
        for column in ("venue_name", "city", "state", "country")
        if column in plays.columns
    ]
    set_columns = [
        column
        for column in ("set_number", "song_position", "encore")
        if column in plays.columns
    ]
    df = plays[base_columns + context_columns + set_columns].copy()
    df = df.dropna(subset=["song_name", "show_index", "show_date"])
    df["show_date"] = pd.to_datetime(df["show_date"], errors="coerce")
    df["show_index"] = pd.to_numeric(df["show_index"], errors="coerce")
    if "set_number" in df.columns:
        df["set_number"] = pd.to_numeric(df["set_number"], errors="coerce").astype(
            "Int64"
        )
    if "song_position" in df.columns:
        df["song_position"] = pd.to_numeric(
            df["song_position"], errors="coerce"
        ).astype("Int64")
    if "encore" in df.columns:
        df["encore"] = df["encore"].fillna(False).astype(bool)
    df = df.dropna(subset=["show_date", "show_index"])
    df["show_index"] = df["show_index"].astype(int)
    return df.reset_index(drop=True)


def _build_presence(plays: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    presence = (
        plays.groupby(["song_name", "show_index"])
        .size()
        .gt(0)
        .unstack(fill_value=False)
    )
    show_cols = presence.columns.to_numpy(dtype=np.int64)
    return presence, show_cols


def _build_current_gap_matrix(presence: pd.DataFrame) -> pd.DataFrame:
    """Completed-show gap before each target column."""
    n_shows = presence.shape[1]
    col_pos = np.arange(n_shows, dtype=float)
    play_col = np.where(presence.values, col_pos[np.newaxis, :], np.nan)
    last_play = pd.DataFrame(
        play_col, index=presence.index, columns=presence.columns
    ).ffill(axis=1)
    last_play_before = last_play.shift(1, axis=1)
    gap_arr = col_pos[np.newaxis, :] - last_play_before.values - 1.0
    gap_arr = np.where(np.isnan(last_play_before.values), float(n_shows), gap_arr)
    gap_arr = np.clip(gap_arr, 0.0, None)
    return pd.DataFrame(gap_arr, index=presence.index, columns=presence.columns)


def _current_gap_for_prediction(presence: pd.DataFrame) -> pd.Series:
    n_shows = presence.shape[1]
    col_pos = np.arange(n_shows, dtype=float)
    play_col = np.where(presence.values, col_pos[np.newaxis, :], np.nan)
    last_play = pd.DataFrame(
        play_col, index=presence.index, columns=presence.columns
    ).ffill(axis=1)
    last_play_col = last_play.iloc[:, -1]
    gap = n_shows - last_play_col - 1.0
    return gap.fillna(float(n_shows)).clip(lower=0.0).astype(float)


def _window_plays(cum: pd.DataFrame, upper_col: int, window: int) -> pd.Series:
    end = upper_col - 1
    if end < 0:
        return pd.Series(0.0, index=cum.index)
    end = min(end, cum.shape[1] - 1)
    start = max(0, upper_col - window)
    if start == 0:
        return cum.iloc[:, end].astype(float)
    return (cum.iloc[:, end] - cum.iloc[:, start - 1]).astype(float)


def _build_month_cums(
    plays: pd.DataFrame,
    presence: pd.DataFrame,
) -> dict[int, pd.DataFrame]:
    all_songs = presence.index
    cols = presence.columns
    month_cums: dict[int, pd.DataFrame] = {}
    for month in range(1, 13):
        month_presence = (
            plays[plays["_month"] == month]
            .groupby(["song_name", "show_index"])
            .size()
            .unstack(fill_value=0)
            .reindex(index=all_songs, columns=cols, fill_value=0)
            .astype(float)
        )
        month_cums[month] = month_presence.cumsum(axis=1)
    return month_cums


def _sum_matrix(
    plays: pd.DataFrame,
    value_column: str,
    presence: pd.DataFrame,
) -> pd.DataFrame:
    return (
        plays.groupby(["song_name", "show_index"])[value_column]
        .sum()
        .unstack(fill_value=0.0)
        .reindex(index=presence.index, columns=presence.columns, fill_value=0.0)
        .astype(float)
    )


def _build_set_position_cums(
    plays: pd.DataFrame,
    presence: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    prepared = plays[["song_name", "show_index"]].copy()
    prepared["_set_1"] = 0.0
    prepared["_set_2"] = 0.0
    prepared["_encore"] = 0.0
    prepared["_position"] = 0.0
    prepared["_position_sq"] = 0.0
    prepared["_position_count"] = 0.0

    if "set_number" in plays.columns:
        set_number = pd.to_numeric(plays["set_number"], errors="coerce")
        prepared["_set_1"] = (set_number == 1).astype(float)
        prepared["_set_2"] = (set_number == 2).astype(float)
    if "encore" in plays.columns:
        prepared["_encore"] = plays["encore"].fillna(False).astype(bool).astype(float)
    if "song_position" in plays.columns:
        song_position = pd.to_numeric(plays["song_position"], errors="coerce")
        max_position = (
            plays.assign(_song_position=song_position)
            .groupby("show_index")["_song_position"]
            .transform("max")
        )
        normalized = ((song_position - 1.0) / (max_position - 1.0)).where(
            max_position > 1.0,
            0.5,
        )
        normalized = normalized.fillna(0.0).astype(float)
        has_position = song_position.notna().astype(float)
        prepared["_position"] = normalized * has_position
        prepared["_position_sq"] = (normalized**2) * has_position
        prepared["_position_count"] = has_position

    cums: dict[str, pd.DataFrame] = {}
    for column in (
        "_set_1",
        "_set_2",
        "_encore",
        "_position",
        "_position_sq",
        "_position_count",
    ):
        cums[column] = _sum_matrix(prepared, column, presence).cumsum(axis=1)
    return cums


def _ltp_stat_arrays(
    *,
    eligible_songs: pd.Index,
    upper_col: int,
    gap_e: pd.Series,
    presence: pd.DataFrame,
    show_cols: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    avg_values: list[float] = []
    recent_values: list[float] = []
    z_values: list[float] = []
    for song_name in eligible_songs:
        row = presence.loc[song_name].to_numpy(dtype=bool)[:upper_col]
        play_cols = np.where(row)[0]
        if len(play_cols) >= 2:
            played_show_indices = show_cols[play_cols].astype(float)
            gaps = np.diff(played_show_indices)
            avg_ltp = float(np.mean(gaps))
            recent = gaps[-10:]
            recent_avg_ltp = float(np.mean(recent)) if len(recent) else avg_ltp
            std_gap = float(np.std(gaps, ddof=0))
            gap_z = (
                (float(gap_e.loc[song_name]) - avg_ltp) / std_gap
                if std_gap > 0
                else 0.0
            )
        else:
            avg_ltp = 0.0
            recent_avg_ltp = 0.0
            gap_z = 0.0
        avg_values.append(avg_ltp)
        recent_values.append(recent_avg_ltp)
        z_values.append(gap_z)
    return (
        np.array(avg_values, dtype=float),
        np.array(recent_values, dtype=float),
        np.array(z_values, dtype=float),
    )


def _one_year_rate_features(
    *,
    eligible_songs: pd.Index,
    total_e: pd.Series,
    upper_col: int,
    target_date: Any,
    plays: pd.DataFrame,
    target_show_index: int | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pct_all_time = (total_e / max(1, upper_col)).reindex(eligible_songs).fillna(0.0)
    if target_date is None:
        pct_1yr = pd.Series(0.0, index=eligible_songs)
    else:
        cutoff = pd.Timestamp(target_date) - pd.Timedelta(days=365)
        if target_show_index is not None:
            historical = plays[plays["show_index"] < target_show_index]
        else:
            historical = plays
        window_plays = historical[
            (historical["show_date"] >= cutoff)
            & (historical["show_date"] < pd.Timestamp(target_date))
        ]
        window_show_count = max(1, window_plays["show_index"].nunique())
        pct_1yr = (
            window_plays.groupby("song_name")["show_index"]
            .nunique()
            .reindex(eligible_songs, fill_value=0)
            .astype(float)
            / window_show_count
        )
    diff = pct_1yr - pct_all_time
    return (
        pct_1yr.to_numpy(dtype=float),
        pct_all_time.to_numpy(dtype=float),
        diff.to_numpy(dtype=float),
    )


def _window_rate_features(
    *,
    eligible_songs: pd.Index,
    target_date: Any,
    plays: pd.DataFrame,
    target_show_index: int | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if target_date is None:
        zeros = np.zeros(len(eligible_songs), dtype=float)
        return zeros, zeros, zeros, zeros

    target_timestamp = pd.Timestamp(target_date)
    historical = (
        plays[plays["show_index"] < target_show_index]
        if target_show_index is not None
        else plays
    )

    def _counts_for_days(days: int) -> tuple[pd.Series, int]:
        window = historical[
            (historical["show_date"] >= target_timestamp - pd.Timedelta(days=days))
            & (historical["show_date"] < target_timestamp)
        ]
        show_count = max(1, window["show_index"].nunique())
        counts = (
            window.groupby("song_name")["show_index"]
            .nunique()
            .reindex(eligible_songs, fill_value=0)
            .astype(float)
        )
        return counts, show_count

    counts_6mo, shows_6mo = _counts_for_days(182)
    counts_1yr, shows_1yr = _counts_for_days(365)
    counts_2yr, _shows_2yr = _counts_for_days(730)
    pct_6mo = counts_6mo / shows_6mo
    pct_1yr = counts_1yr / shows_1yr
    return (
        counts_1yr.to_numpy(dtype=float),
        counts_2yr.to_numpy(dtype=float),
        pct_6mo.to_numpy(dtype=float),
        (pct_6mo - pct_1yr).to_numpy(dtype=float),
    )


def _history_context_counts(
    *,
    eligible_songs: pd.Index,
    plays: pd.DataFrame,
    target_show_index: int | None,
) -> tuple[np.ndarray, np.ndarray]:
    historical = (
        plays[plays["show_index"] < target_show_index]
        if target_show_index is not None
        else plays
    )
    if historical.empty:
        zeros = np.zeros(len(eligible_songs), dtype=float)
        return zeros, zeros

    venue_counts: dict[str, float] = {}
    state_counts: dict[str, float] = {}
    has_venue = "venue_name" in historical.columns
    has_state = "state" in historical.columns
    for song_name, group in historical.groupby("song_name"):
        ordered = group.sort_values("show_index")
        last_row = ordered.iloc[-1]
        if has_venue:
            venue = last_row.get("venue_name")
            venue_counts[str(song_name)] = (
                float(ordered[ordered["venue_name"] == venue]["show_index"].nunique())
                if pd.notna(venue) and venue
                else 0.0
            )
        if has_state:
            state = last_row.get("state")
            state_counts[str(song_name)] = (
                float(ordered[ordered["state"] == state]["show_index"].nunique())
                if pd.notna(state) and state
                else 0.0
            )

    return (
        np.array([venue_counts.get(str(song), 0.0) for song in eligible_songs]),
        np.array([state_counts.get(str(song), 0.0) for song in eligible_songs]),
    )


def _debut_novelty_arrays(
    *,
    eligible_songs: pd.Index,
    total_e: pd.Series,
    upper_col: int,
    presence: pd.DataFrame,
    show_cols: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    debut_cols: dict[str, int] = {}
    debut_show_indices: dict[str, float] = {}
    for song_name in presence.index:
        row = presence.loc[song_name].to_numpy(dtype=bool)[:upper_col]
        play_cols = np.where(row)[0]
        if len(play_cols) > 0:
            debut_cols[str(song_name)] = int(play_cols[0])
            debut_show_indices[str(song_name)] = float(show_cols[int(play_cols[0])])

    debut_age = np.array(
        [
            float(upper_col - debut_cols.get(str(song), upper_col))
            for song in eligible_songs
        ],
        dtype=float,
    )

    all_songs = pd.Index([song for song in presence.index if str(song) in debut_cols])
    if len(all_songs) == 0:
        return debut_age, np.zeros(len(eligible_songs), dtype=float)

    all_debuts = np.array(
        [debut_show_indices[str(song)] for song in all_songs],
        dtype=float,
    )
    all_totals = total_e.reindex(all_songs).fillna(0.0).to_numpy(dtype=float)
    novelty: list[float] = []
    for song in eligible_songs:
        song_key = str(song)
        debut = debut_show_indices.get(song_key, float(upper_col))
        total = float(total_e.get(song, 0.0))
        novelty.append(float(((all_debuts < debut) & (all_totals < total)).sum()))
    return debut_age, np.array(novelty, dtype=float)


def _anchor_songs(
    *,
    presence: pd.DataFrame,
    upper_col: int,
    window: int,
) -> pd.Index:
    if upper_col <= 0:
        return pd.Index([])
    start = max(0, upper_col - window)
    played = presence.iloc[:, start:upper_col].any(axis=1)
    return presence.index[played]


def _matrix_cooc_features(
    *,
    eligible_songs: pd.Index,
    anchor_songs: pd.Index,
    upper_col: int,
    presence: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    if len(eligible_songs) == 0 or len(anchor_songs) == 0 or upper_col <= 0:
        zeros = np.zeros(len(eligible_songs), dtype=float)
        return zeros, zeros
    usable_anchors = anchor_songs.intersection(presence.index)
    if len(usable_anchors) == 0:
        zeros = np.zeros(len(eligible_songs), dtype=float)
        return zeros, zeros

    candidate_matrix = (
        presence.loc[eligible_songs].iloc[:, :upper_col].to_numpy(dtype=float)
    )
    anchor_matrix = (
        presence.loc[usable_anchors].iloc[:, :upper_col].to_numpy(dtype=float)
    )
    anchor_totals = np.maximum(anchor_matrix.sum(axis=1), 1.0)
    co_counts = candidate_matrix @ anchor_matrix.T
    rates = co_counts / anchor_totals[np.newaxis, :]
    return rates.mean(axis=1), rates.max(axis=1)


def _set_position_arrays(
    *,
    eligible_songs: pd.Index,
    upper_col: int,
    cache: dict[str, Any],
) -> pd.DataFrame:
    cums = cache.get("set_position_cums")
    if not cums or upper_col <= 0:
        return pd.DataFrame(0.0, index=eligible_songs, columns=SET_POSITION_FEATURES)
    col = min(upper_col - 1, cums["_set_1"].shape[1] - 1)
    set_1 = cums["_set_1"].iloc[:, col].reindex(eligible_songs).fillna(0.0)
    set_2 = cums["_set_2"].iloc[:, col].reindex(eligible_songs).fillna(0.0)
    encore = cums["_encore"].iloc[:, col].reindex(eligible_songs).fillna(0.0)
    position = cums["_position"].iloc[:, col].reindex(eligible_songs).fillna(0.0)
    position_sq = cums["_position_sq"].iloc[:, col].reindex(eligible_songs).fillna(0.0)
    position_count = (
        cums["_position_count"].iloc[:, col].reindex(eligible_songs).fillna(0.0)
    )
    total = cache["cum"].iloc[:, col].reindex(eligible_songs).fillna(0.0)

    pct_set_1 = (set_1 / total.clip(lower=1.0)).fillna(0.0)
    pct_set_2 = (set_2 / total.clip(lower=1.0)).fillna(0.0)
    pct_encore = (encore / total.clip(lower=1.0)).fillna(0.0)
    typical_position = (position / position_count.clip(lower=1.0)).fillna(0.0)
    variance = (position_sq / position_count.clip(lower=1.0)) - typical_position**2
    position_consistency = np.sqrt(np.clip(variance.to_numpy(dtype=float), 0.0, None))
    set_denominator = (set_1 + set_2).clip(lower=1.0)
    set_affinity = (set_2 / set_denominator).fillna(0.0)

    return pd.DataFrame(
        {
            "pct_set_1": pct_set_1.to_numpy(dtype=float),
            "pct_set_2": pct_set_2.to_numpy(dtype=float),
            "pct_encore": pct_encore.to_numpy(dtype=float),
            "typical_position_pct": typical_position.to_numpy(dtype=float),
            "position_consistency": position_consistency,
            "set_affinity": set_affinity.to_numpy(dtype=float),
        },
        index=eligible_songs,
    )


class GooseFastPredictor(PredictionModel):
    """Goose compact LightGBM ranker using Billy-style matrix features."""

    MODEL_VERSION = "goose_fast_gbm_v1"
    _FEATURE_COLS: list[str] = GOOSE_FAST_FEATURE_COLS
    _LGB_PARAMS: dict[str, Any] = _LGB_PARAMS
    _LGB_ROUNDS: int = _LGB_ROUNDS

    def __init__(
        self,
        band: str = "goose",
        persist_artifacts: bool = True,
        **kwargs: Any,
    ) -> None:
        if band != "goose":
            raise ValueError("GooseFastPredictor only supports band='goose'.")
        self.band = band
        self.persist_artifacts = persist_artifacts
        self.min_plays_threshold = int(kwargs.pop("min_plays_threshold", _MIN_PLAYS))
        self.retired_gap_threshold = int(
            kwargs.pop("retired_gap_threshold", _RETIRED_GAP)
        )
        self.training_window_shows = int(
            kwargs.pop("training_window_shows", _TRAINING_WINDOW)
        )
        self.exclusion_window = int(
            kwargs.pop(
                "exclusion_window",
                BAND_EXCLUSION_WINDOWS.get(band, EXCLUSION_WINDOW_DEFAULT),
            )
        )
        self._model: lgb.Booster | None = None
        self._cache: dict[str, Any] | None = None

    def _prepare(self, plays: pd.DataFrame) -> dict[str, Any]:
        plays = plays.copy()
        plays["_month"] = plays["show_date"].dt.month
        presence, show_cols = _build_presence(plays)
        cum = presence.astype(float).cumsum(axis=1)
        gap_mat = _build_current_gap_matrix(presence)
        month_cums = _build_month_cums(plays, presence)

        show_date_map = (
            plays[["show_index", "show_date"]]
            .drop_duplicates("show_index")
            .set_index("show_index")["show_date"]
            .to_dict()
        )
        col_dates = [
            (
                pd.Timestamp(show_date_map[int(show_index)]).date()
                if int(show_index) in show_date_map
                else None
            )
            for show_index in show_cols
        ]
        venue_map: dict[int, Any] = {}
        if "venue_name" in plays.columns:
            venue_map = (
                plays[["show_index", "venue_name"]]
                .dropna(subset=["venue_name"])
                .drop_duplicates("show_index")
                .set_index("show_index")["venue_name"]
                .to_dict()
            )
        col_venues = [venue_map.get(int(show_index)) for show_index in show_cols]
        last_play_dates = (
            plays.sort_values("show_index")
            .groupby("song_name")["show_date"]
            .max()
            .to_dict()
        )

        return {
            "presence": presence,
            "show_cols": show_cols,
            "cum": cum,
            "gap_mat": gap_mat,
            "month_cums": month_cums,
            "show_date_map": show_date_map,
            "col_dates": col_dates,
            "col_venues": col_venues,
            "last_play_dates": last_play_dates,
        }

    def _context_features(
        self,
        *,
        eligible_songs: pd.Index,
        upper_col: int,
        target_date: Any,
        p25: pd.Series,
        p50: pd.Series,
        cache: dict[str, Any],
        plays: pd.DataFrame,
        target_show_context: Any,
        target_show_index: int | None,
    ) -> dict[str, Any]:
        col_dates = cache["col_dates"]
        prior_dates = [date_value for date_value in col_dates[:upper_col] if date_value]
        if target_date is None:
            tour_position = 1.0
            show_position = 1.0
        else:
            tour_position = float(
                _tour_position(prior_dates, target_date, tour_gap_days=14)
            )
            show_position = float(_run_position(prior_dates, target_date, gap_days=1))

        pct25 = p25 / max(1, min(25, upper_col))
        pct50 = p50 / max(1, min(50, upper_col))

        normalized_ctx = normalize_target_show_context(target_show_context or {})
        if not normalized_venue_key(normalized_ctx) and target_show_index is not None:
            col_venues = cache["col_venues"]
            target_col = np.where(cache["show_cols"] == target_show_index)[0]
            if len(target_col) > 0:
                venue = col_venues[int(target_col[0])]
                normalized_ctx = normalize_target_show_context({"venue_name": venue})

        if normalized_venue_key(normalized_ctx):
            sub_plays = (
                plays[plays["show_index"] < target_show_index]
                if target_show_index is not None
                else plays
            )
            same_run_indices = same_venue_run_show_indices(sub_plays, normalized_ctx)
            same_venue_run_position = float(len(same_run_indices) + 1)
        else:
            same_venue_run_position = 0.0

        return {
            "diff_25_to_50": (pct25 - pct50).values,
            "show_position_in_run": show_position,
            "tour_position": tour_position,
            "same_venue_run_position": same_venue_run_position,
        }

    def _candidate_min_plays(self, target_show_context: Any) -> int:
        """Minimum historical plays required for candidate eligibility."""
        return self.min_plays_threshold

    def _candidate_recent_gap_floor(self, target_show_context: Any) -> int:
        """Minimum show gap required for candidate eligibility."""
        return self.exclusion_window

    def _feature_frame_for_target(
        self,
        *,
        eligible_songs: pd.Index,
        upper_col: int,
        target_date: Any,
        gap_e: pd.Series,
        total_e: pd.Series,
        cache: dict[str, Any],
        plays: pd.DataFrame,
        target_show_context: Any,
        target_show_index: int | None,
    ) -> pd.DataFrame:
        cum = cache["cum"]
        month_cums = cache["month_cums"]
        p3 = _window_plays(cum, upper_col, 3).loc[eligible_songs]
        p5 = _window_plays(cum, upper_col, 5).loc[eligible_songs]
        p10 = _window_plays(cum, upper_col, 10).loc[eligible_songs]
        p25 = _window_plays(cum, upper_col, 25).loc[eligible_songs]
        p50 = _window_plays(cum, upper_col, 50).loc[eligible_songs]
        career_pct = total_e / max(1, upper_col)

        target_month = target_date.month if target_date is not None else 1
        month_before = (
            month_cums[target_month].iloc[:, max(0, upper_col - 1)].loc[eligible_songs]
        )
        month_play_rate = (month_before / total_e.clip(lower=1)).fillna(0.0)
        context = self._context_features(
            eligible_songs=eligible_songs,
            upper_col=upper_col,
            target_date=target_date,
            p25=p25,
            p50=p50,
            cache=cache,
            plays=plays,
            target_show_context=target_show_context,
            target_show_index=target_show_index,
        )
        window = max(1, min(25, upper_col))
        avg_ltp_recent = window / p25.clip(lower=1).values

        return pd.DataFrame(
            {
                "song_name": eligible_songs.to_numpy(),
                "current_gap": gap_e.values,
                "plays_past_3": p3.values,
                "plays_past_5": p5.values,
                "plays_past_10": p10.values,
                "plays_past_25": p25.values,
                "plays_past_50": p50.values,
                "career_play_pct": career_pct.values,
                "month_play_rate": month_play_rate.values,
                **context,
                "overdue_ratio": (gap_e * career_pct).values,
                "avg_ltp_recent": avg_ltp_recent,
                "ltp_diff_recent": gap_e.values - avg_ltp_recent,
            }
        )

    def build_diagnostic_training_frame(self, model_data: ModelData) -> pd.DataFrame:
        plays = _clean_plays(model_data.historical_plays)
        columns = ["song_name", "target_show_index", *self._FEATURE_COLS, "label"]
        if plays.empty:
            return pd.DataFrame(columns=columns)

        cache = self._prepare(plays)
        rows: list[pd.DataFrame] = []
        for frame, _group_size in self._iter_training_frames(plays, cache):
            rows.append(frame)
        if not rows:
            return pd.DataFrame(columns=columns)
        return pd.concat(rows, ignore_index=True)[columns]

    def _iter_training_frames(
        self,
        plays: pd.DataFrame,
        cache: dict[str, Any],
    ) -> list[tuple[pd.DataFrame, int]]:
        presence = cache["presence"]
        cum = cache["cum"]
        gap_mat = cache["gap_mat"]
        show_cols = cache["show_cols"]
        show_date_map = cache["show_date_map"]
        all_songs = presence.index
        n_shows = len(show_cols)
        start_col = self.min_plays_threshold
        excluded_songs = get_excluded_songs(self.band)
        frames: list[tuple[pd.DataFrame, int]] = []

        for col in range(start_col, n_shows):
            ref_col = col - 1
            total_before = cum.iloc[:, ref_col]
            gap_at_target = gap_mat.iloc[:, col]
            target_show_index = int(show_cols[col])
            target_date_raw = show_date_map.get(target_show_index)
            target_date = (
                pd.Timestamp(target_date_raw).date()
                if target_date_raw is not None
                else None
            )
            target_rows = plays[plays["show_index"] == target_show_index]
            target_context = (
                normalize_target_show_context(target_rows.iloc[0])
                if not target_rows.empty
                else {}
            )
            min_plays = self._candidate_min_plays(target_context)
            recent_gap_floor = self._candidate_recent_gap_floor(target_context)
            recent_plays = _window_plays(cum, col, recent_gap_floor)
            eligible_mask = (
                (total_before >= min_plays)
                & (gap_at_target >= recent_gap_floor)
                & (gap_at_target <= self.retired_gap_threshold)
                & (recent_plays == 0)
            )
            if excluded_songs:
                song_index = all_songs.astype(str).str.lower().str.strip()
                eligible_mask &= ~song_index.isin(excluded_songs)
            if not eligible_mask.any():
                continue

            eligible_songs = all_songs[eligible_mask]
            frame = self._feature_frame_for_target(
                eligible_songs=eligible_songs,
                upper_col=col,
                target_date=target_date,
                gap_e=gap_at_target.loc[eligible_songs],
                total_e=total_before.loc[eligible_songs],
                cache=cache,
                plays=plays,
                target_show_context=target_context,
                target_show_index=target_show_index,
            )
            labels = presence.iloc[:, col].loc[eligible_songs].astype(float)
            frame["label"] = labels.values
            frame["target_show_index"] = target_show_index
            frames.append((frame, len(eligible_songs)))
        return frames

    def train(self, model_data: ModelData) -> None:
        plays = _clean_plays(model_data.historical_plays)
        if plays.empty:
            return

        cache = self._prepare(plays)
        self._cache = cache
        frame_groups = self._iter_training_frames(plays, cache)
        if not frame_groups:
            return

        rows = [frame for frame, _group_size in frame_groups]
        group_sizes = [group_size for _frame, group_size in frame_groups]
        training_frame = pd.concat(rows, ignore_index=True)
        labels = training_frame.pop("label")
        if labels.sum() == 0:
            return

        train_data = lgb.Dataset(
            training_frame[self._FEATURE_COLS],
            label=labels,
            group=group_sizes,
            free_raw_data=False,
        )
        self._model = lgb.train(
            self._LGB_PARAMS,
            train_data,
            num_boost_round=self._LGB_ROUNDS,
        )

    def predict(self, model_data: ModelData, top_k: int = 50) -> list[DealPrediction]:
        if self._model is None:
            return []

        plays = _clean_plays(model_data.historical_plays)
        if plays.empty:
            return []

        cache = self._cache if self._cache is not None else self._prepare(plays)
        presence = cache["presence"]
        cum = cache["cum"]
        all_songs = presence.index
        n_shows = presence.shape[1]
        ref_col = n_shows - 1
        total_plays = cum.iloc[:, ref_col]
        current_gap = _current_gap_for_prediction(presence)
        target_context = normalize_target_show_context(model_data.target_show_context)
        min_plays = self._candidate_min_plays(target_context)
        recent_gap_floor = self._candidate_recent_gap_floor(target_context)

        recent_set = set(model_data.recently_played_songs)
        eligible_mask = (
            (total_plays >= min_plays)
            & (current_gap >= recent_gap_floor)
            & (current_gap <= self.retired_gap_threshold)
        )
        if recent_gap_floor > 0:
            eligible_mask &= ~all_songs.isin(recent_set)
        excluded_songs = get_excluded_songs(self.band)
        if excluded_songs:
            song_index = all_songs.astype(str).str.lower().str.strip()
            eligible_mask &= ~song_index.isin(excluded_songs)
        eligible_songs = all_songs[eligible_mask]
        if len(eligible_songs) == 0:
            return []

        ref_date = pd.Timestamp(model_data.reference_date).date()
        features = self._feature_frame_for_target(
            eligible_songs=eligible_songs,
            upper_col=n_shows,
            target_date=ref_date,
            gap_e=current_gap.loc[eligible_songs],
            total_e=total_plays.loc[eligible_songs],
            cache=cache,
            plays=plays,
            target_show_context=model_data.target_show_context,
            target_show_index=None,
        ).set_index("song_name")

        scores = self._model.predict(features[self._FEATURE_COLS].values)
        probabilities = 1.0 / (1.0 + np.exp(-scores))
        order = np.argsort(probabilities)[::-1][:top_k]
        last_play_dates = cache["last_play_dates"]
        p50 = _window_plays(cum, n_shows, 50).loc[eligible_songs]

        return [
            DealPrediction(
                song_name=str(eligible_songs[index]),
                probability=float(probabilities[index]),
                current_gap=int(current_gap.loc[eligible_songs[index]]),
                plays_past_year=0,
                recent_plays_50=int(p50.loc[eligible_songs[index]]),
                LTP=(
                    pd.Timestamp(last_play_dates[str(eligible_songs[index])])
                    .date()
                    .isoformat()
                    if str(eligible_songs[index]) in last_play_dates
                    else None
                ),
            )
            for index in order
        ]


class GooseMatrixPredictor(GooseFastPredictor):
    """Goose matrix challenger with cheap Deal-parity and set-position features."""

    MODEL_VERSION = "goose_matrix_gbm_v1"
    _FEATURE_COLS: list[str] = GOOSE_MATRIX_FEATURE_COLS

    def _prepare(self, plays: pd.DataFrame) -> dict[str, Any]:
        cache = super()._prepare(plays)
        cache["set_position_cums"] = _build_set_position_cums(
            plays,
            cache["presence"],
        )
        return cache

    def _feature_frame_for_target(
        self,
        *,
        eligible_songs: pd.Index,
        upper_col: int,
        target_date: Any,
        gap_e: pd.Series,
        total_e: pd.Series,
        cache: dict[str, Any],
        plays: pd.DataFrame,
        target_show_context: Any,
        target_show_index: int | None,
    ) -> pd.DataFrame:
        frame = super()._feature_frame_for_target(
            eligible_songs=eligible_songs,
            upper_col=upper_col,
            target_date=target_date,
            gap_e=gap_e,
            total_e=total_e,
            cache=cache,
            plays=plays,
            target_show_context=target_show_context,
            target_show_index=target_show_index,
        )
        presence = cache["presence"]
        show_cols = cache["show_cols"]
        avg_ltp, recent_avg_ltp, gap_z_score = _ltp_stat_arrays(
            eligible_songs=eligible_songs,
            upper_col=upper_col,
            gap_e=gap_e,
            presence=presence,
            show_cols=show_cols,
        )
        pct_1yr, pct_all_time, diff_1yr = _one_year_rate_features(
            eligible_songs=eligible_songs,
            total_e=total_e,
            upper_col=upper_col,
            target_date=target_date,
            plays=plays,
            target_show_index=target_show_index,
        )
        set_position = _set_position_arrays(
            eligible_songs=eligible_songs,
            upper_col=upper_col,
            cache=cache,
        ).reset_index(drop=True)

        frame["avg_ltp"] = avg_ltp
        frame["recent_avg_ltp"] = recent_avg_ltp
        frame["gap_z_score"] = gap_z_score
        frame["pct_shows_1yr"] = pct_1yr
        frame["pct_shows_all_time"] = pct_all_time
        frame["diff_1yr_to_alltime"] = diff_1yr
        for column in SET_POSITION_FEATURES:
            frame[column] = set_position[column].to_numpy(dtype=float)
        return frame


class GooseMatrixPredictorV2(GooseMatrixPredictor):
    """Goose matrix challenger with incumbent-parity and selective co-occurrence."""

    MODEL_VERSION = "goose_matrix_gbm_v2"
    _FEATURE_COLS: list[str] = GOOSE_MATRIX_V2_FEATURE_COLS

    def _feature_frame_for_target(
        self,
        *,
        eligible_songs: pd.Index,
        upper_col: int,
        target_date: Any,
        gap_e: pd.Series,
        total_e: pd.Series,
        cache: dict[str, Any],
        plays: pd.DataFrame,
        target_show_context: Any,
        target_show_index: int | None,
    ) -> pd.DataFrame:
        frame = super()._feature_frame_for_target(
            eligible_songs=eligible_songs,
            upper_col=upper_col,
            target_date=target_date,
            gap_e=gap_e,
            total_e=total_e,
            cache=cache,
            plays=plays,
            target_show_context=target_show_context,
            target_show_index=target_show_index,
        )
        presence = cache["presence"]
        show_cols = cache["show_cols"]

        plays_past_year, plays_past_2yr, pct_6mo, diff_6mo_to_1yr = (
            _window_rate_features(
                eligible_songs=eligible_songs,
                target_date=target_date,
                plays=plays,
                target_show_index=target_show_index,
            )
        )
        n_same_venue, n_same_state = _history_context_counts(
            eligible_songs=eligible_songs,
            plays=plays,
            target_show_index=target_show_index,
        )
        debut_age, novelty_rank = _debut_novelty_arrays(
            eligible_songs=eligible_songs,
            total_e=total_e,
            upper_col=upper_col,
            presence=presence,
            show_cols=show_cols,
        )
        recent_anchors = _anchor_songs(
            presence=presence,
            upper_col=upper_col,
            window=self.exclusion_window,
        )
        last_show_anchors = _anchor_songs(
            presence=presence,
            upper_col=upper_col,
            window=1,
        )
        recent_mean, recent_max = _matrix_cooc_features(
            eligible_songs=eligible_songs,
            anchor_songs=recent_anchors,
            upper_col=upper_col,
            presence=presence,
        )
        last_mean, last_max = _matrix_cooc_features(
            eligible_songs=eligible_songs,
            anchor_songs=last_show_anchors,
            upper_col=upper_col,
            presence=presence,
        )

        frame["plays_past_year"] = plays_past_year
        frame["plays_past_2yr"] = plays_past_2yr
        frame["pct_shows_6mo"] = pct_6mo
        frame["diff_6mo_to_1yr"] = diff_6mo_to_1yr
        frame["n_shows_same_venue"] = n_same_venue
        frame["n_shows_same_state"] = n_same_state
        frame["debut_age_shows"] = debut_age
        frame["novelty_rank"] = novelty_rank
        frame["recent_anchor_cooc_mean"] = recent_mean
        frame["recent_anchor_cooc_max"] = recent_max
        frame["last_show_cooc_mean"] = last_mean
        frame["last_show_cooc_max"] = last_max
        return frame
