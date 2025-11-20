"""Tests for database operations."""

from unittest.mock import MagicMock, patch

import pytest

from jambandnerd.db.connection import get_supabase_client, validate_environment


class TestSupabaseConnection:
    """Tests for Supabase connection management."""

    def test_validate_environment_missing_url(self, monkeypatch):
        """Test validation fails when SUPABASE_URL is missing."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_KEY", "test_key")

        with pytest.raises(ValueError, match="Missing SUPABASE_URL"):
            validate_environment()

    def test_validate_environment_missing_key(self, monkeypatch):
        """Test validation fails when SUPABASE_KEY is missing."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.delenv("SUPABASE_KEY", raising=False)

        with pytest.raises(ValueError, match="Missing SUPABASE_URL or SUPABASE_KEY"):
            validate_environment()

    def test_validate_environment_success(self, setup_test_env):
        """Test validation passes when both variables are set."""
        # Should not raise an exception
        validate_environment()

    @patch('jambandnerd.db.connection.create_client')
    def test_get_supabase_client_success(self, mock_create_client, setup_test_env):
        """Test successful Supabase client creation."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        client = get_supabase_client()

        assert client == mock_client
        mock_create_client.assert_called_once_with(
            "https://test.supabase.co",
            "test_key_123"
        )

    @patch('jambandnerd.db.connection.create_client')
    def test_get_supabase_client_singleton(self, mock_create_client, setup_test_env):
        """Test that get_supabase_client returns the same instance."""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        # Clear any existing client instance
        import jambandnerd.db.connection
        jambandnerd.db.connection._supabase_client = None

        client1 = get_supabase_client()
        client2 = get_supabase_client()

        assert client1 is client2
        # Should only be called once due to singleton pattern
        mock_create_client.assert_called_once()

    def test_get_supabase_client_missing_env_vars(self, monkeypatch):
        """Test client creation fails with missing environment variables."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_KEY", raising=False)

        # Clear any existing client instance
        import jambandnerd.db.connection
        jambandnerd.db.connection._supabase_client = None

        with pytest.raises(ValueError, match="SUPABASE_URL and SUPABASE_KEY must be set"):
            get_supabase_client()
