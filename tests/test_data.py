"""Unit tests for the pure Host Monitor data layer."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from data import (
    BYTE_UNITS,
    DATA_RATE_UNITS,
    CpuTimes,
    NetworkCounters,
    RawSnapshot,
    TemperatureReading,
    build_data,
    build_disk_usage,
    choose_interface,
    choose_temperature,
    clean_model,
    compute_cpu_usage,
    compute_rate,
    parse_cpu_stat,
    parse_default_interface,
    parse_loadavg,
    parse_meminfo,
    parse_net_dev,
    parse_uptime,
    scale_value,
)

PROC_STAT = "cpu  100 0 100 800 100 0 0 0 0 0\ncpu0 50 0 50 400 50 0 0 0 0 0\n"
PROC_STAT_LATER = "cpu  200 0 200 1600 200 0 0 0 0 0\n"


def test_parse_cpu_stat_excludes_guest() -> None:
    parsed = parse_cpu_stat(PROC_STAT)
    assert parsed == CpuTimes(total=1100, idle=900)


def test_parse_cpu_stat_requires_cpu_line() -> None:
    with pytest.raises(ValueError):
        parse_cpu_stat("intr 0\n")


def test_compute_cpu_usage() -> None:
    previous = parse_cpu_stat(PROC_STAT)
    current = parse_cpu_stat(PROC_STAT_LATER)
    assert compute_cpu_usage(previous, current) == 18.2


def test_compute_cpu_usage_handles_equal_samples() -> None:
    sample = parse_cpu_stat(PROC_STAT)
    assert compute_cpu_usage(sample, sample) is None


MEMINFO = """\
MemTotal:       16384000 kB
MemFree:         1000000 kB
MemAvailable:    8000000 kB
Buffers:          100000 kB
Cached:          4000000 kB
SReclaimable:     200000 kB
"""

MEMINFO_NO_AVAILABLE = """\
MemTotal:       16384000 kB
MemFree:         1000000 kB
Buffers:          100000 kB
Cached:          4000000 kB
SReclaimable:     200000 kB
"""


def test_parse_meminfo_uses_memavailable() -> None:
    parsed = parse_meminfo(MEMINFO)
    assert parsed.total == 16384000 * 1024
    assert parsed.available == 8000000 * 1024
    assert parsed.used == (16384000 - 8000000) * 1024
    assert parsed.usage == pytest.approx(51.171875)


def test_parse_meminfo_falls_back_without_memavailable() -> None:
    parsed = parse_meminfo(MEMINFO_NO_AVAILABLE)
    expected_kb = 1000000 + 100000 + 4000000 + 200000
    assert parsed.available == expected_kb * 1024


def test_parse_loadavg_and_uptime() -> None:
    assert parse_loadavg("0.52 0.58 0.59 1/234 5678") == (0.52, 0.58, 0.59)
    assert parse_uptime("123456.78 987654.32") == pytest.approx(123456.78)


NET_DEV = """\
Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
    lo: 1000 1 0 0 0 0 0 0 1000 1 0 0 0 0 0 0
  eth0: 5000 10 0 0 0 0 0 0 7000 12 0 0 0 0 0 0
