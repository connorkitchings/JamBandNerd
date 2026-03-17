"""Handles Supabase connection."""

import os
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

# Safe optional import for Streamlit secrets
try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore

load_dotenv()

_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Initializes and returns a singleton Supabase client.

    Prefers Streamlit secrets when available, with environment variable fallback.

    Returns:
        Client: An initialized Supabase client.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY are not set.
    """
    global _supabase_client
    if _supabase_client is None:
        supabase_url: Optional[str] = None
        supabase_key: Optional[str] = None

        # Prefer Streamlit secrets when running in a Streamlit environment
        try:
            if st is not None and hasattr(st, "secrets"):
                supabase_url = st.secrets.get("SUPABASE_URL")  # type: ignore[attr-defined]
                supabase_key = st.secrets.get("SUPABASE_KEY")  # type: ignore[attr-defined]
        except Exception:
            # If accessing st.secrets fails, fall back to env vars
            pass

        # Fallback to environment variables
        supabase_url = supabase_url or os.environ.get("SUPABASE_URL")
        supabase_key = supabase_key or os.environ.get("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY must be set in Streamlit secrets or the environment."
            )

        _supabase_client = create_client(supabase_url, supabase_key)

    return _supabase_client


def validate_environment() -> None:
    """
    Validates that necessary credentials are present (Streamlit secrets or env).
    """
    has_url = False
    has_key = False

    try:
        if st is not None and hasattr(st, "secrets"):
            has_url = bool(st.secrets.get("SUPABASE_URL"))  # type: ignore[attr-defined]
            has_key = bool(st.secrets.get("SUPABASE_KEY"))  # type: ignore[attr-defined]
    except Exception:
        pass

    has_url = has_url or bool(os.environ.get("SUPABASE_URL"))
    has_key = has_key or bool(os.environ.get("SUPABASE_KEY"))

    if not (has_url and has_key):
        raise ValueError(
            "Missing SUPABASE_URL or SUPABASE_KEY (in Streamlit secrets or environment)."
        )
