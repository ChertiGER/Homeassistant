"""Tests for the Quality Auditor integration setup (__init__.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ha_quality_auditor import async_setup
from custom_components.ha_quality_auditor.const import (
    DOMAIN,
    PANEL_COMPONENT_NAME,
    PANEL_FRONTEND_URL_PATH,
    PANEL_URL,
    WS_TYPE_RUN_AUDIT,
)


@pytest.fixture
def setup_hass(mock_hass):
    """Extend mock_hass with http, tasks, and coordinator methods."""
    mock_hass.http = MagicMock()
    mock_hass.http.async_register_static_paths = AsyncMock()
    def _create_task(coro):
        coro.close()
        return MagicMock()

    mock_hass.async_create_task = MagicMock(side_effect=_create_task)
    return mock_hass


@pytest.mark.asyncio
async def test_async_setup_success(setup_hass):
    """Test successful integration setup."""
    with patch(
        "custom_components.ha_quality_auditor.coordinator.QualityAuditCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ), patch(
        "homeassistant.components.panel_custom.async_register_panel",
        new_callable=AsyncMock,
    ) as mock_panel, patch(
        "homeassistant.components.websocket_api.async_register_command"
    ) as mock_ws_reg, patch(
        "homeassistant.helpers.discovery.async_load_platform",
        new_callable=AsyncMock,
    ) as mock_discovery:

        result = await async_setup(setup_hass, {DOMAIN: {}})

        assert result is True

        # 1. Static paths registered
        setup_hass.http.async_register_static_paths.assert_called_once()
        static_configs = setup_hass.http.async_register_static_paths.call_args[0][0]
        assert len(static_configs) == 1
        assert static_configs[0].url_path == PANEL_FRONTEND_URL_PATH

        # 2. Panel registered
        mock_panel.assert_called_once()
        _, kwargs = mock_panel.call_args
        assert kwargs["webcomponent_name"] == PANEL_COMPONENT_NAME
        assert kwargs["frontend_url_path"] == PANEL_URL
        assert kwargs["module_url"] == f"{PANEL_FRONTEND_URL_PATH}/ha-quality-auditor-panel.js"
        assert kwargs["require_admin"] is False

        # 3. Coordinator stored in hass.data
        assert DOMAIN in setup_hass.data
        assert "coordinator" in setup_hass.data[DOMAIN]

        # 4. WebSocket command registered
        mock_ws_reg.assert_called_once()

        # 5. Sensor platform loaded
        mock_discovery.assert_called_once_with(
            setup_hass, "sensor", DOMAIN, {}, {DOMAIN: {}}
        )
