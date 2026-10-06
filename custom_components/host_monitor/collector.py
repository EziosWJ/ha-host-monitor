"""Filesystem access for Host Monitor.

Every function here performs blocking I/O and must be called from an executor.
Parsing and calculation lives in data.py.
"""

from __future__ import annotations

import os
import socket

from .const import (
    DMI_PRODUCT_NAME_PATH,
    PROC_LOADAVG,
    PROC_MEMINFO,
    PROC_NET_DEV,
    PROC_NET_ROUTE,
    PROC_STAT,
    PROC_UPTIME,
    ROOT_HOSTNAME_PATH,
    ROOT_MACHINE_ID_PATH,
    ROOT_PATH,
    SYS_HWMON_PATH,
    SYS_THERMAL_PATH,
)
from .data import (
    DiskUsage,
    MemoryInfo,
    NetworkCounters,
    RawSnapshot,
    TemperatureReading,
    build_disk_usage,
    choose_interface,
    choose_temperature,
    clean_model,
    parse_cpu_stat,
    parse_default_interface,
    parse_loadavg,
    parse_meminfo,
    parse_net_dev,
    parse_uptime,
)


def _read_text(path: str) -> str:
    """Read a text file, raising OSError on failure."""
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def _read_optional(path: str) -> str | None:
    """Read and strip a file, returning None when it is not readable."""
    try:
        return _read_text(path).strip()
    except OSError:
        return None


def read_snapshot() -> RawSnapshot:
    """Read all host metrics.

    Failure to read the core /proc/stat file propagates so the coordinator can
    flag the whole device as unavailable. Every other metric degrades to None
    on its own.
    """
    snapshot = RawSnapshot()
    snapshot.cpu = parse_cpu_stat(_read_text(PROC_STAT))
    snapshot.memory = _read_memory()
    snapshot.load = _read_load()
    snapshot.uptime = _read_uptime()
    snapshot.network, snapshot.network_interface = _read_network()
    snapshot.temperature = _read_temperature()
    snapshot.disk = _read_disk()
    return snapshot


def read_host_identity() -> tuple[str | None, str | None, str | None]:
    """Read the hostname, machine id and hardware model.

    The hostname is read from the mounted host root because the UTS namespace
    would otherwise expose the container hostname. Some distributions leave
    /etc/hostname empty and rely on a transient (DHCP) hostname, so fall back
    to the current UTS hostname in that case.
    """
    hostname = _read_optional(ROOT_HOSTNAME_PATH)
    if not hostname:
        hostname = socket.gethostname() or None
    return (
        hostname,
        _read_optional(ROOT_MACHINE_ID_PATH),
        clean_model(_read_optional(DMI_PRODUCT_NAME_PATH)),
    )


def _read_memory() -> MemoryInfo | None:
    try:
        return parse_meminfo(_read_text(PROC_MEMINFO))
    except (OSError, ValueError):
        return None


def _read_load() -> tuple[float, float, float] | None:
    try:
        return parse_loadavg(_read_text(PROC_LOADAVG))
    except (OSError, ValueError):
        return None


def _read_uptime() -> float | None:
    try:
        return parse_uptime(_read_text(PROC_UPTIME))
    except (OSError, ValueError):
        return None


def _read_network() -> tuple[NetworkCounters | None, str | None]:
    try:
        counters = parse_net_dev(_read_text(PROC_NET_DEV))
    except (OSError, ValueError):
        return None, None

    default_interface: str | None = None
    try:
        default_interface = parse_default_interface(_read_text(PROC_NET_ROUTE))
    except OSError:
        pass

    interface = choose_interface(counters, default_interface)
    if interface is None:
        return None, None
    return counters[interface], interface


def _read_disk() -> DiskUsage | None:
    try:
        return build_disk_usage(os.statvfs(ROOT_PATH))
    except OSError:
        return None


def _read_temperature() -> float | None:
    return choose_temperature(_collect_temperature_readings())


def _collect_temperature_readings() -> list[TemperatureReading]:
    readings: list[TemperatureReading] = []
    readings.extend(_collect_hwmon_readings())
    readings.extend(_collect_thermal_readings())
    return readings


def _collect_hwmon_readings() -> list[TemperatureReading]:
    readings: list[TemperatureReading] = []
    try:
        entries = os.listdir(SYS_HWMON_PATH)
    except OSError:
        return readings

    for entry in entries:
        base = os.path.join(SYS_HWMON_PATH, entry)
        identifier = _read_optional(os.path.join(base, "name")) or entry
        try:
            filenames = os.listdir(base)
        except OSError:
            continue
        for filename in filenames:
            if not filename.startswith("temp") or not filename.endswith("_input"):
                continue
            raw = _read_optional(os.path.join(base, filename))
            if raw is None:
                continue
            try:
                value = float(raw) / 1000
            except ValueError:
                continue
            label = _read_optional(
                os.path.join(base, f"{filename[: -len('_input')]}_label")
            )
            readings.append(
                TemperatureReading("hwmon", identifier, label, value)
            )
    return readings


def _collect_thermal_readings() -> list[TemperatureReading]:
    readings: list[TemperatureReading] = []
    try:
        entries = os.listdir(SYS_THERMAL_PATH)
    except OSError:
        return readings

    for entry in entries:
        if not entry.startswith("thermal_zone"):
            continue
        base = os.path.join(SYS_THERMAL_PATH, entry)
        zone_type = _read_optional(os.path.join(base, "type")) or entry
        raw = _read_optional(os.path.join(base, "temp"))
        if raw is None:
            continue
        try:
            value = float(raw) / 1000
        except ValueError:
            continue
        readings.append(TemperatureReading("thermal", zone_type, None, value))
    return readings
