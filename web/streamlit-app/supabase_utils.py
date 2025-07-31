"""Supabase client and data fetching utilities."""

import os
from typing import Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client


@st.cache_resource
def get_supabase_client() -> Optional[Client]:
    """Create and return a Supabase client using credentials from the .env file."""
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        st.error("Supabase credentials not found. Please ensure SUPABASE_URL and SUPABASE_KEY are in your .env file.")
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Failed to create Supabase client. Please check your URL and Key. Error: {e}")
        return None


@st.cache_data(ttl=3600)  # Cache data for 1 hour
def get_table_as_dataframe(_client: Client, table_name: str) -> pd.DataFrame:
    """Fetch all records from a Supabase table and return as a pandas DataFrame."""
    if not _client:
        return pd.DataFrame()

    try:
        response = _client.table(table_name).select("*", count="exact").execute()
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data from table '{table_name}': {e}")
        return pd.DataFrame()
