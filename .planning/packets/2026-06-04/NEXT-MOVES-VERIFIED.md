# NEXT MOVES — VERIFIED (2026-06-04)

> Survivor opportunities only. Each move was re-verified against HEAD source or a reproduced run. These become the next `/goal` chunks. "What it buys" and "how to prove" are load-bearing — a move that cannot be proven by-ear or by-bus on current source does not ship.

## What to give each lane next

Ranked within each lane by leverage. The single highest-leverage verified move is listed first per lane.

### Sven — live co-host voice/coaching

**1. Direct assertion tests for the cue-lookahead voice line (WIRE, ~1h, no external gate — do FIRST).**
The new forward-coach branch (`_build_cue_lookahead_voice_line`) is a verified-untested grounding surface.
- *Buys:* a regression guard on the only new grounding code Sven shipped today, before anyone benches it.
- *Prove:* extend `tests/runtime/test_suggestion_voice.py` — assert the line plus a `[cue:...]` registry write when conf >= 0.7 and ETA in (0, 64]; assert `None` below floor, outside the window, when `next_phrase_cue_id` is None, and when `state=None`. Verify the body resolves in a fresh `EvidenceRegistry`. Cheapest move on the board.

**2. Run the Sven quality bench for real and commit the number (WIRE, ~2-3h, owner-gated on `RESPAN_API_KEY`).**
This is one task with a mandatory prerequisite, not a standalone bench run.
- *Buys:* turns "friend -> >=2" from aspiration into a committed artifact — the #1 voice gate currently has no run.
- *Prove:* first add `--match-live-persona` flipping `include_citation_grammar=True` so the sim judges the shipping prompt, not the wrong one. Then commit a result JSON under `.planning/eval-runs/sven-forward-coach-<date>/` showing gate 9/9 AND friend >=2 / voice >=2 on the two cue-lookahead scenarios, generated with the live-grammar persona. Do not claim "friend >=2 proven" until this artifact lands — running the bench without the flag produces a number that does not describe shipping behavior.

**3. Relabel the heartbeat-judge replay flag (~20min, local).**
Reframe, not rebuild. The replay's docstring already admits it cannot reconstruct old `event.extra` payloads.
- *Buys:* stops `--apply-current-gate` from implying "what the gate keeps" when it measures a no-payload worst case.
- *Prove:* rename `--apply-current-gate` -> `--describe-bank-census`; output string states the no-payload caveat. Reserve real payload-reconstruction only if a real corpus exists to validate against (it does not yet).

### Learn — hands-on practice + teaching loop

**1. Lock today's gains with one Course-1 by-ear/by-bus proof (PROVE, ~1-2h, zero new code — do FIRST).**
The 28-lesson audio and auto-advance are SRC-green but the only by-bus proof predates the commits that added them.
- *Buys:* converts today's biggest Learn gains from "tests pass" to "observed live at HEAD."
- *Prove:* via `drive-vibemix` / `VIBEMIX_DEV_SIDECAR=1`, capture L1.03/L1.14 EQ-audible + L1.13 waveform render + one auto-advance, recording the ws envelopes the way `4c0eed9a` did (`learn.waveform_ready` + `learn.tutor_speak` + a lesson-advance envelope) into a new eval-run doc.

**2. Anchor cue grade to deck playhead, not wall-clock (WIRE, ~15 lines).**
Verified feasible: `b_frame` is already in `playhead_payload`, `CuePlacementPracticeDriver` already accepts `cue_frame`, and the wall-clock `action_elapsed_s` path is the documented loose one.
- *Buys:* a deliberate learner stops getting penalized for taking time; cue grading becomes musically honest.
- *Prove:* unit test that a correct-frame press grades on-beat regardless of elapsed lesson time; by-bus confirm L2.10 voices the cited grade only on a real press; run `vibemix-grounding-review`.

**3. Light L1.09 (WIRE, trivial) — and gate the CUE-DETR-on-L1.13 idea, do not auto-build it.**
L1.09's only action is `master_vol` (no deck), so the gate's `if deck or control=="xfader"` skips it; add it to `_PRACTICE_AUDIO_DEMO_LESSONS` or special-case `master_vol`.
- *Buys:* one more lesson goes audible for a trivial change.
- *Caveat:* CUE-DETR (torch-free ONNX, in-tree at `library/cue_detr.py`) is validated on real techno/psy/house. Running it on L1.13's 22.5s **synthesized** 3-band loop is unlikely to yield meaningful intro/build/breakdown and could produce a worse map than the authored bands. Do not swap `_demo_cues()` against a synth loop; if pursued, validate CUE-DETR on a real bundled track first.

