"""Utility functions for fetching upcoming Umphrey's McGee shows from Seated."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

SEATED_API_HOST = "https://cdn.seated.com"
ARTIST_ID = "38328e2c-56c6-463f-aa18-1641e417c49c"
USER_AGENT = "Mozilla/5.0"
CLIENT_VERSION = "HEAD"


class UpcomingShowsError(RuntimeError):
    """Raised when the upcoming shows widget cannot be fetched."""


@dataclass(frozen=True)
class UpcomingShow:
    """Normalized representation of an upcoming show."""

    source_uuid: str
    starts_at: Optional[str]
    starts_at_local: Optional[str]
    ends_at: Optional[str]
    venue_name: Optional[str]
    formatted_address: Optional[str]
    city: Optional[str]
    region: Optional[str]
    country: Optional[str]
    details: Optional[str]
    exchange_listing_url: Optional[str]
    vip_link_url: Optional[str]
    is_sold_out: Optional[bool]
    is_collecting_waitlist: Optional[bool]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source_uuid": self.source_uuid,
            "starts_at": self.starts_at,
            "starts_at_local": self.starts_at_local,
            "ends_at": self.ends_at,
            "venue_name": self.venue_name,
            "formatted_address": self.formatted_address,
            "city": self.city,
            "region": self.region,
            "country": self.country,
            "details": self.details,
            "exchange_listing_url": self.exchange_listing_url,
            "vip_link_url": self.vip_link_url,
            "is_sold_out": self.is_sold_out,
            "is_collecting_waitlist": self.is_collecting_waitlist,
        }


def _parse_address(
    formatted: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Parse the formatted address into city, region/state, country."""
    if not formatted:
        return None, None, None
    parts = [part.strip() for part in formatted.split(",") if part.strip()]
    if not parts:
        return None, None, None
    if len(parts) == 1:
        return parts[0], None, None
    if len(parts) == 2:
        return parts[0], parts[1], None
    # Three or more components; treat last as country, second-to-last as region.
    city = ", ".join(parts[:-2])
    region = parts[-2]
    country = parts[-1]
    return city or None, region or None, country or None


def _coerce_iso(dt_value: Optional[str]) -> Optional[str]:
    """Ensure datetime values are ISO 8601 strings."""
    if not dt_value:
        return None
    try:
        parsed = datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
    except ValueError:
        return dt_value
    return parsed.isoformat()


def collect_upcoming_shows(
    *,
    artist_id: str = ARTIST_ID,
    session: Optional[requests.Session] = None,
) -> List[Dict[str, Any]]:
    """Fetch upcoming Umphrey's McGee shows from the Seated widget API."""
    sess = session or requests.Session()
    url = f"{SEATED_API_HOST}/api/tour/{artist_id}?include=tour-events"
    response = sess.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "X-Client-Version": CLIENT_VERSION,
            "Accept": "application/vnd.api+json",
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise UpcomingShowsError(
            f"Failed to fetch upcoming shows ({response.status_code})"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise UpcomingShowsError("Received non-JSON response from Seated API") from exc

    included: Iterable[Dict[str, Any]] = payload.get("included") or []
    shows: List[UpcomingShow] = []
    for item in included:
        if item.get("type") != "tour-events":
            continue
        attrs = item.get("attributes") or {}
        formatted_address = attrs.get("formatted-address")
        city, region, country = _parse_address(formatted_address)
        shows.append(
            UpcomingShow(
                source_uuid=str(item.get("id")),
                starts_at=_coerce_iso(attrs.get("starts-at")),
                starts_at_local=attrs.get("starts-at-date-local"),
                ends_at=_coerce_iso(attrs.get("ends-at")),
                venue_name=attrs.get("venue-name"),
                formatted_address=formatted_address,
                city=city,
                region=region,
                country=country,
                details=attrs.get("details"),
                exchange_listing_url=attrs.get("exchange-listing-url"),
                vip_link_url=attrs.get("vip-link-url"),
                is_sold_out=attrs.get("is-sold-out"),
                is_collecting_waitlist=attrs.get("is-collecting-waitlist"),
            )
        )

    return [show.as_dict() for show in shows]
