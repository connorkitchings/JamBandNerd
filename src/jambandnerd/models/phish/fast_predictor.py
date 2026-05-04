"""Phish fast predictor — vectorized presence-matrix approach.

Based on BillyFastPredictor architecture optimized for Phish's larger catalog:
- 100-show training window (vs 75 for Billy)
- 100-show retirement gap (vs 120 for Billy)
- 30 minimum training shows (vs default for larger catalog stability)
- 17 features including plays_past_2yr for Phish's longer history
- Candidate pruning: songs played in last 150 shows + top 100 by career plays

Bypasses DealPredictor's O(n²) cooccurrence bottleneck using vectorized matrix operations.
Per-show train+predict time: seconds, not minutes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from jambandnerd.models.base import PredictionModel
from jambandnerd.transformations.gaps import ModelData
from jambandnerd.transformations.run_context import (
    normalize_target_show_context,
    normalized_venue_key,
    same_venue_run_show_indices,
)

# ── Constants ─────────────────────────────────────────────────────────────────

_MIN_PLAYS = 3
_RETIRED_GAP = 100  # Retire songs unplayed for 100+ shows
_TRAINING_WINDOW = 100  # Most recent 100 shows for training
_MIN_TRAINING_SHOWS = 30  # Higher minimum for Phish's larger catalog

# Candidate pruning: Keep songs from last 150 shows + top 100 career plays
_CANDIDATE_RECENT_SHOWS = 150
_CANDIDATE_TOP_CAREER = 100

PHISH_FAST_FEATURE_COLS: list[str] = [
    "gap_shows",
    "plays_past_10",
    "plays_past_25",
    "plays_past_50",
    "plays_past_2yr",  # Phish-specific: captures longer history
    "career_play_pct",
    "month_play_rate",
]

PHISH_FAST_CANDIDATE_CONTEXT_COLS: list[str] = [
    "show_position_in_run",
    "tour_position",
    "diff_25_to_50",
    "same_venue_run_prior_played",
    "same_venue_run_prior_play_count",
    "same_venue_run_prior_play_share",
    "same_venue_run_position",
]

PHISH_FAST_DIAGNOSTIC_FEATURE_COLS: list[str] = [
    *PHISH_FAST_FEATURE_COLS,
    *PHISH_FAST_CANDIDATE_CONTEXT_COLS,
]

_EMPTY_ARR: np.ndarray = np.array([], dtype=float)

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


# ── Prediction result ─────────────────────────────────────────────────────────


@dataclass
class PhishPrediction:
    song_name: str
    probability: float
    gap_shows: int


# ── Helpers ───────────────────────────────────────────────────────────────────


def _precompute_gap_distributions(presence: pd.DataFrame) -> dict[str, np.ndarray]:
    """Per-song sorted array of inter-play column gaps from the presence matrix."""
    arr = presence.values.astype(bool)
    result: dict[str, np.ndarray] = {}
    for i, song in enumerate(presence.index):
        play_cols = np.where(arr[i])[0]
        if len(play_cols) >= 2:
            result[str(song)] = np.sort(np.diff(play_cols).astype(float))
        else:
            result[str(song)] = _EMPTY_ARR
    return result


def _precompute_first_play_col(presence: pd.DataFrame) -> dict[str, int]:
    """Per-song column index of the first-ever play."""
    arr = presence.values.astype(bool)
    result: dict[str, int] = {}
    for i, song in enumerate(presence.index):
        play_cols = np.where(arr[i])[0]
        result[str(song)] = int(play_cols[0]) if len(play_cols) > 0 else 0
    return result


def _precompute_avg_days_between_plays(
    presence: pd.DataFrame, col_dates: list
) -> dict[str, float]:
    """Per-song mean calendar days between consecutive plays."""
    arr = presence.values.astype(bool)
    result: dict[str, float] = {}
    for i, song in enumerate(presence.index):
        play_cols = np.where(arr[i])[0]
        if len(play_cols) >= 2:
            dates = [
                col_dates[c]
                for c in play_cols
                if c < len(col_dates) and col_dates[c] is not None
            ]
            if len(dates) >= 2:
                diffs = [(dates[k + 1] - dates[k]).days for k in range(len(dates) - 1)]
                result[str(song)] = float(np.mean(diffs))
            else:
                result[str(song)] = 0.0
        else:
            result[str(song)] = 0.0
    return result


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
    df = df.dropna(subset=["show_date", "show_index"])
    df["show_index"] = df["show_index"].astype(int)
    return df.reset_index(drop=True)


def _build_presence(plays: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """(n_songs × n_shows) bool DataFrame; show_cols = sorted show_index values."""
    pres = (
        plays.groupby(["song_name", "show_index"])
        .size()
        .gt(0)
        .unstack(fill_value=False)
    )
    show_cols = pres.columns.to_numpy(dtype=np.int64)
    return pres, show_cols


def _build_gap_matrix(presence: pd.DataFrame) -> pd.DataFrame:
    """(n_songs × n_shows) gap matrix.

    gap_mat[s, j] = number of show-columns elapsed since song s was last
    played before column j. Equals 1 if played at column j-1; equals
    n_shows if never played before j (beyond any retired threshold).
    """
    n_shows = presence.shape[1]
    col_pos = np.arange(n_shows, dtype=float)

    play_col = np.where(presence.values, col_pos[np.newaxis, :], np.nan)
    df = pd.DataFrame(play_col, index=presence.index, columns=presence.columns)

    last_play = df.ffill(axis=1)
    last_play_before = last_play.shift(1, axis=1)

    gap_arr = col_pos[np.newaxis, :] - last_play_before.values
    gap_arr = np.where(np.isnan(last_play_before.values), float(n_shows), gap_arr)
    return pd.DataFrame(gap_arr, index=presence.index, columns=presence.columns)


def _window_plays(cum: pd.DataFrame, upper_col: int, window: int) -> pd.Series:
    """Per-song play count in columns [upper_col - window, upper_col) exclusive.

    upper_col is the first column NOT included (i.e., the target show column
    or n_shows for prediction). window is the number of prior columns to sum.
    """
    end = upper_col - 1
    if end < 0:
        return pd.Series(0.0, index=cum.index)
    end = min(end, cum.shape[1] - 1)
    start = max(0, upper_col - window)
    if start == 0:
        return cum.iloc[:, end].astype(float)
    return (cum.iloc[:, end] - cum.iloc[:, start - 1]).astype(float)


def _window_plays_by_days(
    plays: pd.DataFrame,
    presence: pd.DataFrame,
    ref_col: int,
    days: int,
    col_dates: list,
) -> pd.Series:
    """Per-song play count in the last N days before the reference column."""
    if ref_col < 0 or not col_dates:
        return pd.Series(0.0, index=presence.index)
    
    ref_date = col_dates[ref_col]
    if ref_date is None:
        return pd.Series(0.0, index=presence.index)
    
    # Calculate cutoff date
    cutoff_date = ref_date - pd.Timedelta(days=days)
    
    # Find which columns are within the date window
    valid_cols = [
        i for i, d in enumerate(col_dates[:ref_col + 1])
        if d is not None and d >= cutoff_date
    ]
    
    if not valid_cols:
        return pd.Series(0.0, index=presence.index)
    
    # Sum plays across valid columns
    plays_in_window = presence.iloc[:, valid_cols].sum(axis=1).astype(float)
    return plays_in_window


def _build_month_cums(
    plays: pd.DataFrame,
    presence: pd.DataFrame,
) -> dict[int, pd.DataFrame]:
    """12 month-specific cumulative-sum matrices, same shape as presence cumsum."""
    all_songs = presence.index
    cols = presence.columns
    month_cums: dict[int, pd.DataFrame] = {}
    for m in range(1, 13):
        mp = (
            plays[plays["_month"] == m]
            .groupby(["song_name", "show_index"])
            .size()
            .unstack(fill_value=0)
            .reindex(index=all_songs, columns=cols, fill_value=0)
            .astype(float)
        )
        month_cums[m] = mp.cumsum(axis=1)
    return month_cums


def _run_position(dates: list, target_date: Any, gap_days: int = 1) -> int:
    """Position in current run (consecutive dates within gap_days)."""
    if not dates or target_date is None:
        return 1
    sorted_dates = sorted(dates)
    position = 1
    for i in range(len(sorted_dates) - 1, -1, -1):
        if (target_date - sorted_dates[i]).days <= gap_days:
            position += 1
        else:
            break
    return position


def _tour_position(dates: list, target_date: Any, tour_gap_days: int = 14) -> int:
    """Position in current tour (dates within tour_gap_days)."""
    if not dates or target_date is None:
        return 1
    sorted_dates = sorted(dates)
    position = 1
    for i in range(len(sorted_dates) - 1, -1, -1):
        if (target_date - sorted_dates[i]).days <= tour_gap_days:
            position += 1
        else:
            break
    return position


def _get_candidate_songs(
    presence: pd.DataFrame,
    cum: pd.DataFrame,
    ref_col: int,
    recent_shows: int = _CANDIDATE_RECENT_SHOWS,
    top_career: int = _CANDIDATE_TOP_CAREER,
) -> pd.Index:
    """Get candidate songs: played in last N shows + top M by career plays.
    
    Reduces inference cost for large catalogs like Phish (~500-800 songs).
    """
    # Songs played in recent window
    start_col = max(0, ref_col - recent_shows + 1)
    recent_plays = presence.iloc[:, start_col:ref_col + 1].sum(axis=1)
    recent_songs = presence.index[recent_plays > 0]
    
    # Top songs by career plays
    career_plays = cum.iloc[:, ref_col]
    top_songs = career_plays.nlargest(top_career).index
    
    # Union of both sets
    candidates = recent_songs.union(top_songs)
    return candidates


# ── Predictor ─────────────────────────────────────────────────────────────────


class PhishFastPredictor(PredictionModel):
    """Phish LightGBM LambdaRank predictor using vectorized presence-matrix features.

    Optimized for Phish's large catalog using:
    - 100-show training window (captures ~3 years of Phish touring)
    - 100-show retirement gap (aggressive pruning of stale songs)
    - Candidate pruning: last 150 shows + top 100 career plays
    - plays_past_2yr feature for long-term history

    All features computed via vectorized matrix operations — no O(n²) loops.
    """

    MODEL_VERSION = "phish_fast_gbm_v1"
    _FEATURE_COLS: list[str] = PHISH_FAST_FEATURE_COLS
    _LGB_PARAMS: dict[str, Any] = _LGB_PARAMS
    _LGB_ROUNDS: int = _LGB_ROUNDS
    _EARLY_STOPPING_ROUNDS: int | None = None
    _VALIDATION_FRACTION: float = 0.2

    def __init__(
        self,
        band: str = "phish",
        **kwargs: Any,
    ) -> None:
        if band != "phish":
            raise ValueError("PhishFastPredictor only supports band='phish'.")
        self.band = band
        self._model: lgb.Booster | None = None
        self.best_iteration: int | None = None
        # Cached from train() for reuse in predict()
        self._cache: dict | None = None
        self.diagnostic_feature_columns = list(PHISH_FAST_DIAGNOSTIC_FEATURE_COLS)

    # ── Extension hooks ────────────────────────────────────────────────────────

    def _extra_training_row_features(
        self,
        *,
        eligible_songs: pd.Index,
        j: int,
        target_date: Any,
        gap_e: pd.Series,
        career_pct: pd.Series,
        p25: pd.Series,
        p50: pd.Series,
        cache: dict,
        plays: pd.DataFrame,
        target_show_index: int,
    ) -> dict:
        return {}

    def _extra_predict_features(
        self,
        *,
        eligible_songs: pd.Index,
        n_shows: int,
        ref_date: pd.Timestamp,
        gap_e: pd.Series,
        career_pct: pd.Series,
        p25: pd.Series,
        p50: pd.Series,
        cache: dict,
        plays: pd.DataFrame,
        target_show_context: Any,
    ) -> dict:
        return {}

    # ── Matrix build ───────────────────────────────────────────────────────────

    def _prepare(self, plays: pd.DataFrame) -> dict:
        plays = plays.copy()
        plays["_month"] = plays["show_date"].dt.month

        presence, show_cols = _build_presence(plays)
        cum = presence.astype(float).cumsum(axis=1)
        gap_mat = _build_gap_matrix(presence)
        month_cums = _build_month_cums(plays, presence)

        show_date_map: dict[int, Any] = (
            plays[["show_index", "show_date"]]
            .drop_duplicates("show_index")
            .set_index("show_index")["show_date"]
            .to_dict()
        )

        col_dates = [
            (
                pd.Timestamp(show_date_map[int(sc)]).date()
                if int(sc) in show_date_map
                else None
            )
            for sc in show_cols
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
        col_venues = [venue_map.get(int(sc)) for sc in show_cols]

        gap_dist = _precompute_gap_distributions(presence)
        first_play_col = _precompute_first_play_col(presence)
        avg_days_bp = _precompute_avg_days_between_plays(presence, col_dates)

        return {
            "presence": presence,
            "show_cols": show_cols,
            "cum": cum,
            "gap_mat": gap_mat,
            "month_cums": month_cums,
            "show_date_map": show_date_map,
            "col_dates": col_dates,
            "col_venues": col_venues,
            "gap_dist": gap_dist,
            "first_play_col": first_play_col,
            "avg_days_bp": avg_days_bp,
        }

    def build_diagnostic_training_frame(self, model_data: ModelData) -> pd.DataFrame:
        """Return the labeled frame used for Phase B feature diagnostics.

        This method exposes the active PhishFast training features plus
        candidate context features without changing production feature set.
        """
        plays = _clean_plays(model_data.historical_plays)
        columns = [
            "song_name",
            "target_show_index",
            "target_show_date",
            *PHISH_FAST_DIAGNOSTIC_FEATURE_COLS,
            "label",
        ]
        if plays.empty:
            return pd.DataFrame(columns=columns)

        cache = self._prepare(plays)
        presence = cache["presence"]
        cum = cache["cum"]
        gap_mat = cache["gap_mat"]
        month_cums = cache["month_cums"]
        show_cols = cache["show_cols"]
        show_date_map = cache["show_date_map"]
        col_dates = cache["col_dates"]
        col_venues = cache["col_venues"]
        all_songs = presence.index
        n_shows = len(show_cols)

        start_col = max(_MIN_TRAINING_SHOWS, n_shows - _TRAINING_WINDOW)
        rows: list[pd.DataFrame] = []

        for j in range(start_col, n_shows):
            ref_col = j - 1
            target_show_index = int(show_cols[j])
            raw_target_date = show_date_map.get(target_show_index)
            if raw_target_date is None:
                continue
            target_date = pd.Timestamp(raw_target_date).date()

            # Get candidate songs with pruning
            candidates = _get_candidate_songs(presence, cum, ref_col)
            
            total_before = cum.iloc[:, ref_col]
            gap_at_j = gap_mat.iloc[:, j]
            
            # Filter to eligible candidates
            eligible_mask = (
                total_before.reindex(candidates, fill_value=0) >= _MIN_PLAYS
            ) & (
                gap_at_j.reindex(candidates, fill_value=999) > 0
            ) & (
                gap_at_j.reindex(candidates, fill_value=999) <= _RETIRED_GAP
            )
            
            if not eligible_mask.any():
                continue

            eligible_songs = candidates[eligible_mask.reindex(candidates, fill_value=False)]
            gap_e = gap_at_j.loc[eligible_songs]
            total_e = total_before.loc[eligible_songs]

            p10 = _window_plays(cum, j, 10).loc[eligible_songs]
            p25 = _window_plays(cum, j, 25).loc[eligible_songs]
            p50 = _window_plays(cum, j, 50).loc[eligible_songs]
            p2yr = _window_plays_by_days(plays, presence, ref_col, 730, col_dates).loc[eligible_songs]
            career_pct = total_e / max(1, j)

            target_month = target_date.month
            month_before = month_cums[target_month].iloc[:, ref_col].loc[eligible_songs]
            month_play_rate = (month_before / total_e.clip(lower=1)).fillna(0.0)

            sub_plays = plays[plays["show_index"] < target_show_index].copy()
            show_dates = sorted(
                sub_plays["show_date"].dropna().dt.date.unique().tolist()
            )
            show_position = _run_position(show_dates, target_date, gap_days=1)
            tour_position = _tour_position(show_dates, target_date, tour_gap_days=14)

            pct25 = p25 / max(1, min(25, j))
            pct50 = p50 / max(1, min(50, j))
            diff_25_to_50 = pct25 - pct50

            target_rows = plays[plays["show_index"] == target_show_index]
            target_context = (
                normalize_target_show_context(target_rows.iloc[0])
                if not target_rows.empty
                else {}
            )
            normalized_ctx = normalize_target_show_context(target_context)
            if normalized_venue_key(normalized_ctx):
                same_run_indices = same_venue_run_show_indices(
                    sub_plays,
                    normalized_ctx,
                )
            else:
                same_run_indices = []

            if same_run_indices:
                same_run_counts = (
                    sub_plays[sub_plays["show_index"].isin(same_run_indices)]
                    .groupby("song_name")["show_index"]
                    .nunique()
                    .reindex(eligible_songs, fill_value=0)
                    .astype(float)
                )
                same_run_played = (same_run_counts > 0).astype(float)
                same_run_share = same_run_counts / len(same_run_indices)
                same_run_position = float(len(same_run_indices) + 1)
            else:
                same_run_counts = pd.Series(0.0, index=eligible_songs)
                same_run_played = pd.Series(0.0, index=eligible_songs)
                same_run_share = pd.Series(0.0, index=eligible_songs)
                same_run_position = 1.0 if normalized_venue_key(normalized_ctx) else 0.0

            labels = presence.iloc[:, j].loc[eligible_songs].astype(float)
            rows.append(
                pd.DataFrame(
                    {
                        "song_name": eligible_songs.to_numpy(),
                        "target_show_index": target_show_index,
                        "target_show_date": target_date.isoformat(),
                        "gap_shows": gap_e.values,
                        "plays_past_10": p10.values,
                        "plays_past_25": p25.values,
                        "plays_past_50": p50.values,
                        "plays_past_2yr": p2yr.values,
                        "career_play_pct": career_pct.values,
                        "month_play_rate": month_play_rate.values,
                        "show_position_in_run": float(show_position),
                        "tour_position": float(tour_position),
                        "diff_25_to_50": diff_25_to_50.values,
                        "same_venue_run_prior_played": same_run_played.values,
                        "same_venue_run_prior_play_count": same_run_counts.values,
                        "same_venue_run_prior_play_share": same_run_share.values,
                        "same_venue_run_position": same_run_position,
                        "label": labels.values,
                    }
                )
            )

        if not rows:
            return pd.DataFrame(columns=columns)
        return pd.concat(rows, ignore_index=True)[columns]

    # ── Training ───────────────────────────────────────────────────────────────

    def train(self, model_data: ModelData) -> None:
        plays = _clean_plays(model_data.historical_plays)
        if plays.empty:
            return

        cache = self._prepare(plays)
        self._cache = cache

        presence = cache["presence"]
        cum = cache["cum"]
        gap_mat = cache["gap_mat"]
        month_cums = cache["month_cums"]
        show_cols = cache["show_cols"]
        show_date_map = cache["show_date_map"]
        col_dates = cache["col_dates"]
        all_songs = presence.index
        n_shows = len(show_cols)

        start_col = max(_MIN_TRAINING_SHOWS, n_shows - _TRAINING_WINDOW)

        rows: list[pd.DataFrame] = []
        group_sizes: list[int] = []

        for j in range(start_col, n_shows):
            ref_col = j - 1

            # Get candidate songs with pruning
            candidates = _get_candidate_songs(presence, cum, ref_col)
            
            total_before = cum.iloc[:, ref_col]
            gap_at_j = gap_mat.iloc[:, j]
            
            # Filter to eligible candidates
            eligible_mask = (
                total_before.reindex(candidates, fill_value=0) >= _MIN_PLAYS
            ) & (
                gap_at_j.reindex(candidates, fill_value=999) > 0
            ) & (
                gap_at_j.reindex(candidates, fill_value=999) <= _RETIRED_GAP
            )
            
            if not eligible_mask.any():
                continue

            eligible_songs = candidates[eligible_mask.reindex(candidates, fill_value=False)]
            gap_e = gap_at_j.loc[eligible_songs]
            total_e = total_before.loc[eligible_songs]

            p10 = _window_plays(cum, j, 10).loc[eligible_songs]
            p25 = _window_plays(cum, j, 25).loc[eligible_songs]
            p50 = _window_plays(cum, j, 50).loc[eligible_songs]
            p2yr = _window_plays_by_days(plays, presence, ref_col, 730, col_dates).loc[eligible_songs]

            career_pct = total_e / max(1, j)

            sd = show_date_map.get(int(show_cols[j]))
            target_date = pd.Timestamp(sd).date() if sd is not None else None
            target_month = pd.Timestamp(sd).month if sd is not None else 1
            month_before = month_cums[target_month].iloc[:, ref_col].loc[eligible_songs]
            mpr = (month_before / total_e.clip(lower=1)).fillna(0.0)

            labels = presence.iloc[:, j].loc[eligible_songs].astype(float)

            extra = self._extra_training_row_features(
                eligible_songs=eligible_songs,
                j=j,
                target_date=target_date,
                gap_e=gap_e,
                career_pct=career_pct,
                p25=p25,
                p50=p50,
                cache=cache,
                plays=plays,
                target_show_index=int(show_cols[j]),
            )

            rows.append(
                pd.DataFrame(
                    {
                        "gap_shows": gap_e.values,
                        "plays_past_10": p10.values,
                        "plays_past_25": p25.values,
                        "plays_past_50": p50.values,
                        "plays_past_2yr": p2yr.values,
                        "career_play_pct": career_pct.values,
                        "month_play_rate": mpr.values,
                        **extra,
                        "label": labels.values,
                    }
                )
            )
            group_sizes.append(int(len(eligible_songs)))

        if not rows:
            return

        X_all = pd.concat(rows, ignore_index=True)
        y = X_all.pop("label")
        X_features = X_all[self._FEATURE_COLS]

        if self._EARLY_STOPPING_ROUNDS is None or len(group_sizes) < 2:
            train_data = lgb.Dataset(
                X_features,
                label=y,
                group=group_sizes,
                free_raw_data=False,
            )
            self._model = lgb.train(
                self._LGB_PARAMS,
                train_data,
                num_boost_round=self._LGB_ROUNDS,
            )
            self.best_iteration = int(self._model.current_iteration())
            return

        val_group_count = max(
            1,
            int(round(len(group_sizes) * self._VALIDATION_FRACTION)),
        )
        val_group_count = min(val_group_count, len(group_sizes) - 1)
        train_group_count = len(group_sizes) - val_group_count
        train_row_count = sum(group_sizes[:train_group_count])

        train_data = lgb.Dataset(
            X_features.iloc[:train_row_count],
            label=y.iloc[:train_row_count],
            group=group_sizes[:train_group_count],
            free_raw_data=False,
        )
        valid_data = lgb.Dataset(
            X_features.iloc[train_row_count:],
            label=y.iloc[train_row_count:],
            group=group_sizes[train_group_count:],
            reference=train_data,
            free_raw_data=False,
        )
        stopping_model = lgb.train(
            self._LGB_PARAMS,
            train_data,
            num_boost_round=self._LGB_ROUNDS,
            valid_sets=[valid_data],
            valid_names=["valid"],
            callbacks=[
                lgb.early_stopping(
                    self._EARLY_STOPPING_ROUNDS,
                    first_metric_only=False,
                    verbose=False,
                    min_delta=0.0,
                )
            ],
        )
        self.best_iteration = int(
            stopping_model.best_iteration or stopping_model.current_iteration()
        )

        full_train_data = lgb.Dataset(
            X_features,
            label=y,
            group=group_sizes,
            free_raw_data=False,
        )
        self._model = lgb.train(
            self._LGB_PARAMS,
            full_train_data,
            num_boost_round=self.best_iteration,
        )

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(self, model_data: ModelData, top_k: int = 50) -> list[PhishPrediction]:
        if self._model is None:
            return []

        plays = _clean_plays(model_data.historical_plays)
        if plays.empty:
            return []

        cache = self._cache if self._cache is not None else self._prepare(plays)

        presence = cache["presence"]
        cum = cache["cum"]
        gap_mat = cache["gap_mat"]
        month_cums = cache["month_cums"]
        col_dates = cache["col_dates"]
        all_songs = presence.index
        n_shows = presence.shape[1]
        ref_col = n_shows - 1

        total_plays = cum.iloc[:, ref_col]

        gap_predict = (
            gap_mat.iloc[:, ref_col].astype(float)
            * (1.0 - presence.iloc[:, ref_col].astype(float))
            + 1.0
        )

        # Get candidate songs with pruning
        candidates = _get_candidate_songs(presence, cum, ref_col)
        
        # Filter to eligible candidates
        eligible_mask = (
            total_plays.reindex(candidates, fill_value=0) >= _MIN_PLAYS
        ) & (
            gap_predict.reindex(candidates, fill_value=999) > 0
        ) & (
            gap_predict.reindex(candidates, fill_value=999) <= _RETIRED_GAP
        )
        
        eligible_songs = candidates[eligible_mask.reindex(candidates, fill_value=False)]
        if len(eligible_songs) == 0:
            return []

        gap_e = gap_predict.loc[eligible_songs]
        total_e = total_plays.loc[eligible_songs]

        ref_date = pd.Timestamp(model_data.reference_date)
        target_month = ref_date.month

        p10 = _window_plays(cum, n_shows, 10).loc[eligible_songs]
        p25 = _window_plays(cum, n_shows, 25).loc[eligible_songs]
        p50 = _window_plays(cum, n_shows, 50).loc[eligible_songs]
        p2yr = _window_plays_by_days(plays, presence, ref_col, 730, col_dates).loc[eligible_songs]

        career_pct = total_e / max(1, n_shows)
        month_before = month_cums[target_month].iloc[:, ref_col].loc[eligible_songs]
        mpr = (month_before / total_e.clip(lower=1)).fillna(0.0)

        extra = self._extra_predict_features(
            eligible_songs=eligible_songs,
            n_shows=n_shows,
            ref_date=ref_date,
            gap_e=gap_e,
            career_pct=career_pct,
            p25=p25,
            p50=p50,
            cache=cache,
            plays=plays,
            target_show_context=model_data.target_show_context,
        )

        X = pd.DataFrame(
            {
                "gap_shows": gap_e.values,
                "plays_past_10": p10.values,
                "plays_past_25": p25.values,
                "plays_past_50": p50.values,
                "plays_past_2yr": p2yr.values,
                "career_play_pct": career_pct.values,
                "month_play_rate": mpr.values,
                **extra,
            },
            index=eligible_songs,
        )

        scores = self._model.predict(X[self._FEATURE_COLS].values)
        probs = 1.0 / (1.0 + np.exp(-scores))

        order = np.argsort(probs)[::-1][:top_k]
        gap_arr = gap_predict.loc[eligible_songs].values
        return [
            PhishPrediction(
                song_name=str(eligible_songs[i]),
                probability=float(probs[i]),
                gap_shows=int(gap_arr[i]),
            )
            for i in order
        ]


# ── PhishFastPredictorV2 ──────────────────────────────────────────────────────


PHISH_FAST_V2_FEATURE_COLS: list[str] = [
    *PHISH_FAST_FEATURE_COLS,
    "tour_position",
    "diff_25_to_50",
    "show_position_in_run",
    "same_venue_run_position",
    "plays_past_3",
    "plays_past_5",
    "overdue_ratio",
    "avg_ltp_recent",
    "ltp_diff_recent",
]


class PhishFastPredictorV2(PhishFastPredictor):
    """PhishFast v2 — extended features + per-show LightGBM early stopping.

    Adds BillyFast V3-equivalent features (tour/run context, short-window
    recency, rotation analytics) plus early stopping. Total: 16 features.
    """

    MODEL_VERSION = "phish_fast_gbm_v2"
    _FEATURE_COLS: list[str] = PHISH_FAST_V2_FEATURE_COLS
    _LGB_ROUNDS: int = 500
    _EARLY_STOPPING_ROUNDS: int | None = 25

    def _extra_training_row_features(
        self,
        *,
        eligible_songs: pd.Index,
        j: int,
        target_date: Any,
        gap_e: pd.Series,
        career_pct: pd.Series,
        p25: pd.Series,
        p50: pd.Series,
        cache: dict,
        plays: pd.DataFrame,
        target_show_index: int,
    ) -> dict:
        col_dates = cache["col_dates"]
        col_venues = cache["col_venues"]

        prior_dates = [d for d in col_dates[:j] if d is not None]
        if target_date is None:
            tour_pos = 1.0
            run_pos = 1.0
        else:
            tour_pos = float(_tour_position(prior_dates, target_date, tour_gap_days=14))
            run_pos = float(_run_position(prior_dates, target_date, gap_days=1))

        pct25 = p25 / max(1, min(25, j))
        pct50 = p50 / max(1, min(50, j))
        diff = (pct25 - pct50).values

        target_venue = col_venues[j] if j < len(col_venues) else None
        if target_venue:
            target_context = normalize_target_show_context({"venue_name": target_venue})
            if normalized_venue_key(target_context):
                sub_plays = plays[plays["show_index"] < target_show_index]
                same_run_indices = same_venue_run_show_indices(
                    sub_plays, target_context
                )
                same_run_position = float(len(same_run_indices) + 1)
            else:
                same_run_position = 0.0
        else:
            same_run_position = 0.0

        cum = cache["cum"]
        p3 = _window_plays(cum, j, 3).loc[eligible_songs]
        p5 = _window_plays(cum, j, 5).loc[eligible_songs]
        window = max(1, min(25, j))
        avg_ltp = window / p25.clip(lower=1).values

        return {
            "tour_position": tour_pos,
            "diff_25_to_50": diff,
            "show_position_in_run": run_pos,
            "same_venue_run_position": same_run_position,
            "plays_past_3": p3.values,
            "plays_past_5": p5.values,
            "overdue_ratio": (gap_e * career_pct).values,
            "avg_ltp_recent": avg_ltp,
            "ltp_diff_recent": gap_e.values - avg_ltp,
        }

    def _extra_predict_features(
        self,
        *,
        eligible_songs: pd.Index,
        n_shows: int,
        ref_date: pd.Timestamp,
        gap_e: pd.Series,
        career_pct: pd.Series,
        p25: pd.Series,
        p50: pd.Series,
        cache: dict,
        plays: pd.DataFrame,
        target_show_context: Any,
    ) -> dict:
        col_dates = cache["col_dates"]
        prior_dates = [d for d in col_dates if d is not None]
        tour_pos = float(_tour_position(prior_dates, ref_date.date(), tour_gap_days=14))
        run_pos = float(_run_position(prior_dates, ref_date.date(), gap_days=1))

        pct25 = p25 / max(1, min(25, n_shows))
        pct50 = p50 / max(1, min(50, n_shows))
        diff = (pct25 - pct50).values

        normalized_ctx = normalize_target_show_context(target_show_context or {})
        if normalized_venue_key(normalized_ctx):
            same_run_indices = same_venue_run_show_indices(plays, normalized_ctx)
            same_run_position = float(len(same_run_indices) + 1)
        else:
            same_run_position = 0.0

        cum = cache["cum"]
        p3 = _window_plays(cum, n_shows, 3).loc[eligible_songs]
        p5 = _window_plays(cum, n_shows, 5).loc[eligible_songs]
        window = max(1, min(25, n_shows))
        avg_ltp = window / p25.clip(lower=1).values

        return {
            "tour_position": tour_pos,
            "diff_25_to_50": diff,
            "show_position_in_run": run_pos,
            "same_venue_run_position": same_run_position,
            "plays_past_3": p3.values,
            "plays_past_5": p5.values,
            "overdue_ratio": (gap_e * career_pct).values,
            "avg_ltp_recent": avg_ltp,
            "ltp_diff_recent": gap_e.values - avg_ltp,
        }
