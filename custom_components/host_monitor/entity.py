"""Base entity for Host Monitor."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import HostMonitorCoordinator
from .data import SCALE_FAMILIES, scale_value

if TYPE_CHECKING:
    from .sensor import HostMonitorSensorEntityDescription


class HostMonitorEntity(CoordinatorEntity[HostMonitorCoordinator], SensorEntity):
    """A sensor backed by the shared coordinator snapshot."""

    _attr_has_entity_name = True
    entity_description: HostMonitorSensorEntityDescription

    def __init__(
        self,
        coordinator: HostMonitorCoordinator,
        description: HostMonitorSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.identity}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """All entities belong to the monitored host device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.identity)},
            name=self.coordinator.hostname or "Linux Host",
            manufacturer=MANUFACTURER,
            model=self.coordinator.model,
            sw_version=self.coordinator.sw_version,
        )

    @property
    def native_value(self) -> float | int | None:
        """Read the value from the coordinator snapshot."""
        return self._scaled_value()[0]

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit matching the current value when auto scaling."""
        value, unit = self._scaled_value()
        if value is None:
            return self.entity_description.native_unit_of_measurement
        return unit

    def _scaled_value(self) -> tuple[float | int | None, str | None]:
        """Return (value, unit), auto scaling byte/rate sensors by magnitude."""
        description = self.entity_description
        base_unit = description.native_unit_of_measurement
        if self.coordinator.data is None:
            return None, base_unit
        raw = description.value_fn(self.coordinator.data)
        if raw is None:
            return None, base_unit
        if description.auto_scale is None:
            return raw, base_unit
        scaled, unit = scale_value(raw, SCALE_FAMILIES[description.auto_scale])
        return scaled, unit

    @property
    def available(self) -> bool:
        """An entity is unavailable when its own metric is missing."""
        return super().available and self.native_value is not None
