"""Number platform for Tado X."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_TIMER_DURATION_MINUTES, DOMAIN
from .coordinator import TadoXDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tado X number entities."""
    coordinator: TadoXDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[NumberEntity] = []

    if coordinator.data:
        for room_id in coordinator.data.rooms:
            entities.append(TadoXRoomTimerDuration(coordinator, room_id))

    # Only add flow temperature if the feature is available
    if coordinator.data and coordinator.data.has_flow_temp_control:
        entities.append(TadoXMaxFlowTemperature(coordinator))

    async_add_entities(entities)


class TadoXMaxFlowTemperature(CoordinatorEntity[TadoXDataUpdateCoordinator], NumberEntity):
    """Number entity for Tado X max flow temperature."""

    _attr_has_entity_name = True
    _attr_translation_key = "max_flow_temperature"
    _attr_icon = "mdi:thermometer-water"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: TadoXDataUpdateCoordinator) -> None:
        """Initialize the max flow temperature entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.home_id}_max_flow_temperature"

        # Set min/max from constraints
        data = coordinator.data
        if data:
            self._attr_native_min_value = float(data.flow_temp_min or 20)
            self._attr_native_max_value = float(data.flow_temp_max or 75)
        else:
            self._attr_native_min_value = 20.0
            self._attr_native_max_value = 75.0
        self._attr_native_step = 1.0

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the home."""
        home_name = self.coordinator.home_name or f"Tado Home {self.coordinator.home_id}"
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.coordinator.home_id))},
            name=home_name,
            manufacturer="Tado",
            model="Tado X Home",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current max flow temperature."""
        data = self.coordinator.data
        if not data or not data.has_flow_temp_control:
            return None
        return float(data.max_flow_temperature) if data.max_flow_temperature else None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        data = self.coordinator.data
        return data is not None and data.has_flow_temp_control

    async def async_set_native_value(self, value: float) -> None:
        """Set the max flow temperature."""
        try:
            await self.coordinator.api.set_max_flow_temperature(int(value))
            await self.coordinator.async_request_refresh()
            _LOGGER.info("Set max flow temperature to %d°C", int(value))
        except Exception as err:
            _LOGGER.error("Failed to set max flow temperature: %s", err)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update min/max if constraints changed
        data = self.coordinator.data
        if data and data.has_flow_temp_control:
            if data.flow_temp_min is not None:
                self._attr_native_min_value = float(data.flow_temp_min)
            if data.flow_temp_max is not None:
                self._attr_native_max_value = float(data.flow_temp_max)
        self.async_write_ha_state()


class TadoXRoomTimerDuration(
    CoordinatorEntity[TadoXDataUpdateCoordinator],
    RestoreEntity,
    NumberEntity,
):
    """Number entity for per-room timer duration default."""

    _attr_has_entity_name = True
    _attr_translation_key = "timer_duration"
    _attr_icon = "mdi:timer-outline"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1.0
    _attr_native_max_value = 1440.0
    _attr_native_step = 1.0

    def __init__(self, coordinator: TadoXDataUpdateCoordinator, room_id: int) -> None:
        """Initialize the room timer duration entity."""
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_unique_id = f"{coordinator.home_id}_{room_id}_timer_duration"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        room = self.coordinator.data.rooms.get(self._room_id) if self.coordinator.data else None
        room_name = room.name if room else f"Room {self._room_id}"
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.home_id}_{self._room_id}")},
            name=room_name,
            manufacturer="Tado",
            model="Tado X Room",
            via_device=(DOMAIN, str(self.coordinator.home_id)),
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        data = self.coordinator.data
        return data is not None and self._room_id in data.rooms

    @property
    def native_value(self) -> float | None:
        """Return the current default duration in minutes."""
        defaults = self.coordinator.get_room_control_defaults(self._room_id)
        return float(defaults.duration_minutes)

    async def async_set_native_value(self, value: float) -> None:
        """Set the Tado manual-control timer duration."""

        duration_minutes = int(value)

        defaults = self.coordinator.get_room_control_defaults(self._room_id)

        # Store the new timer duration locally.
        self.coordinator.set_room_control_defaults(
            self._room_id,
            duration_minutes=duration_minutes,
        )

        # Only TIMER has a duration in the Tado API.
        #
        # If TIMER is currently selected, update the Tado master setting
        # immediately.
        if defaults.termination_type == "TIMER":
            await self.coordinator.api.set_room_manual_control_termination(
                self._room_id,
                "TIMER",
                duration_seconds=duration_minutes * 60,
            )

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore last value and populate the coordinator defaults."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()

        if (
            last_state
            and last_state.state not in (None, "unknown", "unavailable")
        ):
            try:
                restored = int(float(last_state.state))
            except ValueError:
                restored = DEFAULT_TIMER_DURATION_MINUTES
        else:
            restored = DEFAULT_TIMER_DURATION_MINUTES

        self.coordinator.set_room_control_defaults(
            self._room_id,
            duration_minutes=restored,
        )

        self.async_write_ha_state()
