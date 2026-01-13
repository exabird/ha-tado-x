"""Climate platform for Tado X."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DEFAULT_TIMER_DURATION,
    DOMAIN,
    MAX_TEMP,
    MIN_TEMP,
    TEMP_STEP,
    TERMINATION_MANUAL,
    TERMINATION_TIMER,
)
from .coordinator import TadoXDataUpdateCoordinator, TadoXRoom

_LOGGER = logging.getLogger(__name__)

PRESET_HOME = "home"
PRESET_AWAY = "away"
PRESET_AUTO = "auto"
PRESET_BOOST = "boost"
PRESET_SCHEDULE = "schedule"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tado X climate entities."""
    coordinator: TadoXDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for room_id, room in coordinator.data.rooms.items():
        entities.append(TadoXClimate(coordinator, room_id))

    async_add_entities(entities)


class TadoXClimate(CoordinatorEntity[TadoXDataUpdateCoordinator], ClimateEntity):
    """Tado X Climate entity for a room."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TURN_ON
    )
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]
    _attr_preset_modes = [PRESET_SCHEDULE, PRESET_BOOST, PRESET_HOME, PRESET_AWAY, PRESET_AUTO]
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = TEMP_STEP
    _enable_turn_on_off_backwards_compat = False

    def __init__(
        self,
        coordinator: TadoXDataUpdateCoordinator,
        room_id: int,
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_unique_id = f"{coordinator.home_id}_{room_id}_climate"

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
    def available(self) -> bool:
        """Return if entity is available."""
        room = self._room
        if not room:
            return False
        return room.connection_state == "CONNECTED"

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        room = self._room
        return room.current_temperature if room else None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        room = self._room
        if not room:
            return None
        if room.power == "OFF":
            return None
        return room.target_temperature

    @property
    def current_humidity(self) -> float | None:
        """Return the current humidity."""
        room = self._room
        return room.humidity if room else None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        room = self._room
        if not room:
            return HVACMode.OFF

        _LOGGER.debug(
            "Room %s hvac_mode check - power: %s, manual_control_active: %s",
            room.name,
            room.power,
            room.manual_control_active,
        )

        if room.power == "OFF":
            return HVACMode.OFF

        # If manual control is active, return HEAT
        if room.manual_control_active:
            return HVACMode.HEAT

        # Otherwise, it's following the schedule (AUTO)
        return HVACMode.AUTO

    @property
    def hvac_action(self) -> HVACAction:
        """Return the current HVAC action."""
        room = self._room
        if not room:
            return HVACAction.OFF

        if room.power == "OFF":
            return HVACAction.OFF

        if room.heating_power > 0:
            return HVACAction.HEATING

        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        room = self._room
        if not room:
            return None

        # Check boost first
        if room.boost_mode:
            return PRESET_BOOST

        # Check presence state
        presence = self.coordinator.data.presence
        presence_locked = self.coordinator.data.presence_locked

        if presence_locked:
            if presence == "HOME":
                return PRESET_HOME
            if presence == "AWAY":
                return PRESET_AWAY
        elif presence is not None:
            # Geofencing is active (AUTO mode)
            return PRESET_AUTO

        # Check schedule
        if not room.manual_control_active:
            return PRESET_SCHEDULE

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        room = self._room
        if not room:
            return {}

        attrs: dict[str, Any] = {
            "heating_power": room.heating_power,
            "manual_control_active": room.manual_control_active,
        }

        if room.manual_control_active:
            attrs["manual_control_type"] = room.manual_control_type
            if room.manual_control_remaining_seconds:
                attrs["manual_control_remaining_minutes"] = round(
                    room.manual_control_remaining_seconds / 60
                )

        if room.next_schedule_change:
            attrs["next_schedule_change"] = room.next_schedule_change
            attrs["next_schedule_temperature"] = room.next_schedule_temperature

        if room.open_window_detected:
            attrs["open_window_detected"] = True

        return attrs

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        room = self._room
        if not room:
            return

        if hvac_mode == HVACMode.OFF:
            await self.coordinator.api.set_room_off(
                self._room_id,
                termination_type=TERMINATION_MANUAL,
            )
        elif hvac_mode == HVACMode.HEAT:
            # Set to current target or default 21
            temp = room.target_temperature or 21.0
            await self.coordinator.api.set_room_temperature(
                self._room_id,
                temperature=temp,
                termination_type=TERMINATION_MANUAL,
            )
        elif hvac_mode == HVACMode.AUTO:
            # Resume schedule
            await self.coordinator.api.resume_schedule(self._room_id)

        await self.coordinator.async_request_refresh()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        await self.coordinator.api.set_room_temperature(
            self._room_id,
            temperature=temperature,
            termination_type=TERMINATION_TIMER,
            duration_seconds=DEFAULT_TIMER_DURATION,
        )
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode."""
        if preset_mode == PRESET_SCHEDULE:
            await self.coordinator.api.resume_schedule(self._room_id)
        elif preset_mode == PRESET_BOOST:
            await self.coordinator.api.set_boost_mode(self._room_id)
        elif preset_mode == PRESET_HOME:
            await self.coordinator.api.set_presence_home()
        elif preset_mode == PRESET_AWAY:
            await self.coordinator.api.set_presence_away()
        elif preset_mode == PRESET_AUTO:
            await self.coordinator.api.set_presence_auto()

        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn on heating."""
        room = self._room
        temp = room.target_temperature if room else 21.0
        if temp is None:
            temp = 21.0

        await self.coordinator.api.set_room_temperature(
            self._room_id,
            temperature=temp,
            termination_type=TERMINATION_MANUAL,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn off heating."""
        await self.coordinator.api.set_room_off(
            self._room_id,
            termination_type=TERMINATION_MANUAL,
        )
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
