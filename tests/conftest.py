"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def sample_data_dir(project_root):
    """Return the sample data directory for tests."""
    return project_root / "tests" / "data"


@pytest.fixture
def mock_env_vars():
    """Provide mock environment variables for testing."""
    return {
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test_service_role_key_123",
        "PHISH_API_KEY": "test_phish_key_456",
    }


@pytest.fixture
def setup_test_env(mock_env_vars, monkeypatch):
    """Set up test environment variables."""
    for key, value in mock_env_vars.items():
        monkeypatch.setenv(key, value)
    return mock_env_vars
