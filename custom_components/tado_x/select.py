"""Select platform for Tado X."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, TERMINATION_MANUAL, TERMINATION_NEXT_TIME_BLOCK, TERMINATION_TIMER
from .coordinator import TadoXDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Presence modes
PRESENCE_HOME = "home"
PRESENCE_AWAY = "away"
PRESENCE_AUTO = "auto"

PRESENCE_OPTIONS = [PRESENCE_HOME, PRESENCE_AWAY, PRESENCE_AUTO]

TERMINATION_OPTIONS = [
    TERMINATION_TIMER,
    TERMINATION_MANUAL,
    TERMINATION_NEXT_TIME_BLOCK,
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tado X select entities."""
    coordinator: TadoXDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SelectEntity] = [
        TadoXPresenceSelect(coordinator),
    ]

    if coordinator.data:
        for room_id in coordinator.data.rooms:
            entities.append(TadoXRoomTerminationType(coordinator, room_id))

    async_add_entities(entities)


class TadoXPresenceSelect(CoordinatorEntity[TadoXDataUpdateCoordinator], SelectEntity):
    """Select entity for Tado X home presence mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "presence_mode"
    _attr_icon = "mdi:home-account"
    _attr_options = PRESENCE_OPTIONS

    def __init__(self, coordinator: TadoXDataUpdateCoordinator) -> None:
        """Initialize the presence select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.home_id}_presence_mode"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the home."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.coordinator.home_id))},
            name=self.coordinator.home_name,
            manufacturer="Tado",
            model="Tado X Home",
        )

    @property
    def current_option(self) -> str | None:
        """Return the current presence mode."""
        data = self.coordinator.data
        if not data:
            return None

        # If presence is locked, user manually set home or away
        if data.presence_locked:
            if data.presence == "HOME":
                return PRESENCE_HOME
            elif data.presence == "AWAY":
                return PRESENCE_AWAY

        # Not locked = auto/geofencing mode
        return PRESENCE_AUTO

    async def async_select_option(self, option: str) -> None:
        """Change the presence mode."""
        try:
            if option == PRESENCE_HOME:
                await self.coordinator.api.set_presence_home()
            elif option == PRESENCE_AWAY:
                await self.coordinator.api.set_presence_away()
            elif option == PRESENCE_AUTO:
                await self.coordinator.api.set_presence_auto()

            # Refresh to get updated state
            await self.coordinator.async_request_refresh()
        except Exception as err:
            _LOGGER.error("Failed to set presence mode to %s: %s", option, err)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()


class TadoXRoomTerminationType(
    CoordinatorEntity[TadoXDataUpdateCoordinator],
    RestoreEntity,
    SelectEntity,
):
    """Select entity for per-room termination type default."""

    _attr_has_entity_name = True
    _attr_translation_key = "termination_type"
    _attr_icon = "mdi:timer-cog-outline"
    _attr_options = TERMINATION_OPTIONS
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: TadoXDataUpdateCoordinator, room_id: int) -> None:
        """Initialize the room termination type entity."""
        super().__init__(coordinator)
        self._room_id = room_id
        self._attr_unique_id = f"{coordinator.home_id}_{room_id}_termination_type"

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
    def current_option(self) -> str | None:
        """Return the current Tado termination type."""
        defaults = self.coordinator.get_room_control_defaults(self._room_id)
        return defaults.termination_type

    async def async_select_option(self, option: str) -> None:
        """Change the Tado manual-control termination type."""
        defaults = self.coordinator.get_room_control_defaults(self._room_id)

        # TIMER requires a duration.
        duration_seconds = None
        if option == TERMINATION_TIMER:
            duration_seconds = defaults.duration_minutes * 60

        await self.coordinator.api.set_room_manual_control_termination(
            self._room_id,
            option,
            duration_seconds=duration_seconds,
        )

        # Update locally immediately rather than waiting for the next poll.
        self.coordinator.set_room_control_defaults(
            self._room_id,
            termination_type=option,
        )

        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Initialize from the current Tado configuration."""
        await super().async_added_to_hass()
        self.async_write_ha_state()