"""Sensor platform for Tado X."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import API_QUOTA_FREE_TIER, DOMAIN
from .coordinator import TadoXData, TadoXDataUpdateCoordinator, TadoXDevice, TadoXRoom

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TadoXRoomSensorEntityDescription(SensorEntityDescription):
    """Describes a Tado X room sensor entity."""

    value_fn: Callable[[TadoXRoom], Any]


@dataclass(frozen=True, kw_only=True)
class TadoXDeviceSensorEntityDescription(SensorEntityDescription):
    """Describes a Tado X device sensor entity."""

    value_fn: Callable[[TadoXDevice], Any]


@dataclass(frozen=True, kw_only=True)
class TadoXHomeSensorEntityDescription(SensorEntityDescription):
    """Describes a Tado X home sensor entity."""

    value_fn: Callable[[TadoXData], Any]


ROOM_SENSORS: tuple[TadoXRoomSensorEntityDescription, ...] = (
    TadoXRoomSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda room: room.current_temperature,
    ),
    TadoXRoomSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda room: room.humidity,
    ),
    TadoXRoomSensorEntityDescription(
        key="heating_power",
        translation_key="heating_power",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:radiator",
        value_fn=lambda room: room.heating_power,
    ),
)

DEVICE_SENSORS: tuple[TadoXDeviceSensorEntityDescription, ...] = (
    TadoXDeviceSensorEntityDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.ENUM,
        options=["normal", "low"],
        icon="mdi:battery",
        value_fn=lambda device: device.battery_state.lower() if device.battery_state else None,
    ),
    TadoXDeviceSensorEntityDescription(
        key="device_temperature",
        translation_key="device_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda device: device.temperature_measured,
    ),
)

HOME_SENSORS: tuple[TadoXHomeSensorEntityDescription, ...] = (
    TadoXHomeSensorEntityDescription(
        key="api_calls_today",
        translation_key="api_calls_today",
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.api_calls_today,
    ),
    TadoXHomeSensorEntityDescription(
        key="api_quota_remaining",
        translation_key="api_quota_remaining",
        icon="mdi:api",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: max(0, API_QUOTA_FREE_TIER - data.api_calls_today),
    ),
    TadoXHomeSensorEntityDescription(
        key="api_usage_percentage",
        translation_key="api_usage_percentage",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: min(100, round((data.api_calls_today / API_QUOTA_FREE_TIER) * 100, 1)),
    ),
    TadoXHomeSensorEntityDescription(
        key="api_reset_time",
        translation_key="api_reset_time",
        icon="mdi:clock-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.api_reset_time,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tado X sensor entities."""
    coordinator: TadoXDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Add home-level sensors (API monitoring)
    for description in HOME_SENSORS:
        entities.append(TadoXHomeSensor(coordinator, description))

    # Add room sensors
    for room_id in coordinator.data.rooms:
        for description in ROOM_SENSORS:
            entities.append(TadoXRoomSensor(coordinator, room_id, description))

    # Add device sensors (for devices with batteries - valves and sensors)
    for device in coordinator.data.devices.values():
        if device.battery_state:  # Only devices with batteries
            for description in DEVICE_SENSORS:
                # Skip device temperature for sensors that don't have it
                if description.key == "device_temperature" and device.temperature_measured is None:
                    continue
                entities.append(TadoXDeviceSensor(coordinator, device.serial_number, description))

    async_add_entities(entities)


