"""Energy Management switch matching the 1KOMMA5° portal."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import HeartbeatApiError, HeartbeatAuthError
from .const import CONF_SYSTEM_ID, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    state = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([EnergyManagementSwitch(state["energy_management"], state["client"], entry)])


class EnergyManagementSwitch(CoordinatorEntity, SwitchEntity):
    """Show and change the portal's agreedEMSTerms setting."""

    _attr_has_entity_name = True
    _attr_name = "Energy Management"
    _attr_icon = "mdi:home-lightning-bolt"

    def __init__(self, coordinator, client, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._client = client
        self._system_id = entry.data[CONF_SYSTEM_ID]
        self._attr_unique_id = f"{self._system_id}_energy_management"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._system_id)},
            "name": "1KOMMA5° Heartbeat & Energidata",
            "manufacturer": "1KOMMA5°",
        }

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.last_update_success:
            return None
        return self.coordinator.data if isinstance(self.coordinator.data, bool) else None

    async def _set_enabled(self, enabled: bool) -> None:
        try:
            await self._client.set_energy_management(self._system_id, enabled)
        except (HeartbeatApiError, HeartbeatAuthError, OSError, TimeoutError) as err:
            raise HomeAssistantError("Kunne ikke ændre Energy Management i GridX") from err
        finally:
            await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs) -> None:
        await self._set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._set_enabled(False)
