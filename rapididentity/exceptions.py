"""
Exception classes for RapidIdentity API interactions.
"""


class RapidIdentityError(Exception):
    """Base exception for all RapidIdentity API errors."""

    pass


class AuthenticationError(RapidIdentityError):
    """Raised when authentication fails."""

    pass


class ValidationError(RapidIdentityError):
    """Raised when validation of request data fails."""

    pass


class NotFoundError(RapidIdentityError):
    """Raised when a requested resource is not found (404)."""

    pass


class APIError(RapidIdentityError):
    """Raised for API-level errors (5xx, 4xx)."""

    def __init__(self, status_code, message, response_data=None):
        self.status_code = status_code
        self.message = message
        self.response_data = response_data
        super().__init__(f"API Error {status_code}: {message}")


class ConnectionError(RapidIdentityError):
    """Raised when connection to the API fails."""

    pass
