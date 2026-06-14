// src/ui/components/HistoryChart.ts
//
// Patient history timeline with side-by-side detail panel.
// Fully theme-aware — uses CSS variables from style.css for light/dark mode.

interface VitalsEntry {
  timestamp: number;
  bpm?: number;
  heartRate?: number;
  spo2?: number;
  temperature?: number;
  temp?: number;
  patient_name?: string;
}

interface EcgEntry {
  timestamp: number;
  verified_hr: number | null;
  confidence: number | null;
  quality: string | null;
  missing_samples: number | null;
  patient_name?: string;
}

interface TimelineEvent {
  timestamp: number;
  dateLabel: string;
  time: string;
  datetime: string;
  hr: number | null;
  spo2: number | null;
  temp: number | null;
  verified_hr: number | null;
  confidence: number | null;
  quality: string | null;
  status: "STABLE" | "WARNING" | "CRITICAL";
  message: string;
  isHourly: boolean;
  patient_name?: string;
}

const T = {
  HR_WARN_LO: 50,
  HR_WARN_HI: 120,
  HR_CRIT_LO: 35,
  HR_CRIT_HI: 160,
  SPO2_WARN: 92,
  SPO2_CRIT: 88,
  TEMP_WARN: 38,
  TEMP_CRIT: 39,
};

// Status colors — same in both themes
const STATUS = {
  stable: "#00cc66",
  warning: "#ffaa00",
  critical: "#ff4444",
};

function statusColor(s: "STABLE" | "WARNING" | "CRITICAL"): string {
  return s === "CRITICAL"
    ? STATUS.critical
    : s === "WARNING"
      ? STATUS.warning
      : STATUS.stable;
}

