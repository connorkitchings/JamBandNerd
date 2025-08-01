import pandas as pd
from supabase import Client

from jambandnerd.data_collection.wsp.utils import get_logger
from jambandnerd.db.supabase_client import create_supabase_client

logger = get_logger(__name__, add_console_handler=True)


def fetch_all_records(supabase: Client, table_name: str) -> pd.DataFrame:
    """
    Fetches all records from a Supabase table with pagination.

    Args:
        supabase: The Supabase client.
        table_name: The name of the table to fetch from.

    Returns:
        A DataFrame containing all records from the table.
    """
    all_data = []
    offset = 0
    page_size = 1000  # Default Supabase limit

    while True:
        try:
            start = offset
            end = offset + page_size - 1
            logger.info("Fetching page for %s with offset: %d", table_name, start)
            try:
                response = (
                    supabase.table(table_name)
                    .select("*", count="exact")
                    .range(start, end)
                    .execute()
                )
            except Exception as e:
                logger.error(
                    "Caught exception during fetch for table %s at offset %d: %s",
                    table_name,
                    start,
                    e,
                )
                break

            if not hasattr(response, "data"):
                logger.error("Error fetching data from %s: %s", table_name, response)
                break

            data = response.data
            logger.info(
                "Fetched page for %s with %d records (offset: %d).",
                table_name,
                len(data),
                offset,
            )
            all_data.extend(data)

            if len(data) < page_size:
                break  # Last page reached

            offset += page_size
        except Exception as e:
            logger.exception(
                "An exception occurred while fetching from %s: %s", table_name, e
            )
            break

    logger.info("Fetched a total of %d records from %s.", len(all_data), table_name)
    return pd.DataFrame(all_data)


def load_wsp_data() -> dict[str, pd.DataFrame]:
    """
    Loads all WSP data from Supabase tables using pagination.

    Returns:
        A dictionary containing DataFrames for songs, shows, and setlists.
    """
    supabase = create_supabase_client()
    logger.info("Loading WSP data from Supabase with pagination...")

    try:
        logger.info("Fetching WSP songs...")
        songs_df = fetch_all_records(supabase, "wsp_songs")
        logger.info("Finished fetching %d songs.", len(songs_df))

        logger.info("Fetching WSP shows...")
        shows_df = fetch_all_records(supabase, "wsp_shows")
        logger.info("Finished fetching %d shows.", len(shows_df))

        logger.info("Fetching WSP setlists...")
        setlists_df = fetch_all_records(supabase, "wsp_setlists")
        logger.info("Finished fetching %d setlist records.", len(setlists_df))

        logger.info("Finished fetching all data.")

        return {
            "songs": songs_df,
            "shows": shows_df,
            "setlists": setlists_df,
        }

    except Exception as e:
        logger.exception("Failed to load data from Supabase: %s", e)
        return {
            "songs": pd.DataFrame(),
            "shows": pd.DataFrame(),
            "setlists": pd.DataFrame(),
        }
