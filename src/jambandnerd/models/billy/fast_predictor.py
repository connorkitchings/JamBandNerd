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

from dataclasses import dataclass
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from jambandnerd.models.base import PredictionModel
from jambandnerd.transformations.gaps import ModelData

from .model import _BILLY_ORIGINAL_ARTISTS, _fetch_songs_from_supabase

# ── Constants ─────────────────────────────────────────────────────────────────

_MIN_PLAYS = 3
_RETIRED_GAP = 120     # shows; songs absent > this are excluded
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
class BillyPrediction:
    song_name: str
    probability: float
    gap_shows: int


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


def _clean_plays(plays: pd.DataFrame) -> pd.DataFrame:
    df = plays[["song_name", "show_index", "show_date"]].copy()
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
        songs_df_resolved = (
            songs_df if songs_df is not None else _fetch_songs_from_supabase()
        )
        self._songs_lookup: dict[str, float] = _build_is_cover_lookup(songs_df_resolved)
        self._model: lgb.Booster | None = None
        # Cached from train() for reuse in predict()
        self._cache: dict | None = None

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

        return {
            "presence": presence,
            "show_cols": show_cols,
            "cum": cum,
            "gap_mat": gap_mat,
            "month_cums": month_cums,
            "show_date_map": show_date_map,
        }

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
        all_songs = presence.index
        n_shows = len(show_cols)

        start_col = max(_MIN_PLAYS, n_shows - _TRAINING_WINDOW)

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
            month_before = month_cums[target_month].iloc[:, ref_col].loc[eligible_songs]
            mpr = (month_before / total_e.clip(lower=1)).fillna(0.0)

            is_cover = _is_cover_series(eligible_songs, self._songs_lookup)
            labels = presence.iloc[:, j].loc[eligible_songs].astype(float)

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
                        "label": labels.values,
                    }
                )
            )
            group_sizes.append(int(eligible_mask.sum()))

        if not rows:
            return

        X_all = pd.concat(rows, ignore_index=True)
        y = X_all.pop("label")

        train_data = lgb.Dataset(
            X_all[BILLY_FAST_FEATURE_COLS],
            label=y,
            group=group_sizes,
            free_raw_data=False,
        )
        self._model = lgb.train(
            _LGB_PARAMS,
            train_data,
            num_boost_round=_LGB_ROUNDS,
        )

    # ── Prediction ────────────────────────────────────────────────────────────

    def predict(self, model_data: ModelData, top_k: int = 50) -> list[BillyPrediction]:
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

        X = pd.DataFrame(
            {
                "gap_shows": gap_e.values,
                "plays_past_10": p10.values,
                "plays_past_25": p25.values,
                "plays_past_50": p50.values,
                "career_play_pct": career_pct.values,
                "month_play_rate": mpr.values,
                "is_cover": is_cover,
            },
            index=eligible_songs,
        )

        scores = self._model.predict(X[BILLY_FAST_FEATURE_COLS].values)
        probs = 1.0 / (1.0 + np.exp(-scores))

        order = np.argsort(probs)[::-1][:top_k]
        gap_arr = gap_predict.loc[eligible_songs].values
        return [
            BillyPrediction(
                song_name=str(eligible_songs[i]),
                probability=float(probs[i]),
                gap_shows=int(gap_arr[i]),
            )
            for i in order
        ]
