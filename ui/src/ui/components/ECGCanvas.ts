// src/ui/components/ECGCanvas.ts
//
// Real-time scrolling ECG monitor using PixiJS (WebGL).
//
// Key fix: labelContainer is built ONCE in initialize() and never cleared.
// Only the signal graphics are cleared and redrawn on each frame.
// This prevents PIXI Text blur caused by recreating text objects at 60fps.
//
// Y scale: fixed -2 to +2 (matches Python z-score normalization).
// Signal clamped to ±2.5 so it never exits the grid.
//
// Features:
//   - Fixed Y labels (+2, +1, 0, -1, -2) aligned with grid lines
//   - Fixed X labels (0s to 4s)
//   - R-peak markers (yellow dots)
//   - Mouse hover: crosshair + tooltip
//   - Pause/Resume button
//   - Flatline mode (red line + FLATLINE text) for cardiac arrest

import * as PIXI from "pixi.js";

export class ECGCanvas {
  private app!: PIXI.Application;
  private graphics!: PIXI.Graphics;
  private labelContainer!: PIXI.Container;
  private flatlineText!: PIXI.Text;
  private container: HTMLElement;

  private readonly canvasWidth = 1000;
  private readonly canvasHeight = 300;
  private readonly maxPoints = 800;

  private readonly marginLeft = 48;
  private readonly marginBottom = 28;
  private readonly marginTop = 14;
  private readonly marginRight = 10;

  private readonly yMin = -3;
  private readonly yMax = 3;

  private get drawH() { return this.canvasHeight - this.marginTop - this.marginBottom; }
  private get drawW() { return this.canvasWidth - this.marginLeft - this.marginRight; }

  private signalBuffer: number[] = [];
  private peakBuffer: number[] = [];
  private isFlat = false;

  private initialized = false;
  private pendingSignal: number[] = [];
  private pendingPeaks: number[] = [];
  private pendingFlat = false;

  private paused = false;
  private frozenBuffer: number[] = [];
  private frozenPeaks: number[] = [];
  private frozenFlat = false;

  private hoverX: number | null = null;
  private tooltip!: HTMLDivElement;
  private pauseBtn!: HTMLButtonElement;

  // Single source of truth for Y coordinate mapping
  private ampToY(amp: number): number {
    const norm = (amp - this.yMin) / (this.yMax - this.yMin);
    const y0 = this.marginTop;
    const y1 = this.canvasHeight - this.marginBottom;
    return y1 - norm * (y1 - y0);
  }

  constructor(containerId: string) {
    let container = document.getElementById(containerId);
    if (!container) container = document.querySelector(".ecg-panel");
    if (!container) throw new Error(`ECG container not found: ${containerId}`);
    this.container = container;
    void this.initialize();
  }

  private async initialize(): Promise<void> {
    const dpr = window.devicePixelRatio || 1;

    this.app = new PIXI.Application();
    await this.app.init({
      width: this.canvasWidth,
      height: this.canvasHeight,
      background: "#081018",
      antialias: true,
      resolution: dpr,
      autoDensity: true,
    });

    // graphics: cleared every frame (signal + grid)
    this.graphics = new PIXI.Graphics();

    // labelContainer: built ONCE, never cleared — prevents blur
    this.labelContainer = new PIXI.Container();

    this.app.stage.addChild(this.graphics);
    this.app.stage.addChild(this.labelContainer);

    // Build static labels once
    this.buildLabels();

    // FLATLINE text — hidden by default, shown in cardiac arrest
    this.flatlineText = new PIXI.Text({
      text: "FLATLINE",
      style: {
        fontSize: 28,
        fill: 0xff2222,
        fontFamily: "monospace",
        fontWeight: "bold",
      }
    });
    this.flatlineText.anchor.set(0.5, 0.5);
    this.flatlineText.x = this.canvasWidth / 2;
    this.flatlineText.y = this.canvasHeight / 2;
    this.flatlineText.visible = false;
    this.app.stage.addChild(this.flatlineText);

    // DOM
    this.container.innerHTML = "";
    this.container.style.cssText = "display:flex; flex-direction:column; gap:4px; position:relative;";

    const canvasWrapper = document.createElement("div");
    canvasWrapper.style.cssText = "position:relative;";
    canvasWrapper.appendChild(this.app.canvas);

    this.tooltip = document.createElement("div");
    this.tooltip.style.cssText = `
      position:absolute; display:none; pointer-events:none;
      background:rgba(4,12,18,0.93); color:#00ff66; font-size:11px;
      padding:4px 10px; border-radius:4px; border:1px solid #00cc55;
      font-family:monospace; white-space:nowrap; z-index:10;
    `;
    canvasWrapper.appendChild(this.tooltip);
    this.container.appendChild(canvasWrapper);

    const controlRow = document.createElement("div");
    controlRow.style.cssText = "display:flex; justify-content:space-between; align-items:center; padding:0 4px;";

    const xTitle = document.createElement("span");
    xTitle.textContent = "time (s)";
    xTitle.style.cssText = "font-size:10px; color:#2a5a4a; font-family:monospace;";
    controlRow.appendChild(xTitle);

    this.pauseBtn = document.createElement("button");
    this.pauseBtn.textContent = "⏸  Pause";
    this.pauseBtn.style.cssText = `
      font-size:13px; padding:6px 20px; cursor:pointer; border-radius:6px;
      background:transparent; color:#4a8a6a; border:1px solid #2a5a4a;
      font-family:monospace;
    `;
    this.pauseBtn.addEventListener("click", () => this.togglePause());
    controlRow.appendChild(this.pauseBtn);
    this.container.appendChild(controlRow);

    this.app.canvas.addEventListener("mousemove", (e) => this.onMouseMove(e));
    this.app.canvas.addEventListener("mouseleave", () => {
      this.hoverX = null;
      this.tooltip.style.display = "none";
    });

    this.initialized = true;
    this.startLoop();

    if (this.pendingSignal.length > 0) {
      this.renderSignal(this.pendingSignal, this.pendingPeaks, this.pendingFlat);
      this.pendingSignal = [];
      this.pendingPeaks = [];
    }
  }

