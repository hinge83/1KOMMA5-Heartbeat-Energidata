"""Set up read-only Heartbeat decisions in Home Assistant."""

from __future__ import annotations

import logging

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HeartbeatApiError, HeartbeatAuthError, HeartbeatClient
from .const import CONF_SYSTEM_ID, DOMAIN, POLL_INTERVAL

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up only the requested site; existing HACS integrations are untouched."""
    client = HeartbeatClient(
        async_get_clientsession(hass),
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    async def update() -> dict:
        try:
            return await client.decisions(entry.data[CONF_SYSTEM_ID])
        except HeartbeatAuthError as err:
            raise ConfigEntryAuthFailed("Heartbeat-login blev afvist") from err
        except (HeartbeatApiError, ClientError, TimeoutError) as err:
            raise UpdateFailed("Kunne ikke hente Heartbeat-beslutninger") from err

    coordinator = DataUpdateCoordinator[dict](
        hass, logger=logging.getLogger(__name__),
        name=DOMAIN, update_method=update, update_interval=POLL_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload comparison sensors."""
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False