// Theme-aware: reads computed CSS variable from document root
function cssVar(name: string): string {
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

export class HistoryChart {
  private timelineEl!: HTMLDivElement;
  private detailEl!: HTMLDivElement;
  private noDataEl!: HTMLDivElement;
  private events: TimelineEvent[] = [];
  private selectedIdx: number = -1;
  private rowEls: HTMLDivElement[] = [];

  constructor(private readonly containerId: string) {
    this.buildDOM();
  }

  // ── DOM ───────────────────────────────────────────────────────

  private buildDOM(): void {
    const root = document.getElementById(this.containerId);
    if (!root)
      throw new Error(`HistoryChart: container not found: ${this.containerId}`);
    root.innerHTML = "";

    this.noDataEl = document.createElement("div");
    this.noDataEl.textContent = "No data in selected time range.";
    this.noDataEl.style.cssText = `
      display:none; text-align:center;
      color:var(--text-color); opacity:0.5;
      font-family:monospace; font-size:14px; padding:24px 0;
    `;
    root.appendChild(this.noDataEl);

    // Two-column wrapper — timeline 60%, detail 40%
    const cols = document.createElement("div");
    cols.style.cssText = "display:flex; gap:16px; align-items:flex-start;";
    root.appendChild(cols);

    // Left: scrollable timeline — 60%
    const leftWrap = document.createElement("div");
    leftWrap.style.cssText = `
      flex:6; min-width:0;
      max-height:460px; overflow-y:auto;
      scrollbar-width:thin;
    `;
    this.timelineEl = document.createElement("div");
    this.timelineEl.style.cssText =
      "display:flex; flex-direction:column; gap:0;";
    leftWrap.appendChild(this.timelineEl);
    cols.appendChild(leftWrap);

    // Right: detail panel — 40%, fully theme-aware
    this.detailEl = document.createElement("div");
    this.detailEl.style.cssText = `
      flex:4; min-width:0;
      background:var(--card-bg);
      border:1px solid var(--card-border);
      border-radius:10px; padding:20px;
      font-family:monospace; font-size:13px;
      color:var(--text-color);
      position:sticky; top:0;
      display:none;
    `;
    this.detailEl.innerHTML = `
      <div style="font-size:12px; text-align:center; padding:20px 0; color:var(--text-color); opacity:0.5;">
        Click an event to see details
      </div>`;
    cols.appendChild(this.detailEl);
  }

  // ── Classification ────────────────────────────────────────────

  private classify(
    hr: number | null,
    spo2: number | null,
    temp: number | null,
  ) {
    if (spo2 !== null && spo2 < T.SPO2_CRIT)
      return {
        status: "CRITICAL" as const,
        message: `Critical oxygen saturation: ${spo2}%`,
      };
    if (hr !== null && (hr < T.HR_CRIT_LO || hr > T.HR_CRIT_HI))
      return {
        status: "CRITICAL" as const,
        message: `Critical heart rate: ${hr} BPM`,
      };
    if (temp !== null && temp >= T.TEMP_CRIT)
      return {
        status: "CRITICAL" as const,
        message: `Critical temperature: ${temp.toFixed(1)}°C`,
      };
    if (spo2 !== null && spo2 < T.SPO2_WARN)
      return {
        status: "WARNING" as const,
        message: `Low oxygen saturation: ${spo2}%`,
      };
    if (hr !== null && (hr < T.HR_WARN_LO || hr > T.HR_WARN_HI))
      return {
        status: "WARNING" as const,
        message: `Abnormal heart rate: ${hr} BPM`,
      };
    if (temp !== null && temp >= T.TEMP_WARN)
      return {
        status: "WARNING" as const,
        message: `Elevated temperature: ${temp.toFixed(1)}°C`,
      };
    return { status: "STABLE" as const, message: "Patient stable" };
  }

  // ── Build events ──────────────────────────────────────────────

  private buildTimeline(
    vitals: VitalsEntry[],
    ecgHistory: EcgEntry[],
  ): TimelineEvent[] {
    if (vitals.length === 0) return [];

    const sorted = [...vitals].sort((a, b) => a.timestamp - b.timestamp);
    const ecgMap = new Map<number, EcgEntry>();
    for (const e of ecgHistory) ecgMap.set(e.timestamp, e);

    const events: TimelineEvent[] = [];
    let lastStatus: "STABLE" | "WARNING" | "CRITICAL" | null = null;
    let lastHourlyTs = -Infinity;
    const ONE_HOUR = 1 * 60 * 1000;

    for (const v of sorted) {
      const hr = v.bpm ?? v.heartRate ?? null;
      const spo2 = v.spo2 ?? null;
      const temp = v.temperature ?? v.temp ?? null;
      const { status, message } = this.classify(
        typeof hr === "number" ? hr : null,
        typeof spo2 === "number" ? spo2 : null,
        typeof temp === "number" ? temp : null,
      );

      const isHourly = status === "STABLE" && lastStatus === "STABLE";
      const shouldEmit =
        status !== "STABLE" ||
        lastStatus !== "STABLE" ||
        v.timestamp - lastHourlyTs >= ONE_HOUR;

      if (!shouldEmit) continue;

      // Find nearest ECG entry ±30s
      let bestEcg: EcgEntry | null = null;
      let bestDiff = 30_000;
      for (const [ts, ecg] of ecgMap) {
        const diff = Math.abs(ts - v.timestamp);
        if (diff < bestDiff) {
          bestDiff = diff;
          bestEcg = ecg;
        }
      }

      const d = new Date(v.timestamp);
      events.push({
        timestamp: v.timestamp,
        dateLabel: d.toLocaleDateString([], {
          weekday: "long",
          day: "numeric",
          month: "long",
          year: "numeric",
        }),
        time: d.toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
        datetime: d.toLocaleString([], {
          weekday: "short",
          day: "numeric",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
        hr,
        spo2,
        temp,
        verified_hr: bestEcg?.verified_hr ?? null,
        confidence: bestEcg?.confidence ?? null,
        quality: bestEcg?.quality ?? null,
        status,
        message,
        isHourly,
        patient_name: v.patient_name,
      });

      if (status === "STABLE") lastHourlyTs = v.timestamp;
      lastStatus = status;
    }

    return events;
  }

  // ── Render timeline ───────────────────────────────────────────

  private renderTimeline(): void {
    this.timelineEl.innerHTML = "";
    this.rowEls = [];
    this.selectedIdx = -1;
    this.detailEl.style.display = "none";

    let lastDateLabel = "";

    this.events.forEach((ev, idx) => {
      // Day separator — uses theme-aware border color
      if (ev.dateLabel !== lastDateLabel) {
        lastDateLabel = ev.dateLabel;
        const sep = document.createElement("div");
        sep.style.cssText = `
          display:flex; align-items:center; gap:10px;
          padding:12px 4px 6px;
          font-family:monospace; font-size:11px;
          color:var(--text-color); opacity:0.5;
        `;
        sep.innerHTML = `
          <div style="flex:1; height:1px; background:var(--card-border);"></div>
          <span>${ev.dateLabel}</span>
          <div style="flex:1; height:1px; background:var(--card-border);"></div>
        `;
        this.timelineEl.appendChild(sep);
      }

      const color = statusColor(ev.status);

      const row = document.createElement("div");
      row.style.cssText = `
        display:flex; align-items:center; gap:10px;
        padding:8px 10px; border-radius:6px; cursor:pointer;
        font-family:monospace; font-size:12px;
        color:var(--text-color);
        border:1px solid transparent;
        transition: background 0.15s, border-color 0.15s;
      `;
      row.title = ev.datetime; // hover tooltip

      row.addEventListener("mouseenter", () => {
        if (idx !== this.selectedIdx) {
          row.style.background = "var(--card-bg)";
          row.style.borderColor = color + "66";
        }
      });
      row.addEventListener("mouseleave", () => {
        if (idx !== this.selectedIdx) {
          row.style.background = "transparent";
          row.style.borderColor = "transparent";
        }
      });
      row.addEventListener("click", () => this.selectRow(idx));

      // Dot
      const dot = document.createElement("div");
      dot.style.cssText = `
        width:8px; height:8px; border-radius:50%;
        background:${color}; flex-shrink:0;
        opacity:${ev.isHourly ? "0.4" : "1"};
      `;

      // Time
      const time = document.createElement("span");
      time.textContent = ev.time;
      time.style.cssText = `
        min-width:72px; font-size:11px;
        color:var(--text-color); opacity:0.6;
      `;

      // Badge
      const badge = document.createElement("span");
      badge.textContent = ev.status;
      badge.style.cssText = `
        padding:1px 7px; border-radius:9px; font-size:10px; font-weight:bold;
        background:${color}22; color:${color}; border:1px solid ${color};
        min-width:54px; text-align:center; flex-shrink:0;
      `;

      // Message — uses --text-color so it's readable in both themes
      const msg = document.createElement("span");
      msg.textContent = ev.isHourly
        ? "Patient stable — hourly check"
        : ev.message;
      msg.style.cssText = `
        flex:1;
        color:var(--text-color);
        opacity:${ev.isHourly ? "0.55" : "1"};
      `;

      row.append(dot, time, badge, msg);
      this.timelineEl.appendChild(row);
      this.rowEls.push(row);
    });
  }

  private selectRow(idx: number): void {
    // Clear previous selection
    if (this.selectedIdx >= 0 && this.rowEls[this.selectedIdx]) {
      const prev = this.rowEls[this.selectedIdx];
      prev.style.background = "transparent";
      prev.style.borderColor = "transparent";
    }

    this.selectedIdx = idx;
    const row = this.rowEls[idx];
    const ev = this.events[idx];
    const color = statusColor(ev.status);

    row.style.background = "var(--card-bg)";
    row.style.borderColor = color;

    this.renderDetail(ev, color);
  }

  // ── Detail panel ──────────────────────────────────────────────

  private renderDetail(ev: TimelineEvent, sc: string): void {
    this.detailEl.style.display = "block";
    this.detailEl.style.borderColor = sc;

    const qualityColor =
      ev.quality === "good"
        ? STATUS.stable
        : ev.quality === "fair"
          ? STATUS.warning
          : STATUS.critical;

    const qualityBadge = ev.quality
      ? `<span style="padding:2px 7px; border-radius:8px; font-size:10px;
           background:${qualityColor}22; color:${qualityColor}; border:1px solid ${qualityColor};">
           ECG: ${ev.quality}</span>`
      : "";

    const confText =
      ev.confidence != null
        ? `${(ev.confidence * 100).toFixed(0)}% confidence`
        : "from ECG";

    const verifiedDisplay =
      ev.verified_hr !== null ? ev.verified_hr.toFixed(2) + " BPM" : "--";

    this.detailEl.innerHTML = `
      <div style="margin-bottom:14px;">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
          <span style="padding:2px 8px; border-radius:9px; font-size:11px; font-weight:bold;
            background:${sc}22; color:${sc}; border:1px solid ${sc};">${ev.status}</span>
          ${qualityBadge}
        </div>
        <div style="font-size:12px; color:var(--text-color); opacity:0.7;">${ev.datetime}</div>
        ${ev.patient_name ? `<div style="font-size:12px; color:var(--text-color); opacity:0.7; margin-top:2px;">Patient: ${ev.patient_name}</div>` : ""}
        ${
          ev.message !== "Patient stable"
            ? `<div style="color:${sc}; font-size:12px; margin-top:6px;">⚠ ${ev.message}</div>`
            : ""
        }
      </div>

      <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
        ${this.box(
          "Heart Rate",
          ev.hr !== null ? ev.hr + " BPM" : "--",
          ev.hr !== null && (ev.hr < 50 || ev.hr > 120)
            ? STATUS.warning
            : STATUS.stable,
          "normal: 50–120",
        )}
        ${this.box("Verified HR", verifiedDisplay, "#aa88ff", confText)}
        ${this.box(
          "SpO₂",
          ev.spo2 !== null ? ev.spo2 + "%" : "--",
          ev.spo2 !== null && ev.spo2 < 92 ? STATUS.warning : "#00ccff",
          "normal: ≥92%",
        )}
        ${this.box(
          "Temperature",
          ev.temp !== null ? ev.temp.toFixed(1) + "°C" : "--",
          ev.temp !== null && ev.temp >= T.TEMP_CRIT
            ? STATUS.critical
            : ev.temp !== null && ev.temp >= T.TEMP_WARN
              ? STATUS.warning
              : "#ffaa00",
          "normal: <38°C",
        )}
      </div>
    `;
  }

  private box(
    label: string,
    value: string,
    valueColor: string,
    note: string,
  ): string {
    return `
      <div style="
        background:var(--bg-color);
        border:1px solid var(--card-border);
        border-radius:8px; padding:10px; text-align:center;
      ">
        <div style="font-size:11px; font-weight:600; color:var(--text-color); margin-bottom:6px;">${label}</div>
        <div style="font-size:18px; font-weight:bold; color:${valueColor};">${value}</div>
        <div style="font-size:10px; color:var(--text-color); opacity:0.6; margin-top:4px;">${note}</div>
      </div>`;
  }

  // ── Public ────────────────────────────────────────────────────

  public updateData(vitals: VitalsEntry[], ecgHistory: EcgEntry[] = []): void {
    this.detailEl.style.display = "none";

    if (!vitals || vitals.length === 0) {
      this.noDataEl.style.display = "block";
      this.timelineEl.innerHTML = "";
      return;
    }

    this.noDataEl.style.display = "none";
    this.events = this.buildTimeline(vitals, ecgHistory);
    this.renderTimeline();
  }
}
