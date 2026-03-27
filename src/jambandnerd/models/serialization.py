"""Shared prediction serialization helpers."""

from __future__ import annotations

from typing import Any, Sequence

from jambandnerd.models.registry import serialize_model_predictions


def serialize_predictions(
    *, model_slug: str, predictions: Sequence[Any]
) -> list[dict[str, Any]]:
    """Convert model outputs into the canonical JSON payload shape."""
    return serialize_model_predictions(model_slug, predictions)
