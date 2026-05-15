"""Orchestrates the Widespread Panic data collection pipeline.

This module contains the core logic for collecting, processing, and storing
WSP data from various sources.
"""

import logging
import os
import re
from collections import Counter
from datetime import date, datetime, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup

from jambandnerd.data_collection.utils import CollectionTimer, compute_source_hash
from jambandnerd.db.connection import get_supabase_client
from jambandnerd.db.operations import (
    fetch_existing_values,
    get_table_schema,
    validate_and_upsert_dataframe,
)
from scripts.common import ensure_source_reachable, fetch_table

from .collector import WSPCollector
from .normalizer import (
    normalize_setlists,
    normalize_shows,
    normalize_songs,
    normalize_venues,
)
from .panicstream import fetch_setlist_from_panicstream
from .parser import parse_setlist_from_text
from .parser_profile import (
    DEFAULT_PROFILE,
    fingerprint_page,
    validate_fingerprint,
)
from .session import cleanup_playwright, create_enhanced_session, decode_ec_response
from .status import CollectionStatus
from .tourwrangler import fetch_setlist_from_tourwrangler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

RECENT_WSP_FALLBACK_SOURCES = (
    ("panicstream", fetch_setlist_from_panicstream),
    ("tourwrangler", fetch_setlist_from_tourwrangler),
)


def _page_has_setlist_table(page_html: str, show_id: str) -> bool:
    """Return True when an EC page appears to expose a parseable setlist."""
    soup = BeautifulSoup(page_html, "html.parser")

    fp = fingerprint_page(soup, DEFAULT_PROFILE)
    warnings = validate_fingerprint(fp, DEFAULT_PROFILE)
    if warnings:
        logging.warning(
            "WSP DOM fingerprint mismatch for show_id=%s: %s",
            show_id,
            "; ".join(warnings),
        )

    if parse_setlist_from_text(soup, show_id):
        return True

    tables = soup.find_all("table")
    if len(tables) < DEFAULT_PROFILE.song_table_min_tables:
        return False

    lo, hi = DEFAULT_PROFILE.setlist_table_range
    for table in tables[lo:hi]:
        table_text = table.get_text()
        if (
            any(m in table_text for m in DEFAULT_PROFILE.setlist_set_markers)
        ) and not any(m in table_text for m in DEFAULT_PROFILE.setlist_noise_markers):
            return True

    return False


def _probe_everydaycompanion_setlist_status(source_url: str, show_id: str) -> str:
    """Classify whether an EC page has a setlist or is simply unpublished."""
    session = create_enhanced_session()
    try:
        response = session.get(source_url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        page_html = decode_ec_response(response)
        if _page_has_setlist_table(page_html, show_id):
            return "collector_missed_setlist"
        return "upstream_missing_setlist"
    except requests.exceptions.RequestException:
        return "ec_request_failed"
    finally:
        session.close()
        cleanup_playwright()


def classify_missing_recent_setlists(
    client, missing_shows: list[dict[str, object]]
) -> list[dict[str, object]]:
    """Classify recent missing WSP setlists as upstream lag or system issues."""
    diagnostics: list[dict[str, object]] = []

    for record in missing_shows:
        show_id = str(record.get("show_id") or "").strip()
        show_date = str(record.get("show_date") or "").strip()
        source_url = _normalize_source_url(record.get("source_url"))
        city = record.get("city")
        state = record.get("state")

        if not show_id or not show_date:
            continue

        if not source_url:
            diagnostics.append(
                {
                    "show_id": show_id,
                    "show_date": show_date,
                    "diagnosis": "missing_source_url",
                    "detail": "show row has no source_url",
                }
            )
            continue

        diagnosis = _probe_everydaycompanion_setlist_status(source_url, show_id)
        if diagnosis in {"upstream_missing_setlist", "ec_request_failed"}:
            backup_rows, backup_source, lookup_errors = _resolve_recent_wsp_fallback(
                pd.to_datetime(show_date).date(), show_id, city, state
            )
            detail = (
                "Everyday Companion page has no setlist table"
                if diagnosis == "upstream_missing_setlist"
                else "Everyday Companion request failed and fallback was empty"
            )
            if backup_rows:
                diagnosis = "fallback_data_available"
                detail = f"{_format_fallback_source(backup_source)} returned backup rows for this show"
            elif lookup_errors:
                detail = f"{detail}; {'; '.join(lookup_errors)}"
        elif diagnosis == "collector_missed_setlist":
            detail = "Everyday Companion page appears to contain a setlist"
        else:
            detail = diagnosis

        diagnostics.append(
            {
                "show_id": show_id,
                "show_date": show_date,
                "diagnosis": diagnosis,
                "detail": detail,
            }
        )

    return diagnostics


def _normalize_source_url(value: object) -> str | None:
    """Return a normalized source URL string or None if unavailable."""
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_venue_name(value: object) -> str | None:
    """Normalize venue text for fallback matching only."""
    if value is None:
        return None
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value).lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if normalized.startswith("the "):
        normalized = normalized[4:]
    return normalized or None


