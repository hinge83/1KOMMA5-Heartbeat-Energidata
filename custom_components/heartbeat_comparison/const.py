"""Constants for the read-only Heartbeat comparison integration."""

from datetime import timedelta

DOMAIN = "heartbeat_comparison"
AUTH_URL = "https://gridx.eu.auth0.com/oauth/token"
API_URL = "https://api.gridx.de"
POLL_INTERVAL = timedelta(minutes=5)
CONF_SYSTEM_ID = "system_id"

# Public client ID used by the legacy 1KOMMA5° / gridX web portal.
AUTH_CLIENT_ID = "CrqUiQt6VhwOgWHqkX40CgYNlhABF3dB"