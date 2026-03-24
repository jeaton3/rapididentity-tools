"""
Authentication utilities for RapidIdentity API.
"""

from typing import Optional, Dict, Any
import base64
from datetime import datetime, timedelta


class APIKeyAuth:
    """Handle API Key authentication for RapidIdentity."""

    def __init__(self, api_key: str):
        """
        Initialize API Key authentication.

        Args:
            api_key: The API key for authentication
        """
        self.api_key = api_key

    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


class BasicAuth:
    """Handle Basic authentication for RapidIdentity."""

    def __init__(self, username: str, password: str):
        """
        Initialize Basic authentication.

        Args:
            username: Username for authentication
            password: Password for authentication
        """
        self.username = username
        self.password = password

    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }


class OAuth2Session:
    """Handle OAuth2 token-based authentication for RapidIdentity."""

    def __init__(self, access_token: str, token_type: str = "Bearer"):
        """
        Initialize OAuth2 authentication.

        Args:
            access_token: The OAuth2 access token
            token_type: The token type (default: Bearer)
        """
        self.access_token = access_token
        self.token_type = token_type
        self.expires_at: Optional[datetime] = None

    def set_expiration(self, expires_in: int) -> None:
        """
        Set token expiration time.

        Args:
            expires_in: Token expiration time in seconds
        """
        self.expires_at = datetime.now() + timedelta(seconds=expires_in)

    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now() >= self.expires_at

    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        return {
            "Authorization": f"{self.token_type} {self.access_token}",
            "Content-Type": "application/json",
        }


class AuthConfig:
    """Configuration for different authentication methods."""

    def __init__(self, auth_type: str = "api_key", **kwargs):
        """
        Initialize authentication configuration.

        Args:
            auth_type: Type of authentication (api_key, basic, oauth2)
            **kwargs: Additional authentication parameters
        """
        self.auth_type = auth_type
        self.params = kwargs
        self.auth_handler: Optional[Any] = None

        if auth_type == "api_key":
            self.auth_handler = APIKeyAuth(kwargs.get("api_key"))
        elif auth_type == "basic":
            self.auth_handler = BasicAuth(kwargs.get("username"), kwargs.get("password"))
        elif auth_type == "oauth2":
            self.auth_handler = OAuth2Session(kwargs.get("access_token"))
        else:
            raise ValueError(f"Unsupported authentication type: {auth_type}")

    def get_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        return self.auth_handler.get_headers()
