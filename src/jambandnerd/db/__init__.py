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
        get_table_schema,
        upsert_dataframe,
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
    "bulk_insert_dataframe",
    "upsert_dataframe",
    "get_table_schema",
    "TypeMismatch",
    "ValidationReport",
    "coerce_df_types",
    "validate_dataframe_against_table",
    "connection",
    "operations",
    "validation",
]
