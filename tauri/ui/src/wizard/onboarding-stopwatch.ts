/* onboarding-stopwatch.ts — Phase 33 / INSTALL-05.
 *
 * Per-step + total stopwatch for the first-launch onboarding flow. The
 * wall-clock target is ≤ 60s from icon-tap to first AI reaction
 * (validated on real hardware as Kaan-action — this surface only
 * captures the measurement).
 *
 * The stopwatch uses ``performance.now()`` so it is monotonic across
 * vsync, and emits an ``onboarding.timing`` IPC-style event at
 * completion. The event shape:
 *
 *   {
 *     totalMs: number,             // wall-clock from start() to stop()
 *     steps: Array<{               // ordered by completion timestamp
 *       name: string,
 *       startedAtMs: number,       // since stopwatch.start()
 *       completedAtMs: number,
 *       durationMs: number
 *     }>
 *   }
 *
 * Pure helper — no Tauri IPC binding here. The wizard router pipes the
 * event into the existing emit channel (`ipc.session.event` or a
 * dedicated `onboarding.timing` topic, decided at integration time).
 */

export interface StepTiming {
  name: string;
  startedAtMs: number;
  completedAtMs: number;
  durationMs: number;
}

export interface OnboardingTimingEvent {
  totalMs: number;
  steps: StepTiming[];
}

type Now = () => number;

export class OnboardingStopwatch {
  private readonly _now: Now;
  private _startedAt: number | null = null;
  private _stoppedAt: number | null = null;
  private readonly _activeSteps: Map<string, number> = new Map();
  private readonly _steps: StepTiming[] = [];

  constructor(now: Now = () => performance.now()) {
    this._now = now;
  }

  /** Begin measuring the entire onboarding session. */
  start(): void {
    this._startedAt = this._now();
    this._stoppedAt = null;
    this._activeSteps.clear();
    this._steps.length = 0;
  }

  /** Mark a step started. ``performance.now()`` since start() is tracked. */
  beginStep(name: string): void {
    if (this._startedAt === null) {
      throw new Error("OnboardingStopwatch.beginStep called before start()");
    }
    this._activeSteps.set(name, this._now() - this._startedAt);
  }

  /** Mark a step completed. The pair (begin/end) becomes a StepTiming. */
  completeStep(name: string): void {
    if (this._startedAt === null) {
      throw new Error("OnboardingStopwatch.completeStep called before start()");
    }
    const startedAt = this._activeSteps.get(name);
    if (startedAt === undefined) {
      throw new Error(`OnboardingStopwatch: completeStep('${name}') without beginStep`);
    }
    this._activeSteps.delete(name);
    const completedAt = this._now() - this._startedAt;
    this._steps.push({
      name,
      startedAtMs: startedAt,
      completedAtMs: completedAt,
      durationMs: completedAt - startedAt,
    });
  }

  /** Close the session and return the timing event. */
  stop(): OnboardingTimingEvent {
    if (this._startedAt === null) {
      throw new Error("OnboardingStopwatch.stop called before start()");
    }
    this._stoppedAt = this._now();
    return {
      totalMs: this._stoppedAt - this._startedAt,
      steps: this._steps.slice(),
    };
  }
}
