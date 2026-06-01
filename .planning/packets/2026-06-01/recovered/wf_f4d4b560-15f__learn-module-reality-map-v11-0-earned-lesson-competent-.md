# Learn-module reality map — v11.0 "Earned" lesson→Competent→Mastered spine

## Scope

A design-only reality map of the v11.0 Learn module: for each of the 6 DJ competencies, where the lesson→Competent producer and the cited-live-demo→Mastered producer actually live (or do not), and the status of the 4 load-bearing seams that connect the Learn island to the live co-host spine. The goal is to give Codex an accurate, file:line-grounded picture so any follow-on work builds on the *real* wiring and does not re-do finished work or trust stale "DEFERRED/orphaned" docstrings. Static analysis only — no socket, no test execution of beginner-path/GSD suites; SOURCE + repo-pin reads only.

**Accepted ground (build on, not re-verified):** `ai-message-observability` (ACCEPTED_SOURCE_SIDE) — the `build_ai_message_record` spine and `learn_tutor_speak_observability_events` emitter are accepted as authored correctly; this packet only locates them and confirms the Learn tutor reuses them (it does, not a silo). `product-reality-spine` (ACCEPTED_SUBSTANCE) — the EvidenceRegistry/citation grounding contract is accepted; Learn reuses the same shared registry, it does not invent a second one.

**Worktree note (load-bearing for every coach.py:NNN cite below):** `src/vibemix/runtime/coach.py` is **dirty (`M`)** in the 171-file working tree. The brief's `0e7bdc1c` is the committed HEAD; the credit/judge/refresh chain exists at that HEAD too (`git grep 0e7bdc1c` → `_credit_live_skill_demo@coach.py:115`, `recognize` import @154, `verdict_evidence_line@judge_voice.py:32`) but at **shifted line numbers**. All `coach.py:NNN` cites in this packet are the **worktree** lines (read this session). The credit logic itself landed in commits `6dc07ab3` (wire orphaned recognizer) + `2f265fc7` (4d judge credit glue). No git-crypt/LFS in play — all files plain UTF-8 (verified `git-crypt` absent, `.gitattributes` LFS removed).

---

## Per-competency reality table

The 6 skills are defined once in `SKILL_MANIFEST` (`skill_tree.py:129-182`), import-time drift-asserted against `CURRICULUM` + `LearnProgress` fields (`skill_tree.py:190-218`). The stage model is THREE stages — `locked | competent | mastered` (`skill_tree.py:232`, `compute` assigns all three at :340-345) — NOT two; there are two advancement *edges* (lesson→Competent, cited-live-demo→Mastered) over three stages. `compute` caps `mastered = live.get("mastered") AND spec.live_creditable` (:326), so beatmatching cannot show Mastered even with a hand-edited progress.json.

| competency | lesson→Competent producer (file:line) | cited-live-demo→Mastered producer (file:line) | status |
|---|---|---|---|
| **deck_control** | `SKILL_MANIFEST["deck_control"]` lessons L1.02–L1.09 + gate `course_2_unlocked` → `SkillTree.compute` `learn_fill≥0.6 AND gate` (`skill_tree.py:130-142`, `:316-321`) | `MIX_MOVE` w/ `_play→`/`xfader` substr → `_candidate_skills` (`skill_recognizer.py:120-133`, substrs `:91`) → `recognize` MAST-03 gate (`:274`) → live caller `_credit_live_skill_demo` (`coach.py:624`) | **WIRED** |
| **eq_mixing** | lessons L1.14/L2.04/L2.05 + gate `course_3_unlocked` (`skill_tree.py:152-155`) | `MIX_MOVE` w/ `_low:/_mid:/_hi:/_filter:/killed` substr (`skill_recognizer.py:90`,`120-133`) → `recognize` → `coach.py:624` | **WIRED** |
| **transitions** | lessons L2.03/L2.06-09 + gate `course_3_unlocked` (`skill_tree.py:160-163`) | `LAYER_ARRIVAL` → `EVENT_SKILL_MAP` (`skill_recognizer.py:73`) → `recognize` → `coach.py:624` | **WIRED** |
| **phrasing_performance** | 13 lessons L1.10-13/L2.10/12/13/L3.01-06 + gate `course_3_unlocked` (`skill_tree.py:164-181`) | `PHASE` / `PHRASE_BOUNDARY` → `EVENT_SKILL_MAP` (`skill_recognizer.py:74-75`) → `recognize` → `coach.py:624` | **WIRED** |
| **harmonic_mixing** | lesson L2.11 + gate `course_3_unlocked` (`skill_tree.py:156-159`) | `transition_judged` w/ COMPATIBLE harmonic component>0 → `_candidate_skills` (`skill_recognizer.py:135-151`) ← `_credit_judged_transition` synth event + `[ev:transition_judged]` write (`coach.py:309-321`) ← `_run_live_judge` (`coach.py:392`, gated `deck_audio_capture is not None and tag=="TRACK_CHANGE"` `coach.py:812`) | **WIRED** |
| **beatmatching** | lessons L2.01/L2.02 + gate `course_3_unlocked` (`skill_tree.py:143-151`) — Competent IS reachable | engine + consumer ready: `grade_beatmatch` (`beatmatch_judge.py:83`) + `grade_to_event_extra` (`:145`) + `BEATMATCH_GRADED` recognizer branch (`skill_recognizer.py:153-170`) — but **NO production emitter**: zero `grade_beatmatch`/`grade_to_event_extra` call-sites in `src/vibemix/` (all hits are def/comment/test); `live_creditable=False` (`skill_tree.py:150`); still in `_HONEST_UNCREDITABLE_V11` (`skill_recognizer.py:104`) | **PARTIAL (overclaim-guarded)** |

