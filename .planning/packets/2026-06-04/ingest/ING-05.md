# ING-05 — LEARN teaching loop (ship-ingestion, adversarial verify)

## ING05

**HEAD read at:** `d7d5337a175ac90612702c3adda4d17aa3918899` (`d7d5337a test(config): isolate device defaults from rig env`), branch `ux-redesign-impeccable`. All line numbers below were re-pinned at this SHA (the tree moved a lot since the SHIP-MAP; the LEARN-PLAYABILITY-TEARDOWN was written on an earlier HEAD and several of its blockers have since been built — flagged inline).

**Proof tiers used (never conflated):** SRC = green tests / verifiable on source at HEAD. PKG = present in a signed DMG built at HEAD (NOT checked here — no build run). LIVE = a real user actually reaches it at runtime (`python -m vibemix` → `main()` → start gate). Verdict flags: LANDED / CLAIMED-BUT-DARK / NOT-STARTED.

**Method:** static read + grep + AST + codegraph reasoning + the committed packets + targeted pytest. READ-ONLY. Did NOT launch the sidecar (one socket). Ran `tests/runtime/test_coach*.py` (40 passed) and `tests/learn/` (896 passed, 1 skipped opt-in jog).

---

## HEADLINE FINDING (the one that matters most): the entire LEARN runtime is DEAD on the ship path

The START-GATE refactor (`18dc95cb test(start-gate): lock idle-cold`, message: "main() split into an idle boot + _activate_session") split `main()` so the live graph activates only on Start. It lifted the **co-host** loop into the nested `_activate_session` coroutine but did NOT lift the **Learn** runtime. The Learn wiring still sits in the now-unreachable tail of `main()`.

- `main()` spans `__main__.py:1098-4204` (AST-confirmed).
- `main()` has a **top-level `return` at `__main__.py:2314`** (AST-confirmed: `top-level return in main at line 2314`), reached via `await stop_event.wait()` at `:2278` then `finally:` cleanup at `:2279-2313`, then `return` at `:2314`.
- **Everything from `:2316` to `:4204` is unreachable dead code.** `:2316` (`voice_stream = None`) begins the orphaned tail. Evidence of a stale-shadow second copy: `_ws_broadcast_once` is defined twice (`:2250` reachable, `:3864` dead).
- The **LessonRuntime is constructed at `__main__.py:3606`** — past the return. Its loops are spawned at `:3890` (`lesson_tick_task = asyncio.create_task(lesson_runtime.tick_loop(stop_event))`) and `:3891` (`lesson_live_grade_task = asyncio.create_task(lesson_runtime.live_grade_loop(stop_event))`) — both unreachable.
- The IPC adapter `_LessonRuntimeIpcAdapter` (`:3505`/`:3544`), `_learn_state = LearnState()` (`:3543`), `_learn_progress` load (`:2409`), and all learn IPC handler registration live in the dead region too.
- I scanned the reachable body (`:1098-2314`) and the entire `_activate_session` body (`:1704-2170`) for any learn wiring: the ONLY learn references are a comment at `:1416` (`ipc.learn.midi_position` snapshot writer) and two `learn_progress=None` passes inside `_activate_session` (`:2010` and one more). No `LessonRuntime`, no `live_grade_loop`, no `tick_loop`, no learn IPC handler registration is reachable.

**Consequence:** at runtime, the sidecar never instantiates `LessonRuntime`. The frontend Learn window can open and emit `ipc.learn.start_lesson`/`ack`/etc., but the sidecar has no consumer running. The Learn surface is **CLAIMED-BUT-DARK at LIVE tier**, despite being SRC-green (896 tests) and PKG-buildable. The default entry is `asyncio.run(main())` (`:9446`); `python -m vibemix` hits this path.

- Verdict: **CLAIMED-BUT-DARK (LIVE).** SRC: LANDED (all loops, FSM, IPC dataclasses exist and pass tests). PKG: code is bundled. LIVE: the Learn runtime is unreachable after the `main()` start-gate split — `__main__.py:2314` return strands `:3606`/`:3890`/`:3891`.
- This is almost certainly an **unintended orphaning by the start-gate refactor**, not a design decision. The start-gate commit message references only "the live graph" (co-host) and `test_smoke_03`; it never mentions Learn. The fix is a WIRE, not a build: lift the LessonRuntime construction + its two task spawns + learn IPC handler registration above the `:2314` return (or into the reachable boot shell, independent of Start since Learn must run at idle), and pass `learn_progress=_learn_progress` to whichever coach_loop the live path uses.

