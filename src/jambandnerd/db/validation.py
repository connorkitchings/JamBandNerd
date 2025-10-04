"""Dataframe validation against Supabase table schemas.

This module provides comprehensive validation of pandas DataFrames against
Postgres/Supabase table schemas, including type coercion, null checking,
and schema validation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional

import json
import pandas as pd


@dataclass
class TypeMismatch:
    """Represents a data type mismatch between a DataFrame and a database schema.
    
    Attributes:
        column: Name of the column with the mismatch
        expected_type: Expected Postgres type (normalized)
        observed_type: Observed pandas/Python type
        example_values: Sample values from the column showing the issue
    """

    column: str
    expected_type: str
    observed_type: str
    example_values: list[Any] = field(default_factory=list)


@dataclass
class ValidationReport:
    """A report summarizing the validation of a DataFrame against a table schema.
    
    Attributes:
        is_valid: Whether the DataFrame passes all validation checks
        row_count: Number of rows in the DataFrame
        missing_columns: Required columns not present in the DataFrame
        extra_columns: DataFrame columns not in the schema
        type_mismatches: List of type mismatch details
        nullable_violations: Columns with null values that should be non-null
    """

    is_valid: bool
    row_count: int
    missing_columns: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)
    type_mismatches: list[TypeMismatch] = field(default_factory=list)
    nullable_violations: list[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """Return a human-readable summary of the validation report."""
        if self.is_valid:
            return f"ValidationReport(is_valid=True, {self.row_count} rows)"        
        
        lines = [
            f"ValidationReport(is_valid=False, {self.row_count} rows)",
            f"  Missing columns: {len(self.missing_columns)}",
            f"  Extra columns: {len(self.extra_columns)}",
            f"  Type mismatches: {len(self.type_mismatches)}",
            f"  Nullable violations: {len(self.nullable_violations)}"
        ]
        return "\n".join(lines)


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
    """Infer pandas type for validation - more permissive."""
    # Check for null/empty series
    if series.empty or series.isna().all():
        return "text"  # Default to text for empty series
    
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


def coerce_df_types(
    df: pd.DataFrame, 
    schema_rows: list[Mapping[str, Any]]
) -> pd.DataFrame:
    """Coerce DataFrame column types to match expected Postgres types.
    
    This function performs best-effort type coercion for each column in the DataFrame
    based on the expected Postgres type from the schema. Extra columns not in the
    schema are preserved unchanged.

    Args:
        df: Input DataFrame to coerce
        schema_rows: List of dicts with at least 'column_name' and 'data_type' keys

    Returns:
        A new DataFrame with coerced types. Original DataFrame is not modified.
        
    Example:
        >>> schema = [{"column_name": "id", "data_type": "integer"}]
        >>> df = pd.DataFrame({"id": ["1", "2", "3"]})
        >>> coerced = coerce_df_types(df, schema)
        >>> coerced["id"].dtype
        Int64
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
    schema_rows: list[Mapping[str, Any]],
) -> ValidationReport:
    """Validate a DataFrame against a Postgres/Supabase table schema.
    
    Performs comprehensive validation including:
    - Missing required columns
    - Extra unexpected columns
    - Type mismatches between DataFrame and schema
    - Null value violations in non-nullable columns

    Args:
        df: DataFrame to validate
        table_name: Name of the table (used for reporting only)
        schema_rows: Schema info from Supabase RPC with keys:
            - column_name: Name of the column
            - data_type: Postgres data type
            - is_nullable: "YES" or "NO"

    Returns:
        ValidationReport with detailed validation results
        
    Example:
        >>> schema = [{"column_name": "id", "data_type": "integer", "is_nullable": "NO"}]
        >>> df = pd.DataFrame({"id": [1, 2, 3]})
        >>> report = validate_dataframe_against_table(df, "my_table", schema)
        >>> report.is_valid
        True
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

    # Type checks for overlapping columns - be more permissive
    mismatches: list[TypeMismatch] = []
    for c in df_cols:
        if c not in col_to_expected:
            continue
        expected = col_to_expected[c]
        observed = _infer_pd_type_for_validation(df[c])
        
        # Be permissive with text - it can hold anything
        if expected == "text":
            continue
        
        # Allow numeric types to be compatible (integer/numeric/float)
        if expected in ("integer", "numeric") and observed in ("integer", "numeric", "text"):
            continue
        
        # Allow date/timestamp compatibility
        if expected in ("date", "timestamp") and observed in ("date", "timestamp", "text"):
            continue
        
        # Only flag as mismatch if truly incompatible
        if expected != observed:
            examples = df[c].dropna().head(3).tolist()
            mismatches.append(TypeMismatch(column=c, expected_type=expected, observed_type=observed, example_values=examples))

    # Nullability violations - only check non-PK columns
    null_violations: list[str] = []
    for c, nullable in col_nullable.items():
        # Skip auto-generated columns
        if c in ('id', 'created_at', 'updated_at'):
            continue
        if not nullable and c in df.columns:
            if df[c].isna().any():
                null_violations.append(c)

    # Validation is now more lenient - only fail on critical issues
    # Missing required columns is critical, but type mismatches are just warnings
    is_valid = len(missing) == 0 and len(null_violations) == 0
    return ValidationReport(
        is_valid=is_valid,
        row_count=row_count,
        missing_columns=missing,
        extra_columns=extra,
        type_mismatches=mismatches,
        nullable_violations=null_violations,
    )
