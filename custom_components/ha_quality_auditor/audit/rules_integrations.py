"""Integration Health & Orphan Detection Rule.

Audits Home Assistant config entries for setup failures, connection retry loops,
and orphaned or unloaded integrations.

Strictly read-only: inspects config entry states, never unloads or modifies entries.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..const import (
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
)
from .models import Finding

_LOGGER = logging.getLogger(__name__)


class IntegrationHealthRule:
    """Evaluate configuration entries for setup errors, retry loops, and orphaned state."""

    async def evaluate(
        self, hass: HomeAssistant
    ) -> tuple[list[Finding], int]:
        """Return (findings, entities_checked)."""
        findings: list[Finding] = []
        checked = 0

        # Verify config_entries manager is available
        config_entries = getattr(hass, "config_entries", None)
        if config_entries is None or not hasattr(config_entries, "async_entries"):
            return findings, checked

        entries = config_entries.async_entries()
        if not entries:
            return findings, checked

        for entry in entries:
            checked += 1

            # Ignore integrations explicitly disabled by user
            if getattr(entry, "disabled_by", None) is not None:
                continue

            # Robust state extraction supporting both Enum and string states
            state_attr = getattr(entry, "state", None)
            state_val = getattr(state_attr, "value", str(state_attr)).lower()

            domain = getattr(entry, "domain", "unknown")
            title = getattr(entry, "title", domain) or domain
            entry_id = getattr(entry, "entry_id", "")
            finding_id = f"integration.{domain}.{entry_id[:8]}" if entry_id else f"integration.{domain}"

            if state_val in ("setup_error", "migration_error"):
                findings.append(
                    Finding(
                        entity_id=finding_id,
                        rule="Integration Setup Error",
                        category="Integrations",
                        severity=SEVERITY_CRITICAL,
                        description=(
                            f"Integration '{title}' ({domain}) failed during setup ({state_val.upper()}). "
                            "Check Home Assistant logs for tracebacks or reconfigure in Settings → Devices & Services."
                        ),
                    )
                )
            elif state_val == "failed_unload":
                findings.append(
                    Finding(
                        entity_id=finding_id,
                        rule="Integration Unload Failure",
                        category="Integrations",
                        severity=SEVERITY_MAJOR,
                        description=(
                            f"Integration '{title}' ({domain}) failed to unload cleanly. "
                            "A restart of Home Assistant is recommended to clear dead locks."
                        ),
                    )
                )
            elif state_val == "setup_retry":
                findings.append(
                    Finding(
                        entity_id=finding_id,
                        rule="Integration Reconnect Loop",
                        category="Integrations",
                        severity=SEVERITY_MAJOR,
                        description=(
                            f"Integration '{title}' ({domain}) is stuck in a reconnect loop (SETUP_RETRY). "
                            "Associated device or cloud service may be offline or unreachable."
                        ),
                    )
                )
            elif state_val == "not_loaded":
                findings.append(
                    Finding(
                        entity_id=finding_id,
                        rule="Orphaned Integration",
                        category="Integrations",
                        severity=SEVERITY_MINOR,
                        description=(
                            f"Integration '{title}' ({domain}) is not loaded (NOT_LOADED) but not marked as disabled. "
                            "Possible orphaned configuration entry or missing hardware component."
                        ),
                    )
                )

        return findings, checked
