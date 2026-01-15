"""Switch platform for Tado X."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TadoXDataUpdateCoordinator, TadoXDevice, TadoXRoom

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tado X switch entities."""
    coordinator: TadoXDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = []

    # Add child lock switch for each device that supports it (valves and thermostats)
    for device in coordinator.data.devices.values():
        if device.device_type in ("VA04", "TR04"):  # Valve and Thermostat
            entities.append(TadoXChildLockSwitch(coordinator, device.serial_number))

    # Add open window switch for each room
    for room_id in coordinator.data.rooms:
        entities.append(TadoXOpenWindowSwitch(coordinator, room_id))

    async_add_entities(entities)


class TadoXChildLockSwitch(CoordinatorEntity[TadoXDataUpdateCoordinator], SwitchEntity):
    """Tado X child lock switch entity."""

    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:lock-outline"

    def __init__(
        self,
        coordinator: TadoXDataUpdateCoordinator,
        serial_number: str,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._serial_number = serial_number
        self._attr_unique_id = f"{serial_number}_child_lock"
        self._attr_translation_key = "child_lock"

    @property
    def _device(self) -> TadoXDevice | None:
        """Get the device data."""
        return self.coordinator.data.devices.get(self._serial_number)

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return "Child Lock"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        device = self._device
        if not device:
            return DeviceInfo(
                identifiers={(DOMAIN, self._serial_number)},
            )

        device_type_names_fr = {
            "VA04": "Vanne",
            "SU04": "Capteur Temp",
            "TR04": "Thermostat",
            "IB02": "Bridge X",
        }

        device_type_models = {
            "VA04": "Radiator Valve X",
            "SU04": "Temperature Sensor X",
            "TR04": "Thermostat X",
            "IB02": "Bridge X",
        }

        via_device_id = (
            (DOMAIN, f"{self.coordinator.home_id}_{device.room_id}")
            if device.room_id
            else (DOMAIN, str(self.coordinator.home_id))
        )

        base_name = device_type_names_fr.get(device.device_type, device.device_type)

        if device.room_id and device.room_name:
            same_type_in_room = sorted([
                d.serial_number for d in self.coordinator.data.devices.values()
                if d.room_id == device.room_id and d.device_type == device.device_type
            ])

            if len(same_type_in_room) > 1:
                device_number = same_type_in_room.index(self._serial_number) + 1
                device_name = f"{base_name} {device_number} - {device.room_name}"
            else:
                device_name = f"{base_name} - {device.room_name}"
        else:
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
    def is_on(self) -> bool | None:
        """Return True if child lock is enabled."""
        device = self._device
        if not device:
            return None
        return device.child_lock_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable child lock."""
        await self.coordinator.api.set_child_lock(self._serial_number, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable child lock."""
        await self.coordinator.api.set_child_lock(self._serial_number, False)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class TadoXOpenWindowSwitch(CoordinatorEntity[TadoXDataUpdateCoordinator], SwitchEntity):
    """Tado X open window switch entity.

    When on: open window mode is active (heating reduced)
    Turn off: reset/dismiss open window detection
    Turn on: only works if open window was detected by the system
    """

    _attr_has_entity_name = True
    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:window-open-variant"

    def __init__(
        self,
        coordinator: TadoXDataUpdateCoordinator,
        room_id: int,
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_unique_id = f"{coordinator.home_id}_{room_id}_open_window"
        self._attr_translation_key = "open_window"

    @property
    def _room(self) -> TadoXRoom | None:
        """Get the room data."""
        return self.coordinator.data.rooms.get(self._room_id)

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return "Open Window"

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
        """Return True if open window mode is active."""
        room = self._room
        if not room:
            return None
        return room.open_window_detected

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Activate open window mode (only if system detected an open window)."""
        await self.coordinator.api.set_open_window_detection(self._room_id, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Reset/dismiss open window detection."""
        await self.coordinator.api.set_open_window_detection(self._room_id, False)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
