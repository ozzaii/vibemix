/* router.ts — wizard state machine + step transitions (UI-SPEC §Motion §step).
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
 *   - Launch mount -> library_setup_candidates + ipc.library.import.
 *   - Legacy smoke-test mount -> ipc.calibration.smoke_test (timeout 30s).
 *   - Wizard done → emitIpc ipc.wizard.done + invoke write_first_run_state.
 *
 * State transitions ride the room's rise language: 250ms (--motion-step)
 * on var(--ease-brand), translateY — same vocabulary as vmx-intro-rise —
 * and skip entirely under prefers-reduced-motion (inline styles bypass
 * media queries, so the router gates itself).
 */

import { invoke } from "@tauri-apps/api/core";

import { emitIpc, sendIpcRequest, subscribeIpc } from "../ipc/client.js";
import {
  libraryImportFromAction,
  libraryImportOutcome,
  libraryModels,
  libraryStats,
  onLibraryImportProgress,
  onModelProgress,
  type LibrarySetupCandidate,
} from "../library/api.js";
import { registerShortcuts } from "../session/shortcuts.js";
import { renderConfirmDialog } from "../settings/components/confirm-dialog.js";
import { listenTauri } from "../tauri-runtime.js";
import { registerStyle } from "./components/_style-registry.js";
import { StatusBar } from "./components/status-bar.js";
import type { StatusBarProps } from "./components/status-bar.js";
import { StepIndicator } from "./components/step-indicator.js";
import { renderSmokeTest, type SmokeTestState } from "./smoke-test.js";
import { renderStep0Intro } from "./step0-intro.js";
import { renderStep1, type Step1State } from "./step1-permissions.js";
import {
  renderStepProfileConsent,
  type ProfileConsentState,
} from "./step-profile-consent.js";
import {
  renderStepTelemetryConsent,
  type TelemetryConsentState,
} from "./step-telemetry-consent.js";
import {
  renderStepSkillLevel,
  type SkillLevelState,
} from "./step-skill-level.js";
import {
  renderStepLibraryFeed,
  voiceModelReadoutText,
  type LibraryFeedState,
  type VoiceModelState,
} from "./step-library-feed.js";
import { createStepDriverFetch } from "./step-driver-fetch.js";
import { createStepForewarning } from "./step-forewarning.js";

export type WizardStep =
  | "intro"
  | "permissions"
  | "library-feed"
  | "skill-level"
  // Phase 49 — new step types for the one-click install chain.
  // Registered as types here; the render-switch below routes them.
  // Full integration into the step-strip ordering is plan-49-04 (Inno
  // Setup + DMG firstrun hook ties them to install lifecycle).
  | "forewarning"
  | "driver-fetch"
  | "format-check"
  | "profile-consent"
  | "telemetry-consent"
  | "smoke-test"
  | "done";

