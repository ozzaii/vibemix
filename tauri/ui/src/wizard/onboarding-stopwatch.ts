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

/* Phase 49 Plan 03 — INSTALL_READY emit helper.
 *
 * Wizard step-driver-fetch.ts calls this when the driver-fetch + parallel
 * probes all complete. Emits `audio.probe.install_ready` event with the
 * per-step breakdown + total elapsed ms + auto_install_attempted flag.
 *
 * Payload is consumed by:
 *   - scripts/dist/install_vm_matrix.sh --check-60s (Plan 49-05): asserts
 *     median across fresh-VM matrix ≤ 60000 ms (CI gate).
 *   - tests/dist/test_60s_gate.py: behavioral tests of the gate.
 *
 * IPC contract invariant: this reuses the `audio.probe.*` event family —
 * specifically a NEW event type `audio.probe.install_ready` with the
 * payload below. The base `audio.probe.detected` / `audio.probe.missing` /
 * `audio.probe.cta_fired` event types from v3.0 stay byte-identical. The
 * additive payload field `auto_install_attempted` is also added to those
 * existing event types (Plan 49-03 Task 7 in blackhole_probe.py).
 */

export interface InstallReadyPayload {
  elapsed_ms: number;
  per_step: Record<string, number>;
  auto_install_attempted: boolean;
}

export async function emitInstallReadyEvent(
  perStep: Record<string, number>,
  autoInstallAttempted: boolean,
): Promise<void> {
  const elapsed = Object.values(perStep).reduce((a, b) => a + b, 0);
  const payload: InstallReadyPayload = {
    elapsed_ms: elapsed,
    per_step: perStep,
    auto_install_attempted: autoInstallAttempted,
  };
  try {
    // Lazy-import to avoid a hard dep at module init (test envs without
    // Tauri shouldn't crash on import).
    const { emit } = await import("@tauri-apps/api/event");
    await emit("audio.probe.install_ready", payload);
  } catch {
    // Tauri unavailable (test env) — no-op. The stopwatch readout is
    // still useful even without IPC.
  }
}
