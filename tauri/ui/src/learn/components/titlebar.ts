// SPDX-License-Identifier: Apache-2.0
//
// Phase 91 Plan 05 — LearnTitlebar component (UI-SPEC §Component Inventory).
//
// 56px-tall titlebar. Three regions:
//   - Left:   `LEARN` wordmark (Saira wdth 85, wght 700, 18px silk + 12px
//             amber text-shadow) — matches the existing wizard/debrief
//             titlebar wordmark visual.
//   - Center: controller display_name (JetBrains Mono 11px silk-65,
//             UPPERCASE letter-spacing 0.18em). Populated from the
//             `display_name` field on `ipc.learn.controller_detected`.
//   - Right:  clock (JetBrains Mono 11px silk-40, HH:MM, updates every
//             1s).
//
// Background recipe verbatim from the wizard titlebar (UI-SPEC §Component
// Inventory): linear-gradient void-glass + backdrop blur + glass-edge
// bottom border + inset top-sheen.

export class LearnTitlebar {
  private el: HTMLElement;
  private controllerNameEl: HTMLSpanElement;
  private clockEl: HTMLSpanElement;
  private clockTimer: number | null = null;

  constructor(el: HTMLElement) {
    this.el = el;
    this.el.className = "learn-titlebar";
    this.el.innerHTML = `
      <span class="learn-titlebar-wordmark">LEARN</span>
      <span class="learn-titlebar-controller" data-empty="true"></span>
      <span class="learn-titlebar-clock"></span>
    `;
    this.controllerNameEl = this.el.querySelector(
      ".learn-titlebar-controller",
    ) as HTMLSpanElement;
    this.clockEl = this.el.querySelector(
      ".learn-titlebar-clock",
    ) as HTMLSpanElement;
    this.tickClock();
    // Tick once per second — `setInterval` returns a positive number in
    // both Node and browser (TS DOM types narrow on the cast).
    this.clockTimer = setInterval(() => this.tickClock(), 1000) as unknown as number;
  }

  /** Update the centre controller-name display. Pass null/empty to clear. */
  setControllerName(displayName: string | null): void {
    if (!displayName || displayName.trim() === "") {
      this.controllerNameEl.textContent = "";
      this.controllerNameEl.setAttribute("data-empty", "true");
      return;
    }
    this.controllerNameEl.textContent = displayName;
    this.controllerNameEl.removeAttribute("data-empty");
  }

  /** Stop the clock tick (called on window unload). */
  dispose(): void {
    if (this.clockTimer !== null) {
      clearInterval(this.clockTimer as unknown as ReturnType<typeof setInterval>);
      this.clockTimer = null;
    }
  }

  // ---- private ----

  private tickClock(): void {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    this.clockEl.textContent = `${hh}:${mm}`;
  }
}
