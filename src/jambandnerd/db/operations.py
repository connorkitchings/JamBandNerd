"""Provides high-level database operations."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

import pandas as pd

from .connection import get_supabase_client


def fetch_existing_ids(
    table_name: str, id_column: str, since: Optional[str] = None, date_column: str = "created_at"
) -> Set[Any]:
    """
    Fetches existing IDs from a table to prevent duplicate entries.

    Args:
        table_name: The name of the table to query.
        id_column: The name of the column containing the IDs.
        since: An optional date string to filter records.
        date_column: The name of the date column to filter on (defaults to 'created_at').

    Returns:
        A set of existing IDs.
    """
    client = get_supabase_client()
    query = client.table(table_name).select(id_column)
    if since:
        query = query.gte(date_column, since)

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

def get_table_schema(table_name: str) -> List[Dict[str, Any]]:
    """
    Fetch the schema for a given table from Supabase via RPC, if available.

    This expects a Postgres function (RPC) named `get_table_schema(p_table_name text)`
    that returns rows with at least: column_name, data_type, is_nullable.

    If the RPC is not present or fails, returns an empty list so callers can
    fall back to local expected schemas.

    Args:
        table_name: The name of the table whose schema to retrieve.

    Returns:
        A list of dictionaries describing columns, or an empty list on failure.
    """
    client = get_supabase_client()
    try:
        response = client.rpc("get_table_schema", {"p_table_name": table_name}).execute()
        return response.data or []
    except Exception:
        # RPC not available or other error; let validation layer use local expectations
        return []
