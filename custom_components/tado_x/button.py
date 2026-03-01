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

from .const import DOMAIN, FEATURE_ENTITY_MAP
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
    TadoXButtonEntityDescription(
        key="boost_hot_water",
        translation_key="boost_hot_water",
        icon="mdi:fire",
        press_fn=lambda coordinator: coordinator.api.boost_domestic_hot_water(),
    ),
    TadoXButtonEntityDescription(
        key="disable_hot_water",
        translation_key="disable_hot_water",
        icon="mdi:power-off",
        press_fn=lambda coordinator: coordinator.api.disable_domestic_hot_water(),
    ),
    TadoXButtonEntityDescription(
        key="resume_hot_water_schedule",
        translation_key="resume_hot_water_schedule",
        icon="mdi:calendar-clock",
        press_fn=lambda coordinator: coordinator.api.resume_domestic_hot_water_schedule(),
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

    # Set initial disabled_by state based on feature flags
    from homeassistant.helpers import entity_registry as er
    entity_registry = er.async_get(hass)
    
    # Disable entities based on feature flags
    for entity_id, entity_entry in list(entity_registry.entities.items()):
        # Only process Tado X button entities
        if entity_entry.platform != DOMAIN or entity_entry.domain != "button":
            continue
        
        if not entity_entry.unique_id:
            continue
        
        # Check if this entity matches a disabled feature
        should_be_disabled = False
        for feature_flag, entity_keys in FEATURE_ENTITY_MAP.items():
            feature_enabled = getattr(coordinator, feature_flag, False)
            
            # Check if entity_key matches any of the disabled feature's keys
            for entity_key in entity_keys:
                if entity_entry.unique_id.endswith(f"_{entity_key}"):
                    if not feature_enabled:
                        should_be_disabled = True
                    break
            
            if should_be_disabled:
                break
        
        # Update disabled state
        if should_be_disabled:
            entity_registry.async_update_entity(
                entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
            )
        else:
            # Make sure it's enabled if the feature is on
            if entity_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION:
                entity_registry.async_update_entity(
                    entity_id,
                    disabled_by=None,
                )


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
