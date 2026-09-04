"""DataUpdateCoordinator for the HA Quality Auditor.

Schedules periodic audit runs and stores the latest result for consumption
by sensor entities and the frontend panel.
"""

from __future__ import annotations

import logging

from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

from .audit.engine import AuditEngine, AuditResult
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class QualityAuditCoordinator(DataUpdateCoordinator[AuditResult]):
    """Coordinator that runs the audit engine on a schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry | None = None,
    ) -> None:
        """Initialise the coordinator with default scan interval."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
            config_entry=config_entry,
        )
        self._engine = AuditEngine()

    async def _async_update_data(self) -> AuditResult:
        """Run the full audit and return the result.

        Exceptions from individual rules are caught inside the engine,
        so this method should not raise under normal circumstances.
        """
        return await self._engine.run_audit(self.hass)
