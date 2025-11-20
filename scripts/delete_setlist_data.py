
import argparse
import os
import sys
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client


def delete_setlist_data(band: str, date_str: str):
    """
    Deletes setlist data for a specific band and date from the corresponding raw table.

    Args:
        band: The band to delete data for (e.g., "goose", "phish", "wsp").
        date_str: The date to delete data for in YYYY-MM-DD format.
    """
    try:
        # Validate date format
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print("Error: Invalid date format. Please use YYYY-MM-DD.")
        return

    client = get_supabase_client()
    table_name = f"{band}_setlists_raw"

    print(f"Deleting data from {table_name} for date: {date_str}...")

    shows_table_name = f"{band}_shows_raw"
    shows_response = client.table(shows_table_name).select("show_id").eq("show_date", date_str).execute()

    if not shows_response.data:
        print(f"No shows found for {band} on {date_str}.")
        return

    show_ids = [show["show_id"] for show in shows_response.data]

    if not show_ids:
        print(f"No show_ids found for {band} on {date_str}.")
        return

    print(f"Found {len(show_ids)} show(s) for {band} on {date_str}.")

    # Delete from setlists table
    setlists_delete_response = client.table(table_name).delete().in_("show_id", show_ids).execute()

    if len(setlists_delete_response.data) > 0:
        print(f"Successfully deleted {len(setlists_delete_response.data)} rows from {table_name}.")
    else:
        print(f"No data to delete in {table_name} for shows on {date_str}.")

    # Also delete the show from the shows table
    shows_delete_response = client.table(shows_table_name).delete().in_("show_id", show_ids).execute()

    if len(shows_delete_response.data) > 0:
        print(f"Successfully deleted {len(shows_delete_response.data)} rows from {shows_table_name}.")
    else:
        print(f"No data to delete in {shows_table_name} for date {date_str}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete setlist data for a specific band and date.")
    parser.add_argument("--band", required=True, help="The band to delete data for (e.g., 'goose', 'phish', 'wsp').")
    parser.add_argument("--date", required=True, help="The date to delete data for in YYYY-MM-DD format.")
    args = parser.parse_args()

    delete_setlist_data(args.band, args.date)
