"""Tests for the HA Quality Auditor sensor entities.

Verifies that CoordinatorEntity-based sensors correctly reflect
the coordinator's audit result data. Stubs are set up in conftest.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Import modules under test (stubs already registered by conftest.py)
from custom_components.ha_quality_auditor.audit.engine import AuditResult, Finding
from custom_components.ha_quality_auditor.sensor import QualityScoreSensor, FindingsCountSensor


# ── Mock Coordinator ─────────────────────────────────────────────────


class MockCoordinator:
    """Minimal coordinator mock with controllable data."""

    def __init__(self, data: AuditResult | None = None):
        self.data = data


# ═══════════════════════════════════════════════════════════════════════
# Sensor Tests
# ═══════════════════════════════════════════════════════════════════════


class TestQualityScoreSensor:
    """Tests for the quality score sensor entity."""

    def test_quality_score_sensor_state(self):
        """Score sensor reflects coordinator data."""
        result = AuditResult(
            score=87.5,
            grade="B",
            findings=[
                Finding("sensor.x", "Frozen", "Sensors", "MAJOR", "frozen"),
            ],
            total_entities_checked=40,
            timestamp="2026-09-04T12:00:00+00:00",
        )
        coordinator = MockCoordinator(data=result)
        sensor = QualityScoreSensor(coordinator)

        assert sensor.native_value == 87.5

    def test_quality_score_none_when_no_data(self):
        """Score sensor returns None when coordinator has no data."""
        coordinator = MockCoordinator(data=None)
        sensor = QualityScoreSensor(coordinator)

        assert sensor.native_value is None

    def test_quality_score_attributes(self):
        """Score sensor exposes grade, timestamp, and entity count."""
        result = AuditResult(
            score=95.0,
            grade="A",
            findings=[],
            total_entities_checked=100,
            timestamp="2026-09-04T10:00:00+00:00",
        )
        coordinator = MockCoordinator(data=result)
        sensor = QualityScoreSensor(coordinator)

        attrs = sensor.extra_state_attributes
        assert attrs["grade"] == "A"
        assert attrs["entities_checked"] == 100
        assert attrs["last_audit"] == "2026-09-04T10:00:00+00:00"


class TestFindingsCountSensor:
    """Tests for the findings count sensor entity."""

    def test_findings_count_sensor_state(self):
        """Count sensor reflects finding count."""
        result = AuditResult(
            score=80.0,
            grade="B",
            findings=[
                Finding("sensor.a", "Frozen", "Sensors", "MAJOR", "frozen"),
                Finding("auto.b", "Error", "Automations", "CRITICAL", "error"),
                Finding("binary.c", "Chatter", "Signals", "MINOR", "chatty"),
            ],
            total_entities_checked=50,
            timestamp="2026-09-04T12:00:00+00:00",
        )
        coordinator = MockCoordinator(data=result)
        sensor = FindingsCountSensor(coordinator)

        assert sensor.native_value == 3

    def test_findings_count_none_when_no_data(self):
        """Count sensor returns None when coordinator has no data."""
        coordinator = MockCoordinator(data=None)
        sensor = FindingsCountSensor(coordinator)

        assert sensor.native_value is None

    def test_findings_severity_breakdown(self):
        """Count sensor exposes severity breakdown in attributes."""
        result = AuditResult(
            score=70.0,
            grade="B",
            findings=[
                Finding("a.1", "Error", "Automations", "CRITICAL", "err"),
                Finding("a.2", "Error", "Automations", "CRITICAL", "err"),
                Finding("s.1", "Frozen", "Sensors", "MAJOR", "frozen"),
                Finding("b.1", "Chatter", "Signals", "MINOR", "chat"),
            ],
            total_entities_checked=30,
            timestamp="2026-09-04T11:00:00+00:00",
        )
        coordinator = MockCoordinator(data=result)
        sensor = FindingsCountSensor(coordinator)

        attrs = sensor.extra_state_attributes
        assert attrs["critical"] == 2
        assert attrs["major"] == 1
        assert attrs["minor"] == 1


@pytest.mark.asyncio
async def test_async_setup_entry_sensors():
    """Test async_setup_entry registers both sensors."""
    from custom_components.ha_quality_auditor.const import DOMAIN
    from custom_components.ha_quality_auditor.sensor import async_setup_entry

    hass = MagicMock()
    coordinator = MockCoordinator()
    hass.data = {DOMAIN: {"coordinator": coordinator}}

    added_entities = []
    def _add_entities(entities, update_before_add=False):
        added_entities.extend(entities)

    await async_setup_entry(hass, MagicMock(), _add_entities)

    assert len(added_entities) == 2
    assert isinstance(added_entities[0], QualityScoreSensor)
    assert isinstance(added_entities[1], FindingsCountSensor)

