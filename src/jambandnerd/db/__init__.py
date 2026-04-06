"""Database package for Supabase connection and operations.

Provides comprehensive database connectivity, operations, and validation
for the JamBandNerd platform using Supabase as the backend.

Core components:
- connection: Singleton Supabase client with environment validation
- operations: High-level database operations (upsert, bulk insert, schema retrieval)
- validation: DataFrame validation against table schemas with type coercion
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import Client

    from .connection import get_supabase_client, validate_environment
    from .operations import (
        bulk_insert_dataframe,
        fetch_existing_ids,
        fetch_existing_values,
        fetch_historical_prediction_run,
        fetch_latest_prediction_songs,
        fetch_prediction_songs_for_date,
        fetch_rows_by_column_values,
        get_table_schema,
        prepare_dataframe_for_upsert,
        replace_prediction_projection,
        upsert_dataframe,
        upsert_historical_prediction_run,
        validate_and_upsert_dataframe,
    )
    from .validation import (
        TypeMismatch,
        ValidationReport,
        coerce_df_types,
        validate_dataframe_against_table,
    )

__all__ = [
    "Client",
    "get_supabase_client",
    "validate_environment",
    "fetch_existing_ids",
    "fetch_existing_values",
    "fetch_rows_by_column_values",
    "fetch_historical_prediction_run",
    "fetch_latest_prediction_songs",
    "fetch_prediction_songs_for_date",
    "bulk_insert_dataframe",
    "upsert_dataframe",
    "upsert_historical_prediction_run",
    "replace_prediction_projection",
    "prepare_dataframe_for_upsert",
    "validate_and_upsert_dataframe",
    "get_table_schema",
    "TypeMismatch",
    "ValidationReport",
    "coerce_df_types",
    "validate_dataframe_against_table",
    "connection",
    "operations",
    "validation",
]
