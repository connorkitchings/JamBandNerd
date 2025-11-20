import sys
import os
import pandas as pd
from datetime import date, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from jambandnerd.db.connection import get_supabase_client
from jambandnerd.config import BAND_ID_COLUMNS


def check_band(band):
    print(f"\nChecking {band}...")
    client = get_supabase_client()
    cutoff = (date.today() - timedelta(days=7)).isoformat()
    id_col = BAND_ID_COLUMNS.get(band, "show_id")

    print(f"Fetching shows since {cutoff}...")
    shows_data = (
        client.table(f"{band}_shows_raw")
        .select("*")
        .gte("show_date", cutoff)
        .lte("show_date", date.today().isoformat())
        .execute()
        .data
    )

    shows = pd.DataFrame(shows_data) if shows_data else pd.DataFrame()

    if not shows.empty:
        show_ids = list(set(shows[id_col].astype(str)))
        print(f"Found {len(show_ids)} recent shows.")

        # Fetch only setlists for these specific shows to avoid row limits
        print(f"Fetching setlists for {len(show_ids)} shows...")
        setlists_data = (
            client.table(f"{band}_setlists_raw")
            .select(id_col)
            .in_(id_col, show_ids)
            .execute()
            .data
        )
        setlists = pd.DataFrame(setlists_data) if setlists_data else pd.DataFrame()

        setlist_ids = set(setlists[id_col].astype(str)) if not setlists.empty else set()
        missing = set(show_ids) - setlist_ids

        if missing:
            print(
                f"::warning::WARNING: {len(missing)} recent shows missing setlist data for {band}"
            )
            for show_id in list(missing)[:5]:
                show = shows[shows[id_col].astype(str) == show_id].iloc[0]
                print(f"  - {show.get('show_date', 'Unknown date')} (ID: {show_id})")
        else:
            print(f"✅ All recent shows have setlist data for {band}")
    else:
        print(f"ℹ️ No recent shows found for {band} in the last 7 days")


if __name__ == "__main__":
    bands = ["billy", "eggy", "goose", "phish", "um", "wsp"]
    for band in bands:
        try:
            check_band(band)
        except Exception as e:
            print(f"Error checking {band}: {e}")
