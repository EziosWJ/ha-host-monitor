"""The Host Monitor integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import HostMonitorCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type HostMonitorConfigEntry = ConfigEntry[HostMonitorCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: HostMonitorConfigEntry) -> bool:
    """Set up Host Monitor from a config entry."""
    coordinator = HostMonitorCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HostMonitorConfigEntry) -> bool:
    """Unload a Host Monitor config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
