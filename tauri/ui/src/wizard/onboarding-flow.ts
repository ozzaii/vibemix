/* onboarding-flow.ts — Phase 33 / INSTALL-05.
 *
 * Orchestrator for the first-launch onboarding flow. Chains:
 *   STEP 1 — TCC grants (microphone + screen-recording + optional
 *            accessibility + automation). Backed by 33-01 helpers +
 *            33-02 plugin.
 *   STEP 2 — Audio device pick (already a Phase 11 surface, includes
 *            BlackHole probe from 33-03).
 *   STEP 3 — Controller probe (Phase 23 controller-probe component).
 *   STEP 4 — AI test reaction (smoke-test fixture that emits a single
 *            scripted reaction so the user sees vibemix talk back
 *            before the main session begins).
 *
 * Pure orchestration — the surface is the state machine, not the
 * rendering. Each step has a {complete, skip} disposition; skip
 * propagates a warning that the wizard surfaces as a toast.
 *
 * Stopwatch (onboarding-stopwatch.ts) is the only thing this layer
 * actively manages — every step's start/end timestamp threads through
 * the OnboardingStopwatch instance and the final ``onboarding.timing``
 * event is emitted via the provided ``onEvent`` callback.
 */

import { OnboardingStopwatch, type OnboardingTimingEvent } from "./onboarding-stopwatch.js";

export type StepName =
  | "tcc-grants"
  | "audio-device"
  | "controller-probe"
  | "ai-test-reaction";

export type StepDisposition = "complete" | "skip";

export interface OnboardingFlowCallbacks {
  /** Emits one warning per skipped step. */
  onWarning: (step: StepName, reason: string) => void;
  /** Emits the final timing event when the flow completes. */
  onTimingEvent: (event: OnboardingTimingEvent) => void;
}

export const ONBOARDING_STEPS: ReadonlyArray<StepName> = [
  "tcc-grants",
  "audio-device",
  "controller-probe",
  "ai-test-reaction",
];

export class OnboardingFlow {
  private readonly _stopwatch: OnboardingStopwatch;
  private readonly _cb: OnboardingFlowCallbacks;
  private _index = 0;
  private _completed: StepName[] = [];

  constructor(callbacks: OnboardingFlowCallbacks, stopwatch?: OnboardingStopwatch) {
    this._cb = callbacks;
    this._stopwatch = stopwatch ?? new OnboardingStopwatch();
  }

  /** Begin the flow. Starts the stopwatch and arms STEP 1. */
  start(): void {
    this._index = 0;
    this._completed = [];
    this._stopwatch.start();
    this._stopwatch.beginStep(ONBOARDING_STEPS[0]!);
  }

  /** Current step name; null after the flow completes. */
  currentStep(): StepName | null {
    return this._index < ONBOARDING_STEPS.length
      ? ONBOARDING_STEPS[this._index]!
      : null;
  }

  /** Advance from the current step. ``disposition === "skip"`` emits a
   *  warning via the configured callback; both dispositions advance the
   *  cursor and stopwatch. */
  advance(disposition: StepDisposition, reason?: string): void {
    const current = this.currentStep();
    if (current === null) {
      throw new Error("OnboardingFlow.advance called after flow completion");
    }
    this._stopwatch.completeStep(current);
    this._completed.push(current);
    if (disposition === "skip") {
      this._cb.onWarning(current, reason ?? "step skipped");
    }
    this._index++;
    const next = this.currentStep();
    if (next === null) {
      const event = this._stopwatch.stop();
      this._cb.onTimingEvent(event);
    } else {
      this._stopwatch.beginStep(next);
    }
  }

  /** All step names visited so far (complete OR skipped). */
  completedSteps(): ReadonlyArray<StepName> {
    return this._completed.slice();
  }
}
