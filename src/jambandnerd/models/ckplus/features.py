from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import pandas as pd


@dataclass
class CKPlusAggregates:
    features: pd.DataFrame
    reference_show_date: date
    reference_index: int


def compute_gap_features(
    shows_df: pd.DataFrame,
    setlists_df: pd.DataFrame,
    reference_show_date: date,
    window_days: int = 5 * 365,
) -> CKPlusAggregates:
    """
    Compute CK+ gap-based features using a lookback window of window_days ending at the
    last completed show before the reference date.
    """
    if shows_df.empty or setlists_df.empty:
        return CKPlusAggregates(features=pd.DataFrame(), reference_show_date=reference_show_date, reference_index=0)

    # Normalize data types
    shows = shows_df.copy()
    shows["show_id"] = shows["show_id"].astype(str)
    shows["_dt"] = pd.to_datetime(shows["show_date"]).dt.date
    shows = shows.sort_values(["_dt", "show_id"]).reset_index(drop=True)
    shows["_idx"] = range(1, len(shows) + 1)

    sets = setlists_df.copy()
    sets["show_id"] = sets["show_id"].astype(str)

    # Determine last completed show strictly before reference date
    last_completed = shows[shows["_dt"] < reference_show_date].tail(1)
    if last_completed.empty:
        return CKPlusAggregates(features=pd.DataFrame(), reference_show_date=reference_show_date, reference_index=0)

    ref_idx = int(last_completed["_idx"].iloc[0]) + 1  # reference index is next show index
    last_completed_date: date = last_completed["_dt"].iloc[0]
    window_start = last_completed_date - timedelta(days=window_days)

    # Join setlists with shows to obtain show indices and filter to window
    idx_by_id = shows.set_index("show_id")["_idx"].to_dict()
    dt_by_id = shows.set_index("show_id")["_dt"].to_dict()
    s = sets.copy()
    s = s[s["show_id"].isin(idx_by_id.keys())]
    s["_idx"] = s["show_id"].map(idx_by_id)
    s["_dt"] = s["show_id"].map(dt_by_id)
    s = s[(s["_dt"] >= window_start) & (s["_dt"] <= last_completed_date)]

    if s.empty:
        return CKPlusAggregates(features=pd.DataFrame(), reference_show_date=reference_show_date, reference_index=ref_idx)

    # For each song, compute plays, last played, current gap, and gap stats
    def _stats_for_song(group: pd.DataFrame) -> pd.Series:
        plays_idx = sorted(group["_idx"].tolist())
        times_played = len(plays_idx)
        last_idx = plays_idx[-1]
        current_gap = (ref_idx - 1) - last_idx
        gaps = []
        for i in range(1, len(plays_idx)):
            gaps.append(plays_idx[i] - plays_idx[i - 1])
        avg_gap = float(pd.Series(gaps).mean()) if gaps else float("nan")
        std_gap = float(pd.Series(gaps).std(ddof=0)) if gaps else float(0.0)
        last_dt = group.sort_values("_idx")["_dt"].iloc[-1]
        return pd.Series(
            {
                "times_played": times_played,
                "last_played_dt": last_dt,
                "current_gap": int(current_gap),
                "avg_gap": avg_gap,
                "std_gap": std_gap,
                "last_played_idx": int(last_idx),
            }
        )

    # Use include_groups=False to silence pandas future warning about groupby.apply
    feat = s.groupby("song_name").apply(_stats_for_song, include_groups=False).reset_index()
    # Derived metrics
    feat["gap_ratio"] = feat.apply(lambda r: (r["current_gap"] / r["avg_gap"]) if pd.notna(r["avg_gap"]) and r["avg_gap"] > 0 else float("nan"), axis=1)
    feat["gap_z_score"] = feat.apply(
        lambda r: ((r["current_gap"] - r["avg_gap"]) / r["std_gap"]) if (r["std_gap"] and r["std_gap"] > 0) else 0.0,
        axis=1,
    )
    # LTP as mm/dd/yyyy string
    feat["LTP"] = feat["last_played_dt"].apply(lambda d: f"{d.month:02d}/{d.day:02d}/{d.year}" if isinstance(d, date) else None)

    return CKPlusAggregates(features=feat, reference_show_date=reference_show_date, reference_index=ref_idx)