---

## W12 LIVE BEATMATCH CREDIT — `[ev:BEATMATCH_GRADED]` consumed in `runtime/coach.py`?

This was the explicit verify target. Answer: **the consumer EXISTS and is wired into the reaction loop, but it is triple-dark on the ship path. CLAIMED-BUT-DARK (LIVE), LANDED (SRC).**

The producer/consumer pair:
- Producer (practice side): `learn/runtime.py:2570 _emit_live_beatmatch_grade` voices the grade and, for a credited locked edge, `grade_owned_beatmatch_attempt` writes `evidence_registry.write("ev","BEATMATCH_GRADED",t)` (the citable atom; `learn/practice_loop.py:81`). The receipt citation string is built at `learn/runtime.py:2597`.
- Consumer (live side): `runtime/coach.py:264 _credit_live_beatmatch_grade_receipts` polls the registry for fresh `BEATMATCH_GRADED` rows (`:295-299`), de-dupes via `seen_receipts` (`:307/:311`), freshness-gates to 2.0s (`:309`, `_BEATMATCH_GRADED_RECEIPT_FRESH_S` at `:113`), synthesizes the locked `Event` shape (`:312-322`), and feeds the generic `_credit_live_skill_demo` (`:324`) which runs the citation gate `evidence_registry.has(s,k,t,tol=1.0)` (`:215`).
- **It is genuinely CALLED in the live reaction loop:** `runtime/coach.py:643-651`, inside `while not stop_event.is_set()` (`:602`), every 100ms (`await asyncio.sleep(0.1)` `:603`), BEFORE the in_flight skip (`:654`). So at SRC the W12 path is wired, not just defined. Tests prove it: `tests/runtime/test_coach_skill_credit.py:263 test_live_beatmatch_grade_receipt_credits_beatmatching` (passes) and the de-dupe re-run at `:293`.

Why it is DARK at LIVE — three independent kills, any one of which is fatal:
1. **`learn_progress=None` on the live call site.** The live coach_loop runs inside `_activate_session` at `__main__.py:1989`, passing `learn_progress=None` (`:2010`) and `mastered_marker_writer=None` (`:2011`). The guard `if evidence_registry is None or learn_progress is None: return []` (`coach.py:286`) short-circuits. The only call site that passes `learn_progress=_learn_progress` is `__main__.py:3930` (`:3959`) — which is in the dead region past the `:2314` return.
2. **`state.session_active` never True in a plain live set.** The W12 guard `if not bool(getattr(state,"session_active",False)): return []` (`coach.py:288`) requires `MusicState.session_active`. That field is written ONLY by `state/refresh.py:1309` as `bool(course3_live and state.audible and aud_deck != "none")`, where `course3_live = _course3_session_lens_active(learn_state)` (`refresh.py:1308`). It is True only in the Course 3 live-set lesson lens, not a normal DJ set.
3. **`learn_state` not passed to the live refresh loop.** The live `state_refresh_loop` (inside `_activate_session`, `__main__.py:1973`) does NOT pass `learn_state` → `_course3_session_lens_active(None)` → `session_active` stays False. The only refresh call that passes `learn_state=_learn_state` is `__main__.py:3923` — again in the dead region.

Tests pass because they call `_credit_live_beatmatch_grade_receipts(... learn_progress=progress ...)` directly with a populated progress and `state.session_active=True` (`test_coach_skill_credit.py:77`). Classic test-passing-but-dark: the function is proven, the ship wiring is not.

- Stage verdict for the explicit question: **the receipt IS consumed by a wired consumer in `runtime/coach.py:643` for the LIVE-set credit path at SRC, but a real live set never reaches it (learn_progress=None + session_active=False).** It is, in effect, still practice-only at LIVE tier. file:line of the consumer call: `runtime/coach.py:643-651`. file:line of the dark gate: `__main__.py:2010` (learn_progress=None) + `__main__.py:1973` (no learn_state) + `coach.py:288` (session_active guard).

