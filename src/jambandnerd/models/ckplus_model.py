"""
Band-agnostic CK+ (gap-based) model implementation.
Aggregates setlist data by song name using gap-based method.
"""

import pandas as pd

from jambandnerd.logging_utils import get_logger

logger = get_logger(__name__)


def aggregate_setlist_features(df, method="mean"):
    """
    Aggregates setlist data by song name using the CK+ (gap-based) method.

    Args:
        df (pd.DataFrame): Setlist data with 'song', 'show_index_overall', 'showdate'
        method (str): 'mean' or 'median' for gap calculation

    Returns:
        pd.DataFrame: CK+ score and related features per song
    """
    logger.info("Starting CK+ model aggregation for %d setlist entries", len(df))

    # Standardize 'showdate' to datetime, coercing errors to NaT
    df['showdate'] = pd.to_datetime(df['showdate'], errors='coerce')

    # Ensure 'show_index_overall' exists
    if "show_index_overall" not in df.columns:
        show_order = (
            df[["showid", "showdate"]]
            .drop_duplicates()
            .sort_values("showdate")
            .reset_index(drop=True)
        )
        show_order["show_index_overall"] = show_order.index + 1
        df = df.merge(
            show_order[["showid", "show_index_overall"]], on="showid", how="left"
        )

    # Calculate the current show number as the next show after today
    # Filter to shows up to today's date to avoid including future scheduled shows
    today = pd.Timestamp.now().normalize()
    past_shows = df[df['showdate'] <= today]

    if past_shows.empty:
        logger.warning("No shows found up to today's date. Using all shows.")
        current_show_num = df["show_index_overall"].max() + 1
    else:
        current_show_num = past_shows["show_index_overall"].max() + 1

    logger.info("Using current show number: %d (next show after today)", current_show_num)
    df = df.sort_values(by=["song", "show_index_overall"], ascending=[True, True])
    df["gap"] = df.groupby("song")["show_index_overall"].diff()

    song_stats = df.groupby("song").agg(
        {
            "showid": "nunique",
            "showdate": "max",
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
            "showid_nunique": "times_played",
            "showdate_max": "ltp_date",
            "show_index_overall_max": "ltp_show_num",
            "gap_mean": "avg_gap",
            "gap_median": "med_gap",
            "gap_std": "std_gap",
        }
    )
    song_stats["current_gap"] = current_show_num - song_stats["ltp_show_num"]
    song_stats["gap_variance"] = song_stats["std_gap"] ** 2
    song_stats = song_stats[
        (song_stats["times_played"] > 2) & (song_stats["current_gap"] > 0)
    ].reset_index()

    # Filter out songs with invalid gap data before calculations
    # Remove songs where avg_gap or med_gap is 0 or NaN to prevent division by zero
    if method == "mean":
        valid_songs = (song_stats["avg_gap"] > 0) & (song_stats["avg_gap"].notna())
        song_stats = song_stats[valid_songs].copy()
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
        valid_songs = (song_stats["med_gap"] > 0) & (song_stats["med_gap"].notna())
        song_stats = song_stats[valid_songs].copy()
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

    # Calculate gap_z_score with additional safety checks
    # Ensure std_gap is positive and not NaN
    valid_std = (song_stats["std_gap"] > 0) & (song_stats["std_gap"].notna())
    song_stats = song_stats[valid_std].copy()

    song_stats["gap_z_score"] = song_stats["gap_ratio"] / (song_stats["std_gap"] + 1e-6)
    song_stats["ckplus_score"] = song_stats["gap_z_score"] * song_stats["gap_ratio"]

    # Final validation: remove any remaining inf or NaN values
    numeric_cols = ["gap_ratio", "gap_z_score", "ckplus_score"]
    for col in numeric_cols:
        song_stats = song_stats[song_stats[col].notna() & ~song_stats[col].isin([float('inf'), float('-inf')])].copy()

    song_stats = (
        song_stats[final_columns]
        .sort_values(by="ckplus_score", ascending=False)
        .reset_index(drop=True)
    )

    # Filter out songs with current_gap > 75 and return top 100
    song_stats = (
        song_stats[song_stats["current_gap"] <= 75].copy().reset_index(drop=True)
    )
    logger.info("Generated %d CK+ predictions", len(song_stats.head(100)))
    return song_stats.head(100)


def run_ckplus_model(
    song_data: pd.DataFrame,
    show_data: pd.DataFrame,
    venue_data: pd.DataFrame,
    setlist_data: pd.DataFrame,
    transition_data: pd.DataFrame,
    gap_threshold: int = 75,
    top_n: int = 100,
) -> pd.DataFrame:
    """
    Run the complete CK+ model pipeline.

    Args:
        song_data: DataFrame with song information
        show_data: DataFrame with show information
        venue_data: DataFrame with venue information
        setlist_data: DataFrame with setlist information
        transition_data: DataFrame with transition information
        gap_threshold: Maximum gap to include in predictions (default 75)
        top_n: Number of top predictions to return (default 100)

    Returns:
        pd.DataFrame: CK+ predictions with scores
    """
    logger.info(
        "Running CK+ model with gap_threshold=%d, top_n=%d", gap_threshold, top_n
    )

    # Prepare setlist data for CK+ model
    # The model expects columns: song, showid, showdate, show_index_overall
    # Conditionally add song names if they aren't already present
    if "song" not in setlist_data.columns:
        setlist_with_songs = setlist_data.merge(
            song_data[["song_id", "song"]], on="song_id", how="left"
        )
    else:
        setlist_with_songs = setlist_data.copy()
        # If song column exists but song_id doesn't, add it via merge
        if "song_id" not in setlist_with_songs.columns:
            setlist_with_songs = setlist_with_songs.merge(
                song_data[["song_id", "song"]], on="song", how="left"
            )

    setlist_with_shows = setlist_with_songs.merge(
        show_data[["show_id", "show_date"]], on="show_id", how="left"
    )

    # Rename columns to match model expectations
    model_input = setlist_with_shows.rename(
        columns={"show_id": "showid", "show_date": "showdate"}
    )

    # Run the CK+ aggregation
    predictions = aggregate_setlist_features(model_input, method="mean")

    # Apply custom filtering
    predictions = predictions[predictions["current_gap"] <= gap_threshold].copy()

    # --- Post-processing to match Supabase schema ---
    # 1. Add prediction_date and band
    predictions["prediction_date"] = pd.to_datetime("today").date()
    predictions["band"] = show_data["band"].iloc[0]



    # 3. Rename columns to match the database
    predictions = predictions.rename(
        columns={
            "song": "song_name",
            "ltp_date": "last_played_date",
            "times_played": "times_played_total",
        }
    )

    # 4. Format date columns to MM/DD/YYYY text format
    predictions["prediction_date"] = pd.to_datetime(
        predictions["prediction_date"]
    ).dt.strftime("%m/%d/%Y")
    predictions["last_played_date"] = pd.to_datetime(
        predictions["last_played_date"]
    ).dt.strftime("%m/%d/%Y")

    logger.info(
        "CK+ model generated %d predictions (before top-N filtering)", len(predictions)
    )

    # Ensure predictions are unique per song to avoid upsert conflicts
    predictions = predictions.drop_duplicates(subset=["song_name"], keep="first")

    return predictions.head(top_n)
