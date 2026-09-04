/**
 * HA Quality Auditor — Sidebar Panel (LitElement Web Component)
 *
 * Industrial Leitstand design following:
 * - DIN EN ISO 9241-110 (ergonomics)
 * - High-Performance HMI principles
 * - Continuous system quality audit visualisation
 *
 * Colour coding (strict):
 *   Green (#10b981) = Compliant / Grade A
 *   Amber (#f59e0b) = Process deviation / Grade B
 *   Red   (#ef4444) = Critical non-conformity / Grade C
 */

const LitElement = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace") ?? customElements.get("hc-lovelace")
);
const html = LitElement?.prototype?.html ?? (() => "");
const css = LitElement?.prototype?.css ?? (() => "");

class HaQualityAuditorPanel extends (LitElement ?? HTMLElement) {
  static get properties() {
    return {
      hass: { type: Object },
      panel: { type: Object },
      narrow: { type: Boolean },
      _data: { type: Object, state: true },
      _loading: { type: Boolean, state: true },
      _sortColumn: { type: String, state: true },
      _sortAsc: { type: Boolean, state: true },
    };
  }

  constructor() {
    super();
    this._data = null;
    this._loading = false;
    this._sortColumn = "severity";
    this._sortAsc = true;
  }

  connectedCallback() {
    super.connectedCallback();
    this._fetchData();
  }

  async _fetchData() {
    if (!this.hass) return;
    this._loading = true;
    try {
      const result = await this.hass.callWS({
        type: "ha_quality_auditor/run_audit",
      });
      this._data = result;
    } catch (err) {
      console.error("Quality Auditor: Failed to fetch audit data", err);
      // Fallback: try reading sensor states
      this._tryReadSensors();
    } finally {
      this._loading = false;
    }
  }

  _tryReadSensors() {
    if (!this.hass) return;
    const scoreState = this.hass.states["sensor.ha_quality_score"];
    const findingsState = this.hass.states["sensor.ha_audit_findings_count"];
    if (scoreState) {
      this._data = {
        score: parseFloat(scoreState.state) || 0,
        grade: scoreState.attributes.grade || "?",
        findings: [],
        total_entities_checked: scoreState.attributes.entities_checked || 0,
        findings_count: parseInt(findingsState?.state) || 0,
        critical_count: findingsState?.attributes?.critical || 0,
        major_count: findingsState?.attributes?.major || 0,
        minor_count: findingsState?.attributes?.minor || 0,
        timestamp: scoreState.attributes.last_audit || "",
      };
    }
  }

  async _runAudit() {
    this._loading = true;
    try {
      const result = await this.hass.callWS({
        type: "ha_quality_auditor/run_audit",
      });
      this._data = result;
    } catch (err) {
      console.error("Quality Auditor: Audit trigger failed", err);
    } finally {
      this._loading = false;
    }
  }

  _getGradeColor(grade) {
    switch (grade) {
      case "A":
        return "var(--qa-green)";
      case "B":
        return "var(--qa-amber)";
      case "C":
        return "var(--qa-red)";
      default:
        return "var(--qa-text)";
    }
  }

  _getSeverityColor(severity) {
    switch (severity) {
      case "CRITICAL":
        return "var(--qa-red)";
      case "MAJOR":
        return "var(--qa-amber)";
      case "MINOR":
        return "var(--qa-green)";
      default:
        return "var(--qa-border)";
    }
  }

  _getSeverityWeight(severity) {
    switch (severity) {
      case "CRITICAL":
        return 3;
      case "MAJOR":
        return 2;
      case "MINOR":
        return 1;
      default:
        return 0;
    }
  }

  _sortFindings(findings) {
    if (!findings) return [];
    const sorted = [...findings];
    sorted.sort((a, b) => {
      let valA, valB;
      switch (this._sortColumn) {
        case "severity":
          valA = this._getSeverityWeight(a.severity);
          valB = this._getSeverityWeight(b.severity);
          break;
        case "entity_id":
          valA = a.entity_id;
          valB = b.entity_id;
          break;
        case "rule":
          valA = a.rule;
          valB = b.rule;
          break;
        default:
          valA = a.entity_id;
          valB = b.entity_id;
      }
      if (valA < valB) return this._sortAsc ? -1 : 1;
      if (valA > valB) return this._sortAsc ? 1 : -1;
      return 0;
    });
    return sorted;
  }

  _toggleSort(column) {
    if (this._sortColumn === column) {
      this._sortAsc = !this._sortAsc;
    } else {
      this._sortColumn = column;
      this._sortAsc = true;
    }
    this.requestUpdate();
  }

