# HA Host Monitor

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Release](https://img.shields.io/github/v/release/EziosWJ/ha-host-monitor?include_prereleases)](https://github.com/EziosWJ/ha-host-monitor/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A lightweight Home Assistant custom integration that exposes **Linux host**
metrics by reading the host's `/proc`, `/sys` and root filesystem, which are
mounted read-only into the Home Assistant container.

No sidecar agent, no database, no MQTT, no third-party monitoring library, no
external shell commands — just the kernel's own interfaces.

## Features

- CPU usage and load average (1/5/15 min)
- Memory usage, used, available and total
- Root filesystem usage, used, free and total
- Network throughput for the default-route interface (cumulative and per-second)
- CPU temperature, detected from `hwmon` with a `thermal` fallback
- Uptime
- Automatic unit scaling for byte and rate sensors (B → KiB → MiB → GiB, B/s → KiB/s → MiB/s)
- One device, one config entry, zero-configuration UI setup
- A failing metric never takes down the integration

## Requirements

- Home Assistant **Container** (Docker / Podman), `2024.6` or newer
- A Linux host
- The host directories mounted read-only into the container
- Host networking (`network_mode: host`) for correct network statistics

> Home Assistant OS and Home Assistant Supervised are **not** supported. Windows,
> macOS and remote hosts are out of scope.

## Installation

### HACS (recommended)

1. In HACS, open the menu → **Custom repositories**.
2. Add `https://github.com/EziosWJ/ha-host-monitor` with category
   **Integration**.
3. Install **Host Monitor**.
4. Restart Home Assistant.

### Manual

Copy `custom_components/host_monitor` into your Home Assistant
`config/custom_components` directory and restart.

## Mounting the host

Add the mounts to the Home Assistant service. All mounts are read-only.

```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    network_mode: host
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/host/root:ro
      - ./config:/config
    restart: unless-stopped
```

With **Podman + Quadlet** (`~/.config/containers/systemd/homeassistant.container`):

```ini
[Container]
Network=host
Volume=%h/.config/homeassistant:/config:Z
Volume=/proc:/host/proc:ro
Volume=/sys:/host/sys:ro
Volume=/:/host/root:ro
```

Then open **Settings → Devices & Services → Add Integration → Host Monitor**.
The flow is zero-configuration: it only checks that the mounts are readable.

> A container that publishes ports (`ports:`) cannot also use host networking.
> Drop the `ports:` section when you enable `network_mode: host`.

### Security note

Mounting `/:/host/root:ro` makes the whole host filesystem readable from inside
the Home Assistant container. It is required for disk usage, the host hostname
and a stable machine id. The mount is read-only, but the container can read
files such as `/etc/shadow`. Only enable it on a host you trust and understand
the exposure.

## Why host networking matters

Most host metrics are read from files that are **not** namespaced
(`/proc/stat`, `/proc/meminfo`, `/proc/loadavg`, `/proc/uptime`) and are
therefore already host-wide even inside the container.

`/proc/net/dev` and `/proc/net/route`, however, are bound to the **network
namespace**. Without host networking the network sensors would report the
container's own interfaces. Host networking is also the recommended setup for
Home Assistant Container.

## Entities

All entities belong to a single device that represents the host.

| Entity | Notes |
| --- | --- |
| CPU usage | `user+nice+system+irq+softirq+steal` over the sample window; iowait is counted as idle |
| Load (1/5/15 min) | Diagnostic |
| Memory usage / used / available / total | `used = MemTotal − MemAvailable` |
| Disk usage / used / free / total | Host root filesystem, `df` semantics |
| Network received / sent | Cumulative bytes for the default-route interface, diagnostic |
| Network receive / transmit rate | Bytes per second |
| CPU temperature | Only created when a CPU sensor is detected |
| Uptime | Diagnostic |

Memory, disk and network-rate sensors automatically scale their unit to the
current magnitude (B, KiB, MiB, GiB and B/s, KiB/s, MiB/s, GiB/s).

### A note on dynamic units

These sensors are intentionally **not** using the `data_size` / `data_rate`
device classes. Home Assistant pins the display unit of device-class sensors to
the unit stored when the entity was first registered, which would defeat
automatic scaling. As a consequence, their long-term statistics can reset when
the unit changes.

## Data sources

| Metric | Source |
| --- | --- |
| CPU | `/host/proc/stat` |
| Memory | `/host/proc/meminfo` |
| Load | `/host/proc/loadavg` |
| Uptime | `/host/proc/uptime` |
| Network | `/host/proc/net/dev`, `/host/proc/net/route` |
| Disk | `statvfs("/host/root")` |
| Temperature | `/host/sys/class/hwmon`, fallback `/host/sys/class/thermal` |
| Hostname / machine id | `/host/root/etc/hostname`, `/host/root/etc/machine-id` |

## Configuration

There is nothing to configure. A single config entry is created per Home
Assistant instance and represents the local host.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Host system directories are not mounted` | Add the three read-only mounts shown above and recreate the container |
| Network sensors show the container interfaces | Enable host networking (`network_mode: host`) |
| No temperature entity | No CPU sensor was detected; the entity is intentionally not created |
| CPU usage unavailable on first load | Expected for the very first update; a baseline is taken at setup |

## Notes and limitations

- Poll interval is 10 seconds. CPU usage and network rates need two samples.
- A failing metric (temperature, one file, a single interface) degrades to
  `unavailable` on its own; only an unreadable `/host/proc/stat` marks the whole
  device unavailable.
- Temperature detection prefers CPU-specific hwmon drivers (`coretemp`,
  `k10temp`, `zenpower`, ...) and rejects ACPI/NVMe/wifi/GPU sensors so a board
  or disk sensor is never reported as the CPU temperature.
- The network interface can change between polls (for example a VPN); rates are
  skipped for that one interval instead of reporting a bogus spike.

## Development

```bash
uv sync
uv run pytest
```

## License

[MIT](LICENSE)
