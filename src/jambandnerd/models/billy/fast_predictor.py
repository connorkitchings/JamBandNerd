"""Billy Strings fast predictor — vectorized presence-matrix approach.

Bypasses the DealPredictor machinery (which calls generate_deal_features
N_training_shows times, hitting the O(n_songs^2 * n_shows) cooccurrence
triple-loop each time). Instead:

  1. Build a (songs × shows) presence matrix once per train() call.
  2. Derive all features via vectorized cumsum / ffill operations.
  3. Fit a LightGBM LambdaRank ranker on the resulting flat training frame.
  4. At predict() time, compute features at the reference point and score.

Per-show train+predict time: seconds, not minutes.
"""

from __future__ import annotations

from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from jambandnerd.models.base import PredictionModel
from jambandnerd.models.deal.model import DealPrediction
from jambandnerd.transformations.gaps import ModelData
from jambandnerd.transformations.run_context import (
    normalize_target_show_context,
    normalized_venue_key,
    same_venue_run_show_indices,
)
from jambandnerd.transformations.set_position import compute_set_position_features

from .features import _run_position, _tour_position
from .model import _BILLY_ORIGINAL_ARTISTS, _fetch_songs_from_supabase

# ── Constants ─────────────────────────────────────────────────────────────────

_MIN_PLAYS = 3
_RETIRED_GAP = 120  # shows; songs absent > this are excluded
_TRAINING_WINDOW = 75  # most recent N shows used to build training pairs

BILLY_FAST_FEATURE_COLS: list[str] = [
    "gap_shows",
    "plays_past_10",
    "plays_past_25",
    "plays_past_50",
    "career_play_pct",
    "month_play_rate",
    "is_cover",
]

BILLY_FAST_CANDIDATE_CONTEXT_COLS: list[str] = [
    "show_position_in_run",
    "tour_position",
    "diff_25_to_50",
    "same_venue_run_prior_played",
    "same_venue_run_prior_play_count",
    "same_venue_run_prior_play_share",
    "same_venue_run_position",
]

BILLY_FAST_DIAGNOSTIC_FEATURE_COLS: list[str] = [
    *BILLY_FAST_FEATURE_COLS,
    *BILLY_FAST_CANDIDATE_CONTEXT_COLS,
]

BILLY_FAST_V2_FEATURE_COLS: list[str] = [
    *BILLY_FAST_FEATURE_COLS,
    "tour_position",
    "diff_25_to_50",
    "show_position_in_run",
    "same_venue_run_position",
]

BILLY_FAST_V3_FEATURE_COLS: list[str] = [
    *BILLY_FAST_V2_FEATURE_COLS,
    "plays_past_3",
    "plays_past_5",
    "overdue_ratio",
    "avg_ltp_recent",
    "ltp_diff_recent",
]

BILLY_FAST_V9_FEATURE_COLS: list[str] = [
    *BILLY_FAST_V3_FEATURE_COLS,
    "notebook_rank_score",
]