### Library — embeddings, key, cue, next-suggestion

**1. Add the missing regression guard (WIRE, leverage HIGH) — NOT the live-key wiring.**
The proposed live-key wiring already exists (`ingest.py:792`: `if compute_key and not key: estimate_key(...)`, `compute_key=True` default). The genuinely missing piece is the gate.
- *Buys:* protects the single most load-bearing gap — today any CLAP/CQT/profile change can silently drop 0.558 with every test green.
- *Prove:* add a CI test that re-scores a frozen ~20-track GiantSteps subset and fails below ~0.50 MIREX; confirm it goes red when CQT params are perturbed.
- *Hard boundary:* do NOT surface estimated keys as live co-host citations. `deck_poller.py:277` deliberately nulls `numpy_ks` keys so Sven never receives an estimated key as a citable deck fact. At 0.558 MIREX (~44% wrong) that suppression is correct Invariant-#3 discipline; reversing it is a slop regression. The offline next-suggestion/Viber path already consumes the estimated camelot — the right place for it.

**2. Get owner-labeled truth for auto-tags + a 2nd reference DJ for cue (small-medium).**
Both mechanisms are done and stuck at honest-null purely for lack of ground truth.
- *Buys:* flips `auto_tags` status from `unproven_no_hand_labels` to `ok` with per-category p@1, and tests whether cue-`0.236` generalizes; directly closes the one-owner-library risk.
- *Prove:* Kaan tags ~50 tracks (auto-tags) and confirms ~30 cues via the existing `--triplets` hook; a 2nd DJ XML gives cue a real generalization test. Wire `auto_tags` to a real caller afterward.

**3. Pivot cue placement from PSSI-phrase to CUE-DETR via the existing harness (after move 2).**
Verified feasible: `cue_detr.py` (MIT ONNX, torch-free) is in-tree and `cue_agreement.py` lives in product code (not just scripts) and scores any anchor source vs a DJ ref.
- *Buys:* a real shot at beating the `0.236` negative result with detected drops instead of phrase anchors.
- *Prove:* run cue-agreement with CUE-DETR anchors vs the 44 PSYMIND DJ cues; a number meaningfully above `0.236` proves the pivot. Best done after move 2 supplies a 2nd reference DJ so the pivot is not validated on one collection.

**4. Stop selling "section beats whole" (one-line honesty edit).**
- *Buys:* keeps the artifact honest; kills a low-value window-sweep before it starts.
- *Prove:* set `section_beats_whole=false` (or remove the boolean) and reword the headline to "comparable to whole-track; section vectors buy explainability, not raw accuracy." Re-bench only if move 2's larger labeled set (n>=100) lands for free.

### Frontend + Organism — Crate, settings, debrief, session, pill, organism

**1. Wire the organism's expressive layer to grounded learn/event signals (WIRE not build, small-medium — highest leverage in the lane).**
The focus/morph engine is fully built and unit-tested but unreachable from the renderer.
- *Buys:* the visual-grounding thesis (the organism lights up only for grounded events) finally reaches the human.
- *Prove:* add pass-through methods on `renderer.ts` (it exposes none for morph/focus today) plus bus-driven calls in `index.ts`. By-bus: fire a learn-focus/speak frame on `127.0.0.1:8765`, assert `MorphController.update()` returns `focusPhase:"holding"`; then by-eye in the opt-in mascot window via `drive-vibemix`. Drive focus ONLY off cited/detected events, never a free timer; route through `vibemix-grounding-review` before shipping.

**2. Runtime visual receipt (`?dev=organism-probe` + Playwright pixel-variance, small).**
Closes the one real SUSPECT gap: green CI cannot prove the GLSL compiles or blooms on the real WebView (vite ships the shader as a runtime string; jsdom never compiles WebGL).
- *Buys:* the first runtime proof that "real physics, blooms" is true and not just code-true.
- *Prove:* mirror the existing `?dev=mascot-mock` harness; Playwright is already wired for learn e2e. The harness is the proof: pixel-variance above threshold over N frames.

**3. End-to-end by-bus proof for conversational Crate (small).**
B2/chip -> `run()` -> Viber-answer is only by-eye + unit-tested today.
- *Buys:* a regression guard against a future CSS edit silently breaking submit.
- *Prove:* extend the existing `chat.test.ts` mock-Viber spec — click `[data-chat]`, assert a turn renders and the starters hide.

---

## Left behind / not there yet (gaps no lane currently owns)

