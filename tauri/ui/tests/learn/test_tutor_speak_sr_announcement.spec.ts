// SPDX-License-Identifier: Apache-2.0
// REQ-ID: LESSON-05 / A11Y — Screen-reader announcement on
//                  `ipc.learn.tutor_speak`.
//
// Phase 92 Plan 02 — RED-state. The LearnWindow's `#learn-sr-announcement`
// aria-live region surfaces tutor narration text for VoiceOver / NVDA.
// Plan 92-05 lands the wiring (LearnWindow → aria-live region update on
// tutor_speak envelope). For now this spec is `it.todo` — the contract
// is documented so the Plan 92-05 executor can flip it to live.
//
// Shape contract (per UI-SPEC §Accessibility lines 330-331):
//   1. Dispatch a CustomEvent("ipc.learn.tutor_speak", { detail: {
//        type: "ipc.learn.tutor_speak",
//        payload: {
//          text: "find deck A play button",
//          tts_marker: "L000.beat0",
//          citations: [],
//          data_state: "active",
//        },
//      }}) on window.
//   2. Within one event loop turn, the `[data-sr-region="tutor"]`
//      aria-live="polite" element's textContent equals the
//      payload.text VERBATIM.
//   3. data-state="active" → aria-live="polite"; data-state="hint" →
//      aria-live="assertive" (the 3-strike hint surface raises urgency).

import { describe, it } from "vitest";

describe("test_tutor_speak_sr_announcement.spec.ts (LESSON-05 a11y)", () => {
  it.todo(
    "aria-live polite region receives tutor_speak text within one tick (Plan 92-05)",
    // TODO: Plan 92-05 executor — when LearnWindow lands the SR region:
    //   1. Import `mountLearnWindow` from "../../src/learn/learn-window.js"
    //      (the entry that Plan 92-05 ships)
    //   2. Mount it into a JSDOM document body
    //   3. Dispatch the CustomEvent shown above
    //   4. await a microtask (`await Promise.resolve()`)
    //   5. Assert `document.querySelector('[data-sr-region="tutor"]')
    //              .textContent === "find deck A play button"`
    //   6. Repeat with data_state="hint" → assert aria-live === "assertive"
    //   7. Flip `it.todo` → `it`, fill in the body, run vitest
  );

  it.todo(
    "data-state='hint' raises aria-live to assertive (Plan 92-05)",
  );
});
