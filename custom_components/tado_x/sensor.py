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

from .const import DOMAIN
from .coordinator import TadoXDataUpdateCoordinator, TadoXDevice, TadoXRoom

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TadoXRoomSensorEntityDescription(SensorEntityDescription):
    """Describes a Tado X room sensor entity."""

    value_fn: Callable[[TadoXRoom], Any]


@dataclass(frozen=True, kw_only=True)
class TadoXDeviceSensorEntityDescription(SensorEntityDescription):
    """Describes a Tado X device sensor entity."""

    value_fn: Callable[[TadoXDevice], Any]


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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tado X sensor entities."""
    coordinator: TadoXDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

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
        self._attr_name = f"{description.key.replace('_', ' ').title()} ({serial_number[-4:]})"

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

        # If device has a room, attach to the room device
        if device.room_id:
            return DeviceInfo(
                identifiers={(DOMAIN, f"{self.coordinator.home_id}_{device.room_id}")},
            )

        # For devices without a room (like Bridge), create their own device
        device_type_names = {
            "VA04": "Radiator Valve X",
            "SU04": "Temperature Sensor X",
            "TR04": "Thermostat X",
            "IB02": "Bridge X",
        }

        return DeviceInfo(
            identifiers={(DOMAIN, self._serial_number)},
            name=f"{device_type_names.get(device.device_type, device.device_type)} ({self._serial_number[-4:]})",
            manufacturer="Tado",
            model=device_type_names.get(device.device_type, device.device_type),
            sw_version=device.firmware_version,
            via_device=(DOMAIN, str(self.coordinator.home_id)),
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
