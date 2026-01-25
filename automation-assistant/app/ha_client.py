"""Home Assistant API client using Supervisor API."""

import asyncio
import logging
from typing import Any, Optional

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
        self._session: Optional[aiohttp.ClientSession] = None

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
        ws_url = config.ha_ws_url

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

    async def create_or_update_automation(
        self, automation_id: str, automation_config: dict[str, Any]
    ) -> dict[str, Any]:
        """Create or update an automation in Home Assistant.

        Uses the /api/config/automation/config/{id} endpoint to save
        the automation configuration directly to HA.

        Args:
            automation_id: The unique ID for the automation
            automation_config: The automation configuration dict

        Returns:
            Dict with 'success' and optionally 'error' keys
        """
        session = await self._get_session()
        url = f"{self.ha_url}/api/config/automation/config/{automation_id}"

        try:
            async with session.post(url, json=automation_config) as response:
                if response.status == 200:
                    return {"success": True}
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to save automation: {response.status} - {error_text}")
                    return {"success": False, "error": error_text}
        except aiohttp.ClientError as e:
            logger.error(f"Failed to save automation: {e}")
            return {"success": False, "error": str(e)}

    async def reload_automations(self) -> bool:
        """Reload automations in Home Assistant.

        Calls the automation.reload service to make HA pick up changes.

        Returns:
            True if reload was successful, False otherwise
        """
        session = await self._get_session()
        url = f"{self.ha_url}/api/services/automation/reload"

        try:
            async with session.post(url, json={}) as response:
                if response.status == 200:
                    logger.info("Automations reloaded successfully")
                    return True
                else:
                    logger.error(f"Failed to reload automations: {response.status}")
                    return False
        except aiohttp.ClientError as e:
            logger.error(f"Failed to reload automations: {e}")
            return False

    async def get_automation_config(self, automation_id: str) -> Optional[dict[str, Any]]:
        """Get the configuration of a specific automation.

        Args:
            automation_id: The automation ID to fetch

        Returns:
            The automation config dict, or None if not found
        """
        session = await self._get_session()
        url = f"{self.ha_url}/api/config/automation/config/{automation_id}"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return None
                else:
                    logger.error(f"Failed to get automation config: {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"Failed to get automation config: {e}")
            return None

    async def list_automations(self) -> list[dict[str, Any]]:
        """List all automations via the HA REST API.

        Gets automation info from entity states and their attributes.
        Used for local development when we can't read automations.yaml directly.

        Returns:
            List of automation config dicts with basic info (id, alias, mode, entity_id)
        """
        states = await self.get_states()
        automation_states = [s for s in states if s.get("entity_id", "").startswith("automation.")]

        automations = []
        for state in automation_states:
            entity_id = state.get("entity_id", "")
            attrs = state.get("attributes", {})
            # The real automation ID is in attributes.id
            auto_id = attrs.get("id", "")
            if not auto_id:
                # Fall back to entity_id suffix if no id attribute
                auto_id = entity_id.replace("automation.", "")

            automations.append({
                "id": auto_id,
                "alias": attrs.get("friendly_name", "Unnamed Automation"),
                "mode": attrs.get("mode", "single"),
                "_entity_id": entity_id,  # Store for enrichment lookups
            })

        logger.info(f"Fetched {len(automations)} automations via API")
        return automations

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
