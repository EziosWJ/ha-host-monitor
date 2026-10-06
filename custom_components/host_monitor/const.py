"""Constants for the Host Monitor integration."""

DOMAIN = "host_monitor"
NAME = "Host Monitor"
MANUFACTURER = "HA Host Monitor"

PROC_PATH = "/host/proc"
SYS_PATH = "/host/sys"
ROOT_PATH = "/host/root"

PROC_STAT = f"{PROC_PATH}/stat"
PROC_MEMINFO = f"{PROC_PATH}/meminfo"
PROC_LOADAVG = f"{PROC_PATH}/loadavg"
PROC_UPTIME = f"{PROC_PATH}/uptime"
PROC_NET_DEV = f"{PROC_PATH}/net/dev"
PROC_NET_ROUTE = f"{PROC_PATH}/net/route"

SYS_HWMON_PATH = f"{SYS_PATH}/class/hwmon"
SYS_THERMAL_PATH = f"{SYS_PATH}/class/thermal"

ROOT_HOSTNAME_PATH = f"{ROOT_PATH}/etc/hostname"
ROOT_MACHINE_ID_PATH = f"{ROOT_PATH}/etc/machine-id"
DMI_PRODUCT_NAME_PATH = f"{SYS_PATH}/class/dmi/id/product_name"

DEFAULT_SCAN_INTERVAL = 10
