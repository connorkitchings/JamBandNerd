from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from src.jambandnerd.db.connection import get_supabase_client
from src.jambandnerd.models.registry import get_band_model_version


def ensure_live_env(*, band: str) -> None:
    required = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
    missing = [name for name in required if not os.environ.get(name)]
    if band == "phish" and not os.environ.get("PHISH_API_KEY"):
        missing.append("PHISH_API_KEY")
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"Missing required live-test environment variables: {joined}"
        )


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def assert_prediction_publish_fresh(*, band: str, started_at: datetime) -> None:
    client = get_supabase_client()
    model_version = get_band_model_version(band)
    response = (
        client.table("setlist_predictions")
        .select("band, model_version, generated_at, reference_date, predictions")
        .eq("band", band)
        .eq("model_version", model_version)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )

    assert response.data, f"No setlist_predictions row found for {band}/{model_version}"
    row = response.data[0]
    assert row["reference_date"]
    assert row["predictions"]
    assert parse_timestamp(row["generated_at"]) >= started_at - timedelta(minutes=5)


def assert_accuracy_publish_fresh(*, band: str, started_at: datetime) -> None:
    client = get_supabase_client()
    model_version = get_band_model_version(band)

    per_show_response = (
        client.table("setlist_accuracy")
        .select("band, model_version, evaluated_at, show_date")
        .eq("band", band)
        .eq("model_version", model_version)
        .limit(50)
        .execute()
    )
    assert (
        per_show_response.data
    ), f"No per-show accuracy row found for {band}/{model_version}"
