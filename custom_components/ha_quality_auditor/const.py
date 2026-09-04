"""Constants for the HA Quality Auditor integration."""

from datetime import timedelta

# ── Domain ───────────────────────────────────────────────────────────
DOMAIN = "ha_quality_auditor"

# ── Coordinator ──────────────────────────────────────────────────────
SCAN_INTERVAL = timedelta(hours=1)

# ── Audit Rule: Frozen Sensor ───────────────────────────────────────
FROZEN_WINDOW_HOURS = 6
MIN_HISTORY_POINTS = 2  # Minimum data points to judge frozen state

# ── Audit Rule: State Chatter Index ──────────────────────────────────
CHATTER_WINDOW_MINUTES = 15
CHATTER_THRESHOLD = 20  # Max state transitions before flagging

# ── Audit Rule: Automation Triage ────────────────────────────────────
AUTOMATION_MAX_DURATION_MS = 2500
AUTOMATION_TRACE_COUNT = 5

# ── Quality Scoring ──────────────────────────────────────────────────
PENALTY_CRITICAL = 10
PENALTY_MAJOR = 5
PENALTY_MINOR = 2
GRADE_A_THRESHOLD = 90.0
GRADE_B_THRESHOLD = 70.0

# ── Severity Levels ─────────────────────────────────────────────────
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_MAJOR = "MAJOR"
SEVERITY_MINOR = "MINOR"

# ── Panel / Frontend ────────────────────────────────────────────────
PANEL_URL = "quality-auditor"
PANEL_TITLE = "Quality Audit"
PANEL_ICON = "mdi:clipboard-check-outline"
PANEL_COMPONENT_NAME = "ha-quality-auditor-panel"
PANEL_FRONTEND_URL_PATH = "/ha_quality_auditor_ui"

# ── WebSocket ────────────────────────────────────────────────────────
WS_TYPE_RUN_AUDIT = "ha_quality_auditor/run_audit"

# ── Event Names ──────────────────────────────────────────────────────
EVENT_AUDIT_COMPLETED = "ha_quality_auditor_audit_completed"
