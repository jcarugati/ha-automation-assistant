"""Configuration management for the add-on."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    claude_api_key: str
    model: str
    log_level: str
    supervisor_token: str
    ha_base_url: str = "http://supervisor/core"
    supervisor_base_url: str = "http://supervisor"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            claude_api_key=os.environ.get("CLAUDE_API_KEY", ""),
            model=os.environ.get("MODEL", "claude-sonnet-4-20250514"),
            log_level=os.environ.get("LOG_LEVEL", "info"),
            supervisor_token=os.environ.get("SUPERVISOR_TOKEN", ""),
        )

    @property
    def is_configured(self) -> bool:
        """Check if the add-on is properly configured."""
        return bool(self.claude_api_key)


config = Config.from_env()
