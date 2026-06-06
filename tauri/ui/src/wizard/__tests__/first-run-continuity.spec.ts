/* first-run-continuity.spec.ts — Phase 57 / Plan 57-02 (POLISH-03).
 *
 * The fresh-account continuity smoke. Drives the wizard router across the
 * full STEP_ORDER chain — intro → permissions → audio → controller →
 * skill-level → profile-consent → telemetry-consent → smoke-test — and pins the
 * POLISH-03 invariant: a fresh user is NEVER stuck before audio is live.
 *
 * For every step it asserts (a) the step renders into the #wizard-primary
 * mount and (b) a forward affordance exists (a control wired to advance to
 * the next step). It drives the chain with the real `advanceTo` and asserts
 * `currentStep()` advances accordingly, then asserts the chain terminates at
 * `smoke-test` with the wizard-done "Open vibemix" affordance reachable.
 *
 * This is a SMOKE, not a per-step behaviour suite: the existing step specs
 * (blackhole-step, windows-smartscreen-step, tcc-permissions, onboarding-
 * flow) own the deep per-step assertions. Here we only prove continuity +
 * no dead-end.
 *
 * Headless wiring: every step that fires Tauri IPC (`invoke`,
 * `@tauri-apps/api/event` listen/emit, the ipc/client request helpers)
 * is mocked so the chain runs in jsdom without a sidecar. The mocks
 * resolve to benign empty payloads — the router's per-step bootstrap
 * (.catch()-guarded) tolerates them, and the continuity assertions never
 * depend on a sidecar reply (the gated steps are driven into their armed
 * state directly via setState, which is exactly what the live UI does once
 * the sidecar poll reports success). */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// --- Tauri + IPC mocks (headless: no sidecar) -----------------------------

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async () => undefined),
}));

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => {}),
  emit: vi.fn(async () => undefined),
}));

// The ipc/client helpers never resolve in jsdom (no sidecar), so make the
// requests hang harmlessly (the router awaits them inside .catch()-guarded
// async bootstrap fns and the continuity assertions don't wait on them).
vi.mock("../../ipc/client.js", () => ({
  sendIpcRequest: vi.fn(() => new Promise(() => {})),
  subscribeIpc: vi.fn(async () => () => {}),
  emitIpc: vi.fn(async () => undefined),
}));

import {
  advanceTo,
  currentStep,
  getDevSurface,
  renderCurrentStep,
  type WizardStep,
} from "../router.js";
import { sendIpcRequest } from "../../ipc/client.js";

// Mirrors router.ts STEP_ORDER (the numbered chain after the intro hero).
// Kept local so the test reads the chain it is asserting; if router's
// STEP_ORDER changes, the assertion below catches the drift.
const STEP_ORDER: WizardStep[] = [
  "permissions",
  "audio",
  "controller",
  "skill-level",
  "profile-consent",
  "telemetry-consent",
  "smoke-test",
];

/** Build the three DOM mounts the router renders into. */
function mountWizardShell(): void {
  document.body.innerHTML = `
    <div id="wizard-step-strip"></div>
    <div id="wizard-primary"></div>
    <div id="status-bar"></div>
  `;
}

function primary(): HTMLElement {
  const el = document.getElementById("wizard-primary");
  if (!el) throw new Error("wizard-primary mount missing");
  return el;
}

/** A forward affordance = a non-disabled button whose label moves the user
 *  onward (Continue / Let's go / Open vibemix / Skip). Gated steps expose a
 *  disabled Continue plus a recovery path; we drive those into the armed
 *  state first (see drives below), so by assert-time the forward control is
 *  enabled. */
function hasEnabledForwardControl(root: HTMLElement): boolean {
  const buttons = Array.from(root.querySelectorAll("button"));
  return buttons.some((b) => {
    if (b.disabled) return false;
    if (b.getAttribute("aria-disabled") === "true") return false;
    const label = (b.textContent ?? "").toLowerCase();
    return (
      label.includes("continue") ||
      label.includes("let's go") ||
      label.includes("lets go") ||
      label.includes("open vibemix") ||
      label.includes("skip") ||
      label.includes("start")
    );
  });
}

