"""Device registry helpers for Tado X."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity


def via_device_kwargs(entity: Entity, identifier: tuple[str, str]) -> dict[str, Any]:
    """Return the DeviceInfo kwargs that link a device to its parent.

    Home Assistant 2026.11 deprecates `via_device` (an identifier tuple,
    removed in 2027.8) in favour of `via_device_id` (the parent's registry id).
    """
    hass = entity.hass
    platform = entity.platform
    if hass is None or platform is None or platform.config_entry is None:
        return {}
    parent = dr.async_get(hass).async_get_device_by_identifier(
        identifier, platform.config_entry.entry_id
    )
    if parent is None:
        # Parent not registered yet: leave the link as it is (UNDEFINED).
        return {}
    return {"via_device_id": parent.id}
