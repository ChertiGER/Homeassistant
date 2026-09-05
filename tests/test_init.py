"""Tests for the Quality Auditor integration setup (__init__.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ha_quality_auditor import async_setup, async_setup_entry, async_unload_entry
from custom_components.ha_quality_auditor.config_flow import QualityAuditorConfigFlow
from custom_components.ha_quality_auditor.const import (
    DOMAIN,
    PANEL_COMPONENT_NAME,
    PANEL_FRONTEND_URL_PATH,
    PANEL_URL,
)


@pytest.fixture
def setup_hass(mock_hass):
    """Extend mock_hass with http, tasks, and coordinator methods."""
    mock_hass.http = MagicMock()
    mock_hass.http.async_register_static_paths = AsyncMock()
    mock_hass.config_entries = MagicMock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock()
    mock_hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return mock_hass


@pytest.mark.asyncio
async def test_async_setup_returns_true(setup_hass):
    """Test async_setup returns True for config-flow integrations."""
    result = await async_setup(setup_hass, {DOMAIN: {}})
    assert result is True


@pytest.mark.asyncio
async def test_async_setup_entry_success(setup_hass):
    """Test successful config entry setup."""
    entry = MagicMock()

    with patch(
        "custom_components.ha_quality_auditor.coordinator.QualityAuditCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ), patch(
        "homeassistant.components.panel_custom.async_register_panel",
        new_callable=AsyncMock,
    ) as mock_panel, patch(
        "homeassistant.components.websocket_api.async_register_command"
    ) as mock_ws_reg:

        result = await async_setup_entry(setup_hass, entry)
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

        # 4. Sensor platform forwarded
        setup_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
            entry, ["sensor"]
        )

        # 5. WebSocket command registered
        mock_ws_reg.assert_called_once()

        # 6. Unload entry
        unload_result = await async_unload_entry(setup_hass, entry)
        assert unload_result is True
        assert DOMAIN not in setup_hass.data

    # Test config flow steps
    flow = QualityAuditorConfigFlow()
    flow.hass = setup_hass

    form_result = await flow.async_step_user(user_input=None)
    assert form_result["type"] == "form"
    assert form_result["step_id"] == "user"

    create_result = await flow.async_step_user(user_input={})
    assert create_result["type"] == "create_entry"
    assert create_result["title"] == "Quality Auditor"


@pytest.mark.asyncio
async def test_async_setup_entry_handles_existing_panel_gracefully(setup_hass):
    """Test setup succeeds even if panel is already registered or raises ValueError."""
    entry = MagicMock()

    # Case 1: Panel already in frontend_panels
    setup_hass.data["frontend_panels"] = {PANEL_URL: {}}

    with patch(
        "custom_components.ha_quality_auditor.coordinator.QualityAuditCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ), patch(
        "homeassistant.components.panel_custom.async_register_panel",
        new_callable=AsyncMock,
    ) as mock_panel:
        result = await async_setup_entry(setup_hass, entry)
        assert result is True
        # async_register_panel should not even be called
        mock_panel.assert_not_called()

    # Case 2: Panel not in frontend_panels dict but async_register_panel raises ValueError
    setup_hass.data.pop("frontend_panels", None)
    setup_hass.data.pop(DOMAIN, None)

    with patch(
        "custom_components.ha_quality_auditor.coordinator.QualityAuditCoordinator.async_config_entry_first_refresh",
        new_callable=AsyncMock,
    ), patch(
        "homeassistant.components.panel_custom.async_register_panel",
        side_effect=ValueError(f"Overwriting panel {PANEL_URL}"),
    ):
        result = await async_setup_entry(setup_hass, entry)
        assert result is True
        assert DOMAIN in setup_hass.data
