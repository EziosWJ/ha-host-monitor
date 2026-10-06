"""Sensor platform for Host Monitor."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import HostMonitorCoordinator
from .data import SCALE_BYTES, SCALE_DATA_RATE, HostMonitorData
from .entity import HostMonitorEntity


@dataclass(frozen=True, kw_only=True)
class HostMonitorSensorEntityDescription(SensorEntityDescription):
    """Sensor description with a value accessor into the snapshot."""

    value_fn: Callable[[HostMonitorData], float | int | None]
    auto_scale: str | None = None


CPU_DESCRIPTIONS: tuple[HostMonitorSensorEntityDescription, ...] = (
    HostMonitorSensorEntityDescription(
        key="cpu_usage",
        translation_key="cpu_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:cpu-64-bit",
        value_fn=lambda data: data.cpu_usage,
    ),
    HostMonitorSensorEntityDescription(
        key="load_1m",
        translation_key="load_1m",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:gauge",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.load_1m,
    ),
    HostMonitorSensorEntityDescription(
        key="load_5m",
        translation_key="load_5m",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:gauge",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.load_5m,
    ),
    HostMonitorSensorEntityDescription(
        key="load_15m",
        translation_key="load_15m",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:gauge",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.load_15m,
    ),
)

MEMORY_DESCRIPTIONS: tuple[HostMonitorSensorEntityDescription, ...] = (
    HostMonitorSensorEntityDescription(
        key="memory_usage",
        translation_key="memory_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:memory",
        value_fn=lambda data: data.memory_usage,
    ),
    HostMonitorSensorEntityDescription(
        key="memory_used",
        translation_key="memory_used",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:memory",
        auto_scale=SCALE_BYTES,
        value_fn=lambda data: data.memory_used,
    ),
    HostMonitorSensorEntityDescription(
        key="memory_available",
        translation_key="memory_available",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:memory",
        auto_scale=SCALE_BYTES,
        value_fn=lambda data: data.memory_available,
    ),
    HostMonitorSensorEntityDescription(
        key="memory_total",
        translation_key="memory_total",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=2,
        icon="mdi:memory",
        entity_category=EntityCategory.DIAGNOSTIC,
        auto_scale=SCALE_BYTES,
        value_fn=lambda data: data.memory_total,
    ),
)

DISK_DESCRIPTIONS: tuple[HostMonitorSensorEntityDescription, ...] = (
    HostMonitorSensorEntityDescription(
        key="disk_usage",
        translation_key="disk_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:harddisk",
        value_fn=lambda data: data.disk_usage,
    ),
    HostMonitorSensorEntityDescription(
        key="disk_used",
        translation_key="disk_used",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:harddisk",
        auto_scale=SCALE_BYTES,
        value_fn=lambda data: data.disk_used,
    ),
    HostMonitorSensorEntityDescription(
        key="disk_free",
        translation_key="disk_free",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:harddisk",
        auto_scale=SCALE_BYTES,
        value_fn=lambda data: data.disk_free,
    ),
    HostMonitorSensorEntityDescription(
        key="disk_total",
        translation_key="disk_total",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_display_precision=2,
        icon="mdi:harddisk",
        entity_category=EntityCategory.DIAGNOSTIC,
        auto_scale=SCALE_BYTES,
        value_fn=lambda data: data.disk_total,
    ),
)

NETWORK_DESCRIPTIONS: tuple[HostMonitorSensorEntityDescription, ...] = (
    HostMonitorSensorEntityDescription(
        key="network_rx",
        translation_key="network_rx",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.network_rx,
    ),
    HostMonitorSensorEntityDescription(
        key="network_tx",
        translation_key="network_tx",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.network_tx,
    ),
    HostMonitorSensorEntityDescription(
        key="network_rx_rate",
        translation_key="network_rx_rate",
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:download-network",
        auto_scale=SCALE_DATA_RATE,
        value_fn=lambda data: data.network_rx_rate,
    ),
    HostMonitorSensorEntityDescription(
        key="network_tx_rate",
        translation_key="network_tx_rate",
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:upload-network",
        auto_scale=SCALE_DATA_RATE,
        value_fn=lambda data: data.network_tx_rate,
    ),
)

SYSTEM_DESCRIPTIONS: tuple[HostMonitorSensorEntityDescription, ...] = (
    HostMonitorSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.uptime,
    ),
)

TEMPERATURE_DESCRIPTION = HostMonitorSensorEntityDescription(
    key="cpu_temperature",
    translation_key="cpu_temperature",
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    device_class=SensorDeviceClass.TEMPERATURE,
    state_class=SensorStateClass.MEASUREMENT,
    suggested_display_precision=1,
    value_fn=lambda data: data.cpu_temperature,
)

BASE_DESCRIPTIONS: tuple[HostMonitorSensorEntityDescription, ...] = (
    *CPU_DESCRIPTIONS,
    *MEMORY_DESCRIPTIONS,
    *DISK_DESCRIPTIONS,
    *NETWORK_DESCRIPTIONS,
    *SYSTEM_DESCRIPTIONS,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Host Monitor sensors from a config entry."""
    coordinator: HostMonitorCoordinator = entry.runtime_data

    descriptions = list(BASE_DESCRIPTIONS)
    if coordinator.data is not None and coordinator.data.cpu_temperature is not None:
        descriptions.append(TEMPERATURE_DESCRIPTION)

    async_add_entities(
        HostMonitorEntity(coordinator, description) for description in descriptions
    )
