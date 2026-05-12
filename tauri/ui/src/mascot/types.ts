/* Phase 13 Plan 04 — Mascot state vocabulary + priority + StateRequest.
 *
 * This file is the canonical contract between:
 *   - state-machine.ts        (consumes MascotState + STATE_CLASS + STATE_PRIORITY)
 *   - renderer.ts             (uses MascotState as the AnimationAction key)
 *   - asset-loader.ts         (binds each MascotState to a {clip, timeScale})
 *   - index.ts                (builds StateRequest from public requestState API)
 *   - Plan 13-06 (WS bridge)  (translates ipc.* envelopes → StateRequest)
 *
 * The vocabulary is LIFTED VERBATIM from 13-CONTEXT.md Area 3 (open-questions
 * resolved 2026-05-12). The priority numbers come from CONTEXT Area 3:
 *   effect (100) > talk (80) > react (60) > dance (40) > explanation (30) > idle (20) > misc (10)
 *
 * Why dataclass-shaped constants instead of enums: TypeScript enums are
 * compiled to bidirectional maps which we don't need; const-asserted unions
 * give exhaustive switch checks AND zero runtime cost. This mirrors Phase 11
 * Wave 0's "no pydantic" pattern at the Python boundary — same discipline.
 */

/**
 * Every state the mascot animation state-machine can be in. Mapped 1:1 to a
 * single AnimationClip (or clip + timeScale override) by the asset loader.
 * Adding a state here REQUIRES adding both a STATE_CLASS entry and a
 * manifest.json `states` label that targets a clip.
 */
export type MascotState =
  // ── Idle pool ────────────────────────────────────────────────────────
  | "idle_breathe"
  | "idle_breathe_slow"
  | "idle_bop_to_beat_mellow"
  | "idle_bop_to_beat_energetic"
  // ── Dance pool ────────────────────────────────────────────────────────
  | "dance_a"
  | "dance_b"
  | "dance_hard"
  | "dance_alt"
  | "dance_alt2"
  // ── Talk pool (interrupt-class) ──────────────────────────────────────
  | "talk_loop"
  | "talk_loop_calm"
  | "talk_loop_energetic"
  // ── React pool (pre-empts dance/idle, NOT talk/effect) ───────────────
  | "react_yes"
  | "react_no"
  | "react_no_alt"
  | "react_surprised"
  | "react_drop"
  | "react_glitch"
  // ── Explanation pool ─────────────────────────────────────────────────
  | "point_explain"
  | "gesture_wide"
  | "gesture_wide_alt"
  // ── Effect (highest priority — masks mood swap, etc.) ────────────────
  | "puff_particle"
  // ── Misc (low priority utilities) ────────────────────────────────────
  | "celebrate"
  | "sleep"
  | "locomotion_walk"
  | "locomotion_run";

/**
 * Class buckets used by the state machine to compare priorities + apply
 * the talk/effect block rule. Every MascotState maps to exactly one class.
 */
export type MascotStateClass =
  | "idle"
  | "dance"
  | "talk"
  | "react"
  | "explanation"
  | "effect"
  | "misc";

/**
 * MascotState → MascotStateClass mapping. Verbatim from 13-CONTEXT.md
 * Area 3. Every state present in the MascotState union MUST appear here —
 * the `Record<MascotState, …>` type guarantees TypeScript catches drift.
 *
 * Note: `celebrate` is classed as "react" rather than "misc" because the
 * UX intent (post-drop / post-ai-reply cheer) is a one-shot reaction, not
 * a low-priority utility. `sleep` is "idle" because it's the deep-idle
 * terminal state (Open Q 5 — 5 min timeout).
 */
export const STATE_CLASS: Record<MascotState, MascotStateClass> = {
  idle_breathe: "idle",
  idle_breathe_slow: "idle",
  idle_bop_to_beat_mellow: "idle",
  idle_bop_to_beat_energetic: "idle",
  dance_a: "dance",
  dance_b: "dance",
  dance_hard: "dance",
  dance_alt: "dance",
  dance_alt2: "dance",
  talk_loop: "talk",
  talk_loop_calm: "talk",
  talk_loop_energetic: "talk",
  react_yes: "react",
  react_no: "react",
  react_no_alt: "react",
  react_surprised: "react",
  react_drop: "react",
  react_glitch: "react",
  point_explain: "explanation",
  gesture_wide: "explanation",
  gesture_wide_alt: "explanation",
  puff_particle: "effect",
  celebrate: "react",
  sleep: "idle",
  locomotion_walk: "misc",
  locomotion_run: "misc",
};

/**
 * Class → priority value. Higher wins. Used by the state machine's
 * planTransition() to enforce:
 *   - talk + effect BLOCK lower-priority requests (idle/dance get denied
 *     while talk_loop is active)
 *   - react/explanation/dance/idle DO NOT block — they yield to anything
 *     with higher priority but never deny incoming requests
 *
 * Numbers are spaced (10 / 20 / 30 / 40 / 60 / 80 / 100) so future classes
 * can slot in without renumbering. Don't mutate at runtime.
 */
export const STATE_PRIORITY: Record<MascotStateClass, number> = {
  effect: 100,
  talk: 80,
  react: 60,
  dance: 40,
  explanation: 30,
  idle: 20,
  misc: 10,
};

/**
 * Trigger reasons. These are the abstract events that can produce a state
 * transition; Plan 13-06 will map ipc.* envelopes to these. Beat-locked
 * entry only kicks in for `track_change` / `drop` / `phase_change` /
 * `mood_swap` style triggers — the state machine itself reads
 * `bpmConfidence + downbeatPhase` to decide, not the trigger label.
 */
export type StateTrigger =
  | "track_change"
  | "drop"
  | "ai_generating_reply"
  | "ai_reply_done"
  | "manual_fire"
  | "phase_change"
  | "mood_swap"
  | "idle_timeout"
  | "boot"
  | "level_pulse";

/**
 * Public request envelope. Callers (Plan 13-06 WS bridge, dev __mascot
 * surface, future settings drawer "preview" button) construct this and
 * hand it to the state machine.
 *
 * Beat-lock fields are optional — if any of bpm / bpmConfidence /
 * downbeatPhase is missing, planTransition falls back to immediate
 * switch. bpmConfidence < 0.6 also falls back to immediate switch
 * (CONTEXT Open Q 4 threshold).
 */
export interface StateRequest {
  /** The MascotState the caller wants to transition into. */
  state: MascotState;
  /** Why this request fired (audit + WS-bus replay debugging). */
  trigger: StateTrigger;
  /** Current detected BPM. Required for beat-locked entry. */
  bpm?: number;
  /** 0..1 BPM confidence. Below 0.6 → immediate switch (CONTEXT Open Q 4). */
  bpmConfidence?: number;
  /** 0..1 fraction-through-current-bar. Required for downbeat scheduling. */
  downbeatPhase?: number;
  /** AnimationMixer.crossFadeTo blend duration in ms. Default 300ms. */
  blendMs?: number;
}