  /**
   * Builds static Y and X axis labels into labelContainer.
   * Called once — labels never change and are never recreated.
   */
  private buildLabels(): void {
    const x0 = this.marginLeft;
    const yBot = this.canvasHeight - this.marginBottom;

    // Y labels: +2, +1, 0, -1, -2
    [3, 2, 1, 0, -1, -2, -3].forEach(val => {
      const text = new PIXI.Text({
        text: val === 0 ? "0" : (val > 0 ? `+${val}` : `${val}`),
        style: {
          fontSize: 10,
          fill: val === 0 ? 0x4aaa80 : 0x4a7a68,
          fontFamily: "monospace",
        }
      });
      text.anchor.set(1, 0.5);
      text.x = x0 - 6;
      text.y = this.ampToY(val);
      this.labelContainer.addChild(text);
    });

    // mV label
    const mvLabel = new PIXI.Text({
      text: "mV",
      style: { fontSize: 9, fill: 0x2a5a4a, fontFamily: "monospace" }
    });
    mvLabel.x = 2;
    mvLabel.y = 2;
    this.labelContainer.addChild(mvLabel);

    // X labels: 0.0s to 4.0s
    const xSteps = 8;
    const totalSec = this.maxPoints / 200;
    for (let i = 0; i <= xSteps; i++) {
      const x = x0 + (i / xSteps) * this.drawW;
      const sec = ((i / xSteps) * totalSec).toFixed(1);
      const xLabel = new PIXI.Text({
        text: `${sec}s`,
        style: { fontSize: 10, fill: 0x4a7a68, fontFamily: "monospace" }
      });
      xLabel.anchor.set(0.5, 0);
      xLabel.x = x;
      xLabel.y = yBot + 4;
      this.labelContainer.addChild(xLabel);
    }
  }

  private togglePause(): void {
    this.paused = !this.paused;
    if (this.paused) {
      this.frozenBuffer = [...this.signalBuffer];
      this.frozenPeaks = [...this.peakBuffer];
      this.frozenFlat = this.isFlat;
      this.pauseBtn.textContent = "▶  Resume";
      this.pauseBtn.style.color = "#00ff66";
      this.pauseBtn.style.borderColor = "#00cc55";
    } else {
      this.pauseBtn.textContent = "⏸  Pause";
      this.pauseBtn.style.color = "#4a8a6a";
      this.pauseBtn.style.borderColor = "#2a5a4a";
    }
  }

  private onMouseMove(e: MouseEvent): void {
    const rect = this.app.canvas.getBoundingClientRect();
    const scaleX = this.canvasWidth / rect.width;
    const x = (e.clientX - rect.left) * scaleX;
    const x0 = this.marginLeft;
    const x1 = this.canvasWidth - this.marginRight;

    if (x < x0 || x > x1) {
      this.hoverX = null;
      this.tooltip.style.display = "none";
      return;
    }

    this.hoverX = x;
    const buf = this.paused ? this.frozenBuffer : this.signalBuffer;
    const xStep = this.drawW / (this.maxPoints - 1);
    const sampleIdx = Math.round((x - x0) / xStep);
    const startIdx = Math.max(0, buf.length - this.maxPoints);
    const visible = buf.slice(startIdx);

    if (sampleIdx >= 0 && sampleIdx < visible.length) {
      const amplitude = visible[sampleIdx].toFixed(3);
      const timeSec = (sampleIdx / 200).toFixed(3);
      this.tooltip.style.display = "block";
      this.tooltip.style.left = `${e.clientX - rect.left + 14}px`;
      this.tooltip.style.top = `${e.clientY - rect.top - 36}px`;
      this.tooltip.textContent = `t = ${timeSec} s    amp = ${amplitude}`;
    }
  }

