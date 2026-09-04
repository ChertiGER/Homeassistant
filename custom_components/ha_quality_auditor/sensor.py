"""Sensor platform for the HA Quality Auditor.

Exposes two diagnostic sensors:
- sensor.ha_quality_score  — Overall percentage quality score
- sensor.ha_audit_findings_count — Total number of audit findings
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import QualityAuditCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up sensor entities via platform discovery."""
    coordinator: QualityAuditCoordinator = hass.data[DOMAIN]["coordinator"]

    async_add_entities(
        [
            QualityScoreSensor(coordinator),
            FindingsCountSensor(coordinator),
        ],
        update_before_add=False,  # Coordinator already has data
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities from a config entry."""
    coordinator: QualityAuditCoordinator = hass.data[DOMAIN]["coordinator"]

    async_add_entities(
        [
            QualityScoreSensor(coordinator),
            FindingsCountSensor(coordinator),
        ],
        update_before_add=False,
    )


class QualityScoreSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the overall quality score as a percentage."""

    _attr_has_entity_name = True
    _attr_name = "HA Quality Score"
    _attr_unique_id = f"{DOMAIN}_quality_score"
    _attr_icon = "mdi:clipboard-check-outline"
    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator: QualityAuditCoordinator) -> None:
        """Initialise the score sensor."""
        super().__init__(coordinator)

    @property
    def native_value(self) -> float | None:
        """Return the quality score percentage."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.score

    @property
    def extra_state_attributes(self) -> dict:
        """Return grade, timestamp, and entities checked."""
        if self.coordinator.data is None:
            return {}
        data = self.coordinator.data
        return {
            "grade": data.grade,
            "last_audit": data.timestamp,
            "entities_checked": data.total_entities_checked,
        }


class FindingsCountSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the total number of audit findings."""

    _attr_has_entity_name = True
    _attr_name = "HA Audit Findings Count"
    _attr_unique_id = f"{DOMAIN}_findings_count"
    _attr_icon = "mdi:alert-circle-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: QualityAuditCoordinator) -> None:
        """Initialise the findings count sensor."""
        super().__init__(coordinator)

    @property
    def native_value(self) -> int | None:
        """Return the total findings count."""
        if self.coordinator.data is None:
            return None
        return len(self.coordinator.data.findings)

    @property
    def extra_state_attributes(self) -> dict:
        """Return breakdown by severity."""
        if self.coordinator.data is None:
            return {}
        findings = self.coordinator.data.findings
        return {
            "critical": sum(1 for f in findings if f.severity == "CRITICAL"),
            "major": sum(1 for f in findings if f.severity == "MAJOR"),
            "minor": sum(1 for f in findings if f.severity == "MINOR"),
            "last_audit": self.coordinator.data.timestamp,
        }
