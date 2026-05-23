"""Correction detection module for identifying and applying data corrections.

This module provides utilities for detecting when upstream data sources have
made corrections to existing records (e.g., setlist fixes, venue corrections)
and applying those corrections to the database.

Used primarily by the weekly correction sweep workflow (Tuesdays).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from src.jambandnerd.db.connection import get_supabase_client

logger = logging.getLogger(__name__)


@dataclass
class CorrectionResult:
    """Result of a correction detection operation."""

    band: str
    table_name: str
    records_checked: int
    corrections_found: int
    corrections_applied: int
    errors: List[str] = field(default_factory=list)
    details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "band": self.band,
            "table_name": self.table_name,
            "records_checked": self.records_checked,
            "corrections_found": self.corrections_found,
            "corrections_applied": self.corrections_applied,
            "errors": self.errors,
            "details": self.details,
        }


def compute_record_checksum(record: Dict[str, Any]) -> str:
    """Compute a deterministic checksum for a record.

    This checksum can be used to detect when a record has changed.
    Excludes metadata fields like created_at/updated_at.
    """
    # Fields to exclude from checksum (metadata)
    excluded_fields = {"created_at", "updated_at", "source_hash", "id"}

    # Clean and sort the record
    cleaned = {}
    for key, value in record.items():
        if key in excluded_fields:
            continue
        # Normalize None values
        if value is None:
            cleaned[key] = None
        else:
            cleaned[key] = str(value)

    # Create deterministic JSON representation
    payload = json.dumps(cleaned, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fetch_db_records_with_checksums(
    table_name: str,
    band: str,
    since: Optional[date] = None,
    until: Optional[date] = None,
    client=None,
) -> Dict[str, Tuple[Dict[str, Any], str]]:
    """Fetch records from DB with their checksums.

    Returns:
        Dict mapping record ID to tuple of (record_data, checksum)
    """
    client = client or get_supabase_client()

    try:
        # Build query
        query = client.table(table_name).select("*")

        # Apply date filters
        if since:
            query = query.gte("show_date", since.isoformat())
        if until:
            query = query.lte("show_date", until.isoformat())

        # Execute query
        response = query.execute()
        rows = response.data or []
    except Exception as exc:
        logger.error("Failed to fetch %s records: %s", table_name, exc)
        return {}

    result = {}
    for row in rows:
        record_id = str(
            row.get("show_id") or row.get("api_song_id") or row.get("song_id")
        )
        if not record_id:
            continue

        checksum = compute_record_checksum(row)
        result[record_id] = (row, checksum)

    return result


def detect_setlist_corrections(
    band: str,
    upstream_setlists: List[Dict[str, Any]],
    db_records: Dict[str, Tuple[Dict[str, Any], str]],
    dry_run: bool = True,
    client=None,
) -> CorrectionResult:
    """Detect corrections between upstream and DB setlist data.

    Args:
        band: Band slug (e.g., "goose", "phish")
        upstream_setlists: Fresh setlist data from upstream source
        db_records: Dict of DB records with checksums from fetch_db_records_with_checksums
        dry_run: If True, only detect corrections without applying them
        client: Optional Supabase client

    Returns:
        CorrectionResult with details of found/applied corrections
    """
    client = client or get_supabase_client()
    table_name = f"{band}_setlists_raw"

    result = CorrectionResult(
        band=band,
        table_name=table_name,
        records_checked=len(db_records),
        corrections_found=0,
        corrections_applied=0,
    )

    # Group upstream setlists by show_id for comparison
    upstream_by_show: Dict[str, List[Dict[str, Any]]] = {}
    for sl in upstream_setlists:
        show_id = str(sl.get("show_id"))
        if show_id not in upstream_by_show:
            upstream_by_show[show_id] = []
        upstream_by_show[show_id].append(sl)

    # Check each show in DB
    for show_id, (db_record, db_checksum) in db_records.items():
        if show_id not in upstream_by_show:
            # Show exists in DB but not in upstream (might be deleted)
            continue

        upstream_setlist = upstream_by_show[show_id]

        # Compute checksum of upstream data
        upstream_normalized = {
            "show_id": show_id,
            "setlist": sorted(
                upstream_setlist,
                key=lambda x: (x.get("set_number", 0), x.get("song_position", 0)),
            ),
        }
        upstream_checksum = compute_record_checksum(upstream_normalized)

        if upstream_checksum != db_checksum:
            # Correction detected!
            result.corrections_found += 1

            detail = {
                "show_id": show_id,
                "db_checksum": db_checksum,
                "upstream_checksum": upstream_checksum,
                "action": "detected" if dry_run else "applied",
            }

            if not dry_run:
                # Apply correction: delete old setlist rows and insert new ones
                try:
                    # Delete existing setlist rows for this show
                    client.table(table_name).delete().eq("show_id", show_id).execute()

                    # Insert new setlist rows
                    for row in upstream_setlist:
                        client.table(table_name).insert(row).execute()

                    result.corrections_applied += 1
                    detail["action"] = "applied"
                    logger.info(
                        "Applied setlist correction for %s show %s", band, show_id
                    )

                except Exception as exc:
                    error_msg = f"Failed to apply correction for {show_id}: {exc}"
                    result.errors.append(error_msg)
                    detail["action"] = "error"
                    detail["error"] = error_msg
                    logger.error(error_msg)

            result.details.append(detail)

    return result


def run_correction_sweep(
    band: str,
    window_days: int = 730,
    dry_run: bool = True,
    tables: Optional[List[str]] = None,
    client=None,
) -> Dict[str, CorrectionResult]:
    """Run a full correction sweep for a band.

    Args:
        band: Band slug (e.g., "goose", "phish")
        window_days: Number of days to look back for corrections
        dry_run: If True, only detect corrections without applying
        tables: List of tables to check (default: [shows, setlists, songs])
        client: Optional Supabase client

    Returns:
        Dict mapping table names to CorrectionResult
    """
    client = client or get_supabase_client()
    results = {}

    # Calculate date window
    until = date.today()
    since = until - timedelta(days=window_days)

    logger.info(
        "Starting correction sweep for %s (window: %s to %s, dry_run=%s)",
        band,
        since.isoformat(),
        until.isoformat(),
        dry_run,
    )

    tables = tables or ["setlists"]  # Start with setlists as most common corrections

    # Import the appropriate collector
    collector = _get_collector_for_band(band)
    if not collector:
        logger.error("No collector available for band: %s", band)
        return results

    for table_type in tables:
        table_name = f"{band}_{table_type}_raw"

        try:
            # Fetch DB records with checksums
            db_records = fetch_db_records_with_checksums(
                table_name, band, since=since, until=until, client=client
            )

            if not db_records:
                logger.info(
                    "No %s records found in DB for correction sweep", table_name
                )
                continue

            # Fetch fresh upstream data
            if table_type == "setlists":
                # Fetch shows first, then setlists
                shows = collector.collect_shows(start_date=since, end_date=until)
                show_ids = [str(s.get("show_id")) for s in shows]

                # Fetch fresh setlists for these shows
                upstream_data = collector.collect_setlists(show_ids=show_ids)

                result = detect_setlist_corrections(
                    band, upstream_data, db_records, dry_run=dry_run, client=client
                )
                results[table_name] = result

            elif table_type == "shows":
                # For shows, compare metadata
                # TODO: Implement show metadata correction detection
                # upstream_shows = collector.collect_shows(start_date=since, end_date=until)
                logger.info("Show correction detection not yet implemented")

            elif table_type == "songs":
                # For songs, compare catalog
                # TODO: Implement song correction detection
                # upstream_songs = collector.collect_songs()
                logger.info("Song correction detection not yet implemented")

        except Exception as exc:
            logger.error("Error during correction sweep for %s: %s", table_name, exc)
            results[table_name] = CorrectionResult(
                band=band,
                table_name=table_name,
                records_checked=0,
                corrections_found=0,
                corrections_applied=0,
                errors=[str(exc)],
            )

    return results


def _get_collector_for_band(band: str):
    """Get the appropriate collector class for a band."""
    collectors = {
        "goose": "src.jambandnerd.data_collection.goose.collector.GooseCollector",
        "phish": "src.jambandnerd.data_collection.phish.collector.PhishCollector",
        "eggy": "src.jambandnerd.data_collection.eggy.collector.EggyCollector",
        "um": "src.jambandnerd.data_collection.um.collector.UmCollector",
        "billy": "src.jambandnerd.data_collection.billy.collector.BillyCollector",
        "wsp": "src.jambandnerd.data_collection.wsp.collector.WSPCollector",
    }

    collector_path = collectors.get(band)
    if not collector_path:
        return None

    try:
        module_path, class_name = collector_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)()
    except Exception as exc:
        logger.error("Failed to load collector for %s: %s", band, exc)
        return None


def format_correction_report(results: Dict[str, CorrectionResult]) -> str:
    """Format correction results as a human-readable report."""
    lines = ["=" * 60, "CORRECTION SWEEP REPORT", "=" * 60, ""]

    total_checked = sum(r.records_checked for r in results.values())
    total_found = sum(r.corrections_found for r in results.values())
    total_applied = sum(r.corrections_applied for r in results.values())

    lines.append(f"Total records checked: {total_checked}")
    lines.append(f"Total corrections found: {total_found}")
    lines.append(f"Total corrections applied: {total_applied}")
    lines.append("")

    for table_name, result in results.items():
        lines.append(f"\n{table_name}:")
        lines.append(f"  Records checked: {result.records_checked}")
        lines.append(f"  Corrections found: {result.corrections_found}")
        lines.append(f"  Corrections applied: {result.corrections_applied}")

        if result.errors:
            lines.append(f"  Errors: {len(result.errors)}")
            for error in result.errors[:3]:  # Show first 3 errors
                lines.append(f"    - {error}")

        if result.details:
            lines.append("  Details:")
            for detail in result.details[:5]:  # Show first 5 details
                show_id = detail.get("show_id", "unknown")
                action = detail.get("action", "unknown")
                lines.append(f"    - Show {show_id}: {action}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
