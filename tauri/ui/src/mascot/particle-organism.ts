// SPDX-License-Identifier: Apache-2.0

import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  Points,
  Scene,
  ShaderMaterial,
  Vector3,
} from "three";

import { MorphController, type FocusTarget } from "./morph-controller.js";

export interface OrganismSignals {
  readonly voice?: number;
  readonly beatPhase?: number;
  readonly bpmConfidence?: number;
  /** Signed MIDI CC delta of the EQ knob being taught (-127..127). Drives
   *  the tangential swirl near the focus target. Idle frames omit it. */
  readonly eqKnobDelta?: number;
}

interface OrganismUniforms {
  readonly uTime: { value: number };
  readonly uVoice: { value: number };
  readonly uBeatPulse: { value: number };
  readonly uPoseProgress: { value: number };
  readonly uFocusWeight: { value: number };
  readonly uFocusTarget: { value: Vector3 };
  readonly uTangentialBias: { value: number };
}

const SIM_SIDE = 128;
const PARTICLE_COUNT = SIM_SIDE * SIM_SIDE;
const MAX_DELTA_SECONDS = 0.033;
/** Z of the face plane; exported so the focus layer can pin screen→world
 *  unprojections onto the same plane the mask lives on. */
export const FACE_PLANE_Z = 0.72;
/** Y centroid of the mask; the focus layer's self-focus fallback target. */
export const MASK_CENTER_Y = 1.50;
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
/** Per-frame decay of the EQ-knob swirl (tangential bias). A real CC delta
 *  re-energises it; idle frames decay it to zero so there is no un-caused
 *  swirl (grounding contract). */
const KNOB_SWIRL_DECAY = 0.88;

const VERTEX_SHADER = `
uniform float uTime;
uniform float uVoice;
uniform float uBeatPulse;
uniform float uPoseProgress;
uniform float uFocusWeight;
uniform vec3 uFocusTarget;
uniform float uTangentialBias;
uniform float uPointScale;

attribute vec3 aMask;
attribute vec3 aPill;
attribute float aSeed;
attribute float aFocusAffinity;

varying float vAlpha;
varying float vHeat;

float hash(float n) {
  return fract(sin(n) * 43758.5453123);
}

void main() {
  vec3 base = mix(aMask, aPill, uPoseProgress);
  float phase = aSeed * 6.28318530718;
  float lane = sin(uTime * 0.34 + phase) + cos(uTime * 0.21 + phase * 1.71);
  float voiceBreath = smoothstep(0.02, 0.22, uVoice);
  vec3 tangent = normalize(vec3(
    sin(phase * 1.31 + uTime * 0.13),
    cos(phase * 1.73 + uTime * 0.11),
    sin(phase * 0.71)
  ));
  vec3 drift = tangent * lane * (0.012 + voiceBreath * 0.038);
  vec3 radial = normalize(vec3(base.xy, 0.16));
  vec3 beat = radial * uBeatPulse * (0.018 + hash(aSeed) * 0.034);
  vec3 pos = base + drift + beat;

  float focus = uFocusWeight * aFocusAffinity;
  vec3 focusLane = vec3(
    sin(phase + uTime * 2.0) * 0.045,
    cos(phase * 0.7 + uTime * 1.6) * 0.045,
    sin(phase * 1.9) * 0.018
  );
  vec3 focused = uFocusTarget + focusLane;
  // EQ-knob swirl: a tangential (perpendicular) velocity component around
  // the focus target, signed by the CC delta. Caused only by a real knob
  // move (uTangentialBias is decayed to 0 on idle frames), so the swirl
  // never appears un-caused. Strength tracks the focus weight so it is local
  // to the dissolved region, not the whole face.
  vec2 toTarget = pos.xy - uFocusTarget.xy;
  vec2 swirlDir = vec2(-toTarget.y, toTarget.x);
  focused.xy += swirlDir * uTangentialBias * 0.12;
  pos = mix(pos, focused, focus);

  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mvPosition;
  gl_PointSize = uPointScale * (1.0 + voiceBreath * 0.7 + uBeatPulse * 0.6) / max(0.7, -mvPosition.z);
  vAlpha = 0.34 + hash(aSeed + 11.0) * 0.44 + voiceBreath * 0.18;
  vHeat = max(uBeatPulse, focus);
}
`;

const FRAGMENT_SHADER = `
precision highp float;

uniform vec3 uBaseColor;
uniform vec3 uHotColor;

varying float vAlpha;
varying float vHeat;

void main() {
  vec2 p = gl_PointCoord - vec2(0.5);
  float d = length(p);
  float core = smoothstep(0.5, 0.08, d);
  if (core <= 0.01) discard;
  vec3 color = mix(uBaseColor, uHotColor, clamp(vHeat, 0.0, 1.0));
  gl_FragColor = vec4(color * (0.52 + vHeat * 1.45), core * vAlpha);
}
`;

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

