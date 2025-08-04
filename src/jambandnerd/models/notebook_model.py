"""
Band-agnostic notebook model implementation.
Aggregates setlist data by song name using time-based filtering and gap analysis.
"""

from datetime import datetime, timedelta

import pandas as pd

from jambandnerd.logging_utils import get_logger

logger = get_logger(__name__)


def aggregate_setlist_features(
    df, target_showdate, time_filter_days: int = 365, gap_threshold: int = 2
):
    """
    Aggregates setlist data by song name following the notebook model approach:
    1. Load all setlist data
    2. Remove any setlists from more than 1 year ago
    3. Handle aggregation and ordering logic

    Args:
        df (pd.DataFrame): Setlist data with 'song', 'showid', and 'showdate'
        target_showdate (str or datetime): Target show date (current date for predictions)

    Returns:
        pd.DataFrame: Aggregated features per song (by name)
    """
    logger.info(
        "Starting notebook model aggregation for %d total setlist entries", len(df)
    )
    # Ensure target_showdate is a datetime object
    if isinstance(target_showdate, str):
        try:
            target_showdate = datetime.strptime(target_showdate, "%Y-%m-%d")
        except ValueError:
            try:
                target_showdate = datetime.strptime(target_showdate, "%m-%d-%Y")
            except ValueError as e:
                logger.error("Error parsing target show date: %s", e)
                raise ValueError(
                    f"'{target_showdate}' does not match '%Y-%m-%d' or '%m-%d-%Y'"
                ) from e

    # Standardize 'showdate' to datetime, coercing errors to NaT
    df['showdate'] = pd.to_datetime(df['showdate'], errors='coerce')

    # Calculate next show number using same logic as CK+ model
    # Ensure 'show_index_overall' exists for consistent gap calculation
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

    # Calculate the next show number (same logic as CK+ model)
    today = pd.Timestamp.now().normalize()
    past_shows = df[df['showdate'] <= today]

    if past_shows.empty:
        logger.warning("No shows found up to today's date. Using all shows.")
        next_show_num = df["show_index_overall"].max() + 1
    else:
        next_show_num = past_shows["show_index_overall"].max() + 1

    logger.info("Using next show number: %d (next show after today)", next_show_num)

    # Step 2: Remove any setlists from more than 1 year ago and from the target date.
    time_filter_ago = target_showdate - timedelta(days=time_filter_days)
    logger.info(
        "Filtering data to last %d days (since %s), excluding the target date.",
        time_filter_days,
        time_filter_ago.strftime("%Y-%m-%d"),
    )

    # Ensure both sides of comparison are datetime objects without timezone info
    df_copy = df.copy()
    df_copy["showdate"] = pd.to_datetime(df_copy["showdate"]).dt.tz_localize(None)
    # Filter to last year's data, excluding the target date itself
    mask = (df_copy["showdate"] >= time_filter_ago) & (
        df_copy["showdate"] < target_showdate
    )
    df_last_year = df_copy[mask].copy()
    logger.info("After 1-year filter: %d setlist entries remain", len(df_last_year))

    if df_last_year.empty:
        logger.warning("No setlist data found within the last year")
        return pd.DataFrame()
    # Step 3: Handle aggregation and ordering logic
    # Group by song and calculate features
    song_groups = (
        df_last_year.groupby("song")
        .agg(
            {
                "showid": ["count", "nunique"],  # times played and unique shows
                "showdate": [
                    "max",
                    "min",
                    list,
                ],  # last played, first played, all dates
            }
        )
        .reset_index()
    )

    # Flatten column names
    song_groups.columns = [
        "song",
        "times_played_total",
        "times_played_last_year",
        "last_time_played_date",
        "first_time_played_date",
        "all_play_dates",
    ]

    # Calculate gap-based features
    results = []
    for _, row in song_groups.iterrows():
        song = row["song"]
        times_played = row["times_played_last_year"]
        last_played = row["last_time_played_date"]
        all_dates = sorted(row["all_play_dates"])

        # Calculate show gaps if we have multiple plays
        if times_played > 1:
            # Get unique show dates for this song
            song_show_dates = sorted(set(all_dates))
            # Get all unique show dates in the dataset for gap calculation
            all_show_dates = sorted(df_last_year["showdate"].unique())

            # Calculate gaps between plays
            gaps = []
            for i in range(len(song_show_dates) - 1):
                current_date = song_show_dates[i]
                next_date = song_show_dates[i + 1]
                # Count shows between these dates
                shows_between = len(
                    [d for d in all_show_dates if current_date < d < next_date]
                )
                gaps.append(shows_between + 1)  # +1 to include the gap itself

            average_gap = round(sum(gaps) / len(gaps), 3) if gaps else None
            median_gap = round(pd.Series(gaps).median(), 2) if gaps else None

            # Calculate current gap using next show number (same logic as CK+ model)
            # Find the show number of the last time this song was played
            last_show_entries = df_last_year[df_last_year['song'] == song]
            if not last_show_entries.empty:
                last_show_num = last_show_entries['show_index_overall'].max()
                current_show_gap = next_show_num - last_show_num
            else:
                current_show_gap = None
        else:
            average_gap = None
            median_gap = None
            current_show_gap = None

        results.append(
            {
                "song": song,
                "times_played_last_year": int(times_played),
                "last_played_date": last_played,  # Already in MM/DD/YYYY format
                "current_gap": int(current_show_gap)
                if current_show_gap is not None
                else None,
                "average_gap": float(average_gap) if average_gap is not None else None,
                "median_gap": float(median_gap) if median_gap is not None else None,
            }
        )

    # Create final DataFrame
    agg_df = pd.DataFrame(results)
    if not agg_df.empty:
        # Rule 3: Exclude songs played in the last 3 shows.
        # A gap of 0 means played in the last show, 1 in the 2nd to last, etc.
        # We want songs with a gap greater than 2.
        initial_count = len(agg_df)
        # Also filter out songs with no gap data, as they are not predictable with this metric.
        agg_df = agg_df.dropna(subset=["current_gap"])
        agg_df = agg_df[agg_df["current_gap"] > gap_threshold].copy()
        logger.info(
            "Filtered out %d songs (gap < %d or no gap data). %d predictions remain.",
            initial_count - len(agg_df),
            gap_threshold,
            len(agg_df),
        )

        # Sort by times played and current gap, both in descending order
        agg_df = agg_df.sort_values(
            by=["times_played_last_year", "current_gap"], ascending=[False, False]
        )
        logger.info("Generated %d song predictions", len(agg_df))
    else:
        logger.warning("No predictions generated")

    # Rename average_gap to avg_gap to match schema
    if "average_gap" in agg_df.columns:
        agg_df = agg_df.rename(columns={"average_gap": "avg_gap"})




    return agg_df


