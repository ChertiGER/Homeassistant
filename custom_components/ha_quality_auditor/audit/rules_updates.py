"""Pending Updates Audit Rule.

Scans all update entities (Core, OS, Add-ons, HACS, and Device Firmware)
for available updates that have not been explicitly skipped.

Strictly read-only: inspects state of update entities, never applies updates.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..const import SEVERITY_MINOR
from .models import Finding

_LOGGER = logging.getLogger(__name__)


class PendingUpdateRule:
    """Evaluate update entities for pending software, OS, and firmware updates."""

    async def evaluate(
        self, hass: HomeAssistant
    ) -> tuple[list[Finding], int]:
        """Return (findings, entities_checked)."""
        findings: list[Finding] = []
        checked = 0

        update_states = hass.states.async_all("update")
        if not update_states:
            return findings, checked

        for state in update_states:
            checked += 1

            if state.state != "on":
                continue

            installed = state.attributes.get("installed_version")
            latest = state.attributes.get("latest_version")
            skipped = state.attributes.get("skipped_version")

            # If user explicitly skipped this target version, respect their choice
            if skipped and latest and skipped == latest:
                continue

            title = (
                state.attributes.get("title")
                or state.attributes.get("friendly_name")
                or state.entity_id
            )

            version_info = ""
            if installed and latest:
                version_info = f" ({installed} → {latest})"
            elif latest:
                version_info = f" (target version: {latest})"

            findings.append(
                Finding(
                    entity_id=state.entity_id,
                    rule="Pending Update",
                    category="Updates",
                    severity=SEVERITY_MINOR,
                    description=(
                        f"Update available for '{title}'{version_info}. "
                        "Applying updates ensures security patches, bug fixes, and system stability."
                    ),
                )
            )

        return findings, checked
