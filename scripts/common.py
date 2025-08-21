"""Common utility functions for pipeline scripts."""
from __future__ import annotations

import sys
from datetime import date, datetime

import pandas as pd
from typing import List, Dict

# Local imports
from src.jambandnerd.db.connection import get_supabase_client


def resolve_reference_date(
    date_str: str | None, shows_df: pd.DataFrame
) -> date:
    """
    Resolves the reference date for predictions.

    - If a specific date is provided, it is used directly.
    - If no date is provided or if the provided date is today, the function
      finds the date of the next upcoming show in the dataset.
    """
    today = date.today()
    target_date = today
    is_today = True

    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if target_date != today:
                is_today = False
        except ValueError:
            print(f"Error: Invalid date format '{date_str}'. Please use YYYY-MM-DD.")
            sys.exit(1)

    if is_today:
        shows_df["_show_date_dt"] = pd.to_datetime(shows_df["show_date"]).dt.date
        future_shows = shows_df[shows_df["_show_date_dt"] >= today].copy()
        
        if future_shows.empty:
            print("Error: No future shows found in the database to use as a reference.")
            sys.exit(1)
        
        next_show_date = future_shows["_show_date_dt"].min()
        print(f"No specific date provided; defaulting to next upcoming show: {next_show_date.isoformat()}")
        return next_show_date
    else:
        # If a specific historical date is given, use it
        print(f"Using specified historical date: {target_date.isoformat()}")
        return target_date


def fetch_table(table_name: str) -> List[Dict]:
    """Fetch all rows from a Supabase table.

    Args:
        table_name: The name of the table to fetch.

    Returns:
        A list of row dictionaries. Returns an empty list if no rows are found.
    """
    client = get_supabase_client()
    response = client.table(table_name).select("*").execute()
    return response.data or []


# Backward compatibility alias for callers using the old private name
_fetch_table = fetch_table