export interface WizardState {
  currentStep: WizardStep;
  step1: Step1State;
  skillLevel: SkillLevelState;
  libraryFeed: LibraryFeedState;
  voiceModel: VoiceModelState;
  profileConsent: ProfileConsentState;
  telemetryConsent: TelemetryConsentState;
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
    screenSettingsOpened: false,
  },
  skillLevel: {
    // Quick 260529-ifq — pre-select "intermediate" (the runtime default
    // VIBEMIX_SKILL_LEVEL). Continue is always armed; the step is
    // non-blocking, the user picks their actual level explicitly.
    skill: "intermediate",
  },
  libraryFeed: {
    status: "loading",
    candidates: [],
    indexed: 0,
  },
  voiceModel: { status: "idle", downloaded: 0, size: 0 },
  profileConsent: {
    // PROFILE-05 default-OFF — non-negotiable. The toggle MUST start
    // unchecked; the user opts in explicitly.
    consent: false,
  },
  telemetryConsent: {
    // Phase 34 / SEC-08 (Pitfall P67) — default-OFF, non-negotiable.
    // The "Don't share" radio is the default-selected option; this
    // field's value mirrors that radio's state.
    consent: false,
  },
  smokeTest: {
    greetingPlayed: false,
    failed: false,
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

const STEP_ORDER: WizardStep[] = [
  "permissions",
  // Audit B-audio-firstrun (2026-06-10): the Phase-49 BlackHole install chain
  // was typed + built but never advanced into — a truly-fresh Mac completed
  // the wizard, then the live sidecar exited 3 (MasterCaptureNotFound) before
  // the ws bus served, landing on a crash banner that tells a DJ to brew.
  // The chain now sits in the forward path and is SKIPPED when
  // ipc.calibration.list_devices reports blackhole_present (see
  // advancePastPermissions). format-check stays unwired on purpose:
  // run_audio_config shells a system python3 (a CLT stub on a fresh Mac) and
  // live capture opens the device-native rate + resamples, so a 44.1k
  // BlackHole no longer needs a 48k repair to ship audio.
  "forewarning",
  "driver-fetch",
  "library-feed",
];

const KNOWN_STEPS: WizardStep[] = [
  "intro",
  ...STEP_ORDER,
  "skill-level",
  "profile-consent",
  "telemetry-consent",
  "smoke-test",
  "done",
];

function indexOf(step: WizardStep): number {
  return STEP_ORDER.indexOf(step);
}

function stepStripFor(current: WizardStep): HTMLElement {
  // forewarning + driver-fetch are one strip stop ("audio") — the consent
  // card and the install rows are two beats of the same step.
  const effective: WizardStep =
    current === "forewarning" ? "driver-fetch" : current;
  const idx = indexOf(effective);
  const stepsConfig: Array<{ id: WizardStep; label: string }> = [
    { id: "permissions", label: "permissions" },
    { id: "driver-fetch", label: "audio" },
    { id: "library-feed", label: "music" },
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
      if (current === "smoke-test" || current === "done") {
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

/** Inline styles bypass CSS media queries, so the router gates its own
 *  step transition on the user's motion preference. */
function prefersReducedMotion(): boolean {
  return (
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

export function advanceTo(next: WizardStep): void {
  if (next === wizardState.currentStep) return;
  const primaryMount = document.getElementById("wizard-primary");
  if (primaryMount?.firstElementChild && !prefersReducedMotion()) {
    // Exit on the room's rise language (the reverse of vmx-intro-rise) —
    // the old lateral slide was a foreign move in a vertical room.
    const child = primaryMount.firstElementChild as HTMLElement;
    child.style.transition =
      "opacity var(--motion-step) var(--ease-brand), transform var(--motion-step) var(--ease-brand)";
    child.style.opacity = "0";
    child.style.transform = "translateY(-8px)";
    setTimeout(() => {
      setState({ currentStep: next });
    }, 250);
  } else {
    setState({ currentStep: next });
  }
}

/** Walk the wizard one step backward. Intro has no back (it's the first
 *  surface a user sees). Library-feed goes back to permissions (the
 *  collapsed forward path is intro → permissions → library-feed). Wired to
 *  the per-step `[ ← Back ]` button + the `esc` / `cmd+[` shortcut.
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
    case "forewarning":
      advanceTo("permissions");
      return;
    case "driver-fetch":
      advanceTo("forewarning");
      return;
    case "library-feed":
      advanceTo("permissions");
      return;
    case "skill-level":
      // skill-level is no longer in the forward path (folded into
      // library-feed); only reachable via ?step=. Back returns to launch.
      advanceTo("library-feed");
      return;
    case "profile-consent":
      advanceTo("skill-level");
      return;
    case "telemetry-consent":
      advanceTo("profile-consent");
      return;
    case "smoke-test":
      advanceTo("telemetry-consent");
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
  if (prefersReducedMotion()) return;
  child.style.opacity = "0";
  child.style.transform = "translateY(8px)";
  child.style.transition =
    "opacity var(--motion-step) var(--ease-brand), transform var(--motion-step) var(--ease-brand)";
  requestAnimationFrame(() => {
    child.style.opacity = "1";
    child.style.transform = "translateY(0)";
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
    // via back(), and launch returns to permissions.
    escape: () => back(),
  });
}

// ---------------------------------------------------------------------------
// Wizard chrome clock — the titlebar's mono readout shipped as a dead "00:00"
// through the whole first run (the first fake LED a new user saw). Mirror the
// shell chrome's 1s HH:MM ticker so the instrument tells the truth from boot.
// ---------------------------------------------------------------------------

let wizardClockTimer: number | null = null;

function ensureWizardClock(): void {
  if (wizardClockTimer !== null) return;
  const clock = document.getElementById("wizard-clock");
  if (!clock) return;
  const tick = (): void => {
    const now = new Date();
    clock.textContent = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  };
  tick();
  wizardClockTimer = globalThis.setInterval(tick, 1000) as unknown as number;
}

// The wizard→shell handoff moment. A bare "loading vibemix…" text node read
// like a crash if the sidecar respawn took seconds; the handoff now speaks the
// room's vocabulary — serif line on the void, one breathing rose dot (the only
// element on screen, so the one-breath law holds).
registerStyle(
  "wizard-done",
  `
  .wizard-done {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--sp-4);
    min-height: 360px;
  }
  .wizard-done__line {
    font-family: var(--type-serif);
    font-size: clamp(26px, 3vw, 34px);
    font-weight: 400;
    line-height: 1.2;
    color: var(--text-primary);
    text-shadow: var(--text-3d);
  }
  .wizard-done__dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--brand);
    box-shadow: 0 0 8px var(--brand-40);
    animation: wizard-done-breathe var(--motion-led-pulse) var(--ease-brand) infinite;
  }
  @keyframes wizard-done-breathe {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.45; }
  }
  @media (prefers-reduced-motion: reduce) {
    .wizard-done__dot { animation: none; }
  }
`,
);

function renderDoneHandoff(): HTMLElement {
  const root = document.createElement("div");
  root.className = "wizard-done";
  const line = document.createElement("div");
  line.className = "wizard-done__line";
  line.textContent = "opening the deck";
  const dot = document.createElement("span");
  dot.className = "wizard-done__dot";
  dot.setAttribute("aria-hidden", "true");
  root.append(line, dot);
  return root;
}

export function renderCurrentStep(): void {
  ensureWizardShortcuts();
  ensureWizardClock();
  // Leaving driver-fetch drops the cached mount so a re-entry re-runs the
  // probe (the companion script's already_installed check keeps it idempotent).
  if (wizardState.currentStep !== "driver-fetch" && driverFetchEl !== null) {
    driverFetchEl = null;
  }
  const stepStripMount = document.getElementById("wizard-step-strip");
  const primaryMount = document.getElementById("wizard-primary");
  const statusMount = document.getElementById("status-bar");

  if (!stepStripMount || !primaryMount || !statusMount) {
    console.warn("[router] wizard DOM mounts missing");
    return;
  }

  // Intro hero + smoke-test both own the full surface, no step strip.
  if (
    wizardState.currentStep === "intro" ||
    wizardState.currentStep === "smoke-test"
  ) {
    stepStripMount.replaceChildren();
  } else {
    stepStripMount.replaceChildren(stepStripFor(wizardState.currentStep));
  }

  // Placeholder fallback guarantees definite assignment for the (type-level
  // non-exhaustive) switch below; overwritten by every handled step.
  let primary: HTMLElement = document.createElement("div");
  switch (wizardState.currentStep) {
    case "intro":
      primary = renderStep0Intro({
        onBegin: () => advanceTo("permissions"),
      });
      break;
    case "permissions":
      primary = renderStep1(wizardState.step1, {
        platform: wizardState.platform,
        onContinue: () => void advancePastPermissions(),
        onBack: () => back(),
        onGrantScreen: () => {
          void invoke("open_screen_recording_settings").catch((err) => {
            console.warn("[step1] open_screen_recording_settings failed:", err);
          });
          setState({
            step1: { ...wizardState.step1, screenSettingsOpened: true },
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
          setState({
            step1: { ...wizardState.step1, screenSettingsOpened: true },
          });
        },
        onOpenMicSettings: () => {
          void invoke("open_microphone_settings").catch(() => {});
        },
        onRestartSidecar: () => {
          void invoke("restart_sidecar").catch((err) => {
            console.warn("[step1] restart_sidecar failed:", err);
          });
        },
      });
      if (!step1PollerStarted) {
        startStep1PermissionPoll();
      }
      break;
    case "library-feed":
      if (!libraryFeedBootStarted) {
        libraryFeedBootStarted = true;
        void refreshLibraryFeedCandidates();
      }
      if (!voiceModelPrefetchStarted) {
        voiceModelPrefetchStarted = true;
        void startVoiceModelPrefetch();
      }
      primary = renderStepLibraryFeed(wizardState.libraryFeed, {
        skill: wizardState.skillLevel.skill,
        voiceModel: wizardState.voiceModel,
        profileConsent: wizardState.profileConsent.consent,
        telemetryConsent: wizardState.telemetryConsent.consent,
        onSelectSkill: (next) =>
          setState({
            skillLevel: { ...wizardState.skillLevel, skill: next },
          }),
        onToggleProfile: (next) =>
          setState({
            profileConsent: { ...wizardState.profileConsent, consent: next },
          }),
        onToggleTelemetry: (next) =>
          setState({
            telemetryConsent: {
              ...wizardState.telemetryConsent,
              consent: next,
            },
          }),
        onRefreshCandidates: () => void refreshLibraryFeedCandidates(true),
        onIndexCandidate: (candidate) => void startLibraryFeedImport(candidate),
        onPickFolder: () => void pickLaunchFolder(),
        onOpenVibemix: () => void finishLaunchStep(),
        onBack: () => back(),
      });
      break;
    case "forewarning":
      primary = createStepForewarning({
        platform: wizardState.platform,
        onContinue: () => advanceTo("driver-fetch"),
        onBack: () => back(),
      });
      break;
    case "driver-fetch":
      // Mount-once cache: createStepDriverFetch fires run_companion_fetch on
      // creation (download + macOS admin-password dialog after the
      // forewarning consent card) — a status-bar or setState rerender must
      // NOT refire the installer.
      if (driverFetchEl === null) {
        driverFetchEl = createStepDriverFetch({
          platform: wizardState.platform,
          onContinue: () => advanceTo("library-feed"),
          onBack: () => back(),
        });
      }
      primary = driverFetchEl;
      break;
    case "skill-level":
      primary = renderStepSkillLevel(wizardState.skillLevel, {
        onContinue: () => {
          // Quick 260529-ifq — fire-and-forget IPC so the sidecar persists
          // the chosen level to config.json BEFORE the wizard exits. The
          // wizard bus does NOT handle ipc.settings.set; this dedicated
          // ipc.wizard.set_skill message is what lands extra["skill"], read
          // at the next cold boot by apply_persona_config_to_env. The live
          // Settings drawer is the full recovery path post-wizard.
          void emitIpc("ipc.wizard.set_skill", {
            skill: wizardState.skillLevel.skill,
          }).catch((err) => {
            // eslint-disable-next-line no-console
            console.warn("[skill-level] set_skill emit failed:", err);
          });
          advanceTo("profile-consent");
        },
        onSelect: (next) =>
          setState({
            skillLevel: { ...wizardState.skillLevel, skill: next },
          }),
        onBack: () => back(),
      });
      break;
    case "profile-consent":
      primary = renderStepProfileConsent(wizardState.profileConsent, {
        onContinue: () => {
          // PROFILE-05 — emit ipc.profile.set_consent so the sidecar
          // persists the toggle to state.json BEFORE the smoke-test
          // mounts. The set_consent call is fire-and-forget (sidecar
          // emits ipc.profile.consent_state ack; UI does not block on
          // it because the toggle state is the source of truth in this
          // moment).
          void emitIpc("ipc.profile.set_consent", {
            consent: wizardState.profileConsent.consent,
          }).catch((err) => {
            // Non-fatal: persistence retry happens via Settings → Profile
            // panel. The user advances even if the IPC hiccup fires.
            // eslint-disable-next-line no-console
            console.warn("[profile-consent] set_consent emit failed:", err);
          });
          advanceTo("telemetry-consent");
        },
        onToggle: (next) =>
          setState({
            profileConsent: { ...wizardState.profileConsent, consent: next },
          }),
        onBack: () => back(),
      });
      break;
    case "telemetry-consent":
      primary = renderStepTelemetryConsent(wizardState.telemetryConsent, {
        onContinue: () => {
          // Phase 34 / SEC-08 — fire-and-forget IPC mirror so the sidecar
          // persists telemetry_consent: bool to state.json BEFORE the
          // smoke-test surface mounts. The handler ack is non-blocking;
          // the radio state is the source of truth in this moment.
          void emitIpc("ipc.telemetry.set_consent", {
            consent: wizardState.telemetryConsent.consent,
          }).catch((err) => {
            // eslint-disable-next-line no-console
            console.warn("[telemetry-consent] set_consent emit failed:", err);
          });
          advanceTo("smoke-test");
        },
        onToggle: (next) =>
          setState({
            telemetryConsent: {
              ...wizardState.telemetryConsent,
              consent: next,
            },
          }),
        onBack: () => back(),
      });
      break;
    case "smoke-test":
      if (!smokeTestStarted) {
        smokeTestStarted = true;
        void runSmokeTest();
      }
      primary = renderSmokeTest(wizardState.smokeTest, {
        onReplay: () => {
          smokeTestStarted = false;
          setState({ smokeTest: { greetingPlayed: false, failed: false } });
        },
        onOpenVibemix: () => {
          void completeWizard();
        },
      });
      break;
    case "done":
      primary = renderDoneHandoff();
      break;
  }

  renderInto(primaryMount, primary);
  statusMount.replaceChildren(StatusBar(wizardState.statusBar));
}

// ---------------------------------------------------------------------------
// Wave 4 — real ipc.* request bodies replacing Wave 3 mocks.
// ---------------------------------------------------------------------------

let step1PollerStarted = false;
let step1PollTimer: number | null = null;
let hasTriedScreenRestart = false;
let screenRestartFocusHandler: (() => void) | null = null;
let libraryFeedBootStarted = false;
let voiceModelPrefetchStarted = false;
let smokeTestStarted = false;
let driverFetchEl: HTMLElement | null = null;

/** Poll ipc.permission.check @1Hz for both kinds while Step 1 is active. */
function startStep1PermissionPoll(): void {
  step1PollerStarted = true;
  if (screenRestartFocusHandler === null) {
    screenRestartFocusHandler = (): void => {
      if (
        wizardState.currentStep === "permissions" &&
        wizardState.platform === "darwin" &&
        wizardState.step1.screenRecording !== "granted" &&
        !hasTriedScreenRestart
      ) {
        hasTriedScreenRestart = true;
        void invoke("restart_sidecar").catch((err) => {
          console.warn(
            "[step1] restart_sidecar (screen-rec refresh) failed:",
            err,
          );
        });
      }
    };
    window.addEventListener("focus", screenRestartFocusHandler);
  }
  const poll = async (): Promise<void> => {
    if (wizardState.currentStep !== "permissions") {
      if (step1PollTimer != null) {
        clearInterval(step1PollTimer);
        step1PollTimer = null;
      }
      if (screenRestartFocusHandler !== null) {
        window.removeEventListener("focus", screenRestartFocusHandler);
        screenRestartFocusHandler = null;
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

/** Audit B-audio-firstrun — the post-permissions fork. A fresh Mac without
 *  BlackHole used to sail through the wizard and then hit the sidecar's
 *  exit-3 crash banner. Probe the sidecar device list (wizard.py
 *  _on_list_devices flags blackhole_present) and only surface the install
 *  chain when the driver is genuinely absent. Probe failure routes INTO the
 *  chain (fail-closed): with the driver present the companion script's own
 *  probe exits "already_installed" in under a second, so the worst case of
 *  a bus hiccup is one extra Continue — never a dead deck.
 *
 *  Windows takes NO driver chain at all: the shipped capture backend is
 *  WASAPI loopback on the default playback device — "no virtual cable
 *  required (BlackHole-equivalent install is the macOS-only tax)"
 *  (_audio_windows.py, docs/windows-setup.md). The old routing walked every
 *  fresh Windows user through a UAC-elevated VB-CABLE kernel-driver install
 *  that nothing in the product consumes. */
async function advancePastPermissions(): Promise<void> {
  if (wizardState.platform !== "darwin") {
    advanceTo("library-feed");
    return;
  }
  try {
    const reply = await sendIpcRequest(
      "ipc.calibration.list_devices",
      {},
      "ipc.calibration.device_list",
      3_000,
    );
    const present = Boolean(
      (reply as { payload: { blackhole_present: boolean } }).payload
        .blackhole_present,
    );
    if (present) {
      advanceTo("library-feed");
      return;
    }
  } catch (err) {
    console.warn("[router] blackhole probe failed:", err);
  }
  advanceTo("forewarning");
}

function libraryFeedStatus(
  indexed: number,
  candidates: LibrarySetupCandidate[],
): LibraryFeedState["status"] {
  if (candidates.length > 0) return "ready";
  return indexed > 0 ? "done" : "empty";
}

async function refreshLibraryFeedCandidates(force = false): Promise<void> {
  if (force) libraryFeedBootStarted = true;
  setState({
    libraryFeed: {
      ...wizardState.libraryFeed,
      status: "loading",
      error: undefined,
    },
  });
  try {
    const stats = await libraryStats();
    const candidates = stats.library_setup_candidates ?? [];
    setState({
      libraryFeed: {
        ...wizardState.libraryFeed,
        status: libraryFeedStatus(stats.indexed, candidates),
        candidates,
        indexed: stats.indexed,
        error: undefined,
      },
    });
  } catch (err) {
    // Raw exception text (module paths, tracebacks) stays in the console;
    // the feed chip speaks the consequence + the recovery.
    console.warn("[wizard] library stats failed:", err);
    setState({
      libraryFeed: {
        ...wizardState.libraryFeed,
        status: "error",
        error: "couldn't read your library status. try again.",
      },
    });
  }
}

async function startLibraryFeedImport(
  candidate: LibrarySetupCandidate,
): Promise<void> {
  setState({
    libraryFeed: {
      ...wizardState.libraryFeed,
      status: "indexing",
      selectedPath: candidate.path,
      progress: undefined,
      error: undefined,
    },
  });

  let unlisten = (): void => {};
  try {
    unlisten = await onLibraryImportProgress((progress) => {
      const terminal =
        progress.cancelled || progress.total <= 0 || progress.done >= progress.total;
      const wipeout = terminal && libraryImportOutcome(progress) === "failed";
      setState({
        libraryFeed: {
          ...wizardState.libraryFeed,
          status: terminal ? (wipeout ? "error" : "done") : "indexing",
          selectedPath: candidate.path,
          progress,
          error: wipeout
            ? progress.failure_reason
              ? `indexing failed: ${progress.failure_reason}`
              : "indexing failed: no tracks were indexed"
            : undefined,
        },
      });
      if (terminal) unlisten();
    });
    const accepted = await libraryImportFromAction(
      candidate.import_action,
      candidate.path,
    );
    if (!accepted) {
      unlisten();
      setState({
        libraryFeed: {
          ...wizardState.libraryFeed,
          status: "error",
          selectedPath: candidate.path,
          error: "desktop bridge is not connected",
        },
      });
    }
  } catch (err) {
    unlisten();
    const message = err instanceof Error ? err.message : String(err);
    setState({
      libraryFeed: {
        ...wizardState.libraryFeed,
        status: "error",
        selectedPath: candidate.path,
        error: message,
      },
    });
  }
}

/** Lane A (2026-06-10) — the ~706MB Chatterbox voice + the CLAP embedder used
 *  to download INSIDE ipc.wizard.done, freezing the app on "loading vibemix…"
 *  for the whole transfer. Kick the existing one-shot installer instead
 *  (Tauri `library_models` command → `vibemix library models --install
 *  required --progress`): the child process belongs to the Tauri PARENT, so
 *  it survives the wizard→live sidecar handoff and resumes via the HF cache
 *  on retry. Progress arrives on the already-built `library://model-progress`
 *  channel. Failure is visible, not fatal — the deck opens with the voice
 *  badge muted and the Viber models card as recovery. */
async function startVoiceModelPrefetch(): Promise<void> {
  paintVoiceModel({ ...wizardState.voiceModel, status: "downloading" });
  let unlisten: () => void = () => {};
  try {
    unlisten = await onModelProgress((p) => {
      if (p.id !== "chatterbox") return; // voice dominates the payload
      paintVoiceModel({
        status: p.status === "error" ? "error" : "downloading",
        downloaded: p.downloaded,
        size: p.size,
        detail: p.error,
      });
    });
    const result = await libraryModels("required");
    const ok = result.install ? result.install.ok : result.required_ready;
    paintVoiceModel({
      ...wizardState.voiceModel,
      status: ok ? "ready" : "error",
    });
  } catch (err) {
    paintVoiceModel({
      ...wizardState.voiceModel,
      status: "error",
      detail: err instanceof Error ? err.message : String(err),
    });
  } finally {
    unlisten();
  }
}

/** Update the voiceModel slice WITHOUT re-rendering the whole step — a full
 *  setState() rerender restarts the step entrance animation on every 8MB
 *  progress chunk (same hazard the status-bar subscriber documents). The
 *  readout element repaints in place; the next natural render reads state. */
function paintVoiceModel(next: VoiceModelState): void {
  wizardState = { ...wizardState, voiceModel: next };
  notify();
  const el = document.getElementById("voice-model-readout");
  if (el) {
    el.textContent = voiceModelReadoutText(next);
    el.dataset.status = next.status;
  }
}

function firstDialogPath(selection: unknown): string | null {
  if (typeof selection === "string" && selection.length > 0) return selection;
  if (Array.isArray(selection)) {
    const first = selection.find(
      (item): item is string => typeof item === "string" && item.length > 0,
    );
    return first ?? null;
  }
  return null;
}

async function pickLaunchFolder(): Promise<void> {
  let sourcePath: string | null = null;
  try {
    const { open } = await import("@tauri-apps/plugin-dialog");
    const selection = await open({
      title: "Choose music folder",
      directory: true,
      multiple: false,
    });
    sourcePath = firstDialogPath(selection);
  } catch (err) {
    console.warn("[wizard] folder picker failed:", err);
    setState({
      libraryFeed: {
        ...wizardState.libraryFeed,
        status: "error",
        error: "couldn't open the folder picker. try again.",
      },
    });
    return;
  }
  if (!sourcePath) return;
  await startLibraryFeedImport({
    kind: "music_folder",
    path: sourcePath,
    import_action: {
      type: "ipc.library.import",
      payload: { path: sourcePath },
    },
  });
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
      smokeTest: { greetingPlayed: true, failed: false },
    });
  } catch (err) {
    console.warn("[smoke-test] failed:", err);
    // No dead-end: the Open vibemix CTA stays armed as the escape hatch —
    // but the surface tells the truth (failed renders the fault branch with
    // retry copy, never the READY TO PLAY celebration).
    setState({
      smokeTest: { greetingPlayed: true, failed: true },
    });
  } finally {
    if (unsubStarted) unsubStarted();
  }
}

async function persistLaunchPreferences(): Promise<void> {
  await Promise.allSettled([
    emitIpc("ipc.wizard.set_skill", {
      skill: wizardState.skillLevel.skill,
    }),
    emitIpc("ipc.profile.set_consent", {
      consent: wizardState.profileConsent.consent,
    }),
    emitIpc("ipc.telemetry.set_consent", {
      consent: wizardState.telemetryConsent.consent,
    }),
  ]);
}

/** Fresh-user safety net: a user who never clicked "Index this" but had a
 *  library source auto-detected would otherwise open the deck with an empty
 *  library — the deck stays bare and the what-next pill is dark. The wizard
 *  sidecar QUEUES the source as a pending-import marker (it cannot survive a
 *  real CLAP embed — ipc.wizard.done kills the process), and the live sidecar
 *  runs the real import on its first boot with progress on the deck. The
 *  emit is awaited by finishLaunchStep so the ipc.library.import frame is
 *  SENT before ipc.wizard.done — both ride one ws connection (FIFO), so the
 *  marker is persisted before the wizard sidecar exits. No-op when tracks
 *  already exist / an import ack already landed / nothing was detected. */
function maybeAutoIngestLibrary(): Promise<void> {
  const feed = wizardState.libraryFeed;
  if (feed.indexed > 0 || feed.status === "indexing" || feed.status === "done") {
    return Promise.resolve();
  }
  const candidate = feed.candidates[0];
  if (!candidate) return Promise.resolve();
  return startLibraryFeedImport(candidate);
}

async function finishLaunchStep(): Promise<void> {
  await maybeAutoIngestLibrary();
  await persistLaunchPreferences();
  await completeWizard();
}

// ---------------------------------------------------------------------------
// Wizard → live handoff. After a clean wizard exit the Rust watchdog respawns
// the sidecar WITHOUT --wizard and emits sidecar-state
// {state:"restarting", reason:"wizard-handoff"} (sidecar.rs). main.ts decides
// the surface ONCE per page load, so the webview must reload for boot() to
// re-read first_run_completed=true and mount the shell app in this window —
// without this the user parks on the dead "loading vibemix…" placeholder.
// ---------------------------------------------------------------------------

/** Test seam — jsdom's window.location.reload is not stubbable. */
export const _handoffHooks = {
  reload(): void {
    window.location.reload();
  },
};

let handoffListenerAttached = false;

/** DEV/test-only: clear the once-guard so each spec can re-arm the listener. */
export function _resetWizardHandoffForTests(): void {
  handoffListenerAttached = false;
}

async function armWizardHandoffReload(): Promise<void> {
  if (handoffListenerAttached) return;
  handoffListenerAttached = true;
  await listenTauri<{ state?: string; reason?: string }>(
    "sidecar-state",
    (event) => {
      const payload = event.payload ?? {};
      if (
        payload.state === "restarting" &&
        payload.reason === "wizard-handoff"
      ) {
        _handoffHooks.reload();
      }
    },
  );
}

async function completeWizard(): Promise<void> {
  // The collapsed wizard no longer carries a device/controller step; output
  // device stays "auto" (empty id) and is set on the deck Settings drawer,
  // and the controller profile defaults to generic (live MIDI auto-detect
  // handles real controllers). FirstRunState.output_device_id is Option<String>
  // so "" deserializes cleanly (config.rs:70).
  const payload = {
    output_device_id: "",
    controller_profile: "generic",
    target_window_id: null as string | null,
  };
  try {
    // Arm the reload listener BEFORE the sidecar can exit — the handoff
    // event must never race past an unattached listener.
    await armWizardHandoffReload();
    // Persist first_run_completed BEFORE ipc.wizard.done: the Rust watchdog
    // re-reads is_first_run() the moment the wizard process exits, and the
    // exit is fast now that wizard-done no longer blocks on a model download.
    await invoke("write_first_run_state", {
      state: {
        first_run_completed: true,
        calibrated_at: new Date().toISOString(),
        output_device_id: payload.output_device_id,
        controller_profile: payload.controller_profile,
        target_dj_app_hint: null,
        target_window_id: payload.target_window_id,
        blackhole_install_seen: false,
      },
    });
    await emitIpc("ipc.wizard.done", payload);
  } catch (err) {
    // Without surfacing this, the wizard advances to "done" but the
    // first_run_completed flag isn't persisted → wizard silently
    // re-opens on next launch. Surface an in-room retry — the styled
    // confirm dialog, not a platform window.confirm (an OS alert breaking
    // the warm void mid-onboarding). The raw error stays in the console;
    // the user copy names only the consequence + the choice.
    console.warn("[wizard] completion write failed:", err);
    const retry = await new Promise<boolean>((resolve) => {
      const dialog = renderConfirmDialog({
        heading: "SETUP DIDN'T SAVE",
        body: "your setup couldn't be written to disk. retry now, or continue and vibemix will run setup again on next launch.",
        confirmLabel: "RETRY",
        cancelLabel: "CONTINUE ANYWAY",
        variant: "danger",
        onCancel: () => {
          dialog.remove();
          resolve(false);
        },
        onConfirm: () => {
          dialog.remove();
          resolve(true);
        },
      });
      document.body.append(dialog);
    });
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
  setStatusBar: (status: StatusBarProps) => void;
}

export function getDevSurface(): DevSurface {
  return {
    advanceTo,
    currentStep,
    getState,
    setState: (patch) => setState(patch),
    setStatusBar: (status) => setState({ statusBar: status }),
  };
}

export function consumeUrlParam(): void {
  try {
    const u = new URL(window.location.href);
    const step = u.searchParams.get("step") as WizardStep | null;
    if (step && KNOWN_STEPS.includes(step)) {
      wizardState = { ...wizardState, currentStep: step };
    }
  } catch (_err) {
    // tauri:// URLs may not parse cleanly; ignore.
  }
}
