"""Quality Audit Engine — Orchestrates all audit rules and computes the overall score.

The engine is deterministic and strictly read-only: it queries entity states,
recorder history, and automation traces but never calls any actuator service.
"""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from ..const import (
    GRADE_A_THRESHOLD,
    GRADE_B_THRESHOLD,
    PENALTY_CRITICAL,
    PENALTY_MAJOR,
    PENALTY_MINOR,
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
)
from .models import AuditResult, Finding
from .rules_automations import AutomationTriageRule
from .rules_flaky import ChatterIndexRule
from .rules_frozen import FrozenSensorRule
from .rules_integrations import IntegrationHealthRule
from .rules_updates import PendingUpdateRule

_LOGGER = logging.getLogger(__name__)

# Re-export for backward compat
__all__ = ["AuditEngine", "AuditResult", "Finding"]

# ── Penalty map ──────────────────────────────────────────────────────

_PENALTY = {
    SEVERITY_CRITICAL: PENALTY_CRITICAL,
    SEVERITY_MAJOR: PENALTY_MAJOR,
    SEVERITY_MINOR: PENALTY_MINOR,
}


# ── Engine ───────────────────────────────────────────────────────────


class AuditEngine:
    """Orchestrates individual audit rules and calculates a quality score."""

    def __init__(self) -> None:
        self._rules = [
            FrozenSensorRule(),
            ChatterIndexRule(),
            AutomationTriageRule(),
            PendingUpdateRule(),
            IntegrationHealthRule(),
        ]

    async def run_audit(self, hass: HomeAssistant) -> AuditResult:
        """Execute all audit rules and return the aggregated result.

        This method is fully async-safe and never blocks the event loop.
        """
        all_findings: list[Finding] = []
        total_checked = 0

        for rule in self._rules:
            try:
                findings, checked = await rule.evaluate(hass)
                all_findings.extend(findings)
                total_checked += checked
            except Exception:
                _LOGGER.exception("Audit rule %s failed", rule.__class__.__name__)
                # Rule failure must not crash the entire audit — skip gracefully.

        score, grade = self._calculate_score(all_findings, total_checked)

        from datetime import datetime, timezone

        result = AuditResult(
            score=score,
            grade=grade,
            findings=all_findings,
            total_entities_checked=total_checked,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        _LOGGER.info(
            "Audit complete: score=%.1f%% grade=%s findings=%d entities=%d",
            result.score,
            result.grade,
            len(result.findings),
            result.total_entities_checked,
        )
        return result

    @staticmethod
    def _calculate_score(
        findings: list[Finding], total_checked: int
    ) -> tuple[float, str]:
        """Compute percentage score and grade.

        Scoring model:
        - Each finding incurs a penalty (CRITICAL=10, MAJOR=5, MINOR=2).
        - penalty_sum is normalised against the number of checked entities.
        - Score = max(0, 100 - (penalty_sum / max(total_checked, 1)) * 100)
        - Grade: A (≥90), B (≥70), C (<70).
        """
        if total_checked == 0:
            return 100.0, "A"

        penalty_sum = sum(_PENALTY.get(f.severity, 0) for f in findings)
        score = max(0.0, 100.0 - (penalty_sum / total_checked) * 100.0)

        if score >= GRADE_A_THRESHOLD:
            grade = "A"
        elif score >= GRADE_B_THRESHOLD:
            grade = "B"
        else:
            grade = "C"

        return round(score, 1), grade
