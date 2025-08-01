"""
Centralized Supabase client for the JamBandNerd project.
"""

import os

from dotenv import load_dotenv
from supabase import Client, create_client

from jambandnerd.logging_utils import get_logger

logger = get_logger(__name__)


def create_supabase_client() -> Client:
    """
    Create and return a Supabase client using credentials from the .env file.

    Returns:
        Client: An initialized Supabase client.

    Raises:
        RuntimeError: If Supabase URL or key is not found in the environment.
    """
    # Prioritize existing environment variables (for CI/CD), fallback to .env for local dev
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.info("Supabase credentials not found in environment, checking .env file...")
        load_dotenv()
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Supabase credentials not found. Ensure SUPABASE_URL and SUPABASE_KEY are set "
            "in your environment or a .env file."
        )

    logger.info("Attempting to create Supabase client for URL: %s...", supabase_url[:20])

    return create_client(supabase_url, supabase_key)
