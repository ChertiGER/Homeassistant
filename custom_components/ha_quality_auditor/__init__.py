"""HA Quality Auditor — Integration entry point.

Responsibilities:
1. Register the static frontend path (async, non-blocking, once).
2. Register the custom sidebar panel safely (idempotent, avoid Overwriting panel ValueError).
3. Create the DataUpdateCoordinator and forward entry setup to the sensor platform.
4. Register the WebSocket command for manual audit triggers (idempotent).
"""

from __future__ import annotations

import logging
from pathlib import Path

import voluptuous as vol

from homeassistant.components import panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({})},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Quality Auditor integration via YAML (no-op in modern config-flow integrations)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Quality Auditor from a config entry (UI)."""
    _LOGGER.info("Setting up %s integration from config entry", DOMAIN)

    # ── 1. Register static path for frontend assets (guarded against duplicate calls) ──
    if not hass.data.get(f"{DOMAIN}_static_registered"):
        try:
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        url_path=PANEL_FRONTEND_URL_PATH,
                        path=str(_FRONTEND_DIR),
                        cache_headers=True,
                    )
                ]
            )
            hass.data[f"{DOMAIN}_static_registered"] = True
        except Exception as err:
            _LOGGER.debug("Static path registration: %s", err)

    # ── 2. Register sidebar panel safely (avoid ValueError: Overwriting panel) ─────────
    panels = hass.data.get("frontend_panels", {})
    if PANEL_URL not in panels:
        try:
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
            _LOGGER.info("Registered panel %s", PANEL_URL)
        except ValueError as err:
            _LOGGER.warning("Panel %s already registered: %s", PANEL_URL, err)
        except Exception as err:
            _LOGGER.error("Failed to register panel %s: %s", PANEL_URL, err)

    # ── 3. Create coordinator & store in hass.data ───────────────────────────────────────
    coordinator = QualityAuditCoordinator(hass, config_entry=entry)
    hass.data[DOMAIN] = {"coordinator": coordinator}

    # Perform initial audit refresh
    await coordinator.async_config_entry_first_refresh()

    # ── 4. Forward entry setup to sensor platform ────────────────────────────────────────
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])

    # ── 5. Register WebSocket command for manual re-scan (idempotent) ────────────────────
    from homeassistant.components.websocket_api import (
        async_register_command,
        async_response,
        websocket_command,
    )

    ws_data = hass.data.get("websocket_api")
    ws_handlers = getattr(ws_data, "handlers", {}) if ws_data else {}
    if WS_TYPE_RUN_AUDIT not in ws_handlers:
        @websocket_command({vol.Required("type"): WS_TYPE_RUN_AUDIT})
        @async_response
        async def handle_run_audit(hass: HomeAssistant, connection, msg):
            """Handle a manual audit trigger from the frontend."""
            _LOGGER.info("Manual audit triggered via WebSocket")
            domain_data = hass.data.get(DOMAIN, {})
            coord = domain_data.get("coordinator")
            if coord is not None:
                await coord.async_request_refresh()
                result = coord.data
                if result is not None:
                    connection.send_result(msg["id"], result.to_dict())
                    return
            connection.send_result(msg["id"], {"error": "No audit coordinator or data available"})

        try:
            async_register_command(hass, handle_run_audit)
        except Exception as err:
            _LOGGER.debug("WebSocket command %s registration: %s", WS_TYPE_RUN_AUDIT, err)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading %s config entry", DOMAIN)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        try:
            from homeassistant.components.frontend import async_remove_panel
            async_remove_panel(hass, PANEL_URL)
        except Exception as err:
            _LOGGER.debug("Could not remove panel %s: %s", PANEL_URL, err)
        if DOMAIN in hass.data:
            hass.data.pop(DOMAIN, None)
    return unload_ok
