# 📋 Home Assistant Quality Auditor

[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024%2B-blue.svg)](https://www.home-assistant.io/)
[![Python](https://img.shields.io/badge/Python-3.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![Code Style](https://img.shields.io/badge/Code%20Style-Black%20%2F%20Ruff-black.svg)](https://github.com/astral-sh/ruff)
[![Tests](https://img.shields.io/badge/Tests-19%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

A native **Home Assistant Custom Integration** providing continuous quality monitoring, proactive fault detection, and an **Industrial Leitstand (High-Performance HMI)** sidebar panel for your smart home.

---

## ✨ Features

* **🔍 Sensor Health Monitoring (Messwert-Überwachung):**  
  Detects frozen analog sensors (temperature, power, humidity, etc.) whose values remain perfectly static ($\Delta = 0.0$) across rolling 6-hour windows. Proactively surfaces firmware lockups, dead batteries, or disconnected endpoints.

* **⚡ Signal & State Chatter Index (FCI):**  
  Tracks transition frequencies on binary sensors and telemetry entities (`zha`, `mqtt`, `esphome`). Flags contact prellen (reed switch flutter) and packet-drop reconnect loops ($> 20$ transitions in $15$ minutes).

* **⏱️ Automation Reliability Triage:**  
  Analyzes recent execution traces for all automations. Flags failed executions (`TemplateError`, missing entity references, script aborts) as **CRITICAL** and execution latency exceeding $2500\text{ ms}$ as **MAJOR**.

* **📊 Dynamic Quality Score & Grades:**  
  Calculates a continuous System Quality Score ($0.0 - 100.0\%$) and grade:
  * **Grade A (Optimal, $\ge 90\%$):** System operates within nominal tolerances.
  * **Grade B (Optimierungsbedarf, $\ge 70\%$):** Minor deviations or isolated errors present.
  * **Grade C (Handlungsbedarf, $< 70\%$):** Critical errors or widespread sensor failures detected.

* **🖥️ Native Sidebar Panel (High-Performance HMI):**  
  Integrates directly into the Home Assistant sidebar (`/quality-auditor`) with dark slate aesthetics (DIN EN ISO 9241-110 ergonomics), KPI cards, color-coded findings table, and manual re-scan triggers.

* **🔒 Strict Safety & Privacy Guarantees:**  
  * **Read-Only:** Forbidden from invoking actuator services (`light.turn_off`, `switch.toggle`, `lock.unlock`, `cover.close`).
  * **100% Local:** All computations execute in-process on your Home Assistant host. Zero data leaves your local network.

---

## 🏗️ Architecture & Directory Structure

```
.
├── custom_components/
│   └── ha_quality_auditor/
│       ├── __init__.py                # Async setup, static path & sidebar panel registration
│       ├── const.py                   # Domain thresholds & constants
│       ├── coordinator.py             # DataUpdateCoordinator (1h interval & WebSocket trigger)
│       ├── manifest.json              # Integration metadata (local_push, frontend/http/recorder deps)
│       ├── sensor.py                  # Quality score & findings count sensor platform
│       ├── audit/
│       │   ├── __init__.py            # Audit package
│       │   ├── engine.py              # Orchestrator & quality scoring algorithm
│       │   ├── models.py              # Finding & AuditResult dataclasses
│       │   ├── rules_automations.py   # Automation trace failure & latency triage
│       │   ├── rules_flaky.py         # State chatter index (FCI) rule
│       │   └── rules_frozen.py        # Frozen analog sensor detection rule
│       └── frontend/
│           ├── ha-quality-auditor-panel.js  # LitElement Web Component panel
│           └── preview.html                 # Standalone Leitstand UI preview
├── tests/
│   ├── conftest.py                    # Shared test fixtures & Home Assistant mocks
│   ├── test_engine.py                 # Engine & rule unit tests
│   ├── test_init.py                   # Async setup, static path & panel registration tests
│   └── test_sensor.py                 # Sensor entity & attribute tests
├── .gitignore
└── README.md
```

---

## 🚀 Installation & Setup

### Method 1: Manual Installation

1. Copy the `custom_components/ha_quality_auditor` folder into your Home Assistant `/config/custom_components/` directory:
   ```bash
   cp -r custom_components/ha_quality_auditor /config/custom_components/
   ```
2. Restart Home Assistant Core (**Settings → System → Restart**).
3. The **Quality Audit** entry automatically appears in your left sidebar (`/quality-auditor`).

---

## 📈 Diagnostic Entities

The integration exposes two diagnostic entities for automations, alerts, and dashboard cards:

| Entity ID | State | Attributes |
|---|---|---|
| `sensor.ha_quality_score` | `85.5` (%) | `grade` (A/B/C), `last_audit`, `entities_checked` |
| `sensor.ha_audit_findings_count` | `5` (count) | `critical` (count), `major` (count), `minor` (count) |

### Example Automation (Notify on Critical Finding):
```yaml
automation:
  - alias: "Alert on Smart Home Quality Drop"
    trigger:
      - platform: numeric_state
        entity_id: sensor.ha_quality_score
        below: 70
    action:
      - service: notify.notify
        data:
          title: "⚠️ Smart Home Quality Alert"
          message: >
            Quality Score dropped to {{ states('sensor.ha_quality_score') }}% (Grade {{ state_attr('sensor.ha_quality_score', 'grade') }}).
            {{ state_attr('sensor.ha_audit_findings_count', 'critical') }} critical finding(s) detected.
```

---

## 🧪 Running the Test Suite

The test suite contains 19 automated unit tests verifying the audit engine, rule algorithms, integration lifecycle, and sensor entities:

```bash
# Set up virtual environment (optional, using uv)
uv venv .venv
uv pip install pytest pytest-asyncio voluptuous

# Run tests
.venv/bin/python -m pytest tests/ -v --tb=short
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
