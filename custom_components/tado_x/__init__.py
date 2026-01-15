"""The Tado X integration."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Final

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DEVICE_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TadoXApi, TadoXApiError, TadoXAuthError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_API_CALLS_TODAY,
    CONF_API_RESET_TIME,
    CONF_HAS_AUTO_ASSIST,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN_EXPIRY,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import TadoXDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR]

# Service constants
SERVICE_SET_TEMPERATURE_OFFSET: Final = "set_temperature_offset"
ATTR_OFFSET: Final = "offset"

SERVICE_ADD_METER_READING: Final = "add_meter_reading"
ATTR_READING: Final = "reading"
ATTR_DATE: Final = "date"

SERVICE_SET_EIQ_TARIFF: Final = "set_eiq_tariff"
ATTR_TARIFF: Final = "tariff"
ATTR_UNIT: Final = "unit"
ATTR_START_DATE: Final = "start_date"
ATTR_END_DATE: Final = "end_date"

# Service schemas
SERVICE_SET_TEMPERATURE_OFFSET_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_OFFSET): vol.All(
            vol.Coerce(float),
            vol.Range(min=-9.9, max=9.9),
        ),
    }
)

SERVICE_ADD_METER_READING_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_READING): vol.All(vol.Coerce(int), vol.Range(min=0)),
        vol.Optional(ATTR_DATE): cv.string,
    }
)

SERVICE_SET_EIQ_TARIFF_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TARIFF): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Required(ATTR_UNIT): vol.In(["m3", "kWh"]),
        vol.Optional(ATTR_START_DATE): cv.string,
        vol.Optional(ATTR_END_DATE): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tado X from a config entry."""
    session = async_get_clientsession(hass)

    # Parse token expiry
    token_expiry = None
    if entry.data.get(CONF_TOKEN_EXPIRY):
        try:
            token_expiry = datetime.fromisoformat(entry.data[CONF_TOKEN_EXPIRY])
        except (ValueError, TypeError):
            pass

    # Parse API reset time for persistence
    api_reset_time = None
    if entry.data.get(CONF_API_RESET_TIME):
        try:
            api_reset_time = datetime.fromisoformat(entry.data[CONF_API_RESET_TIME])
        except (ValueError, TypeError):
            pass

    # Create a mutable container for the API reference (needed for callback closure)
    api_container: dict[str, TadoXApi] = {}

    def save_tokens() -> None:
        """Save tokens to config entry after refresh to prevent auth loss on restart."""
        if "api" not in api_container:
            return
        api = api_container["api"]
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_ACCESS_TOKEN: api.access_token,
                CONF_REFRESH_TOKEN: api.refresh_token,
                CONF_TOKEN_EXPIRY: api.token_expiry.isoformat() if api.token_expiry else None,
            },
        )
        _LOGGER.debug("Tokens persisted to config entry")

    api = TadoXApi(
        session=session,
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        token_expiry=token_expiry,
        api_calls_today=entry.data.get(CONF_API_CALLS_TODAY, 0),
        api_reset_time=api_reset_time,
        has_auto_assist=entry.data.get(CONF_HAS_AUTO_ASSIST, False),
        on_token_refresh=save_tokens,
    )
    api_container["api"] = api

    home_id = entry.data[CONF_HOME_ID]
    home_name = entry.data.get(CONF_HOME_NAME, f"Tado Home {home_id}")

    # Test the connection and refresh token if needed
    try:
        await api.refresh_access_token()

        # Update stored tokens and API call stats
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_ACCESS_TOKEN: api.access_token,
                CONF_REFRESH_TOKEN: api.refresh_token,
                CONF_TOKEN_EXPIRY: api.token_expiry.isoformat() if api.token_expiry else None,
                CONF_API_CALLS_TODAY: api.api_calls_today,
                CONF_API_RESET_TIME: api.api_reset_time.isoformat(),
                CONF_HAS_AUTO_ASSIST: api.has_auto_assist,
            },
        )
    except TadoXAuthError as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

    # Create callback to save API stats periodically
    def save_api_stats() -> None:
        """Save API call statistics to config entry."""
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_API_CALLS_TODAY: api.api_calls_today,
                CONF_API_RESET_TIME: api.api_reset_time.isoformat(),
            },
        )

    # Get configured scan interval (or None to use auto-detection based on tier)
    configured_scan_interval = entry.data.get(CONF_SCAN_INTERVAL)

    # Create coordinator
    coordinator = TadoXDataUpdateCoordinator(
        hass=hass,
        api=api,
        home_id=home_id,
        home_name=home_name,
        save_api_stats_callback=save_api_stats,
        scan_interval=configured_scan_interval if configured_scan_interval else None,
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except TadoXApiError as err:
        raise ConfigEntryNotReady(f"Failed to fetch data: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register services
    async def async_set_temperature_offset(call: ServiceCall) -> None:
        """Handle set_temperature_offset service call."""
        device_id = call.data[ATTR_DEVICE_ID]
        offset = call.data[ATTR_OFFSET]

        # Get device registry
        device_registry_instance = dr.async_get(hass)
        device = device_registry_instance.async_get(device_id)

        if not device:
            _LOGGER.error("Device %s not found", device_id)
            return

        # Find the device serial number from identifiers
        device_serial = None
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:
                # Identifier format is (DOMAIN, serial_number) or (DOMAIN, home_id_room_id)
                device_serial = identifier[1]
                break

        if not device_serial:
            _LOGGER.error("Could not find serial number for device %s", device_id)
            return

        # Check if this is a room device (format: home_id_room_id) or a real device
        if "_" in device_serial:
            _LOGGER.error(
                "Cannot set temperature offset for room device %s. "
                "Please select a specific valve or sensor device.",
                device_id,
            )
            return

        try:
            await coordinator.api.set_temperature_offset(device_serial, offset)
            await coordinator.async_request_refresh()
            _LOGGER.info(
                "Set temperature offset for device %s to %.1f°C",
                device_serial,
                offset,
            )
        except Exception as err:
            _LOGGER.error(
                "Failed to set temperature offset for device %s: %s",
                device_serial,
                err,
            )

    # Register temperature offset service (only once per integration)
    if not hass.services.has_service(DOMAIN, SERVICE_SET_TEMPERATURE_OFFSET):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_TEMPERATURE_OFFSET,
            async_set_temperature_offset,
            schema=SERVICE_SET_TEMPERATURE_OFFSET_SCHEMA,
        )

    async def async_add_meter_reading(call: ServiceCall) -> None:
        """Handle add_meter_reading service call."""
        reading = call.data[ATTR_READING]
        date = call.data.get(ATTR_DATE)

        try:
            await coordinator.api.add_meter_reading(reading, date)
            _LOGGER.info("Meter reading %s added successfully", reading)
        except TadoXApiError as err:
            _LOGGER.error("Failed to add meter reading: %s", err)
            raise HomeAssistantError(f"Failed to add meter reading: {err}") from err

    # Register meter reading service (only once per integration)
    if not hass.services.has_service(DOMAIN, SERVICE_ADD_METER_READING):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_METER_READING,
            async_add_meter_reading,
            schema=SERVICE_ADD_METER_READING_SCHEMA,
        )

    async def async_set_eiq_tariff(call: ServiceCall) -> None:
        """Handle set_eiq_tariff service call."""
        tariff = call.data[ATTR_TARIFF]
        unit = call.data[ATTR_UNIT]
        start_date = call.data.get(ATTR_START_DATE)
        end_date = call.data.get(ATTR_END_DATE)

        try:
            await coordinator.api.set_eiq_tariff(tariff, unit, start_date, end_date)
            _LOGGER.info("EIQ tariff %.2f %s set successfully", tariff, unit)
        except TadoXApiError as err:
            _LOGGER.error("Failed to set EIQ tariff: %s", err)
            raise HomeAssistantError(f"Failed to set EIQ tariff: {err}") from err

    # Register EIQ tariff service (only once per integration)
    if not hass.services.has_service(DOMAIN, SERVICE_SET_EIQ_TARIFF):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_EIQ_TARIFF,
            async_set_eiq_tariff,
            schema=SERVICE_SET_EIQ_TARIFF_SCHEMA,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
