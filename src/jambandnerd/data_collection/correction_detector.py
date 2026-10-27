"""Correction detection for upstream setlist changes.

Compares the setlists stored in ``{band}_setlists_raw`` with a fresh upstream
fetch and, when not in dry-run mode, replaces a changed show's setlist through
the ``replace_show_setlist`` Postgres function (a single transaction with a
shrink guard). Used by the weekly correction sweep workflow.

Safety properties:

* Query failures raise ``CorrectionFetchError``; they are never swallowed into
  an empty result.
* A show is skipped when upstream returns fewer than ``MIN_UPSTREAM_ROWS``
  rows, so an upstream blip cannot wipe a good setlist.
* Writes go through one atomic RPC; there is no client-side delete/insert.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from src.jambandnerd.config.bands import SUPPORTED_BANDS, get_repo_band_id_column
from src.jambandnerd.db.connection import get_supabase_client

logger = logging.getLogger(__name__)

# Upstream results with fewer rows than this are treated as a failed/partial
# fetch rather than a real setlist.
MIN_UPSTREAM_ROWS = 3
PAGE_SIZE = 1000
ID_CHUNK_SIZE = 100
REPLACE_RPC = "replace_show_setlist"

# Comparison tuple: (set_number, position, song_name, is_segue)
SongTuple = Tuple[Optional[str], Optional[int], str, bool]


class CorrectionFetchError(RuntimeError):
    """Raised when stored or upstream data cannot be fetched."""


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
    skipped: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "band": self.band,
            "table_name": self.table_name,
            "records_checked": self.records_checked,
            "corrections_found": self.corrections_found,
            "corrections_applied": self.corrections_applied,
            "errors": self.errors,
            "details": self.details,
            "skipped": self.skipped,
        }


def compute_record_checksum(record: Dict[str, Any]) -> str:
    """Compute a deterministic checksum for a record.

    Excludes metadata fields like created_at/updated_at.
    """
    excluded_fields = {"created_at", "updated_at", "source_hash", "id"}

    cleaned = {}
    for key, value in record.items():
        if key in excluded_fields:
            continue
        cleaned[key] = None if value is None else str(value)

    payload = json.dumps(cleaned, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Per-band setlist column mapping
# ---------------------------------------------------------------------------


def _phish_is_segue(row: Dict[str, Any]) -> bool:
    return str(row.get("transition") or "").strip() in {">", "->"}


def _column_segue(column: str) -> Callable[[Dict[str, Any]], bool]:
    return lambda row: bool(row.get(column))


def _no_segue(row: Dict[str, Any]) -> bool:
    return False


@dataclass(frozen=True)
class SetlistSchema:
    """Column names of a band's ``*_setlists_raw`` table."""

    pk_column: str  # unique column used for stable pagination
    set_column: str
    position_column: str
    song_column: str = "song_name"
    segue: Callable[[Dict[str, Any]], bool] = _no_segue


SETLIST_SCHEMAS: Dict[str, SetlistSchema] = {
    "goose": SetlistSchema("id", "set_number", "song_position"),
    "eggy": SetlistSchema("id", "set_number", "song_position"),
    "phish": SetlistSchema(
        "api_unique_id", "set_number", "position", segue=_phish_is_segue
    ),
    "wsp": SetlistSchema(
        "id", "set_number", "song_position", segue=_column_segue("is_segue")
    ),
    "billy": SetlistSchema(
        "id", "set_number", "song_position", segue=_column_segue("is_segue")
    ),
    "um": SetlistSchema(
        "id", "set_label", "show_position", segue=_column_segue("is_segue")
    ),
}