def _format_fallback_source(source_name: str | None) -> str:
    if source_name == "panicstream":
        return "PanicStream"
    if source_name == "tourwrangler":
        return "TourWrangler"
    return "Fallback source"


def _setlist_table_has_source_column() -> bool:
    schema = get_table_schema("wsp_setlists_raw")
    return any(str(col.get("column_name", "")).lower() == "source" for col in schema)


def _resolve_recent_wsp_fallback(
    show_date: date,
    show_id: str,
    city: object,
    state: object,
) -> tuple[list[dict[str, object]], str | None, list[str]]:
    """Return the first recent-gap fallback source that yields parseable rows."""
    lookup_errors: list[str] = []
    city_text = None if city in (None, "") else str(city)
    state_text = None if state in (None, "") else str(state)

    for source_name, fetcher in RECENT_WSP_FALLBACK_SOURCES:
        try:
            rows = fetcher(show_date, show_id, city_text, state_text)
        except Exception as exc:
            lookup_errors.append(
                f"{_format_fallback_source(source_name)} lookup failed: {exc}"
            )
            continue
        if not rows:
            continue

        normalized_rows: list[dict[str, object]] = []
        for row in rows:
            normalized = dict(row)
            normalized.setdefault("source", source_name)
            normalized_rows.append(normalized)
        return normalized_rows, source_name, lookup_errors

    return [], None, lookup_errors


def _show_fallback_key(show: dict[str, object]) -> tuple[str, str] | None:
    """Build a fallback identity key when source_url is unavailable."""
    show_date = show.get("show_date") or show.get("showdate")
    venue_name = show.get("venue_name") or show.get("venuename") or show.get("name")
    if not show_date or not venue_name:
        return None
    normalized_venue = _normalize_venue_name(venue_name)
    if not normalized_venue:
        return None
    return (str(show_date).strip(), normalized_venue)


def _dedupe_show_batch(
    shows_data: list[dict[str, object]],
) -> tuple[list[dict[str, object]], int]:
    """Collapse duplicate show rows in-memory, preferring source_url identity."""
    deduped: list[dict[str, object]] = []
    index_by_key: dict[object, int] = {}
    duplicate_count = 0

    for show in shows_data:
        source_url = _normalize_source_url(show.get("source_url"))
        fallback_key = _show_fallback_key(show)
        dedupe_key: object = source_url or fallback_key

        if dedupe_key is None:
            deduped.append(show.copy())
            continue

        if dedupe_key in index_by_key:
            duplicate_count += 1
            existing = deduped[index_by_key[dedupe_key]]
            for key, value in show.items():
                if existing.get(key) in (None, "") and value not in (None, ""):
                    existing[key] = value
            continue

        index_by_key[dedupe_key] = len(deduped)
        deduped.append(show.copy())

    return deduped, duplicate_count


