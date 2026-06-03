# CODEX VERDICT - Q2 cue-confidence receipt

Item: Q2 - render the CUE-confidence receipt in the same next-song pill card as Q1.

SHA: `6149f327` (`feat(pill): render cue confidence receipts`)

User value: a Free user on the next-song pill now sees whether the proposed entry cue is DJ/Rekordbox-grounded, auto-generated, or review-worthy before they load the deck.

What shipped:
- `nextCueConfidenceReceipt()` converts existing `cue_source` / `cue_confidence` fields into a curated phrase such as `DJ cue A locked` or `auto cue A needs review`.
- The render path adds the cue receipt as a text-only chip in the same receipt row as Q1 reasons. It never prints raw confidence numbers.
- `nextSuggestionRenderKey()` now includes `cue_source`, `cue_confidence`, and `reasons[]`, so receipt-only backend updates cannot leave a stale visible pill.
- The peek/native height cap was raised to fit Q1+Q2 receipts plus the grade rail without clipping.

By-eye artifact:
- Screenshot: `/tmp/vibemix-q2-pill-cue-confidence-final.png`
- Confirmed fake-bus frame on the real `pill.html?controls=1` surface produced `DJ KNOWS`, cue chip `auto cue A needs review`, reason chips `Camelot relationship is clean` and `tempo delta is workable`, and aria text containing both `cue: auto cue A needs review` and `why: Camelot relationship is clean · tempo delta is workable`.
- Geometry proof: card height `142.09375`, grade bottom `184.09375`, card bottom `186.09375`; the grade rail is visible after raising the peek cap to `150`.

Live bus caveat:
- The currently running app bus did not produce a populated real `next_suggestion` during the Q1/Q2 proof window because deck/cue attribution was unresolved. Q2 is therefore proven by-eye with a grounded bus-shaped frame, while live real-track population remains upstream-dependent.

Grounding:
- No co-host say/when path changed. This is a frontend render-only wire of already-serialized deterministic cue fields, so no new utterance or citation source was introduced.

Verification:
- PASS: `npm --prefix tauri/ui test -- src/pill/next-suggestion.test.ts src/pill/index.test.ts` (181 tests).
- PASS: `npm --prefix tauri/ui run build`.
- PASS: `git diff --check -- tauri/ui/src/pill/next-suggestion.ts tauri/ui/src/pill/next-suggestion.test.ts tauri/ui/src/pill/pill.css tauri/ui/src/pill/index.ts tauri/ui/src/pill/index.test.ts`.
- FULL UI SUITE NOT GREEN: `npm --prefix tauri/ui test` still fails in existing unrelated areas:
  - `tests/learn/test_ws_client_filters_mascot.spec.ts`: warn emitted for dropped `ipc.status.tick`.
  - `tests/learn/test_ws_client_tauri_bridge.spec.ts`: expected 10 `subscribeIpc` calls, got 11.
  - `src/library/model-setup.test.ts`: `document is not defined` at `src/library/index.ts:96`.
