# Earned Wall skill-tree: producer/consumer map (6 competencies x 2 stages)

## Correction to the brief's file map (UNVERIFIED claims in the prompt that do not reproduce)
- `src/vibemix/learn/skill_wall.py` — **does not exist**. `ls /Users/ozai/projects/dj-set-ai/src/vibemix/learn/` shows no such file. The engine lives in `skill_tree.py`.
- `ws_bus.py _build_skill_wall (~line 700)` — **does not exist**. `grep -c "def _build_skill_wall" .../runtime/ws_bus.py` → `0`. Line ~700 is `IpcRouterBus.register_handler`, unrelated. The ws_bus session snapshot deliberately does NOT carry the skill wall (coach.py:230-232 comment).
- `tauri/ui/src/learn/SkillWall.ts` and `messages.ts skill_wall/skills (~line 908)` — **correct** (`messages.ts` is at `tauri/ui/src/ipc/messages.ts`, skill_wall block lines 908-924).

## The pipeline (verified)
- **COMPETENT producer** (all 6, real): `SkillTree.compute` `/Users/ozai/projects/dj-set-ai/src/vibemix/learn/skill_tree.py:292` — `competent = learn_fill >= 0.6 AND <recital gate>` (skill_tree.py:321). Pure derivation from `LearnProgress.lessons` + `course_N_unlocked`.
- **MASTERED store/flip** (all 6, real but gated): `record_live_demo` `skill_tree.py:439`, called by the recognizer.
- **MASTERED recognizer** (citation gate): `recognize` `/Users/ozai/projects/dj-set-ai/src/vibemix/learn/skill_recognizer.py:203`.
- **The single LIVE mastery producer (call site):** `_credit_live_skill_demo` `/Users/ozai/projects/dj-set-ai/src/vibemix/runtime/coach.py:123`, invoked from the reaction loop at `coach.py:618` on every detected `ev`, plus the Judge join `_credit_judged_transition` (coach.py:276) → `_run_live_judge` (coach.py:327, called at coach.py:813 on `TRACK_CHANGE`).
- **Payload producer (the actual "skill_wall" emitter):** `skill_wall_payload` `skill_tree.py:390`, folded into `LearnProgress.snapshot()` `/Users/ozai/projects/dj-set-ai/src/vibemix/learn/progress.py:337-339`. Snapshot is shipped on `ipc.learn.progress_state` by: `learn/ipc_handlers.py:478,500`, `learn/runtime.py:1223-1233`, `learn/recital.py:521`, `__main__.py:2253`, and the live-credit refresh `coach.py:_emit_earned_wall_refresh:220/627`.
- **Consumer:** `SkillWall.ts` `mountSkillWall`/`defaultSubscribe` (`/Users/ozai/projects/dj-set-ai/tauri/ui/src/learn/SkillWall.ts:188-198`) reads `detail.progress.skill_wall` off the `ipc.learn.progress_state` window event. Schema mirror: `tauri/ui/src/ipc/messages.ts:915-924`.

Commands run (key ones): `grep -rn "recognize(" .../src/vibemix` → only live caller `coach.py:177`; `grep -rn "grade_beatmatch\|MiniDeck(" .../src/vibemix` → `grade_beatmatch` defined once (beatmatch_judge.py:83), **zero callers**; `grep -rn "BEATMATCH_GRADED" .../src .../tauri/ui/src` → only the recognizer/judge/skill_tree definitions, **no firing site**.

## Per-competency table

