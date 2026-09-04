"""Frozen Sensor Detection.

Detects analog sensors whose float value has remained perfectly unchanged
(Δ = 0.0) across the configured rolling window, indicating a firmware lockup,
communication failure, or misconfigured polling interval.

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
    SEVERITY_MINOR,
)
from .models import Finding

_LOGGER = logging.getLogger(__name__)


class FrozenSensorRule:
    """Evaluate all analog sensors for frozen state over a rolling window."""

    async def evaluate(
        self, hass: HomeAssistant
    ) -> tuple[list[Finding], int]:
        """Return (findings, entities_checked)."""
        # Import here to avoid circular imports and ensure recorder is loaded
        from homeassistant.components.recorder.history import get_significant_states

        findings: list[Finding] = []
        checked = 0

        # Identify analog sensor entities (those with unit_of_measurement)
        sensor_entities = [
            state
            for state in hass.states.async_all("sensor")
            if state.attributes.get("unit_of_measurement") is not None
        ]

        if not sensor_entities:
            return findings, checked

        now = datetime.now(UTC)
        start_time = now - timedelta(hours=FROZEN_WINDOW_HOURS)

        # Fetch history for all target entities in one batch query
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

            # Parse numeric values from history states
            numeric_values: list[float] = []
            for state in states:
                try:
                    numeric_values.append(float(state.state))
                except (ValueError, TypeError):
                    # Skip non-numeric states (unavailable, unknown, etc.)
                    continue

            if len(numeric_values) < MIN_HISTORY_POINTS:
                # Insufficient data — possible data gap
                findings.append(
                    Finding(
                        entity_id=entity_id,
                        rule="Frozen Sensor",
                        category="Sensors",
                        severity=SEVERITY_MINOR,
                        description=(
                            f"Insufficient history data: only {len(numeric_values)} "
                            f"numeric data point(s) in the last {FROZEN_WINDOW_HOURS}h. "
                            "Possible recorder gap or newly added entity."
                        ),
                    )
                )
                continue

            # Check if all values are identical (Δ = 0.0)
            unique_values = set(numeric_values)
            if len(unique_values) == 1:
                frozen_value = numeric_values[0]
                findings.append(
                    Finding(
                        entity_id=entity_id,
                        rule="Frozen Sensor",
                        category="Sensors",
                        severity=SEVERITY_MAJOR,
                        description=(
                            f"Value frozen at {frozen_value} for >{FROZEN_WINDOW_HOURS}h "
                            f"({len(numeric_values)} samples). "
                            "Possible firmware lockup or communication failure."
                        ),
                    )
                )

        return findings, checked
