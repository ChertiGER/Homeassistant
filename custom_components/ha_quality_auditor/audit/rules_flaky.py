"""Flakiness & State-Chatter Index (FCI).

Detects binary sensors and signal telemetry entities that exhibit excessive
state transitions within a short window, indicating bouncing contacts
(magnetic reed flutter), packet-drop loops, or WiFi/Zigbee interference.

Strictly read-only: queries Recorder history, never modifies state.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from homeassistant.core import HomeAssistant

from ..const import (
    CHATTER_THRESHOLD,
    CHATTER_WINDOW_MINUTES,
    SEVERITY_MAJOR,
)
from .models import Finding

_LOGGER = logging.getLogger(__name__)

# Platforms known for wireless signal telemetry
_SIGNAL_PLATFORMS = {"zha", "mqtt", "esphome"}


class ChatterIndexRule:
    """Evaluate binary sensors and signal entities for excessive state chatter."""

    async def evaluate(
        self, hass: HomeAssistant
    ) -> tuple[list[Finding], int]:
        """Return (findings, entities_checked)."""
        from homeassistant.components.recorder.history import get_significant_states

        findings: list[Finding] = []
        checked = 0

        # Collect target entity IDs:
        # 1) All binary_sensor entities
        # 2) Sensor entities from signal-heavy platforms (zha, mqtt, esphome)
        target_entity_ids: list[str] = []

        for state in hass.states.async_all("binary_sensor"):
            target_entity_ids.append(state.entity_id)

        # Also check sensor entities from signal-heavy integrations
        for state in hass.states.async_all("sensor"):
            platform = state.attributes.get("platform", "")
            # Entity registry stores the platform; fallback to checking entity_id prefix
            if platform in _SIGNAL_PLATFORMS or any(
                state.entity_id.startswith(f"sensor.{p}_")
                for p in _SIGNAL_PLATFORMS
            ):
                target_entity_ids.append(state.entity_id)

        if not target_entity_ids:
            return findings, checked

        now = datetime.now(UTC)
        start_time = now - timedelta(minutes=CHATTER_WINDOW_MINUTES)

        try:
            history = await hass.async_add_executor_job(
                get_significant_states,
                hass,
                start_time,
                now,
                target_entity_ids,
            )
        except Exception:
            _LOGGER.exception("Failed to query recorder history for chatter check")
            return findings, checked

        for entity_id in target_entity_ids:
            states = history.get(entity_id, [])
            checked += 1

            # Count state transitions (consecutive entries with different states)
            transitions = 0
            for i in range(1, len(states)):
                if states[i].state != states[i - 1].state:
                    transitions += 1

            if transitions > CHATTER_THRESHOLD:
                fci = round(transitions / CHATTER_WINDOW_MINUTES, 1)
                findings.append(
                    Finding(
                        entity_id=entity_id,
                        rule="State Chatter",
                        category="Signals",
                        severity=SEVERITY_MAJOR,
                        description=(
                            f"{transitions} state transitions in {CHATTER_WINDOW_MINUTES} min "
                            f"(FCI={fci}/min, threshold={CHATTER_THRESHOLD}). "
                            "Possible bouncing contact, reed flutter, or packet-drop loop."
                        ),
                    )
                )

        return findings, checked
