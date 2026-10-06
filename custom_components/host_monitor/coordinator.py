"""DataUpdateCoordinator for Host Monitor."""

from __future__ import annotations

import logging
import platform
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .collector import read_host_identity, read_snapshot
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .data import (
    CpuTimes,
    HostMonitorData,
    NetworkCounters,
    RawSnapshot,
    build_data,
)

_LOGGER = logging.getLogger(__name__)


class HostMonitorCoordinator(DataUpdateCoordinator[HostMonitorData]):
    """Poll the mounted host system directories on a fixed interval."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.hostname: str | None = None
        self.machine_id: str | None = None
        self.model: str | None = None
        self.sw_version: str | None = platform.release()
        self._previous_cpu: CpuTimes | None = None
        self._previous_net: NetworkCounters | None = None
        self._previous_interface: str | None = None
        self._previous_time: float | None = None

    @property
    def identity(self) -> str:
        """Stable identity used for unique ids and the device registry."""
        return self.machine_id or self.config_entry.entry_id

    @property
    def network_interface(self) -> str | None:
        """The interface currently used for network statistics."""
        if self.data is None:
            return self._previous_interface
        return self.data.extras.get("network_interface")  # type: ignore[return-value]

    async def _async_setup(self) -> None:
        """Take a baseline sample so the first poll already has CPU/rates."""
        self.hostname, self.machine_id, self.model = await self.hass.async_add_executor_job(
            read_host_identity
        )
        raw = await self.hass.async_add_executor_job(read_snapshot)
        self._store_baseline(raw)

    async def _async_update_data(self) -> HostMonitorData:
        try:
            raw = await self.hass.async_add_executor_job(read_snapshot)
        except (OSError, ValueError) as err:
            raise UpdateFailed(f"Unable to read host system data: {err}") from err

        now = time.monotonic()
        previous_net = self._previous_net
        if raw.network_interface != self._previous_interface:
            previous_net = None

        data = build_data(
            raw,
            self._previous_cpu,
            previous_net,
            self._previous_time,
            now,
        )

        self._previous_cpu = raw.cpu
        self._previous_net = raw.network
        self._previous_interface = raw.network_interface
        self._previous_time = now
        return data

    def _store_baseline(self, raw: RawSnapshot) -> None:
        self._previous_cpu = raw.cpu
        self._previous_net = raw.network
        self._previous_interface = raw.network_interface
        self._previous_time = time.monotonic()
