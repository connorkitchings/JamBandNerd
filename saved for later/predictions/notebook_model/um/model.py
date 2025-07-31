import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timedelta

import pandas as pd
from logger import get_logger

logger = get_logger(__name__)


def aggregate_setlist_features(df, target_show_date):
    """
    Aggregates setlist data by song for a 1-year window before (not including) the target_show_date.
    Excludes songs played in the last 3 shows and sorts by times_played_last_year descending.
    Args:
        df (pd.DataFrame): Setlist data with 'song', 'show_date'
        target_show_date (str or datetime): Target show date (YYYY-MM-DD or datetime)
    Returns:
        pd.DataFrame: Aggregated features per song (by name)
    """
    if isinstance(target_show_date, str):
        try:
            target_show_date = datetime.strptime(target_show_date, "%Y-%m-%d")
        except ValueError:
            try:
                target_show_date = datetime.strptime(target_show_date, "%m-%d-%Y")
            except ValueError:
                raise ValueError(
                    f"target_show_date '{target_show_date}' does not match '%Y-%m-%d' or '%m-%d-%Y'"
                )
    window_start = target_show_date - timedelta(days=365)
    mask = (df["show_date"] >= window_start) & (df["show_date"] < target_show_date)
    df_in_window = df[mask].copy()
    # Exclude songs played in the last 3 shows (by show_date), only considering shows before the target_show_date
    showdata = df[["show_date"]].drop_duplicates()
    showdata = showdata[showdata["show_date"] < target_show_date]
    showdata = showdata.sort_values("show_date", ascending=False)
    last_3_shows = showdata.head(3)["show_date"].tolist()
    song_groups = df_in_window.groupby("song").agg({"show_date": list})
    results = []
    for song, row in song_groups.iterrows():
        times_played = len(row["show_date"])
        play_dates_sorted = sorted(row["show_date"])
        last_time_played_date = play_dates_sorted[-1] if times_played > 0 else None
        gaps = [j - i for i, j in zip(play_dates_sorted[:-1], play_dates_sorted[1:])]
        average_gap = (
            round(sum(gaps, timedelta(0)).days / len(gaps), 3) if gaps else None
        )
        median_gap = (
            round(pd.Series([g.days for g in gaps]).median(), 2) if gaps else None
        )
        results.append(
            {
                "song": song,
                "times_played_last_year": times_played,
                "last_time_played": last_time_played_date,
                "average_gap_days": average_gap,
                "median_gap_days": median_gap,
            }
        )
    agg_df = pd.DataFrame(results)
    # Exclude songs played in the last 3 shows
    recent_songs = df[df["show_date"].isin(last_3_shows)]["song"].unique()
    agg_df = agg_df[~agg_df["song"].isin(recent_songs)].copy()
    agg_df = agg_df.sort_values("times_played_last_year", ascending=False)
    return agg_df
