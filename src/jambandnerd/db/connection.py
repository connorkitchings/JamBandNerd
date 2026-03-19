"""Handles Supabase connection."""

import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Initializes and returns a singleton Supabase client.

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
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in the environment."
            )

        _supabase_client = create_client(supabase_url, supabase_key)

    return _supabase_client


def validate_environment() -> None:
    """
    Validates that necessary credentials are present.
    """
    has_url = bool(os.environ.get("SUPABASE_URL"))
    has_key = bool(os.environ.get("SUPABASE_KEY"))

    if not (has_url and has_key):
        raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY.")
