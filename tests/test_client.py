"""
Unit tests for RapidIdentity Client.
"""

import sys, os
# ensure local package is available when running tests directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import Mock, patch, MagicMock
from rapididentity import RapidIdentityClient
from rapididentity.auth import AuthConfig
from rapididentity.exceptions import (
    AuthenticationError,
    ValidationError,
    NotFoundError,
    APIError,
)


class TestRapidIdentityClient:
    """Test cases for RapidIdentityClient."""

    def test_client_initialization_with_api_key(self):
        """Test client initialization with API key."""
        client = RapidIdentityClient.with_api_key(
            host="https://api.example.com",
            api_key="test-key",
        )
        assert client.host == "https://api.example.com"
        assert client.auth_config.auth_type == "api_key"

    def test_client_initialization_with_basic_auth(self):
        """Test client initialization with basic auth."""
        client = RapidIdentityClient.with_basic_auth(
            host="https://api.example.com",
            username="testuser",
            password="testpass",
        )
        assert client.host == "https://api.example.com"
        assert client.auth_config.auth_type == "basic"

    def test_client_initialization_invalid_host(self):
        """Test client initialization with invalid host."""
        with pytest.raises(ValidationError):
            RapidIdentityClient(
                host="",
                auth_config=AuthConfig(auth_type="api_key", api_key="test"),
            )

    def test_build_url(self):
        """Test URL building."""
        client = RapidIdentityClient.with_api_key(
            host="https://api.example.com",
            api_key="test-key",
        )
        url = client._build_url("/users")
        assert "api/rest" in url
        assert "users" in url

    def test_get_request(self):
        """Test GET request."""
        client = RapidIdentityClient.with_api_key(
            host="https://api.example.com",
            api_key="test-key",
        )

        with patch.object(client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": [{"id": 1, "name": "Test"}]}
            mock_request.return_value = mock_response

            result = client.get("/users")
            assert result["data"][0]["id"] == 1

    def test_post_request(self):
        """Test POST request."""
        client = RapidIdentityClient.with_api_key(
            host="https://api.example.com",
            api_key="test-key",
        )

        with patch.object(client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"id": 1, "name": "New User"}}
            mock_request.return_value = mock_response

            result = client.post("/users", data={"name": "New User"})
            assert result["data"]["id"] == 1

    def test_request_raw_data(self):
        """Test request with raw body data (e.g., XML)."""
        client = RapidIdentityClient.with_api_key(
            host="https://api.example.com",
            api_key="test-key",
        )

        with patch.object(client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": "ok"}
            mock_request.return_value = mock_response

            client.request("POST", "/xml", raw_data="<root/>", headers={"Content-Type": "application/xml"})

            _, kwargs = mock_request.call_args
            assert kwargs["data"] == "<root/>"
            assert "json" not in kwargs

    def test_authentication_error(self):
        """Test authentication error handling."""
        client = RapidIdentityClient.with_api_key(
            host="https://api.example.com",
            api_key="invalid-key",
        )

        with patch.object(client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_request.return_value = mock_response

            with pytest.raises(AuthenticationError):
                client.get("/users")

    def test_not_found_error(self):
        """Test 404 error handling."""
        client = RapidIdentityClient.with_api_key(
            host="https://api.example.com",
            api_key="test-key",
        )

        with patch.object(client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.url = "https://api.example.com/api/rest/users/999"
            mock_request.return_value = mock_response

            with pytest.raises(NotFoundError):
                client.get("/users/999")

    def test_api_error(self):
        """Test API error handling."""
        client = RapidIdentityClient.with_api_key(
            host="https://api.example.com",
            api_key="test-key",
        )

        with patch.object(client.session, "request") as mock_request:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.json.return_value = {"message": "Internal Server Error"}
            mock_request.return_value = mock_response

            with pytest.raises(APIError):
                client.get("/users")
    def test_from_config_helper(self):
        """Ensure that from_config constructs a client matching manual args."""
        from rapididentity.config import Config

        cfg = Config()
        cfg.config = {  # bypass environment loading
            "host": "https://api.example.com",
            "auth_type": "api_key",
            "api_key": "foobar",
            "verify_ssl": False,
            "timeout": 10,
        }
        client = RapidIdentityClient.from_config(cfg)
        assert client.host == "https://api.example.com"
        assert client.auth_config.auth_type == "api_key"
        assert client.verify_ssl is False
        assert client.timeout == 10

    def test_connect_get_actions_from_config_returns_data(self):
        """Ensure the connect facade returns raw data from /admin/connect/actions."""
        from rapididentity.config import Config

        cfg = Config()
        cfg.config = {
            "host": "https://api.example.com",
            "auth_type": "api_key",
            "api_key": "foobar",
            "verify_ssl": True,
            "timeout": 10,
        }

        client = RapidIdentityClient.from_config(cfg)
        with patch.object(client, "request", return_value={"data": "<xml>ok</xml>"}) as mock_request:
            result = client.connect.get_actions()

        assert result == "<xml>ok</xml>"
        mock_request.assert_called_once_with(
            "GET",
            "/admin/connect/actions",
            params={},
        )

    def test_connect_get_actions_passes_project_and_metadata_only(self):
        """Ensure project and metaDataOnly are mapped to GET query params."""
        from rapididentity.config import Config

        cfg = Config()
        cfg.config = {
            "host": "https://api.example.com",
            "auth_type": "api_key",
            "api_key": "foobar",
            "verify_ssl": True,
            "timeout": 10,
        }

        client = RapidIdentityClient.from_config(cfg)
        with patch.object(client, "request", return_value={"data": []}) as mock_request:
            client.connect.get_actions(project="my-project", metaDataOnly=True)

        mock_request.assert_called_once_with(
            "GET",
            "/admin/connect/actions",
            params={"project": "my-project", "metaDataOnly": "true"},
        )

    def test_connect_post_action_posts_xml(self):
        """Ensure connect.post_action sends XML payload to /admin/connect/actions."""
        from rapididentity.config import Config

        cfg = Config()
        cfg.config = {
            "host": "https://api.example.com",
            "auth_type": "api_key",
            "api_key": "foobar",
            "verify_ssl": True,
            "timeout": 10,
        }

        client = RapidIdentityClient.from_config(cfg)
        with patch.object(client, "request", return_value={"data": {"status": "ok"}}) as mock_request:
            result = client.connect.post_action("<actionSetVersion name='x'/>")

        assert result == {"status": "ok"}
        mock_request.assert_called_once_with(
            "POST",
            "/admin/connect/actions",
            raw_data="<actionSetVersion name='x'/>",
            headers={"Content-Type": "application/xml", "Accept": "application/json"},
        )

    def test_context_manager(self):
        """Test context manager functionality."""
        with RapidIdentityClient.with_api_key(
            host="https://api.example.com",
            api_key="test-key",
        ) as client:
            assert client is not None
            assert client.host == "https://api.example.com"


class TestAuthentication:
    """Test authentication configurations."""

    def test_api_key_auth_headers(self):
        """Test API key auth headers."""
        from rapididentity.auth import APIKeyAuth

        auth = APIKeyAuth("test-key")
        headers = auth.get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-key"

    def test_basic_auth_headers(self):
        """Test basic auth headers."""
        from rapididentity.auth import BasicAuth

        auth = BasicAuth("user", "pass")
        headers = auth.get_headers()
        assert "Authorization" in headers
        assert "Basic" in headers["Authorization"]

    def test_oauth2_headers(self):
        """Test OAuth2 headers."""
        from rapididentity.auth import OAuth2Session

        auth = OAuth2Session("test-token")
        headers = auth.get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token"


class TestValidators:
    """Test validation utilities."""

    def test_email_validation(self):
        """Test email validation."""
        from rapididentity.utils import validate_email

        assert validate_email("user@example.com") is True
        assert validate_email("invalid.email@") is False
        assert validate_email("user@domain.co.uk") is True

    def test_username_validation(self):
        """Test username validation."""
        from rapididentity.utils import validate_username

        assert validate_username("valid_user") is True
        assert validate_username("u") is False  # Too short
        assert validate_username("user.name") is True
        assert validate_username("user-name") is True

    def test_url_validation(self):
        """Test URL validation."""
        from rapididentity.utils import validate_url

        assert validate_url("https://example.com") is True
        assert validate_url("http://example.com") is True
        assert validate_url("ftp://example.com") is False
        assert validate_url("not-a-url") is False
