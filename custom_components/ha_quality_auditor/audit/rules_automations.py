"""Automation Reliability Triage.

Analyses the most recent execution traces for each automation, flagging
those with errors or excessive duration as reliability risks.

Strictly read-only: queries automation traces, never modifies automations.
"""

from __future__ import annotations

import logging
from datetime import datetime

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

        # Get all automation entity states
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

            # Skip disabled automations
            if state.state != "on":
                continue

            # In HA, UI-created automations store unique ID in attributes['id'],
            # while YAML automations use entity_id without 'automation.'
            trace_key = state.attributes.get("id") or entity_id.removeprefix("automation.")

            traces = []
            try:
                traces = await async_list_traces(
                    hass, "automation", str(trace_key)
                )
                if not traces and state.attributes.get("id"):
                    traces = await async_list_traces(
                        hass, "automation", entity_id.removeprefix("automation.")
                    )
            except Exception:
                _LOGGER.debug(
                    "Could not fetch traces for %s — possibly never triggered",
                    entity_id,
                )
                continue

            if not traces:
                continue

            # Limit to the most recent N traces
            recent_traces = traces[:AUTOMATION_TRACE_COUNT]

            has_error = False
            error_msg = ""
            max_duration = 0.0

            for trace_summary in recent_traces:
                # Check for error result
                trace_state = trace_summary.get("state", "")
                script_execution = trace_summary.get("script_execution", "")
                result_dict = trace_summary.get("result") or {}

                if (
                    trace_state == "error"
                    or script_execution == "failed"
                    or trace_summary.get("error")
                    or result_dict.get("error")
                ):
                    has_error = True
                    error_msg = (
                        trace_summary.get("error")
                        or result_dict.get("error")
                        or "Execution error"
                    )

                # Calculate duration in ms (either pre-calculated or from timestamps)
                run_duration = trace_summary.get("duration")
                if run_duration is None:
                    timestamps = trace_summary.get("timestamp")
                    if isinstance(timestamps, dict):
                        start_str = timestamps.get("start")
                        finish_str = timestamps.get("finish")
                        if start_str and finish_str:
                            try:
                                start_dt = datetime.fromisoformat(str(start_str))
                                finish_dt = datetime.fromisoformat(str(finish_str))
                                run_duration = (finish_dt - start_dt).total_seconds()
                            except Exception:
                                pass

                if isinstance(run_duration, (int, float)):
                    duration_ms = run_duration * 1000  # Convert seconds to ms
                    max_duration = max(max_duration, duration_ms)

            friendly_name = state.attributes.get("friendly_name", entity_id)

            if has_error:
                findings.append(
                    Finding(
                        entity_id=entity_id,
                        rule="Automation Error",
                        category="Automations",
                        severity=SEVERITY_CRITICAL,
                        description=(
                            f"Automation '{friendly_name}' failed in recent runs: "
                            f"{error_msg}. Check automation traces for details."
                        ),
                    )
                )

            if max_duration > AUTOMATION_MAX_DURATION_MS and not has_error:
                findings.append(
                    Finding(
                        entity_id=entity_id,
                        rule="Automation Slow",
                        category="Automations",
                        severity=SEVERITY_MAJOR,
                        description=(
                            f"Automation '{friendly_name}' peak duration "
                            f"{max_duration:.0f}ms exceeds {AUTOMATION_MAX_DURATION_MS}ms threshold. "
                            "Investigate for blocking calls or long delays."
                        ),
                    )
                )

        return findings, checked