---

## LOOP CLOSURE AT HEAD — OBSERVE → GRADE → CARRY-TO-IPC → CREDIT → UNLOCK

Evaluated at two scopes. **Practice scope (in the Learn module) closes; Live-set scope (credit a live set) does not.** And ALL of it is currently behind the dead-code wall at LIVE tier (see headline).

| Stage | Closes? (SRC) | file:line | Closes at LIVE? |
|---|---|---|---|
| OBSERVE (audible practice) | Yes (practice) | `learn/runtime.py:2504` reads `snapshot.deck_state` via `_grade_beatmatch_practice_tick`; audio started for any deck-control lesson by `_is_beatmatch_practice_audio_lesson` `learn/runtime.py:797` | No — LessonRuntime not spawned (dead code) |
| GRADE | Yes | `learn/runtime.py:2505 grade_owned_beatmatch_state` + `:2528 grade_owned_beatmatch_attempt`; verdict math in `beatmatch_judge.py` | No (same) |
| CARRY-TO-IPC (`LearnLiveGrade`) | Yes | `learn/runtime.py:2617 LearnLiveGrade.make(...).to_dict()` → `:2623 self._ipc.emit`; driven by `live_grade_loop` `:3254` at ~6.7Hz (`sleep 0.15`) | No — `live_grade_loop` spawned at dead `__main__.py:3891` |
| CREDIT (practice) | Yes | `learn/runtime.py:2537` `if result.credited:` → `:2538 _emit_mastered_unlocks` + `:2550 save_progress` | No (same) |
| CREDIT (live set, W12) | Wired at SRC | `runtime/coach.py:643 _credit_live_beatmatch_grade_receipts` | No — `learn_progress=None` + `session_active` False (3 kills above) |
| UNLOCK (skill bar / Mastered) | Yes (practice) | `_emit_progress_snapshot` `learn/runtime.py:2558`; Earned-Wall live refresh `runtime/coach.py:340 _emit_earned_wall_refresh` (W-glue, wired into `_handle_live_skill_credits` `:587`) | No (same) |

**Net:** the teaching loop is genuinely CLOSED at SRC for practice (this CORRECTS the LEARN-PLAYABILITY-TEARDOWN line 107 "grade computed then DISCARDED" and the MEMORY diagnosis "grade computed then DISCARDED, runtime.py:2088" — recent learn fixes b6bdc4df / f6c50337 / c015cd6d / d67b85da etc. capture and voice the grade). The W12 live-set credit is wired into the reaction loop at SRC. But NONE of it executes at LIVE because the start-gate split orphaned the whole Learn runtime AND the live coach_loop call site passes `learn_progress=None`.

---

## INVARIANT #3 — practice audio never over a live set

- **Intact at SRC. LANDED.** `learn/two_deck_player.py:43-48 can_play()` returns `not (session_active and audible_deck != "none")` — refuses lesson audio whenever a live set is active and audible. This is the correct gate (matches CLAUDE.md: gated by lesson frozenset + `TwoDeckPlayer.can_play()`, NOT the dead `exemplar_audio_forbidden` flag — confirmed: zero `exemplar_audio_forbidden` references remain in the live gate path).
- Caveat: because `state.session_active` is itself only ever set in the Course-3 lens (refresh.py:1309) and the live refresh loop never passes `learn_state`, `session_active` is effectively always False at runtime today. The guard would not actually trigger in a normal set — but that is moot while the entire Learn runtime is dark. The invariant logic is correct; its input is dark. file:line: `two_deck_player.py:46` reads `state.session_active`; the field is starved by `__main__.py:1973`.

---

## "LAUNCHED SMOKE FAILURE" (`462157e7`) — resolved at HEAD?

