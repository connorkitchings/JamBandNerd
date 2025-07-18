"""
Aggregate setlist data by song name for WSP using the CK+ (gap-based) method.
"""

import pandas as pd

from .utils.logger import get_logger

logger = get_logger(__name__)


def aggregate_setlist_features(df: pd.DataFrame, method: str = "mean") -> pd.DataFrame:
    """
    Aggregates setlist data by song name for WSP using the CK+ (gap-based) method.
    Args:
        df (pd.DataFrame): Setlist data with 'song', 'show_date', 'link', 'show_num'
        method (str): 'mean' or 'median' for gap calculation
    Returns:
        pd.DataFrame: CK+ score and related features per song
    """
    # Ensure 'show_index_overall' exists
    if "show_index_overall" not in df.columns:
        show_order = (
            df[["link", "show_date"]]
            .drop_duplicates()
            .sort_values("show_date")
            .reset_index(drop=True)
        )
        show_order["show_index_overall"] = show_order.index + 1
        df = df.merge(show_order[["link", "show_index_overall"]], on="link", how="left")
    max_show_num = df["show_index_overall"].max()
    df = df.sort_values(by=["song", "show_index_overall"], ascending=[True, True])
    df["gap"] = df.groupby("song")["show_index_overall"].diff()

    song_stats = df.groupby("song").agg(
        {
            "link": "nunique",
            "show_date": "max",
            "show_index_overall": "max",
            "gap": ["mean", "median", "std"],
        }
    )
    song_stats.columns = [
        "_".join(col).strip() if isinstance(col, tuple) else col
        for col in song_stats.columns.values
    ]
    song_stats = song_stats.rename(
        columns={
            "link_nunique": "times_played",
            "show_date_max": "ltp_date",
            "show_index_overall_max": "ltp_show_num",
            "gap_mean": "avg_gap",
            "gap_median": "med_gap",
            "gap_std": "std_gap",
        }
    )
    song_stats["current_gap"] = max_show_num - song_stats["ltp_show_num"]
    song_stats["gap_variance"] = song_stats["std_gap"] ** 2
    song_stats = song_stats[song_stats["current_gap"] < 75]
    song_stats = song_stats[
        (song_stats["times_played"] > 5) & (song_stats["current_gap"] > 0)
    ].reset_index()

    if method == "mean":
        song_stats["gap_ratio"] = song_stats["current_gap"] / song_stats["avg_gap"]
        final_columns = [
            "song",
            "times_played",
            "ltp_date",
            "current_gap",
            "avg_gap",
            "gap_ratio",
            "gap_z_score",
            "ckplus_score",
        ]
    elif method == "median":
        song_stats["gap_ratio"] = song_stats["current_gap"] / song_stats["med_gap"]
        final_columns = [
            "song",
            "times_played",
            "ltp_date",
            "current_gap",
            "med_gap",
            "gap_ratio",
            "gap_z_score",
            "ckplus_score",
        ]
    else:
        raise ValueError("method must be 'mean' or 'median'")

    song_stats["gap_z_score"] = song_stats["gap_ratio"] / song_stats["std_gap"]
    song_stats["ckplus_score"] = song_stats["gap_z_score"] * song_stats["gap_ratio"]
    song_stats = (
        song_stats[final_columns]
        .sort_values(by="ckplus_score", ascending=False)
        .reset_index(drop=True)
    )
    return song_stats.head(50)
