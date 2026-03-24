"""
RapidIdentity API Client Library

A Python library for interacting with RapidIdentity REST APIs.
"""

from rapididentity.client import RapidIdentityClient
from rapididentity.exceptions import (
    RapidIdentityError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    APIError,
)
from rapididentity.config import Config
# Resource wrappers removed — use RapidIdentityClient directly

__version__ = "0.1.0"
__author__ = "RapidIdentity Tools Contributors"

__all__ = [
    "RapidIdentityClient",
    "RapidIdentityError",
    "AuthenticationError",
    "NotFoundError",
    "ValidationError",
    "APIError",
    "Config",
    
]