docker0: 20000 20 0 0 0 0 0 0 30000 30 0 0 0 0 0 0
"""

ROUTE = """\
Iface\tDestination\tGateway \tFlags\tRefCnt\tUse\tMetric\tMask\t\tMTU\tWindow\tIRTT
eth0\t00000000\t0102A8C0\t0003\t0\t0\t0\t00000000\t0\t0\t0
"""


def test_parse_net_dev() -> None:
    counters = parse_net_dev(NET_DEV)
    assert counters["eth0"] == NetworkCounters(rx=5000, tx=7000)
    assert counters["lo"] == NetworkCounters(rx=1000, tx=1000)
    assert "Inter-|   Receive" not in counters


def test_parse_default_interface() -> None:
    assert parse_default_interface(ROUTE) == "eth0"


def test_choose_interface_skips_virtual() -> None:
    counters = parse_net_dev(NET_DEV)
    assert choose_interface(counters, None) == "eth0"
    assert choose_interface(counters, "eth0") == "eth0"
    assert choose_interface(counters, "docker0") == "eth0"


def test_choose_interface_empty() -> None:
    assert choose_interface({}, "eth0") is None


def test_compute_rate() -> None:
    assert compute_rate(1000, 1500, 10.0) == 50.0
    assert compute_rate(1000, 500, 10.0) is None
    assert compute_rate(1000, 1500, 0) is None


def test_choose_temperature_prefers_hwmon_package() -> None:
    readings = [
        TemperatureReading("thermal", "acpitz", None, 32.0),
        TemperatureReading("hwmon", "coretemp", "Package id 0", 45.5),
        TemperatureReading("hwmon", "coretemp", "Core 0", 44.0),
    ]
    assert choose_temperature(readings) == 45.5


def test_choose_temperature_falls_back_to_thermal() -> None:
    readings = [
        TemperatureReading("thermal", "acpitz", None, 32.0),
        TemperatureReading("thermal", "x86_pkg_temp", None, 55.0),
    ]
    assert choose_temperature(readings) == 55.0


def test_choose_temperature_rejects_invalid() -> None:
    readings = [
        TemperatureReading("hwmon", "coretemp", "Package id 0", 0.0),
        TemperatureReading("thermal", "acpitz", None, 30.0),
    ]
    assert choose_temperature(readings) is None


def test_clean_model() -> None:
    assert clean_model("To be filled by O.E.M.") is None
    assert clean_model("") is None
    assert clean_model(None) is None
    assert clean_model("Default string") is None
    assert clean_model("NUC11TNKi") == "NUC11TNKi"


def test_scale_value_bytes() -> None:
    assert scale_value(512, BYTE_UNITS) == (512.0, "B")
    assert scale_value(1536, BYTE_UNITS) == (1.5, "KiB")
    assert scale_value(5 * 1024**2, BYTE_UNITS) == (5.0, "MiB")
    assert scale_value(3 * 1024**3, BYTE_UNITS) == (3.0, "GiB")
    assert scale_value(0, BYTE_UNITS) == (0.0, "B")


def test_scale_value_data_rate() -> None:
    assert scale_value(900, DATA_RATE_UNITS) == (900.0, "B/s")
    assert scale_value(2048, DATA_RATE_UNITS) == (2.0, "KiB/s")
    assert scale_value(3 * 1024**2, DATA_RATE_UNITS) == (3.0, "MiB/s")


def test_build_disk_usage_df_semantics() -> None:
    stat = SimpleNamespace(f_frsize=4096, f_blocks=1000, f_bfree=300, f_bavail=200)
    usage = build_disk_usage(stat)
    assert usage.total == 1000 * 4096
    assert usage.free == 200 * 4096
    assert usage.used == 700 * 4096
    assert usage.usage == pytest.approx(77.777777, rel=1e-3)


def test_build_data_combines_snapshot() -> None:
    previous = parse_cpu_stat(PROC_STAT)
    raw = RawSnapshot(
        cpu=parse_cpu_stat(PROC_STAT_LATER),
        load=(0.5, 0.6, 0.7),
        memory=parse_meminfo(MEMINFO),
        uptime=1234.9,
        network=NetworkCounters(rx=2000, tx=3000),
        network_interface="eth0",
        temperature=42.0,
    )
    data = build_data(raw, previous, NetworkCounters(rx=1000, tx=1000), 0.0, 10.0)
    assert data.cpu_usage == 18.2
    assert (data.load_1m, data.load_5m, data.load_15m) == (0.5, 0.6, 0.7)
    assert data.memory_usage == pytest.approx(51.2)
    assert data.network_rx_rate == 100.0
    assert data.network_tx_rate == 200.0
    assert data.cpu_temperature == 42.0
    assert data.uptime == 1235
    assert data.extras["network_interface"] == "eth0"
