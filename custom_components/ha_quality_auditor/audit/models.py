"""Data models for the HA Quality Auditor audit system.

Extracted into a separate module to avoid circular imports between
engine.py and the individual rule modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..const import SEVERITY_CRITICAL, SEVERITY_MAJOR, SEVERITY_MINOR


@dataclass
class Finding:
    """A single audit non-conformity."""

    entity_id: str
    rule: str  # Human-readable rule name (e.g. "Frozen Sensor")
    category: str  # Finding category (e.g. "Sensors", "Signals", "Automations")
    severity: str  # CRITICAL / MAJOR / MINOR
    description: str  # Root-cause / explanation
    p_reference: str = ""  # Alias maintained for backwards compatibility

    def __post_init__(self):
        if not self.p_reference:
            self.p_reference = self.category
        elif not self.category:
            self.category = self.p_reference

    def to_dict(self) -> dict:
        """Serialize for WebSocket / frontend transport."""
        return {
            "entity_id": self.entity_id,
            "rule": self.rule,
            "category": self.category,
            "p_reference": self.category,
            "severity": self.severity,
            "description": self.description,
        }


@dataclass
class AuditResult:
    """Aggregated output of a full audit run."""

    score: float = 100.0  # 0.0 – 100.0
    grade: str = "A"  # A / B / C
    findings: list[Finding] = field(default_factory=list)
    total_entities_checked: int = 0
    timestamp: str = ""

    def to_dict(self) -> dict:
        """Serialize for WebSocket / frontend transport."""
        return {
            "score": round(self.score, 1),
            "grade": self.grade,
            "findings": [f.to_dict() for f in self.findings],
            "total_entities_checked": self.total_entities_checked,
            "timestamp": self.timestamp,
            "findings_count": len(self.findings),
            "critical_count": sum(
                1 for f in self.findings if f.severity == SEVERITY_CRITICAL
            ),
            "major_count": sum(
                1 for f in self.findings if f.severity == SEVERITY_MAJOR
            ),
            "minor_count": sum(
                1 for f in self.findings if f.severity == SEVERITY_MINOR
            ),
        }
