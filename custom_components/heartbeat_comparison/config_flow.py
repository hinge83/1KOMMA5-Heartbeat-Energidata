"""Configure 1KOMMA5° access directly in Home Assistant's UI."""

from __future__ import annotations

from typing import Any
from collections.abc import Mapping

from aiohttp import ClientError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HeartbeatApiError, HeartbeatAuthError, HeartbeatClient
from .const import CONF_SYSTEM_ID, DOMAIN


class HeartbeatComparisonFlow(ConfigFlow, domain=DOMAIN):
    """The config entry owns credentials and the selected gridX system."""

    VERSION = 1

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Allow a changed password to be entered without removing the site."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            entry = self._get_reauth_entry()
            try:
                client = HeartbeatClient(
                    async_get_clientsession(self.hass),
                    entry.data[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                await client.decisions(entry.data[CONF_SYSTEM_ID])
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
            except HeartbeatAuthError:
                errors["base"] = "invalid_auth"
            except (HeartbeatApiError, ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                client = HeartbeatClient(
                    async_get_clientsession(self.hass),
                    user_input[CONF_USERNAME], user_input[CONF_PASSWORD],
                )
                systems = await client.systems()
                requested = user_input.get(CONF_SYSTEM_ID, "").strip()
                if len(systems) > 1 and not requested:
                    errors[CONF_SYSTEM_ID] = "multiple_systems"
                else:
                    system_id = requested or (str(systems[0]["id"]) if systems else "")
                    if not system_id or system_id not in {str(s["id"]) for s in systems}:
                        errors[CONF_SYSTEM_ID] = "system_not_found"
                    else:
                        await client.decisions(system_id)
                        await self.async_set_unique_id(system_id)
                        self._abort_if_unique_id_configured()
                        return self.async_create_entry(
                            title="Heartbeat beslutninger",
                            data={**user_input, CONF_SYSTEM_ID: system_id},
                        )
            except HeartbeatAuthError:
                errors["base"] = "invalid_auth"
            except (HeartbeatApiError, ClientError, TimeoutError):
                errors["base"] = "cannot_connect"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME, default=(user_input or {}).get(CONF_USERNAME, "")): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_SYSTEM_ID, default=(user_input or {}).get(CONF_SYSTEM_ID, "")): str,
            }),
            errors=errors,
        )