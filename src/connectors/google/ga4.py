"""Google Analytics 4 connector for Composio + LangGraph integration."""

import os
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from src.connectors.base import BaseConnector


def _get_composio_client():
    """Get the Composio client instance."""
    try:
        from composio import Composio
        return Composio()
    except ImportError:
        raise ImportError(
            "Composio client not installed. Install with: pip install composio-langchain"
        )


def _get_ga4_toolset():
    """Get the GA4 toolset from Composio."""
    client = _get_composio_client()
    return client.get_toolset("googleanalytics")


@tool
def get_ga4_report(
    property_id: str,
    start_date: str,
    end_date: str,
    dimensions: Optional[List[str]] = None,
    metrics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get a Google Analytics 4 report for the specified property.

    Args:
        property_id: The GA4 property ID (e.g., '123456789').
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
        dimensions: List of dimensions to include (e.g., ['country', 'deviceCategory']).
        metrics: List of metrics to include (e.g., ['sessions', 'conversions']).

    Returns:
        Dictionary containing the GA4 report data.
    """
    toolset = _get_ga4_toolset()

    params = {
        "property_id": property_id,
        "start_date": start_date,
        "end_date": end_date,
    }

    if dimensions:
        params["dimensions"] = dimensions
    if metrics:
        params["metrics"] = metrics

    try:
        result = toolset.execute(action_name="get_report", params=params)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_ga4_realtime_users(property_id: str) -> Dict[str, Any]:
    """Get the number of active users currently on the GA4 property.

    Args:
        property_id: The GA4 property ID (e.g., '123456789').

    Returns:
        Dictionary containing the realtime user count.
    """
    toolset = _get_ga4_toolset()

    try:
        result = toolset.execute(action_name="get_realtime_users", params={"property_id": property_id})
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


class GA4Connector(BaseConnector):
    """Google Analytics 4 connector implementation.

    This connector provides access to GA4 reporting data through
    LangGraph tools, using Composio as the integration layer.
    """

    def __init__(
        self,
        property_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        """Initialize the GA4 connector.

        Args:
            property_id: The GA4 property ID. Can also be set via GOOGLE_GA4_PROPERTY_ID env var.
            client_id: OAuth client ID. Can also be set via GOOGLE_CLIENT_ID env var.
            client_secret: OAuth client secret. Can also be set via GOOGLE_CLIENT_SECRET env var.
        """
        self.property_id = property_id or os.getenv("GOOGLE_GA4_PROPERTY_ID")
        self.client_id = client_id or os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")
        self._token_manager = None

    def get_tools(self) -> List[Any]:
        """Return the list of LangGraph tools for GA4.

        Returns:
            List containing get_ga4_report and get_ga4_realtime_users tools.
        """
        return [get_ga4_report, get_ga4_realtime_users]

    async def test_connection(self) -> bool:
        """Test the connection to Google Analytics 4.

        Returns:
            True if connection is successful, False otherwise.
        """
        if not self.property_id:
            return False

        try:
            result = get_ga4_realtime_users.invoke({"property_id": self.property_id})
            return result.get("success", False)
        except Exception:
            return False

    def get_oauth_authorization_url(self) -> str:
        """Get the OAuth authorization URL for Google Analytics 4.

        Returns:
            The OAuth authorization URL.
        """
        from src.auth.pkce import generate_code_verifier, generate_code_challenge

        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)

        client_id = self.client_id or os.getenv("GOOGLE_CLIENT_ID", "")
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/oauth/callback")

        state_data = f"ga4_{self.property_id or ''}"
        import base64
        state = base64.urlsafe_b64encode(state_data.encode()).decode()

        auth_params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/analytics.readonly",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "state": state,
        }

        from urllib.parse import urlencode
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(auth_params)}"

        return auth_url

    async def handle_oauth_callback(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """Handle the OAuth callback for Google Analytics 4.

        Args:
            code: The authorization code from Google.
            state: Optional state parameter for CSRF protection.

        Returns:
            Dictionary containing the OAuth tokens.
        """
        from src.auth.oauth_manager import OAuthTokenManager

        if not self.client_id or not self.client_secret:
            raise ValueError("Client ID and secret are required for OAuth callback")

        self._token_manager = OAuthTokenManager(
            client_id=self.client_id,
            client_secret=self.client_secret,
            token_url="https://oauth2.googleapis.com/token",
        )

        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/oauth/callback")

        token_data = await self._token_manager.exchange_code(code, redirect_uri)
        await self._token_manager.save_token("google_ga4", token_data)

        return token_data

    async def refresh_credentials(self) -> Dict[str, Any]:
        """Refresh the OAuth credentials for Google Analytics 4.

        Returns:
            Dictionary containing the refreshed OAuth tokens.
        """
        from src.auth.oauth_manager import OAuthTokenManager

        if not self._token_manager:
            self._token_manager = OAuthTokenManager(
                client_id=self.client_id or os.getenv("GOOGLE_CLIENT_ID", ""),
                client_secret=self.client_secret or os.getenv("GOOGLE_CLIENT_SECRET", ""),
                token_url="https://oauth2.googleapis.com/token",
            )

        valid_token = await self._token_manager.get_valid_token("google_ga4")
        return valid_token