**Net: 5 of 6 competencies are Mastered-reachable in production.** Beatmatching is honestly capped at Competent by design — `_what_remains` returns "Mastered isn't live-graded for this skill" for a `live_creditable=False` competent skill (`skill_tree.py:375-379`), NOT a false "3 more demos" promise.

---

## The 4 key seams

| seam | status | evidence file:line | smallest action |
|---|---|---|---|
| **(a) Earned Wall live-credit → UI render** | **WIRED both ends** | Producer: `_credit_live_skill_demo` (`coach.py:624`) returns credited ids → `await _emit_earned_wall_refresh` (`coach.py:633`) builds `LearnProgressState.make(action="snapshot", progress=learn_progress.snapshot())` (`coach.py:241-251`); `snapshot()` merges `skill_wall` (`progress.py:339` `{**to_dict(), "skill_wall": skill_wall_payload(self)}`); payload from `skill_tree.py:389-408`. Envelope `ipc.learn.progress_state` in schema (`messages.schema.json:3036`, `skill_wall` field `:3101`). Bridge: ws-client re-dispatches as window CustomEvent `detail=envelope.payload` (`ws-client.ts:296-304`, type listed `:80`). Consumer: `SkillWall.defaultSubscribe` reads `detail.progress.skill_wall` (`SkillWall.ts:188-198`), `mountSkillWall` (`:213-243`) mounted in DesktopShell (`shell/app.ts:73-74`). | None — chain is correct, citation-gated, fail-soft. (Optional: the seam is also test-pinned `tests/runtime/test_coach_progress_emit.py`, `tests/learn/test_skill_wall.spec.ts`.) |
| **(b) beatmatch Mastered PRODUCER** | **ORPHANED (the one real gap)** | Engine `beatmatch_judge.py:83/145` complete + unit-tested; consumer branch ready `skill_recognizer.py:153-170`; recognize() has a live caller (`coach.py:177`). But the live `recognize` caller only ever sees the EventDetector taxonomy (MIX_MOVE/LAYER_ARRIVAL/PHASE/PHRASE_BOUNDARY/transition_judged) — never `BEATMATCH_GRADED`. Zero prod emitter confirmed: `grep -rn 'grade_beatmatch\|grade_to_event_extra\|BEATMATCH_GRADED' src/vibemix` → only defs/comments/the recognizer branch, no call. `MiniDeck` (`audio/miniplayer.py:99`) + `DeckState` exist (used by `runtime/automix_demo.py`) but are not joined to the grader. | Build the owned-deck practice loop: own a `MiniDeck`, read `DeckState`+both `BeatGrid`s, call `grade_beatmatch`, on a non-abstain LOCKED grade emit an `Event(type="BEATMATCH_GRADED", extra=grade_to_event_extra(grade))` AND `evidence_registry.write("ev","BEATMATCH_GRADED",t_session)`, then feed `recognize` (mirror `_credit_judged_transition` `coach.py:308-321`). In the SAME change: drop `"beatmatching"` from `_HONEST_UNCREDITABLE_V11` (`skill_recognizer.py:104`), flip `live_creditable=True` (`skill_tree.py:150`), and update the 3 RED-going pins in `tests/repo/test_live_reality_pins.py` (`test_beatmatch_judge_has_no_production_emitter:126`, `_is_import_orphaned:144`) — keep the consumer/skill-id pins green (`:159/172/176`). |
| **(c) tutor → ai_message observability** | **WIRED, reuses the shared spine (not a silo)** | `learn/observability.py:13` imports `build_ai_message_record` from `runtime/ai_observability.py:217` (the ACCEPTED shared spine, writes `~/.cache/vibemix/ai_messages.jsonl` `:416`). `learn_tutor_speak_observability_events` (`observability.py:25`) builds the record with `engine="learn_tutor", surface="learn"` (`:55-57`), `event="learn_tutor_speak"` (`:61`), and returns `[("learn_tutor_speak", fields), ("ai_message", record)]` (`:80`). Two live callers: `__main__.py:2139-2147` (`_learn_observer_emit` on `ipc.learn.tutor_speak`) and `LessonRuntime._log_tutor_speak_event` (`runtime.py:1283-1296`, `source="learn_runtime"`). `LessonRuntime` is boot-imported `__main__.py:2018` + instantiated `:2092`. | None. NOTE for Codex: the brief's DROPPED finding cited a non-existent `record_tutor_speak`/`vibemix.obs.ai_message`/`record_ai_message` — those names do NOT exist at this HEAD. The real names are above. There is **no `src/vibemix/obs/` package** (`ls` errors); the spine is `runtime/ai_observability.py`. |
| **(d) live-evidence → mastery bridge + judge_voice caller** | **WIRED (one-directional); judge_voice caller LIVE** | `verdict_evidence_line` (`judge_voice.py:32`) has 1 prod caller: `_run_live_judge` (`coach.py:389`), called at `coach.py:820` guarded by `deck_audio_capture is not None and tag=="TRACK_CHANGE"` (`:812`). `_run_live_judge` calls `judge_and_record` (grounds `[judge:transition@t]` into the SAME shared `evidence_registry`) then `_credit_judged_transition` → `recognize` (single credit path). Deck-audio live evidence → judged verdict → cited credit-gate → Mastered is a closed loop for harmonic_mixing. Mastery-credit half reuses the shared spine correctly. **The genuine gap: the tutor narration (LessonRuntime) PRODUCES screen/midi evidence into the shared registry (`runtime.py:1283-1370`) but does NOT CONSUME live audio/cue/Judge verdicts into its spoken context** — tutor speech is driven by the authored CURRICULUM + deterministic `teaching_loop`, not live audio. | None required for mastery credit. If a "tutor reacts to live mix" bridge is wanted later (feature, not wiring): let the Course-2/3 tutor cite the existing `[judge:transition@t]` atom the Judge already grounds (registry is shared) when an owned-deck transition is judged during a lesson — reuse `_run_live_judge`'s verdict, add no new evidence channel. |

