#!/usr/bin/env python3
"""
Quick script to view WSP predictions from the unified Supabase tables.
"""

import os
import pandas as pd
from dotenv import load_dotenv
from supabase import Client, create_client

# Load environment variables
load_dotenv()

def get_supabase_client() -> Client:
    """Initialize Supabase client."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase URL and Key must be set in environment variables.")
    return create_client(supabase_url, supabase_key)

def main():
    """View WSP predictions from both models."""
    supabase = get_supabase_client()
    
    print("=== WSP CK+ Model Predictions ===")
    try:
        ckplus_response = supabase.table("predictions_ckplus").select("*").eq("band", "wsp").order("ckplus_score", desc=True).limit(10).execute()
        if ckplus_response.data:
            df_ckplus = pd.DataFrame(ckplus_response.data)
            print(f"Found {len(ckplus_response.data)} CK+ predictions for WSP")
            print("\nTop 10 CK+ predictions:")
            for _, row in df_ckplus.head(10).iterrows():
                print(f"  {row['song_name']}: CK+ Score {row['ckplus_score']:.1f}, Gap {row['current_gap']} shows")
        else:
            print("No CK+ predictions found for WSP")
    except Exception as e:
        print(f"Error fetching CK+ predictions: {e}")
    
    print("\n=== WSP Notebook Model Predictions ===")
    try:
        notebook_response = supabase.table("predictions_notebook").select("*").eq("band", "wsp").order("times_played_last_year", desc=True).limit(10).execute()
        if notebook_response.data:
            df_notebook = pd.DataFrame(notebook_response.data)
            print(f"Found {len(notebook_response.data)} Notebook predictions for WSP")
            print("\nTop 10 Notebook predictions (by recent frequency):")
            for _, row in df_notebook.head(10).iterrows():
                print(f"  {row['song_name']}: {row['times_played_last_year']} times last year, Gap {row['current_gap']} shows")
        else:
            print("No Notebook predictions found for WSP")
    except Exception as e:
        print(f"Error fetching Notebook predictions: {e}")

if __name__ == "__main__":
    main()
