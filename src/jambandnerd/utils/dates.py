"""Timezone-aware date helpers for show-date boundaries."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

SHOW_DATE_TIMEZONE = ZoneInfo("America/New_York")


def current_show_date(now: datetime | None = None) -> date:
    """Return today's calendar date in US Eastern time.

    All supported bands store local US concert dates in ``show_date``. Using
    US Eastern instead of the host/runner local timezone (UTC in GitHub
    Actions) prevents evening runs after 00:00 UTC from treating an upcoming
    or in-progress US show as already completed.
    """
    if now is None:
        return datetime.now(SHOW_DATE_TIMEZONE).date()
    return now.astimezone(SHOW_DATE_TIMEZONE).date()
