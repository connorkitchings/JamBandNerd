"""
model.py - Aggregates setlist features for Goose CK+ predictions.

NOTE: For import resolution, run scripts from the CKPlus root directory
and mark CKPlus as the source root in your IDE.
"""

from .utils.logger import get_logger

logger = get_logger(__name__)


def aggregate_setlist_features(df, method="mean"):
    """
    Aggregate setlist features for CK+ prediction.
    Args:
        df (pd.DataFrame): Input merged setlist DataFrame.
        method (str): 'mean' or 'median' for gap calculation.
    Returns:
        pd.DataFrame: Aggregated features for prediction.
    """
    max_show_num = df["show_num"].max()
    df = df.sort_values(by=["song", "show_num"], ascending=[True, True])
    df["gap"] = df.groupby("song")["show_num"].diff()

    song_stats = df.groupby("song").agg(
        {
            "show_id": "nunique",
            "show_date": "max",
            "show_num": "max",
            "gap": ["mean", "median", "std"],
        }
    )
    # Flatten columns
    song_stats.columns = [
        "_".join(col).strip() if isinstance(col, tuple) else col
        for col in song_stats.columns.values
    ]
    # Rename columns
    song_stats = song_stats.rename(
        columns={
            "show_id_nunique": "times_played",
            "show_date_max": "ltp_date",
            "show_num_max": "ltp_show_num",
            "gap_mean": "avg_gap",
            "gap_median": "med_gap",
            "gap_std": "std_gap",
        }
    )
    song_stats["current_gap"] = max_show_num - song_stats["ltp_show_num"]
    song_stats["gap_variance"] = song_stats["std_gap"] ** 2
    song_stats = song_stats[song_stats["current_gap"] < 100]
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
    song_stats = song_stats.sort_values(by="ckplus_score", ascending=False).reset_index(
        drop=True
    )
    song_stats = song_stats[final_columns]
    song_stats = song_stats.head(50)
    return song_stats
