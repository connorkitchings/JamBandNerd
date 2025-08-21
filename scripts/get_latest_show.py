import os
import sys
import pandas as pd

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.jambandnerd.db.connection import get_supabase_client

def main():
    client = get_supabase_client()
    resp = client.table("goose_shows_raw").select("show_date").order("show_date", desc=True).limit(1).execute()
    if resp.data:
        latest_date = resp.data[0]['show_date']
        print(f"LATEST_SHOW_DATE={latest_date}")
    else:
        print("Could not retrieve latest show date.")

if __name__ == "__main__":
    main()
