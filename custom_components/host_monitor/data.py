"""Pure parsing and calculation helpers.

This module only relies on the standard library so it stays unit-testable
without importing Home Assistant. All filesystem access lives in collector.py.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

# Interfaces that should never be considered the "host" interface when the
# default route cannot be resolved.
VIRTUAL_INTERFACE_PREFIXES = (
    "veth",
    "docker",
    "br-",
    "virbr",
    "tun",
    "tap",
    "vmnet",
    "vboxnet",
    "tailscale",
    "wg",
    "zt",
)

HWMON_CPU_NAMES = ("coretemp", "k10temp", "zenpower", "cpu_thermal", "soc_thermal")
HWMON_LABEL_HINTS = ("package", "tctl", "tdie")
THERMAL_CPU_TYPES = ("x86_pkg_temp", "cpu-thermal", "cpu_thermal", "soc_thermal")
THERMAL_EXCLUDE_TYPES = ("acpitz", "pch", "iwlwifi", "nvme", "wifi", "gpu")

MIN_TEMPERATURE = 0.0
MAX_TEMPERATURE = 150.0

DMI_PLACEHOLDERS = (
    "to be filled by o.e.m.",
    "default string",
    "system product name",
    "system version",
    "not specified",
    "undefined",
    "invalid",
    "none",
)

SCALE_BYTES = "bytes"
SCALE_DATA_RATE = "data_rate"

BYTE_UNITS: tuple[tuple[int, str], ...] = (
    (1024**4, "TiB"),
    (1024**3, "GiB"),
    (1024**2, "MiB"),
    (1024, "KiB"),
    (1, "B"),
)

DATA_RATE_UNITS: tuple[tuple[int, str], ...] = (
    (1024**3, "GiB/s"),
    (1024**2, "MiB/s"),
    (1024, "KiB/s"),
    (1, "B/s"),
)

SCALE_FAMILIES: dict[str, tuple[tuple[int, str], ...]] = {
    SCALE_BYTES: BYTE_UNITS,
    SCALE_DATA_RATE: DATA_RATE_UNITS,
}


@dataclass(slots=True)
class CpuTimes:
    """Aggregate CPU time counters from /proc/stat."""

    total: int
    idle: int


@dataclass(slots=True)
class MemoryInfo:
    """Memory figures in bytes."""

    total: int
    used: int
    available: int
    usage: float


@dataclass(slots=True)
class DiskUsage:
    """Disk figures in bytes."""

    total: int
    used: int
    free: int
    usage: float


@dataclass(slots=True)
class NetworkCounters:
    """Cumulative interface byte counters."""

    rx: int
    tx: int


@dataclass(slots=True)
class TemperatureReading:
    """A single candidate temperature reading in degrees Celsius."""

    source: str
    identifier: str
    label: str | None
    value: float


@dataclass(slots=True)
class RawSnapshot:
    """One raw read of the host filesystem."""

    cpu: CpuTimes | None = None
    memory: MemoryInfo | None = None
    load: tuple[float, float, float] | None = None
    uptime: float | None = None
    network: NetworkCounters | None = None
    network_interface: str | None = None
    temperature: float | None = None
    disk: DiskUsage | None = None


@dataclass(slots=True)
class HostMonitorData:
    """Values exposed to entities. None means "not available"."""

    cpu_usage: float | None = None
    load_1m: float | None = None
    load_5m: float | None = None
    load_15m: float | None = None
    memory_used: int | None = None
    memory_available: int | None = None
    memory_total: int | None = None
    memory_usage: float | None = None
    disk_used: int | None = None
    disk_free: int | None = None
    disk_total: int | None = None
    disk_usage: float | None = None
    network_rx: int | None = None
    network_tx: int | None = None
    network_rx_rate: float | None = None
    network_tx_rate: float | None = None
    cpu_temperature: float | None = None
    uptime: float | None = None
    extras: dict[str, object] = field(default_factory=dict)


def parse_cpu_stat(text: str) -> CpuTimes:
    """Parse the aggregate ``cpu`` line of /proc/stat.

    guest/guest_nice are intentionally excluded: they are already accounted
    for inside user/nice and would otherwise be double counted.
    """
    for line in text.splitlines():
        if not line.startswith("cpu "):
            continue
        values = [int(value) for value in line.split()[1:9]]
        total = sum(values)
        idle = values[3] + values[4]  # idle + iowait
        return CpuTimes(total=total, idle=idle)
    raise ValueError("no aggregate cpu line in /proc/stat")


def parse_meminfo(text: str) -> MemoryInfo:
    """Parse /proc/meminfo.

    ``used`` is defined as ``MemTotal - MemAvailable`` to keep the figure
    simple and predictable. MemAvailable is emulated on kernels that predate
    it to avoid a hard failure.
    """
    info: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        parts = rest.split()
        if parts:
            info[key] = int(parts[0])

    total = info.get("MemTotal", 0) * 1024
    if "MemAvailable" in info:
        available_kb = info["MemAvailable"]
    else:
        available_kb = (
            info.get("MemFree", 0)
            + info.get("Buffers", 0)
            + info.get("Cached", 0)
            + info.get("SReclaimable", 0)
        )
    available = available_kb * 1024
    used = max(total - available, 0)
    usage = (used / total * 100) if total else 0.0
    return MemoryInfo(total=total, used=used, available=available, usage=usage)


def parse_loadavg(text: str) -> tuple[float, float, float]:
    """Parse /proc/loadavg into the 1, 5 and 15 minute averages."""
    parts = text.split()
    return (float(parts[0]), float(parts[1]), float(parts[2]))


def parse_uptime(text: str) -> float:
    """Parse the uptime in seconds from /proc/uptime."""
    return float(text.split()[0])


def parse_net_dev(text: str) -> dict[str, NetworkCounters]:
    """Parse /proc/net/dev into per-interface cumulative counters."""
    counters: dict[str, NetworkCounters] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        interface, _, rest = line.partition(":")
        fields = rest.split()
        if len(fields) < 16:
            continue
        counters[interface.strip()] = NetworkCounters(
            rx=int(fields[0]),
            tx=int(fields[8]),
        )
    return counters


def parse_default_interface(text: str) -> str | None:
    """Return the interface carrying the default route from /proc/net/route."""
    for line in text.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 4:
            continue
        interface, destination, _, flags = fields[0], fields[1], fields[2], fields[3]
        try:
            if int(destination, 16) == 0 and int(flags, 16) & 0x2:
                return interface
        except ValueError:
            continue
    return None


def is_virtual_interface(name: str) -> bool:
    """Return True for loopback and common virtual interfaces."""
    return name == "lo" or name.startswith(VIRTUAL_INTERFACE_PREFIXES)


def choose_interface(
    counters: Mapping[str, NetworkCounters],
    default_interface: str | None,
) -> str | None:
    """Choose the single interface used for network statistics.

    Preference order: the default route interface, then the busiest physical
    interface, then the default route interface even if it looks virtual.
    """
    if not counters:
        return None
    if (
        default_interface
        and default_interface in counters
        and not is_virtual_interface(default_interface)
    ):
        return default_interface
    physical = [name for name in counters if not is_virtual_interface(name)]
    if physical:
        return max(physical, key=lambda name: counters[name].rx + counters[name].tx)
    if default_interface and default_interface in counters:
        return default_interface
    return None


def compute_cpu_usage(previous: CpuTimes, current: CpuTimes) -> float | None:
    """Compute CPU usage percentage between two /proc/stat samples."""
    total_delta = current.total - previous.total
    idle_delta = current.idle - previous.idle
    if total_delta <= 0:
        return None
    usage = (total_delta - idle_delta) / total_delta * 100
    return round(min(max(usage, 0.0), 100.0), 1)


def compute_rate(previous: int, current: int, elapsed: float) -> float | None:
    """Compute a per-second rate, tolerating counter resets."""
    if elapsed <= 0:
        return None
    delta = current - previous
    if delta < 0:
        return None
    return round(delta / elapsed, 1)


def scale_value(
    value: float,
    units: tuple[tuple[int, str], ...],
) -> tuple[float, str]:
    """Scale a value to the largest unit that fits, e.g. bytes to MiB."""
    magnitude = abs(value)
    for factor, unit in units:
        if magnitude >= factor:
            return round(value / factor, 2), unit
    return float(value), units[-1][1]


def clean_model(model: str | None) -> str | None:
    """Drop BIOS placeholder values such as "To be filled by O.E.M."."""
    if not model or model.strip().lower() in DMI_PLACEHOLDERS:
        return None
    return model


def is_plausible_temperature(value: float) -> bool:
    """Reject placeholder and clearly invalid temperature readings.

    Zero and negative readings are treated as disabled/placeholder sensors;
    a running CPU is never reported as 0 degrees.
    """
    return MIN_TEMPERATURE < value <= MAX_TEMPERATURE


def choose_temperature(readings: list[TemperatureReading]) -> float | None:
    """Pick a CPU temperature, preferring hwmon over thermal.

    Non CPU-ish sensors (ACPI, NVMe, wifi, GPU) are ignored on purpose so a
    board or disk sensor is never reported as the CPU temperature.
    """
    plausible = [reading for reading in readings if is_plausible_temperature(reading.value)]
    if not plausible:
        return None

    hwmon = [
        reading
        for reading in plausible
        if reading.source == "hwmon"
        and reading.identifier.lower() in HWMON_CPU_NAMES
    ]
    for reading in hwmon:
        label = (reading.label or "").lower()
        if any(hint in label for hint in HWMON_LABEL_HINTS):
            return round(reading.value, 1)
    if hwmon:
        return round(hwmon[0].value, 1)

    for reading in plausible:
        if reading.source != "thermal":
            continue
        identifier = reading.identifier.lower()
        if any(excluded in identifier for excluded in THERMAL_EXCLUDE_TYPES):
            continue
        if any(cpu_type in identifier for cpu_type in THERMAL_CPU_TYPES):
            return round(reading.value, 1)
    return None


def build_disk_usage(stat: os.statvfs_result) -> DiskUsage:
    """Build disk usage figures using df semantics.

    ``usage`` uses ``used / (used + free)`` so reserved blocks are excluded
    from the denominator, matching the output of ``df``.
    """
    block_size = stat.f_frsize
    total = stat.f_blocks * block_size
    free = stat.f_bavail * block_size
    used = (stat.f_blocks - stat.f_bfree) * block_size
    denominator = used + free
    usage = (used / denominator * 100) if denominator else 0.0
    return DiskUsage(total=total, used=used, free=free, usage=round(usage, 1))


def build_data(
    raw: RawSnapshot,
    previous_cpu: CpuTimes | None,
    previous_net: NetworkCounters | None,
    previous_time: float | None,
    now: float,
) -> HostMonitorData:
    """Combine a raw snapshot with previous counters into entity values."""
    data = HostMonitorData()

    if raw.cpu is not None and previous_cpu is not None:
        data.cpu_usage = compute_cpu_usage(previous_cpu, raw.cpu)

    if raw.load is not None:
        data.load_1m, data.load_5m, data.load_15m = raw.load

    if raw.memory is not None:
        data.memory_used = raw.memory.used
        data.memory_available = raw.memory.available
        data.memory_total = raw.memory.total
        data.memory_usage = round(raw.memory.usage, 1)

    if raw.disk is not None:
        data.disk_used = raw.disk.used
        data.disk_free = raw.disk.free
        data.disk_total = raw.disk.total
        data.disk_usage = raw.disk.usage

    if raw.network is not None:
        data.network_rx = raw.network.rx
        data.network_tx = raw.network.tx
        if previous_net is not None and previous_time is not None:
            elapsed = now - previous_time
            data.network_rx_rate = compute_rate(previous_net.rx, raw.network.rx, elapsed)
            data.network_tx_rate = compute_rate(previous_net.tx, raw.network.tx, elapsed)
        data.extras["network_interface"] = raw.network_interface

    data.cpu_temperature = raw.temperature
    if raw.uptime is not None:
        data.uptime = float(round(raw.uptime))

    return data
