"""Async client for the Zodiac iAquaLink cloud API."""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import aiohttp

from .const import (
    API_KEY,
    API_SECRET,
    HEAT_PUMP_DEVICE_TYPES,
    LOGIN_URL,
    SHADOW_URL,
    SYSTEMS_URL,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "okhttp/3.14.7",
}

_TIMEOUT = aiohttp.ClientTimeout(total=20)


class IAquaLinkAuthError(Exception):
    """Authentication failed."""


class IAquaLinkApiError(Exception):
    """Generic transport / protocol error."""


def _sign(serial: str, user_id: str) -> str:
    msg = f"{serial.upper()},{user_id}".encode()
    return hmac.new(API_SECRET.encode(), msg, hashlib.sha1).hexdigest()


class IAquaLinkClient:
    """Minimal client covering login, device list, and shadow read."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        password: str,
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._user_id: str | None = None
        self._auth_token: str | None = None
        self._id_token: str | None = None

    async def login(self) -> None:
        payload = {"apiKey": API_KEY, "email": self._email, "password": self._password}
        try:
            async with self._session.post(
                LOGIN_URL,
                json=payload,
                headers=DEFAULT_HEADERS,
                timeout=_TIMEOUT,
            ) as resp:
                if resp.status in (401, 403):
                    raise IAquaLinkAuthError(f"Login rejected: HTTP {resp.status}")
                resp.raise_for_status()
                data = await resp.json()
        except aiohttp.ClientError as err:
            raise IAquaLinkApiError(f"Login request failed: {err}") from err

        try:
            self._user_id = data["id"]
            self._auth_token = data["authentication_token"]
            self._id_token = data["userPoolOAuth"]["IdToken"]
        except (KeyError, TypeError) as err:
            raise IAquaLinkAuthError(f"Unexpected login response shape: {err}") from err

    async def get_systems(self) -> list[dict[str, Any]]:
        if not self._auth_token or not self._user_id:
            await self.login()
        params = {
            "api_key": API_KEY,
            "authentication_token": self._auth_token,
            "user_id": self._user_id,
        }
        try:
            async with self._session.get(
                SYSTEMS_URL,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as err:
            raise IAquaLinkApiError(f"Systems request failed: {err}") from err

    async def get_shadow(self, serial: str) -> dict[str, Any]:
        if not self._id_token or not self._user_id:
            await self.login()
        url = SHADOW_URL.format(serial=serial)

        async def _do_get() -> dict[str, Any]:
            params = {"signature": _sign(serial, self._user_id)}
            headers = {**DEFAULT_HEADERS, "Authorization": self._id_token}
            async with self._session.get(
                url, params=params, headers=headers, timeout=_TIMEOUT
            ) as resp:
                # 401/403 here typically means the Cognito IdToken expired;
                # re-login once and let the caller retry.
                if resp.status in (401, 403):
                    raise IAquaLinkAuthError(f"Shadow rejected: HTTP {resp.status}")
                resp.raise_for_status()
                return await resp.json()

        try:
            return await _do_get()
        except IAquaLinkAuthError:
            await self.login()
            return await _do_get()
        except aiohttp.ClientError as err:
            raise IAquaLinkApiError(f"Shadow request failed: {err}") from err

    async def discover_heat_pumps(self) -> list[dict[str, Any]]:
        systems = await self.get_systems()
        return [s for s in systems if s.get("device_type") in HEAT_PUMP_DEVICE_TYPES]