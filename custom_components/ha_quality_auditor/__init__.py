"""HA Quality Auditor — Integration entry point.

Responsibilities:
1. Register the static frontend path (async, non-blocking).
2. Register the custom sidebar panel.
3. Register the WebSocket command for manual audit triggers.
4. Create the DataUpdateCoordinator and load the sensor platform.
"""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    PANEL_COMPONENT_NAME,
    PANEL_FRONTEND_URL_PATH,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL,
    WS_TYPE_RUN_AUDIT,
)
from .coordinator import QualityAuditCoordinator

_LOGGER = logging.getLogger(__name__)

# Path to the frontend directory containing the JS panel
_FRONTEND_DIR = Path(__file__).parent / "frontend"

# Minimal config schema — no YAML configuration required
CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({})},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Quality Auditor integration.

    This runs when HA discovers the integration in custom_components/.
    """
    _LOGGER.info("Setting up %s integration", DOMAIN)

    # ── 1. Register static path for frontend assets (async, non-blocking) ──
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path=PANEL_FRONTEND_URL_PATH,
                path=str(_FRONTEND_DIR),
                cache_headers=True,
            )
        ]
    )

    # ── 2. Register sidebar panel ────────────────────────────────────────
    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_COMPONENT_NAME,
        frontend_url_path=PANEL_URL,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=False,
        module_url=f"{PANEL_FRONTEND_URL_PATH}/ha-quality-auditor-panel.js",
        embed_iframe=False,
    )

    # ── 3. Create coordinator & store in hass.data ───────────────────────
    coordinator = QualityAuditCoordinator(hass)
    hass.data[DOMAIN] = {"coordinator": coordinator}

    # Perform the first audit refresh
    await coordinator.async_config_entry_first_refresh()

    # ── 4. Register WebSocket command for manual re-scan ─────────────────
    from homeassistant.components.websocket_api import (
        async_register_command,
        async_response,
        websocket_command,
    )

    @websocket_command({vol.Required("type"): WS_TYPE_RUN_AUDIT})
    @async_response
    async def handle_run_audit(hass, connection, msg):
        """Handle a manual audit trigger from the frontend."""
        _LOGGER.info("Manual audit triggered via WebSocket")
        await coordinator.async_request_refresh()

        result = coordinator.data
        if result is not None:
            connection.send_result(msg["id"], result.to_dict())
        else:
            connection.send_result(msg["id"], {"error": "No audit data available"})

    async_register_command(hass, handle_run_audit)

    # ── 5. Load sensor platform via discovery ────────────────────────────
    hass.async_create_task(
        discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    _LOGGER.info("%s integration setup complete", DOMAIN)
    return True
