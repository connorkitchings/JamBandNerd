"""Tests for database operations."""

import warnings
from unittest.mock import MagicMock, patch

import pytest

from jambandnerd.db.connection import get_supabase_client, validate_environment


class TestSupabaseConnection:
    """Tests for Supabase connection management."""

    def test_validate_environment_missing_url(self, monkeypatch):
        """Test validation fails when SUPABASE_URL is missing."""
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "test_key")

        with pytest.raises(
            ValueError,
            match="Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY",
        ):
            validate_environment()

    def test_validate_environment_missing_key(self, monkeypatch):
        """Test validation fails when the service-role key is missing."""
        monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
        monkeypatch.delenv("SUPABASE_KEY", raising=False)

        with pytest.raises(
            ValueError,
            match="Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY",
        ):
            validate_environment()

    def test_validate_environment_success(self, setup_test_env):
        """Test validation passes when both variables are set."""
        # Should not raise an exception
        validate_environment()

    @patch("jambandnerd.db.connection.create_client")
    def test_get_supabase_client_success(self, mock_create_client, setup_test_env):
        """Test successful Supabase client creation."""
        # Reset the singleton to ensure create_client is called
        import jambandnerd.db.connection

        jambandnerd.db.connection._supabase_client = None

        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        client = get_supabase_client()

        assert client == mock_client
        mock_create_client.assert_called_once()
        call_args = mock_create_client.call_args
        assert call_args.args[0] == "https://test.supabase.co"
        assert call_args.args[1] == "test_service_role_key_123"
        options = call_args.args[2]
        assert options.httpx_client is not None
        assert options.httpx_client.timeout.connect == options.postgrest_client_timeout
        assert options.httpx_client.timeout.read == options.postgrest_client_timeout
        assert options.httpx_client.timeout.write == options.postgrest_client_timeout
        assert options.httpx_client.timeout.pool == options.postgrest_client_timeout
        assert options.httpx_client.follow_redirects is True

    @patch("jambandnerd.db.connection.create_client")
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
        monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

        # Clear any existing client instance
        import jambandnerd.db.connection

        jambandnerd.db.connection._supabase_client = None

        with pytest.raises(
            ValueError,
            match="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY",
        ):
            get_supabase_client()
            get_supabase_client()

    def test_get_supabase_client_avoids_postgrest_deprecation_warnings(
        self, setup_test_env
    ):
        """The wrapper should pass an httpx client instead of deprecated timeout args."""
        import jambandnerd.db.connection

        jambandnerd.db.connection._supabase_client = None

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            client = get_supabase_client()
            client.table("shows")

        deprecation_messages = [
            str(warning.message)
            for warning in caught
            if issubclass(warning.category, DeprecationWarning)
        ]
        assert not any(
            "timeout' parameter is deprecated" in message
            or "verify' parameter is deprecated" in message
            for message in deprecation_messages
        )
