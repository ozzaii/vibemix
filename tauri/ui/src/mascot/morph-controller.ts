// SPDX-License-Identifier: Apache-2.0

export type OrganismPose = "mask" | "pill";
export type FocusPhase = "idle" | "dissolving" | "holding" | "reforming";

export interface FocusTarget {
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

export interface MorphSnapshot {
  readonly pose: OrganismPose;
  readonly poseProgress: number;
  readonly fromPose: OrganismPose;
  readonly toPose: OrganismPose;
  readonly focusPhase: FocusPhase;
  readonly focusWeight: number;
  readonly focusTarget: FocusTarget | null;
}

interface PoseTransition {
  from: OrganismPose;
  to: OrganismPose;
  startedAt: number;
  durationMs: number;
}

interface FocusTransition {
  phase: FocusPhase;
  target: FocusTarget;
  startedAt: number;
  durationMs: number;
}

const DEFAULT_MASK_TO_PILL_MS = 600;
const DEFAULT_PILL_TO_MASK_MS = 900;
const DEFAULT_FOCUS_IN_MS = 400;
const DEFAULT_REFORM_MS = 600;

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function smoothstep(value: number): number {
  const t = clamp01(value);
  return t * t * (3 - 2 * t);
}

function transitionProgress(nowMs: number, startedAt: number, durationMs: number): number {
  if (durationMs <= 0) return 1;
  return clamp01((nowMs - startedAt) / durationMs);
}

function nearestPose(transition: PoseTransition, nowMs: number): OrganismPose {
  return transitionProgress(nowMs, transition.startedAt, transition.durationMs) >= 0.5
    ? transition.to
    : transition.from;
}

export class MorphController {
  private pose: OrganismPose = "mask";
  private poseTransition: PoseTransition | null = null;
  private focusTransition: FocusTransition | null = null;
  private focusTarget: FocusTarget | null = null;
  private focusPhase: FocusPhase = "idle";

  morphTo(pose: OrganismPose, nowMs: number, durationMs?: number): void {
    const current = this.poseTransition ? nearestPose(this.poseTransition, nowMs) : this.pose;
    this.pose = current;
    this.poseTransition = null;
    if (current === pose) return;
    this.poseTransition = {
      from: current,
      to: pose,
      startedAt: nowMs,
      durationMs:
        durationMs ?? (current === "mask" && pose === "pill"
          ? DEFAULT_MASK_TO_PILL_MS
          : DEFAULT_PILL_TO_MASK_MS),
    };
  }

  focusAt(target: FocusTarget, nowMs: number, durationMs = DEFAULT_FOCUS_IN_MS): void {
    this.focusTarget = target;
    this.focusPhase = "dissolving";
    this.focusTransition = {
      phase: "dissolving",
      target,
      startedAt: nowMs,
      durationMs,
    };
  }

  reform(nowMs: number, durationMs = DEFAULT_REFORM_MS): void {
    if (!this.focusTarget || this.focusPhase === "idle") return;
    this.focusPhase = "reforming";
    this.focusTransition = {
      phase: "reforming",
      target: this.focusTarget,
      startedAt: nowMs,
      durationMs,
    };
  }

  update(nowMs: number): MorphSnapshot {
    let fromPose = this.pose;
    let toPose = this.pose;
    let poseProgress = 0;
    if (this.poseTransition) {
      fromPose = this.poseTransition.from;
      toPose = this.poseTransition.to;
      poseProgress = smoothstep(
        transitionProgress(nowMs, this.poseTransition.startedAt, this.poseTransition.durationMs),
      );
      if (poseProgress >= 1) {
        this.pose = this.poseTransition.to;
        this.poseTransition = null;
        fromPose = this.pose;
        toPose = this.pose;
        poseProgress = 0;
      }
    }

    let focusWeight = this.focusPhase === "holding" ? 1 : 0;
    if (this.focusTransition) {
      const t = smoothstep(
        transitionProgress(nowMs, this.focusTransition.startedAt, this.focusTransition.durationMs),
      );
      if (this.focusTransition.phase === "dissolving") {
        focusWeight = t;
        if (t >= 1) {
          this.focusPhase = "holding";
          this.focusTransition = null;
          focusWeight = 1;
        }
      } else if (this.focusTransition.phase === "reforming") {
        focusWeight = 1 - t;
        if (t >= 1) {
          this.focusPhase = "idle";
          this.focusTransition = null;
          this.focusTarget = null;
          focusWeight = 0;
        }
      }
    }

    return {
      pose: this.pose,
      poseProgress,
      fromPose,
      toPose,
      focusPhase: this.focusPhase,
      focusWeight,
      focusTarget: this.focusTarget,
    };
  }
}
