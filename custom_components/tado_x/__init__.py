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
    CONF_ENABLE_AIR_COMFORT,
    CONF_ENABLE_FLOW_TEMP,
    CONF_ENABLE_MOBILE_DEVICES,
    CONF_ENABLE_RUNNING_TIMES,
    CONF_ENABLE_WEATHER,
    CONF_HAS_AUTO_ASSIST,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN_EXPIRY,
    DOMAIN,
    PLATFORMS,
    TERMINATION_MANUAL,
    TERMINATION_NEXT_TIME_BLOCK,
    TERMINATION_TIMER,
)
from .coordinator import TadoXDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Service constants
SERVICE_SET_TEMPERATURE_OFFSET: Final = "set_temperature_offset"
ATTR_OFFSET: Final = "offset"

SERVICE_ADD_METER_READING: Final = "add_meter_reading"
ATTR_HOME_ID: Final = "home_id"
ATTR_READING: Final = "reading"
ATTR_DATE: Final = "date"

SERVICE_SET_EIQ_TARIFF: Final = "set_eiq_tariff"
ATTR_TARIFF: Final = "tariff"
ATTR_UNIT: Final = "unit"
ATTR_START_DATE: Final = "start_date"
ATTR_END_DATE: Final = "end_date"

SERVICE_SET_CLIMATE_TIMER: Final = "set_climate_timer"
ATTR_ENTITY_ID: Final = "entity_id"
ATTR_TEMPERATURE: Final = "temperature"
ATTR_DURATION: Final = "duration"
ATTR_TERMINATION_TYPE: Final = "termination_type"

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
        vol.Optional(ATTR_HOME_ID): cv.string,
    }
)

SERVICE_SET_EIQ_TARIFF_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TARIFF): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Required(ATTR_UNIT): vol.In(["m3", "kWh"]),
        vol.Optional(ATTR_START_DATE): cv.string,
        vol.Optional(ATTR_END_DATE): cv.string,
        vol.Optional(ATTR_HOME_ID): cv.string,
    }
)

