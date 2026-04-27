"""Umphrey's McGee data collector using official JSON API."""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from io import StringIO
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin

import pandas as pd
from requests import RequestException

from ..base import BandCollector
from ..config import get_collector_config

logger = logging.getLogger(__name__)


class UmCollector(BandCollector):
    """Collect Umphrey's McGee data from allthings.umphreys.com API."""

    ARTIST_NAME = "Umphrey's McGee"
    BASE_URL = "https://allthings.umphreys.com"
    EARLIEST_YEAR = 1998

    def __init__(self) -> None:
        config = get_collector_config("um")
        super().__init__(config)
        logger.info(
            "Initialized UmCollector with API base: %s",
            self.config.base_url,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def collect_songs(self) -> List[Dict[str, Any]]:
        """
        Scrape the UM song catalog from HTML.
        We keep the scraper for songs because it provides rich statistics
        (Debut Date, Last Played, Times Played, Avg Gap) not in the JSON API.
        """

        # Song scraping still needs the main website URL
        url = f"{self.BASE_URL}/song/"
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to fetch UM songs from %s: %s", url, exc)
            return []

        try:
            target_df = _extract_table(
                html=response.text,
                required_columns={
                    "Song Name",
                    "Original Artist",
                    "Debut Date",
                    "Last Played",
                },
            )
        except ValueError as exc:
            logger.error("Could not parse UM song table: %s", exc)
            return []

        if target_df.empty:
            logger.warning("UM songs table was empty.")
            return []

        column_map = {
            "Song Name": "song_name",
            "Original Artist": "original_artist",
            "Debut Date": "debut_date",
            "Last Played": "last_played",
            "Times Played Live": "times_played_live",
            "Avg Show Gap": "avg_show_gap",
        }
        df = target_df.rename(
            columns={k: v for k, v in column_map.items() if k in target_df.columns}
        )

        # Normalize string columns
        df["song_name"] = df["song_name"].astype(str).str.strip()

        if "original_artist" in df.columns:
            df["original_artist"] = df["original_artist"].replace(
                {"—": None, "N/A": None, "": None}
            )
            df["is_original"] = df["original_artist"].isna() | (df["original_artist"] == self.ARTIST_NAME)

        # Convert dates to ISO format
        for col in ("debut_date", "last_played"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce").dt.date.apply(
                    lambda d: d.isoformat() if pd.notnull(d) else None
                )

        # Numeric conversions
        if "times_played_live" in df.columns:
            df["times_played_live"] = (
                pd.to_numeric(df["times_played_live"], errors="coerce")
                .fillna(0)
                .astype(int)
            )
        if "avg_show_gap" in df.columns:
            df["avg_show_gap"] = pd.to_numeric(df["avg_show_gap"], errors="coerce")

        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")
        logger.info("✅ %s: Scraped %s songs (rich metadata).", self.ARTIST_NAME, len(records))
        return records

    def collect_venues(self) -> List[Dict[str, Any]]:
        """Scrape UM venue data from HTML for rich statistics."""

        url = f"{self.BASE_URL}/venues/"
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
        except RequestException as exc:
            logger.error("Failed to fetch UM venues from %s: %s", url, exc)
            return []

        try:
            target_df = _extract_table(
                html=response.text,
                required_columns={"Venue Name", "City", "State", "Country"},
            )
        except ValueError as exc:
            logger.error("Could not parse UM venue table: %s", exc)
            return []

        if target_df.empty:
            logger.warning("UM venue table was empty.")
            return []

        df = target_df.copy()
        df.reset_index(drop=True, inplace=True)
        
        # Extract venue_id from links if possible, or use a placeholder
        # Actually, the JSON API had venue_id. Let's see if we can merge them or just use scraping.
        # Scraping gives us the name/city/state/country which is what we used before.
        
        column_map = {
            "Venue Name": "venue_name",
            "City": "venue_city",
            "State": "venue_state",
            "Country": "venue_country",
            "Times Played": "times_played",
            "Last Played": "last_played",
        }
        df.rename(
            columns={k: v for k, v in column_map.items() if k in df.columns},
            inplace=True,
        )

        if "last_played" in df.columns:
            df["last_played"] = pd.to_datetime(
                df["last_played"], errors="coerce"
            ).dt.date.apply(lambda d: d.isoformat() if pd.notnull(d) else None)
        if "times_played" in df.columns:
            df["times_played"] = (
                pd.to_numeric(df["times_played"], errors="coerce").fillna(0).astype(int)
            )

        df["venue_name"] = df["venue_name"].astype(str).str.strip()
        df["venue_city"] = df["venue_city"].astype(str).str.strip()
        df["venue_state"] = df["venue_state"].astype(str).str.strip()
        df["venue_country"] = df["venue_country"].astype(str).str.strip()

        # Since we changed the migration to use venue_id as PK, we need IDs.
        # If we can't get them from scraping, we might need to fetch the API list to map them.
        # For now, let's see if we can just use the API list and accept missing stats, 
        # or scrap and then map IDs.
        
        # NEW PLAN: Fetch API venues first to get IDs, then scrap to get stats, and merge.
        api_venues = self._fetch_api_venues()
        
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")
        
        # Merge with API IDs
        venue_map = {
            (v["venue_name"], v["venue_city"], v["venue_state"]): v["venue_id"]
            for v in api_venues
        }
        
        for r in records:
            key = (r["venue_name"], r["venue_city"], r["venue_state"])
            r["venue_id"] = venue_map.get(key)
            
        # Filter out ones without IDs if we use it as PK
        final_records = [r for r in records if r.get("venue_id") is not None]
        
        logger.info("✅ %s: Collected %s venues with stats.", self.ARTIST_NAME, len(final_records))
        return final_records

    def _fetch_api_venues(self) -> List[Dict[str, Any]]:
        url = f"{self.config.base_url.rstrip('/')}/v2/venues.json"
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()
            data = response.json()
            return [{
                "venue_id": v.get("venue_id"),
                "venue_name": v.get("venuename"),
                "venue_city": v.get("city"),
                "venue_state": v.get("state"),
            } for v in data.get("data", [])]
        except Exception:
            return []

    def collect_shows(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch show metadata for a date range via API."""

        if end_date and start_date and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")

        start = start_date or date(self.EARLIEST_YEAR, 1, 1)
        end = end_date or date.today()

        records: List[Dict[str, Any]] = []
        years = range(start.year, end.year + 1)
        
        for year in years:
            url = f"{self.config.base_url.rstrip('/')}/v2/shows/show_year/{year}.json"
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                data = response.json()
                if data.get("error"):
                    continue
                
                for show in data.get("data", []):
                    show_date_str = show.get("showdate")
                    if not show_date_str:
                        continue
                    try:
                        show_date = datetime.strptime(show_date_str, "%Y-%m-%d").date()
                    except ValueError:
                        continue
                        
                    if show_date < start or show_date > end:
                        continue
                    
                    records.append({
                        "show_id": show.get("show_id"),
                        "source_url": urljoin(self.BASE_URL, show.get("permalink", "")),
                        "show_date": show_date.isoformat(),
                        "venue_name": show.get("venuename"),
                        "venue_city": show.get("city"),
                        "venue_state": show.get("state"),
                        "venue_country": show.get("country"),
                        "show_notes": show.get("shownotes"),
                        "show_year": show_date.year,
                        "show_month": show_date.month,
                        "show_day": show_date.day,
                        "tour_name": show.get("tourname"),
                    })
            except Exception as exc:
                logger.error("Failed to fetch UM shows for %s: %s", year, exc)

        records.sort(key=lambda item: item["show_date"])
        logger.info(
            "✅ %s: Collected %s shows between %s and %s via API.",
            self.ARTIST_NAME,
            len(records),
            start,
            end,
        )
        return records

    def collect_setlists(
        self, shows_to_process: Iterable[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fetch setlist rows for the provided shows via API."""

        shows_list = list(shows_to_process)
        if not shows_list:
            return []

        # Identify unique years to fetch in bulk
        years = set()
        for s in shows_list:
            sd = s.get("show_date")
            if sd:
                years.add(datetime.fromisoformat(sd).year)
        
        # Mapping for quick lookup
        show_ids_to_process = {str(s.get("show_id")) for s in shows_list}
        
        results: List[Dict[str, Any]] = []
        for year in sorted(years):
            url = f"{self.config.base_url.rstrip('/')}/v2/setlists/showyear/{year}.json"
            try:
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                data = response.json()
                if data.get("error"):
                    continue
                
                # Group by show_id to calculate song_position
                show_data = {}
                for row in data.get("data", []):
                    show_id = str(row.get("show_id"))
                    if show_id not in show_ids_to_process:
                        continue
                    if show_id not in show_data:
                        show_data[show_id] = []
                    show_data[show_id].append(row)
                
                for show_id, rows in show_data.items():
                    # Sort by API position just in case
                    rows.sort(key=lambda r: int(r.get("position") or 0))
                    
                    current_set = None
                    song_pos = 0
                    
                    for row in rows:
                        set_num = str(row.get("setnumber"))
                        if set_num != current_set:
                            current_set = set_num
                            song_pos = 1
                        else:
                            song_pos += 1
                            
                        results.append({
                            "show_id": show_id,
                            "song_id": row.get("song_id"),
                            "song_name": row.get("songname"),
                            "set_label": row.get("settype"),
                            "set_sequence": set_num,
                            "song_position": song_pos,
                            "show_position": row.get("position"),
                            "transition": row.get("transition"),
                            "footnote_text": row.get("footnote"),
                        })
            except Exception as exc:
                logger.error("Failed to fetch UM setlists for %s: %s", year, exc)

        logger.info("✅ %s: Collected %s setlist rows via API.", self.ARTIST_NAME, len(results))
        return results


# ----------------------------------------------------------------------
# Pure helper functions
# ----------------------------------------------------------------------


def _extract_table(html: str, required_columns: set[str]) -> pd.DataFrame:
    """Extract the first table containing all required columns."""
    buffer = StringIO(html)
    tables = pd.read_html(buffer)
    for table in tables:
        if required_columns.issubset(set(table.columns)):
            return table
    raise ValueError(f"No table contained required columns: {sorted(required_columns)}")
