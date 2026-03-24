"""
Configuration module for RapidIdentity API client.

Handles loading and managing configuration from environment variables and files.
"""

import os
from typing import Dict, Any, Optional
import json


class Config:
    """Configuration management for RapidIdentity client."""

    # Default settings
    DEFAULT_TIMEOUT = 30
    DEFAULT_VERIFY_SSL = True
    DEFAULT_TIER = "default"

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to JSON configuration file (optional)
        """
        self.config: Dict[str, Any] = {}
        self.load_from_env()
        if config_file:
            self.load_from_file(config_file)

    def load_from_env(self) -> None:
        """Load configuration from environment variables."""
        env_mapping = {
            "RAPIDIDENTITY_HOST": "host",
            "RAPIDIDENTITY_API_KEY": "api_key",
            "RAPIDIDENTITY_USERNAME": "username",
            "RAPIDIDENTITY_PASSWORD": "password",
            "RAPIDIDENTITY_AUTH_TYPE": "auth_type",
            "RAPIDIDENTITY_TIMEOUT": "timeout",
            "RAPIDIDENTITY_VERIFY_SSL": "verify_ssl",
            "RAPIDIDENTITY_TIER": "tier"
        }

        for env_var, config_key in env_mapping.items():
            value = os.getenv(env_var)
            if value:
                # Convert string values to appropriate types
                if config_key == "timeout":
                    self.config[config_key] = int(value)
                elif config_key == "verify_ssl":
                    self.config[config_key] = value.lower() in ("true", "1", "yes")
                else:
                    self.config[config_key] = value

    def load_from_file(self, config_file: str) -> None:
        """
        Load configuration from JSON file.

        Args:
            config_file: Path to JSON configuration file

        Raises:
            FileNotFoundError: If configuration file not found
            json.JSONDecodeError: If file is not valid JSON
        """
        with open(config_file, "r") as f:
            file_config = json.load(f)
        self.config.update(file_config)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def get_host(self) -> str:
        """Get RapidIdentity host URL."""
        host = self.get("host")
        if not host:
            raise ValueError("RapidIdentity host not configured")
        return host

    def get_auth_config(self) -> Dict[str, Any]:
        """Get authentication configuration."""
        auth_type = self.get("auth_type", "api_key")
        auth_config = {"auth_type": auth_type}

        if auth_type == "api_key":
            api_key = self.get("api_key")
            if not api_key:
                raise ValueError("API key not configured")
            auth_config["api_key"] = api_key

        elif auth_type == "basic":
            username = self.get("username")
            password = self.get("password")
            if not username or not password:
                raise ValueError("Username and password not configured")
            auth_config["username"] = username
            auth_config["password"] = password

        elif auth_type == "oauth2":
            access_token = self.get("access_token")
            if not access_token:
                raise ValueError("OAuth2 access token not configured")
            auth_config["access_token"] = access_token

        return auth_config

    def get_timeout(self) -> int:
        """Get request timeout."""
        return self.get("timeout", self.DEFAULT_TIMEOUT)

    def get_tier(self) -> int:
        """Get request tier."""
        return self.get("tier", self.DEFAULT_TIER)

    def get_verify_ssl(self) -> bool:
        """Get SSL verification setting."""
        return self.get("verify_ssl", self.DEFAULT_VERIFY_SSL)

    def to_dict(self) -> Dict[str, Any]:
        """
        Get all configuration as dictionary.

        Note: Does not include sensitive data like passwords.
        """
        safe_config = self.config.copy()
        sensitive_keys = ["password", "api_key", "access_token"]
        for key in sensitive_keys:
            if key in safe_config:
                del safe_config[key]
        return safe_config
