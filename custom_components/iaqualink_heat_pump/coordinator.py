"""Data update coordinator for Zodiac iAquaLink."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import IAquaLinkApiError, IAquaLinkAuthError, IAquaLinkClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ZodiacCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls the shadow for a single heat pump serial."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: IAquaLinkClient,
        serial: str,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {serial}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.entry = entry
        self.client = client
        self.serial = serial
        self.device_info = device_info

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.get_shadow(self.serial)
        except IAquaLinkAuthError as err:
            raise ConfigEntryAuthFailed(f"Authentication error: {err}") from err
        except IAquaLinkApiError as err:
            raise UpdateFailed(f"API error: {err}") from err