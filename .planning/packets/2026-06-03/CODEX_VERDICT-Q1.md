# CODEX VERDICT - Q1 next-song reasons receipt

Item: Q1 - render the next-song `reasons[]` receipt in the pill.

SHA: `fec9dada` (`feat(pill): render next-song reason receipts`)

User value: a Free user on the next-song pill now sees the deterministic "why this track" receipt that the engine already computed, so the anti-slop moat is visible instead of hidden behind a coarse blurb.

What shipped:
- `nextReasonItems()` / `nextReasonReceipt()` caps the existing transition `reasons[]` to the top two cleaned clauses. It does not synthesize scores or numeric claims.
- `renderNextSuggestion()` renders the receipt as text-only reason chips, sets the full receipt as `title`, and includes it in the card aria label.
- The real visible surface is the hover peek card, so the peek CSS and native resize cap were updated to avoid clipping the newly visible receipt and grade rail.

By-eye artifact:
- Screenshot: `/tmp/vibemix-q1-pill-reasons-final.png`
- Confirmed fake-bus frame on the real `pill.html?controls=1` surface produced `DJ KNOWS`, two readable chips (`Camelot relationship is clean`, `tempo delta is workable`), title `Camelot relationship is clean · tempo delta is workable`, and aria text containing `why: Camelot relationship is clean · tempo delta is workable`.
- Geometry proof: card height `124.296875`, grade bottom `166.296875`, card bottom `168.296875`; the grade no longer clips after raising the peek cap to `130`.

Live bus caveat:
- The currently running app bus on `127.0.0.1:8765` did not expose a populated real `next_suggestion` during this pass. Frames reported `next_suggestion: null`, `audible_deck: none`, and blockers around unresolved deck/cue attribution. That means the Q1 renderer is proven by-eye with a grounded bus-shaped frame, but the live rig did not provide a real suggestion to render during this loop.
- `vibemix-dev` MCP probes were unavailable in this pass (`Transport closed`), so ws observation used a manual client.

Grounding:
- No co-host say/when path changed. This is a frontend render-only wire of already-serialized deterministic receipt fields, so no new utterance or citation source was introduced.

Verification:
- PASS: `npm --prefix tauri/ui test -- src/pill/next-suggestion.test.ts src/pill/index.test.ts` (174 tests).
- PASS: `npm --prefix tauri/ui run build`.
- PASS: `git diff --check -- tauri/ui/src/pill/next-suggestion.ts tauri/ui/src/pill/next-suggestion.test.ts tauri/ui/src/pill/pill.css tauri/ui/src/pill/index.ts tauri/ui/src/pill/index.test.ts`.
- FULL UI SUITE NOT GREEN: `npm --prefix tauri/ui test` still fails in existing unrelated areas:
  - `tests/learn/test_ws_client_filters_mascot.spec.ts`: warn emitted for dropped `ipc.status.tick`.
  - `tests/learn/test_ws_client_tauri_bridge.spec.ts`: expected 10 `subscribeIpc` calls, got 11.
  - `src/library/model-setup.test.ts`: `document is not defined` at `src/library/index.ts:96`.

Packet assumption corrected:
- The packet named `next-suggestion.ts` as the primary wire, but by-eye proof showed the user-visible Q1 surface is the peek card. The commit therefore also touched `pill.css`, `pill/index.ts`, and `pill/index.test.ts` so the receipt is visible and the native overlay height does not clip.
