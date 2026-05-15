/* Phase 31 Plan 01 — Crossfade policy (pure function module).
 *
 * Computes the per-transition crossfade timing given the source +
 * destination clip names. Used by the PriorityStack consumer to fill
 * in `fade_in_ms` / `fade_out_ms` defaults consistent with v2.0 Phase
 * 22's empirically-validated values.
 *
 * Purity: no state, no clock reads. Pure function from inputs to a
 * timing record.
 */

/** Layer name passed in for context-sensitive crossfade tuning. */
export type LayerForCrossfade = "base" | "emotion" | "anticipation" | "reaction";

export interface CrossfadeTiming {
  /** Crossfade-in for the new clip (ms). */
  fade_in_ms: number;
  /** Crossfade-out for the previous clip (ms). */
  fade_out_ms: number;
  /** Inter-layer stagger (ms) when multiple transitions fire in the
   *  same frame. Always 100ms per Pitfall P62 — exposed here so
   *  callers don't import the PriorityStack constant. */
  stagger_ms: number;
}

/**
 * Default timings per layer.
 *
 * - base: slow breathy crossfade (300/300) — only used at boot when no
 *         idle clip was previously active.
 * - emotion: medium (200/200) — emotion shifts should feel intentional
 *            but not abrupt.
 * - anticipation: 100/100 — fast prep_* ramp (v2.0 Phase 22 lock).
 * - reaction: 80/120 — sharp entry, gentle exit (v2.0 lk-variant tuning).
 */
const DEFAULT_TIMINGS: Record<LayerForCrossfade, { in: number; out: number }> = {
  base: { in: 300, out: 300 },
  emotion: { in: 200, out: 200 },
  anticipation: { in: 100, out: 100 },
  reaction: { in: 80, out: 120 },
};

/** Stagger gap (ms) — locked per Pitfall P62 single-mixer race. */
export const STAGGER_MS = 100;

/**
 * Pure crossfade-policy lookup.
 *
 *   `transition("emotion", "neutral", "hyped")` →
 *     { fade_in_ms: 200, fade_out_ms: 200, stagger_ms: 100 }
 *
 * `from` may be null to indicate "first play on this layer" (no out-fade
 * needed; we still report a default out value for the renderer's
 * convenience, but the renderer can ignore it when active was null).
 */
export function transition(
  layer: LayerForCrossfade,
  _from: string | null,
  _to: string,
): CrossfadeTiming {
  const defaults = DEFAULT_TIMINGS[layer];
  return {
    fade_in_ms: defaults.in,
    fade_out_ms: defaults.out,
    stagger_ms: STAGGER_MS,
  };
}

/**
 * Cancel transition — instant cut, no fade. Used by the priority-999
 * cancel path (Pitfall P72). Stagger is 0 so cancel signals NEVER wait
 * behind queued transitions.
 */
export function cancelTransition(): CrossfadeTiming {
  return {
    fade_in_ms: 0,
    fade_out_ms: 0,
    stagger_ms: 0,
  };
}
