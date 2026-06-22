"""Tests for BaseConnector ABC enforcement."""

import pytest
from abc import ABC

from src.connectors.base import BaseConnector


def test_base_connector_is_abc():
    """Verify BaseConnector is an Abstract Base Class."""
    assert issubclass(BaseConnector, ABC)


def test_base_connector_cannot_be_instantiated():
    """Verify BaseConnector cannot be instantiated directly."""
    with pytest.raises(TypeError) as exc_info:
        BaseConnector()
    assert "abstract" in str(exc_info.value).lower()


def test_base_connector_has_required_methods():
    """Verify BaseConnector defines all required abstract methods."""
    required_methods = [
        "get_tools",
        "test_connection",
        "get_oauth_authorization_url",
        "handle_oauth_callback",
        "refresh_credentials",
    ]
    for method in required_methods:
        assert hasattr(BaseConnector, method)


class ConcreteConnector(BaseConnector):
    """A minimal concrete implementation of BaseConnector for testing."""

    def get_tools(self):
        return []

    async def test_connection(self):
        return True

    def get_oauth_authorization_url(self):
        return "https://example.com/auth"

    async def handle_oauth_callback(self, code, state=None):
        return {"access_token": "test"}

    async def refresh_credentials(self):
        return {"access_token": "refreshed"}


def test_concrete_connector_can_be_instantiated():
    """Verify a concrete implementation can be instantiated."""
    connector = ConcreteConnector()
    assert connector is not None


def test_concrete_connector_get_tools():
    """Verify concrete implementation returns tools list."""
    connector = ConcreteConnector()
    assert connector.get_tools() == []


@pytest.mark.asyncio
async def test_concrete_connector_test_connection():
    """Verify concrete implementation test_connection works."""
    connector = ConcreteConnector()
    result = await connector.test_connection()
    assert result is True


def test_concrete_connector_get_oauth_authorization_url():
    """Verify concrete implementation returns auth URL."""
    connector = ConcreteConnector()
    url = connector.get_oauth_authorization_url()
    assert url == "https://example.com/auth"


@pytest.mark.asyncio
async def test_concrete_connector_handle_oauth_callback():
    """Verify concrete implementation handles OAuth callback."""
    connector = ConcreteConnector()
    result = await connector.handle_oauth_callback("test_code")
    assert result == {"access_token": "test"}


@pytest.mark.asyncio
async def test_concrete_connector_refresh_credentials():
    """Verify concrete implementation refreshes credentials."""
    connector = ConcreteConnector()
    result = await connector.refresh_credentials()
    assert result == {"access_token": "refreshed"}
