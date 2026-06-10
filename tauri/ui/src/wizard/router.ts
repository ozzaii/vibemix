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
 *   - Launch mount -> library_setup_candidates + ipc.library.import.
 *   - Legacy smoke-test mount -> ipc.calibration.smoke_test (timeout 30s).
 *   - Wizard done → emitIpc ipc.wizard.done + invoke write_first_run_state.
 *
 * State transitions still use 250ms ease-in-out (UI-SPEC §Motion Budget cap).
 */

import { invoke } from "@tauri-apps/api/core";

import { emitIpc, sendIpcRequest, subscribeIpc } from "../ipc/client.js";
import {
  libraryImportFromAction,
  libraryImportOutcome,
  libraryStats,
  onLibraryImportProgress,
  type LibrarySetupCandidate,
} from "../library/api.js";
import { registerShortcuts } from "../session/shortcuts.js";
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
  type LibraryFeedState,
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
    // via back(), and launch returns to permissions.
    escape: () => back(),
  });
}

export function renderCurrentStep(): void {
  ensureWizardShortcuts();
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
      primary = renderStepLibraryFeed(wizardState.libraryFeed, {
        skill: wizardState.skillLevel.skill,
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

// ---------------------------------------------------------------------------
// Wave 4 — real ipc.* request bodies replacing Wave 3 mocks.
// ---------------------------------------------------------------------------

let step1PollerStarted = false;
let step1PollTimer: number | null = null;
let hasTriedScreenRestart = false;
let screenRestartFocusHandler: (() => void) | null = null;
let libraryFeedBootStarted = false;
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
 *  a bus hiccup is one extra Continue — never a dead deck. Windows rigs
 *  (VB-CABLE, never BlackHole) always take the chain; fetch_drivers.ps1
 *  performs the equivalent already-installed probe. */
async function advancePastPermissions(): Promise<void> {
  if (wizardState.platform === "linux") {
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
    const message = err instanceof Error ? err.message : String(err);
    setState({
      libraryFeed: {
        ...wizardState.libraryFeed,
        status: "error",
        error: message,
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
              ? `indexing failed — ${progress.failure_reason}`
              : "indexing failed — no tracks were indexed"
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
    const message = err instanceof Error ? err.message : String(err);
    setState({
      libraryFeed: {
        ...wizardState.libraryFeed,
        status: "error",
        error: `file picker unavailable: ${message}`,
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
 *  library — the deck stays bare and the what-next pill is dark (the sidecar's
 *  SuggestionService is gated on `deck_library is not None`, which is built
 *  once at session activation from an existing library.pkl). Kick the detected
 *  source off as they open the deck so the index exists for the next
 *  activation — and for this one only if the import finishes before they go
 *  live (the live SuggestionService is not re-built mid-session). Fire-and-
 *  forget: do NOT block wizard completion on a multi-minute CLAP embed. No-op
 *  when tracks already exist / an import is in flight, or when no source was
 *  detected (the user picks a folder later from the deck). */
function maybeAutoIngestLibrary(): void {
  const feed = wizardState.libraryFeed;
  if (feed.indexed > 0 || feed.status === "indexing" || feed.status === "done") {
    return;
  }
  const candidate = feed.candidates[0];
  if (!candidate) return;
  void startLibraryFeedImport(candidate);
}

async function finishLaunchStep(): Promise<void> {
  maybeAutoIngestLibrary();
  await persistLaunchPreferences();
  await completeWizard();
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
    await emitIpc("ipc.wizard.done", payload);
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
  } catch (err) {
    // Without surfacing this, the wizard advances to "done" but the
    // first_run_completed flag isn't persisted → wizard silently
    // re-opens on next launch. Show an inline retry instead of
    // looping forever.
    console.warn("[wizard] completion write failed:", err);
    const detail = err instanceof Error ? err.message : String(err);
    const retry = window.confirm(
      `Setup couldn't be saved (${detail}).\n\nRetry now? Cancel to continue ` +
      `without saving. vibemix will re-open the wizard on next launch.`,
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
