/* router.ts — wizard state machine + slide transitions (UI-SPEC §Motion §step).
 *
 * Wave 3 drives every state via MOCK data + a window.__vibemixDev surface
 * for DevTools manipulation. Wave 4 replaces mocks with real ipc.* requests.
 *
 * State transitions use 250ms ease-in-out (UI-SPEC §Motion Budget cap).
 * Going beyond is a violation — checked by the Phase 14 UI-checker.
 *
 * Mascot corner placeholder + status bar render on every step (the
 * persistent frame). Step strip + primary content swap per step. */

import { StepIndicator } from "./components/step-indicator.js";
import { MascotCorner } from "./components/mascot-corner.js";
import { StatusBar } from "./components/status-bar.js";
import type { StatusBarProps } from "./components/status-bar.js";
import { renderStep1, type Step1State } from "./step1-permissions.js";
import { renderStep2, type Step2State } from "./step2-output-device.js";
import { renderStep3, type Step3State } from "./step3-controller.js";
import { renderSmokeTest, type SmokeTestState } from "./smoke-test.js";

export type WizardStep = "permissions" | "audio" | "controller" | "smoke-test" | "done";

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
  currentStep: "permissions",
  step1: {
    screenRecording: "pending",
    microphone: "pending",
  },
  step2: {
    blackHolePresent: true,
    blackHoleBannerPostClick: false,
    devices: [
      { id: "airpods", name: "AirPods Pro", isHeadphones: true, isAuto: true },
      { id: "builtin", name: "Built-in Output", isSpeaker: true },
      { id: "blackhole2ch", name: "BlackHole 2ch", isSpeaker: true },
    ],
    selectedDeviceId: "airpods",
    audioTestState: "idle",
    audioPassed: false,
    actualRate: 48000,
    detectedDjApp: {
      appName: "djay Pro AI",
      windowTitle: "Deck A · Deck B",
    },
    windowPickerMode: "hint",
    windowSelected: false,
  },
  step3: {
    detectedController: { name: "Pioneer DDJ-FLX4", port: "USB MIDI · port 0" },
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

function setState(patch: Partial<WizardState> | ((s: WizardState) => Partial<WizardState>)): void {
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
        stepIdx < idx ? ("complete" as const) :
        stepIdx === idx ? ("active" as const) :
        ("pending" as const);
      // Override: if currentStep === "smoke-test" mark all 3 complete
      if (current === "smoke-test") {
        return { ...s, state: "complete" as const };
      }
      // Override: respect persisted step1/step2/step3 results so a returning
      // user sees completed steps with checkmarks
      if (i === 0 && wizardState.step1.screenRecording === "granted" && wizardState.step1.microphone === "granted" && idx > 0) {
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
    child.style.transition = "opacity var(--motion-step) ease-in-out, transform var(--motion-step) ease-in-out";
    child.style.opacity = "0";
    child.style.transform = "translateX(-16px)";
    setTimeout(() => {
      setState({ currentStep: next });
    }, 250);
  } else {
    setState({ currentStep: next });
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
  // Enter transition
  child.style.opacity = "0";
  child.style.transform = "translateX(16px)";
  child.style.transition = "opacity var(--motion-step) ease-in-out, transform var(--motion-step) ease-in-out";
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

export function renderCurrentStep(): void {
  const stepStripMount = document.getElementById("wizard-step-strip");
  const primaryMount = document.getElementById("wizard-primary");
  const mascotMount = document.getElementById("mascot-corner");
  const statusMount = document.getElementById("status-bar");

  if (!stepStripMount || !primaryMount || !mascotMount || !statusMount) {
    console.warn("[router] wizard DOM mounts missing");
    return;
  }

  // Step strip — hidden during smoke-test (UI-SPEC: smoke-test is a hero
  // surface; step strip indicates 3-step calibration progress only).
  if (wizardState.currentStep === "smoke-test") {
    stepStripMount.replaceChildren();
  } else {
    stepStripMount.replaceChildren(stepStripFor(wizardState.currentStep));
  }

  // Primary content
  let primary: HTMLElement;
  switch (wizardState.currentStep) {
    case "permissions":
      primary = renderStep1(wizardState.step1, {
        platform: wizardState.platform,
        onContinue: () => advanceTo("audio"),
        onGrantScreen: () =>
          setState({ step1: { ...wizardState.step1, screenRecording: "granted" } }),
        onGrantMic: () =>
          setState({ step1: { ...wizardState.step1, microphone: "granted" } }),
        onOpenScreenSettings: () => console.log("[step1] open screen settings"),
        onOpenMicSettings: () => console.log("[step1] open mic settings"),
      });
      break;
    case "audio":
      primary = renderStep2(wizardState.step2, {
        platform: wizardState.platform,
        onContinue: () => advanceTo("controller"),
        onSelectDevice: (id) =>
          setState({ step2: { ...wizardState.step2, selectedDeviceId: id } }),
        onPlayTest: () => {
          setState({ step2: { ...wizardState.step2, audioTestState: "playing" } });
          // Wave 4 will replace this with the real WAV playback path
          setTimeout(() => {
            const result = (wizardState.step2.audioPassed || wizardState.step2.actualRate === 48000)
              ? "passed"
              : "failed";
            setState({ step2: { ...wizardState.step2, audioTestState: result as Step2State["audioTestState"] } });
          }, 1500);
        },
        onAudioYes: () =>
          setState({
            step2: {
              ...wizardState.step2,
              audioTestState: "passed",
              audioPassed: true,
            },
          }),
        onAudioRetry: () =>
          setState({ step2: { ...wizardState.step2, audioTestState: "idle" } }),
        onOpenInstall: () =>
          setState({ step2: { ...wizardState.step2, blackHoleBannerPostClick: true } }),
        onRecheckBlackHole: () =>
          setState({
            step2: {
              ...wizardState.step2,
              blackHolePresent: true,
              blackHoleBannerPostClick: false,
            },
          }),
        onSelectWindow: () =>
          setState({ step2: { ...wizardState.step2, windowSelected: true } }),
        onPickDifferent: () =>
          setState({ step2: { ...wizardState.step2, windowPickerMode: "enum" } }),
      });
      break;
    case "controller":
      primary = renderStep3(wizardState.step3, {
        onContinue: () => advanceTo("smoke-test"),
        onListenAgain: () =>
          setState({
            step3: {
              ...wizardState.step3,
              probeState: "listening",
              secondsLeft: 10,
              caughtLabel: undefined,
            },
          }),
        onSkip: () => advanceTo("smoke-test"),
      });
      // Wave 3 mock: tick the countdown down. Wave 4 replaces with real
      // MIDI event subscription.
      if (wizardState.step3.probeState === "listening" && (wizardState.step3.secondsLeft ?? 10) > 0) {
        scheduleCountdownTick();
      }
      break;
    case "smoke-test":
      primary = renderSmokeTest(wizardState.smokeTest, {
        onReplay: () => console.log("[smoke-test] replay greeting"),
        onOpenVibemix: () => console.log("[smoke-test] open vibemix"),
      });
      // Wave 3 mock: enable [ Open vibemix → ] after 3s
      if (!wizardState.smokeTest.greetingPlayed) {
        setTimeout(() => {
          setState({ smokeTest: { ...wizardState.smokeTest, greetingPlayed: true } });
        }, 3000);
      }
      break;
    case "done":
      primary = document.createElement("div");
      primary.textContent = "wizard done";
      break;
  }

  renderInto(primaryMount, primary);

  // Mascot corner (UI-SPEC: present on every step)
  mascotMount.replaceChildren(MascotCorner());

  // Status bar
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
      // Use wizardState directly to avoid re-rendering for the timer
      // update — we want the final state change to fire rerender.
      if (countdownTimer != null) {
        clearInterval(countdownTimer);
        countdownTimer = null;
      }
      setState({
        step3: { ...s3, secondsLeft: 0, probeState: "timeout" },
      });
    } else {
      // Don't trigger full re-render every second; mutate in place
      wizardState = { ...wizardState, step3: { ...s3, secondsLeft: next } };
      // Update only the LCD via querySelector to keep DSEG7 ticking
      // without remounting the whole step (which would restart rings).
      const lcd = document.querySelector(".cmp-ctrl-probe__lcd");
      if (lcd) {
        const mm = "00";
        const ss = next.toString().padStart(2, "0");
        lcd.textContent = `${mm}:${ss}`;
      }
    }
  }, 1000);
}

/* Wave 3 dev surface — manually trigger state transitions from DevTools. */
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
      // Auto-advance after 1s per UI-SPEC §10
      setTimeout(() => advanceTo("smoke-test"), 1000);
    },
    setStatusBar: (status) => setState({ statusBar: status }),
  };
}

/* URL param routing for state inspection.
 * Wave 3: `?step=audio` advances to that step at boot.
 * Wave 4 strips this in production builds. */
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