class TadoXHomeSensor(CoordinatorEntity[TadoXDataUpdateCoordinator], SensorEntity):
    """Tado X home sensor entity."""

    _attr_has_entity_name = True
    entity_description: TadoXHomeSensorEntityDescription

    def __init__(
        self,
        coordinator: TadoXDataUpdateCoordinator,
        description: TadoXHomeSensorEntityDescription,
    ) -> None:
        """Initialize home sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.home_id}_{description.key}"
        self._attr_name = description.key.replace("_", " ").title()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.coordinator.data.home_id))},
            name=f"{self.coordinator.data.home_name} Home",
            manufacturer="Tado",
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class TadoXRoomSensor(CoordinatorEntity[TadoXDataUpdateCoordinator], SensorEntity):
    """Tado X room sensor entity."""

    _attr_has_entity_name = True
    entity_description: TadoXRoomSensorEntityDescription

    def __init__(
        self,
        coordinator: TadoXDataUpdateCoordinator,
        room_id: int,
        description: TadoXRoomSensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator)
        self._room_id = room_id
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.home_id}_{room_id}_{description.key}"
        self._attr_name = description.key.replace("_", " ").title()

    @property
    def _room(self) -> TadoXRoom | None:
        """Get the room data."""
        return self.coordinator.data.rooms.get(self._room_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        room = self._room
        room_name = room.name if room else f"Room {self._room_id}"

        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.home_id}_{self._room_id}")},
            name=room_name,
            manufacturer="Tado",
            model="Tado X Room",
            via_device=(DOMAIN, str(self.coordinator.home_id)),
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        room = self._room
        if not room:
            return None
        return self.entity_description.value_fn(room)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class TadoXDeviceSensor(CoordinatorEntity[TadoXDataUpdateCoordinator], SensorEntity):
    """Tado X device sensor entity."""

    _attr_has_entity_name = True
    entity_description: TadoXDeviceSensorEntityDescription

    def __init__(
        self,
        coordinator: TadoXDataUpdateCoordinator,
        serial_number: str,
        description: TadoXDeviceSensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator)
        self._serial_number = serial_number
        self.entity_description = description
        self._attr_unique_id = f"{serial_number}_{description.key}"
        # Simple name without serial suffix - device name already has it
        self._attr_name = description.key.replace("_", " ").title()

    @property
    def _device(self) -> TadoXDevice | None:
        """Get the device data."""
        return self.coordinator.data.devices.get(self._serial_number)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        device = self._device
        if not device:
            return DeviceInfo(
                identifiers={(DOMAIN, self._serial_number)},
            )

        # French names for device types (used in device name)
        device_type_names_fr = {
            "VA04": "Vanne",
            "SU04": "Capteur Temp",
            "TR04": "Thermostat",
            "IB02": "Bridge X",
        }

        # English model names (used in device model field)
        device_type_models = {
            "VA04": "Radiator Valve X",
            "SU04": "Temperature Sensor X",
            "TR04": "Thermostat X",
            "IB02": "Bridge X",
        }

        # Determine via_device - link to room if device has one, otherwise to home
        via_device_id = (
            (DOMAIN, f"{self.coordinator.home_id}_{device.room_id}")
            if device.room_id
            else (DOMAIN, str(self.coordinator.home_id))
        )

        # Generate device name with room name and numbering
        base_name = device_type_names_fr.get(device.device_type, device.device_type)

        if device.room_id and device.room_name:
            # Count devices of same type in same room to determine numbering
            same_type_in_room = sorted([
                d.serial_number for d in self.coordinator.data.devices.values()
                if d.room_id == device.room_id and d.device_type == device.device_type
            ])

            if len(same_type_in_room) > 1:
                # Multiple devices of same type - add number
                device_number = same_type_in_room.index(self._serial_number) + 1
                device_name = f"{base_name} {device_number} - {device.room_name}"
            else:
                # Only one device of this type - no number needed
                device_name = f"{base_name} - {device.room_name}"
        else:
            # No room - use serial number suffix (e.g., Bridge)
            device_name = f"{base_name} ({self._serial_number[-4:]})"

        return DeviceInfo(
            identifiers={(DOMAIN, self._serial_number)},
            name=device_name,
            manufacturer="Tado",
            model=device_type_models.get(device.device_type, device.device_type),
            sw_version=device.firmware_version,
            via_device=via_device_id,
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        device = self._device
        if not device:
            return None
        return self.entity_description.value_fn(device)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
