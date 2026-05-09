"""Number platform for Tado X."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
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

    # Only add flow temperature if the feature is available
    if coordinator.data and coordinator.data.has_flow_temp_control:
        entities.append(TadoXMaxFlowTemperature(coordinator))

    # Add domestic hot water setpoint if available
    if coordinator.data and coordinator.data.has_dhw:
        entities.append(TadoXDhwSetpoint(coordinator))

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


class TadoXDhwSetpoint(CoordinatorEntity[TadoXDataUpdateCoordinator], NumberEntity):
    """Number entity for Tado X domestic hot water setpoint."""

    _attr_has_entity_name = True
    _attr_translation_key = "domestic_hot_water_setpoint"
    _attr_icon = "mdi:water-thermometer"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: TadoXDataUpdateCoordinator) -> None:
        """Initialize the DHW setpoint entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.home_id}_dhw_setpoint"

        # Set min/max from constraints
        data = coordinator.data
        if data:
            self._attr_native_min_value = float(data.dhw_min or 30)
            self._attr_native_max_value = float(data.dhw_max or 60)
        else:
            self._attr_native_min_value = 30.0
            self._attr_native_max_value = 60.0
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
        """Return the current DHW setpoint."""
        data = self.coordinator.data
        if not data or not data.has_dhw:
            return None
        return float(data.dhw_setpoint) if data.dhw_setpoint is not None else None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        data = self.coordinator.data
        return data is not None and data.has_dhw

    async def async_set_native_value(self, value: float) -> None:
        """Set the DHW setpoint."""
        try:
            await self.coordinator.api.set_domestic_hot_water_setpoint(int(value))
            await self.coordinator.async_request_refresh()
            _LOGGER.info("Set DHW setpoint to %d°C", int(value))
        except Exception as err:
            _LOGGER.error("Failed to set DHW setpoint: %s", err)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update min/max if constraints changed
        data = self.coordinator.data
        if data and data.has_dhw:
            if data.dhw_min is not None:
                self._attr_native_min_value = float(data.dhw_min)
            if data.dhw_max is not None:
                self._attr_native_max_value = float(data.dhw_max)
        self.async_write_ha_state()
