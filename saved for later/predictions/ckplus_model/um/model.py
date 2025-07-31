"""
Aggregate setlist data by song for UM using the CK+ (gap-based) method.
"""

from typing import Literal

import pandas as pd

from predictions.ckplus.utils.logger import get_logger

logger = get_logger(__name__)


def aggregate_setlist_features(
    df: pd.DataFrame, method: Literal["mean", "median"] = "mean"
) -> pd.DataFrame:
    """
    Aggregates setlist data by song for UM using the CK+ (gap-based) method.

    Args:
        df (pd.DataFrame): Setlist data with 'song', 'show_date', and optionally 'venue'.
        method (Literal['mean', 'median']): Method for gap calculation.

    Returns:
        pd.DataFrame: CK+ score and related features per song (top 50 by score).
    """
    # Assign a unique sequential show index by date and venue
    show_keys = ["show_date", "venue"] if "venue" in df.columns else ["show_date"]
    show_df = (
        df.drop_duplicates(subset=show_keys)
        .sort_values(by=show_keys)
        .reset_index(drop=True)
    )
    show_df["show_index_overall"] = show_df.index + 1
    df = df.merge(show_df[show_keys + ["show_index_overall"]], on=show_keys, how="left")
    max_show_num = df["show_index_overall"].max()
    df = df.sort_values(by=["song", "show_index_overall"], ascending=[True, True])
    df["gap"] = df.groupby("song")["show_index_overall"].diff()

    song_stats = (
        df.groupby("song")
        .agg(
            times_played=("show_date", "count"),
            ltp_date=("show_date", "max"),
            ltp_show_num=("show_index_overall", "max"),
            avg_gap=("gap", "mean"),
            med_gap=("gap", "median"),
            std_gap=("gap", "std"),
        )
        .reset_index()
    )
    song_stats["current_gap"] = max_show_num - song_stats["ltp_show_num"]
    song_stats["gap_variance"] = song_stats["std_gap"] ** 2
    song_stats = song_stats[song_stats["current_gap"] < 100].copy()
    song_stats = song_stats[
        (song_stats["times_played"] > 5) & (song_stats["current_gap"] > 0)
    ].copy()

    if method == "mean":
        song_stats["gap_ratio"] = song_stats["current_gap"] / song_stats["avg_gap"]
        gap_col = "avg_gap"
    elif method == "median":
        song_stats["gap_ratio"] = song_stats["current_gap"] / song_stats["med_gap"]
        gap_col = "med_gap"
    else:
        raise ValueError("method must be 'mean' or 'median'")

    song_stats["gap_z_score"] = song_stats["gap_ratio"] / song_stats["std_gap"]
    song_stats["ck+_score"] = song_stats["gap_z_score"] * song_stats["gap_ratio"]
    song_stats = song_stats.sort_values(by="ck+_score", ascending=False).reset_index(
        drop=True
    )
    logger.info(
        "Aggregated CK+ features for %d songs using %s gap.", len(song_stats), method
    )
    return song_stats[
        [
            "song",
            "times_played",
            "ltp_date",
            "current_gap",
            gap_col,
            "gap_ratio",
            "gap_z_score",
            "ck+_score",
        ]
    ].head(50)
