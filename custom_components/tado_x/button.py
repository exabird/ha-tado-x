"""Button platform for Tado X."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TadoXDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TadoXButtonEntityDescription(ButtonEntityDescription):
    """Describes a Tado X button entity."""

    press_fn: Callable[[TadoXDataUpdateCoordinator], Awaitable[None]]


BUTTON_DESCRIPTIONS: tuple[TadoXButtonEntityDescription, ...] = (
    TadoXButtonEntityDescription(
        key="boost_all",
        translation_key="boost_all",
        icon="mdi:fire",
        press_fn=lambda coordinator: coordinator.api.boost_all_heating(),
    ),
    TadoXButtonEntityDescription(
        key="disable_all",
        translation_key="disable_all",
        icon="mdi:power-off",
        press_fn=lambda coordinator: coordinator.api.disable_all_heating(),
    ),
    TadoXButtonEntityDescription(
        key="resume_schedules",
        translation_key="resume_schedules",
        icon="mdi:calendar-clock",
        press_fn=lambda coordinator: coordinator.api.resume_all_schedules(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tado X button entities."""
    coordinator: TadoXDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        TadoXButton(coordinator, description)
        for description in BUTTON_DESCRIPTIONS
    ]

    async_add_entities(entities)


class TadoXButton(CoordinatorEntity[TadoXDataUpdateCoordinator], ButtonEntity):
    """Tado X button entity for quick actions."""

    _attr_has_entity_name = True
    entity_description: TadoXButtonEntityDescription

    def __init__(
        self,
        coordinator: TadoXDataUpdateCoordinator,
        description: TadoXButtonEntityDescription,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.home_id}_{description.key}"

    @property
    def name(self) -> str:
        """Return the name of the button."""
        return self.entity_description.key.replace("_", " ").title()

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info - buttons belong to the home device."""
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.coordinator.home_id))},
            name=self.coordinator.home_name,
            manufacturer="Tado",
            model="Tado X Home",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.entity_description.press_fn(self.coordinator)
        await self.coordinator.async_request_refresh()
