"""
Goose data export utilities for saving data to Supabase.
"""

from datetime import datetime
import time
from typing import List, Dict, Any

import pandas as pd
from postgrest import APIError

from jambandnerd.db.supabase_client import create_supabase_client

from .utils import get_logger

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


def save_goose_data_to_supabase(
    song_data: pd.DataFrame,
    show_data: pd.DataFrame,
    venue_data: pd.DataFrame,
    setlist_data: pd.DataFrame,
    transition_data: pd.DataFrame,
) -> bool:
    """
    Save Goose data to Supabase tables.

    Args:
        song_data (pd.DataFrame): DataFrame of song data.
        show_data (pd.DataFrame): DataFrame of show data.
        venue_data (pd.DataFrame): DataFrame of venue data.
        setlist_data (pd.DataFrame): DataFrame of setlist data.
        transition_data (pd.DataFrame): DataFrame of transition data.
        
    Returns:
        bool: True if all data was saved successfully, False otherwise.
    """
    logger.info("Starting Goose data save to Supabase...")
    
    supabase = create_supabase_client()
    
    # Define table configurations with proper primary keys
    table_configs = [
        ("goose_songs", song_data, "song_id"),
        ("goose_venues", venue_data, "venue_id"),
        ("goose_shows", show_data, "show_id"),
        ("goose_transitions", transition_data, "transition_id"),
        ("goose_setlists", setlist_data, "uniqueid"),
    ]
    
    all_successful = True
    
    for table_name, df, on_conflict_col in table_configs:
        if df.empty:
            logger.info("No data to save for table '%s'", table_name)
            continue
            
        logger.info("Processing table '%s': %d records", table_name, len(df))
        
        try:
            # Create a copy to avoid modifying the original DataFrame
            df_clean = df.copy()
            
            # Convert boolean columns to integers for setlist data (database expects 0/1, not true/false)
            if table_name == "goose_setlists":
                boolean_columns = ['isreprise', 'isjam', 'isjamchart', 'soundcheck']
                for col in boolean_columns:
                    if col in df_clean.columns:
                        df_clean[col] = df_clean[col].fillna(False).astype(bool).astype(int)
                        
            # Define all known date columns that must be stored as MM/DD/YYYY strings
            date_columns_map = {
                "goose_songs": ["debut_date"],
                "goose_shows": ["show_date"],
                "goose_venues": [],  # No date columns
                "goose_setlists": [],  # No date columns
                "goose_transitions": []  # No date columns
            }
            
            # Force all known date columns to be strings in MM/DD/YYYY format
            if table_name in date_columns_map:
                for col in date_columns_map[table_name]:
                    if col in df_clean.columns:
                        logger.info("Converting %s.%s to MM/DD/YYYY string format", table_name, col)
                        # Convert to datetime first if it's not already, then to MM/DD/YYYY string
                        df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce').dt.strftime('%m/%d/%Y')
                        # Explicitly set the column type to object (string) to prevent Supabase from inferring date type
                        df_clean[col] = df_clean[col].astype('object')
                        logger.info("Column %s.%s is now type: %s", table_name, col, df_clean[col].dtype)
            
            # Also handle any remaining datetime columns that weren't explicitly mapped
            for col in df_clean.select_dtypes(
                include=["datetime64[ns]", "datetime64[ns, UTC]"]
            ).columns:
                logger.warning("Found unmapped datetime column %s.%s, converting to MM/DD/YYYY string", table_name, col)
                df_clean[col] = df_clean[col].apply(
                    lambda x: x.strftime("%m/%d/%Y") if pd.notnull(x) else None
                )
                df_clean[col] = df_clean[col].astype('object')

            # Replace NaN values with None to ensure JSON serialization
            df_clean = df_clean.where(pd.notnull(df_clean), None)

            # Convert DataFrame to records for upsert
            records = df_clean.to_dict(orient="records")
            
            # Use chunked upsert with retry logic for better reliability
            success = chunked_upsert_with_retry(
                supabase=supabase,
                table_name=table_name,
                records=records,
                on_conflict_col=on_conflict_col,
                chunk_size=1000,  # Adjust based on table size and API limits
                max_retries=3
            )
            
            if success:
                logger.info("✅ Successfully upserted all data to '%s'", table_name)
            else:
                logger.error("❌ Failed to upsert some data to '%s'", table_name)
                all_successful = False
                continue  # Skip to next table
        except APIError as e:
            logger.error("Error saving data to '%s': %s", table_name, e)
            all_successful = False

    # Update pipeline metadata with retry logic
    try:
        logger.info("Updating pipeline metadata...")
        metadata = {
            "pipeline_name": "goose",
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
            logger.info("✅ Pipeline metadata updated successfully")
        else:
            logger.error("❌ Failed to update pipeline metadata")
            all_successful = False
            
    except Exception as e:
        logger.error("Unexpected error updating pipeline metadata: %s", e)
        all_successful = False

    return all_successful
