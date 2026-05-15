/* Phase 33 / Plan 33-05 — Onboarding flow orchestration.
 *
 * Pins three behaviours:
 *   - The flow walks all four steps in canonical order.
 *   - The flow emits a single onboarding.timing event at completion
 *     with per-step durations + totalMs.
 *   - Step skip emits a warning callback with the step name + reason.
 */

import { describe, expect, it } from "vitest";

import {
  ONBOARDING_STEPS,
  OnboardingFlow,
  type StepName,
} from "../onboarding-flow.js";
import { OnboardingStopwatch } from "../onboarding-stopwatch.js";

describe("OnboardingFlow", () => {
  function setup(): {
    flow: OnboardingFlow;
    warnings: Array<{ step: StepName; reason: string }>;
    timingEvents: Array<ReturnType<OnboardingStopwatch["stop"]>>;
    advanceClock: (delta: number) => void;
  } {
    let clock = 0;
    const stopwatch = new OnboardingStopwatch(() => clock);
    const warnings: Array<{ step: StepName; reason: string }> = [];
    const timingEvents: Array<ReturnType<OnboardingStopwatch["stop"]>> = [];
    const flow = new OnboardingFlow(
      {
        onWarning: (step, reason) => warnings.push({ step, reason }),
        onTimingEvent: (event) => timingEvents.push(event),
      },
      stopwatch,
    );
    return {
      flow,
      warnings,
      timingEvents,
      advanceClock: (delta: number) => {
        clock += delta;
      },
    };
  }

  it("test_onboarding_flow_visits_all_four_steps", () => {
    const ctx = setup();
    ctx.flow.start();
    const visited: StepName[] = [];
    for (let i = 0; i < ONBOARDING_STEPS.length; i++) {
      visited.push(ctx.flow.currentStep()!);
      ctx.advanceClock(1000);
      ctx.flow.advance("complete");
    }
    expect(visited).toEqual([...ONBOARDING_STEPS]);
    expect(ctx.flow.currentStep()).toBeNull();
    expect(ctx.flow.completedSteps()).toEqual([...ONBOARDING_STEPS]);
  });

  it("test_onboarding_emits_timing_event_on_completion", () => {
    const ctx = setup();
    ctx.flow.start();
    for (let i = 0; i < ONBOARDING_STEPS.length; i++) {
      ctx.advanceClock(1000);
      ctx.flow.advance("complete");
    }
    expect(ctx.timingEvents).toHaveLength(1);
    const event = ctx.timingEvents[0]!;
    expect(event.totalMs).toBe(4000);
    expect(event.steps).toHaveLength(4);
    expect(event.steps.map((s) => s.name)).toEqual([...ONBOARDING_STEPS]);
    for (const step of event.steps) {
      expect(step.durationMs).toBeGreaterThan(0);
    }
  });

  it("test_onboarding_step_skip_propagates_warning", () => {
    const ctx = setup();
    ctx.flow.start();
    // Step 1: complete normally.
    ctx.advanceClock(500);
    ctx.flow.advance("complete");
    // Step 2 (audio-device): skip with reason.
    ctx.advanceClock(200);
    ctx.flow.advance("skip", "no BlackHole detected, advancing");
    // Remaining steps: complete.
    ctx.advanceClock(800);
    ctx.flow.advance("complete");
    ctx.advanceClock(1000);
    ctx.flow.advance("complete");

    expect(ctx.warnings).toHaveLength(1);
    expect(ctx.warnings[0]!.step).toBe("audio-device");
    expect(ctx.warnings[0]!.reason).toContain("BlackHole");
    expect(ctx.timingEvents).toHaveLength(1);
    expect(ctx.timingEvents[0]!.totalMs).toBe(2500);
  });

  it("rejects advance after flow completion", () => {
    const ctx = setup();
    ctx.flow.start();
    for (let i = 0; i < ONBOARDING_STEPS.length; i++) {
      ctx.flow.advance("complete");
    }
    expect(() => ctx.flow.advance("complete")).toThrow();
  });
});

describe("OnboardingStopwatch", () => {
  it("rejects beginStep before start", () => {
    const sw = new OnboardingStopwatch(() => 0);
    expect(() => sw.beginStep("tcc-grants")).toThrow();
  });

  it("rejects completeStep without prior beginStep", () => {
    const sw = new OnboardingStopwatch(() => 0);
    sw.start();
    expect(() => sw.completeStep("tcc-grants")).toThrow();
  });
});
