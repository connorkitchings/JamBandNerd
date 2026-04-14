"""Provides high-level database operations."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

import pandas as pd

from .connection import get_supabase_client
from .validation import coerce_df_types, validate_dataframe_against_table

logger = logging.getLogger(__name__)
_schema_cache: dict[str, List[Dict[str, Any]]] = {}


def _clean_record_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _clean_record_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_record_value(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass

    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            return value.item()
        except Exception:
            pass

    return value


def _dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        cleaned = {
            str(key): _clean_record_value(value)
            for key, value in row.items()
            if not (
                key in {"created_at", "updated_at"}
                and value is not None
                and _clean_record_value(value) is None
            )
        }
        cleaned = {
            key: value
            for key, value in cleaned.items()
            if not (key in {"created_at", "updated_at"} and value is None)
        }
        records.append(cleaned)
    return records


def _format_validation_warnings(
    *, table_name: str, extra_columns: Sequence[str], type_mismatches: Sequence[Any]
) -> None:
    if extra_columns:
        logger.warning("%s: ignoring extra columns %s", table_name, list(extra_columns))
    if type_mismatches:
        logger.warning(
            "%s: %s column(s) still look mismatched after coercion",
            table_name,
            len(type_mismatches),
        )


def dedupe_dataframe_on_conflict(
    df: pd.DataFrame,
    *,
    conflict_columns: Sequence[str],
    table_name: str,
) -> pd.DataFrame:
    """Drop duplicate conflict-key rows before issuing a batched upsert."""
    if df.empty:
        return df

    missing_columns = [
        column for column in conflict_columns if column not in df.columns
    ]
    if missing_columns:
        raise RuntimeError(
            f"{table_name} missing conflict columns: {', '.join(missing_columns)}"
        )

    deduped = df.drop_duplicates(subset=list(conflict_columns), keep="last").copy()
    removed = len(df) - len(deduped)
    if removed > 0:
        logger.warning(
            "%s: removed %s duplicate row(s) for conflict columns %s before upsert",
            table_name,
            removed,
            list(conflict_columns),
        )

    duplicate_mask = deduped.duplicated(subset=list(conflict_columns), keep=False)
    if duplicate_mask.any():
        sample = (
            deduped.loc[duplicate_mask, list(conflict_columns)]
            .head(5)
            .to_dict(orient="records")
        )
        raise RuntimeError(
            f"{table_name} still contains duplicate conflict keys after in-memory "
            f"dedupe: {sample}"
        )

    return deduped


def prepare_dataframe_for_upsert(
    table_name: str,
    df: pd.DataFrame,
    *,
    required_columns: Optional[Sequence[str]] = None,
    skip_validation: bool = False,
) -> pd.DataFrame:
    """Prepare a DataFrame for safe Supabase upserts."""
    prepared = df.copy()
    if prepared.empty:
        return prepared

    if required_columns:
        missing_required = [
            column for column in required_columns if column not in prepared
        ]
        if missing_required:
            joined = ", ".join(missing_required)
            raise RuntimeError(f"{table_name} missing expected columns: {joined}")

    schema = get_table_schema(table_name)
    if not schema or skip_validation:
        return prepared

    prepared = coerce_df_types(prepared, schema)
    report = validate_dataframe_against_table(prepared, table_name, schema)
    if report.missing_columns or report.nullable_violations:
        problems: list[str] = []
        if report.missing_columns:
            problems.append(f"missing columns: {report.missing_columns}")
        if report.nullable_violations:
            problems.append(f"nullable violations: {report.nullable_violations}")
        joined = "; ".join(problems)
        raise RuntimeError(f"{table_name} failed validation: {joined}")

    _format_validation_warnings(
        table_name=table_name,
        extra_columns=report.extra_columns,
        type_mismatches=report.type_mismatches,
    )
    return prepared


def validate_and_upsert_dataframe(
    table_name: str,
    df: pd.DataFrame,
    conflict_columns: List[str],
    *,
    required_columns: Optional[Sequence[str]] = None,
    skip_validation: bool = False,
    chunk_size: int = 500,
) -> None:
    """Validate a DataFrame against live schema and upsert the prepared rows."""
    prepared = prepare_dataframe_for_upsert(
        table_name,
        df,
        required_columns=required_columns,
        skip_validation=skip_validation,
    )
    if prepared.empty:
        return
    prepared = dedupe_dataframe_on_conflict(
        prepared,
        conflict_columns=conflict_columns,
        table_name=table_name,
    )
    upsert_dataframe(
        table_name=table_name,
        df=prepared,
        conflict_columns=conflict_columns,
        chunk_size=chunk_size,
    )


def fetch_existing_ids(
    table_name: str,
    id_column: str,
    since: Optional[str] = None,
    date_column: str = "created_at",
) -> Set[Any]:
    """
    Fetches existing IDs from a table to prevent duplicate entries.

    Args:
        table_name: The name of the table to query.
        id_column: The name of the column containing the IDs.
        since: An optional date string to filter records.
        date_column: The name of the date column to filter on (defaults to 'created_at').

    Returns:
        A set of existing IDs.
    """
    client = get_supabase_client()
    query = client.table(table_name).select(id_column)
    if since:
        query = query.gte(date_column, since)

    response = query.execute()

    if response.data:
        return {item[id_column] for item in response.data}
    return set()


def bulk_insert_dataframe(
    table_name: str, df: pd.DataFrame, chunk_size: int = 500
) -> None:
    """
    Inserts a DataFrame into a Supabase table in chunks.

    Args:
        table_name: The name of the table to insert into.
        df: The DataFrame to insert.
        chunk_size: The number of rows to insert per chunk.
    """
    client = get_supabase_client()
    records = _dataframe_to_records(df)

    for i in range(0, len(records), chunk_size):
        chunk = records[i : i + chunk_size]
        client.table(table_name).insert(chunk).execute()


def upsert_dataframe(
    table_name: str,
    df: pd.DataFrame,
    conflict_columns: List[str],
    chunk_size: int = 500,
) -> None:
    """
    Upserts a DataFrame into a Supabase table in chunks.

    Args:
        table_name: The name of the table to upsert into.
        df: The DataFrame to upsert.
        conflict_columns: A list of column names to use for conflict resolution.
        chunk_size: The number of rows to upsert per chunk.
    """
    client = get_supabase_client()
    records = _dataframe_to_records(df)

    for i in range(0, len(records), chunk_size):
        chunk = records[i : i + chunk_size]
        client.table(table_name).upsert(
            chunk, on_conflict=",".join(conflict_columns)
        ).execute()


def _cleanup_stale_prediction_songs(
    *,
    band: str,
    model_version: str,
    max_age_days: int = 7,
    table_name: str = "prediction_songs",
) -> None:
    """Delete stale prediction_songs rows older than *max_age_days*.

    Never deletes the most recently written projection for a given
    ``(band, model_version)`` so that the website always has data to render.
    """
    from datetime import datetime, timedelta, timezone

    client = get_supabase_client()

    latest_resp = (
        client.table(table_name)
        .select("reference_date, predicted_at")
        .eq("band", band)
        .eq("model_version", model_version)
        .order("predicted_at", desc=True)
        .order("reference_date", desc=True)
        .limit(1)
        .execute()
    )
    latest_rows = latest_resp.data or []
    if not latest_rows:
        return
    latest_ref = latest_rows[0].get("reference_date")

    all_rows = (
        client.table(table_name)
        .select("reference_date, predicted_at")
        .eq("band", band)
        .eq("model_version", model_version)
        .execute()
    )
    rows = all_rows.data or []
    if not rows:
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    stale_refs: set[str] = set()
    for row in rows:
        reference_date = row.get("reference_date")
        predicted_at = row.get("predicted_at")
        if not reference_date or reference_date == latest_ref or not predicted_at:
            continue
        parsed = datetime.fromisoformat(predicted_at.replace("Z", "+00:00"))
        if parsed < cutoff:
            stale_refs.add(reference_date)

    deleted = 0
    for stale_ref in sorted(stale_refs):
        resp = (
            client.table(table_name)
            .delete()
            .eq("band", band)
            .eq("model_version", model_version)
            .eq("reference_date", stale_ref)
            .execute()
        )
        deleted += len(resp.data or [])
    if deleted:
        logger.info(
            "Cleaned %d stale prediction_songs rows for %s/%s (cutoff=%s)",
            deleted,
            band,
            model_version,
            cutoff.isoformat(),
        )


def replace_prediction_projection(
    *,
    band: str,
    model_slug: str,
    model_version: str,
    reference_date: str,
    predicted_at: str,
    predictions: Sequence[dict[str, Any]],
    table_name: str = "prediction_songs",
) -> None:
    """Replace the per-song projection for a canonical prediction row.

    ``prediction_songs`` is a derived projection of the canonical unified
    ``predictions`` table. It is fully rebuildable via
    ``scripts/rebuild_prediction_songs.py``.

    The delete-then-insert pattern prevents duplicate rows for the *current*
    ``reference_date`` but does not remove rows from older dates.  Stale rows
    are cleaned up by ``_cleanup_stale_prediction_songs()`` which is called
    after each projection write.
    """
    client = get_supabase_client()

    (
        client.table(table_name)
        .delete()
        .eq("band", band)
        .eq("model_version", model_version)
        .eq("reference_date", reference_date)
        .execute()
    )

    if not predictions:
        _cleanup_stale_prediction_songs(band=band, model_version=model_version)
        return

    rows = [
        {
            "band": band,
            "model_slug": model_slug,
            "model_version": model_version,
            "reference_date": reference_date,
            "predicted_at": predicted_at,
            "rank": prediction["rank"],
            "song_name": prediction["song_name"],
            "top_k": len(predictions),
            "prediction_payload": prediction,
        }
        for prediction in predictions
    ]
    bulk_insert_dataframe(table_name, pd.DataFrame(rows))

    _cleanup_stale_prediction_songs(band=band, model_version=model_version)


def upsert_historical_prediction_run(
    *,
    band: str,
    model_slug: str,
    model_version: str,
    reference_date: str,
    target_show_id: str,
    target_show_date: str,
    generated_at: str,
    predictions: Sequence[dict[str, Any]],
    actual_songs: Sequence[str],
    table_name: str = "historical_prediction_runs",
) -> int:
    """Upsert a historical scored prediction run and return its stable id."""
    client = get_supabase_client()
    row = {
        "band": band,
        "model_slug": model_slug,
        "model_version": model_version,
        "run_type": "backtest",
        "reference_date": reference_date,
        "target_show_id": target_show_id,
        "target_show_date": target_show_date,
        "generated_at": generated_at,
        "predictions": list(predictions),
        "top_k": len(predictions),
        "actual_songs": list(actual_songs),
        "actual_song_count": len(actual_songs),
    }
    cleaned_row = {str(key): _clean_record_value(value) for key, value in row.items()}

    response = (
        client.table(table_name)
        .upsert(
            cleaned_row,
            on_conflict="band,model_slug,model_version,reference_date,target_show_id",
        )
        .execute()
    )
    data = response.data or []
    if data:
        run_id = data[0].get("id")
        if run_id is not None:
            return int(run_id)

    existing = (
        client.table(table_name)
        .select("id")
        .eq("band", band)
        .eq("model_slug", model_slug)
        .eq("model_version", model_version)
        .eq("reference_date", reference_date)
        .eq("target_show_id", target_show_id)
        .limit(1)
        .execute()
    )
    existing_rows = existing.data or []
    if not existing_rows or existing_rows[0].get("id") is None:
        raise RuntimeError(
            "Failed to resolve historical_prediction_runs.id after upsert"
        )
    return int(existing_rows[0]["id"])


def fetch_historical_prediction_run(
    *,
    band: str,
    model_slug: str,
    model_version: str,
    reference_date: str,
    target_show_id: str,
    table_name: str = "historical_prediction_runs",
) -> dict[str, Any] | None:
    """Fetch one historical scored run by its unique context."""
    client = get_supabase_client()
    response = (
        client.table(table_name)
        .select("*")
        .eq("band", band)
        .eq("model_slug", model_slug)
        .eq("model_version", model_version)
        .eq("reference_date", reference_date)
        .eq("target_show_id", target_show_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def fetch_latest_prediction_songs(
    *, band: str, model_slug: str, table_name: str = "prediction_songs"
) -> list[dict[str, Any]]:
    """Fetch the latest projected songs for a band/model ordered by rank."""
    client = get_supabase_client()
    latest_response = (
        client.table(table_name)
        .select("reference_date, model_version")
        .eq("band", band)
        .eq("model_slug", model_slug)
        .order("predicted_at", desc=True)
        .order("reference_date", desc=True)
        .order("rank")
        .limit(1)
        .execute()
    )
    latest_rows = latest_response.data or []
    if not latest_rows:
        return []

    latest = latest_rows[0]
    response = (
        client.table(table_name)
        .select("*")
        .eq("band", band)
        .eq("model_slug", model_slug)
        .eq("model_version", latest["model_version"])
        .eq("reference_date", latest["reference_date"])
        .order("rank")
        .execute()
    )
    return response.data or []


def fetch_prediction_songs_for_date(
    *,
    band: str,
    model_slug: str,
    reference_date: str,
    table_name: str = "prediction_songs",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch projected songs for an exact band/model/reference_date ordered by rank."""
    client = get_supabase_client()
    query = (
        client.table(table_name)
        .select("*")
        .eq("band", band)
        .eq("model_slug", model_slug)
        .eq("reference_date", reference_date)
        .order("rank")
    )
    if limit is not None:
        query = query.limit(limit)
    response = query.execute()
    return response.data or []