- The commit is `462157e7 docs(learn): record launched smoke failure` (docs only, +104 lines). The run: `.planning/eval-runs/learn-tauri-smoke-current-20260604-054a6638/` at HEAD `054a6638`.
- What it actually was: the launched Tauri smoke **REACHED the Learn webview and COMPLETED the L1.01 flow** (`l101_completed=true`, `completed_lesson_id=L1.01`) but failed its quality phase on `passed=false` / `quality_ok=false` due to a single axe-core serious a11y violation: `aria-prohibited-attr` on `.learn-waveforms` (`tauri-smoke-failed.json` quality check #19). It is a **frontend a11y bug, not a teaching-loop break**. The README states "No tauri/ui source was edited in this Learn proof slice."
- **Not resolved at current HEAD.** The failure is on `.learn-waveforms` (a waveform element that NOW EXISTS — see below). The same violation is referenced in `learn-quality-current-20260604-054a6638/frontend-quality.json`. I found no commit since that removes an aria-prohibited attribute from `.learn-waveforms`. Verdict: **CLAIMED-BUT-DARK / OPEN (PKG/LIVE).** SRC: the smoke is informative — the flow completes; the a11y gate is red. Fix is a frontend WIRE (remove the prohibited ARIA attr from `.learn-waveforms`). Note this smoke ALSO confirms the launched Learn webview opens and L1.01 advances — but that is the frontend FSM with a mocked/standalone bridge, NOT proof the sidecar LessonRuntime is running (the headline dead-code finding still holds).

---

## TEARDOWN BLOCKERS — re-verified at HEAD (several built since LEARN-PLAYABILITY-TEARDOWN)

The teardown predates a wave of learn commits. Re-pinned status:

- **Blocker 1 (continuous mouse drag).** LANDED (SRC). `tauri/ui/src/learn/drag-control.ts` exists with `setPointerCapture` (`:172`), `pointermove`/`pointerup` (`:177-178`). Wired into the stage at `learn-window.ts:1220 stageEl.addEventListener("pointerdown", handleStageControlActivation)`; on drag start it emits a continuous `AnalogDragFrame` via `emitLearnAction(frame.controlId,"click",frame.value,...)` per move (`learn-window.ts:1204-1213`) and drives `stage.applyPositionFrame` (`:1203`). The teardown's "binary toggle, zero pointermove" is OUT OF DATE.
- **Blocker 2 (mixer acks → MiniDeck so dragging changes sound).** LANDED (SRC). `beatmatch_practice_driver.py:259 record_action` now routes `xfader` (`:271-276`), `vol`→`set_volume` (`:280`), `filter`→`set_filter` (`:281`), EQ (`:285`); `_MIXER_CONTROLS` (`:33`) now includes `eq_hi/eq_mid/eq_low/filter/vol`. MiniDeck (`audio/miniplayer.py`, NOT the teardown's wrong `learn/miniplayer.py` path) now has `vol_a`/`vol_b` (`:150-151`) applied as per-deck gain in `render_block` (`:233`).
- **Blocker 3 (audio in every practice lesson, not 4 of 38).** LANDED (SRC). `_is_beatmatch_practice_audio_lesson` (`learn/runtime.py:797`) is no longer a hardcoded 4-id frozenset; it dynamically returns True for any lesson whose expected action touches a deck control or xfader (`:820-825`), plus drill lessons (`:812`) and demo lessons (`:804`), excluding course_0 (`:802`). This is the WIRE the teardown asked for.
- **Blocker 4 (render waveforms).** LANDED (SRC, both ends wired). Frontend: `tauri/ui/src/learn/waveform-display.ts` exists; consumed at `learn-window.ts:428 WaveformDisplay(waveformHost)` + listeners `:1112` (`ipc.learn.waveform_ready`) and `:1117` (`ipc.learn.playhead_tick`); registered in `ws-client.ts:80-81`. Backend: emitters `learn/runtime.py:876 _emit_waveform_ready` → `:888 LearnWaveformReady.make` and `:903 _emit_playhead_tick` → `:915 LearnPlayheadTick.make`. Schema: `ipc.learn.waveform_ready` (`messages.schema.json:3235`) + `ipc.learn.playhead_tick` (`:3292`). The teardown's "100% absent" is OUT OF DATE. (But: dark at LIVE because the emitters run only inside the dead LessonRuntime, and the `.learn-waveforms` a11y gate is red — see smoke.)
- **Blocker 8 (capture+voice the grade, don't discard).** LANDED (SRC). `learn/runtime.py:2570 _emit_live_beatmatch_grade` captures the result, maps verdict→authored copy (`:2584-2590`), emits `LearnLiveGrade` (`:2617`) and `LearnTutorSpeak` with the `[ev:BEATMATCH_GRADED@t]` citation only on a locked edge (`:2594-2601`), uncited for drift/tempo_off/trainwreck, silent on abstain (`:2578`). Honest-grounded.
- **Blocker 9 (continuous live-grade tick).** LANDED (SRC). `live_grade_loop` (`learn/runtime.py:3254`) ticks at ~6.7Hz (`sleep 0.15` `:3258`), calling `_emit_playhead_tick` (`:3259`) + `_emit_live_beatmatch_grade_tick` (`:3260`). (Dark at LIVE — spawned at dead `__main__.py:3891`.)
- **Blocker 13 (generalize Mastered crediting to the learn module).** PARTIAL at SRC. The live-set generic credit (`_credit_live_skill_demo`) + the beatmatch receipt consumer (W12) exist; harmonic practice pair credit landed (`47982741 feat(learn): cite harmonic practice pair`). Whether EVERY skill has a learn-owned creditable Mastered event was not exhaustively verified this pass.

Blockers NOT re-verified this pass (out of LEARN-loop scope or lower priority): 5 (free-play sandbox), 6 (MOSS-by-default — note voice is now Chatterbox not MOSS, see other ingest), 10 (BPM readout), 11 (cue-placement faked-perfect input — `cue_placement_practice_driver.py` was touched by `7f1f31ab fix(learn): anchor cue grading to playhead`, worth a focused re-check), 12 (bundled demo tracks — `2b847c79 fix(learn): use bundled loops for practice waveforms` likely addresses), 14-21.

---

## TESTS (SRC tier) at HEAD

- `tests/runtime/test_coach.py` + `tests/runtime/test_coach_skill_credit.py`: **40 passed in 0.30s.** Includes W12 (`test_live_beatmatch_grade_receipt_credits_beatmatching`) and the session-inactive refusal (`test_beatmatch_grade_receipt_is_not_live_credit_when_session_inactive`).
- `tests/learn/`: **896 passed, 1 skipped** (opt-in live FLX4 jog, `VIBEMIX_LIVE_LEARN_JOG=1`).
- All learn SOURCE is committed (no `M src/vibemix/learn/` in the dirty tree; the only learn-related dirty file is `tauri/ui/tests/learn/test_ws_client_tauri_bridge.spec.ts`). Tree is 235 files dirty overall, almost all `.planning/eval-runs/` artifacts.

---

## SHIP-IMPACT SUMMARY (LEARN)

1. **TOP BLOCKER (LIVE, ship-critical): the LessonRuntime is unreachable.** The start-gate `main()` split (`__main__.py:2314` return) stranded all Learn wiring at `:3606`/`:3890`/`:3891`. Learn is a green test suite + a buildable bundle that never runs in the app. Fix = WIRE: lift LessonRuntime construction + `tick_loop` + `live_grade_loop` + learn IPC handler registration above the `:2314` return (Learn should run at idle, independent of Start). Until this lands, every Learn proof at LIVE tier is fiction.
2. **W12 live-set credit is dark on two more axes even after #1:** the live coach_loop passes `learn_progress=None` (`__main__.py:2010`) and the live refresh loop never passes `learn_state` (`:1973`) so `session_active` stays False (`coach.py:288` refuses). Fix = pass `_learn_progress` + `_learn_state` into the start-gate live path.
3. **Practice teaching loop is genuinely closed at SRC** (OBSERVE→GRADE→IPC→CREDIT→UNLOCK), correcting the prior "grade discarded" diagnosis — but inherits #1's darkness.
4. **Teardown headline gaps (drag, waveforms, mixer-audio, every-lesson-audio) were BUILT since the teardown** and are wired both-ends at SRC — the teardown doc is stale on these; rely on this re-pin.
5. **Invariant #3 logic is correct** (`two_deck_player.py:46`) but its input (`session_active`) is starved at runtime.
6. **The `462157e7` launched-smoke failure is OPEN:** a frontend a11y bug (`aria-prohibited-attr` on `.learn-waveforms`) blocks the quality gate; the L1.01 flow itself completes.
