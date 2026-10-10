# Heartbeat Comparison (legacy GridX)

Custom Home Assistant integration for read-only 1KOMMA5°/GridX Heartbeat battery optimization decisions.

## Installation with HACS

1. In HACS, add this repository as a custom **Integration** repository.
2. Download the integration and restart Home Assistant.
3. Add **Heartbeat beslutninger (sammenligning)** under Settings → Devices & services.

**Important:** This project uses the legacy GridX Auth0 password-realm login, not the newer 1KOMMA5° OAuth2 PKCE login. It is intended for accounts that support the legacy API.

The integration retrieves battery optimization decisions only. No battery control commands are sent. Credentials are stored by Home Assistant's config entry and must never be committed into Git.

## Development

The `main` branch contains the existing v0.1.2 implementation, reorganized for HACS without changes to authentication, polling, or sensor logic. Test modifications in a separate Home Assistant environment before deploying to production.
