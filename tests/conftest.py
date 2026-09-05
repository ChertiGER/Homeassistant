"""Shared pytest fixtures and HA module stubs for Quality Auditor tests.

This conftest runs BEFORE any test module is collected, ensuring all
homeassistant stub modules are registered exactly once in sys.modules.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest


# ═══════════════════════════════════════════════════════════════════════
# HA Module Stubs (set once, shared by all test files)
# ═══════════════════════════════════════════════════════════════════════

# Only register if not already present (first conftest wins)
if "homeassistant" not in sys.modules:

    _ha_core = ModuleType("homeassistant.core")
    _ha_core.HomeAssistant = MagicMock
    _ha_core.callback = lambda f: f

    class _StubDataUpdateCoordinator:
        def __init__(self, *a, **kw):
            self.data = None
            self.hass = a[0] if a else None

        async def async_config_entry_first_refresh(self):
            pass

        async def async_refresh(self):
            pass

        async def async_request_refresh(self):
            pass

        def __class_getitem__(cls, item):
            return cls

    class _StubCoordinatorEntity:
        def __init__(self, coordinator):
            self.coordinator = coordinator

    _ha_helpers_uc = ModuleType("homeassistant.helpers.update_coordinator")
    _ha_helpers_uc.DataUpdateCoordinator = _StubDataUpdateCoordinator
    _ha_helpers_uc.CoordinatorEntity = _StubCoordinatorEntity

    _panel_custom = ModuleType("homeassistant.components.panel_custom")
    _panel_custom.async_register_panel = AsyncMock()

    _http_mod = ModuleType("homeassistant.components.http")
    _http_mod.StaticPathConfig = MagicMock

    _ws_mod = ModuleType("homeassistant.components.websocket_api")
    _ws_mod.async_register_command = MagicMock()
    _ws_mod.async_response = lambda f: f
    _ws_mod.websocket_command = lambda schema: (lambda f: f)

    _discovery_mod = ModuleType("homeassistant.helpers.discovery")
    _discovery_mod.async_load_platform = AsyncMock()

    _typing_mod = ModuleType("homeassistant.helpers.typing")
    _typing_mod.ConfigType = dict
    _typing_mod.DiscoveryInfoType = dict

    _sensor_mod = ModuleType("homeassistant.components.sensor")
    _sensor_mod.SensorEntity = type("SensorEntity", (), {})
    _sensor_mod.SensorStateClass = type(
        "SensorStateClass", (), {"MEASUREMENT": "measurement"}
    )

    _entity_platform = ModuleType("homeassistant.helpers.entity_platform")
    _entity_platform.AddEntitiesCallback = MagicMock

    _recorder_history = ModuleType("homeassistant.components.recorder.history")
    _recorder_history.get_significant_states = MagicMock()

    _trace_mod = ModuleType("homeassistant.components.trace")
    _trace_mod.async_list_traces = AsyncMock()

    class _ConfigFlow:
        VERSION = 1

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

        async def async_set_unique_id(self, unique_id):
            pass

        def _abort_if_unique_id_configured(self):
            pass

        def async_create_entry(self, title, data):
            return {"type": "create_entry", "title": title, "data": data}

        def async_show_form(self, step_id, data_schema=None, errors=None):
            return {"type": "form", "step_id": step_id}

    _config_entries = ModuleType("homeassistant.config_entries")
    _config_entries.ConfigEntry = MagicMock
    _config_entries.ConfigFlow = _ConfigFlow

    _data_entry_flow = ModuleType("homeassistant.data_entry_flow")
    _data_entry_flow.FlowResult = dict

    _ha_root = ModuleType("homeassistant")
    _ha_root.__path__ = []
    _ha_helpers = ModuleType("homeassistant.helpers")
    _ha_helpers.__path__ = []
    _ha_components = ModuleType("homeassistant.components")
    _ha_components.__path__ = []
    _ha_recorder = ModuleType("homeassistant.components.recorder")
    _ha_recorder.__path__ = []

    _frontend_mod = ModuleType("homeassistant.components.frontend")
    _frontend_mod.async_remove_panel = MagicMock()

    for mod_name, mod in [
        ("homeassistant", _ha_root),
        ("homeassistant.core", _ha_core),
        ("homeassistant.config_entries", _config_entries),
        ("homeassistant.data_entry_flow", _data_entry_flow),
        ("homeassistant.helpers", _ha_helpers),
        ("homeassistant.helpers.update_coordinator", _ha_helpers_uc),
        ("homeassistant.helpers.discovery", _discovery_mod),
        ("homeassistant.helpers.typing", _typing_mod),
        ("homeassistant.helpers.entity_platform", _entity_platform),
        ("homeassistant.components", _ha_components),
        ("homeassistant.components.panel_custom", _panel_custom),
        ("homeassistant.components.frontend", _frontend_mod),
        ("homeassistant.components.http", _http_mod),
        ("homeassistant.components.websocket_api", _ws_mod),
        ("homeassistant.components.sensor", _sensor_mod),
        ("homeassistant.components.recorder", _ha_recorder),
        ("homeassistant.components.recorder.history", _recorder_history),
        ("homeassistant.components.trace", _trace_mod),
    ]:
        sys.modules[mod_name] = mod

    # Add custom_components to path
    sys.path.insert(
        0,
        str(__import__("pathlib").Path(__file__).resolve().parent.parent / "custom_components"),
    )


# ═══════════════════════════════════════════════════════════════════════
# Mock State Object
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class MockState:
    """Minimal mock of homeassistant.core.State."""

    entity_id: str
    state: str
    attributes: dict = None
    last_changed: datetime = None

    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        if self.last_changed is None:
            self.last_changed = datetime.now(UTC)


# ═══════════════════════════════════════════════════════════════════════
# Mock HomeAssistant
# ═══════════════════════════════════════════════════════════════════════


class MockStates:
    """Mock of hass.states with async_all() support."""

    def __init__(self, state_list: list[MockState] | None = None):
        self._states = {s.entity_id: s for s in (state_list or [])}

    def async_all(self, domain: str | None = None) -> list[MockState]:
        if domain is None:
            return list(self._states.values())
        return [
            s for s in self._states.values()
            if s.entity_id.startswith(f"{domain}.")
        ]

    def get(self, entity_id: str) -> MockState | None:
        return self._states.get(entity_id)


@dataclass
class MockConfigEntry:
    """Minimal mock of homeassistant.config_entries.ConfigEntry."""

    entry_id: str
    domain: str
    title: str = ""
    state: str = "loaded"
    disabled_by: str | None = None


class MockConfigEntries:
    """Mock of hass.config_entries with async_entries() support."""

    def __init__(self, entries: list[MockConfigEntry] | None = None):
        self._entries = entries or []

    def async_entries(self, domain: str | None = None) -> list[MockConfigEntry]:
        if domain is None:
            return list(self._entries)
        return [e for e in self._entries if e.domain == domain]


class MockHass:
    """Minimal mock of HomeAssistant core object."""

    def __init__(
        self,
        state_list: list[MockState] | None = None,
        config_entries: list[MockConfigEntry] | None = None,
    ):
        self.states = MockStates(state_list)
        self.config_entries = MockConfigEntries(config_entries)
        self.async_add_executor_job = AsyncMock()
        self.data = {}



# ═══════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════


def make_history_states(
    entity_id: str,
    values: list[str],
    interval_minutes: float = 30,
    start: datetime | None = None,
) -> list[MockState]:
    """Generate a list of MockState entries simulating recorder history."""
    if start is None:
        start = datetime.now(UTC) - timedelta(minutes=interval_minutes * len(values))

    return [
        MockState(
            entity_id=entity_id,
            state=val,
            last_changed=start + timedelta(minutes=i * interval_minutes),
        )
        for i, val in enumerate(values)
    ]


def make_trace_summary(
    state: str = "stopped",
    error: str | None = None,
    duration: float = 0.1,
) -> dict:
    """Create a mock automation trace summary."""
    summary = {
        "state": state,
        "duration": duration,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if state == "error" and error:
        summary["error"] = error
    if error and state != "error":
        summary["result"] = {"error": error}
    return summary


# ═══════════════════════════════════════════════════════════════════════
# Pytest Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_hass():
    """Return a bare MockHass with no states."""
    return MockHass()
