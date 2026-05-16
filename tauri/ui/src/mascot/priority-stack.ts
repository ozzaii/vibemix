/* Phase 31 Plan 01 — PriorityStack: 4-channel arbitration manager.
 *
 * ADDITIVE-ONLY (Pitfall P47): extends the v2.0 Phase 22 mascot rig by
 * composing a new layer on TOP of the existing single-mixer
 * AdditiveLayer + state-machine. v2.0 anticipation priority 70 stays
 * verbatim — this class arbitrates which channel fires first when
 * multiple layers want to transition in the same frame.
 *
 * Single-mixer race mitigation (Pitfall P62):
 *   Only the highest-priority pending transition fires immediately. The
 *   next-priority transition stages 100ms later, the next 200ms, etc.
 *   This spreads AnimationMixer crossfade work across multiple frames
 *   so p99 frame budget holds < 22ms even with 4-simultaneous bursts.
 *
 * Cancel-priority 999 (Pitfall P72):
 *   `cancel(layer, {flush: true})` is the priority-999 sentinel — it
 *   flushes pending transitions on ALL layers except `base`, and snaps
 *   the cancelled layer to its baseline immediately (no fade). The base
 *   layer (priority 50) is NEVER canceled — it is the always-on idle
 *   heartbeat.
 *
 * Purity discipline (mirrors state-machine.ts):
 *   - No setTimeout / no wall-clock reads inside the class.
 *   - All scheduling expressed as absolute `fire_at_ms` timestamps in
 *     the caller's clock space, populated when `play()` is invoked
 *     with the caller-provided `now`.
 *   - The caller's rAF loop polls `pending(now)` each frame to discover
 *     which queued transitions have crossed their stagger deadline.
 */

/** Channel names. Order matters: lowest-priority first. */
export type LayerName = "base" | "emotion" | "anticipation" | "reaction";

/**
 * Static priority assignments — locked per CONTEXT Decision Area 1.
 * The numeric values are the SAME numbers used by the existing
 * `STATE_PRIORITY` map in types.ts (anticipation = 70).
 */
export const LAYER_PRIORITY: Record<LayerName, number> = {
  base: 50,
  emotion: 60,
  anticipation: 70,
  reaction: 80,
};

/** Per-call options when scheduling a transition on a channel. */
export interface PlayOpts {
  /** Clip name / identifier — opaque string passed through to consumers. */
  clip: string;
  /** Crossfade-in duration (ms). Default 200. */
  fade_in_ms: number;
  /** Crossfade-out duration (ms) for the previous clip on this channel.
   *  Default 150. */
  fade_out_ms: number;
  /** When the caller invoked play() (caller's clock). The stagger deadline
   *  is computed from this. */
  now_ms: number;
  /** Optional explicit timeout in ms — if the clip is still active after
   *  `now_ms + timeout_ms`, the layer is settled. v2.0 priority-70
   *  contract = 2500ms; reaction layer inherits same value by default. */
  timeout_ms?: number;
}

/** Currently active (already fired) clip on a channel. */
export interface ActiveClip {
  clip: string;
  fade_in_ms: number;
  fade_out_ms: number;
  started_at_ms: number;
  /** Absolute deadline at which the clip should be settled. null = no
   *  timeout (typical for base/emotion). */
  timeout_at_ms: number | null;
}

/** Pending (queued, not-yet-fired) clip on a channel — waiting on stagger. */
export interface PendingClip {
  clip: string;
  fade_in_ms: number;
  fade_out_ms: number;
  /** Absolute timestamp at which this transition should fire. */
  fire_at_ms: number;
  timeout_ms: number | null;
}

/** Snapshot returned by resolve() — read-only view per channel. */
export interface StackSnapshot {
  active: Record<LayerName, ActiveClip | null>;
  pending: Record<LayerName, PendingClip[]>;
}

/** Result of pending(now) — list of (layer, clip) tuples ready to fire. */
export interface ReadyTransition {
  layer: LayerName;
  clip: PendingClip;
}

/**
 * Stagger spacing in ms — locked per Pitfall P62.
 * 100ms × 4 channels = 300ms worst-case spread (well under any visible
 * perceptual threshold for "simultaneous").
 */
export const STAGGER_MS = 100;

const ORDERED_LAYERS: LayerName[] = ["base", "emotion", "anticipation", "reaction"];

/**
 * PriorityStack — the 4-channel arbiter. ONE per mascot session.
 *
 * Lifecycle:
 *   const stack = new PriorityStack();
 *   stack.play("emotion", { clip: "neutral", fade_in_ms: 200,
 *                            fade_out_ms: 150, now_ms: t });
 *   // ... rAF loop ...
 *   for (const r of stack.pending(now)) {
 *     applyToMixer(r.layer, r.clip);
 *     stack.activate(r.layer, r.clip, now);
 *   }
 *   stack.tick(now);  // settles timed-out reactions
 */
