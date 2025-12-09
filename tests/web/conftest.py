"""Shared fixtures for web/Streamlit tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest


@pytest.fixture
def sample_predictions_notebook() -> pd.DataFrame:
    """Sample Notebook model prediction data."""
    return pd.DataFrame(
        {
            "rank": [1, 2, 3, 4, 5],
            "song_name": [
                "Disco",
                "Chilly Water",
                "Space Wrangler",
                "Proving Ground",
                "Pigeons",
            ],
            "plays_past_year": [15, 12, 10, 8, 7],
            "current_gap": [8, 12, 15, 5, 20],
            "LTP": [
                "2025-11-01",
                "2025-10-15",
                "2025-10-01",
                "2025-11-10",
                "2025-09-15",
            ],
        }
    )


@pytest.fixture
def sample_predictions_ckplus() -> pd.DataFrame:
    """Sample CK+ model prediction data."""
    return pd.DataFrame(
        {
            "rank": [1, 2, 3, 4, 5],
            "song_name": [
                "Space Wrangler",
                "Disco",
                "Proving Ground",
                "Pigeons",
                "Chilly Water",
            ],
            "times_played": [150, 200, 80, 120, 180],
            "current_gap": [15, 8, 5, 20, 12],
            "avg_gap": [10.0, 8.0, 6.0, 15.0, 10.0],
            "gap_ratio": [1.5, 1.0, 0.83, 1.33, 1.2],
            "gap_z_score": [2.1, 0.5, -0.3, 1.2, 0.8],
            "ckplus_score": [2.5, 1.8, 1.2, 1.6, 1.4],
            "LTP": [
                "2025-10-01",
                "2025-11-01",
                "2025-11-10",
                "2025-09-15",
                "2025-10-15",
            ],
        }
    )


@pytest.fixture
def sample_setlist_df() -> pd.DataFrame:
    """Sample setlist data for testing."""
    return pd.DataFrame(
        {
            "set_number": [1, 1, 1, 2, 2, 2, "E"],
            "song_position": [1, 2, 3, 1, 2, 3, 1],
            "song_name": [
                "Disco",
                "Space Wrangler",
                "Surprise Song",  # Not in predictions
                "Chilly Water",
                "Another One",  # Not in predictions
                "Proving Ground",
                "Encore Song",  # Not in predictions
            ],
        }
    )


@pytest.fixture
def sample_show_details() -> dict[str, Any]:
    """Sample show details for testing."""
    return {
        "show_id": "12345",
        "show_date": "2025-11-15",
        "venue_name": "Red Rocks Amphitheatre",
        "city": "Morrison",
        "state": "CO",
        "venue_city": "Morrison",
        "venue_state": "CO",
    }


@pytest.fixture
def sample_accuracy_df() -> pd.DataFrame:
    """Sample per-show accuracy data for testing."""
    base_date = date.today() - timedelta(days=30)
    return pd.DataFrame(
        {
            "band": ["wsp"] * 10,
            "model_version": ["notebook_v1"] * 10,
            "show_date": [
                (base_date + timedelta(days=i)).isoformat() for i in range(10)
            ],
            "top_10_hits": [3, 4, 2, 5, 3, 4, 2, 3, 4, 5],
            "top_25_hits": [8, 10, 6, 12, 9, 11, 7, 8, 10, 13],
            "top_50_hits": [15, 18, 12, 20, 16, 19, 14, 15, 18, 22],
            "total_songs": [22, 24, 20, 25, 22, 24, 21, 22, 23, 26],
        }
    )


@pytest.fixture
def mock_supabase_client() -> MagicMock:
    """Create a mock Supabase client for testing."""
    client = MagicMock()

    # Default empty response
    default_response = MagicMock()
    default_response.data = []

    # Chain mock for table().select().eq().execute()
    client.table.return_value.select.return_value.eq.return_value.execute.return_value = default_response
    client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = default_response
    client.table.return_value.select.return_value.eq.return_value.neq.return_value.order.return_value.limit.return_value.execute.return_value = default_response

    return client


@pytest.fixture
def mock_predictions_response(sample_predictions_notebook) -> dict[str, Any]:
    """Mock prediction database response."""
    return {
        "band": "wsp",
        "reference_date": "2025-11-15",
        "predicted_at": datetime.now().isoformat(),
        "model_version": "v1",
        "predictions": sample_predictions_notebook.to_dict("records"),
    }
