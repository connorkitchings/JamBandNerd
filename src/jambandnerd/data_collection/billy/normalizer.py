"""Normalization functions for Billy Strings raw data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable

import pandas as pd

from jambandnerd.data_collection.utils import compute_source_hash


def normalize_songs(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize songs into `billy_songs_raw` schema."""
    df = pd.DataFrame(raw)
    if df.empty:
        return df
    df = df.drop_duplicates(subset=["song_name"]).reset_index(drop=True)
    df["source_hash"] = df.apply(lambda row: compute_source_hash(row.to_dict()), axis=1)
    now = datetime.now(timezone.utc).isoformat()
    df["created_at"] = now
    df["updated_at"] = now
    return df


def normalize_shows(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize shows into `billy_shows_raw` schema."""
    df = pd.DataFrame(raw)
    if df.empty:
        return df

    for column in ["venue_city", "venue_state", "venue_country"]:
        if column not in df.columns:
            df[column] = ""

    df["show_date"] = pd.to_datetime(df["show_date"], errors="coerce").dt.date
    df = df.dropna(subset=["show_date", "source_uuid"])
    df["show_date"] = df["show_date"].apply(
        lambda d: d.isoformat() if pd.notnull(d) else None
    )

    df["source_hash"] = df.apply(lambda row: compute_source_hash(row.to_dict()), axis=1)
    now = datetime.now(timezone.utc).isoformat()
    df["created_at"] = now
    df["updated_at"] = now
    return df


def normalize_setlists(raw: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    """Normalize setlist rows into `billy_setlists_raw` schema."""
    df = pd.DataFrame(raw)
    if df.empty:
        return df

    df["created_at"] = datetime.now(timezone.utc).isoformat()
    df["source_hash"] = df.apply(lambda row: compute_source_hash(row.to_dict()), axis=1)

    numeric_columns = {
        "set_number": "Int64",
        "song_position": "Int64",
    }
    for column, dtype in numeric_columns.items():
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").astype(dtype)

    bool_columns = ["is_segue", "encore"]
    for column in bool_columns:
        if column in df.columns:
            df[column] = df[column].fillna(False).astype(bool)

    df["song_name"] = df["song_name"].fillna("").astype(str)
    df = df.dropna(subset=["show_id", "song_name"])
    return df
