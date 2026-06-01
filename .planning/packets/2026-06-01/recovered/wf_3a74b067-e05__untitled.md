## Summary

I've verified all six claims against the live-tuning-or-brain branch source. Here are the key findings:

**DROP CHIP DEAD BY CONSTRUCTION (CLAIM #1 — TRUE):**
- `_build_session_snapshot()` at line 671 hardcodes `drop_pred_bars=None` every time
- The `renderDropChip()` function exists but is never imported or called anywhere in SessionLayout.ts
- Result: control is dead on arrival, even if predicted_drop_in_sec has a real value

**DROP PREDICTION CONDITIONAL ON LIBRARY IMPORT (CLAIM #2 — PARTIAL):**
- `state.predicted_drop_in_sec` is populated only when `section_source` (deck_library) is not None
- deck_library loads from `~/.cache/vibemix/library.pkl` only if it exists() AND try_load_cache() succeeds
- Most users without a prior rekordbox import will have deck_library=None, making the entire prediction chain unreachable
- The signal is not hardcoded but gated invisibly behind an import prerequisite

**DROP CALL ENABLED BY DEFAULT (CLAIM #3 — TRUE):**
- `VIBEMIX_DROP_CALL=1` is set by default at line 735 via `_apply_packaged_defaults()`
- EventDetector fires DROP event only when `_drop_call_enabled` is True (line 283)
- No user-facing misleading control here—gate works as intended

**SESSION SNAPSHOT HAS NO DECK MIXER/STATE (CLAIM #4 — TRUE):**
- SessionSnapshotPayload (lines 297–308) explicitly lacks deck_mixer and deck_state fields
- Session receives only basic TrackInfo (title/artist/deck string)
- Mock.ts hardcodes fake MIDI labels ('A · LOW EQ ↓', etc.) that the backend never sends

**FRONTEND DROP CHIP WIRING PARTIAL (CLAIM #5 — PARTIAL):**
- Drop value flows through render-loop.ts → SessionLayout state correctly
- But SessionLayout.applyState() never calls renderDropChip—the final 2-line integration is missing
- The only gap is the missing render call in SessionLayout.ts

**DECK MIXER ROUTES TO VIBER, NOT SESSION (CLAIM #6 — TRUE):**
- deck_mixer is in mascot_frame and broadcasts to all ws clients at 30Hz
- Session never reads it (zero references in session/ws-bridge.ts)
- Library window (tauri/ui/library/api.ts) receives LibraryLiveDeckMixer for Viber chat context
- This is intentional routing by design, not a bug

**Honest fix: Wire up renderDropChip in SessionLayout.ts, or remove the UI control. Users need rekordbox import + the actual Python backend call wired to see the countdown.**