def run_notebook_model(
    song_data: pd.DataFrame,
    show_data: pd.DataFrame,
    venue_data: pd.DataFrame,
    setlist_data: pd.DataFrame,
    transition_data: pd.DataFrame,
    gap_threshold: int,
    time_filter_days: int = 365,
) -> pd.DataFrame:
    """
    Run the complete Notebook model pipeline.

    Args:
        song_data: DataFrame with song information
        show_data: DataFrame with show information
        venue_data: DataFrame with venue information
        setlist_data: DataFrame with setlist information
        transition_data: DataFrame with transition information
        recent_shows_filter: Number of recent shows to exclude (default 3)

    Returns:
        pd.DataFrame: Notebook model predictions
    """
    logger.info("Running Notebook model with gap_threshold=%d", gap_threshold)

    # Prepare setlist data for Notebook model
    # The model expects columns: song, showid, showdate
    # Drop existing 'song' column to prevent merge conflicts (song_x, song_y)
    setlist_with_songs = setlist_data.drop(columns=["song"], errors="ignore").merge(
        song_data[["song_id", "song"]], on="song_id", how="left"
    )

    setlist_with_shows = setlist_with_songs.merge(
        show_data[["show_id", "show_date"]], on="show_id", how="left"
    )

    # Rename columns to match model expectations
    model_input = setlist_with_shows.rename(
        columns={"show_id": "showid", "show_date": "showdate"}
    )

    # Use today's date as target for predictions
    target_date = datetime.now().strftime("%Y-%m-%d")

    # Run the Notebook aggregation
    predictions = aggregate_setlist_features(
        model_input,
        target_date,
        time_filter_days=time_filter_days,
        gap_threshold=gap_threshold,
    )

    if not predictions.empty:
        # --- Post-processing to match Supabase schema ---
        # 1. Add prediction_date and band
        predictions["prediction_date"] = pd.to_datetime("today").strftime("%m/%d/%Y")
        predictions["band"] = show_data["band"].iloc[0]

        # 2. Merge to get song_id and rename columns
        predictions = predictions.merge(
            song_data[["song", "song_id"]], on="song", how="left"
        )
        predictions = predictions.rename(columns={"song": "song_name"})

        # 3. Ensure correct integer types for Supabase, handling potential NaNs
        predictions["current_gap"] = predictions["current_gap"].astype("Int64")
        predictions["times_played_last_year"] = predictions[
            "times_played_last_year"
        ].astype("Int64")

        # 4. Format date columns to MM/DD/YYYY text format
        predictions["prediction_date"] = pd.to_datetime(
            predictions["prediction_date"]
        ).dt.strftime("%m/%d/%Y")
        predictions["last_played_date"] = pd.to_datetime(
            predictions["last_played_date"]
        ).dt.strftime("%m/%d/%Y")

        # 5. Drop song_id before exporting
        if "song_id" in predictions.columns:
            predictions = predictions.drop(columns=["song_id"])

    logger.info("Notebook model generated %d predictions", len(predictions))

    return predictions
