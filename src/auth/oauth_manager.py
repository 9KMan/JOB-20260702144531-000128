"""OAuth token management for Composio + LangGraph connectors."""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp


@dataclass
class OAuthToken:
    """OAuth token data class.

    Attributes:
        access_token: The OAuth access token.
        refresh_token: The OAuth refresh token (if applicable).
        token_type: The token type (typically 'Bearer').
        expires_in: Seconds until the token expires.
        expires_at: Unix timestamp when the token expires.
        scope: The granted OAuth scopes.
        refresh_expires_in: Seconds until the refresh token expires.
    """

    access_token: str
    token_type: str = "Bearer"
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    expires_at: Optional[float] = None
    scope: Optional[str] = None
    refresh_expires_in: Optional[int] = None
    _raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthToken":
        """Create an OAuthToken from a dictionary.

        Args:
            data: Dictionary containing token data.

        Returns:
            OAuthToken instance.
        """
        expires_in = data.get("expires_in")
        expires_at = None
        if expires_in:
            expires_at = time.time() + expires_in

        return cls(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_in=expires_in,
            expires_at=expires_at,
            scope=data.get("scope"),
            refresh_expires_in=data.get("refresh_expires_in"),
            _raw=data,
        )

    def is_expired(self) -> bool:
        """Check if the token is expired.

        Returns:
            True if token is expired, False otherwise.
        """
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at

    def needs_refresh(self, buffer_seconds: int = 300) -> bool:
        """Check if the token needs to be refreshed.

        Args:
            buffer_seconds: Seconds before expiry to trigger refresh. Default: 300 (5 min).

        Returns:
            True if token should be refreshed, False otherwise.
        """
        if self.expires_at is None:
            return self.refresh_token is None
        return time.time() >= (self.expires_at - buffer_seconds)

    def to_dict(self) -> Dict[str, Any]:
        """Convert token to dictionary for storage.

        Returns:
            Dictionary representation of the token.
        """
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "expires_at": self.expires_at,
            "scope": self.scope,
            "refresh_expires_in": self.refresh_expires_in,
        }


class OAuthTokenManager:
    """Manages OAuth tokens for connector integrations.

    This class handles token storage, retrieval, refresh, and revocation
    for OAuth-based integrations.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        token_dir: Optional[Path] = None,
    ):
        """Initialize the OAuth token manager.

        Args:
            client_id: The OAuth client ID.
            client_secret: The OAuth client secret.
            token_url: The OAuth token endpoint URL.
            token_dir: Directory to store token files. Defaults to ~/.composio/tokens.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.token_dir = token_dir or (Path.home() / ".composio" / "tokens")
        self._token_cache: Dict[str, OAuthToken] = {}
        self._ensure_token_dir()

    def _ensure_token_dir(self) -> None:
        """Ensure the token directory exists."""
        self.token_dir.mkdir(parents=True, exist_ok=True)

    def _get_token_path(self, service: str) -> Path:
        """Get the file path for a service's token.

        Args:
            service: The service name (e.g., 'google_ga4').

        Returns:
            Path to the token file.
        """
        return self.token_dir / f"{service}.json"

    async def get_token(self, service: str) -> Optional[OAuthToken]:
        """Get the stored token for a service.

        Args:
            service: The service name.

        Returns:
            OAuthToken if found, None otherwise.
        """
        if service in self._token_cache:
            return self._token_cache[service]

        token_path = self._get_token_path(service)
        if not token_path.exists():
            return None

        try:
            with open(token_path, "r") as f:
                data = json.load(f)
            token = OAuthToken.from_dict(data)
            self._token_cache[service] = token
            return token
        except (json.JSONDecodeError, KeyError):
            return None

    async def save_token(self, service: str, token_data: Dict[str, Any]) -> None:
        """Save a token for a service.

        Args:
            service: The service name.
            token_data: Dictionary containing token data from OAuth response.
        """
        token = OAuthToken.from_dict(token_data)
        self._token_cache[service] = token

        token_path = self._get_token_path(service)
        with open(token_path, "w") as f:
            json.dump(token.to_dict(), f, indent=2)

    async def get_valid_token(self, service: str) -> Dict[str, Any]:
        """Get a valid token, refreshing if necessary.

        Args:
            service: The service name.

        Returns:
            Dictionary containing the valid access token.

        Raises:
            ValueError: If no token exists and refresh is not possible.
        """
        token = await self.get_token(service)

        if token is None:
            raise ValueError(f"No token found for service: {service}")

        if token.needs_refresh() and token.refresh_token:
            token = await self._refresh(service, token.refresh_token)

        return {"access_token": token.access_token, "token_type": token.token_type}

    async def revoke(self, service: str) -> bool:
        """Revoke the token for a service.

        Args:
            service: The service name.

        Returns:
            True if revocation was successful, False otherwise.
        """
        token = await self.get_token(service)
        if token is None:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_url.replace("/token", "/revoke"),
                    data={
                        "token": token.access_token,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                ) as response:
                    pass

            if service in self._token_cache:
                del self._token_cache[service]

            token_path = self._get_token_path(service)
            if token_path.exists():
                token_path.unlink()

            return True
        except Exception:
            if service in self._token_cache:
                del self._token_cache[service]
            token_path = self._get_token_path(service)
            if token_path.exists():
                token_path.unlink()
            return True

    async def exchange_code(
        self, code: str, redirect_uri: str, code_verifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exchange an authorization code for tokens.

        Args:
            code: The authorization code.
            redirect_uri: The redirect URI used in the authorization request.
            code_verifier: The PKCE code verifier (if applicable).

        Returns:
            Dictionary containing the OAuth tokens.
        """
        data: Dict[str, str] = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        if code_verifier:
            data["code_verifier"] = code_verifier

        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ValueError(f"Token exchange failed: {error_text}")
                return await response.json()

    async def _refresh(self, service: str, refresh_token: str) -> OAuthToken:
        """Refresh an expired token.

        Args:
            service: The service name.
            refresh_token: The refresh token.

        Returns:
            The refreshed OAuthToken.
        """
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.token_url, data=data) as response:
                if response.status != 200:
                    raise ValueError("Token refresh failed")
                token_data = await response.json()

        token = OAuthToken.from_dict(token_data)
        await self.save_token(service, token_data)
        return token
