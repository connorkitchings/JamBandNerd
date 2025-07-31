from typing import Optional

import pandas as pd
from postgrest import APIError
from supabase import Client

from jambandnerd.db.supabase_client import create_supabase_client
from jambandnerd.logging_utils import get_logger

logger = get_logger(__name__)


def get_table_as_dataframe(table_name: str, client: Optional[Client] = None) -> pd.DataFrame:
    """
    Fetches all records from a Supabase table using pagination and returns them
    as a single pandas DataFrame.

    Args:
        table_name: The name of the table to fetch.
        client: An optional existing Supabase client. If not provided, a new one
                will be created.

    Returns:
        A pandas DataFrame containing all table data, or an empty DataFrame
        if the table is empty or an error occurs.
    """
    logger.info("Attempting to fetch all data from table: '%s'", table_name)
    try:
        if client is None:
            client = create_supabase_client()

        # First, get the total count of records
        count_response = client.table(table_name).select("*", count="exact", head=True).execute()
        total_records = count_response.count

        if total_records == 0:
            logger.warning("No data found in table '%s'. Returning empty DataFrame.", table_name)
            return pd.DataFrame()

        logger.info("Found %d total records in '%s'. Fetching in chunks...", total_records, table_name)

        all_data = []
        chunk_size = 1000  # Supabase's default/max limit per request

        for i in range(0, total_records, chunk_size):
            logger.debug("Fetching records %d to %d...", i, i + chunk_size - 1)
            response = client.table(table_name).select("*").range(i, i + chunk_size - 1).execute()
            all_data.extend(response.data)

        df = pd.DataFrame(all_data)
        logger.info("Successfully loaded all %d records from '%s' into a DataFrame.", len(df), table_name)
        return df

    except APIError as e:
        logger.error("APIError fetching data from '%s': %s", table_name, e)
        return pd.DataFrame()
    except Exception as e:
        logger.error("An unexpected error occurred while fetching data from '%s': %s", table_name, e)
        return pd.DataFrame()
