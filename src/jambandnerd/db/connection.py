"""Handles Supabase connection."""
import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """
    Initializes and returns a singleton Supabase client.

    Validates that the required environment variables are set on first call.

    Returns:
        Client: An initialized Supabase client.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set.
    """
    global _supabase_client
    if _supabase_client is None:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in the environment.")

        _supabase_client = create_client(supabase_url, supabase_key)
    
    return _supabase_client

def validate_environment() -> None:
    """
    Validates that necessary environment variables are present.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set.
    """
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"):
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY.")