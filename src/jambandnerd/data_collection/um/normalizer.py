"""Normalization functions for Umphrey's McGee raw data."""

from __future__ import annotations

import pandas as pd

from jambandnerd.data_collection.utils import compute_source_hash


def attach_source_hash(df: pd.DataFrame) -> pd.DataFrame:
    """Attach a deterministic source_hash column to a DataFrame."""
    if df.empty:
        return df
    df = df.copy()
    df = df.where(pd.notnull(df), None)
    df["source_hash"] = df.apply(lambda row: compute_source_hash(row.to_dict()), axis=1)
    return df


def normalize_setlists(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize UM setlist DataFrame column types and attach source hash."""
    if df.empty:
        return df

    numeric_columns = {
        "set_sequence": "Int64",
        "song_position": "Int64",
        "show_position": "Int64",
    }
    for column, dtype in numeric_columns.items():
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype(dtype)

    bool_columns = ["is_segue", "encore"]
    for column in bool_columns:
        if column in df.columns:
            df[column] = df[column].fillna(False).astype(bool)

    if "set_label" in df.columns and "set_number" not in df.columns:
        df["set_number"] = df["set_label"].fillna("").astype(str)
    if "transition" not in df.columns:
        df["transition"] = None

    return attach_source_hash(df)