def _normalize_set(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None


def _normalize_position(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def row_to_tuple(band: str, row: Dict[str, Any]) -> SongTuple:
    """Normalize a stored or upstream row to ``(set, position, song, segue)``."""
    schema = SETLIST_SCHEMAS[band]
    return (
        _normalize_set(row.get(schema.set_column)),
        _normalize_position(row.get(schema.position_column)),
        str(row.get(schema.song_column) or "").strip(),
        bool(schema.segue(row)),
    )


def _sort_key(item: SongTuple) -> Tuple[str, int, str, bool]:
    return (item[0] or "", item[1] if item[1] is not None else -1, item[2], item[3])


def diff_setlists(
    band: str,
    stored_rows: List[Dict[str, Any]],
    upstream_rows: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Compare two setlists as sorted tuple multisets.

    Returns ``added`` (upstream only), ``removed`` (stored only) and
    ``changed`` (same set and position, different song or segue flag).
    All three are empty when the setlists match.
    """
    stored = Counter(row_to_tuple(band, r) for r in stored_rows)
    upstream = Counter(row_to_tuple(band, r) for r in upstream_rows)
    stored_only = sorted((stored - upstream).elements(), key=_sort_key)
    upstream_only = sorted((upstream - stored).elements(), key=_sort_key)

    def describe(item: SongTuple) -> Dict[str, Any]:
        return {
            "set_number": item[0],
            "position": item[1],
            "song_name": item[2],
            "is_segue": item[3],
        }

    upstream_by_slot: Dict[Tuple[Optional[str], Optional[int]], List[SongTuple]] = (
        defaultdict(list)
    )
    for item in upstream_only:
        upstream_by_slot[(item[0], item[1])].append(item)

    added: List[Dict[str, Any]] = []
    removed: List[Dict[str, Any]] = []
    changed: List[Dict[str, Any]] = []
    for item in stored_only:
        candidates = upstream_by_slot.get((item[0], item[1]))
        if candidates:
            changed.append({"from": describe(item), "to": describe(candidates.pop(0))})
        else:
            removed.append(describe(item))
    for leftovers in upstream_by_slot.values():
        added.extend(describe(item) for item in leftovers)
    added.sort(key=lambda d: (d["set_number"] or "", d["position"] or 0))

    return {"added": added, "removed": removed, "changed": changed}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def _sanitize_error(exc: BaseException) -> str:
    """Short error text safe for logs and reports (no payloads, bounded)."""
    code = getattr(exc, "code", None)
    message = str(getattr(exc, "message", None) or exc)[:200]
    prefix = f"{type(exc).__name__}"
    if code:
        prefix += f" [{code}]"
    return f"{prefix}: {message}"


# ---------------------------------------------------------------------------
# Stored data
# ---------------------------------------------------------------------------


def _fetch_all(build_query: Callable[[], Any], what: str) -> List[Dict[str, Any]]:
    """Run a paginated query to exhaustion; raise on any failure."""
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        try:
            page = (
                build_query().range(offset, offset + PAGE_SIZE - 1).execute().data or []
            )
        except Exception as exc:
            raise CorrectionFetchError(
                f"Failed to fetch {what}: {_sanitize_error(exc)}"
            ) from exc
        rows.extend(page)
        if len(page) < PAGE_SIZE:
            return rows
        offset += PAGE_SIZE


def fetch_stored_setlists(
    band: str,
    since: date,
    until: date,
    client=None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Return stored setlist rows grouped by show id for a date window.

    Setlist tables have no ``show_date``; the window is resolved against
    ``{band}_shows_raw`` and the setlist rows are then fetched by show id.
    """
    client = client or get_supabase_client()
    schema = SETLIST_SCHEMAS[band]
    id_col = get_repo_band_id_column(band)
    shows_table = f"{band}_shows_raw"
    setlists_table = f"{band}_setlists_raw"

    shows = _fetch_all(
        lambda: client.table(shows_table)
        .select(id_col)
        .gte("show_date", since.isoformat())
        .lte("show_date", until.isoformat())
        .order(id_col),
        shows_table,
    )
    show_ids = sorted({str(s[id_col]) for s in shows if s.get(id_col) is not None})

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for i in range(0, len(show_ids), ID_CHUNK_SIZE):
        chunk = show_ids[i : i + ID_CHUNK_SIZE]
        rows = _fetch_all(
            lambda chunk=chunk: client.table(setlists_table)
            .select("*")
            .in_(id_col, chunk)
            .order(schema.pk_column),
            setlists_table,
        )
        for row in rows:
            grouped[str(row[id_col])].append(row)
    return dict(grouped)


# ---------------------------------------------------------------------------
# Upstream data (per-band adapters)
# ---------------------------------------------------------------------------

# Bands whose collect_setlists takes show_ids (the rest take show dicts).
_SHOW_ID_COLLECTORS = {"goose", "eggy", "phish"}

_COLLECTOR_CLASSES = {
    "goose": "src.jambandnerd.data_collection.goose.collector.GooseCollector",
    "phish": "src.jambandnerd.data_collection.phish.collector.PhishCollector",
    "eggy": "src.jambandnerd.data_collection.eggy.collector.EggyCollector",
    "um": "src.jambandnerd.data_collection.um.collector.UmCollector",
    "billy": "src.jambandnerd.data_collection.billy.collector.BillyCollector",
    "wsp": "src.jambandnerd.data_collection.wsp.collector.WSPCollector",
}


def _get_collector_for_band(band: str):
    """Instantiate the band's collector; raise if it cannot be loaded."""
    path = _COLLECTOR_CLASSES.get(band)
    if not path:
        raise CorrectionFetchError(f"No collector available for band: {band}")
    module_path, class_name = path.rsplit(".", 1)
    try:
        return getattr(importlib.import_module(module_path), class_name)()
    except Exception as exc:
        raise CorrectionFetchError(
            f"Failed to load collector for {band}: {_sanitize_error(exc)}"
        ) from exc


def _default_normalizer(band: str) -> Callable[[List[Dict[str, Any]]], pd.DataFrame]:
    module = importlib.import_module(
        f"src.jambandnerd.data_collection.{band}.normalizer"
    )
    normalize = module.normalize_setlists
    if band == "um":  # UM's normalizer takes a DataFrame
        return lambda raw: normalize(pd.DataFrame(raw))
    return normalize


def _jsonable(value: Any) -> Any:
    """Convert pandas/numpy scalars (incl. NA/NaN) into JSON-safe values."""
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def fetch_upstream_setlists(
    band: str,
    stored_show_ids: Iterable[str],
    since: date,
    until: date,
    collector=None,
    normalizer: Optional[Callable[[List[Dict[str, Any]]], pd.DataFrame]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch upstream setlists for the stored shows, as DB-shaped rows by show id."""
    collector = collector or _get_collector_for_band(band)
    id_col = get_repo_band_id_column(band)
    wanted = {str(i) for i in stored_show_ids}
    if not wanted:
        return {}

    try:
        if band in _SHOW_ID_COLLECTORS:
            raw = collector.collect_setlists(show_ids=sorted(wanted))
        else:
            shows = collector.collect_shows(start_date=since, end_date=until)
            to_process = [s for s in shows if str(s.get(id_col)) in wanted]
            raw = collector.collect_setlists(to_process) if to_process else []
        df = (normalizer or _default_normalizer(band))(list(raw or []))
    except Exception as exc:
        raise CorrectionFetchError(
            f"Failed to fetch upstream setlists for {band}: {_sanitize_error(exc)}"
        ) from exc

    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in df.to_dict("records") if len(df) else []:
        row = {k: _jsonable(v) for k, v in record.items()}
        show_id = str(row.get(id_col))
        if show_id in wanted:
            grouped[show_id].append(row)
    return dict(grouped)


# ---------------------------------------------------------------------------
# Detection and apply
# ---------------------------------------------------------------------------


def detect_setlist_corrections(
    band: str,
    upstream_by_show: Dict[str, List[Dict[str, Any]]],
    stored_by_show: Dict[str, List[Dict[str, Any]]],
    dry_run: bool = True,
    client=None,
) -> CorrectionResult:
    """Compare stored and upstream setlists per show and optionally apply fixes.

    Args:
        band: Band slug.
        upstream_by_show: DB-shaped upstream rows keyed by show id.
        stored_by_show: Stored rows keyed by show id.
        dry_run: When True, only report diffs.
        client: Supabase client (required when ``dry_run`` is False).
    """
    if band not in SETLIST_SCHEMAS:
        raise ValueError(f"Unsupported band: {band}")
    if not dry_run:
        client = client or get_supabase_client()

    result = CorrectionResult(
        band=band,
        table_name=f"{band}_setlists_raw",
        records_checked=len(stored_by_show),
        corrections_found=0,
        corrections_applied=0,
    )

    for show_id, stored_rows in sorted(stored_by_show.items()):
        upstream_rows = upstream_by_show.get(show_id)
        if upstream_rows is None:
            result.skipped.append({"show_id": show_id, "reason": "not_in_upstream"})
            continue
        if len(upstream_rows) < MIN_UPSTREAM_ROWS:
            result.skipped.append(
                {
                    "show_id": show_id,
                    "reason": "upstream_below_minimum",
                    "upstream_rows": len(upstream_rows),
                }
            )
            continue

        diff = diff_setlists(band, stored_rows, upstream_rows)
        if not (diff["added"] or diff["removed"] or diff["changed"]):
            continue

        result.corrections_found += 1
        detail: Dict[str, Any] = {
            "show_id": show_id,
            "stored_rows": len(stored_rows),
            "upstream_rows": len(upstream_rows),
            "action": "detected",
            **diff,
        }

        if not dry_run:
            try:
                client.rpc(
                    REPLACE_RPC,
                    {"p_band": band, "p_show_id": show_id, "p_rows": upstream_rows},
                ).execute()
                result.corrections_applied += 1
                detail["action"] = "applied"
                logger.info("Applied setlist correction for %s show %s", band, show_id)
            except Exception as exc:
                message = (
                    f"Failed to apply correction for {show_id}: {_sanitize_error(exc)}"
                )
                result.errors.append(message)
                detail["action"] = "error"
                detail["error"] = message
                logger.error(message)

        result.details.append(detail)

    return result


def run_correction_sweep(
    band: str,
    window_days: int = 730,
    dry_run: bool = True,
    tables: Optional[List[str]] = None,
    client=None,
    collector=None,
    normalizer=None,
) -> Dict[str, CorrectionResult]:
    """Run a correction sweep for a band.

    Failures are recorded as errors on the returned results (never an empty
    dict), so callers can fail the job on ``result.errors``.
    """
    if band not in SUPPORTED_BANDS:
        raise ValueError(f"Unsupported band: {band}")
    client = client or get_supabase_client()
    until = date.today()
    since = until - timedelta(days=window_days)
    tables = tables or ["setlists"]
    results: Dict[str, CorrectionResult] = {}

    logger.info(
        "Starting correction sweep for %s (window: %s to %s, dry_run=%s)",
        band,
        since.isoformat(),
        until.isoformat(),
        dry_run,
    )

    for table_type in tables:
        table_name = f"{band}_{table_type}_raw"
        if table_type != "setlists":
            logger.info("%s correction detection not yet implemented", table_type)
            continue
        try:
            stored = fetch_stored_setlists(band, since, until, client=client)
            if not stored:
                logger.info("No %s records found in window", table_name)
                results[table_name] = CorrectionResult(band, table_name, 0, 0, 0)
                continue
            upstream = fetch_upstream_setlists(
                band,
                stored.keys(),
                since,
                until,
                collector=collector,
                normalizer=normalizer,
            )
            results[table_name] = detect_setlist_corrections(
                band, upstream, stored, dry_run=dry_run, client=client
            )
        except Exception as exc:
            message = _sanitize_error(exc)
            logger.error("Correction sweep failed for %s: %s", table_name, message)
            results[table_name] = CorrectionResult(
                band, table_name, 0, 0, 0, errors=[message]
            )

    return results


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
                counts = ", ".join(
                    f"{len(detail.get(k, []))} {k}"
                    for k in ("added", "removed", "changed")
                )
                lines.append(f"    - Show {show_id}: {action} ({counts})")

        if result.skipped:
            lines.append(f"  Skipped shows: {len(result.skipped)}")

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
