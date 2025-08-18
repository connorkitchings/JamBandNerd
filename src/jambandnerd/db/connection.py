"""Handles Supabase connection."""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_supabase_client() -> Client:
    """
    Initializes and returns a Supabase client.

    Validates that the required environment variables are set.

    Returns:
        Client: An initialized Supabase client.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set.
    """
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the environment.")

    return create_client(supabase_url, supabase_key)

def validate_environment() -> None:
    """
    Validates that necessary environment variables are present.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set.
    """
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"):
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY.")

