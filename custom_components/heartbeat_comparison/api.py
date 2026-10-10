"""Client for the legacy 1KOMMA5° gridX API.

Reads telemetry/decisions and writes only the EMS terms setting when requested.
No API response or credentials are logged.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from aiohttp import ClientResponseError, ClientSession

from .const import API_URL, AUTH_CLIENT_ID, AUTH_URL


class HeartbeatAuthError(Exception):
    """The user credentials were rejected."""


class HeartbeatApiError(Exception):
    """An API response could not be used."""


class HeartbeatClient:
    """Small scoped client; access token is kept only in memory."""

    def __init__(self, session: ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._token: str | None = None
        self._expires = datetime.min.replace(tzinfo=timezone.utc)

    async def _login(self) -> None:
        payload = {
            "grant_type": "http://auth0.com/oauth/grant-type/password-realm",
            "username": self._username,
            "password": self._password,
            "audience": "my.gridx",
            "client_id": AUTH_CLIENT_ID,
            "scope": "email openid offline_access",
            "realm": "1komma5grad-authentication-db",
        }
        try:
            async with self._session.post(AUTH_URL, json=payload, timeout=20) as response:
                if response.status in (400, 401, 403):
                    raise HeartbeatAuthError("1KOMMA5° afviste login")
                response.raise_for_status()
                data = await response.json()
        except ClientResponseError as err:
            raise HeartbeatApiError(f"Auth HTTP {err.status}") from err
        token = data.get("id_token")
        if not isinstance(token, str) or not token:
            raise HeartbeatApiError("Login gav ikke et id_token")
        self._token = token
        self._expires = datetime.now(timezone.utc) + timedelta(
            seconds=max(60, int(data.get("expires_in", 3600)) - 300)
        )

    async def _get(self, path: str) -> Any:
        if not self._token or datetime.now(timezone.utc) >= self._expires:
            await self._login()
        for attempt in range(2):
            try:
                async with self._session.get(
                    f"{API_URL}{path}",
                    headers={"Authorization": f"Bearer {self._token}"},
                    timeout=20,
                ) as response:
                    if response.status == 401 and attempt == 0:
                        self._token = None
                        await self._login()
                        continue
                    if response.status in (401, 403):
                        raise HeartbeatAuthError("Ingen adgang til data")
                    response.raise_for_status()
                    return await response.json()
            except ClientResponseError as err:
                raise HeartbeatApiError(f"gridX HTTP {err.status}") from err
        raise HeartbeatAuthError("Ingen adgang efter nyt login")

    async def systems(self) -> list[dict[str, Any]]:
        data = await self._get("/systems")
        items = data if isinstance(data, list) else data.get("items", [])
        if not isinstance(items, list):
            raise HeartbeatApiError("Uventet systemliste")
        return [item for item in items if isinstance(item, dict) and item.get("id")]

    async def decisions(self, system_id: str) -> dict[str, Any]:
        # The endpoint is listed in gridX's published API changelog. Do not
        # infer a 'normal' decision from an empty or malformed reply.
        data = await self._get(f"/systems/{system_id}/timeofuse/decisions")
        if not isinstance(data, dict) or not isinstance(data.get("decisions"), list):
            raise HeartbeatApiError("Uventet format for beslutninger")
        return data

    async def live(self, system_id: str) -> dict[str, Any]:
        """Return legacy gridX live telemetry without guessing missing fields."""
        data = await self._get(f"/systems/{system_id}/live")
        if not isinstance(data, dict):
            raise HeartbeatApiError("Uventet format for live-data")
        return data

    async def energy_management(self, system_id: str) -> bool:
        """Read the portal's Energy Management setting."""
        data = await self._get(f"/systems/{system_id}")
        ems = data.get("metadata", {}).get("energy", {}).get("ems", {}) if isinstance(data, dict) else {}
        enabled = ems.get("agreedEMSTerms") if isinstance(ems, dict) else None
        if not isinstance(enabled, bool):
            raise HeartbeatApiError("Energy Management-status mangler")
        return enabled

    async def set_energy_management(self, system_id: str, enabled: bool) -> bool:
        """Mirror the portal's PATCH and verify the persisted setting."""
        if not isinstance(enabled, bool):
            raise ValueError("enabled skal være bool")
        path = f"/systems/{system_id}"
        body = {"metadata": {"energy": {"ems": {"agreedEMSTerms": enabled}}}}
        for attempt in range(2):
            if not self._token or datetime.now(timezone.utc) >= self._expires:
                await self._login()
            try:
                async with self._session.patch(
                    f"{API_URL}{path}",
                    headers={"Authorization": f"Bearer {self._token}"},
                    json=body,
                    timeout=20,
                ) as response:
                    if response.status == 401 and attempt == 0:
                        self._token = None
                        continue
                    if response.status in (401, 403):
                        raise HeartbeatAuthError("Ingen adgang til at ændre Energy Management")
                    response.raise_for_status()
                    break
            except ClientResponseError as err:
                raise HeartbeatApiError(f"gridX PATCH HTTP {err.status}") from err
        else:
            raise HeartbeatAuthError("Kan ikke godkende PATCH")
        actual = await self.energy_management(system_id)
        if actual != enabled:
            raise HeartbeatApiError("Energy Management-ændring blev ikke bekræftet")
        return actual
