"""Abstract base connector for Composio + LangGraph integration."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseConnector(ABC):
    """Abstract base class for all Composio connectors.

    All connectors must implement this interface to be used with
    the Composio + LangGraph integration.
    """

    @abstractmethod
    def get_tools(self) -> List[Any]:
        """Return a list of LangGraph @tool functions.

        Returns:
            List of tool functions decorated with @tool decorator.
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the external service.

        Returns:
            True if connection is successful, False otherwise.
        """
        pass

    @abstractmethod
    def get_oauth_authorization_url(self) -> str:
        """Get the OAuth authorization URL for user consent.

        Returns:
            The OAuth authorization URL to redirect users to.
        """
        pass

    @abstractmethod
    async def handle_oauth_callback(self, code: str, state: Optional[str] = None) -> Dict[str, Any]:
        """Handle the OAuth callback after user authorization.

        Args:
            code: The authorization code from the OAuth provider.
            state: Optional state parameter for CSRF protection.

        Returns:
            Dictionary containing the OAuth tokens and user info.
        """
        pass

    @abstractmethod
    async def refresh_credentials(self) -> Dict[str, Any]:
        """Refresh the OAuth credentials using the refresh token.

        Returns:
            Dictionary containing the refreshed OAuth tokens.
        """
        pass
