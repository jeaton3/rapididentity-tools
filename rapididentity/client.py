"""
Main RapidIdentity API Client.
"""

from typing import Optional, Dict, Any, List, Union
import requests
from urllib.parse import urljoin
import logging
from typing import TYPE_CHECKING

from rapididentity.auth import AuthConfig, APIKeyAuth, BasicAuth, OAuth2Session
from rapididentity.exceptions import (
    RapidIdentityError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    APIError,
    ConnectionError,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from rapididentity.connect import RapidIdentityConnect


class RapidIdentityClient:
    """
    Main client for interacting with RapidIdentity APIs.

    Supports multiple authentication methods and provides convenient access
    to RapidIdentity REST API endpoints.
    """

    def __init__(
        self,
        host: str,
        auth_config: AuthConfig,
        verify_ssl: bool = True,
        timeout: int = 30,
    ):
        """
        Initialize RapidIdentity API Client.

        Args:
            host: The RapidIdentity host URL (e.g., https://rapididentity.example.com)
            auth_config: Authentication configuration
            verify_ssl: Whether to verify SSL certificates (default: True)
            timeout: Request timeout in seconds (default: 30)

        Raises:
            ValidationError: If host or auth_config is invalid
        """
        if not host:
            raise ValidationError("Host URL is required")
        if not isinstance(auth_config, AuthConfig):
            raise ValidationError("auth_config must be an AuthConfig instance")

        self.host = host.rstrip("/")
        self.auth_config = auth_config
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = requests.Session()
        self._base_url = f"{self.host}/api/rest"
        self._connect_client: Optional["RapidIdentityConnect"] = None

        logger.debug(f"RapidIdentity client initialized for host: {self.host}")

    @classmethod
    def with_api_key(
        cls,
        host: str,
        api_key: str,
        verify_ssl: bool = True,
        timeout: int = 30,
    ):
        """
        Create client with API Key authentication.

        Args:
            host: The RapidIdentity host URL
            api_key: The API key
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds

        Returns:
            RapidIdentityClient instance
        """
        auth_config = AuthConfig(auth_type="api_key", api_key=api_key)
        return cls(host, auth_config, verify_ssl, timeout)

    @classmethod
    def with_basic_auth(
        cls,
        host: str,
        username: str,
        password: str,
        verify_ssl: bool = True,
        timeout: int = 30,
    ):
        """
        Create client with Basic authentication.

        Args:
            host: The RapidIdentity host URL
            username: Username for authentication
            password: Password for authentication
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds

        Returns:
            RapidIdentityClient instance
        """
        auth_config = AuthConfig(auth_type="basic", username=username, password=password)
        return cls(host, auth_config, verify_ssl, timeout)

    @classmethod
    def with_oauth2(
        cls,
        host: str,
        access_token: str,
        verify_ssl: bool = True,
        timeout: int = 30,
    ):
        """
        Create client with OAuth2 authentication.

        Args:
            host: The RapidIdentity host URL
            access_token: OAuth2 access token
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds

        Returns:
            RapidIdentityClient instance
        """
        auth_config = AuthConfig(auth_type="oauth2", access_token=access_token)
        return cls(host, auth_config, verify_ssl, timeout)

    @classmethod
    def from_config(cls, config: "rapididentity.config.Config") -> "RapidIdentityClient":
        """
        Create a client instance using a :class:`rapididentity.config.Config` object.

        This is a convenience wrapper used by example scripts and tests. It
        extracts the host, authentication configuration, SSL verification, and
        timeout values from the given configuration object.

        Args:
            config: Configuration instance

        Returns:
            RapidIdentityClient instance
        """
        host = config.get_host()
        auth_kwargs = config.get_auth_config()
        verify_ssl = config.get_verify_ssl()
        timeout = config.get_timeout()

        # auth_kwargs already contains auth_type plus any required credentials
        auth_config = AuthConfig(**auth_kwargs)  # type: ignore[arg-type]
        return cls(host, auth_config, verify_ssl, timeout)

    def _build_url(self, endpoint: str) -> str:
        """
        Build full URL for an endpoint.

        Args:
            endpoint: The API endpoint path

        Returns:
            Full URL for the endpoint
        """
        endpoint = endpoint.lstrip("/")
        return urljoin(self._base_url + "/", endpoint)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Handle API response.

        Args:
            response: The requests Response object

        Returns:
            Parsed response data

        Raises:
            AuthenticationError: For 401/403 responses
            NotFoundError: For 404 responses
            APIError: For other error responses
        """
        if response.status_code == 401:
            logger.error("Authentication failed")
            raise AuthenticationError("Authentication failed. Check your credentials.")

        if response.status_code == 403:
            logger.error("Access forbidden")
            raise AuthenticationError("Access forbidden. Check your permissions.")

        if response.status_code == 404:
            logger.warning(f"Resource not found: {response.url}")
            raise NotFoundError(f"Resource not found: {response.url}")

        if response.status_code >= 400:
            try:
                error_data = response.json()
            except Exception:
                error_data = {"message": response.text}

            logger.error(f"API error {response.status_code}: {error_data}")
            raise APIError(
                response.status_code,
                str(error_data.get("message", response.text)),
                error_data,
            )

        try:
            return response.json()
        except Exception:
            return {"data": response.text}

    def request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        raw_data: Optional[Union[str, bytes]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make a request to the RapidIdentity API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path
            data: JSON request body data (for POST/PUT/PATCH)
            raw_data: Raw request body data (e.g., XML string)
            params: Query parameters
            **kwargs: Additional arguments to pass to requests

        Returns:
            Parsed response data

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails
            APIError: If API returns an error
        """
        url = self._build_url(endpoint)
        headers = self.auth_config.get_headers()
        # Only update default headers when a non-None mapping is provided
        extra_headers = kwargs.pop("headers", None)
        if extra_headers:
            headers.update(extra_headers)

        try:
            logger.debug("HTTP request: %s %s", method, url)
            logger.debug("    headers: %s", headers)
            if params:
                logger.debug("    params: %s", params)
            if data:
                logger.debug("    data: %s", data)
            if raw_data:
                logger.debug("    raw_data: <provided>")

            if data is not None and raw_data is not None:
                raise ValidationError("Provide either data or raw_data, not both")

            request_payload: Dict[str, Any] = {
                "method": method,
                "url": url,
                "params": params,
                "headers": headers,
                "verify": self.verify_ssl,
                "timeout": self.timeout,
                **kwargs,
            }

            if raw_data is not None:
                request_payload["data"] = raw_data
            elif data is not None:
                request_payload["json"] = data

            response = self.session.request(**request_payload)

            # log response details before handling
            logger.debug("HTTP response status: %s", response.status_code)
            try:
                logger.debug("HTTP response body: %s", response.text)
            except Exception:
                logger.debug("HTTP response body: <could not decode>")

            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            raise ConnectionError(f"Failed to connect to {self.host}") from e
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            raise ConnectionError(f"Request timeout after {self.timeout}s") from e

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make a GET request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            **kwargs: Additional request parameters

        Returns:
            Parsed response data
        """
        return self.request("GET", endpoint, params=params, **kwargs)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make a POST request.

        Args:
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            **kwargs: Additional request parameters

        Returns:
            Parsed response data
        """
        return self.request("POST", endpoint, data=data, params=params, **kwargs)

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make a PUT request.

        Args:
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            **kwargs: Additional request parameters

        Returns:
            Parsed response data
        """
        return self.request("PUT", endpoint, data=data, params=params, **kwargs)

    def patch(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make a PATCH request.

        Args:
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters
            **kwargs: Additional request parameters

        Returns:
            Parsed response data
        """
        return self.request("PATCH", endpoint, data=data, params=params, **kwargs)

    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Make a DELETE request.

        Args:
            endpoint: API endpoint path
            params: Query parameters
            **kwargs: Additional request parameters

        Returns:
            Parsed response data
        """
        return self.request("DELETE", endpoint, params=params, **kwargs)

    def close(self) -> None:
        """Close the session and cleanup resources."""
        if self.session:
            self.session.close()
            logger.debug("Session closed")

    @property
    def connect(self) -> "RapidIdentityConnect":
        """Access RapidIdentity Connect endpoints through this client."""
        if self._connect_client is None:
            from rapididentity.connect import RapidIdentityConnect

            self._connect_client = RapidIdentityConnect(self)
        return self._connect_client

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
