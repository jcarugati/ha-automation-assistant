"""Home Assistant API client using Supervisor API."""

import asyncio
import logging
from typing import Any

import aiohttp
import websockets

from .config import config

logger = logging.getLogger(__name__)


class HAClient:
    """Client for interacting with Home Assistant via Supervisor API."""

    def __init__(self):
        self.supervisor_url = config.supervisor_base_url
        self.ha_url = config.ha_base_url
        self.token = config.supervisor_token
        self._session: aiohttp.ClientSession | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session

    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_states(self) -> list[dict[str, Any]]:
        """Fetch all entity states from Home Assistant."""
        session = await self._get_session()
        url = f"{self.ha_url}/api/states"
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch states: {e}")
            return []

    async def get_services(self) -> dict[str, Any]:
        """Fetch available services from Home Assistant."""
        session = await self._get_session()
        url = f"{self.ha_url}/api/services"
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch services: {e}")
            return {}

    async def get_config(self) -> dict[str, Any]:
        """Fetch Home Assistant configuration."""
        session = await self._get_session()
        url = f"{self.ha_url}/api/config"
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Failed to fetch config: {e}")
            return {}

    async def _websocket_command(self, command_type: str) -> list[dict[str, Any]]:
        """Execute a WebSocket command and return the result."""
        ws_url = f"ws://supervisor/core/websocket"

        try:
            async with websockets.connect(
                ws_url,
                additional_headers={"Authorization": f"Bearer {self.token}"},
                max_size=10 * 1024 * 1024,  # 10MB limit for large entity registries
            ) as ws:
                # Wait for auth_required message
                auth_required = await asyncio.wait_for(ws.recv(), timeout=10)
                logger.debug(f"Auth required: {auth_required}")

                # Send auth
                await ws.send(
                    '{"type": "auth", "access_token": "' + self.token + '"}'
                )

                # Wait for auth_ok
                auth_result = await asyncio.wait_for(ws.recv(), timeout=10)
                logger.debug(f"Auth result: {auth_result}")

                # Send command
                await ws.send(f'{{"id": 1, "type": "{command_type}"}}')

                # Get result
                result = await asyncio.wait_for(ws.recv(), timeout=30)
                import json

                data = json.loads(result)
                return data.get("result", [])

        except Exception as e:
            logger.error(f"WebSocket command {command_type} failed: {e}")
            return []

    async def get_devices(self) -> list[dict[str, Any]]:
        """Fetch device registry via WebSocket."""
        return await self._websocket_command("config/device_registry/list")

    async def get_areas(self) -> list[dict[str, Any]]:
        """Fetch area registry via WebSocket."""
        return await self._websocket_command("config/area_registry/list")

    async def get_entity_registry(self) -> list[dict[str, Any]]:
        """Fetch entity registry via WebSocket."""
        return await self._websocket_command("config/entity_registry/list")

    async def get_full_context(self) -> dict[str, Any]:
        """Fetch all context data from Home Assistant.

        Filters out unavailable/disabled entities and devices to ensure
        only active resources are included in the context.
        """
        # Run all requests concurrently
        states, services, ha_config, devices, areas, entities = await asyncio.gather(
            self.get_states(),
            self.get_services(),
            self.get_config(),
            self.get_devices(),
            self.get_areas(),
            self.get_entity_registry(),
            return_exceptions=True,
        )

        # Handle any exceptions
        if isinstance(states, Exception):
            logger.error(f"Failed to get states: {states}")
            states = []
        if isinstance(services, Exception):
            logger.error(f"Failed to get services: {services}")
            services = {}
        if isinstance(ha_config, Exception):
            logger.error(f"Failed to get config: {ha_config}")
            ha_config = {}
        if isinstance(devices, Exception):
            logger.error(f"Failed to get devices: {devices}")
            devices = []
        if isinstance(areas, Exception):
            logger.error(f"Failed to get areas: {areas}")
            areas = []
        if isinstance(entities, Exception):
            logger.error(f"Failed to get entity registry: {entities}")
            entities = []

        # Filter out unavailable/unknown states
        unavailable_states = {"unavailable", "unknown"}
        active_states = [
            s for s in states
            if s.get("state", "").lower() not in unavailable_states
        ]
        logger.debug(f"Filtered states: {len(states)} -> {len(active_states)} (removed unavailable/unknown)")

        # Get set of disabled entity IDs from registry
        disabled_entity_ids = {
            e.get("entity_id")
            for e in entities
            if e.get("disabled_by") is not None
        }

        # Further filter states to remove disabled entities
        active_states = [
            s for s in active_states
            if s.get("entity_id") not in disabled_entity_ids
        ]
        logger.debug(f"After removing disabled entities: {len(active_states)}")

        # Filter out disabled devices
        active_devices = [
            d for d in devices
            if d.get("disabled_by") is None
        ]
        logger.debug(f"Filtered devices: {len(devices)} -> {len(active_devices)} (removed disabled)")

        # Filter entity registry to only include enabled entities
        active_entities = [
            e for e in entities
            if e.get("disabled_by") is None
        ]

        return {
            "states": active_states,
            "services": services,
            "config": ha_config,
            "devices": active_devices,
            "areas": areas,
            "entity_registry": active_entities,
        }


# Singleton instance
ha_client = HAClient()