export class PriorityStack {
  private active: Map<LayerName, ActiveClip | null>;
  private queues: Map<LayerName, PendingClip[]>;

  constructor() {
    this.active = new Map();
    this.queues = new Map();
    for (const layer of ORDERED_LAYERS) {
      this.active.set(layer, null);
      this.queues.set(layer, []);
    }
  }

  /**
   * Schedule a transition on the given channel. If no transition is
   * currently active on the channel AND no queue is present, the new
   * transition is queued with stagger delay computed against any OTHER
   * pending transitions across the stack:
   *
   *   - This call's stagger = how many higher-or-equal-priority OTHER
   *     pending transitions are already in the stack at the same `now_ms`.
   *   - Highest priority fires at t=0, next at t=STAGGER_MS, etc.
   *
   * Same-channel re-target: a new play() on the same layer cancels the
   * previously pending transition for that layer (most-recent intent
   * wins). Active clip on the layer fades out as part of the new play.
   *
   * Anti-slop: unknown layer name throws (matches additive-layer.ts).
   */
  play(layer: LayerName, opts: PlayOpts): void {
    if (!ORDERED_LAYERS.includes(layer)) {
      throw new Error(
        `PriorityStack.play: unknown layer '${String(layer)}' ` +
          `(expected one of ${ORDERED_LAYERS.join(", ")})`,
      );
    }

    // Drop any same-layer pending transitions — most-recent intent wins.
    this.queues.set(layer, []);

    // Stagger: count how many OTHER layers (any priority) are pending
    // OR were just pushed-into-queue at this exact `now_ms`. The slot
    // for THIS layer is its priority rank relative to the others.
    //
    // Simpler algorithm: assign fire_at_ms based on the priority order.
    // We re-sort everything pending after pushing, then assign timestamps
    // in priority order (highest priority gets the earliest slot).
    const pending: PendingClip = {
      clip: opts.clip,
      fade_in_ms: opts.fade_in_ms,
      fade_out_ms: opts.fade_out_ms,
      fire_at_ms: opts.now_ms, // recomputed below
      timeout_ms: opts.timeout_ms ?? null,
    };
    const queue = this.queues.get(layer);
    if (!queue) {
      throw new Error(`PriorityStack.play: layer ${layer} has no queue`);
    }
    queue.push(pending);

    // Recompute fire_at_ms for ALL freshly-queued transitions that share
    // this exact now_ms. Highest priority fires first.
    this.rebalanceStagger(opts.now_ms);
  }

  /**
   * Apply 100ms stagger across same-frame pending transitions.
   *
   * Walks the queues in priority order (highest first). Any pending
   * transition whose CURRENT `fire_at_ms` falls within the staggered
   * window for this frame (`[now_ms, now_ms + 4*STAGGER_MS]`) gets
   * re-assigned its slot based on layer priority.
   *
   * The 4-slot window is bounded by the number of layers — older
   * transitions from previous frames will have fire_at_ms < now_ms and
   * are NEVER re-staggered (they should already have fired).
   *
   * This handles the case where layers are scheduled one-by-one within
   * the same frame: each call must reconsider EVERY layer's pending
   * head, not just the freshly-pushed one, to keep slots monotonically
   * priority-ordered.
   */
  private rebalanceStagger(now_ms: number): void {
    // Walk highest-to-lowest priority.
    const ordered = [...ORDERED_LAYERS].sort(
      (a, b) => LAYER_PRIORITY[b] - LAYER_PRIORITY[a],
    );
    const window_end = now_ms + ORDERED_LAYERS.length * STAGGER_MS;
    let slot = 0;
    for (const layer of ordered) {
      const queue = this.queues.get(layer);
      if (!queue || queue.length === 0) continue;
      for (const item of queue) {
        // Only re-stagger if the item lives inside the current frame's
        // stagger window — items from older frames that haven't fired
        // yet keep their original schedule.
        if (item.fire_at_ms >= now_ms && item.fire_at_ms <= window_end) {
          item.fire_at_ms = now_ms + slot * STAGGER_MS;
          slot += 1;
        }
      }
    }
  }