---

## OVERCLAIM watch

1. **`skill_recognizer.py` module docstring still says the live wiring is "DEFERRED KAAN-ACTION §EARNED-LIVE-MASTERED-VERIFY" and calls itself "until-now-orphaned"** (`skill_recognizer.py:17-18, 36-39, 214`). **Truth:** it now has exactly ONE production caller — `_credit_live_skill_demo` at `coach.py:123` (codegraph `callers(recognize)` = 1; `coach.py:133` itself notes it "gives the until-now-orphaned recognize a live call site"). The docstring is **stale** and will mislead the next reader into re-doing finished work. Design-only fix: update the docstring to "live-wired via coach.py:_credit_live_skill_demo". (Confirms the brief's DROPPED finding "recognizer is orphaned" — refuted; it is wired.)

2. **`beatmatch_judge.py:151-152` docstring claims "The live practice loop fires a `BEATMATCH_GRADED` event … AND registers the matching citation"** — present tense for a loop that **does not exist** (no prod emitter, seam (b)). This is forward-looking design copy, not a description of shipped behavior. It is honestly counter-balanced by `skill_recognizer.py:99-104` + `skill_tree.py:146-150` (which correctly state no production loop emits it yet) and pinned by `tests/repo/test_live_reality_pins.py`. Not slop leaking to the user (the UI says "Mastered isn't live-graded"), but the docstring tense should read "WILL fire" until the emitter ships.

3. **No phantom-event overclaim found.** `EVENT_SKILL_MAP` keys (`LAYER_ARRIVAL`/`PHASE`/`PHRASE_BOUNDARY`, `skill_recognizer.py:72-76`) + the `MIX_MOVE`/`transition_judged`/`BEATMATCH_GRADED` branches are all REAL event-type literals; the docstring's "verified this session" claim holds for the 5 live ones (the 6th, `BEATMATCH_GRADED`, is correctly flagged as not-yet-fired). No skill references a non-existent lesson (import-time assert `skill_tree.py:190-218`). No Python↔TS skill-set drift: TS `SKILL_WALL_LABELS` (`SkillWall.ts:33-40`) = the same 6 ids; `STAGE_LABELS`/`STAGE_GLYPHS` = the same 3 stages. (The brief's UNPROVEN claim of a separate `ws_bus _build_skill_wall`/`progress`-event lane was NOT found — the only live wall path is the `ipc.learn.progress_state` envelope verified here.)

