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
import re
import unicodedata
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
# A table where more than this share of stored shows has no upstream setlist is
# treated as a blind sweep (matching/collection broken), not a clean result.
MAX_NOT_IN_UPSTREAM_RATIO = 0.5

# Comparison tuple: (set_number, position, song_name, is_segue); song_name is the
# canonical comparison key (see canonical_song).
TUPLE_FIELDS = ("set_number", "position", "song_name", "is_segue")
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
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        """Counts of stored shows compared vs skipped, by skip reason."""
        by_reason = Counter(item["reason"] for item in self.skipped)
        return {
            "stored_shows": self.records_checked,
            "compared": self.records_checked - len(self.skipped),
            "skipped": len(self.skipped),
            "skipped_by_reason": dict(by_reason),
            "not_in_upstream_ratio": (
                round(by_reason["not_in_upstream"] / self.records_checked, 3)
                if self.records_checked
                else 0.0
            ),
        }

    def is_blind(self) -> bool:
        return self.summary()["not_in_upstream_ratio"] > MAX_NOT_IN_UPSTREAM_RATIO

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary(),
            "band": self.band,
            "table_name": self.table_name,
            "records_checked": self.records_checked,
            "corrections_found": self.corrections_found,
            "corrections_applied": self.corrections_applied,
            "errors": self.errors,
            "warnings": self.warnings,
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
    return lambda row: _normalize_bool(row.get(column))


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


# Encores are stored as "E"/"E2"/"Encore 1" by scrapers and as 99 by the wsp
# (and eggy) normalizers, so every spelling compares as one label. Positions
# still distinguish songs across multiple encores.
ENCORE_LABEL = "E"
ENCORE_SET_NUMBER = 99
_ENCORE_TEXT = re.compile(r"E\d*|ENCORE\s*\d*")


