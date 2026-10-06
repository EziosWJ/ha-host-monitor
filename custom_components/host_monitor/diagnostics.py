"""Diagnostics support for Host Monitor."""

from __future__ import annotations

from dataclasses import asdict

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import HostMonitorCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    coordinator: HostMonitorCoordinator = entry.runtime_data
    return {
        "identity": coordinator.identity,
        "hostname": coordinator.hostname,
        "model": coordinator.model,
        "sw_version": coordinator.sw_version,
        "network_interface": coordinator.network_interface,
        "last_update_success": coordinator.last_update_success,
        "data": asdict(coordinator.data) if coordinator.data is not None else None,
    }
