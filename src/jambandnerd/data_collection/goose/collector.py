"""Data collector for Goose from elgoose.net API."""
import requests
from typing import List, Dict, Any
from datetime import date

from ..base import BandCollector

class GooseCollector(BandCollector):
    """Collects Goose data from the elgoose.net API."""

    BASE_URL = "https://elgoose.net/api"

    def collect_shows(self, start_date: date = None, end_date: date = None) -> List[Dict[str, Any]]:
        """Collects show data from the elgoose.net API."""
        print("Collecting Goose shows...")
        response = requests.get(f"{self.BASE_URL}/v2/shows.json")
        response.raise_for_status()
        data = response.json()
        if data.get('error'):
            raise RuntimeError(f"API Error: {data.get('error_message', 'Unknown error')}")
        return data.get('data', [])

    def collect_setlists(self, show_ids: List[str] = None) -> List[Dict[str, Any]]:
        """Collects setlist data from the elgoose.net API."""
        print("Collecting Goose setlists...")
        response = requests.get(f"{self.BASE_URL}/v1/setlists.json")
        response.raise_for_status()
        data = response.json()
        if data.get('error'):
            raise RuntimeError(f"API Error: {data.get('error_message', 'Unknown error')}")
        return data.get('data', [])

    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collects song data from the elgoose.net API."""
        print("Collecting Goose songs...")
        response = requests.get(f"{self.BASE_URL}/v2/songs.json")
        response.raise_for_status()
        data = response.json()
        if data.get('error'):
            raise RuntimeError(f"API Error: {data.get('error_message', 'Unknown error')}")
        return data.get('data', [])
