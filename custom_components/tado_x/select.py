"""Select platform for Tado X."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TadoXDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Presence modes
PRESENCE_HOME = "home"
PRESENCE_AWAY = "away"
PRESENCE_AUTO = "auto"

PRESENCE_OPTIONS = [PRESENCE_HOME, PRESENCE_AWAY, PRESENCE_AUTO]


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