function seeded(index: number): number {
  const x = Math.sin(index * 12.9898 + 78.233) * 43758.5453;
  return x - Math.floor(x);
}

function setTriplet(target: Float32Array, index: number, x: number, y: number, z: number): void {
  const i3 = index * 3;
  target[i3] = x;
  target[i3 + 1] = y;
  target[i3 + 2] = z;
}

function maskPoint(index: number): Vector3 {
  const pick = seeded(index);
  const jitter = seeded(index + 19);
  if (pick < 0.14) {
    const side = pick < 0.07 ? -1 : 1;
    const t = jitter * Math.PI * 2;
    return new Vector3(
      side * 0.14 + Math.cos(t) * 0.075,
      MASK_CENTER_Y + 0.10 + Math.sin(t) * 0.028,
      FACE_PLANE_Z + Math.sin(t) * 0.012,
    );
  }
  if (pick < 0.24) {
    const y = MASK_CENTER_Y - 0.12 + jitter * 0.22;
    return new Vector3(
      (seeded(index + 23) - 0.5) * 0.045,
      y,
      FACE_PLANE_Z + (seeded(index + 29) - 0.5) * 0.05,
    );
  }
  if (pick < 0.34) {
    const x = (jitter - 0.5) * 0.28;
    return new Vector3(
      x,
      MASK_CENTER_Y - 0.20 + (seeded(index + 31) - 0.5) * 0.014,
      FACE_PLANE_Z + (seeded(index + 37) - 0.5) * 0.018,
    );
  }

  const r = Math.sqrt(seeded(index + 43));
  const theta = index * GOLDEN_ANGLE;
  const yBias = (seeded(index + 47) - 0.5) * 0.08;
  const x = Math.cos(theta) * r * 0.30;
  const y = MASK_CENTER_Y + Math.sin(theta) * r * 0.34 + yBias * 0.6;
  const taper = 1 - Math.min(0.52, Math.abs(y - MASK_CENTER_Y) * 0.54);
  return new Vector3(
    x * taper,
    y,
    FACE_PLANE_Z + (0.035 * (1 - r)) + (seeded(index + 53) - 0.5) * 0.045,
  );
}

function pillPoint(index: number): Vector3 {
  const u = seeded(index + 101);
  const v = seeded(index + 107);
  const side = u < 0.5 ? -1 : 1;
  const t = v * Math.PI * 2;
  const body = seeded(index + 109);
  if (body < 0.58) {
    return new Vector3(
      (u - 0.5) * 0.78,
      MASK_CENTER_Y + Math.sin(t) * 0.17,
      FACE_PLANE_Z + Math.cos(t) * 0.055,
    );
  }
  return new Vector3(
    side * 0.39 + Math.cos(t) * 0.16,
    MASK_CENTER_Y + Math.sin(t) * 0.16,
    FACE_PLANE_Z + (seeded(index + 113) - 0.5) * 0.08,
  );
}

function buildGeometry(): BufferGeometry {
  const basePositions = new Float32Array(PARTICLE_COUNT * 3);
  const mask = new Float32Array(PARTICLE_COUNT * 3);
  const pill = new Float32Array(PARTICLE_COUNT * 3);
  const seed = new Float32Array(PARTICLE_COUNT);
  const affinity = new Float32Array(PARTICLE_COUNT);

  for (let i = 0; i < PARTICLE_COUNT; i += 1) {
    const m = maskPoint(i);
    const p = pillPoint(i);
    setTriplet(basePositions, i, m.x, m.y, m.z);
    setTriplet(mask, i, m.x, m.y, m.z);
    setTriplet(pill, i, p.x, p.y, p.z);
    seed[i] = seeded(i + 5);
    affinity[i] = 0.25 + seeded(i + 7) * 0.75;
  }

  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(basePositions, 3));
  geometry.setAttribute("aMask", new BufferAttribute(mask, 3));
  geometry.setAttribute("aPill", new BufferAttribute(pill, 3));
  geometry.setAttribute("aSeed", new BufferAttribute(seed, 1));
  geometry.setAttribute("aFocusAffinity", new BufferAttribute(affinity, 1));
  return geometry;
}

export class ParticleOrganism {
  private readonly geometry: BufferGeometry;
  private readonly material: ShaderMaterial;
  private readonly points: Points;
  private readonly morph = new MorphController();
  private elapsed = 0;
  private voice = 0;
  private beatPulse = 0;
  private previousBeatPhase: number | null = null;
  /** Tangential swirl bias from the taught EQ knob; re-energised by a real
   *  CC delta, decayed every frame so idle shows no swirl. */
  private knobSwirl = 0;
  private disposed = false;

