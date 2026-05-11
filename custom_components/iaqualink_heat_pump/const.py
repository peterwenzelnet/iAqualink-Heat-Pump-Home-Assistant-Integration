"""Constants for the iAqualink Heat Pump (Unofficial) integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "iaqualink_heat_pump"

# Public iAquaLink mobile-app constants (not user secrets).
API_KEY = "EOOEMOW4YR6QNB07"
API_SECRET = "cj7iYKjiKxOqiLcN65PffA"

LOGIN_URL = "https://prod.zodiac-io.com/users/v1/login"
SYSTEMS_URL = "https://r-api.iaqualink.net/devices.json"
SHADOW_URL = "https://prod.zodiac-io.com/devices/v2/{serial}/shadow"

HEAT_PUMP_DEVICE_TYPES = ("zs500", "hpm")

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

CONF_EMAIL = "email"
CONF_PASSWORD = "password"