def _assign_show_ids(
    shows_data: list[dict[str, object]],
    *,
    client,
    year_start: int | None,
    year_end: int | None,
    full_backfill: bool,
) -> tuple[list[dict[str, object]], dict[str, int]]:
    """Resolve WSP show identity with source_url as the primary EC key."""
    if not shows_data:
        return [], {
            "deduped_in_batch": 0,
            "reused_by_source_url": 0,
            "reused_by_fallback_key": 0,
            "new_ids_assigned": 0,
        }

    deduped_shows, deduped_count = _dedupe_show_batch(shows_data)

    try:
        max_id_resp = (
            client.table("wsp_shows_raw")
            .select("show_id")
            .order("show_id", desc=True)
            .limit(1)
            .execute()
        )
        next_id = (max_id_resp.data[0]["show_id"] + 1) if max_id_resp.data else 1
    except Exception as exc:
        logging.warning(f"Could not fetch max show_id: {exc}. Defaulting to 1.")
        next_id = 1

    source_url_map: dict[str, int] = {}
    fallback_map: dict[tuple[str, str], int] = {}
    existing_query = client.table("wsp_shows_raw").select(
        "show_id, show_date, venue_name, source_url"
    )
    if not full_backfill and year_start and year_end:
        existing_query = existing_query.gte("show_date", f"{year_start}-01-01").lte(
            "show_date", f"{year_end}-12-31"
        )

    try:
        existing_rows = existing_query.execute().data or []
        for row in existing_rows:
            show_id = row.get("show_id")
            if show_id is None:
                continue
            source_url = _normalize_source_url(row.get("source_url"))
            if source_url:
                source_url_map[source_url] = int(show_id)
            fallback_key = _show_fallback_key(row)
            if fallback_key and fallback_key not in fallback_map:
                fallback_map[fallback_key] = int(show_id)
    except Exception as exc:
        logging.warning(f"Could not fetch existing shows: {exc}")

    resolved_shows: list[dict[str, object]] = []
    stats = {
        "deduped_in_batch": deduped_count,
        "reused_by_source_url": 0,
        "reused_by_fallback_key": 0,
        "new_ids_assigned": 0,
    }

    for show in deduped_shows:
        resolved = show.copy()
        source_url = _normalize_source_url(resolved.get("source_url"))
        fallback_key = _show_fallback_key(resolved)

        chosen_id: int | None = None
        if source_url and source_url in source_url_map:
            chosen_id = source_url_map[source_url]
            stats["reused_by_source_url"] += 1
        elif fallback_key and fallback_key in fallback_map:
            chosen_id = fallback_map[fallback_key]
            stats["reused_by_fallback_key"] += 1
        else:
            chosen_id = next_id
            next_id += 1
            stats["new_ids_assigned"] += 1

        resolved["show_id"] = chosen_id
        resolved_shows.append(resolved)

        if source_url:
            source_url_map[source_url] = chosen_id
        if fallback_key and fallback_key not in fallback_map:
            fallback_map[fallback_key] = chosen_id

    return resolved_shows, stats


def _validate_resolved_shows(shows_data: list[dict[str, object]]) -> None:
    """Fail early if the resolved batch still contains ambiguous identities."""
    url_to_ids: dict[str, set[str]] = {}
    for show in shows_data:
        show_id = show.get("show_id")
        if show_id in (None, ""):
            raise RuntimeError(
                "Resolved WSP show batch contains a row without show_id."
            )

        source_url = _normalize_source_url(show.get("source_url"))
        if not source_url:
            raise RuntimeError(
                "Resolved WSP show batch contains a row without source_url."
            )

        url_to_ids.setdefault(source_url, set()).add(str(show_id))

    ambiguous = {url: ids for url, ids in url_to_ids.items() if len(ids) > 1}
    if ambiguous:
        sample_url, sample_ids = next(iter(ambiguous.items()))
        raise RuntimeError(
            "Resolved WSP show batch maps one source_url to multiple show_ids: "
            f"{sample_url} -> {sorted(sample_ids)}"
        )


