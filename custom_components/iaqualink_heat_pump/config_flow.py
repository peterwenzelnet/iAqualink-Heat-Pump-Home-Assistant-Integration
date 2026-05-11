"""Config flow for Zodiac iAquaLink."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IAquaLinkApiError, IAquaLinkAuthError, IAquaLinkClient
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): str,
    }
)


class ZodiacConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _async_try_login(
        self, email: str, password: str
    ) -> tuple[dict[str, str], list[dict[str, Any]]]:
        """Attempt to log in and discover heat pumps.

        Returns (errors, pumps). Errors is empty on success.
        """
        errors: dict[str, str] = {}
        pumps: list[dict[str, Any]] = []
        session = async_get_clientsession(self.hass)
        client = IAquaLinkClient(session, email, password)
        try:
            await client.login()
            pumps = await client.discover_heat_pumps()
        except IAquaLinkAuthError:
            errors["base"] = "invalid_auth"
        except IAquaLinkApiError:
            errors["base"] = "cannot_connect"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error during iAquaLink login")
            errors["base"] = "unknown"
        else:
            if not pumps:
                errors["base"] = "no_heat_pump"
        return errors, pumps

    def _get_entry(self) -> ConfigEntry | None:
        entry_id = self.context.get("entry_id")
        if entry_id is None:
            return None
        return self.hass.config_entries.async_get_entry(entry_id)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, _pumps = await self._async_try_login(
                user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )
            if not errors:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"iAquaLink ({user_input[CONF_EMAIL]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Triggered automatically when stored credentials are rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_entry()
        if entry is None:
            return self.async_abort(reason="unknown")

        errors: dict[str, str] = {}
        email = entry.data[CONF_EMAIL]

        if user_input is not None:
            errors, _pumps = await self._async_try_login(
                email, user_input[CONF_PASSWORD]
            )
            if not errors:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            description_placeholders={"email": email},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """User-triggered popup to update email/password from the integration menu."""
        entry = self._get_entry()
        if entry is None:
            return self.async_abort(reason="unknown")

        errors: dict[str, str] = {}

        if user_input is not None:
            errors, _pumps = await self._async_try_login(
                user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
            )
            if not errors:
                new_unique_id = user_input[CONF_EMAIL].lower()
                if new_unique_id != entry.unique_id:
                    existing = await self.async_set_unique_id(new_unique_id)
                    if existing is not None and existing.entry_id != entry.entry_id:
                        return self.async_abort(reason="already_configured")
                self.hass.config_entries.async_update_entry(
                    entry,
                    data=user_input,
                    title=f"iAquaLink ({user_input[CONF_EMAIL]})",
                    unique_id=new_unique_id,
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_EMAIL, default=entry.data.get(CONF_EMAIL, "")
                ): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )
