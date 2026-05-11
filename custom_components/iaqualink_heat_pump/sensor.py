"""Sensors auto-discovered from the Zodiac iAquaLink shadow document."""
from __future__ import annotations

import logging
from typing import Any, Iterator

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPressure, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZodiacCoordinator

_LOGGER = logging.getLogger(__name__)

# AWS IoT shadow envelope keys that carry no user-facing telemetry.
SKIPPED_KEYS = {"timestamp", "version", "metadata", "delta", "clientToken"}

TEMPERATURE_HINTS = ("temp", "temperature", "tset", "tair", "twater", "setpoint")
PRESSURE_HINTS = ("pressure", "bar")
PERCENT_HINTS = ("humidity", "percent", "level")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZodiacCoordinator = hass.data[DOMAIN][entry.entry_id]

    known_paths: set[tuple[str, ...]] = set()

    @callback
    def _create_new_entities() -> None:
        new: list[ShadowSensor] = []
        for path, _ in _iter_leaves(coordinator.data or {}):
            if path in known_paths or not path:
                continue
            known_paths.add(path)
            new.append(ShadowSensor(coordinator, path))
        if new:
            async_add_entities(new)

    _create_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_create_new_entities))


def _iter_leaves(
    data: Any, path: tuple[str, ...] = ()
) -> Iterator[tuple[tuple[str, ...], Any]]:
    if isinstance(data, dict):
        # Unwrap AWS IoT shadow envelope so paths don't carry "state.reported.*" noise.
        if path == () and isinstance(data.get("state"), dict):
            reported = data["state"].get("reported")
            if isinstance(reported, dict):
                yield from _iter_leaves(reported, path)
                return
        for key, value in data.items():
            if key in SKIPPED_KEYS:
                continue
            yield from _iter_leaves(value, path + (str(key),))
    elif _looks_like_sensor_value(data):
        yield path, data


def _looks_like_sensor_value(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def _infer_unit_and_class(
    path: tuple[str, ...],
) -> tuple[str | None, SensorDeviceClass | None, SensorStateClass | None]:
    name = "_".join(path).lower()
    if any(h in name for h in TEMPERATURE_HINTS):
        return (
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            SensorStateClass.MEASUREMENT,
        )
    if any(h in name for h in PRESSURE_HINTS):
        return (
            UnitOfPressure.BAR,
            SensorDeviceClass.PRESSURE,
            SensorStateClass.MEASUREMENT,
        )
    if any(h in name for h in PERCENT_HINTS):
        return PERCENTAGE, None, SensorStateClass.MEASUREMENT
    return None, None, None


class ShadowSensor(CoordinatorEntity[ZodiacCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ZodiacCoordinator, path: tuple[str, ...]) -> None:
        super().__init__(coordinator)
        self._path = path
        self._attr_unique_id = f"{coordinator.serial}_{'_'.join(path)}"
        self._attr_name = " ".join(path).replace("_", " ").title()
        self._attr_device_info = coordinator.device_info

        sample = self._read(coordinator.data)
        if isinstance(sample, (int, float)) and not isinstance(sample, bool):
            unit, device_class, state_class = _infer_unit_and_class(path)
            self._attr_native_unit_of_measurement = unit
            self._attr_device_class = device_class
            self._attr_state_class = state_class

    def _read(self, data: Any) -> Any:
        # Mirror the unwrap done in _iter_leaves so the path resolves correctly.
        if isinstance(data, dict) and isinstance(data.get("state"), dict):
            reported = data["state"].get("reported")
            if isinstance(reported, dict):
                data = reported
        node: Any = data
        for key in self._path:
            if not isinstance(node, dict) or key not in node:
                return None
            node = node[key]
        return node

    @property
    def native_value(self) -> Any:
        value = self._read(self.coordinator.data)
        if isinstance(value, bool):
            return "on" if value else "off"
        return value