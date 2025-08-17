"""
API utility for Goose data collection.
"""

import requests


def make_api_request(endpoint: str, version: str = "v2") -> dict:
    """
    Make an API request to the Goose API.

    Args:
        endpoint (str): API endpoint to call (e.g., 'songs', 'shows').
        version (str): API version ('v1' or 'v2'). Defaults to 'v2'.
    Returns:
        dict: Parsed JSON response from the API.
    """
    url_templates = {
        "v1": "https://elgoose.net/api/v1/{}.json?",
        "v2": "https://elgoose.net/api/v2/{}.json?",
    }
    url = url_templates.get(version, "").format(endpoint)
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
