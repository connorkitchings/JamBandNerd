"""
Database-based cache utilities for WSP data ingestion optimization.

Manages timestamps and metadata in Supabase to minimize unnecessary scraping operations.
This replaces the file-based caching system to avoid storing cache files in the repository.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from postgrest import APIError

from jambandnerd.db.supabase_client import create_supabase_client


class WSPDatabaseCache:
    """Database-based caching for WSP pipeline using Supabase pipeline_metadata table."""

    def __init__(self, logger: logging.Logger):
        self.supabase_client = create_supabase_client()
        self.pipeline_name = "wsp"
        self.logger = logger

    def get_cache_metadata(self) -> Optional[dict[str, Any]]:
        """
        Get the current cache metadata from the database.

        Returns:
            Dictionary containing cache metadata, or None if no cache exists
        """
        try:
            response = (
                self.supabase_client.table("pipeline_metadata")
                .select("metadata")
                .eq("pipeline_name", self.pipeline_name)
                .execute()
            )

            if response.data and len(response.data) > 0:
                metadata = response.data[0].get("metadata", {})
                return metadata.get("cache", {}) if metadata else {}

            self.logger.info("No cache metadata found for WSP pipeline")
            return None
        except APIError as e:
            if e.code == "42703":  # Column does not exist
                self.logger.warning(
                    "The 'metadata' column does not exist in 'pipeline_metadata' table. "
                    "Please consider running the schema migration. Returning no cache."
                )
                return None
            self.logger.warning("APIError reading cache metadata from database: %s", e)
            return None
        except Exception as e:
            self.logger.warning("Unexpected error reading cache metadata from database: %s", e)
            return None

    def get_last_scrape_timestamp(self, cache_type: str) -> Optional[datetime]:
        """
        Get the last scrape timestamp for a specific cache type (shows/songs).

        Args:
            cache_type: Type of cache ('shows' or 'songs')

        Returns:
            datetime of last scrape, or None if no cache exists
        """
        cache_metadata = self.get_cache_metadata()
        if not cache_metadata or cache_type not in cache_metadata:
            return None

        timestamp_str = cache_metadata[cache_type].get("last_scraped")
        if timestamp_str:
            try:
                return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError as e:
                self.logger.warning("Invalid timestamp format in cache: %s", e)
                return None

        return None

    def should_scrape_shows(
        self, force_scrape: bool = False, max_age_days: int = 7
    ) -> bool:
        """
        Determine if shows should be scraped based on cache age.

        Args:
            force_scrape: If True, always scrape regardless of cache
            max_age_days: Maximum age in days before re-scraping

        Returns:
            True if shows should be scraped
        """
        if force_scrape:
            self.logger.info("Force scrape enabled for shows")
            return True

        last_scraped = self.get_last_scrape_timestamp("shows")
        if last_scraped is None:
            self.logger.info("No shows cache found, scraping required")
            return True

        age = datetime.now(last_scraped.tzinfo) - last_scraped
        should_scrape = age.days >= max_age_days

        self.logger.info(
            "Shows last scraped %d days ago. Should scrape: %s", age.days, should_scrape
        )
        return should_scrape

    def should_scrape_songs(
        self, force_scrape: bool = False, max_age_days: int = 7
    ) -> bool:
        """
        Determine if songs should be scraped based on cache age.

        Args:
            force_scrape: If True, always scrape regardless of cache
            max_age_days: Maximum age in days before re-scraping

        Returns:
            True if songs should be scraped
        """
        if force_scrape:
            self.logger.info("Force scrape enabled for songs")
            return True

        last_scraped = self.get_last_scrape_timestamp("songs")
        if last_scraped is None:
            self.logger.info("No songs cache found, scraping required")
            return True

        age = datetime.now(last_scraped.tzinfo) - last_scraped
        should_scrape = age.days >= max_age_days

        self.logger.info(
            "Songs last scraped %d days ago. Should scrape: %s", age.days, should_scrape
        )
        return should_scrape

    def update_cache_metadata(
        self,
        shows_count: Optional[int] = None,
        songs_count: Optional[int] = None,
        execution_time: Optional[float] = None,
        setlist_count: Optional[int] = None,
    ) -> bool:
        """
        Update the cache metadata in the database.

        Args:
            shows_count: Number of shows scraped (if shows were scraped)
            songs_count: Number of songs scraped (if songs were scraped)
            execution_time: Pipeline execution time in seconds
            setlist_count: Number of setlists processed

        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Get existing metadata or create new
            existing_metadata = self.get_cache_metadata() or {}
            now = datetime.now()

            # Update cache information
            if shows_count is not None:
                existing_metadata["shows"] = {
                    "last_scraped": now.isoformat(),
                    "count": shows_count,
                    "scrape_type": "full",
                }
                self.logger.info("Updated shows cache: %d shows scraped", shows_count)

            if songs_count is not None:
                existing_metadata["songs"] = {
                    "last_scraped": now.isoformat(),
                    "count": songs_count,
                    "scrape_type": "full",
                }
                self.logger.info("Updated songs cache: %d songs scraped", songs_count)

            # Build complete metadata object
            metadata = {"cache": existing_metadata, "performance": {}}

            if execution_time is not None:
                metadata["performance"]["execution_time_seconds"] = execution_time

            if setlist_count is not None:
                metadata["performance"]["setlist_count"] = setlist_count

            # Upsert to database
            response = (
                self.supabase_client.table("pipeline_metadata")
                .upsert(
                    {
                        "pipeline_name": self.pipeline_name,
                        "last_updated": now.isoformat(),
                        "metadata": metadata,
                    }
                )
                .execute()
            )

            if response.data:
                self.logger.info("✅ Cache metadata updated successfully in database")
                return True
            else:
                self.logger.error("❌ Failed to update cache metadata: no data returned")
                return False
        except APIError as e:
            if e.code == "PGRST204":  # Schema cache issue / missing column
                self.logger.warning(
                    "Could not update 'metadata' column, it may not exist. "
                    "Please consider running the schema migration. Skipping cache update."
                )
                return False
            self.logger.error("❌ APIError while updating cache metadata: %s", e)
            return False
        except Exception as e:
            self.logger.error("❌ Unexpected error while updating cache metadata: %s", e)
            return False

    def get_date_filter_cutoff(self, months_back: int = 3) -> datetime:
        """
        Get the cutoff date for filtering recent shows.

        Args:
            months_back: Number of months to look back

        Returns:
            datetime cutoff for filtering
        """
        cutoff = datetime.now() - timedelta(days=months_back * 30)  # Approximate months
        self.logger.info(
            "Using date filter cutoff: %s (%d months back)",
            cutoff.strftime("%Y-%m-%d"),
            months_back,
        )
        return cutoff

    def get_supabase_date_filter(self, years_back: int = 3) -> str:
        """
        Get the date filter for Supabase queries.

        Args:
            years_back: Number of years to look back

        Returns:
            ISO date string for Supabase filtering
        """
        cutoff = datetime.now() - timedelta(days=years_back * 365)
        date_str = cutoff.strftime("%Y-%m-%d")
        self.logger.info(
            "Using Supabase date filter: %s (%d years back)", date_str, years_back
        )
        return date_str