BILLY_FAST_V5_FEATURE_COLS: list[str] = [
    *BILLY_FAST_V3_FEATURE_COLS,
    "gap_percentile",
    "shows_since_debut",
    "is_recent_debut",
    "gap_days",
    "avg_days_between_plays",
    "days_overdue",
    "pct_set_1",
    "pct_encore",
    "set_affinity",
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


# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_is_cover_lookup(songs_df: pd.DataFrame | None) -> dict[str, float]:
    if songs_df is None or songs_df.empty:
        return {}
    lookup: dict[str, float] = {}
    for _, row in songs_df.iterrows():
        raw = row.get("original_artist")
        artist = "" if pd.isna(raw) else str(raw).strip()
        is_cover = 0.0 if not artist or artist in _BILLY_ORIGINAL_ARTISTS else 1.0
        lookup[str(row["song_name"])] = is_cover
    return lookup


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


def _is_cover_series(songs: pd.Index, lookup: dict[str, float]) -> np.ndarray:
    return np.array([lookup.get(str(s), 0.0) for s in songs], dtype=float)


# ── Predictor ─────────────────────────────────────────────────────────────────


class BillyFastPredictor(PredictionModel):
    """Billy Strings LightGBM LambdaRank predictor using vectorized presence-matrix features.

    All features (gap, recency windows, career rate, month rate, is_cover) are
    computed in a single vectorized pass — no per-show groupby loops, no
    cooccurrence computation.
    """

    MODEL_VERSION = "billy_fast_gbm_v1"
    _FEATURE_COLS: list[str] = BILLY_FAST_FEATURE_COLS
    _LGB_PARAMS: dict[str, Any] = _LGB_PARAMS
    _LGB_ROUNDS: int = _LGB_ROUNDS
    _EARLY_STOPPING_ROUNDS: int | None = None
    _VALIDATION_FRACTION: float = 0.2

    def __init__(
        self,
        band: str = "billy",
        songs_df: pd.DataFrame | None = None,
        persist_artifacts: bool = True,
        **kwargs: Any,
    ) -> None:
        if band != "billy":
            raise ValueError("BillyFastPredictor only supports band='billy'.")
        self.band = band
        if songs_df is not None:
            songs_df_resolved = songs_df
        else:
            try:
                songs_df_resolved = _fetch_songs_from_supabase()
            except ValueError:
                songs_df_resolved = None
        self._songs_lookup: dict[str, float] = _build_is_cover_lookup(songs_df_resolved)
        self._model: lgb.Booster | None = None
        self.best_iteration: int | None = None
        # Cached from train() for reuse in predict()
        self._cache: dict | None = None
        self.diagnostic_feature_columns = list(BILLY_FAST_DIAGNOSTIC_FEATURE_COLS)

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
        sp_df = compute_set_position_features(plays)
        set_feats = (
            sp_df.set_index("song_name")
            if not sp_df.empty
            else pd.DataFrame(index=pd.Index([], name="song_name"))
        )
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
            "gap_dist": gap_dist,
            "first_play_col": first_play_col,
            "avg_days_bp": avg_days_bp,
            "set_feats": set_feats,
            "last_play_dates": last_play_dates,
        }

    def build_diagnostic_training_frame(self, model_data: ModelData) -> pd.DataFrame:
        """Return the labeled frame used for Phase B feature diagnostics.

        This method is intentionally separate from ``train``. It exposes the active
        BillyFast training features plus offline candidate context features without
        changing the production feature set or model version.
        """
        plays = _clean_plays(model_data.historical_plays)
        columns = [
            "song_name",
            "target_show_index",
            "target_show_date",
            *BILLY_FAST_DIAGNOSTIC_FEATURE_COLS,
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
        all_songs = presence.index
        n_shows = len(show_cols)

        start_col = self._start_col(n_shows)

        rows: list[pd.DataFrame] = []

        for j in range(start_col, n_shows):
            ref_col = j - 1
            target_show_index = int(show_cols[j])
            raw_target_date = show_date_map.get(target_show_index)
            if raw_target_date is None:
                continue
            target_date = pd.Timestamp(raw_target_date).date()

            total_before = cum.iloc[:, ref_col]
            gap_at_j = gap_mat.iloc[:, j]
            eligible_mask = (
                (total_before >= _MIN_PLAYS)
                & (gap_at_j > 0)
                & (gap_at_j <= _RETIRED_GAP)
            )
            if not eligible_mask.any():
                continue

            eligible_songs = all_songs[eligible_mask]
            gap_e = gap_at_j.loc[eligible_songs]
            total_e = total_before.loc[eligible_songs]

            p10 = _window_plays(cum, j, 10).loc[eligible_songs]
            p25 = _window_plays(cum, j, 25).loc[eligible_songs]
            p50 = _window_plays(cum, j, 50).loc[eligible_songs]
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
                        "career_play_pct": career_pct.values,
                        "month_play_rate": month_play_rate.values,
                        "is_cover": _is_cover_series(
                            eligible_songs,
                            self._songs_lookup,
                        ),
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

    # ── Training ───────────────────────────────────────────────────────────────

    def _start_col(self, n_shows: int) -> int:
        return max(_MIN_PLAYS, n_shows - _TRAINING_WINDOW)

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
        all_songs = presence.index
        n_shows = len(show_cols)

        start_col = self._start_col(n_shows)

        rows: list[pd.DataFrame] = []
        group_sizes: list[int] = []

        for j in range(start_col, n_shows):
            ref_col = j - 1

            total_before = cum.iloc[:, ref_col]
            gap_at_j = gap_mat.iloc[:, j]

            eligible_mask = (
                (total_before >= _MIN_PLAYS)
                & (gap_at_j > 0)
                & (gap_at_j <= _RETIRED_GAP)
            )
            if not eligible_mask.any():
                continue

            eligible_songs = all_songs[eligible_mask]
            gap_e = gap_at_j.loc[eligible_songs]
            total_e = total_before.loc[eligible_songs]

            p10 = _window_plays(cum, j, 10).loc[eligible_songs]
            p25 = _window_plays(cum, j, 25).loc[eligible_songs]
            p50 = _window_plays(cum, j, 50).loc[eligible_songs]

            career_pct = total_e / max(1, j)

            sd = show_date_map.get(int(show_cols[j]))
            target_month = pd.Timestamp(sd).month if sd is not None else 1
            target_date = pd.Timestamp(sd).date() if sd is not None else None
            target_show_index = int(show_cols[j])
            month_before = month_cums[target_month].iloc[:, ref_col].loc[eligible_songs]
            mpr = (month_before / total_e.clip(lower=1)).fillna(0.0)

            is_cover = _is_cover_series(eligible_songs, self._songs_lookup)
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
                target_show_index=target_show_index,
            )

            rows.append(
                pd.DataFrame(
                    {
                        "gap_shows": gap_e.values,
                        "plays_past_10": p10.values,
                        "plays_past_25": p25.values,
                        "plays_past_50": p50.values,
                        "career_play_pct": career_pct.values,
                        "month_play_rate": mpr.values,
                        "is_cover": is_cover,
                        **extra,
                        "label": labels.values,
                    }
                )
            )
            group_sizes.append(int(eligible_mask.sum()))

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

    def predict(self, model_data: ModelData, top_k: int = 50) -> list[DealPrediction]:
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
        all_songs = presence.index
        n_shows = presence.shape[1]
        ref_col = n_shows - 1

        total_plays = cum.iloc[:, ref_col]

        gap_predict = (
            gap_mat.iloc[:, ref_col].astype(float)
            * (1.0 - presence.iloc[:, ref_col].astype(float))
            + 1.0
        )

        eligible_mask = (
            (total_plays >= _MIN_PLAYS)
            & (gap_predict > 0)
            & (gap_predict <= _RETIRED_GAP)
        )
        eligible_songs = all_songs[eligible_mask]
        if len(eligible_songs) == 0:
            return []

        gap_e = gap_predict.loc[eligible_songs]
        total_e = total_plays.loc[eligible_songs]

        ref_date = pd.Timestamp(model_data.reference_date)
        target_month = ref_date.month

        p10 = _window_plays(cum, n_shows, 10).loc[eligible_songs]
        p25 = _window_plays(cum, n_shows, 25).loc[eligible_songs]
        p50 = _window_plays(cum, n_shows, 50).loc[eligible_songs]

        career_pct = total_e / max(1, n_shows)
        month_before = month_cums[target_month].iloc[:, ref_col].loc[eligible_songs]
        mpr = (month_before / total_e.clip(lower=1)).fillna(0.0)
        is_cover = _is_cover_series(eligible_songs, self._songs_lookup)
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
                "career_play_pct": career_pct.values,
                "month_play_rate": mpr.values,
                "is_cover": is_cover,
                **extra,
            },
            index=eligible_songs,
        )

        scores = self._model.predict(X[self._FEATURE_COLS].values)
        probs = 1.0 / (1.0 + np.exp(-scores))

        order = np.argsort(probs)[::-1][:top_k]
        gap_arr = gap_predict.loc[eligible_songs].values
        last_play_dates = cache["last_play_dates"]
        return [
            DealPrediction(
                song_name=str(eligible_songs[i]),
                probability=float(probs[i]),
                current_gap=int(gap_arr[i]),
                plays_past_year=0,
                recent_plays_50=int(p50.loc[eligible_songs[i]]),
                LTP=(
                    pd.Timestamp(last_play_dates[str(eligible_songs[i])])
                    .date()
                    .isoformat()
                    if str(eligible_songs[i]) in last_play_dates
                    else None
                ),
            )
            for i in order
        ]