  /**
   * Cancel a layer's active + pending state.
   *
   *   - `flush: false` (default): cancel ONLY this layer.
   *   - `flush: true`: priority-999 sentinel — cancel + flush every layer
   *     EXCEPT base. Used for the cancel-aware crossfade-to-settle path
   *     (Pitfall P72).
   *
   * Base layer is NEVER canceled — even with flush:true, base.active and
   * base.queue are untouched.
   */
  cancel(
    layer: LayerName,
    opts: { flush?: boolean } = {},
  ): void {
    if (!ORDERED_LAYERS.includes(layer)) {
      throw new Error(`PriorityStack.cancel: unknown layer '${String(layer)}'`);
    }
    if (opts.flush === true) {
      // Priority-999 sentinel — flush ALL except base.
      for (const ly of ORDERED_LAYERS) {
        if (ly === "base") continue;
        this.queues.set(ly, []);
        this.active.set(ly, null);
      }
      return;
    }
    // Single-layer cancel.
    if (layer === "base") {
      // Base never canceled. No-op.
      return;
    }
    this.queues.set(layer, []);
    this.active.set(layer, null);
  }

  /**
   * Flush queue + clear active on all non-base layers. Equivalent to
   * cancel(any_layer, {flush: true}) — provided as a named API for
   * call-site clarity.
   */
  cancelAll(): void {
    for (const layer of ORDERED_LAYERS) {
      if (layer === "base") continue;
      this.queues.set(layer, []);
      this.active.set(layer, null);
    }
  }

  /**
   * Return all queued transitions whose fire_at_ms has been crossed by
   * `now`. Caller is expected to:
   *   1. Apply each ready transition to its concrete renderer layer.
   *   2. Call activate(layer, clip, now) to promote the pending clip into
   *      active state and pop it from the queue.
   *
   * Returned order: highest-priority first (matches stagger ordering).
   */
  pending(now_ms: number): ReadyTransition[] {
    const ready: ReadyTransition[] = [];
    const ordered = [...ORDERED_LAYERS].sort(
      (a, b) => LAYER_PRIORITY[b] - LAYER_PRIORITY[a],
    );
    for (const layer of ordered) {
      const queue = this.queues.get(layer);
      if (!queue || queue.length === 0) continue;
      // First-in-queue should always be the earliest fire_at_ms because
      // play() pushes to the back AND drops same-layer-stale entries.
      const head = queue[0];
      if (head && now_ms >= head.fire_at_ms) {
        ready.push({ layer, clip: head });
      }
    }
    return ready;
  }

  /**
   * Promote a pending clip into active state. Called by the renderer
   * after it has applied the transition to the mixer.
   *
   * If the clip was queued with `timeout_ms`, the active record stores
   * an absolute deadline; `tick(now)` settles the layer when crossed.
   */
  activate(layer: LayerName, clip: string, now_ms: number): void {
    const queue = this.queues.get(layer);
    if (!queue) {
      throw new Error(`PriorityStack.activate: unknown layer '${layer}'`);
    }
    // Find + remove the matching pending entry (clip name match — there
    // is always at most one head matching per call by construction).
    const idx = queue.findIndex((p) => p.clip === clip);
    if (idx < 0) {
      // No matching pending — be defensive, do not throw (renderer may
      // have raced). Set active from the call anyway.
      this.active.set(layer, {
        clip,
        fade_in_ms: 200,
        fade_out_ms: 150,
        started_at_ms: now_ms,
        timeout_at_ms: null,
      });
      return;
    }
    const head = queue[idx];
    if (!head) {
      // Defensive — should never happen since idx was just found.
      return;
    }
    queue.splice(idx, 1);
    this.active.set(layer, {
      clip: head.clip,
      fade_in_ms: head.fade_in_ms,
      fade_out_ms: head.fade_out_ms,
      started_at_ms: now_ms,
      timeout_at_ms:
        head.timeout_ms !== null ? now_ms + head.timeout_ms : null,
    });
  }

  /**
   * Tick — settles any active clip whose timeout has elapsed. Returns
   * the set of layers that just timed out (caller may fire a follow-up
   * settle clip for reaction/anticipation channels).
   */
  tick(now_ms: number): LayerName[] {
    const settled: LayerName[] = [];
    for (const layer of ORDERED_LAYERS) {
      const active = this.active.get(layer);
      if (!active) continue;
      if (active.timeout_at_ms !== null && now_ms >= active.timeout_at_ms) {
        this.active.set(layer, null);
        settled.push(layer);
      }
    }
    return settled;
  }

  /** Read-only snapshot of the entire stack. */
  resolve(): StackSnapshot {
    const active = {} as Record<LayerName, ActiveClip | null>;
    const pending = {} as Record<LayerName, PendingClip[]>;
    for (const layer of ORDERED_LAYERS) {
      active[layer] = this.active.get(layer) ?? null;
      pending[layer] = [...(this.queues.get(layer) ?? [])];
    }
    return { active, pending };
  }
}
