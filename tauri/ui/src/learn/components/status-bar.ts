// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — StatusBar component (UI-SPEC §Component Inventory).
//
// 40px-tall bottom rail. Three segments separated by silk-22 hairline
// `|` dividers:
//
//   1. Controller display name + mirror status:
//        `<display name> · midi mirror live`  (when active)
//        `waiting for midi`                    (when no port)
//        `controller unplugged`                (when port disappeared)
//   2. Latency probe `P95: NN ms` with a colored pip:
//        ≤50ms green (--led-ok), 50-80ms amber (--led-warn),
//        >80ms red (--led-fault) — the red-guardrail visual signal
//        that fires §LEARN-LATENCY-CONTINGENCY.
//   3. Window-management hint `cmd+tab to deck`.
//
// Latency calculation: rolling 240-sample window of (performance.now() -
// envelope_emit_ts) deltas. Pushed by `learn-window.ts` on each
// midi_position frame. P95 computed once per second.

type MirrorStatus = "waiting" | "live" | "unplugged";

/**
 * The rolling-window latency tracker. 240 samples = 8 seconds of 30 Hz
 * MIDI frames — the canonical sample size for the §LEARN-LATENCY harness.
 */
class LatencyRing {
  private samples: number[] = [];
  private readonly capacity = 240;

  push(ms: number): void {
    if (!Number.isFinite(ms) || ms < 0) return;
    this.samples.push(ms);
    if (this.samples.length > this.capacity) this.samples.shift();
  }

  /** Compute P95 latency; returns null if no samples. */
  p95(): number | null {
    if (this.samples.length === 0) return null;
    const sorted = [...this.samples].sort((a, b) => a - b);
    const idx = Math.floor(sorted.length * 0.95);
    return sorted[Math.min(idx, sorted.length - 1)] ?? null;
  }
}

export class StatusBar {
  private el: HTMLElement;
  private controllerEl: HTMLSpanElement;
  private latencyEl: HTMLSpanElement;
  private latencyPipEl: HTMLSpanElement;
  private hintEl: HTMLSpanElement;
  private ring = new LatencyRing();
  private timer: number | null = null;

  constructor(el: HTMLElement) {
    this.el = el;
    this.el.className = "learn-status-bar";
    this.el.innerHTML = `
      <span class="learn-status-segment learn-status-controller">waiting for midi</span>
      <span class="learn-status-divider" aria-hidden="true">|</span>
      <span class="learn-status-segment learn-status-latency">
        <span class="learn-status-latency-pip" data-pip="neutral" aria-hidden="true"></span>
        <span class="learn-status-latency-text">P95: -- ms</span>
      </span>
      <span class="learn-status-divider" aria-hidden="true">|</span>
      <span class="learn-status-segment learn-status-hint">${this.hintText()}</span>
    `;
    this.controllerEl = this.el.querySelector(
      ".learn-status-controller",
    ) as HTMLSpanElement;
    this.latencyEl = this.el.querySelector(
      ".learn-status-latency-text",
    ) as HTMLSpanElement;
    this.latencyPipEl = this.el.querySelector(
      ".learn-status-latency-pip",
    ) as HTMLSpanElement;
    this.hintEl = this.el.querySelector(
      ".learn-status-hint",
    ) as HTMLSpanElement;
    this.timer = setInterval(() => this.refreshLatency(), 1000) as unknown as number;
  }

  /** Set the mirror-status segment text. */
  setMirrorStatus(status: MirrorStatus, displayName?: string): void {
    let text: string;
    switch (status) {
      case "live":
        text = `${displayName ?? "controller"} · midi mirror live`;
        break;
      case "unplugged":
        text = "controller unplugged";
        break;
      default:
        text = "waiting for midi";
    }
    this.controllerEl.textContent = text;
  }

  /**
   * Record an emit→render latency sample. Called from
   * `learn-window.ts` whenever a midi_position frame is consumed.
   */
  pushLatency(ms: number): void {
    this.ring.push(ms);
  }

  dispose(): void {
    if (this.timer !== null) {
      clearInterval(this.timer as unknown as ReturnType<typeof setInterval>);
      this.timer = null;
    }
  }

  // ---- private ----

  private refreshLatency(): void {
    const p = this.ring.p95();
    if (p === null) {
      this.latencyEl.textContent = "P95: -- ms";
      this.latencyPipEl.setAttribute("data-pip", "neutral");
      return;
    }
    this.latencyEl.textContent = `P95: ${Math.round(p)} ms`;
    let pip: "ok" | "warn" | "fault";
    if (p <= 50) pip = "ok";
    else if (p <= 80) pip = "warn";
    else pip = "fault";
    this.latencyPipEl.setAttribute("data-pip", pip);
  }

  private hintText(): string {
    // navigator.platform is deprecated but still the most reliable
    // jsdom-safe windows-vs-mac fork. Anything other than Mac uses Alt+Tab.
    const platform =
      typeof navigator !== "undefined"
        ? (navigator.platform ?? "").toLowerCase()
        : "";
    const isMac = platform.includes("mac");
    return isMac ? "cmd+tab to deck" : "alt+tab to deck";
  }
}
