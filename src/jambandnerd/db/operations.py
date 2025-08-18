"""Provides high-level database operations."""
from typing import Optional, Set, List, Dict, Any
import pandas as pd
from supabase import Client
from .connection import get_supabase_client

def fetch_existing_ids(table_name: str, id_column: str, since: Optional[str] = None) -> Set[Any]:
    """
    Fetches existing IDs from a table to prevent duplicate entries.

    Args:
        table_name: The name of the table to query.
        id_column: The name of the column containing the IDs.
        since: An optional date string to filter records.

    Returns:
        A set of existing IDs.
    """
    client = get_supabase_client()
    query = client.table(table_name).select(id_column)
    if since:
        # Assuming a 'created_at' column for filtering
        query = query.gte('created_at', since)
    
    response = query.execute()
    
    if response.data:
        return {item[id_column] for item in response.data}
    return set()

def bulk_insert_dataframe(table_name: str, df: pd.DataFrame, chunk_size: int = 500) -> None:
    """
    Inserts a DataFrame into a Supabase table in chunks.

    Args:
        table_name: The name of the table to insert into.
        df: The DataFrame to insert.
        chunk_size: The number of rows to insert per chunk.
    """
    client = get_supabase_client()
    records = df.to_dict(orient='records')
    
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        client.table(table_name).insert(chunk).execute()

def upsert_dataframe(table_name: str, df: pd.DataFrame, conflict_columns: List[str], chunk_size: int = 500) -> None:
    """
    Upserts a DataFrame into a Supabase table in chunks.

    Args:
        table_name: The name of the table to upsert into.
        df: The DataFrame to upsert.
        conflict_columns: A list of column names to use for conflict resolution.
        chunk_size: The number of rows to upsert per chunk.
    """
    client = get_supabase_client()
    records = df.to_dict(orient='records')

    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        client.table(table_name).upsert(chunk, on_conflict=','.join(conflict_columns)).execute()
