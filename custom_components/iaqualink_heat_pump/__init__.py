"""Zodiac iAquaLink Heat Pump integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo

from .api import IAquaLinkApiError, IAquaLinkAuthError, IAquaLinkClient
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN
from .coordinator import ZodiacCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = IAquaLinkClient(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])

    try:
        await client.login()
        pumps = await client.discover_heat_pumps()
    except IAquaLinkAuthError as err:
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except IAquaLinkApiError as err:
        raise ConfigEntryNotReady(f"Cannot reach iAquaLink: {err}") from err

    if not pumps:
        raise ConfigEntryNotReady("No heat pump found on this account")

    pump = pumps[0]
    serial = pump["serial_number"]
    device_info = DeviceInfo(
        identifiers={(DOMAIN, serial)},
        name=pump.get("name") or f"Zodiac Heat Pump {serial}",
        manufacturer="Zodiac",
        model=pump.get("device_type", "heat pump"),
        serial_number=serial,
    )

    coordinator = ZodiacCoordinator(hass, entry, client, serial, device_info)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded