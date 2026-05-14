/* router.ts — wizard state machine + slide transitions (UI-SPEC §Motion §step).
 *
 * Phase 11 Wave 4: replaces Wave 3's setTimeout mocks with real ipc.*
 * requests. Every webview→sidecar interaction goes through
 * ``vibemix/ui/src/ipc/client.ts`` which wraps Promise.race with a 10s
 * timeout (RESEARCH Pitfall 6).
 *
 * Wire-up sites (Wave 4 fills in what Wave 3 mocked):
 *   - Step 1 permission cards poll ipc.permission.check @1Hz.
 *   - Step 1 [ Grant ] buttons invoke Tauri commands open_*_settings /
 *     request_microphone_permission.
 *   - Step 2 mount → ipc.calibration.list_devices.
 *   - Step 2 [ PLAY 1 kHz TEST ] → ipc.calibration.probe_audio (parallel
 *     to user heard-tone Yes/Retry → emitIpc user_heard_tone).
 *   - Step 2 window picker → ipc.calibration.list_windows (Warning #4 —
 *     WS-only window picker; no Tauri-side window-enum command).
 *   - Step 3 mount → ipc.calibration.start_midi_listen (timeout 10s).
 *   - Smoke-test mount → ipc.calibration.smoke_test (timeout 30s).
 *   - Wizard done → emitIpc ipc.wizard.done + invoke write_first_run_state.
 *
 * State transitions still use 250ms ease-in-out (UI-SPEC §Motion Budget cap).
 */

import { invoke } from "@tauri-apps/api/core";

import { emitIpc, sendIpcRequest, subscribeIpc } from "../ipc/client.js";
import { registerShortcuts } from "../session/shortcuts.js";
import { StatusBar } from "./components/status-bar.js";
import type { StatusBarProps } from "./components/status-bar.js";
import { StepIndicator } from "./components/step-indicator.js";
import { renderSmokeTest, type SmokeTestState } from "./smoke-test.js";
import { renderStep0Intro } from "./step0-intro.js";
import { renderStep1, type Step1State } from "./step1-permissions.js";
import { renderStep2, type Step2State } from "./step2-output-device.js";
import { renderStep3, type Step3State } from "./step3-controller.js";

export type WizardStep = "intro" | "permissions" | "audio" | "controller" | "smoke-test" | "done";

export interface WizardState {
  currentStep: WizardStep;
  step1: Step1State;
  step2: Step2State;
  step3: Step3State;
  smokeTest: SmokeTestState;
  statusBar: StatusBarProps;
  platform: "darwin" | "win32" | "linux";
}

const DEFAULT_STATE: WizardState = {
  // Impeccable Wave 1.2 (2026-05-14): wizard now starts at "intro" — the
  // VIBEMIX / DJ FRIEND / IN YOUR EAR hero. One click advances to
  // permissions; the intro is never seen again post-install.
  currentStep: "intro",
  step1: {
    screenRecording: "pending",
    microphone: "pending",
  },
  step2: {
    blackHolePresent: false, // sidecar replies fill this in
    blackHoleBannerPostClick: false,
    devices: [],
    selectedDeviceId: "",
    audioTestState: "idle",
    audioPassed: false,
    actualRate: 0,
    detectedDjApp: undefined,
    windowPickerMode: "hint",
    windowSelected: false,
  },
  step3: {
    detectedController: undefined,
    probeState: "listening",
    secondsLeft: 10,
    caughtLabel: undefined,
  },
  smokeTest: {
    greetingPlayed: false,
    meterLevel: 0.5,
  },
  statusBar: {
    livekit: null,
    gemini: null,
    midi: null,
    screen: null,
  },
  platform: detectPlatform(),
};

function detectPlatform(): "darwin" | "win32" | "linux" {
  // Tauri ships @tauri-apps/api/os.platform() but the Wave 0 scaffold
  // doesn't bundle the OS plugin — falling back to UA detection is
  // adequate for the wizard's macOS/Windows split. (Tauri webview UA
  // contains the underlying platform string.)
  const ua = (globalThis.navigator?.userAgent ?? "").toLowerCase();
  if (ua.includes("mac")) return "darwin";
  if (ua.includes("win")) return "win32";
  return "linux";
}

let wizardState: WizardState = structuredClone(DEFAULT_STATE);
const subscribers = new Set<(state: WizardState) => void>();

function notify(): void {
  for (const cb of subscribers) cb(wizardState);
}

function setState(
  patch: Partial<WizardState> | ((s: WizardState) => Partial<WizardState>),
): void {
  const partial = typeof patch === "function" ? patch(wizardState) : patch;
  wizardState = { ...wizardState, ...partial };
  notify();
  rerender();
}

const STEP_ORDER: WizardStep[] = ["permissions", "audio", "controller", "smoke-test"];

function indexOf(step: WizardStep): number {
  return STEP_ORDER.indexOf(step);
}

function stepStripFor(current: WizardStep): HTMLElement {
  const idx = indexOf(current);
  const stepsConfig: Array<{ id: WizardStep; label: string }> = [
    { id: "permissions", label: "permissions" },
    { id: "audio", label: "device" },
    { id: "controller", label: "controller" },
  ];
  return StepIndicator({
    steps: stepsConfig.map((s, i) => {
      const stepIdx = indexOf(s.id);
      const state =
        stepIdx < idx
          ? ("complete" as const)
          : stepIdx === idx
            ? ("active" as const)
            : ("pending" as const);
      if (current === "smoke-test") {
        return { ...s, state: "complete" as const };
      }
      if (
        i === 0 &&
        wizardState.step1.screenRecording === "granted" &&
        wizardState.step1.microphone === "granted" &&
        idx > 0
      ) {
        return { ...s, state: "complete" as const };
      }
      return { ...s, state };
    }),
  });
}

export function advanceTo(next: WizardStep): void {
  if (next === wizardState.currentStep) return;
  const primaryMount = document.getElementById("wizard-primary");
  if (primaryMount && primaryMount.firstElementChild) {
    const child = primaryMount.firstElementChild as HTMLElement;
    child.style.transition =
      "opacity var(--motion-step) ease-in-out, transform var(--motion-step) ease-in-out";
    child.style.opacity = "0";
    child.style.transform = "translateX(-16px)";
    setTimeout(() => {
      setState({ currentStep: next });
    }, 250);
  } else {
    setState({ currentStep: next });
  }
}

/** Walk the wizard one step backward. Intro has no back (it's the first
 *  surface a user sees). Smoke-test goes back to controller. Wired to the
 *  per-step `[ ← Back ]` button + the `esc` / `cmd+[` shortcut.
 *
 *  Impeccable Wave 5.A — closes the Heuristic 3 (User Control & Freedom)
 *  gap from the 2026-05-14 critique: previously the wizard was strictly
 *  one-way until the user finished. */
export function back(): void {
  const current = wizardState.currentStep;
  switch (current) {
    case "intro":
      return; // No back from the first surface.
    case "permissions":
      // Permissions is the first wizard step proper; back returns to intro.
      advanceTo("intro");
      return;
    case "audio":
      advanceTo("permissions");
      return;
    case "controller":
      advanceTo("audio");
      return;
    case "smoke-test":
      advanceTo("controller");
      return;
    case "done":
      return; // Wizard is done; no back.
  }
}

export function currentStep(): WizardStep {
  return wizardState.currentStep;
}

export function getState(): Readonly<WizardState> {
  return wizardState;
}

function renderInto(parent: HTMLElement, child: HTMLElement): void {
  parent.replaceChildren(child);
  child.style.opacity = "0";
  child.style.transform = "translateX(16px)";
  child.style.transition =
    "opacity var(--motion-step) ease-in-out, transform var(--motion-step) ease-in-out";
  requestAnimationFrame(() => {
    child.style.opacity = "1";
    child.style.transform = "translateX(0)";
  });
}

let rendering = false;

function rerender(): void {
  if (rendering) return;
  rendering = true;
  try {
    renderCurrentStep();
  } finally {
    rendering = false;
  }
}

// Impeccable Wave 5.A — register wizard-wide back shortcuts once. The
// callback inspects the live currentStep so adding a step doesn't require
// re-binding (and intro stays a no-op via back()).
let wizardShortcutsRegistered = false;
function ensureWizardShortcuts(): void {
  if (wizardShortcutsRegistered) return;
  wizardShortcutsRegistered = true;
  registerShortcuts({
    "cmd+[": () => back(),
    "ctrl+[": () => back(),
    // `esc` from a wizard step walks back one. The intro returns no-op
    // via back(), and the smoke-test surface absorbs esc (it's the last
    // step before completion — `back()` is the safe action).
    escape: () => back(),
  });
}

export function renderCurrentStep(): void {
  ensureWizardShortcuts();
  const stepStripMount = document.getElementById("wizard-step-strip");
  const primaryMount = document.getElementById("wizard-primary");
  const statusMount = document.getElementById("status-bar");

  if (!stepStripMount || !primaryMount || !statusMount) {
    console.warn("[router] wizard DOM mounts missing");
    return;
  }

  // Intro hero + smoke-test both own the full surface — no step strip.
  if (
    wizardState.currentStep === "intro" ||
    wizardState.currentStep === "smoke-test"
  ) {
    stepStripMount.replaceChildren();
  } else {
    stepStripMount.replaceChildren(stepStripFor(wizardState.currentStep));
  }

  let primary: HTMLElement;
  switch (wizardState.currentStep) {
    case "intro":
      primary = renderStep0Intro({
        onBegin: () => advanceTo("permissions"),
      });
      break;
    case "permissions":
      primary = renderStep1(wizardState.step1, {
        platform: wizardState.platform,
        onContinue: () => advanceTo("audio"),
        onBack: () => back(),
        onGrantScreen: () => {
          void invoke("open_screen_recording_settings").catch((err) => {
            console.warn("[step1] open_screen_recording_settings failed:", err);
          });
        },
        onGrantMic: () => {
          // Trigger the OS mic prompt. Sidecar's AVCaptureDevice
          // request fires here via Tauri command; the next 1-Hz
          // permission poll picks up the new state.
          void invoke("request_microphone_permission").catch((err) => {
            console.warn("[step1] request_microphone_permission failed:", err);
          });
        },
        onOpenScreenSettings: () => {
          void invoke("open_screen_recording_settings").catch(() => {});
        },
        onOpenMicSettings: () => {
          void invoke("open_microphone_settings").catch(() => {});
        },
      });
      if (!step1PollerStarted) {
        startStep1PermissionPoll();
      }
      break;
    case "audio":
      if (!step2BootStarted) {
        step2BootStarted = true;
        void boostrapStep2();
      }
      primary = renderStep2(wizardState.step2, {
        platform: wizardState.platform,
        onContinue: () => advanceTo("controller"),
        onBack: () => back(),
        onSelectDevice: (id) =>
          setState({ step2: { ...wizardState.step2, selectedDeviceId: id } }),
        onPlayTest: () => {
          setState({
            step2: { ...wizardState.step2, audioTestState: "playing" },
          });
          void runProbeAudio();
        },
        onAudioYes: () => {
          // Forward the user's Yes — the sidecar correlates this
          // with the in-flight probe_audio handler.
          void emitIpc("ipc.calibration.user_heard_tone", { heard: true });
        },
        onAudioRetry: () => {
          void emitIpc("ipc.calibration.user_heard_tone", { heard: false });
          setState({
            step2: { ...wizardState.step2, audioTestState: "idle" },
          });
        },
        onOpenInstall: () => {
          // Capability allowlist (11-03) permits this single URL.
          void invoke("plugin:shell|open", {
            path: "https://existential.audio/blackhole",
          }).catch(() => {});
          setState({
            step2: { ...wizardState.step2, blackHoleBannerPostClick: true },
          });
        },
        onRecheckBlackHole: () => {
          void recheckBlackHole();
        },
        onSelectWindow: () =>
          setState({ step2: { ...wizardState.step2, windowSelected: true } }),
        onPickDifferent: () => {
          setState({
            step2: { ...wizardState.step2, windowPickerMode: "enum" },
          });
          void refreshWindowList();
        },
      });
      break;
    case "controller":
      if (!step3ListenStarted) {
        step3ListenStarted = true;
        void runMidiListen();
      }
      primary = renderStep3(wizardState.step3, {
        onContinue: () => advanceTo("smoke-test"),
        onBack: () => back(),
        onListenAgain: () => {
          step3ListenStarted = false;
          setState({
            step3: {
              ...wizardState.step3,
              probeState: "listening",
              secondsLeft: 10,
              caughtLabel: undefined,
            },
          });
        },
        onSkip: () => advanceTo("smoke-test"),
      });
      if (
        wizardState.step3.probeState === "listening" &&
        (wizardState.step3.secondsLeft ?? 10) > 0
      ) {
        scheduleCountdownTick();
      }
      break;
    case "smoke-test":
      if (!smokeTestStarted) {
        smokeTestStarted = true;
        void runSmokeTest();
      }
      primary = renderSmokeTest(wizardState.smokeTest, {
        onReplay: () => {
          smokeTestStarted = false;
          setState({ smokeTest: { ...wizardState.smokeTest, greetingPlayed: false } });
        },
        onOpenVibemix: () => {
          void completeWizard();
        },
      });
      break;
    case "done":
      primary = document.createElement("div");
      primary.textContent = "loading vibemix…";
      break;
  }

  renderInto(primaryMount, primary);
  statusMount.replaceChildren(StatusBar(wizardState.statusBar));
}

let countdownTimer: number | null = null;

function scheduleCountdownTick(): void {
  if (countdownTimer != null) return;
  countdownTimer = window.setInterval(() => {
    const s3 = wizardState.step3;
    if (s3.probeState !== "listening") {
      if (countdownTimer != null) {
        clearInterval(countdownTimer);
        countdownTimer = null;
      }
      return;
    }
    const next = (s3.secondsLeft ?? 10) - 1;
    if (next <= 0) {
      if (countdownTimer != null) {
        clearInterval(countdownTimer);
        countdownTimer = null;
      }
      setState({
        step3: { ...s3, secondsLeft: 0, probeState: "timeout" },
      });
    } else {
      wizardState = { ...wizardState, step3: { ...s3, secondsLeft: next } };
      const lcd = document.querySelector(".cmp-ctrl-probe__lcd");
      if (lcd) {
        const mm = "00";
        const ss = next.toString().padStart(2, "0");
        lcd.textContent = `${mm}:${ss}`;
      }
    }
  }, 1000);
}

// ---------------------------------------------------------------------------
// Wave 4 — real ipc.* request bodies replacing Wave 3 mocks.
// ---------------------------------------------------------------------------

let step1PollerStarted = false;
let step1PollTimer: number | null = null;
let step2BootStarted = false;
let step3ListenStarted = false;
let smokeTestStarted = false;

/** Poll ipc.permission.check @1Hz for both kinds while Step 1 is active. */
function startStep1PermissionPoll(): void {
  step1PollerStarted = true;
  const poll = async (): Promise<void> => {
    if (wizardState.currentStep !== "permissions") {
      if (step1PollTimer != null) {
        clearInterval(step1PollTimer);
        step1PollTimer = null;
      }
      step1PollerStarted = false;
      return;
    }
    if (wizardState.platform === "darwin") {
      try {
        const screen = await sendIpcRequest(
          "ipc.permission.check",
          { kind: "screen_recording" },
          "ipc.permission.state",
        );
        const screenStatus = (screen as { payload: { status: string } }).payload.status;
        const cardState =
          screenStatus === "authorized" ? "granted" : screenStatus === "denied" ? "denied" : "pending";
        if (wizardState.step1.screenRecording !== cardState) {
          setState({
            step1: { ...wizardState.step1, screenRecording: cardState as Step1State["screenRecording"] },
          });
        }
      } catch (err) {
        // Sidecar bus hiccup — quietly retry next tick.
        console.warn("[step1] screen probe failed:", err);
      }
    }
    try {
      const mic = await sendIpcRequest(
        "ipc.permission.check",
        { kind: "microphone" },
        "ipc.permission.state",
      );
      const micStatus = (mic as { payload: { status: string } }).payload.status;
      const cardState =
        micStatus === "authorized" ? "granted" : micStatus === "denied" ? "denied" : "pending";
      if (wizardState.step1.microphone !== cardState) {
        setState({
          step1: { ...wizardState.step1, microphone: cardState as Step1State["microphone"] },
        });
      }
    } catch (err) {
      console.warn("[step1] mic probe failed:", err);
    }
  };
  // Initial poll, then every 1s.
  void poll();
  step1PollTimer = window.setInterval(() => void poll(), 1000);
}

/** Step 2 bootstrap — request device list + window list in parallel. */
async function boostrapStep2(): Promise<void> {
  await Promise.allSettled([refreshDeviceList(), refreshWindowList()]);
}

async function refreshDeviceList(): Promise<void> {
  try {
    const resp = await sendIpcRequest(
      "ipc.calibration.list_devices",
      {},
      "ipc.calibration.device_list",
    );
    const payload = (resp as { payload: { devices: Array<{ id: string; name: string; is_blackhole: boolean; variant: string | null }>; blackhole_present: boolean } }).payload;
    // Convert sidecar wire shape to UI shape (DropdownDeviceItem).
    // BlackHole entries render as speakers so the picker shows them in
    // the dropdown; auto-select skips them in favor of a real output.
    const devices = payload.devices.map((d) => ({
      id: d.id,
      name: d.name,
      isHeadphones: false,
      isSpeaker: true,
      isAuto: false,
    }));
    // Auto-pick the first non-BlackHole output device as the default
    // selection (matches the UI-SPEC §5 AUTO pill behavior).
    const defaultSelection =
      payload.devices.find((d) => !d.is_blackhole)?.id ?? payload.devices[0]?.id ?? "";
    setState({
      step2: {
        ...wizardState.step2,
        devices,
        blackHolePresent: payload.blackhole_present,
        selectedDeviceId: wizardState.step2.selectedDeviceId || defaultSelection,
      },
    });
  } catch (err) {
    console.warn("[step2] list_devices failed:", err);
  }
}

async function refreshWindowList(): Promise<void> {
  // Warning #4 — WS-only window picker; no Tauri window-enum command.
  try {
    const resp = await sendIpcRequest(
      "ipc.calibration.list_windows",
      {},
      "ipc.calibration.window_list",
    );
    const payload = (resp as { payload: { windows: Array<{ id: string; app_name: string; title: string; dj_app_hint: string | null }> } }).payload;
    if (payload.windows.length === 0) {
      // Empty enumeration — surface "no windowed apps detected" via enum
      // mode with an empty list (the picker shows the recheck CTA).
      setState({
        step2: {
          ...wizardState.step2,
          detectedDjApp: undefined,
          windowPickerMode: "enum",
        },
      });
      return;
    }
    // Auto-select the first DJ-app match (preferring djay > rekordbox >
    // serato > traktor > virtualdj per the Python hint table).
    const djWindow = payload.windows.find((w) => w.dj_app_hint !== null);
    if (djWindow) {
      setState({
        step2: {
          ...wizardState.step2,
          detectedDjApp: {
            appName: djWindow.app_name,
            windowTitle: djWindow.title,
          },
          windowPickerMode: "hint",
        },
      });
    } else {
      setState({
        step2: {
          ...wizardState.step2,
          detectedDjApp: undefined,
          windowPickerMode: "enum",
        },
      });
    }
  } catch (err) {
    console.warn("[step2] list_windows failed:", err);
  }
}

async function recheckBlackHole(): Promise<void> {
  setState({
    step2: { ...wizardState.step2, blackHoleBannerPostClick: false },
  });
  await refreshDeviceList();
}

async function runProbeAudio(): Promise<void> {
  if (!wizardState.step2.selectedDeviceId) {
    console.warn("[step2] no device selected");
    return;
  }
  try {
    const resp = await sendIpcRequest(
      "ipc.calibration.probe_audio",
      {
        output_device_id: wizardState.step2.selectedDeviceId,
        expected_rate: 48000,
      },
      "ipc.calibration.audio_result",
      35_000, // longer than default — 30s user-confirm window + 5s buffer
    );
    const payload = (resp as {
      payload: {
        playback_ok: boolean;
        audible_confirmed: boolean;
        programmatic_pass: boolean;
        actual_rate: number | null;
        error: string | null;
      };
    }).payload;
    const passed = payload.audible_confirmed && payload.programmatic_pass;
    setState({
      step2: {
        ...wizardState.step2,
        audioTestState: passed ? "passed" : "failed",
        audioPassed: passed,
        actualRate: payload.actual_rate ?? 0,
      },
    });
  } catch (err) {
    console.warn("[step2] probe_audio failed:", err);
    setState({
      step2: { ...wizardState.step2, audioTestState: "failed", audioPassed: false },
    });
  }
}

async function runMidiListen(): Promise<void> {
  // Race the event handler against the timeout subscription so either
  // outcome resolves the listen.
  let resolved = false;
  let timeoutUnlisten: (() => void) | null = null;
  try {
    timeoutUnlisten = await subscribeIpc("ipc.calibration.midi_timeout", () => {
      if (resolved) return;
      resolved = true;
      setState({
        step3: { ...wizardState.step3, probeState: "timeout", secondsLeft: 0 },
      });
    });
    const ev = await sendIpcRequest(
      "ipc.calibration.start_midi_listen",
      { timeout_s: 10 },
      "ipc.calibration.midi_event",
      12_000, // 10s timeout + 2s buffer
    );
    if (resolved) return;
    resolved = true;
    const label = (ev as { payload: { control_label: string } }).payload.control_label;
    setState({
      step3: {
        ...wizardState.step3,
        probeState: "caught",
        caughtLabel: label,
      },
    });
    // Auto-advance after 1s per UI-SPEC §10.
    setTimeout(() => advanceTo("smoke-test"), 1000);
  } catch (err) {
    if (!resolved) {
      console.warn("[step3] midi listen failed:", err);
      setState({
        step3: { ...wizardState.step3, probeState: "timeout", secondsLeft: 0 },
      });
    }
  } finally {
    if (timeoutUnlisten) timeoutUnlisten();
  }
}

async function runSmokeTest(): Promise<void> {
  // Subscribe to the started event for the loading state; await the
  // done event with a longer timeout (cascade greeting ~5-8s).
  let unsubStarted: (() => void) | null = null;
  try {
    unsubStarted = await subscribeIpc("ipc.calibration.smoke_test_started", () => {
      console.log("[smoke-test] cascade greeting started");
    });
    await sendIpcRequest(
      "ipc.calibration.smoke_test",
      { template: "HYPE_BEGINNER" },
      "ipc.calibration.smoke_test_done",
      30_000,
    );
    setState({
      smokeTest: { ...wizardState.smokeTest, greetingPlayed: true },
    });
  } catch (err) {
    console.warn("[smoke-test] failed:", err);
    // Even on failure, enable the Open vibemix CTA — the user might want
    // to proceed past a borked greeting; their dev rig still works.
    setState({
      smokeTest: { ...wizardState.smokeTest, greetingPlayed: true },
    });
  } finally {
    if (unsubStarted) unsubStarted();
  }
}

async function completeWizard(): Promise<void> {
  const payload = {
    output_device_id: wizardState.step2.selectedDeviceId,
    controller_profile:
      wizardState.step3.detectedController?.name ?? "generic",
    target_window_id: null as string | null,
  };
  try {
    await emitIpc("ipc.wizard.done", payload);
    await invoke("write_first_run_state", {
      state: {
        first_run_completed: true,
        calibrated_at: new Date().toISOString(),
        output_device_id: payload.output_device_id,
        controller_profile: payload.controller_profile,
        target_dj_app_hint: wizardState.step2.detectedDjApp?.appName ?? null,
        target_window_id: payload.target_window_id,
        blackhole_install_seen: wizardState.step2.blackHoleBannerPostClick,
      },
    });
  } catch (err) {
    // Without surfacing this, the wizard advances to "done" but the
    // first_run_completed flag isn't persisted → wizard silently
    // re-opens on next launch. Show an inline retry instead of
    // looping forever.
    console.warn("[wizard] completion write failed:", err);
    const detail = err instanceof Error ? err.message : String(err);
    const retry = window.confirm(
      `Setup couldn't be saved (${detail}).\n\nRetry now? Cancel to continue ` +
      `without saving — vibemix will re-open the wizard on next launch.`,
    );
    if (retry) {
      await completeWizard();
      return;
    }
  }
  setState({ currentStep: "done" });
}

// ---------------------------------------------------------------------------
// Status bar subscription — drives the 4 LED dots from ipc.status.tick.
// ---------------------------------------------------------------------------

let statusBarSubscribed = false;

export async function subscribeStatusBar(): Promise<void> {
  if (statusBarSubscribed) return;
  statusBarSubscribed = true;
  await subscribeIpc("ipc.status.tick", (msg) => {
    const payload = (msg as { payload: { livekit: string; gemini: string; midi: number | null; screen: string } }).payload;
    // The status tick fires at 1Hz. Routing it through setState() would
    // call rerender() → renderCurrentStep() → replaceChildren on the
    // wizard's primary surface, which restarts the entrance animation
    // every second and visually looks like the page is reloading.
    // Mutate state in place + re-render ONLY the status-bar mount.
    wizardState = {
      ...wizardState,
      statusBar: {
        livekit: payload.livekit as StatusBarProps["livekit"],
        gemini: payload.gemini as StatusBarProps["gemini"],
        midi: payload.midi,
        screen: payload.screen as StatusBarProps["screen"],
      },
    };
    notify();
    const statusMount = document.getElementById("status-bar");
    if (statusMount) {
      statusMount.replaceChildren(StatusBar(wizardState.statusBar));
    }
  });
}

// ---------------------------------------------------------------------------
// Dev surface (DEV-only — main.ts strips in production builds).
// ---------------------------------------------------------------------------

export interface DevSurface {
  advanceTo: (next: WizardStep) => void;
  currentStep: () => WizardStep;
  getState: () => Readonly<WizardState>;
  setState: (patch: Partial<WizardState>) => void;
  fakeMidiEvent: (ev: { label: string }) => void;
  setStatusBar: (status: StatusBarProps) => void;
}

export function getDevSurface(): DevSurface {
  return {
    advanceTo,
    currentStep,
    getState,
    setState: (patch) => setState(patch),
    fakeMidiEvent: (ev) => {
      setState({
        step3: {
          ...wizardState.step3,
          probeState: "caught",
          caughtLabel: ev.label,
        },
      });
      setTimeout(() => advanceTo("smoke-test"), 1000);
    },
    setStatusBar: (status) => setState({ statusBar: status }),
  };
}

export function consumeUrlParam(): void {
  try {
    const u = new URL(window.location.href);
    const step = u.searchParams.get("step") as WizardStep | null;
    if (step && STEP_ORDER.includes(step)) {
      wizardState = { ...wizardState, currentStep: step };
    }
  } catch (_err) {
    // tauri:// URLs may not parse cleanly; ignore.
  }
}
