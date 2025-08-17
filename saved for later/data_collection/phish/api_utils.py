"""
API utilities for Phish data collection, providing dependency-free functions for reuse.
"""

import logging
import os
import time

import requests
from dotenv import load_dotenv
from requests.exceptions import ChunkedEncodingError, RequestException


def get_api_key(logger: logging.Logger) -> str:
    """
    Load the PHISH_API_KEY from environment variables or the .env file.

    Checks for the PHISH_API_KEY in the environment variables first (for CI/CD),
    and falls back to loading from a .env file for local development.
    """
    api_key = os.getenv("PHISH_API_KEY")
    if api_key:
        return api_key

    # load_dotenv() returns True if it found and loaded a .env file
    dotenv_found = load_dotenv()
    if not dotenv_found:
        logger.warning("No .env file found. Relying solely on environment variables.")

    api_key = os.getenv("PHISH_API_KEY")
    if not api_key:
        error_message = (
            "PHISH_API_KEY not found. Please ensure it is set in your environment variables "
            "or in a .env file in the project root."
        )
        logger.error(error_message)
        raise RuntimeError(error_message)
    return api_key


def make_api_request(endpoint: str, api_key: str, logger: logging.Logger) -> dict:
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
                time.sleep(3)
            else:
                logger.error("API request failed after %d retries.", retries)
                raise
    return {}
