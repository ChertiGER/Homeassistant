"""Frozen Sensor Detection.

Detects fluctuating environmental analog sensors whose float value has remained
perfectly unchanged (Δ = 0.0) across the rolling window despite active reporting,
indicating firmware lockup, stuck hardware, or misconfigured polling.

Strictly excludes:
- Batteries (which naturally remain at a fixed percentage for long periods)
- Cumulative counters / energy meters (totals that only increase with consumption)
- Setpoints, targets, thresholds, limits, and configuration offsets
- Idle 0.0 readings (e.g. 0 W power, 0 A current, 0 mm rain)
- Entities with insufficient samples (normal recorder behavior when state is unchanged)

Strictly read-only: queries Recorder history, never modifies state.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant

from ..const import (
    FROZEN_WINDOW_HOURS,
    MIN_HISTORY_POINTS,
    SEVERITY_MAJOR,
)
from .models import Finding

_LOGGER = logging.getLogger(__name__)

# Environmental device classes that naturally fluctuate over a 6h period
_FREEZABLE_DEVICE_CLASSES = {
    "temperature",
    "humidity",
    "atmospheric_pressure",
    "pressure",
    "illuminance",
    "carbon_dioxide",
    "carbon_monoxide",
    "volatile_organic_compounds",
    "volatile_organic_compounds_parts",
    "pm1",
    "pm25",
    "pm10",
    "aqi",
    "sound_pressure",
}

# Physical units corresponding to environmental/fluctuating measurements
_FREEZABLE_UNITS = {
    "°C",
    "°F",
    "K",
    "hPa",
    "mbar",
    "bar",
    "lx",
    "lm",
    "ppm",
    "ppb",
    "µg/m³",
    "ug/m3",
    "dB",
    "dBA",
}

# Classes that must NEVER be flagged as frozen (counters, batteries, static attributes)
_EXCLUDED_DEVICE_CLASSES = {
    "battery",
    "energy",
    "gas",
    "water",
    "monetary",
    "duration",
    "distance",
    "date",
    "timestamp",
    "volume",
    "volume_storage",
    "data_rate",
    "data_size",
    "power_factor",
}

_EXCLUDED_STATE_CLASSES = {
    "total",
    "total_increasing",
}

_EXCLUDED_ENTITY_SUBSTRINGS = (
    "battery",
    "_target",
    "_setpoint",
    "_threshold",
    "_limit",
    "_preset",
    "_setting",
    "_offset",
    "_min",
    "_max",
)


class FrozenSensorRule:
    """Evaluate fluctuating environmental sensors for frozen state over a rolling window."""

    async def evaluate(
        self, hass: HomeAssistant
    ) -> tuple[list[Finding], int]:
        """Return (findings, entities_checked)."""
        from homeassistant.components.recorder.history import get_significant_states

        findings: list[Finding] = []
        checked = 0

        # Filter strictly for fluctuating environmental analog sensors
        sensor_entities = []
        for state in hass.states.async_all("sensor"):
            unit = state.attributes.get("unit_of_measurement")
            if not unit:
                continue

            device_class = state.attributes.get("device_class", "")
            state_class = state.attributes.get("state_class", "")
            entity_id_lower = state.entity_id.lower()

            if device_class in _EXCLUDED_DEVICE_CLASSES:
                continue
            if state_class in _EXCLUDED_STATE_CLASSES:
                continue
            if any(sub in entity_id_lower for sub in _EXCLUDED_ENTITY_SUBSTRINGS):
                continue

            # Check if this is an environmental/fluctuating sensor
            if device_class in _FREEZABLE_DEVICE_CLASSES or unit in _FREEZABLE_UNITS:
                # Must be a valid numeric current state (not unavailable/unknown)
                try:
                    float(state.state)
                except (ValueError, TypeError):
                    continue
                sensor_entities.append(state)

        if not sensor_entities:
            return findings, checked

        now = datetime.now(UTC)
        start_time = now - timedelta(hours=FROZEN_WINDOW_HOURS)
        entity_ids = [s.entity_id for s in sensor_entities]

        try:
            history = await hass.async_add_executor_job(
                get_significant_states,
                hass,
                start_time,
                now,
                entity_ids,
            )
        except Exception:
            _LOGGER.exception("Failed to query recorder history for frozen check")
            return findings, checked

        for entity_id in entity_ids:
            states = history.get(entity_id, [])
            checked += 1

            numeric_values: list[float] = []
            for state in states:
                try:
                    numeric_values.append(float(state.state))
                except (ValueError, TypeError):
                    continue

            # In Home Assistant, recorder only records state transitions.
            # Few or no records in 6h is completely normal if value did not change,
            # so we NEVER flag insufficient data as a defect.
            if len(numeric_values) < MIN_HISTORY_POINTS:
                continue

            # If all values are 0.0 (e.g. idle device or rain gauge with no rain), ignore
            if all(v == 0.0 for v in numeric_values):
                continue

            # Check if all values are bit-for-bit identical across multiple samples
            unique_values = set(numeric_values)
            if len(unique_values) == 1:
                frozen_value = numeric_values[0]
                state_obj = hass.states.get(entity_id)
                friendly_name = (
                    state_obj.attributes.get("friendly_name", entity_id)
                    if state_obj
                    else entity_id
                )
                unit_str = (
                    f" {state_obj.attributes.get('unit_of_measurement', '')}"
                    if state_obj and state_obj.attributes.get("unit_of_measurement")
                    else ""
                )
                findings.append(
                    Finding(
                        entity_id=entity_id,
                        rule="Frozen Sensor",
                        category="Sensors",
                        severity=SEVERITY_MAJOR,
                        description=(
                            f"Sensor '{friendly_name}' value frozen at {frozen_value}{unit_str} "
                            f"for >{FROZEN_WINDOW_HOURS}h ({len(numeric_values)} consecutive identical updates). "
                            "Possible firmware lockup or communication failure."
                        ),
                    )
                )

        return findings, checked