SERVICE_SET_CLIMATE_TIMER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_TEMPERATURE): vol.All(
            vol.Coerce(float),
            vol.Range(min=5.0, max=30.0),
        ),
        vol.Required(ATTR_DURATION): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=1440),  # 1 minute to 24 hours
        ),
        vol.Optional(ATTR_TERMINATION_TYPE, default=TERMINATION_TIMER): vol.In(
            [TERMINATION_TIMER, TERMINATION_MANUAL, TERMINATION_NEXT_TIME_BLOCK]
        ),
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

    # Get feature toggles - default based on subscription tier
    # Auto-Assist users get all features enabled, free tier users get them disabled
    has_auto_assist = entry.data.get(CONF_HAS_AUTO_ASSIST, False)
    default_features = has_auto_assist
    enable_weather = entry.data.get(CONF_ENABLE_WEATHER, default_features)
    enable_mobile_devices = entry.data.get(CONF_ENABLE_MOBILE_DEVICES, default_features)
    enable_air_comfort = entry.data.get(CONF_ENABLE_AIR_COMFORT, default_features)
    enable_running_times = entry.data.get(CONF_ENABLE_RUNNING_TIMES, default_features)
    enable_flow_temp = entry.data.get(CONF_ENABLE_FLOW_TEMP, default_features)

    # Create coordinator
    coordinator = TadoXDataUpdateCoordinator(
        hass=hass,
        api=api,
        home_id=home_id,
        home_name=home_name,
        save_api_stats_callback=save_api_stats,
        scan_interval=configured_scan_interval if configured_scan_interval else None,
        enable_weather=enable_weather,
        enable_mobile_devices=enable_mobile_devices,
        enable_air_comfort=enable_air_comfort,
        enable_running_times=enable_running_times,
        enable_flow_temp=enable_flow_temp,
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except TadoXApiError as err:
        raise ConfigEntryNotReady(f"Failed to fetch data: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Register services
    #
    # Services are global to the integration domain, while coordinators are
    # specific to config entries. Service handlers must therefore resolve the
    # correct coordinator at call time rather than using the coordinator from
    # whichever config entry happened to register the service first.

    def get_coordinator_for_config_entry(
        config_entry_id: str,
    ) -> TadoXDataUpdateCoordinator:
        """Return the coordinator belonging to a config entry."""
        service_coordinator = hass.data.get(DOMAIN, {}).get(config_entry_id)
        if service_coordinator is None:
            raise HomeAssistantError(
                f"No Tado X coordinator found for config entry {config_entry_id}"
            )
        return service_coordinator

    def get_coordinator_for_home(home_id: str) -> TadoXDataUpdateCoordinator:
        """Return the coordinator belonging to a Tado home."""
        for service_coordinator in hass.data.get(DOMAIN, {}).values():
            if str(service_coordinator.home_id) == str(home_id):
                return service_coordinator
        raise HomeAssistantError(f"No Tado X coordinator found for home {home_id}")

    def get_default_coordinator() -> TadoXDataUpdateCoordinator:
        """Return the coordinator when exactly one Tado home is configured."""
        coordinators = hass.data.get(DOMAIN, {})
        if not coordinators:
            raise HomeAssistantError("No Tado X homes are configured")
        if len(coordinators) > 1:
            raise HomeAssistantError(
                "Multiple Tado X homes are configured. A home_id must be specified."
            )
        return next(iter(coordinators.values()))

    def get_home_coordinator(call: ServiceCall) -> TadoXDataUpdateCoordinator:
        """Resolve coordinator for a home-level service."""
        requested_home_id = call.data.get(ATTR_HOME_ID)
        if requested_home_id is not None:
            return get_coordinator_for_home(requested_home_id)
        return get_default_coordinator()

    async def async_set_temperature_offset(call: ServiceCall) -> None:
        """Handle set_temperature_offset service call."""
        device_id = call.data[ATTR_DEVICE_ID]
        offset = call.data[ATTR_OFFSET]

        device_registry_instance = dr.async_get(hass)
        device = device_registry_instance.async_get(device_id)
        if not device:
            raise HomeAssistantError(f"Device {device_id} not found")

        config_entry_id = next(
            (
                entry_id
                for entry_id in device.config_entries
                if entry_id in hass.data.get(DOMAIN, {})
            ),
            None,
        )
        if config_entry_id is None:
            raise HomeAssistantError(
                f"Could not determine Tado X config entry for device {device_id}"
            )

        service_coordinator = get_coordinator_for_config_entry(config_entry_id)

        device_serial = None
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:
                device_serial = identifier[1]
                break

        if not device_serial:
            raise HomeAssistantError(
                f"Could not find serial number for device {device_id}"
            )

        if "_" in device_serial:
            raise HomeAssistantError(
                f"Cannot set temperature offset for room device {device_id}. "
                "Please select a specific valve or sensor device."
            )

        try:
            await service_coordinator.api.set_temperature_offset(device_serial, offset)
            await service_coordinator.async_request_refresh()
            _LOGGER.info(
                "Set temperature offset for device %s to %.1f°C",
                device_serial,
                offset,
            )
        except TadoXApiError as err:
            _LOGGER.error(
                "Failed to set temperature offset for device %s: %s",
                device_serial,
                err,
            )
            raise HomeAssistantError(
                f"Failed to set temperature offset: {err}"
            ) from err

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
        service_coordinator = get_home_coordinator(call)

        try:
            await service_coordinator.api.add_meter_reading(reading, date)
            _LOGGER.info(
                "Meter reading %s added successfully for home %s",
                reading,
                service_coordinator.home_id,
            )
        except TadoXApiError as err:
            _LOGGER.error("Failed to add meter reading: %s", err)
            raise HomeAssistantError(f"Failed to add meter reading: {err}") from err

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
        service_coordinator = get_home_coordinator(call)

        try:
            await service_coordinator.api.set_eiq_tariff(
                tariff, unit, start_date, end_date
            )
            _LOGGER.info(
                "EIQ tariff %.2f %s set successfully for home %s",
                tariff,
                unit,
                service_coordinator.home_id,
            )
        except TadoXApiError as err:
            _LOGGER.error("Failed to set EIQ tariff: %s", err)
            raise HomeAssistantError(f"Failed to set EIQ tariff: {err}") from err

    if not hass.services.has_service(DOMAIN, SERVICE_SET_EIQ_TARIFF):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_EIQ_TARIFF,
            async_set_eiq_tariff,
            schema=SERVICE_SET_EIQ_TARIFF_SCHEMA,
        )

    async def async_set_climate_timer(call: ServiceCall) -> None:
        """Handle set_climate_timer service call."""
        from homeassistant.helpers import entity_registry as er

        entity_id = call.data[ATTR_ENTITY_ID]
        temperature = call.data[ATTR_TEMPERATURE]
        duration_minutes = call.data[ATTR_DURATION]
        termination_type = call.data.get(ATTR_TERMINATION_TYPE, TERMINATION_TIMER)

        entity_registry = er.async_get(hass)
        entity_entry = entity_registry.async_get(entity_id)
        if not entity_entry:
            raise HomeAssistantError(f"Entity {entity_id} not found in registry")

        if entity_entry.platform != DOMAIN:
            raise HomeAssistantError(
                f"Entity {entity_id} is not a Tado X entity "
                f"(platform: {entity_entry.platform}). "
                "The set_climate_timer service only works with native "
                "Tado X climate entities."
            )

        if not entity_entry.config_entry_id:
            raise HomeAssistantError(f"Entity {entity_id} has no config entry")
        if not entity_entry.unique_id:
            raise HomeAssistantError(f"Entity {entity_id} has no unique_id")

        service_coordinator = get_coordinator_for_config_entry(
            entity_entry.config_entry_id
        )

        try:
            parts = entity_entry.unique_id.split("_")
            if len(parts) == 3 and parts[2] == "climate":
                entity_home_id = parts[0]
                room_id = int(parts[1])
            elif len(parts) == 2:
                entity_home_id = parts[0]
                room_id = int(parts[1])
            else:
                raise ValueError(
                    f"Unexpected unique_id format: {entity_entry.unique_id}"
                )
        except (ValueError, IndexError) as err:
            raise HomeAssistantError(
                f"Could not extract room_id from entity {entity_id}: {err}"
            ) from err

        if str(service_coordinator.home_id) != str(entity_home_id):
            raise HomeAssistantError(
                f"Entity {entity_id} belongs to Tado home {entity_home_id}, "
                f"but its config entry belongs to home {service_coordinator.home_id}"
            )

        duration_seconds = duration_minutes * 60

        try:
            await service_coordinator.api.set_room_temperature(
                room_id=room_id,
                temperature=temperature,
                power="ON",
                termination_type=termination_type,
                duration_seconds=duration_seconds,
            )
            await service_coordinator.async_request_refresh()
            _LOGGER.info(
                "Set %s to %.1f°C for %d minutes (home %s, room %s)",
                entity_id,
                temperature,
                duration_minutes,
                service_coordinator.home_id,
                room_id,
            )
        except TadoXApiError as err:
            _LOGGER.error("Failed to set climate timer for %s: %s", entity_id, err)
            raise HomeAssistantError(f"Failed to set climate timer: {err}") from err

    if not hass.services.has_service(DOMAIN, SERVICE_SET_CLIMATE_TIMER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_CLIMATE_TIMER,
            async_set_climate_timer,
            schema=SERVICE_SET_CLIMATE_TIMER_SCHEMA,
        )

    # Create the "Home" device before loading platforms to ensure via_device references work
    # This prevents deprecation warnings about via_device referencing non-existing devices
    device_registry_instance = dr.async_get(hass)
    device_registry_instance.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, str(home_id))},
        name=f"{home_name} Home",
        manufacturer="Tado",
        model="Tado X Home",
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