def _to_int(value: Any) -> Optional[int]:
    """Parse ints, integral floats and float-stringified ints ("1.0")."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip())
    except ValueError:
        return None
    if number != number or not number.is_integer():  # NaN or fractional
        return None
    return int(number)


def _normalize_set(value: Any) -> Optional[str]:
    """Canonical set label: numeric sets as "1"/"2"; others stripped, upper-cased.

    Stored rows may hold float-stringified sets ("1.0") while upstream rows
    carry ints, so both sides must pass through this one function.
    """
    if value is None:
        return None
    as_int = _to_int(value)
    if as_int == ENCORE_SET_NUMBER:
        return ENCORE_LABEL
    if as_int is not None:
        return str(as_int)
    text = str(value).strip().upper()
    if not text or text in {"NAN", "NONE", "<NA>"}:
        return None
    return ENCORE_LABEL if _ENCORE_TEXT.fullmatch(text) else text


def _normalize_position(value: Any) -> Optional[int]:
    return _to_int(value)


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "t", "1", "yes", "y"}
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(value)


_TRAILING_SEGUE = re.compile(r"\s*(?:->|>)\s*$")


def canonical_song(name: Any) -> Tuple[str, bool]:
    """Return ``(comparison key, trailing_segue)`` for a raw song name.

    The key is NFKC-normalized, casefolded and reduced to letters and digits,
    so quotes ("I\u2019m" vs "I'm"), dashes, spacing, periods and other
    punctuation never count as a difference. Trailing ``>`` / ``->`` markers
    are removed and reported as a segue. Raw names are never altered; this is
    only used to compare.
    """
    text = unicodedata.normalize("NFKC", str(name or "")).strip()
    stripped = _TRAILING_SEGUE.sub("", text)
    segue = stripped != text and bool(stripped)
    key = re.sub(r"[\W_]+", "", (stripped if segue else text).casefold())
    return key, segue


def row_to_tuple(band: str, row: Dict[str, Any]) -> SongTuple:
    """Normalize a stored or upstream row to ``(set, position, song, segue)``."""
    schema = SETLIST_SCHEMAS[band]
    song, name_segue = canonical_song(row.get(schema.song_column))
    return (
        _normalize_set(row.get(schema.set_column)),
        _normalize_position(row.get(schema.position_column)),
        song,
        _normalize_bool(schema.segue(row)) or name_segue,
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
    schema = SETLIST_SCHEMAS[band]
    raw_names: Dict[Tuple[str, SongTuple], str] = {}

    def keyed(side: str, rows: List[Dict[str, Any]]) -> Counter:
        items = []
        for row in rows:
            item = row_to_tuple(band, row)
            raw_names.setdefault(
                (side, item), str(row.get(schema.song_column) or "").strip()
            )
            items.append(item)
        return Counter(items)

    stored = keyed("stored", stored_rows)
    upstream = keyed("upstream", upstream_rows)
    stored_only = sorted((stored - upstream).elements(), key=_sort_key)
    upstream_only = sorted((upstream - stored).elements(), key=_sort_key)

    def describe(item: SongTuple, side: str) -> Dict[str, Any]:
        return {
            "set_number": item[0],
            "position": item[1],
            "song_name": raw_names[(side, item)],
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
            match = candidates.pop(0)
            changed.append(
                {
                    "from": describe(item, "stored"),
                    "to": describe(match, "upstream"),
                    "fields": [
                        name for name, a, b in zip(TUPLE_FIELDS, item, match) if a != b
                    ],
                }
            )
        else:
            removed.append(describe(item, "stored"))
    for leftovers in upstream_by_slot.values():
        added.extend(describe(item, "upstream") for item in leftovers)
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


def fetch_stored_shows(
    band: str,
    since: date,
    until: date,
    client=None,
    columns: Iterable[str] = (),
) -> List[Dict[str, Any]]:
    """Return ``{band}_shows_raw`` rows (id column plus ``columns``) in a window."""
    client = client or get_supabase_client()
    id_col = get_repo_band_id_column(band)
    select = ", ".join(dict.fromkeys([id_col, *columns]))
    shows_table = f"{band}_shows_raw"
    return _fetch_all(
        lambda: client.table(shows_table)
        .select(select)
        .gte("show_date", since.isoformat())
        .lte("show_date", until.isoformat())
        .order(id_col),
        shows_table,
    )


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
    setlists_table = f"{band}_setlists_raw"

    shows = fetch_stored_shows(band, since, until, client=client)
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

# Bands whose collect_setlists takes show_ids (the rest take show dicts and are
# matched to stored shows by natural key, see NATURAL_KEY_KINDS).
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
        collector = getattr(importlib.import_module(module_path), class_name)()
        # WSP's collector skips any show that already has stored setlist rows,
        # which would make every comparison come back empty.
        if band == "wsp":
            collector.skip_existing_setlists = False
        return collector
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


# Columns the table fills itself (identity ``id``, ``created_at``/``updated_at``
# defaults). Normalizers emit them as None, and the replace_show_setlist RPC
# inserts every key of the first row explicitly, so a null here violates NOT
# NULL instead of falling back to the default. They are never sent.
SERVER_MANAGED_COLUMNS = frozenset({"id", "created_at", "updated_at"})


def _replacement_payload(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build the ``p_rows`` payload: no server-managed keys, JSON-safe values."""
    return [
        {k: _jsonable(v) for k, v in row.items() if k not in SERVER_MANAGED_COLUMNS}
        for row in rows
    ]


# Bands whose show ids are assigned locally at normalization time, so upstream
# shows carry no stored ``show_id``. They are matched to stored shows by these
# natural keys, tried in order (mirrors each band's collection reconciliation:
# billy by source_uuid/date+venue, um by source_url, wsp by source_url then
# date+venue).
NATURAL_KEY_KINDS: Dict[str, Tuple[str, ...]] = {
    "billy": ("source_uuid", "date_venue"),
    "um": ("source_url",),
    "wsp": ("source_url", "date_venue"),
}

# Columns each natural-key kind reads from a show row.
KEY_KIND_COLUMNS: Dict[str, Tuple[str, ...]] = {
    "source_uuid": ("source_uuid",),
    "source_url": ("source_url",),
    "date_venue": ("show_date", "venue_name"),
}

# Columns that really exist on each band's ``*_shows_raw`` table (see
# supabase/migrations). Only billy has ``source_uuid``; selecting a column a
# table lacks fails the whole sweep.
SHOWS_TABLE_COLUMNS: Dict[str, frozenset] = {
    "billy": frozenset(
        {"show_id", "show_date", "venue_name", "source_url", "source_uuid"}
    ),
    "um": frozenset({"show_id", "show_date", "venue_name", "source_url"}),
    "wsp": frozenset({"show_id", "show_date", "venue_name", "source_url"}),
}


def show_match_columns(band: str) -> Tuple[str, ...]:
    """Columns to select from the band's shows table for natural-key matching."""
    return tuple(
        dict.fromkeys(c for k in NATURAL_KEY_KINDS[band] for c in KEY_KIND_COLUMNS[k])
    )