| Competency | Competent producer | Mastered producer (live event → recognizer branch) | Mastered REAL or STUB |
|---|---|---|---|
| **deck_control** | skill_tree.py:131-144 (lessons L1.02-L1.09 + `course_2_unlocked`) | `MIX_MOVE` w/ `_play→`/`xfader` substrings → `_candidate_skills` skill_recognizer.py:134-137. Fired live by EventDetector `_fire("MIX_MOVE")` event_detector.py:377-378, citation written event_detector.py:547. | **REAL** |
| **eq_mixing** | skill_tree.py:153-156 (L1.14/L2.04/L2.05 + `course_3_unlocked`) | `MIX_MOVE` w/ `_low:/_mid:/_hi:/_filter:/killed` → skill_recognizer.py:90,132-133. Same live MIX_MOVE producer. | **REAL** |
| **transitions** | skill_tree.py:161-164 (L2.03/06/07/08/09) | `LAYER_ARRIVAL` → `EVENT_SKILL_MAP` skill_recognizer.py:73. Fired live `_fire("LAYER_ARRIVAL")` event_detector.py:350. | **REAL** |
| **phrasing_performance** | skill_tree.py:165-182 (C1/C2/C3 lessons) | `PHASE` → skill_recognizer.py:74 (fired event_detector.py:327); `PHRASE_BOUNDARY` → skill_recognizer.py:75 (fired by `phrase_boundary.py:107,209` detector, routed via `event_detector.py:502`). | **REAL** |
| **harmonic_mixing** | skill_tree.py:157-160 (L2.11) | `transition_judged` w/ harmonic component > 0 → skill_recognizer.py:140-156. Live producer EXISTS: `_run_live_judge` → `judge_and_record` → `_credit_judged_transition` grounds the `ev:transition_judged` atom (coach.py:303-321, 379-392). | **REAL** (but conditional: only fires on `TRACK_CHANGE` with `deck_audio_capture` present AND a non-abstain two-deck verdict; abstains on master-only rigs — coach.py:806-821, 347-351) |
| **beatmatching** | skill_tree.py:145-152 (L2.01/L2.02) | `BEATMATCH_GRADED` w/ `tempo_matched AND phase_locked AND not abstain` → skill_recognizer.py:158-175. | **STUB / no producer** |

## The one real stub: beatmatching

The mastery *contract* for beatmatching is fully shipped and unit-tested, but **nothing in the running app produces the event that would trigger it**:
- `skill_recognizer.py:158-175` has the `BEATMATCH_GRADED` branch; `skill_tree.py` `SKILL_MANIFEST["beatmatching"].live_creditable` is `True` (default, skill_tree.py:145-152); `_HONEST_UNCREDITABLE_V11 = ()` is empty (skill_recognizer.py:109). The drift test pins the flag, not a producer.
- `grade_beatmatch` (beatmatch_judge.py:83) — the only function that can emit a grade — has **zero callers** in `src/vibemix/`. `grade_to_event_extra` (beatmatch_judge.py:145) is referenced only by docstrings/recognizer. No code anywhere does `Event(type="BEATMATCH_GRADED", ...)` or `registry.write("ev","BEATMATCH_GRADED",t)`. `MiniDeck` appears only in `automix_demo.py` docstrings.
- The docstring at beatmatch_judge.py:151-152 ("The live practice loop fires a `BEATMATCH_GRADED` event…") describes a loop **that does not exist** — a present-tense claim for absent code.
- Result: a user can reach **Competent** for beatmatching from lessons, but **Mastered is structurally unreachable live** — 1 of 6 skills.

This is corroborated by the repo's own audits (planning docs, not source — secondary evidence): `.planning/singularity/2026-05-31/ROADMAP-SINGULARITY.md:94`, `.planning/singularity/2026-05-31/census-learn-skilltree.md:65,121`, and `.planning/LEARN-MOAT-PLAN.md:1` all independently flag the missing `BEATMATCH_GRADED` producer.

## Summary
- **Competent producer: REAL for all 6** — single-sourced in `SkillTree.compute` (skill_tree.py:292).
- **Mastered producer: REAL for 5** (deck_control, eq_mixing, transitions, phrasing_performance via live EventDetector fires; harmonic_mixing via the live Vibe Judge join, conditional on routed two-deck audio).
- **Mastered producer: STUB for 1** — beatmatching. The credit gate is wired and tested, but no live `BEATMATCH_GRADED` emitter exists; `grade_beatmatch` has zero non-test callers.

UNVERIFIED note: I confirmed each event TYPE has a live `_fire`/detector and an `ev` citation write, and that `_credit_live_skill_demo` runs on every event. I did NOT execute the app, so I cannot confirm at runtime that the harmonic_mixing Judge path actually reaches a non-abstain verdict on a real rig (its own code documents it abstains on the common master-only setup — coach.py:347-351); treat harmonic_mixing's live demonstrability as code-present but runtime-conditional.
