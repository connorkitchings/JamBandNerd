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
from jambandnerd.transformations.run_context import (
    normalize_target_show_context,
    normalized_venue_key,
    same_venue_run_show_indices,
)

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
    base_columns = ["song_name", "show_index", "show_date"]
    context_columns = [
        column
        for column in ("venue_name", "city", "state", "country")
        if column in plays.columns
    ]
    df = plays[base_columns + context_columns].copy()
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

        return {
            "presence": presence,
            "show_cols": show_cols,
            "cum": cum,
            "gap_mat": gap_mat,
            "month_cums": month_cums,
            "show_date_map": show_date_map,
            "col_dates": col_dates,
            "col_venues": col_venues,
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

        start_col = max(_MIN_PLAYS, n_shows - _TRAINING_WINDOW)
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
        p25: pd.Series,
        p50: pd.Series,
        cache: dict,
        plays: pd.DataFrame,
    ) -> dict:
        return {}

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

        train_data = lgb.Dataset(
            X_all[self._FEATURE_COLS],
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
        extra = self._extra_predict_features(
            eligible_songs=eligible_songs,
            n_shows=n_shows,
            ref_date=ref_date,
            p25=p25,
            p50=p50,
            cache=cache,
            plays=plays,
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
        return [
            BillyPrediction(
                song_name=str(eligible_songs[i]),
                probability=float(probs[i]),
                gap_shows=int(gap_arr[i]),
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
        p25: pd.Series,
        p50: pd.Series,
        cache: dict,
        plays: pd.DataFrame,
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