# ── BillyFastPredictorV2 ──────────────────────────────────────────────────────


class BillyFastPredictorV2(BillyFastPredictor):
    """BillyFast v2 — Phase B ablation candidate adding 4 context features.

    Extends v1 with tour_position, diff_25_to_50, show_position_in_run, and
    same_venue_run_position. Retire if it does not improve dual_score over v1.
    """

    MODEL_VERSION = "billy_fast_gbm_v2"
    _FEATURE_COLS: list[str] = BILLY_FAST_V2_FEATURE_COLS

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

        return {
            "tour_position": tour_pos,
            "diff_25_to_50": diff,
            "show_position_in_run": run_pos,
            "same_venue_run_position": same_run_position,
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

        return {
            "tour_position": tour_pos,
            "diff_25_to_50": diff,
            "show_position_in_run": run_pos,
            "same_venue_run_position": 0.0,
        }


# ── BillyFastPredictorV3 ──────────────────────────────────────────────────────


class BillyFastPredictorV3(BillyFastPredictorV2):
    """BillyFast v3 — adds rotation analytics and short-window recency features.

    Inspired by Widespread Panic model methodology: avg_ltp_recent (expected gap
    from recent frequency), ltp_diff_recent (overdue shows vs. expectation),
    overdue_ratio (gap × career rate), plays_past_3/5 (hot-song windows).
    Also fixes same_venue_run_position at predict time to use target_show_context.
    """

    MODEL_VERSION = "billy_fast_gbm_v3"
    _FEATURE_COLS: list[str] = BILLY_FAST_V3_FEATURE_COLS

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
        v2 = super()._extra_training_row_features(
            eligible_songs=eligible_songs,
            j=j,
            target_date=target_date,
            gap_e=gap_e,
            career_pct=career_pct,
            p25=p25,
            p50=p50,
            cache=cache,
            plays=plays,
            target_show_index=target_show_index,
        )
        cum = cache["cum"]
        p3 = _window_plays(cum, j, 3).loc[eligible_songs]
        p5 = _window_plays(cum, j, 5).loc[eligible_songs]
        window = max(1, min(25, j))
        avg_ltp = window / p25.clip(lower=1).values
        return {
            **v2,
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


# ── BillyFastPredictorV4 ──────────────────────────────────────────────────────

_BILLY_FAST_V4_LGB_PARAMS: dict[str, Any] = {
    **_LGB_PARAMS,
    "num_leaves": 63,
    "reg_lambda": 0.1,
}
_BILLY_FAST_V4_LGB_ROUNDS: int = 400


class BillyFastPredictorV4(BillyFastPredictorV3):
    """BillyFast v4 — LightGBM HP tuning on top of V3 features.

    Same 16-feature set as V3. Doubles num_leaves (31→63) and num_boost_round
    (200→400) while adding L2 regularization (reg_lambda=0.1).
    """

    MODEL_VERSION = "billy_fast_gbm_v4"
    _FEATURE_COLS: list[str] = BILLY_FAST_V3_FEATURE_COLS
    _LGB_PARAMS: dict[str, Any] = _BILLY_FAST_V4_LGB_PARAMS
    _LGB_ROUNDS: int = _BILLY_FAST_V4_LGB_ROUNDS


# ── BillyFastPredictorV5 ──────────────────────────────────────────────────────


def _gap_percentile_arr(
    eligible_songs: pd.Index,
    gap_e: pd.Series,
    gap_dist: dict[str, np.ndarray],
) -> np.ndarray:
    return np.array(
        [
            np.searchsorted(gap_dist.get(s, _EMPTY_ARR), g, side="right")
            / max(1, len(gap_dist.get(s, _EMPTY_ARR)))
            for s, g in zip(eligible_songs, gap_e.values)
        ],
        dtype=float,
    )


def _set_dist_arrays(
    eligible_songs: pd.Index, set_feats: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n = len(eligible_songs)
    if set_feats.empty:
        return np.zeros(n), np.zeros(n), np.zeros(n)
    sf = set_feats.reindex(eligible_songs, fill_value=0.0)
    return (
        sf["pct_set_1"].to_numpy(dtype=float, na_value=0.0),
        sf["pct_encore"].to_numpy(dtype=float, na_value=0.0),
        sf["set_affinity"].to_numpy(dtype=float, na_value=0.0),
    )


class BillyFastPredictorV5(BillyFastPredictorV3):
    """BillyFast v5 — gap percentile, debut recency, calendar gap, set distribution.

    Adds 9 features on top of V3's 16 (25 total):
    - gap_percentile: how extreme is current gap vs song's own history
    - shows_since_debut / is_recent_debut: new-song revisit dynamics
    - gap_days / avg_days_between_plays / days_overdue: calendar-time signal
    - pct_set_1 / pct_encore / set_affinity: historical set distribution
    """

    MODEL_VERSION = "billy_fast_gbm_v5"
    _FEATURE_COLS: list[str] = BILLY_FAST_V5_FEATURE_COLS

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
        v3 = super()._extra_training_row_features(
            eligible_songs=eligible_songs,
            j=j,
            target_date=target_date,
            gap_e=gap_e,
            career_pct=career_pct,
            p25=p25,
            p50=p50,
            cache=cache,
            plays=plays,
            target_show_index=target_show_index,
        )

        gap_dist = cache["gap_dist"]
        first_play_col = cache["first_play_col"]
        avg_days_bp = cache["avg_days_bp"]
        col_dates = cache["col_dates"]
        set_feats = cache["set_feats"]

        gap_percentile = _gap_percentile_arr(eligible_songs, gap_e, gap_dist)

        shows_since_debut = np.array(
            [float(j - first_play_col.get(s, j)) for s in eligible_songs], dtype=float
        )
        is_recent_debut = (shows_since_debut < 20).astype(float)

        current_date = col_dates[j] if j < len(col_dates) else None
        if current_date is not None:
            gap_days = np.array(
                [
                    (
                        float((current_date - col_dates[j - int(g)]).days)
                        if 0 <= (j - int(g)) < len(col_dates)
                        and col_dates[j - int(g)] is not None
                        else 0.0
                    )
                    for g in gap_e.values
                ],
                dtype=float,
            )
        else:
            gap_days = np.zeros(len(eligible_songs), dtype=float)

        avg_days = np.array(
            [avg_days_bp.get(s, 0.0) for s in eligible_songs], dtype=float
        )

        pct_set_1, pct_encore, set_affinity = _set_dist_arrays(
            eligible_songs, set_feats
        )

        return {
            **v3,
            "gap_percentile": gap_percentile,
            "shows_since_debut": shows_since_debut,
            "is_recent_debut": is_recent_debut,
            "gap_days": gap_days,
            "avg_days_between_plays": avg_days,
            "days_overdue": gap_days - avg_days,
            "pct_set_1": pct_set_1,
            "pct_encore": pct_encore,
            "set_affinity": set_affinity,
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
        v3 = super()._extra_predict_features(
            eligible_songs=eligible_songs,
            n_shows=n_shows,
            ref_date=ref_date,
            gap_e=gap_e,
            career_pct=career_pct,
            p25=p25,
            p50=p50,
            cache=cache,
            plays=plays,
            target_show_context=target_show_context,
        )

        gap_dist = cache["gap_dist"]
        first_play_col = cache["first_play_col"]
        avg_days_bp = cache["avg_days_bp"]
        col_dates = cache["col_dates"]
        set_feats = cache["set_feats"]

        gap_percentile = _gap_percentile_arr(eligible_songs, gap_e, gap_dist)

        shows_since_debut = np.array(
            [float(n_shows - first_play_col.get(s, n_shows)) for s in eligible_songs],
            dtype=float,
        )
        is_recent_debut = (shows_since_debut < 20).astype(float)

        ref_date_val = ref_date.date()
        gap_days = np.array(
            [
                (
                    float((ref_date_val - col_dates[n_shows - int(g)]).days)
                    if 0 <= (n_shows - int(g)) < len(col_dates)
                    and col_dates[n_shows - int(g)] is not None
                    else 0.0
                )
                for g in gap_e.values
            ],
            dtype=float,
        )

        avg_days = np.array(
            [avg_days_bp.get(s, 0.0) for s in eligible_songs], dtype=float
        )

        pct_set_1, pct_encore, set_affinity = _set_dist_arrays(
            eligible_songs, set_feats
        )

        return {
            **v3,
            "gap_percentile": gap_percentile,
            "shows_since_debut": shows_since_debut,
            "is_recent_debut": is_recent_debut,
            "gap_days": gap_days,
            "avg_days_between_plays": avg_days,
            "days_overdue": gap_days - avg_days,
            "pct_set_1": pct_set_1,
            "pct_encore": pct_encore,
            "set_affinity": set_affinity,
        }


# ── BillyFastPredictorV6 ──────────────────────────────────────────────────────


class BillyFastPredictorV6(BillyFastPredictorV3):
    """BillyFast f6 — V3 features with per-show LightGBM early stopping."""

    MODEL_VERSION = "billy_fast_gbm_v6_early_stop"
    _FEATURE_COLS: list[str] = BILLY_FAST_V3_FEATURE_COLS
    _LGB_ROUNDS: int = 500
    _EARLY_STOPPING_ROUNDS: int | None = 25


# ── BillyFastPredictorV7 ──────────────────────────────────────────────────────


class BillyFastPredictorV7(BillyFastPredictorV3):
    """BillyFast V7 — V3 features with full-history training (no 75-show cap).

    Hypothesis: Billy plays ~200+ shows/year, so a 75-show window covers only
    ~4 months.  Seasonal rotation patterns span longer periods.  Goose gained
    +0.025 dual by switching to full-history training.
    """

    MODEL_VERSION = "billy_fast_gbm_v7_full_history"
    _FEATURE_COLS: list[str] = BILLY_FAST_V3_FEATURE_COLS

    def _start_col(self, n_shows: int) -> int:
        return _MIN_PLAYS


class BillyFastPredictorV8(BillyFastPredictorV3):
    """BillyFast V8 — V3 features with 150-show training window (2x the V3 cap)."""

    MODEL_VERSION = "billy_fast_gbm_v8_window_150"
    _FEATURE_COLS: list[str] = BILLY_FAST_V3_FEATURE_COLS

    def _start_col(self, n_shows: int) -> int:
        return max(_MIN_PLAYS, n_shows - 150)


class BillyFastPredictorV9(BillyFastPredictorV3):
    """BillyFast V9 — V3 features + notebook_rank_score using plays_past_50 proxy.

    Sorts eligible songs by (plays_past_50 DESC, gap_shows DESC, song_name ASC)
    — the Notebook-style heuristic — and converts the rank to a normalized score
    in [0, 1].  This gave Goose +0.006 and Phish +0.014 dual improvement.
    """

    MODEL_VERSION = "billy_fast_gbm_v9_notebook_rank"
    _FEATURE_COLS: list[str] = BILLY_FAST_V9_FEATURE_COLS

    @staticmethod
    def _notebook_rank_score(
        *,
        eligible_songs: pd.Index,
        plays_past_50: pd.Series,
        gap_e: pd.Series,
    ) -> list[float]:
        frame = pd.DataFrame(
            {
                "song_name": eligible_songs.astype(str),
                "plays_past_50": plays_past_50.values,
                "gap_shows": gap_e.values,
            }
        )
        ranked = frame.sort_values(
            by=["plays_past_50", "gap_shows", "song_name"],
            ascending=[False, False, True],
        )
        n = len(ranked)
        if n <= 1:
            return [1.0] * n
        scores = {
            str(row["song_name"]): 1.0 - (rank / (n - 1))
            for rank, (_, row) in enumerate(ranked.iterrows())
        }
        return [
            float(scores.get(str(song), 0.0)) for song in eligible_songs.astype(str)
        ]

    def _extra_training_row_features(self, **kwargs: Any) -> dict:
        v3 = super()._extra_training_row_features(**kwargs)
        v3["notebook_rank_score"] = self._notebook_rank_score(
            eligible_songs=kwargs["eligible_songs"],
            plays_past_50=kwargs["p50"],
            gap_e=kwargs["gap_e"],
        )
        return v3

    def _extra_predict_features(self, **kwargs: Any) -> dict:
        v3 = super()._extra_predict_features(**kwargs)
        v3["notebook_rank_score"] = self._notebook_rank_score(
            eligible_songs=kwargs["eligible_songs"],
            plays_past_50=kwargs["p50"],
            gap_e=kwargs["gap_e"],
        )
        return v3


# ── BillyFastPredictorV10 ─────────────────────────────────────────────────────

_BILLY_FAST_V10_LGB_PARAMS: dict[str, Any] = {
    **_LGB_PARAMS,
    "num_leaves": 15,
    "min_data_in_leaf": 10,
}


class BillyFastPredictorV10(BillyFastPredictorV3):
    """BillyFast V10 — V3 features with HP-tuned leaves=15 + min_leaf=10.

    Combo sweep winner: dual=0.3879 (+0.011 vs V3). Less capacity and more
    leaf regularization help Billy's model generalize across its rapidly
    changing rotation patterns.
    """

    MODEL_VERSION = "billy_fast_gbm_v10_hp_tuned"
    _FEATURE_COLS: list[str] = BILLY_FAST_V3_FEATURE_COLS
    _LGB_PARAMS: dict[str, Any] = _BILLY_FAST_V10_LGB_PARAMS


# Accepted Billy baseline. Historical experiment class names remain importable so
# prior backtest artifacts and diagnostic commands keep their original meaning.
BillyFastBaselinePredictor = BillyFastPredictorV10


# ── V10 experiment subclasses ─────────────────────────────────────────────────


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

    cutoff_date = ref_date - pd.Timedelta(days=days)

    valid_cols = [
        i
        for i, d in enumerate(col_dates[: ref_col + 1])
        if d is not None and d >= cutoff_date
    ]

    if not valid_cols:
        return pd.Series(0.0, index=presence.index)

    plays_in_window = presence.iloc[:, valid_cols].sum(axis=1).astype(float)
    return plays_in_window


class BillyFastV10PlaysPastYear(BillyFastPredictorV10):
    """V10 + plays_past_year (distinct shows in trailing 365 days)."""

    MODEL_VERSION = "billy_fast_gbm_v10_feat_plays_past_year"
    _FEATURE_COLS: list[str] = [
        *BillyFastPredictorV10._FEATURE_COLS,
        "plays_past_year",
    ]

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
        extra = super()._extra_training_row_features(
            eligible_songs=eligible_songs,
            j=j,
            target_date=target_date,
            gap_e=gap_e,
            career_pct=career_pct,
            p25=p25,
            p50=p50,
            cache=cache,
            plays=plays,
            target_show_index=target_show_index,
        )
        ref_col = j - 1
        extra["plays_past_year"] = (
            _window_plays_by_days(
                plays,
                cache["presence"],
                ref_col,
                365,
                cache["col_dates"],
            )
            .loc[eligible_songs]
            .values
        )
        return extra

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
        extra = super()._extra_predict_features(
            eligible_songs=eligible_songs,
            n_shows=n_shows,
            ref_date=ref_date,
            gap_e=gap_e,
            career_pct=career_pct,
            p25=p25,
            p50=p50,
            cache=cache,
            plays=plays,
            target_show_context=target_show_context,
        )
        ref_col = n_shows - 1
        extra["plays_past_year"] = (
            _window_plays_by_days(
                plays,
                cache["presence"],
                ref_col,
                365,
                cache["col_dates"],
            )
            .loc[eligible_songs]
            .values
        )
        return extra


class BillyFastV10LongRotation(BillyFastPredictorV10):
    """V10 + longer-window rotation pressure.

    Adds plays_past_100, diff_50_to_100, long_rotation_pressure.
    """

    MODEL_VERSION = "billy_fast_gbm_v10_feat_long_rotation"
    _FEATURE_COLS: list[str] = [
        *BillyFastPredictorV10._FEATURE_COLS,
        "plays_past_100",
        "diff_50_to_100",
        "long_rotation_pressure",
    ]

    def _rotation_features(
        self,
        *,
        eligible_songs: pd.Index,
        upper_col: int,
        p50: pd.Series,
        gap_e: pd.Series,
        cache: dict,
    ) -> dict[str, Any]:
        p100 = _window_plays(cache["cum"], upper_col, 100).loc[eligible_songs]
        pct50 = p50 / max(1, min(50, upper_col))
        pct100 = p100 / max(1, min(100, upper_col))
        return {
            "plays_past_100": p100.values,
            "diff_50_to_100": (pct50 - pct100).values,
            "long_rotation_pressure": (gap_e * pct100.clip(lower=0.01)).values,
        }

    def _extra_training_row_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_training_row_features(**kwargs)
        extra.update(
            self._rotation_features(
                eligible_songs=kwargs["eligible_songs"],
                upper_col=kwargs["j"],
                p50=kwargs["p50"],
                gap_e=kwargs["gap_e"],
                cache=kwargs["cache"],
            )
        )
        return extra

    def _extra_predict_features(self, **kwargs: Any) -> dict:
        extra = super()._extra_predict_features(**kwargs)
        extra.update(
            self._rotation_features(
                eligible_songs=kwargs["eligible_songs"],
                upper_col=kwargs["n_shows"],
                p50=kwargs["p50"],
                gap_e=kwargs["gap_e"],
                cache=kwargs["cache"],
            )
        )
        return extra


class BillyFastV10EarlyStop(BillyFastPredictorV10):
    """V10 + 500 rounds + 25-round per-show early stopping."""

    MODEL_VERSION = "billy_fast_gbm_v10_early_stop"
    _LGB_ROUNDS: int = 500
    _EARLY_STOPPING_ROUNDS: int | None = 25


class BillyFastV10FullHistory(BillyFastPredictorV10):
    """V10 with full-history training (no 75-show window cap)."""

    MODEL_VERSION = "billy_fast_gbm_v10_full_history"

    def _start_col(self, n_shows: int) -> int:
        return _MIN_PLAYS


class BillyFastV10Window150(BillyFastPredictorV10):
    """V10 with 150-show training window (2x the V10 cap)."""

    MODEL_VERSION = "billy_fast_gbm_v10_window_150"

    def _start_col(self, n_shows: int) -> int:
        return max(_MIN_PLAYS, n_shows - 150)
