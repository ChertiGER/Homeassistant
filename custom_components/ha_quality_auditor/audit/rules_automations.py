"""Automation Reliability Triage.

Analyses the most recent execution traces for each automation, flagging
those with errors or excessive duration as reliability risks.

Strictly read-only: queries automation traces, never modifies automations.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..const import (
    AUTOMATION_MAX_DURATION_MS,
    AUTOMATION_TRACE_COUNT,
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
)
from .models import Finding

_LOGGER = logging.getLogger(__name__)


class AutomationTriageRule:
    """Evaluate automation trace history for errors and latency issues."""

    async def evaluate(
        self, hass: HomeAssistant
    ) -> tuple[list[Finding], int]:
        """Return (findings, entities_checked)."""
        findings: list[Finding] = []
        checked = 0

        # Get all automation entity IDs
        automation_states = hass.states.async_all("automation")
        if not automation_states:
            return findings, checked

        # Try to import trace APIs
        try:
            from homeassistant.components.trace import async_list_traces
        except ImportError:
            _LOGGER.warning(
                "Trace component not available — skipping automation triage"
            )
            return findings, checked

        for state in automation_states:
            entity_id = state.entity_id
            checked += 1

            # Extract the automation_id (entity_id without 'automation.' prefix)
            automation_id = entity_id.removeprefix("automation.")

            try:
                # Fetch recent traces for this automation
                traces = await async_list_traces(
                    hass, "automation", automation_id
                )
            except Exception:
                _LOGGER.debug(
                    "Could not fetch traces for %s — possibly never triggered",
                    entity_id,
                )
                continue

            # Limit to the most recent N traces
            recent_traces = traces[:AUTOMATION_TRACE_COUNT] if traces else []

            has_error = False
            has_slow = False
            error_msg = ""
            max_duration = 0.0

            for trace_summary in recent_traces:
                # Check for error result
                trace_state = trace_summary.get("state", "")
                if trace_state == "stopped" and trace_summary.get("result", {}).get(
                    "error"
                ):
                    has_error = True
                    error_msg = trace_summary.get("result", {}).get(
                        "error", "Unknown error"
                    )

                # Also check the 'last_step' error pattern
                if trace_summary.get("state") == "error":
                    has_error = True
                    error_msg = trace_summary.get("error", "Execution error")

                # Check duration
                run_duration = trace_summary.get("duration", 0)
                if isinstance(run_duration, (int, float)):
                    duration_ms = run_duration * 1000  # Convert seconds to ms
                    max_duration = max(max_duration, duration_ms)

            # Generate findings based on analysis
            if has_error:
                friendly_name = state.attributes.get("friendly_name", entity_id)
                findings.append(
                    Finding(
                        entity_id=entity_id,
                        rule="Automation Error",
                        category="Automations",
                        severity=SEVERITY_CRITICAL,
                        description=(
                            f"Automation '{friendly_name}' has error in recent traces: "
                            f"{error_msg}. Check automation trace for details."
                        ),
                    )
                )

            if max_duration > AUTOMATION_MAX_DURATION_MS:
                friendly_name = state.attributes.get("friendly_name", entity_id)
                # Only add if not already flagged as error (avoid double-flagging)
                if not has_error:
                    findings.append(
                        Finding(
                            entity_id=entity_id,
                            rule="Automation Slow",
                            category="Automations",
                            severity=SEVERITY_MAJOR,
                            description=(
                                f"Automation '{friendly_name}' peak duration "
                                f"{max_duration:.0f}ms exceeds {AUTOMATION_MAX_DURATION_MS}ms "
                                "threshold. Investigate for blocking calls or long waits."
                            ),
                        )
                    )

        return findings, checked
