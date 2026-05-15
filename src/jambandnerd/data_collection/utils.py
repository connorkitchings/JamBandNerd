"""Shared utility functions for data collection scripts."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import date
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def compute_source_hash(record: Dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash of a JSON-serializable record.

    Handles pandas NaN values by converting them to None before hashing.
    Uses ``default=str`` to safely serialize non-standard types (e.g., Timestamps).
    """
    cleaned: Dict[str, Any] = {}
    for key, value in record.items():
        if value is None:
            cleaned[key] = None
            continue
        try:
            if pd.isna(value):
                cleaned[key] = None
                continue
        except (TypeError, ValueError):
            pass
        cleaned[key] = value
    payload = json.dumps(
        cleaned, sort_keys=True, ensure_ascii=False, default=str
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def log_collection_run(
    band: str,
    *,
    start_time: float,
    max_show_date: Optional[date | str] = None,
    rows_collected: Optional[int] = None,
    status: str = "success",
) -> None:
    """Log a completed collection run to the ``collection_runs`` table.

    Args:
        band: Band slug (e.g. "goose", "phish").
        start_time: Monotonic clock value from before collection started
                    (via ``time.monotonic()``).
        max_show_date: Latest show_date seen during collection.
        rows_collected: Total rows upserted across all tables.
        status: "success", "degraded", or "failed".
    """
    from jambandnerd.db.connection import get_supabase_client

    elapsed = round(time.monotonic() - start_time, 2)
    record: Dict[str, Any] = {
        "band": band,
        "status": status,
        "duration_seconds": elapsed,
    }
    if max_show_date is not None:
        record["max_show_date"] = str(max_show_date)
    if rows_collected is not None:
        record["rows_collected"] = rows_collected

    try:
        client = get_supabase_client()
        client.table("collection_runs").insert(record).execute()
        logger.info("Logged collection run for %s (%ss, %s)", band, elapsed, status)
    except Exception as exc:
        logger.warning("Could not log collection run for %s: %s", band, exc)


class CollectionTimer:
    """Context manager that tracks elapsed time for collection runs.

    Usage::

        timer = CollectionTimer()
        # ... do collection work ...
        timer.log("goose", max_show_date="2026-04-14")
    """

    def __init__(self) -> None:
        self.start_time = time.monotonic()

    def log(
        self,
        band: str,
        *,
        max_show_date: Optional[date | str] = None,
        rows_collected: Optional[int] = None,
        status: str = "success",
    ) -> None:
        log_collection_run(
            band,
            start_time=self.start_time,
            max_show_date=max_show_date,
            rows_collected=rows_collected,
            status=status,
        )
