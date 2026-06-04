# NEXT /goal PROMPTS — 2026-06-04 (paste-ready, one per lane)

Derived from `NEXT-MOVES-VERIFIED.md` (the EOD audit's survivor opportunities). Each
block is a complete copy-paste prompt for its session: it names the lane's file-island,
lists the verified moves in pull order (item 1 = do-first), states the proof bar
(by-ear / by-bus / a bench number, never green tests), and ends with the SHARED LAW.

The four islands are disjoint by file path, so no two sessions can stage the same file.
Pull order within a lane is top-to-bottom. The IPC schema is the Frontend lane's alone.

---

## ① SVEN — live co-host voice/coaching

Island: `src/vibemix/prompts/**`, `state/coach.py`, `state/event_detector.py`,
`state/evidence_registry.py`, `agent/dj_cohost.py`, `runtime/speak_gate.py`,
`runtime/suggestion_voice.py`, `llm/**`, `scripts/eval/respan_*`, their tests.

```
/goal Continue the Sven voice lane. Two verified moves from .planning/packets/2026-06-04/NEXT-MOVES-VERIFIED.md, in order. (1) DO FIRST, no gate, ~1h: add direct assertion tests for the new forward-coach branch `_build_cue_lookahead_voice_line` — it's the only new grounding code Sven shipped today and has zero coverage. Extend tests/runtime/test_suggestion_voice.py: assert the voice line PLUS a `[cue:...]` write to EvidenceRegistry when confidence >= 0.7 and ETA in (0, 64]; assert None below the floor, outside the window, when next_phrase_cue_id is None, and when state=None; verify the cited body resolves in a fresh EvidenceRegistry (Invariant #2). (2) Then run the Sven quality bench for real — but FIRST add a `--match-live-persona` flag that flips include_citation_grammar=True (sim sets False at respan_sven_sim.py:263, live sets True at dj_cohost.py:1345; without this the sim judges the wrong prompt and the number is fiction). Commit the result JSON under .planning/eval-runs/sven-forward-coach-<date>/ showing gate routing 9/9 AND friend >= 2 / voice >= 2 on the two cue-lookahead scenarios with grounded staying >= 2.4. Do not claim "friend >= 2 proven" without that artifact. THE VALIDATOR IS THE RESPAN NUMBER, NOT GREEN TESTS. Positive-framing prompts only (one generalizing target, never per-failure NOT-X); model_router for any literal; speech = local MOSS only; run vibemix-grounding-review before shipping any change to what/when Sven speaks. Your island: src/vibemix/prompts/**, state/coach.py, state/event_detector.py, state/evidence_registry.py, agent/dj_cohost.py, runtime/speak_gate.py, runtime/suggestion_voice.py, llm/**, scripts/eval/respan_*, and their tests. NOT library/, NOT tauri/ui, NOT the IPC schema.
SHARED LAW — one shared tree (ux-redesign-impeccable): commits survive, uncommitted gets WIPED by a sibling git op. git add <your exact paths> NEVER -A; verify git diff --cached shows only your files before committing. IPC schema = FRONTEND lane only. Sidecar 127.0.0.1:8765 = one socket: pkill -f "python -m vibemix" before any probe, stop it after. Proof = by-ear/by-bus on current source + grounding-review on any co-host line. test-passing-but-dark = 0. commit -s, identity Kaan Özkan <rahipdotaci@gmail.com>. Commit each piece atomically the moment it's green+proven.
```

---

## ② LEARN — hands-on practice + teaching loop

Island: `src/vibemix/learn/**`, `src/vibemix/audio/miniplayer.py`, their tests.
NOT `tauri/ui/src/learn/**` (Frontend's learn-window TS), NOT the IPC schema.

```
/goal Continue the Learn lane. Verified moves from .planning/packets/2026-06-04/NEXT-MOVES-VERIFIED.md, in order. (1) DO FIRST, zero new code, ~1-2h: lock today's gains with one Course-1 by-bus proof at HEAD. The 28-of-37 audible lessons and grade-to-advance are SRC-green but the only by-bus proof (4c0eed9a) predates the commits that added them. Via VIBEMIX_DEV_SIDECAR=1 / drive-vibemix, capture L1.03/L1.14 EQ-audible + L1.13 waveform render + one auto-advance, recording the ws envelopes the way 4c0eed9a did (learn.waveform_ready + learn.tutor_speak + a lesson-advance envelope) into a new .planning/eval-runs/ doc. (2) WIRE ~15 lines: anchor cue-placement grade to the deck playhead, not wall-clock — b_frame is already in playhead_payload and CuePlacementPracticeDriver already accepts cue_frame, so replace the wall-clock action_elapsed_s path. Add a unit test that a correct-frame press grades on-beat regardless of elapsed lesson time; by-bus confirm L2.10 voices the cited grade only on a real press. (3) TRIVIAL: light L1.09 — its only action is master_vol (no deck) so the audio gate skips it; special-case master_vol or add it to _PRACTICE_AUDIO_DEMO_LESSONS. Do NOT swap _demo_cues() to CUE-DETR against L1.13's synthesized loop (validate CUE-DETR on a real bundled track first if ever pursued). Preserve Invariant A1: can_play() must still refuse during a live audible set. Your island: src/vibemix/learn/**, src/vibemix/audio/miniplayer.py, and their tests. NOT tauri/ui/src/learn/** (that learn-window TS is the Frontend lane) and NOT the IPC schema — if you need a new learn IPC type, stop and request it from Frontend.
SHARED LAW — one shared tree (ux-redesign-impeccable): commits survive, uncommitted gets WIPED by a sibling git op. git add <your exact paths> NEVER -A; verify git diff --cached shows only your files before committing. IPC schema = FRONTEND lane only. Sidecar 127.0.0.1:8765 = one socket: pkill -f "python -m vibemix" before any probe, stop it after. Proof = by-ear/by-bus on current source + grounding-review on any co-host line. test-passing-but-dark = 0. commit -s, identity Kaan Özkan <rahipdotaci@gmail.com>. Commit each piece atomically the moment it's green+proven.
```

---

## ③ LIBRARY — embeddings, key, cue, next-suggestion

Island: `src/vibemix/library/**`, `src/vibemix/intel/**`, `scripts/eval/**`, their tests.
NOT `tauri/ui`, NOT the IPC schema, NOT prompts/state/agent (Sven's).

```
/goal Continue the Library/Engine lane. Verified moves from .planning/packets/2026-06-04/NEXT-MOVES-VERIFIED.md, in order. (1) HIGHEST LEVERAGE, do first: add the missing accuracy regression guard. The live-key wiring already exists (ingest.py:792, compute_key=True default) — what's missing is the gate. Today any CLAP/CQT/profile change silently drops the 0.558 MIREX with every test green. Add a CI test that re-scores a frozen ~20-track GiantSteps subset and fails below ~0.50 MIREX; prove it goes RED when CQT params are perturbed. HARD BOUNDARY: do NOT surface estimated keys as live co-host citations — deck_poller.py:277 deliberately nulls numpy_ks keys so Sven never gets an estimated key as a citable deck fact; at ~44% wrong that suppression is correct Invariant-#3 discipline and reversing it is a slop regression. The offline next-suggestion/Viber path is the right consumer for the estimated camelot. (2) ONE-LINE HONESTY EDIT: stop selling "section beats whole" — the section_beats_whole=true claim rests on +0.026 at n=38 and reverses on every other metric (centered p@5 -0.137, raw p@1 -0.158, whole-track MRR 0.695 > 0.678). Set it false / remove the boolean and reword the headline to "comparable to whole-track; section vectors buy explainability, not raw accuracy." NO accuracy claim ships without its bench number. (NOTE: the auto-tags / 2nd-DJ-cue moves are owner-gated on Kaan supplying labeled truth — do NOT start them yet; and the full-tree gate is currently RED on auto_crate.py's non-whitelisted stop_reason write, B5/Viber territory — fix that in the toolset whitelist or revert, do not absorb it blind.) Your island: src/vibemix/library/**, src/vibemix/intel/**, scripts/eval/**, and their tests. NOT tauri/ui, NOT the IPC schema, NOT prompts/state/agent (Sven's).
SHARED LAW — one shared tree (ux-redesign-impeccable): commits survive, uncommitted gets WIPED by a sibling git op. git add <your exact paths> NEVER -A; verify git diff --cached shows only your files before committing. IPC schema = FRONTEND lane only. Sidecar 127.0.0.1:8765 = one socket: pkill -f "python -m vibemix" before any probe, stop it after. Proof = by-ear/by-bus on current source + grounding-review on any co-host line. test-passing-but-dark = 0. commit -s, identity Kaan Özkan <rahipdotaci@gmail.com>. Commit each piece atomically the moment it's green+benched.
```

---

## ④ FRONTEND — Crate, settings, debrief, session, pill, organism

Island: ALL `tauri/ui/src/**` + the IPC schema (sole owner) + `src/vibemix/ui_bus/*.py`
+ `scripts/check_ipc_schema.py`. NOT any other `src/vibemix/**` Python.

```
/goal Continue the Frontend/Organism lane (impeccable + frontend-enforcement). Verified moves from .planning/packets/2026-06-04/NEXT-MOVES-VERIFIED.md, in order. (1) HIGHEST LEVERAGE: wire the organism's expressive layer to grounded signals. The morph/focus engine (morphToPill/morphToMask/focusAt/reform on MorphController) is fully built and unit-tested but UNREACHABLE — renderer.ts exposes only tick/setSignals/enableBloomLayer/dispose and index.ts has no path to focus or morph. Add pass-through methods on renderer.ts plus bus-driven calls in index.ts. By-bus proof: fire a learn-focus/speak frame on 127.0.0.1:8765 and assert MorphController.update() returns focusPhase:"holding"; then by-eye in the opt-in mascot window via drive-vibemix. Drive focus/morph ONLY off cited or detected events (voice RMS, detected beat, teaching focus, MIDI) — NEVER a free timer; random animation = failure. Run vibemix-grounding-review before shipping. If this needs the ipc.learn.teaching_focus {control_id,deck,band,phase} schema section, add it (you own the schema) and run npm run codegen:ipc + the ipc-wiring-checker. (2) RUNTIME VISUAL RECEIPT: add a `?dev=organism-probe` harness mirroring `?dev=mascot-mock` and a Playwright pixel-variance check — green CI cannot prove the GLSL compiles or blooms on a real WebView (jsdom never compiles WebGL); the harness is the proof (pixel-variance above threshold over N frames). (3) SMALL: extend chat.test.ts so a chip/B2 click -> run() -> Viber-answer asserts a turn renders and the starters hide. Verify on the real rig by eye, not just vitest. Your island: ALL tauri/ui/src/** (session, settings, debrief, pill, shell, Crate, mascot/organism, learn-window TS) + the IPC schema (you are its SOLE owner) + src/vibemix/ui_bus/*.py + scripts/check_ipc_schema.py. NOT any other src/vibemix/** Python.
SHARED LAW — one shared tree (ux-redesign-impeccable): commits survive, uncommitted gets WIPED by a sibling git op. git add <your exact paths> NEVER -A; verify git diff --cached shows only your files before committing. You own the IPC schema; backend lanes request types from you. Sidecar 127.0.0.1:8765 = one socket: pkill -f "python -m vibemix" before any probe, stop it after. Proof = by-eye/by-bus on current source. test-passing-but-dark = 0. commit -s, identity Kaan Özkan <rahipdotaci@gmail.com>. Commit each surface the instant it's green+proven.
```