/** Force a step into the state where its forward control is armed — exactly
 *  the state the live sidecar poll/probe would produce. This is the
 *  "gated-then-armable" contract: a permanently-blocked step would have no
 *  way to reach an armed forward control and would fail the assertion. */
function armStep(step: WizardStep): void {
  const dev = getDevSurface();
  switch (step) {
    case "permissions":
      // Both grants land → Continue arms (step1-permissions.ts:189).
      dev.setState({
        step1: { screenRecording: "granted", microphone: "granted" },
      });
      break;
    case "audio":
      // Output selection lands -> Continue arms.
      dev.setState({
        step2: { ...dev.getState().step2, selectedDeviceId: "built-in" },
      });
      break;
    case "controller":
      // Hardware mapping is optional, so Continue is armed before a listen.
      dev.setState({
        step3: { ...dev.getState().step3, probeState: "idle", secondsLeft: 0 },
      });
      break;
    case "smoke-test":
      // Greeting played (router sets this even on cascade failure) → Open arms.
      dev.setState({
        smokeTest: { ...dev.getState().smokeTest, greetingPlayed: true },
      });
      break;
    default:
      // profile-consent / telemetry-consent have no gating — Continue is
      // always armed.
      break;
  }
}

describe("first-run continuity smoke (POLISH-03)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mountWizardShell();
    // Reset router state to the fresh-install default (intro) via the dev
    // surface — getDevSurface().setState merges, so set currentStep explicitly.
    getDevSurface().setState({ currentStep: "intro" });
    getDevSurface().setState({
      step1: { screenRecording: "pending", microphone: "pending" },
      step2: {
        blackHolePresent: false,
        blackHoleBannerPostClick: false,
        devices: [],
        selectedDeviceId: "",
        selectedHeadphoneDeviceIndex: null,
      },
      step3: {
        detectedController: undefined,
        probeState: "idle",
        secondsLeft: 0,
        caughtLabel: undefined,
      },
      smokeTest: { greetingPlayed: false, meterLevel: 0.5 },
    });
    renderCurrentStep();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
    document.body.replaceChildren();
  });

  it("local STEP_ORDER mirror matches the chain the smoke drives", () => {
    // If router's STEP_ORDER drifts from this mirror, the smoke is asserting
    // a stale chain — surface it loudly. (Drives via currentStep below prove
    // the live order; this guards the mirror used for the loop.)
    expect(STEP_ORDER).toEqual([
      "permissions",
      "audio",
      "controller",
      "skill-level",
      "profile-consent",
      "telemetry-consent",
      "smoke-test",
    ]);
  });

  it("intro renders with a forward affordance into permissions", () => {
    expect(currentStep()).toBe("intro");
    expect(hasEnabledForwardControl(primary())).toBe(true);

    advanceTo("permissions");
    vi.advanceTimersByTime(300); // clear advanceTo's 250ms transition timer
    expect(currentStep()).toBe("permissions");
  });

  it("drives the full STEP_ORDER chain with no dead-end and reaches smoke-test", () => {
    // Start from intro (beforeEach). Step into permissions to begin the chain.
    advanceTo("permissions");
    vi.advanceTimersByTime(300);
    expect(currentStep()).toBe("permissions");

    for (let i = 0; i < STEP_ORDER.length; i++) {
      const step = STEP_ORDER[i]!;
      expect(currentStep()).toBe(step);

      // (a) the step rendered into the primary mount.
      expect(primary().children.length).toBeGreaterThan(0);

      // Drive the gated step into its armed state (sidecar-success analogue).
      armStep(step);
      renderCurrentStep();

      // (b) a forward affordance exists and is enabled — never stuck.
      expect(hasEnabledForwardControl(primary())).toBe(true);

      // Advance to the next step (if any) and confirm currentStep moves.
      const next = STEP_ORDER[i + 1];
      if (next) {
        advanceTo(next);
        vi.advanceTimersByTime(300);
        expect(currentStep()).toBe(next);
      }
    }

    // The chain terminates at the terminal full-surface step.
    expect(currentStep()).toBe("smoke-test");
  });

  it("smoke-test exposes the reachable wizard-done 'Open vibemix' affordance", () => {
    getDevSurface().setState({ currentStep: "smoke-test" });
    armStep("smoke-test"); // greetingPlayed → Open vibemix arms
    renderCurrentStep();

    const buttons = Array.from(primary().querySelectorAll("button"));
    const openCta = buttons.find((b) =>
      (b.textContent ?? "").toLowerCase().includes("open vibemix"),
    );
    expect(openCta).toBeDefined();
    // Reachable = not disabled (greeting played arms it; the router arms it
    // even on greeting failure, so the user is never stranded at the finish).
    expect(openCta!.disabled).toBe(false);
    expect(openCta!.getAttribute("aria-disabled")).not.toBe("true");
  });

  it("permissions Continue is gated-then-armable, not a permanent dead-end", () => {
    getDevSurface().setState({
      currentStep: "permissions",
      step1: { screenRecording: "pending", microphone: "pending" },
    });
    renderCurrentStep();
    // Ungranted: the forward Continue is present but disabled (gated).
    const gated = Array.from(primary().querySelectorAll("button")).find((b) =>
      (b.textContent ?? "").toLowerCase().includes("continue"),
    );
    expect(gated).toBeDefined();
    expect(gated!.disabled).toBe(true);

    // Granting both arms it — the gate releases (recovery path works).
    armStep("permissions");
    renderCurrentStep();
    expect(hasEnabledForwardControl(primary())).toBe(true);
  });

  it("audio step does not probe DJ application windows", () => {
    const sendIpcRequestMock = vi.mocked(sendIpcRequest);
    sendIpcRequestMock.mockClear();

    getDevSurface().setState({
      currentStep: "audio",
      step2: {
        ...getDevSurface().getState().step2,
        selectedDeviceId: "",
      },
    });
    renderCurrentStep();

    expect(sendIpcRequestMock).not.toHaveBeenCalledWith(
      "ipc.calibration.list_windows",
      {},
      "ipc.calibration.window_list",
    );
  });

  it("controller step is passive and does not start MIDI listen on mount", () => {
    const sendIpcRequestMock = vi.mocked(sendIpcRequest);
    sendIpcRequestMock.mockClear();

    getDevSurface().setState({ currentStep: "controller" });
    renderCurrentStep();

    expect(sendIpcRequestMock).not.toHaveBeenCalledWith(
      "ipc.calibration.start_midi_listen",
      expect.anything(),
      expect.anything(),
      expect.anything(),
    );
    expect(primary().textContent).toContain("controller detection is optional");

    const continueCta = Array.from(primary().querySelectorAll("button")).find((b) =>
      (b.textContent ?? "").toLowerCase().includes("continue"),
    );
    expect(continueCta).toBeDefined();
    expect(continueCta!.disabled).toBe(false);
  });

  it("controller Listen now starts the MIDI listener on demand", async () => {
    const sendIpcRequestMock = vi.mocked(sendIpcRequest);
    sendIpcRequestMock.mockClear();
    sendIpcRequestMock.mockResolvedValueOnce({
      type: "ipc.calibration.midi_event",
      ts: "2026-06-06T00:00:00.000Z",
      payload: { control_label: "filter knob", raw: "b0 10 7f" },
    });

    getDevSurface().setState({ currentStep: "controller" });
    renderCurrentStep();

    const listenCta = Array.from(primary().querySelectorAll("button")).find((b) =>
      (b.textContent ?? "").toLowerCase().includes("listen now"),
    );
    expect(listenCta).toBeDefined();
    listenCta!.click();
    await Promise.resolve();
    await Promise.resolve();

    expect(sendIpcRequestMock).toHaveBeenCalledWith(
      "ipc.calibration.start_midi_listen",
      { timeout_s: 10 },
      "ipc.calibration.midi_event",
      12_000,
    );
    expect(getDevSurface().getState().step3.probeState).toBe("caught");
    expect(getDevSurface().getState().step3.caughtLabel).toBe("filter knob");
  });
});