def process_wsp_data(
    skip_existing_setlists: bool = True,
    year_start: int | None = None,
    year_end: int | None = None,
    full_backfill: bool = False,
) -> CollectionStatus:
    """Collect all WSP data and store it in Supabase raw tables."""
    timer = CollectionTimer()
    logging.info("Starting Widespread Panic data collection...")
    ensure_source_reachable("wsp")

    # Create status tracker to monitor collection success/failure
    status = CollectionStatus()
    collector = WSPCollector(status=status)
    client = get_supabase_client()

    # 1. Collect and Upsert Songs
    logging.info("--- Starting WSP Song Collection ---")
    songs_data = collector.collect_songs()
    if songs_data:
        songs_df = normalize_songs(songs_data)
        validate_and_upsert_dataframe(
            table_name="wsp_songs_raw",
            df=songs_df,
            conflict_columns=["api_song_id"],
        )
        logging.info(f"Upserted {len(songs_df)} songs into wsp_songs_raw.")
    status.songs_collected = len(songs_data)
    logging.info("--- Finished WSP Song Collection ---")

    # 2. Collect and Upsert Shows
    logging.info("--- Starting WSP Show Collection ---")
    shows_data = collector.collect_shows(
        start_date=datetime(year_start, 1, 1).date() if year_start else None,
        end_date=datetime(year_end, 12, 31).date() if year_end else None,
    )

    if shows_data:
        shows_data, identity_stats = _assign_show_ids(
            shows_data,
            client=client,
            year_start=year_start,
            year_end=year_end,
            full_backfill=full_backfill,
        )
        _validate_resolved_shows(shows_data)
        logging.info(
            "WSP show identity resolution: deduped=%s reused_by_source_url=%s "
            "reused_by_fallback_key=%s new_ids=%s",
            identity_stats["deduped_in_batch"],
            identity_stats["reused_by_source_url"],
            identity_stats["reused_by_fallback_key"],
            identity_stats["new_ids_assigned"],
        )

    if shows_data:
        shows_df = normalize_shows(shows_data)
        try:
            validate_and_upsert_dataframe(
                table_name="wsp_shows_raw",
                df=shows_df,
                conflict_columns=["show_id"],
            )
        except Exception as exc:
            duplicate_source_urls = (
                shows_df["source_url"][shows_df["source_url"].duplicated()].tolist()
                if "source_url" in shows_df.columns
                else []
            )
            if duplicate_source_urls:
                raise RuntimeError(
                    "WSP show upsert failed with duplicate source_url values in the "
                    f"resolved batch: {duplicate_source_urls[:5]}"
                ) from exc
            raise RuntimeError(
                "WSP show upsert failed after identity resolution. "
                "This likely indicates an existing DB row matched by source_url but "
                "was assigned a different show_id before upsert."
            ) from exc
        logging.info(f"Upserted {len(shows_df)} shows into wsp_shows_raw.")
    status.shows_collected = len(shows_data)
    logging.info("--- Finished WSP Show Collection ---")

    # 3. Collect and Upsert Venues
    logging.info("--- Starting WSP Venue Collection ---")
    venues_data = collector.collect_venues()
    if venues_data:
        venues_df = normalize_venues(venues_data)
        validate_and_upsert_dataframe(
            table_name="wsp_venues_raw",
            df=venues_df,
            conflict_columns=["venue_id"],
        )
        logging.info(f"Upserted {len(venues_df)} venues into wsp_venues_raw.")
    logging.info("--- Finished WSP Venue Collection ---")

    # 4. Fetch shows from DB for the specified year range
    if not full_backfill:
        if year_start and year_end:
            logging.info(
                f"Fetching shows from database for years {year_start}-{year_end}..."
            )
            shows_response = (
                client.table("wsp_shows_raw")
                .select("*")
                .gte("show_date", f"{year_start}-01-01")
                .lte("show_date", f"{year_end}-12-31")
                .execute()
            )
            shows_to_process_df = pd.DataFrame(shows_response.data)
        else:
            logging.info("Fetching all shows from database...")
            shows_to_process_df = pd.DataFrame(fetch_table("wsp_shows_raw"))
    else:
        logging.info("Fetching all shows from database for full backfill...")
        shows_to_process_df = pd.DataFrame(fetch_table("wsp_shows_raw"))

    if shows_to_process_df.empty:
        logging.error(
            "Could not retrieve shows from database. Aborting setlist collection."
        )
        return

    # 5. Check for existing setlists to avoid re-scraping
    if skip_existing_setlists:
        try:
            candidate_show_ids = shows_to_process_df["show_id"].dropna().tolist()
            existing_ids = fetch_existing_values(
                "wsp_setlists_raw",
                value_column="show_id",
                candidate_values=candidate_show_ids,
            )
            shows_to_process_df = shows_to_process_df[
                ~shows_to_process_df["show_id"].astype(str).isin(existing_ids)
            ]
        except Exception as e:
            logging.warning(
                f"Could not check existing setlists: {e}. Proceeding with all shows."
            )

    # 6. Collect and Upsert Setlists
    if not shows_to_process_df.empty:
        records_for_scrape = shows_to_process_df.to_dict("records")
        logging.info(
            f"Starting setlist collection for {len(records_for_scrape)} shows."
        )
        setlists_data = collector.collect_setlists(records_for_scrape)
        if setlists_data:
            setlists_df = normalize_setlists(setlists_data)
            validate_and_upsert_dataframe(
                table_name="wsp_setlists_raw",
                df=setlists_df,
                conflict_columns=["show_id", "set_number", "song_position"],
                required_columns=["set_number", "song_position"],
            )
            logging.info(
                f"Upserted {len(setlists_df)} setlist records into wsp_setlists_raw."
            )
            status.setlists_collected += len(setlists_df)
        else:
            logging.info("No new shows require setlist scraping.")

    # 7. Promote EC over TW for recent shows
    try:
        today = date.today()
        window_days = int(os.environ.get("WSP_BACKUP_WINDOW_DAYS", "3"))
        window_start = today - timedelta(days=window_days)
        has_source_col = _setlist_table_has_source_column()

        resp_shows = (
            client.table("wsp_shows_raw")
            .select("show_id, show_date")
            .gte("show_date", window_start.isoformat())
            .lt("show_date", today.isoformat())
            .execute()
        )
        recent_ids = [
            str(r.get("show_id")) for r in (resp_shows.data or []) if r.get("show_id")
        ]

        if has_source_col and recent_ids:
            logging.info(
                "Promoting Everyday Companion data over TourWrangler for recent shows..."
            )
            resp_ec = (
                client.table("wsp_setlists_raw")
                .select("show_id")
                .in_("show_id", recent_ids)
                .eq("source", "everydaycompanion")
                .execute()
            )
            ec_ids = sorted(
                {
                    str(r.get("show_id"))
                    for r in (resp_ec.data or [])
                    if r.get("show_id")
                }
            )
            if ec_ids:
                for source_name in ("panicstream", "tourwrangler"):
                    client.table("wsp_setlists_raw").delete().in_("show_id", ec_ids).eq(
                        "source", source_name
                    ).execute()
                logging.info(
                    "Removed fallback rows for %s show(s) now covered by EC.",
                    len(ec_ids),
                )
    except Exception as exc:
        logging.warning(f"EC-over-TW promotion step encountered an error: {exc}")

    # 7. PanicStream / TourWrangler fallback for missing recent historical setlists
    fallback_rows, fallback_shows = tourwrangler_fallback(client)
    status.fallback_setlists_collected = fallback_rows
    status.fallback_shows_filled = fallback_shows
    status.setlists_collected += fallback_rows

    try:
        today = date.today()
        window_days = int(os.environ.get("WSP_BACKUP_WINDOW_DAYS", "3"))
        window_start = today - timedelta(days=window_days)
        recent_resp = (
            client.table("wsp_shows_raw")
            .select("show_id, show_date, city, state, source_url")
            .gte("show_date", window_start.isoformat())
            .lt("show_date", today.isoformat())
            .execute()
        )
        recent_rows = recent_resp.data or []
        show_ids = [
            str(row.get("show_id")) for row in recent_rows if row.get("show_id")
        ]
        if show_ids:
            setlists_resp = (
                client.table("wsp_setlists_raw")
                .select("show_id")
                .in_("show_id", show_ids)
                .execute()
            )
            completed_ids = {
                str(row.get("show_id"))
                for row in (setlists_resp.data or [])
                if row.get("show_id")
            }
            missing_rows = [
                row
                for row in recent_rows
                if str(row.get("show_id")) not in completed_ids
            ]
            diagnostics = classify_missing_recent_setlists(client, missing_rows)
            if diagnostics:
                counts = Counter(
                    str(item.get("diagnosis", "unknown")) for item in diagnostics
                )
                logging.warning(
                    "Recent WSP missing-setlist diagnostics: %s",
                    ", ".join(
                        f"{key}={value}" for key, value in sorted(counts.items())
                    ),
                )
                for item in diagnostics[:5]:
                    logging.warning(
                        "WSP missing-setlist detail: show_id=%s show_date=%s diagnosis=%s detail=%s",
                        item.get("show_id"),
                        item.get("show_date"),
                        item.get("diagnosis"),
                        item.get("detail"),
                    )
                for item in diagnostics:
                    status.record_missing_setlist_diagnostic(
                        str(item.get("diagnosis", "unknown"))
                    )
    except Exception as exc:
        logging.warning(f"Missing-setlist diagnostic step encountered an error: {exc}")

    # 8. Log collection run
    try:
        timer.log("wsp", status=status.workflow_state())
        logging.info("Logged collection run.")
    except Exception as exc:
        logging.warning(f"Could not log collection run ({exc}).")

    # Evaluate collection status and fail if critical errors occurred
    if status.should_fail():
        error_summary = status.get_failure_summary()
        logging.error(error_summary)
        raise RuntimeError(
            "WSP collection failed with a non-degraded internal outcome "
            f"({status.outcome_code()}). Check the failure summary above for details."
        )

    if status.workflow_state() == "degraded":
        logging.warning(status.get_degraded_summary())
        return status

    # Log success summary
    success_summary = status.get_success_summary()
    logging.info(success_summary)
    logging.info("Widespread Panic data collection finished.")
    return status


