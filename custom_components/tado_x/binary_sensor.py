"""Binary sensor platform for Tado X."""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TadoXDataUpdateCoordinator, TadoXDevice, TadoXRoom

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TadoXRoomBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Tado X room binary sensor entity."""

    value_fn: Callable[[TadoXRoom], bool | None]


@dataclass(frozen=True, kw_only=True)
class TadoXDeviceBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Tado X device binary sensor entity."""

    value_fn: Callable[[TadoXDevice], bool | None]


ROOM_BINARY_SENSORS: tuple[TadoXRoomBinarySensorEntityDescription, ...] = (
    TadoXRoomBinarySensorEntityDescription(
        key="window_open",
        translation_key="window_open",
        device_class=BinarySensorDeviceClass.WINDOW,
        value_fn=lambda room: room.open_window_detected,
    ),
    TadoXRoomBinarySensorEntityDescription(
        key="heating",
        translation_key="heating",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda room: room.heating_power > 0,
    ),
    TadoXRoomBinarySensorEntityDescription(
        key="overlay_active",
        translation_key="overlay_active",
        icon="mdi:hand-back-left",
        value_fn=lambda room: room.manual_control_active,
    ),
)

DEVICE_BINARY_SENSORS: tuple[TadoXDeviceBinarySensorEntityDescription, ...] = (
    TadoXDeviceBinarySensorEntityDescription(
        key="connectivity",
        translation_key="connectivity",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda device: device.connection_state == "CONNECTED",
    ),
    TadoXDeviceBinarySensorEntityDescription(
        key="battery_low",
        translation_key="battery_low",
        device_class=BinarySensorDeviceClass.BATTERY,
        value_fn=lambda device: device.battery_state == "LOW" if device.battery_state else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tado X binary sensor entities."""
    coordinator: TadoXDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []

    # Add room binary sensors
    for room_id in coordinator.data.rooms:
        for description in ROOM_BINARY_SENSORS:
            entities.append(TadoXRoomBinarySensor(coordinator, room_id, description))

    # Add device binary sensors
    for device in coordinator.data.devices.values():
        for description in DEVICE_BINARY_SENSORS:
            # Skip battery low for devices without batteries
            if description.key == "battery_low" and not device.battery_state:
                continue
            entities.append(TadoXDeviceBinarySensor(coordinator, device.serial_number, description))

    async_add_entities(entities)


class TadoXRoomBinarySensor(CoordinatorEntity[TadoXDataUpdateCoordinator], BinarySensorEntity):
    """Tado X room binary sensor entity."""

    _attr_has_entity_name = True
    entity_description: TadoXRoomBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: TadoXDataUpdateCoordinator,
        room_id: int,
        description: TadoXRoomBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor entity."""
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
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        room = self._room
        if not room:
            return None
        return self.entity_description.value_fn(room)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class TadoXDeviceBinarySensor(CoordinatorEntity[TadoXDataUpdateCoordinator], BinarySensorEntity):
    """Tado X device binary sensor entity."""

    _attr_has_entity_name = True
    entity_description: TadoXDeviceBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: TadoXDataUpdateCoordinator,
        serial_number: str,
        description: TadoXDeviceBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor entity."""
        super().__init__(coordinator)
        self._serial_number = serial_number
        self.entity_description = description
        self._attr_unique_id = f"{serial_number}_{description.key}"
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
            via_device=(DOMAIN, f"{self.coordinator.home_id}_{device.room_id}") if device.room_id else None,
        )

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        device = self._device
        if not device:
            return None
        return self.entity_description.value_fn(device)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
