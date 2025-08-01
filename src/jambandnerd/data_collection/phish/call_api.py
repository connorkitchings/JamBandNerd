"""
API helpers for Phish data collection. No config dependencies; loads API key from .env.
"""

import os
import time

import requests
from dotenv import load_dotenv
from requests.exceptions import ChunkedEncodingError, RequestException

from .utils import get_logger

# Ensure logs/Phish/ is always relative to the project root, not src/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
logs_dir = os.path.join(project_root, "logs", "Phish")
os.makedirs(logs_dir, exist_ok=True)
log_file = os.path.join(logs_dir, "phish_pipeline.log")
logger = get_logger(__name__, log_file=log_file, add_console_handler=True)


def get_api_key() -> str:
    """
    Load the PHISH_API_KEY from environment variables or the .env file.

    Checks for the PHISH_API_KEY in the environment variables first (for CI/CD),
    and falls back to loading from a .env file for local development.
    """
    api_key = os.getenv("PHISH_API_KEY")
    if api_key:
        return api_key

    # If not found in env, try loading from .env file for local dev
    load_dotenv()
    api_key = os.getenv("PHISH_API_KEY")
    if not api_key:
        error_message = "PHISH_API_KEY not found in environment variables or .env file."
        logger.error(error_message)
        raise RuntimeError(error_message)
    return api_key


def make_api_request(endpoint: str, api_key: str) -> dict:
    """Make a resilient API request to the Phish API with retry logic."""
    url = f"https://api.phish.net/v5/{endpoint}.json?apikey={api_key}"
    retries = 5
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            return response.json()
        except (ChunkedEncodingError, RequestException) as e:
            logger.warning(
                "API request failed on attempt %d/%d for endpoint '%s': %s",
                attempt + 1,
                retries,
                endpoint,
                e,
            )
            if attempt < retries - 1:
                time.sleep(3)  # Wait 3 seconds before retrying
            else:
                logger.error("API request failed after %d retries.", retries)
                raise  # Re-raise the last exception
    return {} # Should be unreachable
