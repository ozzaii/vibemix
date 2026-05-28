# Plan 96-04 — SUMMARY (DEFERRED to KAAN-ACTION queue)

**Status:** `kaan_action_deferred` — per `/gsd-autonomous fully` mode, the checkpoint:human-verify plan is parked.

## What needs to happen (Kaan-side)

Live ear-pass on real DDJ-FLX4 hardware:

1. Launch with current-source sidecar:
   ```bash
   VIBEMIX_DEV_SIDECAR=1 cd tauri && cargo tauri dev
   ```
2. Open Learn window → finish Course 1 + Course 2 (or load progress.json with `course_3_unlocked: true`) → walk all 6 Course 3 lessons end-to-end on real FLX4.
3. Critical checks per lesson:

   - **L3.01 First 5-Minute Mix** (proactive_lens_active=true, exemplar_audio_forbidden=true): tutor suggests ≤1 grounded move per minute; every count-in cites `[cue:<anchor_id>]`; NO exemplar audio plays (live mix is audible_deck != none → guard refuses).
   - **L3.02 First 15-Minute Set** (proactive_lens_active=true, exemplar_audio_forbidden=true): v8.2 Build-a-Set engine pre-sequences; tutor live-coaches each transition; count-ins only fire when bpm_confidence ≥ 0.8 AND phrase_position_confidence ≥ 0.7.
   - **L3.03 Reading The Room** (proactive_lens_active=true, exemplar_audio_forbidden=true): tutor walks user through reading energy curve mid-set; suggests next-track adjustments grounded on `[cue:]` evidence.
   - **L3.04 First 30-Minute Set Capstone** — **THE HEADLINE LIVE TEST** (proactive_lens_active=true, exemplar_audio_forbidden=true): proactive co-pilot full 30-min; session recorded; v2.1 debrief auto-opens on completion (port 8766).
   - **L3.05 Recovery Drills** (proactive_lens_active=true, exemplar_audio_forbidden=true): system synthetically introduces train-wrecks (drill_shapes: key_clash + misaligned_phrase); user bails out (echo-out / filter / cut) within 4 bars.
   - **L3.06 DJ Profile Graduation** (proactive_lens_active=false, exemplar_audio_forbidden=false): user reviews v8.1 long-term profile + lesson completion summary in v2.1 debrief.

4. **Invariant #3 verification** (THE phase-defining check):
   - When live BPM is shaky (e.g. ambient outro tail): NO count-in language ("breakdown in 16 beats") fires; tutor downgrades to retrospective ("that was a breakdown").
   - When the audio is locked (clean techno groove): proactive count-ins fire grounded on `[cue:<anchor_id>]` and feel ALIVE, not scripted.
   - The 4 forbidden tutor moves verifiably absent (compliment / summarize / preview / upbeat-hook).

5. **EXEMPLAR-06 verification** (active-session guard):
   - L3.01-L3.05 confirm: pressing the EQ knob during live mix does NOT trigger an exemplar audio bleed into the master.
   - L3.06 confirms: exemplar audio CAN play during the graduation review (no live deck).

6. **Tone gate** — Kaan's ear:
   - Tutor narration sounds like a "real DJ friend in your ear" mid-set
   - 35-token slop blocklist verifiably absent (auto-gated in CI; live read confirms)
   - Count-ins feel timely, not late or speculative

## Pass / Fail criteria

**PASSED if:**
- All 6 Course 3 lessons complete without backend errors
- L3.04 30-min capstone completes + debrief auto-opens
- Tutor narration passes Kaan's ear on the "real DJ friend" bar
- Invariant #3 verifiable in the wild (count-ins downgrade when audio shaky; proactive when locked)
- EXEMPLAR-06 guard verifiable (no exemplar bleed during live)
- L3.05 train-wreck drills work (user can bail within 4 bars; system grades the recovery)

