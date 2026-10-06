# HA Host Monitor

[English](README.md) | **简体中文**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Release](https://img.shields.io/github/v/release/EziosWJ/ha-host-monitor?include_prereleases)](https://github.com/EziosWJ/ha-host-monitor/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个轻量的 Home Assistant 自定义集成，通过读取**以只读方式挂载进 Home Assistant
容器**的宿主机 `/proc`、`/sys` 和根文件系统，暴露 Linux 宿主机运行指标。

无需旁路 Agent、无需数据库、无需 MQTT、不依赖任何第三方监控库、不调用外部 Shell
命令——只使用内核自身的接口。

## 功能

- CPU 使用率与负载（1/5/15 分钟）
- 内存使用率、已用、可用、总量
- 根文件系统使用率、已用、可用、总量
- 默认路由网卡的网络吞吐（累计量与速率）
- CPU 温度（优先 `hwmon`，回退 `thermal`）
- 运行时间（Uptime）
- 内存/磁盘/网络速率实体按量级自动切换单位（B → KiB → MiB → GiB，B/s → KiB/s → MiB/s）
- 单个设备、单个配置项、零配置 UI 添加
- 单个指标失败不会拖垮整个集成

## 环境要求

- Home Assistant **Container**（Docker / Podman），`2024.6` 或更高
- Linux 宿主机
- 已把宿主机目录以只读方式挂载进容器
- 使用 host 网络（`network_mode: host`）以获得正确的网络统计

> 不支持 Home Assistant OS 和 Home Assistant Supervised。Windows、macOS
> 以及远程服务器不在支持范围内。

## 安装

### HACS（推荐）

1. 打开 HACS → 右上角菜单 → **自定义仓库（Custom repositories）**。
2. 添加 `https://github.com/EziosWJ/ha-host-monitor`，类别选 **Integration**。
3. 安装 **Host Monitor**。
4. 重启 Home Assistant。

### 手动安装

把 `custom_components/host_monitor` 拷贝到 Home Assistant 的
`config/custom_components` 目录并重启。

## 挂载宿主机目录

给 Home Assistant 服务添加以下挂载，全部为只读。

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

若使用 **Podman + Quadlet**
（`~/.config/containers/systemd/homeassistant.container`）：

```ini
[Container]
Network=host
Volume=%h/.config/homeassistant:/config:Z
Volume=/proc:/host/proc:ro
Volume=/sys:/host/sys:ro
Volume=/:/host/root:ro
```

然后在 **设置 → 设备与服务 → 添加集成 → Host Monitor**。配置流程是零配置的，
只会检查挂载是否可以读取。

> 一旦启用 host 网络，容器就不能再发布端口（`ports:`）。请移除 `ports:` 段落。

### 安全提示

将 `/:/host/root:ro` 挂载进容器后，Home Assistant 容器可以读取宿主机的整个根文件
系统（磁盘用量、主机名和稳定的机器码都需要它）。挂载是只读的，但容器仍能读取诸如
`/etc/shadow` 之类的文件。请仅在你自己信任并理解其暴露面的主机上启用。

## 为什么需要 host 网络

大部分指标来自**不按命名空间隔离**的文件（`/proc/stat`、`/proc/meminfo`、
`/proc/loadavg`、`/proc/uptime`），因此即便在容器内也已经是宿主机全局值。

但 `/proc/net/dev` 和 `/proc/net/route` 是**绑定网络命名空间**的。如果容器没有使用
host 网络，网络传感器读到的会是容器自己的网卡。Host 网络同时也是 Home Assistant
Container 官方推荐的方式。

## 实体

所有实体都属于同一个代表宿主机的设备。

| 实体 | 说明 |
| --- | --- |
| CPU 使用率 | 采样窗口内 `user+nice+system+irq+softirq+steal`；iowait 计入 idle |
| 负载（1/5/15 分钟） | 诊断类 |
| 内存 使用率 / 已用 / 可用 / 总量 | `已用 = MemTotal − MemAvailable` |
| 磁盘 使用率 / 已用 / 可用 / 总量 | 宿主机根分区，采用 `df` 口径 |
| 网络 接收 / 发送 | 默认路由网卡的累计字节，诊断类 |
| 网络 接收 / 发送速率 | 字节/秒 |
| CPU 温度 | 仅在检测到 CPU 温度传感器时创建 |
| 运行时间 | 诊断类 |

内存、磁盘与网络速率实体在每次更新时按当前数值量级自动切换单位
（B、KiB、MiB、GiB 以及 B/s、KiB/s、MiB/s、GiB/s）。

### 关于动态单位

这些实体**刻意不使用** `data_size` / `data_rate` 设备类。Home Assistant 会把带设备类
的实体的显示单位固定在实体首次注册时写入的单位上，从而破坏自动缩放。相应的代价是：
当单位发生切换时，它们的长期统计（statistics）可能会重置。

## 数据来源

| 指标 | 来源 |
| --- | --- |
| CPU | `/host/proc/stat` |
| 内存 | `/host/proc/meminfo` |
| 负载 | `/host/proc/loadavg` |
| 运行时间 | `/host/proc/uptime` |
| 网络 | `/host/proc/net/dev`、`/host/proc/net/route` |
| 磁盘 | `statvfs("/host/root")` |
| 温度 | `/host/sys/class/hwmon`，回退 `/host/sys/class/thermal` |
| 主机名 / 机器码 | `/host/root/etc/hostname`、`/host/root/etc/machine-id` |

## 配置

无需配置。每个 Home Assistant 实例创建一个配置项，代表本机宿主机。

## 故障排查

| 现象 | 处理 |
| --- | --- |
| 提示 `Host system directories are not mounted` | 按上文添加三个只读挂载，并重建容器 |
| 网络传感器显示的是容器网卡 | 启用 host 网络（`network_mode: host`） |
| 没有温度实体 | 未检测到 CPU 温度传感器，实体被有意省略 |
| 首次加载时 CPU 使用率不可用 | 属正常现象；插件在启动时采集了基准值，仅首次更新可能短暂不可用 |

## 注意事项与限制

- 轮询间隔为 10 秒。CPU 使用率与网络速率需要两次采样。
- 单个指标失败（温度、某个文件、某块网卡）只会让对应实体变为 `unavailable`；
  只有 `/host/proc/stat` 不可读时才会判定整个设备不可用。
- 温度识别优先使用 CPU 专用 hwmon 驱动（`coretemp`、`k10temp`、`zenpower` 等），
  并排除 ACPI/NVMe/无线网卡/GPU 传感器，避免把主板或硬盘温度误报为 CPU 温度。
- 网卡可能在两次采样之间切换（例如 VPN）；此时跳过该周期的速率计算，而不是给出
  错误的尖峰。

## 开发

```bash
uv sync
uv run pytest
```

## 许可证

[MIT](LICENSE)
