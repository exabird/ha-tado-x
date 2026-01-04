"""DataUpdateCoordinator for Tado X."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TadoXApi, TadoXApiError, TadoXAuthError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class TadoXDevice:
    """Representation of a Tado X device."""

    serial_number: str
    device_type: str
    firmware_version: str
    connection_state: str
    battery_state: str | None = None
    temperature_measured: float | None = None
    temperature_offset: float = 0.0
    mounting_state: str | None = None
    child_lock_enabled: bool = False
    room_id: int | None = None
    room_name: str | None = None


@dataclass
class TadoXRoom:
    """Representation of a Tado X room."""

    room_id: int
    name: str
    current_temperature: float | None = None
    target_temperature: float | None = None
    humidity: float | None = None
    heating_power: int = 0
    power: str = "OFF"
    connection_state: str = "DISCONNECTED"
    manual_control_active: bool = False
    manual_control_remaining_seconds: int | None = None
    manual_control_type: str | None = None
    boost_mode: bool = False
    open_window_detected: bool = False
    next_schedule_change: str | None = None
    next_schedule_temperature: float | None = None
    devices: list[TadoXDevice] = field(default_factory=list)


@dataclass
class TadoXData:
    """Data from Tado X API."""

    home_id: int
    home_name: str
    rooms: dict[int, TadoXRoom] = field(default_factory=dict)
    devices: dict[str, TadoXDevice] = field(default_factory=dict)
    other_devices: list[TadoXDevice] = field(default_factory=list)


class TadoXDataUpdateCoordinator(DataUpdateCoordinator[TadoXData]):
    """Class to manage fetching Tado X data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: TadoXApi,
        home_id: int,
        home_name: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.home_id = home_id
        self.home_name = home_name
        self.api.home_id = home_id

    async def _async_update_data(self) -> TadoXData:
        """Fetch data from Tado X API."""
        try:
            # Get rooms with current state
            rooms_data = await self.api.get_rooms()

            # Get rooms with devices
            rooms_devices_data = await self.api.get_rooms_and_devices()

            # Process the data
            data = TadoXData(
                home_id=self.home_id,
                home_name=self.home_name,
            )

            # Process rooms and devices
            rooms_info = rooms_devices_data.get("rooms", [])
            room_devices_map: dict[int, list[dict]] = {}

            for room_info in rooms_info:
                room_id = room_info.get("roomId")
                if room_id:
                    room_devices_map[room_id] = room_info.get("devices", [])

            # Process room states
            for room_data in rooms_data:
                room_id = room_data.get("id")
                if not room_id:
                    continue

                # Debug: log raw room data for power/setting analysis
                setting = room_data.get("setting") or {}
                _LOGGER.debug(
                    "Room %s (%s) - setting: %s, manualControl: %s",
                    room_id,
                    room_data.get("name"),
                    setting,
                    room_data.get("manualControlTermination"),
                )

                # Get sensor data (use 'or {}' to handle None values)
                sensor_data = room_data.get("sensorDataPoints") or {}
                inside_temp = sensor_data.get("insideTemperature") or {}
                humidity_data = sensor_data.get("humidity") or {}

                # Get setting (use 'or {}' to handle None values)
                setting = room_data.get("setting") or {}
                target_temp = setting.get("temperature") or {}

                # Get manual control info
                manual_control = room_data.get("manualControlTermination")
                manual_active = manual_control is not None
                manual_remaining = None
                manual_type = None
                if manual_control:
                    manual_remaining = manual_control.get("remainingTimeInSeconds")
                    manual_type = manual_control.get("type")

                # Get next schedule change (use 'or {}' to handle None values)
                next_change = room_data.get("nextScheduleChange") or {}
                next_change_time = next_change.get("start")
                next_change_setting = next_change.get("setting") or {}
                next_change_temp_obj = next_change_setting.get("temperature") or {}
                next_change_temp = next_change_temp_obj.get("value")

                # Get heating power and connection (use 'or {}' to handle None values)
                heating_power_data = room_data.get("heatingPower") or {}
                connection_data = room_data.get("connection") or {}

                room = TadoXRoom(
                    room_id=room_id,
                    name=room_data.get("name", f"Room {room_id}"),
                    current_temperature=inside_temp.get("value"),
                    target_temperature=target_temp.get("value"),
                    humidity=humidity_data.get("percentage"),
                    heating_power=heating_power_data.get("percentage", 0),
                    power=setting.get("power", "OFF"),
                    connection_state=connection_data.get("state", "DISCONNECTED"),
                    manual_control_active=manual_active,
                    manual_control_remaining_seconds=manual_remaining,
                    manual_control_type=manual_type,
                    boost_mode=room_data.get("boostMode") is not None,
                    open_window_detected=room_data.get("openWindow") is not None,
                    next_schedule_change=next_change_time,
                    next_schedule_temperature=next_change_temp,
                )

                # Add devices for this room
                for device_data in room_devices_map.get(room_id, []):
                    device_connection = device_data.get("connection") or {}
                    device = TadoXDevice(
                        serial_number=device_data.get("serialNumber", ""),
                        device_type=device_data.get("type", ""),
                        firmware_version=device_data.get("firmwareVersion", ""),
                        connection_state=device_connection.get("state", "DISCONNECTED"),
                        battery_state=device_data.get("batteryState"),
                        temperature_measured=device_data.get("temperatureAsMeasured"),
                        temperature_offset=device_data.get("temperatureOffset", 0.0),
                        mounting_state=device_data.get("mountingState"),
                        child_lock_enabled=device_data.get("childLockEnabled", False),
                        room_id=room_id,
                        room_name=room.name,
                    )
                    room.devices.append(device)
                    data.devices[device.serial_number] = device

                data.rooms[room_id] = room

            # Process other devices (bridge, thermostat controller)
            # First, find the room with the most devices (for thermostat association)
            room_with_most_devices: int | None = None
            max_device_count = 0
            for room_id, room in data.rooms.items():
                device_count = len(room.devices)
                if device_count > max_device_count:
                    max_device_count = device_count
                    room_with_most_devices = room_id

            for device_data in rooms_devices_data.get("otherDevices") or []:
                other_device_connection = device_data.get("connection") or {}
                other_room_id = device_data.get("roomId")
                other_room_name = None
                device_type = device_data.get("type", "")

                # If device has a room association from API, use it
                if other_room_id and other_room_id in data.rooms:
                    other_room_name = data.rooms[other_room_id].name
                # For Thermostat X (TR04) without room, associate with the room
                # that has the most devices (typically the main room it controls)
                elif device_type == "TR04" and room_with_most_devices:
                    other_room_id = room_with_most_devices
                    other_room_name = data.rooms[room_with_most_devices].name
                    _LOGGER.debug(
                        "Associating Thermostat X %s with room %s (%s) - room has %d devices",
                        device_data.get("serialNumber"),
                        other_room_id,
                        other_room_name,
                        max_device_count,
                    )

                device = TadoXDevice(
                    serial_number=device_data.get("serialNumber", ""),
                    device_type=device_type,
                    firmware_version=device_data.get("firmwareVersion", ""),
                    connection_state=other_device_connection.get("state", "DISCONNECTED"),
                    room_id=other_room_id,
                    room_name=other_room_name,
                )

                # If device has a room, add it to the room's device list
                if other_room_id and other_room_id in data.rooms:
                    data.rooms[other_room_id].devices.append(device)

                data.other_devices.append(device)
                data.devices[device.serial_number] = device

            return data

        except TadoXAuthError as err:
            raise UpdateFailed(f"Authentication error: {err}") from err
        except TadoXApiError as err:
            raise UpdateFailed(f"API error: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching Tado X data")
            raise UpdateFailed(f"Unexpected error: {err}") from err