**UNPROVEN/out-of-scope:** the brief's DROPPED finding about a `curriculum.py` ↔ generated `curriculum-meta.ts` drift (`course_2_transitions.capabilities` missing `library_supgestions`) is a COURSE-capability field drift, NOT a lesson-set or skill drift, and is orthogonal to the lesson→Competent feed; it is NOT re-verified here (would require running `scripts/export_learn_curriculum_meta.py --check`, out of scope for a read-only static map). Flagged so Codex knows it is open. The recital that flips `course_N_unlocked` (the upstream of every Competent gate) was NOT exercised here — `compute` reads `getattr(progress, spec.gate)` and trusts it; whether `RecitalRuntime` 5/5 actually sets the flag is out of scope.

---

## Tool-health note

**codegraph + Read + grep were RELIABLE this run.** Sanity probes that passed: codegraph `status` (1663 files / 28017 nodes indexed) and `callers(recognize)` returned the known-good `_credit_live_skill_demo@coach.py:123` (matches grep + Read). grep/Read agreed on every load-bearing symbol across repeated invocations. Therefore the ORPHANED verdict for seam (b) (beatmatch producer) is **HIGH confidence** — it rests on a working `grep -rn` across `src/vibemix/` returning zero `grade_beatmatch`/`grade_to_event_extra`/`BEATMATCH_GRADED` call-sites (only defs/comments/the consumer branch), corroborated by the dedicated repo pin `tests/repo/test_live_reality_pins.py:126/144` which asserts exactly this. No ABSENT/ORPHANED verdict in this packet rests on a dead-tool result. The only non-codegraph caveat: `state/coach.py` (the prompt-builder, 1063 lines) is a DIFFERENT file from `runtime/coach.py` (the loop, 887 lines) — both dirty; the credit/judge/refresh chain lives in `runtime/coach.py`, the prompt assembly + `judge_evidence_line` consumption in `state/coach.py:745-748`.

---

## Request to Codex

Please VERDICT this reality map (substance, not line-number nits — the tree is dirty so worktree lines may shift). Specifically confirm or refute:

1. **Seam (b) is THE gap** and the smallest-action plan (owned-deck practice loop emitting `BEATMATCH_GRADED` + `[ev]` citation, reusing the `_credit_judged_transition` pattern, + the 5 coordinated pin/flag edits) is the correct close.
2. The 5-of-6 Mastered-reachable verdict is accurate and matches any marketing/UI copy (block if any surface says "master all 6 live").
3. Seam (c) reuses the ACCEPTED `build_ai_message_record` spine (not a Learn silo) — confirm the engine/surface/source field shapes.

Reproduce commands (read-only; do NOT run beginner-path/GSD suites):
```bash
git -C /Users/ozai/projects/dj-set-ai rev-parse HEAD   # expect 0e7bdc1c…
# seam (a) producer→UI
grep -n '_emit_earned_wall_refresh\|_credit_live_skill_demo' src/vibemix/runtime/coach.py
grep -n 'def snapshot\|skill_wall_payload' src/vibemix/learn/progress.py
grep -n 'skill_wall\|ipc.learn.progress_state' tauri/ui/src/ipc/messages.schema.json
grep -n 'defaultSubscribe\|mountSkillWall' tauri/ui/src/learn/SkillWall.ts tauri/ui/src/shell/app.ts
# seam (b) beatmatch — expect zero NON-def/comment/test call-sites
grep -rn 'grade_beatmatch\|grade_to_event_extra\|BEATMATCH_GRADED' src/vibemix --include='*.py'
grep -n 'def test_beatmatch_judge_has_no_production_emitter\|_EMITTER_FNS' tests/repo/test_live_reality_pins.py
# seam (c) tutor→ai_message — shared spine
grep -n 'build_ai_message_record\|engine=\|surface=\|learn_tutor_speak' src/vibemix/learn/observability.py
grep -n 'build_ai_message_record\|ai_messages.jsonl' src/vibemix/runtime/ai_observability.py
grep -n 'learn_tutor_speak_observability_events\|LessonRuntime' src/vibemix/__main__.py
# seam (d) judge_voice caller + manifest/recognizer
grep -rn 'verdict_evidence_line' src/vibemix --include='*.py'
grep -n 'SKILL_MANIFEST\|live_creditable\|_HONEST_UNCREDITABLE_V11' src/vibemix/learn/skill_tree.py src/vibemix/learn/skill_recognizer.py
# optional (NOT run here): focused unit suites
# uv run pytest -q tests/learn/test_skill_tree.py tests/learn/test_creditability_drift.py tests/repo/test_live_reality_pins.py
```

Reply at: `/tmp/vibemix-codex-inbox/CODEX_VERDICT-learn-reality-map.md`. Design-only — no edits pending; freeze holds until that file exists.