def get_table_schema(
    table_name: str, *, use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Fetch the schema for a given table from Supabase via RPC, if available.

    This expects a Postgres function (RPC) named `get_table_schema(p_table_name text)`
    that returns rows with at least: column_name, data_type, is_nullable.

    If the RPC is not present or fails, returns an empty list so callers can
    fall back to local expected schemas.

    Args:
        table_name: The name of the table whose schema to retrieve.

    Returns:
        A list of dictionaries describing columns, or an empty list on failure.
    """
    if use_cache and table_name in _schema_cache:
        return _schema_cache[table_name]

    client = get_supabase_client()
    try:
        response = client.rpc(
            "get_table_schema", {"p_table_name": table_name}
        ).execute()
        schema = response.data or []
        if use_cache:
            _schema_cache[table_name] = schema
        return schema
    except Exception:
        # RPC not available or other error; let validation layer use local expectations
        return []


def fetch_rows_by_column_values(
    table_name: str,
    *,
    select_columns: Iterable[str],
    filter_column: str,
    values: Iterable[Any],
    chunk_size: int = 200,
) -> list[dict[str, Any]]:
    """Fetch selected rows for a set of candidate values using batched IN queries."""
    client = get_supabase_client()
    unique_values = list(dict.fromkeys(values))
    if not unique_values:
        return []

    selected = ",".join(select_columns)
    rows: list[dict[str, Any]] = []
    for start in range(0, len(unique_values), chunk_size):
        chunk = unique_values[start : start + chunk_size]
        response = (
            client.table(table_name)
            .select(selected)
            .in_(filter_column, list(chunk))
            .execute()
        )
        rows.extend(response.data or [])
    return rows


def fetch_existing_values(
    table_name: str,
    *,
    value_column: str,
    candidate_values: Iterable[Any],
    chunk_size: int = 200,
) -> set[str]:
    """Return the existing subset of candidate values from a table."""
    rows = fetch_rows_by_column_values(
        table_name,
        select_columns=[value_column],
        filter_column=value_column,
        values=candidate_values,
        chunk_size=chunk_size,
    )
    existing: set[str] = set()
    for row in rows:
        value = row.get(value_column)
        if value is not None:
            existing.add(str(value))
    return existing


def check_prediction_staleness(
    band: str,
    model_version: str,
    max_age_hours: int = 48,
) -> tuple[bool, Optional[datetime]]:
    """Check if predictions for a band/model are stale.

    Args:
        band: Band name (e.g., 'goose')
        model_version: Model version (e.g., 'notebook_v1', 'ckplus_v1')
        max_age_hours: Maximum allowed staleness in hours

    Returns:
        Tuple of (is_fresh, last_predicted_at)
        - is_fresh: True if predictions are within max_age_hours
        - last_predicted_at: Timestamp of last prediction, or None if no predictions exist
    """
    from datetime import timezone as tz

    client = get_supabase_client()

    try:
        response = (
            client.table("predictions")
            .select("predicted_at")
            .eq("band", band)
            .eq("model_version", model_version)
            .order("predicted_at", desc=True)
            .limit(1)
            .execute()
        )

        if not response.data:
            return False, None

        last_predicted_at_str = response.data[0].get("predicted_at")
        if not last_predicted_at_str:
            return False, None

        last_predicted_at = datetime.fromisoformat(
            last_predicted_at_str.replace("Z", "+00:00")
        )
        now = datetime.now(tz.utc)
        age_hours = (now - last_predicted_at).total_seconds() / 3600
        is_fresh = age_hours <= max_age_hours

        if not is_fresh:
            logger.warning(
                f"Predictions for {band}/{model_version} are stale: "
                f"{age_hours:.1f}h old (max: {max_age_hours}h)"
            )

        return is_fresh, last_predicted_at

    except Exception as e:
        logger.error(
            f"Error checking prediction staleness for {band}/{model_version}: {e}"
        )
        return False, None


def fetch_active_bands() -> list[dict[str, Any]]:
    """Fetch active bands from the bands registry table."""
    try:
        client = get_supabase_client()
        response = client.table("bands").select("*").eq("is_active", True).execute()
        return response.data or []
    except Exception as e:
        logger.warning(f"Failed to fetch active bands from registry: {e}")
        return []
