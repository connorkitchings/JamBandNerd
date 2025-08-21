"""Dataframe validation against Supabase table schemas."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

import json
import pandas as pd


@dataclass
class TypeMismatch:
    """Represents a data type mismatch between a DataFrame and a database schema."""

    column: str
    expected_type: str
    observed_type: str
    example_values: List[Any]


@dataclass
class ValidationReport:
    """A report summarizing the validation of a DataFrame against a table schema."""

    is_valid: bool
    row_count: int
    missing_columns: List[str]
    extra_columns: List[str]
    type_mismatches: List[TypeMismatch]
    nullable_violations: List[str]


def _pg_type_to_expected(pg_type: str) -> str:
    t = pg_type.lower()
    if t.startswith("character varying") or t in {"text", "varchar"}:
        return "text"
    if t in {"integer", "int4", "bigint", "int8", "smallint", "int2"}:
        return "integer"
    if t in {"numeric", "decimal", "float", "float4", "float8", "double precision", "real"}:
        return "numeric"
    if t in {"boolean", "bool"}:
        return "boolean"
    if t in {"date"}:
        return "date"
    if "timestamp" in t:
        return "timestamp"
    if t in {"json", "jsonb"}:
        return "json"
    return "text"


def _infer_pd_type_for_validation(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "numeric"
    # We often store dates/timestamps as strings before sending to API
    # Try to guess date/timestamp by sample values
    sample = series.dropna().head(3).tolist()
    for val in sample:
        if isinstance(val, (dict, list)):
            return "json"
        if isinstance(val, str):
            # Heuristic
            if len(val) == 10 and val[4] == "-" and val[7] == "-":
                return "date"
            if "T" in val and ":" in val:
                return "timestamp"
    return "text"


def _coerce_series(series: pd.Series, expected: str) -> pd.Series:
    if expected == "integer":
        coerced = pd.to_numeric(series, errors="coerce").astype("Int64")
        return coerced
    if expected == "numeric":
        return pd.to_numeric(series, errors="coerce")
    if expected == "boolean":
        if pd.api.types.is_bool_dtype(series):
            return series
        mapping = {"true": True, "false": False, "1": True, "0": False, 1: True, 0: False}
        return series.map(lambda x: mapping.get(str(x).lower(), None))
    if expected == "date":
        dt = pd.to_datetime(series, errors="coerce").dt.date
        # Convert to ISO strings while preserving NA as None
        return dt.astype("string").where(dt.notna(), None)
    if expected == "timestamp":
        # Explicitly handle ISO-like format from API, coercing errors to NaT
        ts = pd.to_datetime(series, format="%Y-%m-%d %H:%M:%S", errors="coerce")
        return ts.astype("string").where(ts.notna(), None)
    if expected == "json":
        def _ensure_json(v: Any) -> Any:
            if isinstance(v, (dict, list)):
                return v
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except Exception:
                    return None
            return None

        return series.map(_ensure_json)
    # text/default
    def _to_text(v: Any) -> Optional[str]:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return str(v)

    return series.map(_to_text)


def coerce_df_types(df: pd.DataFrame, schema_rows: List[Mapping[str, Any]]) -> pd.DataFrame:
    """
    Coerce DataFrame column types to match expected Postgres types derived from schema rows.

    Args:
        df: Input DataFrame
        schema_rows: Rows from RPC with at least column_name, data_type

    Returns:
        A new DataFrame with best-effort coercions applied. Extra columns are preserved
        (caller may choose to drop them later).
    """
    if not schema_rows or df.empty:
        return df.copy()

    schema = {str(r.get("column_name")): _pg_type_to_expected(str(r.get("data_type", "text"))) for r in schema_rows}
    coerced = df.copy()
    for col, expected in schema.items():
        if col in coerced.columns:
            coerced[col] = _coerce_series(coerced[col], expected)
    return coerced


def validate_dataframe_against_table(
    df: pd.DataFrame,
    table_name: str,
    schema_rows: List[Mapping[str, Any]],
) -> ValidationReport:
    """
    Validate a DataFrame against a table schema fetched from Supabase.

    Args:
        df: DataFrame to validate
        table_name: Name used for reporting only
        schema_rows: Rows from RPC with at least column_name, data_type, is_nullable

    Returns:
        ValidationReport
    """
    row_count = int(len(df))
    if df.empty:
        return ValidationReport(
            is_valid=True,
            row_count=row_count,
            missing_columns=[],
            extra_columns=[],
            type_mismatches=[],
            nullable_violations=[],
        )

    # Build schema dicts
    schema_cols = [str(r.get("column_name")) for r in schema_rows]
    col_to_expected = {str(r.get("column_name")): _pg_type_to_expected(str(r.get("data_type", "text"))) for r in schema_rows}
    col_nullable = {str(r.get("column_name")): str(r.get("is_nullable", "YES")).upper() == "YES" for r in schema_rows}

    # Drop primary key columns (like 'id') from the list of required schema columns,
    # as they are typically auto-generated by the database and not expected in input frames.
    # This is a heuristic; a more robust solution might involve fetching primary key info.
    schema_cols_no_pk = [c for c in schema_cols if c != 'id']

    # Compute missing/extra
    df_cols = list(map(str, df.columns))
    missing = [c for c in schema_cols_no_pk if c not in df_cols]
    extra = [c for c in df_cols if c not in schema_cols]

    # Type checks for overlapping columns
    mismatches: List[TypeMismatch] = []
    for c in df_cols:
        if c not in col_to_expected:
            continue
        expected = col_to_expected[c]
        observed = _infer_pd_type_for_validation(df[c])
        if expected == "text":
            # text accepts anything once coerced; skip strict check
            continue
        if expected != observed:
            examples = df[c].dropna().head(3).tolist()
            mismatches.append(TypeMismatch(column=c, expected_type=expected, observed_type=observed, example_values=examples))

    # Nullability violations
    null_violations: List[str] = []
    for c, nullable in col_nullable.items():
        if not nullable and c in df.columns:
            if df[c].isna().any():
                null_violations.append(c)

    is_valid = len(missing) == 0 and len(mismatches) == 0 and len(null_violations) == 0
    return ValidationReport(
        is_valid=is_valid,
        row_count=row_count,
        missing_columns=missing,
        extra_columns=extra,
        type_mismatches=mismatches,
        nullable_violations=null_violations,
    )
