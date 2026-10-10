"""Expose Heartbeat decisions for Home Assistant recorder and dashboards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .const import CONF_SYSTEM_ID, DOMAIN


def _when(value: Any) -> datetime | None:
    """Parse an ISO time without inventing one for a missing field."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _events(data: dict) -> list[dict]:
    """Flatten the published gridX decisions/items structure."""
    events: list[dict] = []
    for group in data.get("decisions", []):
        if not isinstance(group, dict):
            continue
        nested = group.get("items")
        for row in (nested if isinstance(nested, list) else [group]):
            if not isinstance(row, dict):
                continue
            case = row.get("case_name") or row.get("caseName")
            start = row.get("from") or row.get("start") or group.get("from") or group.get("start")
            end = row.get("to") or row.get("end") or group.get("to") or group.get("end")
            if case and start:
                events.append({"case": str(case), "start": str(start), "end": str(end or "")})
    return sorted(events, key=lambda e: e["start"])


def _battery_events(data: dict) -> list[dict]:
    """Discard simultaneous grid/EV/heat-pump decisions."""
    return [e for e in _events(data) if e["case"].startswith("BATTERY_")]


def _active(events: list[dict], now: datetime) -> dict | None:
    """Choose a battery decision only for the current time window."""
    active = [
        e for e in events if (start := _when(e["start"])) and start <= now
        and (end := _when(e["end"])) and now < end
    ]
    return active[-1] if active else None


def _latest_past(events: list[dict], now: datetime) -> dict | None:
    """Never report a future plan as the latest observed decision."""
    past = [e for e in events if (start := _when(e["start"])) and start <= now]
    return past[-1] if past else None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DecisionSensor(coordinator, entry, "current"),
        DecisionSensor(coordinator, entry, "latest"),
        DecisionSensor(coordinator, entry, "count"),
    ])


class DecisionSensor(CoordinatorEntity[DataUpdateCoordinator[dict]], SensorEntity):
    """One active, latest or count state; raw context stays as attributes."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DataUpdateCoordinator[dict], entry: ConfigEntry, kind: str) -> None:
        super().__init__(coordinator)
        self.kind = kind
        self._attr_unique_id = f"{entry.data[CONF_SYSTEM_ID]}_{kind}"
        self._attr_name = {
            "current": "Aktuel beslutning", "latest": "Seneste beslutning",
            "count": "Antal beslutninger",
        }[kind]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data[CONF_SYSTEM_ID])},
            "name": "1KOMMA5° Heartbeat sammenligning",
            "manufacturer": "1KOMMA5°",
        }

    async def async_added_to_hass(self) -> None:
        """Refresh time-dependent decisions without polling the cloud again."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._refresh_time_state, timedelta(minutes=1))
        )

    @callback
    def _refresh_time_state(self, now: datetime) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | int:
        events = _battery_events(self.coordinator.data)
        if self.kind == "count":
            return len(events)
        now = datetime.now(timezone.utc)
        if self.kind == "latest":
            event = _latest_past(events, now)
            return event["case"] if event else "Ingen beslutning"
        event = _active(events, now)
        return event["case"] if event else "Ingen aktiv batteribeslutning"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        events = _battery_events(self.coordinator.data)
        if self.kind == "count":
            now = datetime.now(timezone.utc)
            past = [e for e in events if (start := _when(e["start"])) and start <= now]
            future = [e for e in events if (start := _when(e["start"])) and start > now]
            return {"seneste": past[-12:], "kommende": future[:12]}
        now = datetime.now(timezone.utc)
        event = (_active(events, now) if self.kind == "current"
                 else _latest_past(events, now)) or {}
        return {"fra": event.get("start"), "til": event.get("end"),
                "kode": event.get("case")}