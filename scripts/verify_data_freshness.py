import sys
import os
import pandas as pd
from datetime import date, timedelta

# Add src to path if running from repo root
repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
sys.path.insert(0, os.path.join(repo_root, "src"))

try:
    from jambandnerd.db.connection import get_supabase_client
    from jambandnerd.config import BAND_ID_COLUMNS

    client = get_supabase_client()
except Exception as e:
    print(f"::error::Failed to initialize Supabase client: {e}")
    sys.exit(1)


def main():
    band = os.environ.get("BAND")
    if not band:
        print("::error::BAND environment variable not set")
        sys.exit(1)

    cutoff = (date.today() - timedelta(days=7)).isoformat()
    id_col = BAND_ID_COLUMNS.get(band, "show_id")

    print(f"Checking data freshness for {band} since {cutoff}")

    try:
        shows_data = (
            client.table(f"{band}_shows_raw")
            .select("*")
            .gte("show_date", cutoff)
            .lte("show_date", date.today().isoformat())
            .execute()
            .data
        )
        shows = pd.DataFrame(shows_data) if shows_data else pd.DataFrame()

        github_output = os.environ.get("GITHUB_OUTPUT")

        if not shows.empty:
            show_ids = list(set(shows[id_col].astype(str)))
            # Fetch only setlists for these specific shows to avoid row limits
            setlists_data = (
                client.table(f"{band}_setlists_raw")
                .select(id_col)
                .in_(id_col, show_ids)
                .execute()
                .data
            )
            setlists = pd.DataFrame(setlists_data) if setlists_data else pd.DataFrame()

            setlist_ids = (
                set(setlists[id_col].astype(str)) if not setlists.empty else set()
            )
            missing = set(show_ids) - setlist_ids

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
            print(f"ℹ️ No recent shows found for {band} in the last 7 days")
            if github_output:
                with open(github_output, "a") as f:
                    f.write("missing_data=false\n")
                    f.write("missing_count=0\n")

    except Exception as e:
        print(f"::error::Error checking data freshness: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