- **One real captured set is the keystone, and no lane owns it.** Every lane's load-bearing proof (Sven friend score, Learn live HEAD reach, organism on a real WebView, the cloned voice reaching a human, the keystone itself) collapses into a single missing artifact: one sustained driven set with library enabled, captured with `invocations/` directories, on a stable master-capture device. This needs the one-socket / live-sidecar owner, not any read-only lane.
- **Audio-device-ranking instability is unowned.** The doctor recommends BlackHole 2ch in one run and 16ch 37 minutes later on the same rig. Nobody is chartered to find out why before the keystone set is captured.
- **Runtime engine-failure has no MOSS floor.** `build_chatterbox_adapter` returns a single-provider FallbackAdapter; a mid-session synth failure goes silent. Never-mute is proven for selection, not runtime. This is a genuine hole worth closing (add MOSS as a 2nd `FallbackAdapter` entry, prove via an injected failing engine asserting MOSS PCM emits) but no lane has claimed it.
- **Learn tutor voice unification.** `_build_learn_tutor_speak_audio` hardcodes MOSS; a chatterbox session speaks two voices. The fix is low-effort wiring (pass the selected provider into the tutor sink) but it sits between the Voice and Learn lanes and is currently orphaned.
- **No cross-lane grounding-review gate on the new organism + cue-lookahead reaction surfaces.** Both touch what the human sees/hears; neither has a committed grounding-review pass.
- **Full-tree gate suite is RED right now.** `tests/repo/test_no_seen_relaxation.py::test_stop_reason_writes_confined_to_toolset` fails because `src/vibemix/library/auto_crate.py` added a non-whitelisted `stop_reason` write — almost certainly a concurrent session's uncommitted work on the shared tree. This is B5/Viber-library territory. Whoever commits next must NOT absorb the `auto_crate.py` change.

---

## Owner-decision gates (Kaan only)

- **OPEN — cloned-voice provenance/licensing (HARD SHIP-BLOCKER).** The default Chatterbox ref `~/.cache/vibemix/cohost_voice_ref.wav` is a cloned recognizable real YouTube person -> right-of-publicity / takedown risk that can kill launch. The boundary is half-held already (the PyInstaller specs do not bundle the ref, `.cache/vibemix`, chatterbox, or mlx today). Keep it that way until Kaan/Francesco clear provenance or swap to a cleared reference asset. This gates every other Voice move.
- **OPEN — `mlx-audio` dependency decision.** Whether to add a macOS-only optional extra (none exists in `pyproject.toml` today) so the voice can reach the human. Base torch-free contract stays intact since it would be Apple-gated opt-in, but adding the dep is Kaan's call. Gates moves Voice-2 onward.
- **OPEN — device-ranking + keystone capture sign-off.** Which BlackHole device is the real master-capture path (2ch vs 16ch flips between runs), and the go-ahead to capture the keystone set. Live-sidecar / one-socket owner work.
- **OPEN — promote the organism out of opt-in.** Kaan deliberately set `visible:false` for rc1 (placeholder art + incomplete signature features hurt launch screenshots). After Frontend moves 1+2 land, propose the flip with the perf-fallback check (the `prefersReducedMotion` + `isWebGL2` guards at `renderer.ts:161-167` already exist). Do not flip autonomously.
- **OPEN — GiantSteps abstain policy.** The tuned run trades Invariant-#3 "don't assert what you can't ground" for 100% emission coverage. Add a confidence-threshold knob, bench `exact_accuracy_emitted` vs coverage at 2-3 thresholds, pick where emitted-accuracy stays high. Worth it for a DJ-facing key call.
- **OPEN — residual gamification vocabulary.** Whether to delete `src/pill/move-grade-vocabulary.ts` ("SEXY"/"overdrive" verbs, ships in bundle, reachable only in DEV demo) or keep it as a dev fixture.
- **RESOLVED — energy-scale.** Already resolved upstream; not a blocker.
- **RESOLVED — taste / privacy posture.** Already resolved upstream; not a blocker.

---

## SHARED LAW

One shared tree (`ux-redesign-impeccable`): commits survive, uncommitted gets WIPED by a sibling git op (proven today). `git add <exact paths>` NEVER `-A`; verify `git diff --cached`. IPC schema = FRONTEND lane ONLY. Sidecar `127.0.0.1:8765` = one socket: `pkill -f "python -m vibemix"` before any probe. Proof = by-ear/by-bus on current source + grounding-review on any co-host line. test-passing-but-dark = 0. `commit -s`, Kaan Ozkan <rahipdotaci@gmail.com>.
