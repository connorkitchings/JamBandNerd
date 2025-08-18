"""Abstract base classes for data collection."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import date

class BandCollector(ABC):
    """Abstract base class for band-specific data collectors."""

    @abstractmethod
    def collect_shows(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Collect show data for a given date range."""
        pass

    @abstractmethod
    def collect_setlists(self, show_ids: List[str]) -> List[Dict[str, Any]]:
        """Collect setlist data for a list of show IDs."""
        pass

    @abstractmethod
    def collect_songs(self) -> List[Dict[str, Any]]:
        """Collect the entire song catalog for the band."""
        pass
