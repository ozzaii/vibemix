/* Phase 47 / MASCOT-06 — Persona smoke harness.
 *
 * Loaded into the Tauri WebviewWindow when --persona-smoke is passed
 * to `cargo tauri dev`. Cycles through the 15-state Phase 47 persona
 * loop (5 emotion updates + 10 reaction fires) at fixed timestamps
 * over 30 seconds.
 *
 * Schedule:
 *   t=0s..1s     idle lead-in
 *   t=1s..3.5s   emotion_joy
 *   t=3.5s..6s   emotion_trust
 *   t=6s..8.5s   emotion_surprise
 *   t=8.5s..11s  emotion_anticipation
 *   t=11s..13.5s emotion_focus
 *   t=13.5s..15s react_kick_swap
 *   t=15s..16.5s react_sub_layer
 *   t=16.5s..18s react_breakdown
 *   t=18s..19.5s react_reentry
 *   t=19.5s..21s react_phrase_boundary
 *   t=21s..22.5s react_distortion_climb
 *   t=22.5s..24s react_acid_line
 *   t=24s..25.5s react_mix_in
 *   t=25.5s..27s react_mix_out
 *   t=27s..30s   react_hype_peak (extra 1.5s — README hero anchor)
 *
 * After 30s, harness exits cleanly. ffmpeg (via persona_smoke.sh)
 * captures the WebView output for the duration.
 */

import type { MascotLayerBundle47 } from "./event-dispatcher.js";
import type { EmotionClip, ReactionClip } from "./types.js";

interface ScheduleEntry {
  t_ms: number;
  kind: "emotion" | "reaction";
  clip: EmotionClip | ReactionClip;
  caption: string;
}

export const PERSONA_SMOKE_SCHEDULE: ReadonlyArray<ScheduleEntry> =
  Object.freeze([
    { t_ms: 1000, kind: "emotion", clip: "emotion_joy", caption: "emotion_joy / 1 of 15" },
    { t_ms: 3500, kind: "emotion", clip: "emotion_trust", caption: "emotion_trust / 2 of 15" },
    { t_ms: 6000, kind: "emotion", clip: "emotion_surprise", caption: "emotion_surprise / 3 of 15" },
    { t_ms: 8500, kind: "emotion", clip: "emotion_anticipation", caption: "emotion_anticipation / 4 of 15" },
    { t_ms: 11000, kind: "emotion", clip: "emotion_focus", caption: "emotion_focus / 5 of 15" },
    { t_ms: 13500, kind: "reaction", clip: "react_kick_swap", caption: "react_kick_swap / 6 of 15" },
    { t_ms: 15000, kind: "reaction", clip: "react_sub_layer", caption: "react_sub_layer / 7 of 15" },
    { t_ms: 16500, kind: "reaction", clip: "react_breakdown", caption: "react_breakdown / 8 of 15" },
    { t_ms: 18000, kind: "reaction", clip: "react_reentry", caption: "react_reentry / 9 of 15" },
    { t_ms: 19500, kind: "reaction", clip: "react_phrase_boundary", caption: "react_phrase_boundary / 10 of 15" },
    { t_ms: 21000, kind: "reaction", clip: "react_distortion_climb", caption: "react_distortion_climb / 11 of 15" },
    { t_ms: 22500, kind: "reaction", clip: "react_acid_line", caption: "react_acid_line / 12 of 15" },
    { t_ms: 24000, kind: "reaction", clip: "react_mix_in", caption: "react_mix_in / 13 of 15" },
    { t_ms: 25500, kind: "reaction", clip: "react_mix_out", caption: "react_mix_out / 14 of 15" },
    { t_ms: 27000, kind: "reaction", clip: "react_hype_peak", caption: "react_hype_peak / 15 of 15" },
  ]);

export const PERSONA_SMOKE_DURATION_MS = 30000;

/**
 * Run the persona smoke schedule against the given layer bundle.
 * Returns a Promise that resolves after 30s.
 */
export async function runPersonaSmoke(
  layers: MascotLayerBundle47,
  captionEl: HTMLElement | null,
  now: () => number = () => performance.now(),
): Promise<void> {
  const t0 = now();

  function scheduleEntry(entry: ScheduleEntry): Promise<void> {
    return new Promise((resolve) => {
      const fireAt = t0 + entry.t_ms;
      const tick = () => {
        const remaining = fireAt - now();
        if (remaining <= 0) {
          if (entry.kind === "emotion") {
            layers.emotion.update(entry.clip as EmotionClip, now());
          } else {
            layers.reaction.fire(entry.clip as ReactionClip, now());
          }
          if (captionEl) captionEl.textContent = entry.caption;
          resolve();
        } else {
          setTimeout(tick, Math.min(50, remaining));
        }
      };
      tick();
    });
  }

  const allEntries = PERSONA_SMOKE_SCHEDULE.map(scheduleEntry);

  const overallDeadline = new Promise<void>((resolve) => {
    const tick = () => {
      if (now() - t0 >= PERSONA_SMOKE_DURATION_MS) {
        resolve();
      } else {
        setTimeout(tick, 100);
      }
    };
    tick();
  });

  await Promise.all([...allEntries, overallDeadline]);
}

/**
 * Detect --persona-smoke flag from Tauri argv (or URL query for browser dev).
 * Pure flag detector; the actual harness rigging up the layer bundle lives
 * in tauri/ui/src/main.ts (or wherever the entry point reads CLI args).
 */
export function isPersonaSmokeRequested(): boolean {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  return params.has("persona-smoke") || params.has("personaSmoke");
}