def tourwrangler_fallback(client) -> tuple[int, int]:
    """Fetch missing recent historical WSP setlists from fallback sources.

    This function checks for shows in the configured backup window that are missing
    setlist data and attempts to fetch them from PanicStream first, then
    TourWrangler if PanicStream yields nothing parseable.

    Args:
        client: Supabase client instance.
    """
    try:
        today = date.today()
        window_days = int(os.environ.get("WSP_BACKUP_WINDOW_DAYS", "3"))
        window_start = today - timedelta(days=window_days)
        logging.info(
            f"Checking for missing setlists in window {window_start.isoformat()}..{today.isoformat()} (excluding today); window_days={window_days}"
        )

        recent_shows_resp = (
            client.table("wsp_shows_raw")
            .select("show_id, show_date, city, state")
            .gte("show_date", window_start.isoformat())
            .lt("show_date", today.isoformat())
            .execute()
        )
        recent_shows = recent_shows_resp.data or []
        if recent_shows:
            show_ids = [str(r.get("show_id")) for r in recent_shows if r.get("show_id")]
            if show_ids:
                setlists_resp = (
                    client.table("wsp_setlists_raw")
                    .select("show_id")
                    .in_("show_id", show_ids)
                    .execute()
                )
                with_setlists = {
                    str(r.get("show_id"))
                    for r in (setlists_resp.data or [])
                    if r.get("show_id")
                }
            else:
                with_setlists = set()

            missing = [
                r for r in recent_shows if str(r.get("show_id")) not in with_setlists
            ]
            logging.info(
                f"Found {len(missing)} recent shows with empty setlists needing backup."
            )

            backup_rows = []
            if missing:
                for rec in missing:
                    sid = str(rec.get("show_id"))
                    sdate_str = rec.get("show_date")
                    try:
                        sdate = pd.to_datetime(sdate_str).date() if sdate_str else None
                    except Exception:
                        sdate = None
                    if not sdate:
                        continue
                    city = rec.get("city")
                    state = rec.get("state")
                    rows, source_name, lookup_errors = _resolve_recent_wsp_fallback(
                        sdate, sid, city, state
                    )
                    for error in lookup_errors:
                        logging.warning(
                            "%s for show_id=%s (%s)",
                            error,
                            sid,
                            sdate_str,
                        )
                    if rows:
                        backup_rows.extend(rows)
                        logging.info(
                            "%s provided %s rows for show_id=%s (%s).",
                            _format_fallback_source(source_name),
                            len(rows),
                            sid,
                            sdate_str,
                        )

            if backup_rows:
                backup_df = pd.DataFrame(backup_rows)
                has_source_col = _setlist_table_has_source_column()
                if has_source_col:
                    backup_df["source"] = backup_df.get("source", "panicstream")
                elif "source" in backup_df.columns:
                    backup_df = backup_df.drop(columns=["source"])

                backup_df["source_hash"] = backup_df.apply(
                    lambda row: compute_source_hash(row.to_dict()), axis=1
                )

                validate_and_upsert_dataframe(
                    table_name="wsp_setlists_raw",
                    df=backup_df,
                    conflict_columns=["show_id", "set_number", "song_position"],
                    required_columns=["set_number", "song_position"],
                )
                logging.info(
                    "Upserted %s recent fallback setlist rows.",
                    len(backup_df),
                )
                return len(backup_df), backup_df["show_id"].astype(str).nunique()
        return 0, 0
    except Exception as exc:
        logging.warning(f"Recent fallback step encountered an error: {exc}")
        return 0, 0
