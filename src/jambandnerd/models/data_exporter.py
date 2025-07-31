"""
Band-agnostic data export utilities for saving raw data to Supabase.
This module contains the chunked upsert logic that can be used by any band's data collection pipeline.
"""

from datetime import datetime
import time
from typing import List, Dict, Any

import pandas as pd
from postgrest import APIError

from jambandnerd.db.supabase_client import create_supabase_client
from jambandnerd.logging_utils import get_logger

logger = get_logger(__name__)


def chunked_upsert_with_retry(
    supabase, 
    table_name: str, 
    records: List[Dict[Any, Any]], 
    on_conflict_col: str, 
    chunk_size: int = 1000,
    max_retries: int = 3,
    retry_delay: float = 1.0
) -> bool:
    """
    Perform chunked upsert operations with retry logic for better reliability.
    
    Args:
        supabase: Supabase client instance
        table_name: Name of the table to upsert to
        records: List of records to upsert
        on_conflict_col: Column name for conflict resolution
        chunk_size: Number of records per chunk (default 1000)
        max_retries: Maximum number of retry attempts (default 3)
        retry_delay: Delay between retries in seconds (default 1.0)
        
    Returns:
        bool: True if all chunks were successfully upserted, False otherwise
    """
    if not records:
        logger.info("No records to upsert for table '%s'", table_name)
        return True
        
    total_records = len(records)
    chunks = [records[i:i + chunk_size] for i in range(0, total_records, chunk_size)]
    
    logger.info("Upserting %d records to '%s' in %d chunks of %d records each", 
                total_records, table_name, len(chunks), chunk_size)
    
    successful_chunks = 0
    
    for chunk_idx, chunk in enumerate(chunks, 1):
        for attempt in range(max_retries):
            try:
                logger.debug("Upserting chunk %d/%d (attempt %d/%d): %d records", 
                           chunk_idx, len(chunks), attempt + 1, max_retries, len(chunk))
                
                supabase.table(table_name).upsert(
                    chunk, on_conflict=on_conflict_col
                ).execute()
                
                successful_chunks += 1
                logger.debug("✅ Chunk %d/%d completed successfully", chunk_idx, len(chunks))
                break  # Success, move to next chunk
                
            except APIError as e:
                error_code = getattr(e, 'code', 'UNKNOWN')
                error_message = str(e)
                
                if attempt < max_retries - 1:
                    logger.warning("Chunk %d/%d failed (attempt %d/%d), retrying in %.1fs: %s", 
                                 chunk_idx, len(chunks), attempt + 1, max_retries, 
                                 retry_delay, error_message[:100])
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                else:
                    logger.error("Chunk %d/%d failed after %d attempts: %s (Code: %s)", 
                               chunk_idx, len(chunks), max_retries, error_message, error_code)
                    return False
                    
            except Exception as e:
                logger.error("Unexpected error in chunk %d/%d: %s", chunk_idx, len(chunks), e)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 1.5
                else:
                    return False
    
    logger.info("✅ Successfully upserted %d/%d chunks to '%s'", 
                successful_chunks, len(chunks), table_name)
    return successful_chunks == len(chunks)