  constructor(private readonly scene: Scene) {
    this.geometry = buildGeometry();
    this.material = new ShaderMaterial({
      transparent: true,
      depthTest: false,
      depthWrite: false,
      blending: AdditiveBlending,
      vertexShader: VERTEX_SHADER,
      fragmentShader: FRAGMENT_SHADER,
      uniforms: {
        uTime: { value: 0 },
        uVoice: { value: 0 },
        uBeatPulse: { value: 0 },
        uPoseProgress: { value: 0 },
        uFocusWeight: { value: 0 },
        uFocusTarget: { value: new Vector3(0, MASK_CENTER_Y, FACE_PLANE_Z) },
        uTangentialBias: { value: 0 },
        uPointScale: { value: 6.2 },
        uBaseColor: { value: new Color(1.0, 0.65, 0.87) },
        uHotColor: { value: new Color(1.0, 0.86, 0.48) },
      },
    });
    this.points = new Points(this.geometry, this.material);
    this.points.frustumCulled = false;
    this.points.renderOrder = 1000;
    this.scene.add(this.points);
  }

  enableBloomLayer(layer: number): void {
    this.points.layers.enable(layer);
  }

  setSignals(signals: OrganismSignals): void {
    if (this.disposed) return;
    if (typeof signals.voice === "number") {
      this.voice = this.voice * 0.82 + clamp01(signals.voice) * 0.18;
    }
    if (
      typeof signals.beatPhase === "number" &&
      typeof signals.bpmConfidence === "number" &&
      signals.bpmConfidence > 0.6
    ) {
      const phase = signals.beatPhase;
      if (this.previousBeatPhase !== null && this.previousBeatPhase > 0.85 && phase < 0.15) {
        this.beatPulse = 1;
      }
      this.previousBeatPhase = phase;
    }
    if (typeof signals.eqKnobDelta === "number" && signals.eqKnobDelta !== 0) {
      this.setKnobSwirl(signals.eqKnobDelta);
    }
  }

  /** Re-energise the EQ-knob swirl from a real CC delta. The sign sets the
   *  swirl direction (knob turn direction); magnitude is normalised by the
   *  127-tick CC range and clamped. The learn window separately rotates the
   *  SVG `.knob-indicator` needle by `angleDeg = (value / 127) * 270 - 135`
   *  (DDJ-FLX4 unipolar EQ knobs sweep +/-135 from noon) — that SVG needle
   *  element is a design dependency, not added here. */
  setKnobSwirl(knobDelta: number): void {
    if (this.disposed) return;
    const signed = Math.max(-1, Math.min(1, knobDelta / 127));
    // Bias toward the strongest recent move rather than averaging, so a
    // sharp turn reads as a sharp swirl.
    if (Math.abs(signed) >= Math.abs(this.knobSwirl)) {
      this.knobSwirl = signed;
    }
  }

  morphToPill(nowMs: number): void {
    this.morph.morphTo("pill", nowMs);
  }

  morphToMask(nowMs: number): void {
    this.morph.morphTo("mask", nowMs);
  }

  focusAt(target: FocusTarget, nowMs: number): void {
    this.morph.focusAt(target, nowMs);
  }

  reform(nowMs: number): void {
    this.morph.reform(nowMs);
  }

  tick(deltaSeconds: number, nowMs: number = performance.now()): void {
    if (this.disposed) return;
    const dt = Math.min(MAX_DELTA_SECONDS, Math.max(0, deltaSeconds));
    this.elapsed += dt;
    this.beatPulse *= 0.85;
    this.knobSwirl *= KNOB_SWIRL_DECAY;
    const snapshot = this.morph.update(nowMs);
    const target = snapshot.focusTarget ?? { x: 0, y: MASK_CENTER_Y, z: FACE_PLANE_Z };
    let poseProgress = snapshot.pose === "pill" ? 1 : 0;
    if (snapshot.fromPose !== snapshot.toPose) {
      poseProgress =
        snapshot.toPose === "pill" ? snapshot.poseProgress : 1 - snapshot.poseProgress;
    }

    const uniforms = this.material.uniforms as unknown as OrganismUniforms;
    uniforms.uTime.value = this.elapsed;
    uniforms.uVoice.value = this.voice;
    uniforms.uBeatPulse.value = this.beatPulse;
    uniforms.uPoseProgress.value = poseProgress;
    uniforms.uFocusWeight.value = snapshot.focusWeight;
    uniforms.uFocusTarget.value.set(target.x, target.y, target.z);
    uniforms.uTangentialBias.value = this.knobSwirl;
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.scene.remove(this.points);
    this.geometry.dispose();
    this.material.dispose();
  }
}