  _formatTimestamp(ts) {
    if (!ts) return "—";
    try {
      const d = new Date(ts);
      return d.toLocaleString("de-DE", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return ts;
    }
  }

  render() {
    const d = this._data;
    const score = d ? d.score : 0;
    const grade = d ? d.grade : "—";
    const findingsCount = d ? d.findings_count || 0 : 0;
    const critical = d ? d.critical_count || 0 : 0;
    const major = d ? d.major_count || 0 : 0;
    const minor = d ? d.minor_count || 0 : 0;
    const findings = d ? this._sortFindings(d.findings || []) : [];
    const timestamp = d ? this._formatTimestamp(d.timestamp) : "—";
    const entitiesChecked = d ? d.total_entities_checked || 0 : 0;

    return html`
      <div class="qa-container">
        <!-- Header -->
        <div class="qa-header">
          <div class="qa-header-left">
            <ha-icon icon="mdi:clipboard-check-outline"></ha-icon>
            <h1>Quality Auditor</h1>
            <span class="qa-subtitle">System Quality Audit</span>
          </div>
          <div class="qa-header-right">
            <a
              href="https://paypal.me/YHolz"
              target="_blank"
              rel="noopener noreferrer"
              class="qa-btn-coffee"
            >
              ☕ Buy me a coffee
            </a>
            <span class="qa-timestamp">
              <ha-icon icon="mdi:clock-outline" class="qa-ts-icon"></ha-icon>
              ${timestamp}
            </span>
          </div>
        </div>

        <!-- KPI Cards -->
        <div class="qa-kpi-grid">
          <!-- Score Card -->
          <div class="qa-kpi-card">
            <div class="qa-kpi-label">Quality Score</div>
            <div
              class="qa-kpi-value"
              style="color: ${this._getGradeColor(grade)}"
            >
              ${d ? score.toFixed(1) : "—"}%
            </div>
            <div class="qa-kpi-bar">
              <div
                class="qa-kpi-bar-fill"
                style="width: ${score}%; background: ${this._getGradeColor(
                  grade
                )}"
              ></div>
            </div>
            <div class="qa-kpi-sub">${entitiesChecked} Entities geprüft</div>
          </div>

          <!-- Grade Card -->
          <div class="qa-kpi-card">
            <div class="qa-kpi-label">Systembewertung</div>
            <div
              class="qa-kpi-value qa-grade"
              style="color: ${this._getGradeColor(grade)}"
            >
              ${grade}
            </div>
            <div class="qa-kpi-sub">
              ${grade === "A"
                ? "Optimal"
                : grade === "B"
                ? "Optimierungsbedarf"
                : grade === "C"
                ? "Handlungsbedarf"
                : "—"}
            </div>
          </div>

          <!-- Findings Card -->
          <div class="qa-kpi-card">
            <div class="qa-kpi-label">Befunde</div>
            <div class="qa-kpi-value">${findingsCount}</div>
            <div class="qa-findings-breakdown">
              <span class="qa-badge qa-badge-critical">${critical}C</span>
              <span class="qa-badge qa-badge-major">${major}M</span>
              <span class="qa-badge qa-badge-minor">${minor}m</span>
            </div>
          </div>
        </div>

        <!-- Action Bar -->
        <div class="qa-action-bar">
          <button
            class="qa-btn-scan"
            @click=${this._runAudit}
            ?disabled=${this._loading}
          >
            ${this._loading
              ? html`<ha-icon
                    icon="mdi:loading"
                    class="qa-spin"
                  ></ha-icon>
                  Audit läuft…`
              : html`<ha-icon icon="mdi:refresh"></ha-icon> Audit starten`}
          </button>
        </div>

        <!-- Findings Table -->
        ${findings.length > 0
          ? html`
              <div class="qa-table-container">
                <table class="qa-table">
                  <thead>
                    <tr>
                      <th class="qa-th-num">#</th>
                      <th
                        class="qa-th-sortable"
                        @click=${() => this._toggleSort("entity_id")}
                      >
                        Entity
                        ${this._sortColumn === "entity_id"
                          ? this._sortAsc
                            ? "▲"
                            : "▼"
                          : ""}
                      </th>
                      <th
                        class="qa-th-sortable"
                        @click=${() => this._toggleSort("rule")}
                      >
                        Regel
                        ${this._sortColumn === "rule"
                          ? this._sortAsc
                            ? "▲"
                            : "▼"
                          : ""}
                      </th>
                      <th>Kategorie</th>
                      <th
                        class="qa-th-sortable"
                        @click=${() => this._toggleSort("severity")}
                      >
                        Severity
                        ${this._sortColumn === "severity"
                          ? this._sortAsc
                            ? "▲"
                            : "▼"
                          : ""}
                      </th>
                      <th>Ursache / Hinweis</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${findings.map(
                      (f, i) => html`
                        <tr
                          class="qa-row"
                          style="border-left: 4px solid ${this._getSeverityColor(
                            f.severity
                          )}"
                        >
                          <td class="qa-td-num">${i + 1}</td>
                          <td class="qa-td-entity">${f.entity_id}</td>
                          <td>${f.rule}</td>
                          <td class="qa-td-ref">${f.category || f.p_reference}</td>
                          <td>
                            <span
                              class="qa-severity-badge"
                              style="background: ${this._getSeverityColor(
                                f.severity
                              )}"
                            >
                              ${f.severity}
                            </span>
                          </td>
                          <td class="qa-td-desc">${f.description}</td>
                        </tr>
                      `
                    )}
                  </tbody>
                </table>
              </div>
            `
          : html`
              <div class="qa-empty-state">
                <ha-icon icon="mdi:check-circle-outline"></ha-icon>
                <p>
                  ${d
                    ? "Keine Befunde — alle geprüften Entities sind konform."
                    : "Noch kein Audit durchgeführt."}
                </p>
              </div>
            `}
      </div>
    `;
  }

  static get styles() {
    return css`
      :host {
        --qa-bg: #1e293b;
        --qa-surface: #334155;
        --qa-surface-hover: #3b4d66;
        --qa-text: #f1f5f9;
        --qa-text-muted: #94a3b8;
        --qa-green: #10b981;
        --qa-amber: #f59e0b;
        --qa-red: #ef4444;
        --qa-border: #475569;
        --qa-radius: 12px;
        --qa-transition: 0.2s ease;

        display: block;
        min-height: 100vh;
        background: var(--qa-bg);
        color: var(--qa-text);
        font-family: "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;
        padding: 24px;
        box-sizing: border-box;
      }

      /* ── Header ────────────────────────────────── */
      .qa-container {
        max-width: 1400px;
        margin: 0 auto;
      }

      .qa-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 28px;
        flex-wrap: wrap;
        gap: 12px;
      }

      .qa-header-left {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .qa-header-left ha-icon {
        --mdc-icon-size: 32px;
        color: var(--qa-green);
      }

      .qa-header h1 {
        margin: 0;
        font-size: 24px;
        font-weight: 700;
        letter-spacing: -0.02em;
      }

      .qa-subtitle {
        font-size: 13px;
        color: var(--qa-text-muted);
        background: rgba(255, 255, 255, 0.06);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 500;
      }

      .qa-header-right {
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
      }

      .qa-btn-coffee {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 221, 0, 0.12);
        color: #facc15;
        border: 1px solid rgba(250, 204, 21, 0.35);
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 600;
        text-decoration: none;
        transition: transform var(--qa-transition), background var(--qa-transition), box-shadow var(--qa-transition);
      }

      .qa-btn-coffee:hover {
        background: rgba(255, 221, 0, 0.22);
        border-color: #facc15;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(250, 204, 21, 0.2);
        color: #fef08a;
      }

      .qa-timestamp {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
        color: var(--qa-text-muted);
      }

      .qa-ts-icon {
        --mdc-icon-size: 16px;
      }

      /* ── KPI Grid ──────────────────────────────── */
      .qa-kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
        gap: 20px;
        margin-bottom: 24px;
      }

      .qa-kpi-card {
        background: var(--qa-surface);
        border-radius: var(--qa-radius);
        padding: 24px;
        border: 1px solid var(--qa-border);
        transition: transform var(--qa-transition),
          box-shadow var(--qa-transition);
      }

      .qa-kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
      }

      .qa-kpi-label {
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--qa-text-muted);
        margin-bottom: 8px;
      }

      .qa-kpi-value {
        font-size: 42px;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: 8px;
        transition: color var(--qa-transition);
      }

      .qa-grade {
        font-size: 56px;
      }

      .qa-kpi-sub {
        font-size: 12px;
        color: var(--qa-text-muted);
      }

      .qa-kpi-bar {
        height: 6px;
        background: rgba(255, 255, 255, 0.08);
        border-radius: 3px;
        margin: 12px 0 8px;
        overflow: hidden;
      }

      .qa-kpi-bar-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.6s ease, background 0.4s ease;
      }

      .qa-findings-breakdown {
        display: flex;
        gap: 8px;
        margin-top: 12px;
      }

      .qa-badge {
        font-size: 12px;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 6px;
        font-family: "SF Mono", "Fira Code", monospace;
      }

      .qa-badge-critical {
        background: rgba(239, 68, 68, 0.18);
        color: var(--qa-red);
      }
      .qa-badge-major {
        background: rgba(245, 158, 11, 0.18);
        color: var(--qa-amber);
      }
      .qa-badge-minor {
        background: rgba(16, 185, 129, 0.18);
        color: var(--qa-green);
      }

      /* ── Action Bar ────────────────────────────── */
      .qa-action-bar {
        margin-bottom: 24px;
      }

      .qa-btn-scan {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(135deg, #10b981, #059669);
        color: #fff;
        font-size: 14px;
        font-weight: 600;
        padding: 10px 24px;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        transition: transform var(--qa-transition), opacity var(--qa-transition),
          box-shadow var(--qa-transition);
      }

      .qa-btn-scan:hover:not([disabled]) {
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(16, 185, 129, 0.35);
      }

      .qa-btn-scan:active:not([disabled]) {
        transform: scale(0.98);
      }

      .qa-btn-scan[disabled] {
        opacity: 0.6;
        cursor: not-allowed;
      }

      .qa-btn-scan ha-icon {
        --mdc-icon-size: 18px;
      }

      @keyframes spin {
        from {
          transform: rotate(0deg);
        }
        to {
          transform: rotate(360deg);
        }
      }
      .qa-spin {
        animation: spin 1s linear infinite;
      }

      /* ── Table ─────────────────────────────────── */
      .qa-table-container {
        overflow-x: auto;
        border-radius: var(--qa-radius);
        border: 1px solid var(--qa-border);
        background: var(--qa-surface);
      }

      .qa-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
      }

      .qa-table thead {
        background: rgba(0, 0, 0, 0.2);
      }

      .qa-table th {
        text-align: left;
        padding: 12px 16px;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.05em;
        color: var(--qa-text-muted);
        white-space: nowrap;
        border-bottom: 1px solid var(--qa-border);
      }

      .qa-th-sortable {
        cursor: pointer;
        user-select: none;
      }

      .qa-th-sortable:hover {
        color: var(--qa-text);
      }

      .qa-th-num {
        width: 40px;
      }

      .qa-table td {
        padding: 10px 16px;
        border-bottom: 1px solid rgba(71, 85, 105, 0.4);
        vertical-align: top;
      }

      .qa-row {
        transition: background var(--qa-transition);
      }

      .qa-row:hover {
        background: var(--qa-surface-hover);
      }

      .qa-td-num {
        color: var(--qa-text-muted);
        font-family: "SF Mono", "Fira Code", monospace;
        font-size: 11px;
      }

      .qa-td-entity {
        font-family: "SF Mono", "Fira Code", monospace;
        font-size: 12px;
        color: #93c5fd;
        word-break: break-all;
      }

      .qa-td-ref {
        font-family: "SF Mono", "Fira Code", monospace;
        color: var(--qa-text-muted);
      }

      .qa-td-desc {
        max-width: 400px;
        line-height: 1.5;
        color: var(--qa-text-muted);
      }

      .qa-severity-badge {
        display: inline-block;
        font-size: 10px;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        color: #fff;
        letter-spacing: 0.04em;
      }

      /* ── Empty State ───────────────────────────── */
      .qa-empty-state {
        text-align: center;
        padding: 64px 24px;
        color: var(--qa-text-muted);
      }

      .qa-empty-state ha-icon {
        --mdc-icon-size: 48px;
        color: var(--qa-green);
        opacity: 0.6;
        margin-bottom: 16px;
      }

      .qa-empty-state p {
        font-size: 15px;
        margin: 0;
      }

      /* ── Responsive ────────────────────────────── */
      @media (max-width: 768px) {
        :host {
          padding: 16px;
        }

        .qa-header h1 {
          font-size: 20px;
        }

        .qa-kpi-value {
          font-size: 32px;
        }

        .qa-grade {
          font-size: 42px;
        }

        .qa-kpi-grid {
          grid-template-columns: 1fr;
        }

        .qa-td-desc {
          max-width: 200px;
        }
      }
    `;
  }
}

customElements.define("ha-quality-auditor-panel", HaQualityAuditorPanel);
