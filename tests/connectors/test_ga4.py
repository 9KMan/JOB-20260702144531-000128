"""Tests for GA4Connector and GA4 tools."""

import pytest
from unittest.mock import patch, MagicMock

from src.connectors.google.ga4 import GA4Connector, get_ga4_report, get_ga4_realtime_users


class TestGA4Connector:
    """Tests for the GA4Connector class."""

    def test_ga4_connector_inheritance(self):
        """Verify GA4Connector inherits from BaseConnector."""
        from src.connectors.base import BaseConnector
        assert issubclass(GA4Connector, BaseConnector)

    def test_ga4_connector_init(self):
        """Verify GA4Connector initializes with correct parameters."""
        connector = GA4Connector(
            property_id="123456789",
            client_id="test_client_id",
            client_secret="test_client_secret",
        )
        assert connector.property_id == "123456789"
        assert connector.client_id == "test_client_id"
        assert connector.client_secret == "test_client_secret"

    def test_ga4_connector_init_from_env(self, mock_env):
        """Verify GA4Connector reads from environment variables."""
        connector = GA4Connector()
        assert connector.property_id == "123456789"
        assert connector.client_id == "test_google_client_id"
        assert connector.client_secret == "test_google_client_secret"

    def test_ga4_connector_get_tools(self):
        """Verify get_tools returns the correct tool list."""
        connector = GA4Connector(property_id="123456789")
        tools = connector.get_tools()
        assert len(tools) == 2
        tool_names = [t.name for t in tools]
        assert "get_ga4_report" in tool_names
        assert "get_ga4_realtime_users" in tool_names

    @pytest.mark.asyncio
    async def test_ga4_connector_test_connection(self, mock_env):
        """Verify test_connection returns correct result."""
        connector = GA4Connector(property_id="123456789")
        with patch.object(
            get_ga4_realtime_users,
            "invoke",
            return_value={"success": True, "data": {"activeUsers": 42}},
        ):
            result = await connector.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_ga4_connector_test_connection_failure(self, mock_env):
        """Verify test_connection returns False on failure."""
        connector = GA4Connector(property_id="123456789")
        with patch.object(
            get_ga4_realtime_users,
            "invoke",
            side_effect=Exception("Connection failed"),
        ):
            result = await connector.test_connection()
            assert result is False

    def test_ga4_connector_get_oauth_authorization_url(self, mock_env):
        """Verify get_oauth_authorization_url returns valid URL."""
        connector = GA4Connector(property_id="123456789")
        url = connector.get_oauth_authorization_url()
        assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "client_id=test_google_client_id" in url
        assert "scope=https://www.googleapis.com/auth/analytics.readonly" in url

    def test_ga4_connector_oauth_url_contains_pkce_params(self, mock_env):
        """Verify OAuth URL contains PKCE challenge parameters."""
        connector = GA4Connector(property_id="123456789")
        url = connector.get_oauth_authorization_url()
        assert "code_challenge=" in url
        assert "code_challenge_method=S256" in url


class TestGetGA4ReportTool:
    """Tests for the get_ga4_report LangGraph tool."""

    def test_get_ga4_report_tool_exists(self):
        """Verify get_ga4_report tool is defined."""
        assert get_ga4_report is not None
        assert hasattr(get_ga4_report, "invoke")

    def test_get_ga4_report_tool_name(self):
        """Verify get_ga4_report tool has correct name."""
        assert get_ga4_report.name == "get_ga4_report"

    def test_get_ga4_report_tool_description(self):
        """Verify get_ga4_report tool has a description."""
        assert get_ga4_report.description is not None
        assert len(get_ga4_report.description) > 0

    def test_get_ga4_report_tool_parameters(self):
        """Verify get_ga4_report tool has expected parameters."""
        # Check the function signature
        import inspect
        sig = inspect.signature(get_ga4_report.invoke)
        params = list(sig.parameters.keys())
        assert "property_id" in params
        assert "start_date" in params
        assert "end_date" in params

    def test_get_ga4_report_invoke_with_mock(self, mock_composio_client, sample_ga4_response):
        """Verify get_ga4_report.invoke returns expected structure."""
        with patch(
            "src.connectors.google.ga4._get_ga4_toolset",
            return_value=mock_composio_client.get_toolset(),
        ):
            mock_composio_client.get_toolset().execute.return_value = sample_ga4_response["data"]
            result = get_ga4_report.invoke({
                "property_id": "123456789",
                "start_date": "2024-01-01",
                "end_date": "2024-01-02",
                "dimensions": ["date", "country"],
                "metrics": ["sessions", "activeUsers"],
            })
            assert "success" in result


class TestGetGA4RealtimeUsersTool:
    """Tests for the get_ga4_realtime_users LangGraph tool."""

    def test_get_ga4_realtime_users_tool_exists(self):
        """Verify get_ga4_realtime_users tool is defined."""
        assert get_ga4_realtime_users is not None
        assert hasattr(get_ga4_realtime_users, "invoke")

    def test_get_ga4_realtime_users_tool_name(self):
        """Verify get_ga4_realtime_users tool has correct name."""
        assert get_ga4_realtime_users.name == "get_ga4_realtime_users"

    def test_get_ga4_realtime_users_invoke_with_mock(self, mock_composio_client, sample_realtime_response):
        """Verify get_ga4_realtime_users.invoke returns expected structure."""
        with patch(
            "src.connectors.google.ga4._get_ga4_toolset",
            return_value=mock_composio_client.get_toolset(),
        ):
            mock_composio_client.get_toolset().execute.return_value = sample_realtime_response["data"]
            result = get_ga4_realtime_users.invoke({"property_id": "123456789"})
            assert "success" in result