  private startLoop(): void {
    const loop = () => { this.draw(); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  }

  /**
   * Receives a new ECG batch from DashboardController.
   * @param newSignal - Filtered ECG samples from Python processor
   * @param peaks     - R-peak indices
   * @param flat      - true = cardiac arrest → show flatline
   */
  public renderSignal(newSignal: number[], peaks: number[] = [], flat = false): void {
    if (!Array.isArray(newSignal) || newSignal.length === 0) return;

    if (!this.initialized) {
      this.pendingSignal = newSignal;
      this.pendingPeaks = peaks;
      this.pendingFlat = flat;
      return;
    }

    if (this.paused) return;

    this.isFlat = flat;
    const offset = this.signalBuffer.length;

    for (const value of newSignal) {
      const n = Number(value);
      const clamped = Math.max(-2.5, Math.min(2.5, Number.isFinite(n) ? n : 0));
      this.signalBuffer.push(clamped);
    }

    for (const p of peaks) this.peakBuffer.push(offset + p);

    if (this.signalBuffer.length > this.maxPoints) {
      const drop = this.signalBuffer.length - this.maxPoints;
      this.signalBuffer = this.signalBuffer.slice(-this.maxPoints);
      this.peakBuffer = this.peakBuffer.map(p => p - drop).filter(p => p >= 0);
    }
  }

  private drawGrid(): void {
    const x0 = this.marginLeft;
    const x1 = this.canvasWidth - this.marginRight;
    const yTop = this.marginTop;
    const yBot = this.canvasHeight - this.marginBottom;

    // Horizontal lines at -2, -1, 0, +1, +2
    [2, 1, 0, -1, -2].forEach(val => {
      const y = this.ampToY(val);
      this.graphics.moveTo(x0, y).lineTo(x1, y);
    });
    this.graphics.stroke({ width: 1, color: 0x16303a, alpha: 0.8 });

    // Zero line brighter
    this.graphics.moveTo(x0, this.ampToY(0)).lineTo(x1, this.ampToY(0));
    this.graphics.stroke({ width: 1, color: 0x1e5a40, alpha: 1 });

    // Vertical lines
    for (let i = 0; i <= 8; i++) {
      const x = x0 + (i / 8) * this.drawW;
      this.graphics.moveTo(x, yTop).lineTo(x, yBot);
    }
    this.graphics.stroke({ width: 1, color: 0x16303a, alpha: 0.8 });
  }

  private draw(): void {
    if (!this.initialized) return;

    // Only clear graphics (signal + grid), never labelContainer
    this.graphics.clear();
    this.drawGrid();

    const buf = this.paused ? this.frozenBuffer : this.signalBuffer;
    const peaks = this.paused ? this.frozenPeaks : this.peakBuffer;
    const flat = this.paused ? this.frozenFlat : this.isFlat;

    this.flatlineText.visible = false;

    const x0 = this.marginLeft;
    const xStep = this.drawW / (this.maxPoints - 1);
    const startIdx = Math.max(0, buf.length - this.maxPoints);
    const visible = buf.slice(startIdx);

    if (visible.length < 2) return;

    const offsetX = x0 + this.drawW - (visible.length - 1) * xStep;
    const yTop = this.marginTop;
    const yBot = this.canvasHeight - this.marginBottom;

    if (flat) {
      // Cardiac arrest — red flatline at y=0
      const yZero = this.ampToY(0);
      this.graphics.moveTo(offsetX, yZero)
        .lineTo(offsetX + (visible.length - 1) * xStep, yZero);
      this.graphics.stroke({ width: 2, color: 0xff2222, alpha: 1 });
      return;
    }

    // Normal ECG signal
    this.graphics.moveTo(offsetX, this.ampToY(visible[0]));
    for (let i = 1; i < visible.length; i++) {
      this.graphics.lineTo(offsetX + i * xStep, this.ampToY(visible[i]));
    }
    this.graphics.stroke({ width: 2, color: 0x00ff66, alpha: 1 });

    // R-peak markers — yellow dots at QRS peaks
    const sigMax = Math.max(...visible);
    const sigMin = Math.min(...visible);
    const threshold = sigMin + (sigMax - sigMin) * 0.70;
    const searchWindow = 20;

    for (const peakIdx of peaks) {
      const visIdx = peakIdx - startIdx;
      if (visIdx < 0 || visIdx >= visible.length) continue;
      const lo = Math.max(0, visIdx - searchWindow);
      const hi = Math.min(visible.length - 1, visIdx + searchWindow);
      let bestIdx = visIdx, bestVal = visible[visIdx];
      for (let j = lo; j <= hi; j++) {
        if (visible[j] > bestVal) { bestVal = visible[j]; bestIdx = j; }
      }
      if (bestVal < threshold) continue;
      const px = offsetX + bestIdx * xStep;
      const py = this.ampToY(bestVal);
      this.graphics.circle(px, py, 4);
      this.graphics.fill({ color: 0xffdd00, alpha: 0.9 });
    }

    // Hover crosshair
    if (this.hoverX !== null) {
      this.graphics.moveTo(this.hoverX, yTop).lineTo(this.hoverX, yBot);
      this.graphics.stroke({ width: 1, color: 0xffffff, alpha: 0.2 });
    }
  }
}