def prepare_dataframe_for_supabase(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    """
    Prepare a DataFrame for Supabase storage with proper data type conversions.
    
    Args:
        df: DataFrame to prepare
        table_name: Name of the target table (used for band-specific date column mapping)
        
    Returns:
        pd.DataFrame: Prepared DataFrame ready for Supabase storage
    """
    df = df.copy()
    
    # Handle boolean columns - convert to integers for Supabase compatibility
    boolean_columns = ["is_jam", "is_segue", "is_encore", "is_soundcheck", "is_guest"]
    for col in boolean_columns:
        if col in df.columns:
            # Handle NaN values and convert booleans to integers
            df[col] = df[col].fillna(False).astype(bool).astype(int)
            
    # Define date columns that must be stored as MM/DD/YYYY strings
    # This mapping can be extended for other bands
    date_columns_map = {
        "wsp_songs": ["first_played", "last_played"],
        "phish_shows": ["showdate"],
        "phish_venues": [],
        "phish_setlists": [],
        "phish_transitions": [],
        "goose_songs": ["debut_date"],
        "goose_shows": ["showdate"],
        "goose_venues": [],
        "goose_setlists": [],
        "goose_transitions": []
    }
    
    # Force all known date columns to be strings in MM/DD/YYYY format
    if table_name in date_columns_map:
        for col in date_columns_map[table_name]:
            if col in df.columns:
                logger.info("Converting %s.%s to MM/DD/YYYY string format", table_name, col)
                # Convert to datetime first if it's not already, then to MM/DD/YYYY string
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%m/%d/%Y')
                # Explicitly set the column type to object (string) to prevent Supabase from inferring date type
                df[col] = df[col].astype('object')
                logger.info("Column %s.%s is now type: %s", table_name, col, df[col].dtype)
    
    # Also handle any remaining datetime columns that weren't explicitly mapped
    for col in df.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        logger.warning("Found unmapped datetime column %s.%s, converting to MM/DD/YYYY string", table_name, col)
        df[col] = df[col].apply(
            lambda x: x.strftime("%m/%d/%Y") if pd.notnull(x) else None
        )
        df[col] = df[col].astype('object')

    # Convert numeric columns to nullable integers to handle NaNs
    for col in df.select_dtypes(include=['number']).columns:
        df[col] = df[col].astype('Int64')

    # Replace NaN values with None to ensure JSON serialization
    df = df.where(pd.notnull(df), None)
    
    return df


def export_dataframe_to_supabase(
    df: pd.DataFrame, 
    table_name: str, 
    on_conflict_col: str, 
    logger
) -> bool:
    """
    Prepare and export a DataFrame to a Supabase table with chunked upsert.

    Args:
        df: DataFrame to export
        table_name: Name of the target Supabase table
        on_conflict_col: Column name for conflict resolution
        logger: Logger instance for logging

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        supabase = create_supabase_client()
        logger.info("Preparing DataFrame for Supabase table '%s'...", table_name)
        
        prepared_df = prepare_dataframe_for_supabase(df, table_name)
        records = prepared_df.to_dict(orient='records')
        
        logger.info("Exporting %d records to '%s'...", len(records), table_name)
        
        success = chunked_upsert_with_retry(
            supabase=supabase,
            table_name=table_name,
            records=records,
            on_conflict_col=on_conflict_col
        )
        
        if success:
            logger.info("✅ Successfully exported data to '%s'", table_name)
        else:
            logger.error("❌ Failed to export data to '%s'", table_name)
            
        return success
        
    except Exception as e:
        logger.error("Unexpected error exporting DataFrame to '%s': %s", table_name, e)
        return False

def update_pipeline_metadata(pipeline_name: str) -> bool:
    """
    Update pipeline metadata in Supabase to track last run time.
    
    Args:
        pipeline_name: Name of the pipeline (e.g., "phish", "goose")
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        supabase = create_supabase_client()
        logger.info("Updating pipeline metadata for '%s'...", pipeline_name)
        
        metadata = {
            "pipeline_name": pipeline_name,
            "last_updated": datetime.now().isoformat(),
        }
        
        # Use chunked upsert for consistency (even though it's just one record)
        success = chunked_upsert_with_retry(
            supabase=supabase,
            table_name="pipeline_metadata",
            records=[metadata],
            on_conflict_col="pipeline_name",
            chunk_size=1,
            max_retries=3
        )
        
        if success:
            logger.info("✅ Pipeline metadata updated successfully for '%s'", pipeline_name)
        else:
            logger.error("❌ Failed to update pipeline metadata for '%s'", pipeline_name)
            
        return success
        
    except Exception as e:
        logger.error("Unexpected error updating pipeline metadata for '%s': %s", pipeline_name, e)
        return False