# Bands whose upstream source only exposes recent history (billy: BillyBase
# lists ~11 of 152 stored shows). A high not_in_upstream share is structural
# there, so the blind-sweep guard only warns, and still fails if nothing at all
# could be compared.
LIMITED_UPSTREAM_HISTORY = frozenset({"billy"})


def _venue_key(name: Any) -> str:
    key = re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).strip()
    return re.sub(r"^the ", "", key).replace(" ", "")


def _natural_key(kind: str, show: Dict[str, Any]) -> Optional[Tuple[Any, ...]]:
    if kind == "date_venue":
        show_date = str(show.get("show_date") or "")[:10]
        venue = _venue_key(show.get("venue_name"))
        return (kind, show_date, venue) if show_date and venue else None
    value = str(show.get(kind) or "").strip()
    return (kind, value) if value else None


def match_upstream_shows(
    band: str,
    upstream_shows: Iterable[Dict[str, Any]],
    stored_shows: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return upstream shows re-keyed with the STORED show id.

    A key that matches more than one stored show is ambiguous and ignored; an
    upstream show matching no stored show is dropped. Each stored show is
    claimed by at most one upstream show.
    """
    id_col = get_repo_band_id_column(band)
    kinds = NATURAL_KEY_KINDS[band]
    index: Dict[Tuple[Any, ...], set] = defaultdict(set)
    stored_id: Dict[str, Any] = {}
    for stored in stored_shows:
        if stored.get(id_col) is None:
            continue
        stored_id[str(stored[id_col])] = stored[id_col]
        for kind in kinds:
            key = _natural_key(kind, stored)
            if key:
                index[key].add(str(stored[id_col]))

    matched: List[Dict[str, Any]] = []
    claimed: set = set()
    for show in upstream_shows:
        for kind in kinds:
            key = _natural_key(kind, show)
            ids = index.get(key, set()) if key else set()
            if len(ids) == 1:
                (sid,) = ids
                if sid not in claimed:
                    claimed.add(sid)
                    matched.append({**show, id_col: stored_id[sid]})
                break
    return matched


def fetch_upstream_setlists(
    band: str,
    stored_show_ids: Iterable[str],
    since: date,
    until: date,
    collector=None,
    normalizer: Optional[Callable[[List[Dict[str, Any]]], pd.DataFrame]] = None,
    stored_shows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Fetch upstream setlists for the stored shows, as DB-shaped rows by show id.

    ``stored_shows`` (rows with ``show_match_columns(band)``) is required for bands
    outside the show-id collectors: their upstream shows are mapped to stored
    show ids by natural key.
    """
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
            to_process = match_upstream_shows(band, shows, stored_shows or [])
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
                    {
                        "p_band": band,
                        "p_show_id": show_id,
                        "p_rows": _replacement_payload(upstream_rows),
                    },
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
            stored_shows = (
                fetch_stored_shows(
                    band, since, until, client=client, columns=show_match_columns(band)
                )
                if band in NATURAL_KEY_KINDS
                else None
            )
            upstream = fetch_upstream_setlists(
                band,
                stored.keys(),
                since,
                until,
                collector=collector,
                normalizer=normalizer,
                stored_shows=stored_shows,
            )
            result = detect_setlist_corrections(
                band, upstream, stored, dry_run=dry_run, client=client
            )
            if result.is_blind():
                summary = result.summary()
                message = (
                    f"{summary['skipped_by_reason']['not_in_upstream']}"
                    f" of {summary['stored_shows']} stored shows had no upstream "
                    f"setlist (> {MAX_NOT_IN_UPSTREAM_RATIO:.0%})"
                )
                if band not in LIMITED_UPSTREAM_HISTORY:
                    result.errors.append(
                        f"Blind sweep: {message}; upstream matching or "
                        "collection is likely broken."
                    )
                elif summary["compared"] == 0:
                    result.errors.append(f"Blind sweep: {message}; nothing compared.")
                else:
                    result.warnings.append(
                        f"Limited upstream history for {band}: {message}; "
                        f"compared {summary['compared']}."
                    )
            results[table_name] = result
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
            summary = result.summary()
            lines.append(
                f"  Compared: {summary['compared']} of {summary['stored_shows']};"
                f" skipped {summary['skipped']} {summary['skipped_by_reason']}"
            )

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
