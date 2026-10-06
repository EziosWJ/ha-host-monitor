"""Config flow for Host Monitor."""

from __future__ import annotations

import os

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN, PROC_PATH, PROC_STAT, ROOT_PATH, SYS_PATH


def missing_mounts() -> list[str]:
    """Return the labels of required host mounts that are missing or unreadable."""
    missing: list[str] = []
    if not os.path.isdir(PROC_PATH) or not os.access(PROC_STAT, os.R_OK):
        missing.append("proc")
    if not os.path.isdir(SYS_PATH):
        missing.append("sys")
    if not os.path.isdir(ROOT_PATH):
        missing.append("root")
    return missing


class HostMonitorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Host Monitor config flow.

    The first version is zero-configuration: it only validates that the host
    directories are mounted and then creates the single config entry.
    """

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        """Validate mounts and create the config entry."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            missing = await self.hass.async_add_executor_job(missing_mounts)
            if missing:
                errors["base"] = "not_mounted"
            else:
                return self.async_create_entry(title="Host Monitor", data={})

        return self.async_show_form(
            step_id="user",
            errors=errors,
            description_placeholders={
                "proc": PROC_PATH,
                "sys": SYS_PATH,
                "root": ROOT_PATH,
            },
        )