# Convenience functions to maintain API compatibility with the old cache_utils.py
_cache_instance = None


def get_cache_instance(logger: logging.Logger) -> WSPDatabaseCache:
    """Get a singleton instance of the database cache."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = WSPDatabaseCache(logger)
    return _cache_instance


def should_scrape_shows(logger: logging.Logger, force_scrape: bool = False, max_age_days: int = 7) -> bool:
    """Convenience function for backward compatibility."""
    return get_cache_instance(logger).should_scrape_shows(force_scrape, max_age_days)


def should_scrape_songs(logger: logging.Logger, force_scrape: bool = False, max_age_days: int = 7) -> bool:
    """Convenience function for backward compatibility."""
    return get_cache_instance(logger).should_scrape_songs(force_scrape, max_age_days)


def update_shows_cache(logger: logging.Logger, show_count: int) -> bool:
    """Convenience function for backward compatibility."""
    return get_cache_instance(logger).update_cache_metadata(shows_count=show_count)


def update_songs_cache(logger: logging.Logger, song_count: int) -> bool:
    """Convenience function for backward compatibility."""
    return get_cache_instance(logger).update_cache_metadata(songs_count=song_count)


def get_date_filter_cutoff(logger: logging.Logger, months_back: int = 3) -> datetime:
    """Convenience function for backward compatibility."""
    return get_cache_instance(logger).get_date_filter_cutoff(months_back)


def get_supabase_date_filter(logger: logging.Logger, years_back: int = 3) -> str:
    """Convenience function for backward compatibility."""
    return get_cache_instance(logger).get_supabase_date_filter(years_back)
