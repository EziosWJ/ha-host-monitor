# HA Host Monitor

## 1. 项目定位

`HA Host Monitor` 是一个面向 Home Assistant Container 场景的轻量级自定义集成。

目标是在不部署 Glances、Prometheus、Node Exporter 等额外监控服务的情况下，直接读取挂载进 Home Assistant 容器的 Linux 宿主机 `/proc`、`/sys` 等系统信息，并将宿主机运行状态暴露为 Home Assistant 实体。

项目重点：

- 轻量
- 无额外常驻 Agent
- 无额外数据库
- 无 MQTT 依赖
- 无第三方 Python 监控库依赖
- 原生 Home Assistant 设备与实体体验
- 支持通过 HACS 安装和升级

---

## 2. V0.1 支持范围

仅支持：

- Linux 宿主机
- Home Assistant Container
- Docker / Docker Compose 部署
- 本机宿主机监控
- 本地轮询采集

暂不支持：

- Home Assistant OS
- Home Assistant Supervised
- Windows
- macOS
- 远程服务器
- 多服务器管理
- Docker 容器级监控
- GPU 监控
- Prometheus
- MQTT
- Web API
- 历史数据库

---

## 3. 数据来源

默认要求用户将宿主机目录以只读方式挂载到 Home Assistant 容器：

```yaml
volumes:
  - /proc:/host/proc:ro
  - /sys:/host/sys:ro
  - /:/host/root:ro
```

主要读取：

```text
/host/proc/stat
/host/proc/meminfo
/host/proc/loadavg
/host/proc/uptime
/host/proc/net/dev

/host/sys/class/thermal/
/host/sys/class/hwmon/

/host/root
```

禁止依赖：

- psutil
- Glances
- Prometheus Client
- Node Exporter
- 外部 Shell 命令

优先直接解析 Linux procfs / sysfs。

---

## 4. V0.1 监控指标

### CPU

- CPU 使用率 %
- Load 1m
- Load 5m
- Load 15m

CPU 使用率通过两次 `/proc/stat` 采样差值计算。

### 内存

- Memory Used
- Memory Available
- Memory Total
- Memory Usage %

数据来源：

```text
/proc/meminfo
```

### 磁盘

默认监控宿主机根分区：

```text
/host/root
```

提供：

- Disk Used
- Disk Free
- Disk Total
- Disk Usage %

### 网络

读取：

```text
/proc/net/dev
```

提供：

- RX Bytes
- TX Bytes
- RX Rate
- TX Rate

第一版可以统计全部非 loopback 网卡总量。

### 温度

优先尝试：

```text
/sys/class/hwmon/
```

其次：

```text
/sys/class/thermal/
```

提供：

- CPU Temperature

如果无法检测温度，不应导致集成加载失败。

### 系统状态

提供：

- Uptime

---

## 5. Home Assistant 实体模型

一个 Config Entry 对应一个宿主机设备。

结构：

```text
Integration
└── Host Monitor
    └── Device: Linux Host
        ├── CPU Usage
        ├── Load 1m
        ├── Load 5m
        ├── Load 15m
        ├── Memory Usage
        ├── Memory Used
        ├── Memory Available
        ├── Memory Total
        ├── Disk Usage
        ├── Disk Used
        ├── Disk Free
        ├── Disk Total
        ├── Network RX
        ├── Network TX
        ├── Network RX Rate
        ├── Network TX Rate
        ├── CPU Temperature
        └── Uptime
```

所有实体必须归属同一个 Device。

---

## 6. Home Assistant 技术实现

建议目录：

```text
custom_components/
└── host_monitor/
    ├── __init__.py
    ├── manifest.json
    ├── const.py
    ├── config_flow.py
    ├── coordinator.py
    ├── sensor.py
    ├── diagnostics.py
    ├── strings.json
    └── translations/
        ├── en.json
        └── zh-Hans.json
```

### Coordinator

统一使用：

```text
DataUpdateCoordinator
```

职责：

- 周期性读取宿主机数据
- 维护上一轮 CPU 数据
- 维护上一轮网络字节数
- 计算速率
- 统一异常处理
- 将采集结果提供给所有 Sensor

默认刷新间隔：

```text
10 秒
```

V0.1 暂不提供复杂的多级刷新周期。

### Sensor

Sensor 不允许自行访问 `/proc` 或 `/sys`。

所有 Sensor 必须读取 Coordinator 已采集的数据。

建议使用描述表驱动：

```python
HostMonitorSensorEntityDescription(...)
```

避免每个 Sensor 单独写一个类。

---

## 7. Config Flow

必须支持 UI 配置。

添加集成时：

```text
设置
→ 设备与服务
→ 添加集成
→ Host Monitor
```

第一版尽量做到零配置。

启动时自动检查：

```text
/host/proc
/host/sys
/host/root
```

如果路径不存在，应提示：

```text
Host system directories are not mounted.
```

不要直接抛 Python 异常。

后续版本可以支持自定义路径。

---

## 8. 错误处理原则

单个指标读取失败不能影响整个集成。

例如：

- 温度读取失败
- 某个网卡异常
- 某个 sysfs 文件不存在

应允许其他指标继续更新。

只有核心路径完全不可访问时才认为集成不可用，例如：

```text
/host/proc/stat
```

---

## 9. 性能目标

目标：

- 无后台子进程
- 无 Shell 调用
- 无第三方采集服务
- 无数据库
- 单次采集尽量只读取必要文件
- 默认 10 秒刷新
- 对 Home Assistant CPU / 内存影响可忽略

---

## 10. HACS

仓库需支持通过 HACS Custom Repository 安装。

根目录包含：

```text
hacs.json
README.md
LICENSE
```

发布版本使用 GitHub Release。

版本遵循：

```text
Semantic Versioning
```

例如：

```text
0.1.0
0.1.1
0.2.0
1.0.0
```

---

## 11. V0.1 非目标

不要在 V0.1 中实现：

- Web UI
- 独立 Dashboard
- Alert 规则
- 自动化规则
- Docker 容器列表
- Docker Socket 访问
- SSH
- REST API
- MQTT
- GPU
- SMART
- 硬盘温度
- 风扇转速
- 多磁盘配置
- 多网卡独立实体
- 历史数据存储

这些功能留到后续版本评估。

---

## 12. 核心设计原则

1. 优先简单。
2. 优先使用 Home Assistant 原生架构。
3. 不重复实现 Home Assistant 已经提供的能力。
4. 采集和实体展示分离。
5. 单个指标失败不能拖垮整体。
6. 尽量不增加外部依赖。
7. 第一版只解决 Linux Host Monitoring 这一件事。