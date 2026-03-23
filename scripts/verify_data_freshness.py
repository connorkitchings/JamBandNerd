import os
import sys

import pandas as pd

# Add src to path if running from repo root
repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
sys.path.insert(0, repo_root)
sys.path.insert(0, os.path.join(repo_root, "src"))

try:
    from jambandnerd.config import BAND_ID_COLUMNS
    from jambandnerd.db.connection import get_supabase_client
except Exception as e:
    print(f"::error::Failed to import pipeline modules: {e}")
    raise SystemExit(1) from e

from scripts.common import (
    completed_show_window,
    fetch_column_values_for_ids,
    fetch_table_rows,
)

_completed_show_window = completed_show_window


def main():
    band = os.environ.get("BAND")
    if not band:
        print("::error::BAND environment variable not set")
        sys.exit(1)

    cutoff, end_date = completed_show_window()
    id_col = BAND_ID_COLUMNS.get(band, "show_id")

    print(
        f"Checking data freshness for {band} from {cutoff} through {end_date} (completed shows only)"
    )

    try:
        client = get_supabase_client()
        shows_data = fetch_table_rows(
            f"{band}_shows_raw",
            filters=[("gte", "show_date", cutoff), ("lte", "show_date", end_date)],
            client=client,
        )
        shows = pd.DataFrame(shows_data) if shows_data else pd.DataFrame()

        github_output = os.environ.get("GITHUB_OUTPUT")

        if not shows.empty:
            show_ids_raw = [show_id for show_id in shows[id_col].dropna().tolist()]
            show_ids = {str(show_id) for show_id in show_ids_raw}
            setlist_ids = fetch_column_values_for_ids(
                f"{band}_setlists_raw",
                id_column=id_col,
                ids=show_ids_raw,
                client=client,
            )
            missing = show_ids - setlist_ids

            if missing:
                print(
                    f"::warning::WARNING: {len(missing)} recent shows missing setlist data for {band}"
                )
                print(f"WARNING: {len(missing)} recent shows missing setlist data")
                for show_id in list(missing)[:5]:
                    show = shows[shows[id_col].astype(str) == show_id].iloc[0]
                    print(
                        f"  - {show.get('show_date', 'Unknown date')} (ID: {show_id})"
                    )

                if github_output:
                    with open(github_output, "a") as f:
                        f.write("missing_data=true\n")
                        f.write(f"missing_count={len(missing)}\n")
            else:
                print(f"✅ All recent shows have setlist data for {band}")
                if github_output:
                    with open(github_output, "a") as f:
                        f.write("missing_data=false\n")
                        f.write("missing_count=0\n")
        else:
            print(f"ℹ️ No recent completed shows found for {band} in the last 7 days")
            if github_output:
                with open(github_output, "a") as f:
                    f.write("missing_data=false\n")
                    f.write("missing_count=0\n")

    except Exception as e:
        print(f"::error::Error checking data freshness: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
