"""Curated sensors from the Zodiac iAquaLink shadow document."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZodiacCoordinator


def _tenth_degrees(value: Any) -> float | None:
    """Cloud reports tenths of a degree (e.g. 135 -> 13.5 °C)."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value / 10
    return None


@dataclass(frozen=True)
class ZodiacSensorSpec:
    path: tuple[str, ...]
    name: str
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    entity_category: EntityCategory | None = None
    icon: str | None = None
    transform: Callable[[Any], Any] | None = None


SENSORS: tuple[ZodiacSensorSpec, ...] = (
    ZodiacSensorSpec(
        path=("equipment", "hp_0", "sns_1", "value"),
        name="Water temperature",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        transform=_tenth_degrees,
    ),
    ZodiacSensorSpec(
        path=("equipment", "hp_0", "sns_2", "value"),
        name="Air temperature",
        unit=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        transform=_tenth_degrees,
    ),
    ZodiacSensorSpec(
        path=("dt",),
        name="Equipment ID",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
    ),
    ZodiacSensorSpec(
        path=("ip",),
        name="IP address",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:ip-network",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ZodiacCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        ZodiacShadowSensor(coordinator, spec) for spec in SENSORS
    ]
    entities.append(ZodiacLastUpdateSensor(coordinator))
    async_add_entities(entities)


class ZodiacShadowSensor(CoordinatorEntity[ZodiacCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: ZodiacCoordinator, spec: ZodiacSensorSpec
    ) -> None:
        super().__init__(coordinator)
        self._spec = spec
        self._attr_unique_id = f"{coordinator.serial}_{'_'.join(spec.path)}"
        self._attr_name = spec.name
        self._attr_device_info = coordinator.device_info
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class
        self._attr_entity_category = spec.entity_category
        self._attr_icon = spec.icon

    def _read(self) -> Any:
        data = self.coordinator.data
        # Unwrap AWS IoT shadow envelope: {"state": {"reported": {...}}}
        if isinstance(data, dict) and isinstance(data.get("state"), dict):
            reported = data["state"].get("reported")
            if isinstance(reported, dict):
                data = reported
        node: Any = data
        for key in self._spec.path:
            if not isinstance(node, dict) or key not in node:
                return None
            node = node[key]
        return node

    @property
    def native_value(self) -> Any:
        value = self._read()
        if self._spec.transform is not None:
            return self._spec.transform(value)
        return value


class ZodiacLastUpdateSensor(CoordinatorEntity[ZodiacCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Last update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: ZodiacCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial}_last_update"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> datetime | None:
        # Prefer the cloud's own shadow timestamp; fall back to the last
        # successful poll if the field is missing.
        data = self.coordinator.data
        if isinstance(data, dict):
            ts = data.get("timestamp")
            if isinstance(ts, (int, float)) and not isinstance(ts, bool):
                return datetime.fromtimestamp(ts, tz=timezone.utc)
        return self.coordinator.last_data_time
