"""Configuration management for the add-on."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

# Read version from config.yaml
_config_yaml_path = Path(__file__).parent.parent / "config.yaml"
try:
    with open(_config_yaml_path) as f:
        _addon_config = yaml.safe_load(f)
    VERSION = _addon_config.get("version", "unknown")
except Exception:
    VERSION = "unknown"


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    claude_api_key: str
    model: str
    doctor_model: Optional[str]
    log_level: str
    supervisor_token: str
    ha_base_url: str = "http://supervisor/core"
    supervisor_base_url: str = "http://supervisor"
    ha_ws_url: str = "ws://supervisor/core/api/websocket"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.
        
        For local development, set HA_URL to your Home Assistant instance
        (e.g., http://192.168.1.100:8123) and SUPERVISOR_TOKEN to a 
        long-lived access token from HA.
        """
        ha_url = os.environ.get("HA_URL", "")
        if ha_url:
            ha_base_url = ha_url.rstrip("/")
            ws_url = ha_base_url.replace("http://", "ws://").replace("https://", "wss://")
            ha_ws_url = f"{ws_url}/api/websocket"
        else:
            ha_base_url = "http://supervisor/core"
            ha_ws_url = "ws://supervisor/core/api/websocket"
        
        return cls(
            claude_api_key=os.environ.get("CLAUDE_API_KEY", ""),
            model=os.environ.get("MODEL", "claude-sonnet-4-20250514"),
            doctor_model=os.environ.get("DOCTOR_MODEL", "").strip() or None,
            log_level=os.environ.get("LOG_LEVEL", "info"),
            supervisor_token=os.environ.get("SUPERVISOR_TOKEN", ""),
            ha_base_url=ha_base_url,
            ha_ws_url=ha_ws_url,
        )

    @property
    def is_configured(self) -> bool:
        """Check if the add-on is properly configured."""
        return bool(self.claude_api_key)

    @property
    def doctor_model_or_default(self) -> str:
        """Return the doctor model or fall back to the default model."""
        return self.doctor_model or self.model


config = Config.from_env()
