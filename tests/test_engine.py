"""Tests for the HA Quality Auditor engine and audit rules.

All tests use mocked HA objects — no real Home Assistant instance required.
Stubs are set up in conftest.py.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock

import pytest

# Import modules under test (stubs already registered by conftest.py)
from ha_quality_auditor.audit.engine import AuditEngine, AuditResult, Finding
from ha_quality_auditor.audit.rules_frozen import FrozenSensorRule
from ha_quality_auditor.audit.rules_flaky import ChatterIndexRule
from ha_quality_auditor.audit.rules_automations import AutomationTriageRule

from conftest import MockHass, MockState, make_history_states, make_trace_summary

# Reference to trace stub module for setting per-test mock functions
_trace_mod = sys.modules["homeassistant.components.trace"]


# ── Frozen Sensor Detection ───────────────────────────────────────────


class TestFrozenSensorRule:
    """Tests for the frozen sensor detection rule."""

    @pytest.mark.asyncio
    async def test_frozen_sensor_detected(self):
        """Fluctuating environmental sensor with 12 identical values over 6h → MAJOR finding."""
        hass = MockHass([
            MockState(
                entity_id="sensor.outdoor_temp",
                state="18.5",
                attributes={
                    "unit_of_measurement": "°C",
                    "device_class": "temperature",
                    "friendly_name": "Outdoor Temperature",
                },
            ),
        ])

        frozen_history = {
            "sensor.outdoor_temp": make_history_states(
                "sensor.outdoor_temp",
                ["18.5"] * 12,
                interval_minutes=30,
            ),
        }
        hass.async_add_executor_job = AsyncMock(return_value=frozen_history)

        rule = FrozenSensorRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 1
        assert findings[0].severity == "MAJOR"
        assert findings[0].rule == "Frozen Sensor"
        assert findings[0].category == "Sensors"
        assert "18.5" in findings[0].description
        assert "Outdoor Temperature" in findings[0].description

    @pytest.mark.asyncio
    async def test_sensor_with_variance_passes(self):
        """Normal sensor with variance → no finding."""
        hass = MockHass([
            MockState(
                entity_id="sensor.indoor_temp",
                state="22.1",
                attributes={
                    "unit_of_measurement": "°C",
                    "device_class": "temperature",
                },
            ),
        ])

        normal_history = {
            "sensor.indoor_temp": make_history_states(
                "sensor.indoor_temp",
                ["21.0", "21.3", "21.8", "22.0", "22.1", "21.9", "22.0", "22.2"],
                interval_minutes=45,
            ),
        }
        hass.async_add_executor_job = AsyncMock(return_value=normal_history)

        rule = FrozenSensorRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_insufficient_history_not_flagged(self):
        """Sensor with only 1 data point (normal recorder behavior) → NO finding."""
        hass = MockHass([
            MockState(
                entity_id="sensor.living_room_temp",
                state="21.5",
                attributes={
                    "unit_of_measurement": "°C",
                    "device_class": "temperature",
                },
            ),
        ])

        sparse_history = {
            "sensor.living_room_temp": make_history_states(
                "sensor.living_room_temp",
                ["21.5"],
                interval_minutes=60,
            ),
        }
        hass.async_add_executor_job = AsyncMock(return_value=sparse_history)

        rule = FrozenSensorRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_battery_sensor_excluded(self):
        """Battery sensor staying at 100% → excluded from frozen check."""
        hass = MockHass([
            MockState(
                entity_id="sensor.door_lock_battery",
                state="100",
                attributes={
                    "unit_of_measurement": "%",
                    "device_class": "battery",
                },
            ),
        ])

        rule = FrozenSensorRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 0
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_energy_total_increasing_excluded(self):
        """Cumulative energy meter → excluded from frozen check."""
        hass = MockHass([
            MockState(
                entity_id="sensor.solar_energy_produced",
                state="1234.5",
                attributes={
                    "unit_of_measurement": "kWh",
                    "device_class": "energy",
                    "state_class": "total_increasing",
                },
            ),
        ])

        rule = FrozenSensorRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 0
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_setpoint_excluded(self):
        """Target setpoint entity → excluded by substring."""
        hass = MockHass([
            MockState(
                entity_id="sensor.thermostat_target_temperature",
                state="21.0",
                attributes={
                    "unit_of_measurement": "°C",
                    "device_class": "temperature",
                },
            ),
        ])

        rule = FrozenSensorRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 0
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_idle_zero_excluded(self):
        """Sensor resting at 0.0 → excluded from freeze alert."""
        hass = MockHass([
            MockState(
                entity_id="sensor.rain_rate",
                state="0.0",
                attributes={
                    "unit_of_measurement": "µg/m³",
                    "device_class": "pm25",
                },
            ),
        ])

        zero_history = {
            "sensor.rain_rate": make_history_states(
                "sensor.rain_rate",
                ["0.0"] * 10,
                interval_minutes=30,
            ),
        }
        hass.async_add_executor_job = AsyncMock(return_value=zero_history)

        rule = FrozenSensorRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 0


# ── State Chatter Index ───────────────────────────────────────────────


class TestChatterIndexRule:
    """Tests for the state chatter index rule."""

    @pytest.mark.asyncio
    async def test_chatter_index_exceeded(self):
        """25 transitions in 15 min → MAJOR finding."""
        hass = MockHass([
            MockState(entity_id="binary_sensor.door_sensor", state="off"),
        ])

        values = ["on" if i % 2 else "off" for i in range(26)]
        chatty_history = {
            "binary_sensor.door_sensor": make_history_states(
                "binary_sensor.door_sensor",
                values,
                interval_minutes=0.5,
            ),
        }
        hass.async_add_executor_job = AsyncMock(return_value=chatty_history)

        rule = ChatterIndexRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 1
        assert findings[0].severity == "MAJOR"
        assert findings[0].rule == "State Chatter"
        assert findings[0].category == "Signals"

    @pytest.mark.asyncio
    async def test_chatter_index_normal(self):
        """5 transitions in 15 min → no finding."""
        hass = MockHass([
            MockState(entity_id="binary_sensor.motion", state="off"),
        ])

        values = ["off", "on", "off", "on", "off", "on"]
        normal_history = {
            "binary_sensor.motion": make_history_states(
                "binary_sensor.motion",
                values,
                interval_minutes=2,
            ),
        }
        hass.async_add_executor_job = AsyncMock(return_value=normal_history)

        rule = ChatterIndexRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 0


# ── Automation Triage ───────────────────────────────────────────────


class TestAutomationTriageRule:
    """Tests for the automation reliability triage rule."""

    @pytest.mark.asyncio
    async def test_automation_error_critical(self):
        """Automation with error trace → CRITICAL finding."""
        hass = MockHass([
            MockState(
                entity_id="automation.broken_automation",
                state="on",
                attributes={"friendly_name": "Broken Automation"},
            ),
        ])

        traces = [
            make_trace_summary(state="error", error="TemplateError: undefined variable"),
        ]
        _trace_mod.async_list_traces = AsyncMock(return_value=traces)

        rule = AutomationTriageRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 1
        assert findings[0].severity == "CRITICAL"
        assert findings[0].rule == "Automation Error"
        assert findings[0].category == "Automations"
        assert "TemplateError" in findings[0].description

    @pytest.mark.asyncio
    async def test_automation_slow_major(self):
        """Automation with 3s duration → MAJOR finding."""
        hass = MockHass([
            MockState(
                entity_id="automation.slow_automation",
                state="on",
                attributes={"friendly_name": "Slow Automation"},
            ),
        ])

        traces = [
            make_trace_summary(state="stopped", duration=3.0),
        ]
        _trace_mod.async_list_traces = AsyncMock(return_value=traces)

        rule = AutomationTriageRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 1
        assert findings[0].severity == "MAJOR"
        assert findings[0].rule == "Automation Slow"
        assert findings[0].category == "Automations"

    @pytest.mark.asyncio
    async def test_automation_healthy(self):
        """All traces OK → no finding."""
        hass = MockHass([
            MockState(
                entity_id="automation.healthy_automation",
                state="on",
                attributes={"friendly_name": "Healthy Automation"},
            ),
        ])

        traces = [
            make_trace_summary(state="stopped", duration=0.1),
            make_trace_summary(state="stopped", duration=0.2),
        ]
        _trace_mod.async_list_traces = AsyncMock(return_value=traces)

        rule = AutomationTriageRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_automation_slow_calculated_from_timestamps(self):
        """Automation with duration calculated from start/finish timestamps."""
        hass = MockHass([
            MockState(
                entity_id="automation.timestamp_slow",
                state="on",
                attributes={"friendly_name": "Timestamp Slow Automation"},
            ),
        ])

        traces = [
            {
                "state": "stopped",
                "timestamp": {
                    "start": "2026-09-05T10:00:00.000000+00:00",
                    "finish": "2026-09-05T10:00:04.500000+00:00",
                },
            }
        ]
        _trace_mod.async_list_traces = AsyncMock(return_value=traces)

        rule = AutomationTriageRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 1
        assert findings[0].severity == "MAJOR"
        assert findings[0].rule == "Automation Slow"
        assert "4500ms" in findings[0].description

    @pytest.mark.asyncio
    async def test_automation_disabled_skipped(self):
        """Disabled automation (state == 'off') → skipped from error checks."""
        hass = MockHass([
            MockState(
                entity_id="automation.disabled_with_error",
                state="off",
                attributes={"friendly_name": "Disabled Automation"},
            ),
        ])

        traces = [
            make_trace_summary(state="error", error="Broken"),
        ]
        _trace_mod.async_list_traces = AsyncMock(return_value=traces)

        rule = AutomationTriageRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 0

    @pytest.mark.asyncio
    async def test_automation_lookup_by_attribute_id(self):
        """UI automations with id attribute → trace looked up via attributes['id']."""
        hass = MockHass([
            MockState(
                entity_id="automation.living_room_lights",
                state="on",
                attributes={"id": "1715869129139", "friendly_name": "Living Room Lights"},
            ),
        ])

        async def mock_list(hass, domain, key):
            if key == "1715869129139":
                return [make_trace_summary(state="error", error="ServiceNotFound")]
            return []

        _trace_mod.async_list_traces = AsyncMock(side_effect=mock_list)

        rule = AutomationTriageRule()
        findings, checked = await rule.evaluate(hass)

        assert checked == 1
        assert len(findings) == 1
        assert "ServiceNotFound" in findings[0].description


# ── Quality Score Calculation ───────────────────────────────────────


class TestScoreCalculation:
    """Tests for the quality scoring algorithm."""

    def test_score_grade_a(self):
        """No findings → 100% / Grade A."""
        score, grade = AuditEngine._calculate_score([], total_checked=50)
        assert score == 100.0
        assert grade == "A"

    def test_score_grade_b(self):
        """Mixed findings → Grade B range."""
        findings = [
            Finding("s.1", "Frozen", "Sensors", "MAJOR", "frozen"),
            Finding("s.2", "Chatter", "Signals", "MINOR", "chatty"),
        ]
        score, grade = AuditEngine._calculate_score(findings, total_checked=50)
        assert score == 86.0
        assert grade == "B"

    def test_score_grade_c(self):
        """Many critical findings → Grade C."""
        findings = [
            Finding(f"a.{i}", "Error", "Automations", "CRITICAL", "error")
            for i in range(5)
        ]
        score, grade = AuditEngine._calculate_score(findings, total_checked=10)
        assert score == 0.0
        assert grade == "C"

    def test_empty_system(self):
        """No entities → 100% / Grade A (nothing to fail)."""
        score, grade = AuditEngine._calculate_score([], total_checked=0)
        assert score == 100.0
        assert grade == "A"