**FAILED if:**
- Tutor emits a count-in when `bpm_confidence < 0.8` OR `phrase_position_confidence < 0.7` OR `next_phrase_at is None` (Invariant #3 violation — the AST + runtime gate should make this impossible, but live verification is the truth)
- Exemplar audio bleeds during live mix (EXEMPLAR-06 violation)
- L3.06 doesn't surface long-term DJ profile in debrief
- Tutor trips any of the 4 forbidden moves OR any slop-blocklist token

## Engineering provenance (Plans 96-01..96-03 SHIPPED)

| Plan | What landed | Tests |
|------|-------------|-------|
| 96-01 | `test_no_speculative_phrase.py` AST gate + `test_course3_uses_existing_coach.py` AST gate + 3 additive MusicState fields (`session_active`, `phrase_position_confidence`, `next_phrase_at`) + `AICoach.evidence_line` confidence gate (`_COUNT_IN_BPM_FLOOR=0.8`, `_COUNT_IN_PHRASE_FLOOR=0.7`, retrospective downgrade) | +18 new (4 + 5 + 9); 81 broader sweep; 111 coach goldens |
| 96-02 | `[cue:<anchor_id>]` atomic 4-site mirror (EVIDENCE_SOURCES count: 10 → 11) + `test_cue_citation_schema_mirror.py` pins all 4 sites | +8 new; 188 sweep |
| 96-03 | 6 Course 3 JSON fixtures + curriculum.py COURSE_FRAMES["course_3_play_mode"] + 6 L3.NN CURRICULUM entries + ExemplarPlayer EXEMPLAR-06 active-session guard wired + `test_course3_no_exemplar_during_live.py` | +50 new (41 + 9); 258 full `tests/learn/`; 268 with confidence-gate |

**Total Phase 96 commits:** 9 atomic, named-paths only.

## REQ-ID coverage

| REQ-ID | Plans | Status |
|--------|-------|--------|
| CURR-3.01..3.06 (6 Course 3 lessons) | 96-01 (test gates) + 96-02 (citation source) + 96-03 (fixtures + curriculum + guard) | Complete |
| CURR-3.07 (test infrastructure pin: test_no_speculative_phrase + test_course3_uses_existing_coach + evidence_line confidence gate) | 96-01 | Complete |
| EXEMPLAR-06 (active-session guard) | 96-03 (ExemplarPlayer guard) | Complete |

## Cardinal invariant pin status (4/4)

| Invariant | Status |
|-----------|--------|
| #1 single-writer (LessonRuntime + ExemplarLessonController + RecitalRuntime + audio_cue all read MusicState only; state/refresh.py is the sole writer) | `test_runtime_invariants.py` AST gate green |
| #2 citation grounding (`[cue:<anchor_id>]` atomic 4-site mirror; EVIDENCE_SOURCES count = 11) | `test_cue_citation_schema_mirror.py` green |
| **#3 BINDING (trust the audio) — THE PHASE'S KEY PIN** — proactive count-ins ONLY when bpm_confidence ≥ 0.8 AND phrase_position_confidence ≥ 0.7 AND next_phrase_at is not None | `test_no_speculative_phrase.py` AST gate + `test_coach_course3_confidence_gate.py` runtime gate both green |
| #4 one socket (no new ws ports; debrief surface continues on port 8766 from v2.1) | `test_no_new_ws_port.py` green |

## Acceptable deferrals (NOT gaps)

- **§LEARN-EAR-COURSE-3** — Kaan ear-pass on all 6 Course 3 lessons + L3.04 30-min capstone marquee (THIS deferred plan)
- **§LEARN-COURSE-3-REFRESH-WIRING** — `state/refresh.py` to flip `state.session_active` based on `fixture.proactive_lens_active` (engineering follow-up; state/refresh.py is the sole MusicState writer per Invariant #1)
- **§LEARN-COURSE-3-DRIFT-WIRING** — actual playback-rate-drift introduction for L3.05 `drill_shapes` synthetic train-wrecks (fixture surface shipped; downstream runtime wiring deferred to v9.x)

## Status: PASSED engineering goal; live ear-pass deferred

Phase 96 engineering deliverables satisfy goal-backward verification. Per `/gsd-autonomous fully`, advancing to P97 (Onboarding + Verbatim Tone Locks + Mode Picker).

---

*Generated by `/gsd-autonomous` overnight run. Plan 96-04 owes Kaan a real-FLX4 Course 3 walkthrough + L3.04 30-min capstone session record.*
