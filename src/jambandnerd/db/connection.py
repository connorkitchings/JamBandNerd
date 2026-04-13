"""Handles Supabase connection."""

import atexit
import os
from typing import Optional

from dotenv import load_dotenv
from httpx import Client as HttpxClient

from supabase import Client, ClientOptions, create_client

load_dotenv()

_supabase_client: Optional[Client] = None


def _build_client_options() -> ClientOptions:
    """Construct client options without deprecated PostgREST init parameters."""
    return ClientOptions(
        httpx_client=HttpxClient(
            timeout=ClientOptions().postgrest_client_timeout,
            follow_redirects=True,
            http2=True,
        )
    )


def _get_supabase_service_role_key() -> Optional[str]:
    """Return the preferred service-role credential, with legacy fallback."""
    return os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")


def close_supabase_client() -> None:
    """Close the singleton Supabase client and its shared HTTP resources."""
    global _supabase_client

    client = _supabase_client
    _supabase_client = None

    if client is None:
        return

    auth_client = getattr(client, "auth", None)
    if auth_client is not None and hasattr(auth_client, "close"):
        auth_client.close()

    httpx_client = getattr(client.options, "httpx_client", None)
    if httpx_client is not None:
        httpx_client.close()


def get_supabase_client() -> Client:
    """
    Initializes and returns a singleton Supabase client.

    Returns:
        Client: An initialized Supabase client.

    Raises:
        ValueError: If SUPABASE_URL or a service-role key are not set.
    """
    global _supabase_client
    if _supabase_client is None:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = _get_supabase_service_role_key()

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                "(or legacy SUPABASE_KEY) must be set in the environment."
            )

        _supabase_client = create_client(
            supabase_url,
            supabase_key,
            _build_client_options(),
        )

    return _supabase_client


def validate_environment() -> None:
    """
    Validates that necessary credentials are present.
    """
    has_url = bool(os.environ.get("SUPABASE_URL"))
    has_key = bool(_get_supabase_service_role_key())

    if not (has_url and has_key):
        raise ValueError(
            "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY "
            "(or legacy SUPABASE_KEY)."
        )


atexit.register(close_supabase_client)
