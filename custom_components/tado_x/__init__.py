"""The Tado X integration."""
from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TadoXApi, TadoXApiError, TadoXAuthError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_HOME_ID,
    CONF_HOME_NAME,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRY,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import TadoXDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.SENSOR, Platform.BINARY_SENSOR]


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

    api = TadoXApi(
        session=session,
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        token_expiry=token_expiry,
    )

    home_id = entry.data[CONF_HOME_ID]
    home_name = entry.data.get(CONF_HOME_NAME, f"Tado Home {home_id}")

    # Test the connection and refresh token if needed
    try:
        await api.refresh_access_token()

        # Update stored tokens
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_ACCESS_TOKEN: api.access_token,
                CONF_REFRESH_TOKEN: api.refresh_token,
                CONF_TOKEN_EXPIRY: api.token_expiry.isoformat() if api.token_expiry else None,
            },
        )
    except TadoXAuthError as err:
        _LOGGER.error("Authentication failed: %s", err)
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err

    # Create coordinator
    coordinator = TadoXDataUpdateCoordinator(
        hass=hass,
        api=api,
        home_id=home_id,
        home_name=home_name,
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except TadoXApiError as err:
        raise ConfigEntryNotReady(f"Failed to fetch data: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Clean up orphan device entries (devices with serial number identifiers
    # that should be merged into room devices)
    await _async_cleanup_orphan_devices(hass, entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def _async_cleanup_orphan_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator: TadoXDataUpdateCoordinator,
) -> None:
    """Remove orphan device entries for devices that are now merged into rooms.

    Previously, valve devices (VA04, SU04, etc.) created their own device entries.
    Now they are merged into room devices. This function removes the old orphan
    device entries that have serial number identifiers.
    """
    device_registry = dr.async_get(hass)

    # Get all devices with serial numbers that belong to a room
    devices_in_rooms = {
        device.serial_number
        for device in coordinator.data.devices.values()
        if device.room_id is not None
    }

    # Find and remove orphan device entries
    devices_to_remove = []
    for device_entry in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        for identifier in device_entry.identifiers:
            if identifier[0] == DOMAIN:
                device_id = identifier[1]
                # Check if this is a serial number identifier for a device in a room
                if device_id in devices_in_rooms:
                    devices_to_remove.append(device_entry.id)
                    _LOGGER.debug(
                        "Marking orphan device for removal: %s (%s)",
                        device_entry.name,
                        device_id,
                    )
                    break

    # Remove orphan devices
    for device_id in devices_to_remove:
        _LOGGER.info("Removing orphan device entry: %s", device_id)
        device_registry.async_remove_device(device_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
