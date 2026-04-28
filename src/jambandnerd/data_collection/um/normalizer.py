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
    df = df.copy()

    numeric_columns = {
        "set_sequence": "Int64",
        "song_position": "Int64",
        "show_position": "Int64",
        "song_id": "Int64",
        "show_id": "Int64",
    }

    if "set_sequence" in df.columns:
        df["set_sequence"] = (
            df["set_sequence"].astype(str).str.lower().replace({"e": "99"})
        )

    for column, dtype in numeric_columns.items():
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype(dtype)

    if "transition" in df.columns:
        df["is_segue"] = (
            df["transition"].fillna("").astype(str).str.contains(">", regex=False)
        )

    if "set_label" in df.columns:
        encore_from_label = (
            df["set_label"].fillna("").astype(str).str.contains("Encore", case=False)
        )
        if "set_sequence" in df.columns:
            df["encore"] = encore_from_label | (df["set_sequence"] == 99)
        else:
            df["encore"] = encore_from_label

    bool_columns = ["is_segue", "encore"]
    for column in bool_columns:
        if column in df.columns:
            df[column] = df[column].fillna(False).astype(bool)

    return attach_source_hash(df)
