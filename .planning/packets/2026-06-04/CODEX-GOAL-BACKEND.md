# CODEX GOAL — BACKEND lane (Sven becomes a coach from AUDIO alone)

> Paste this whole block as the Codex goal. File island: `src/vibemix/` only. Verified against `ux-redesign-impeccable` HEAD `364c55ba` (2026-06-04). The QA loop (`scripts/eval/qa_loop_run.py`) measures you.

## The one thing (keystone)

On a real set there is **NO MIDI move and NO per-deck audio** reaching Sven (master-only rig / audio-only replay). Today that means the eq-move guard never fires, the Vibe Judge + transition scorer abstain (two-deck-gated), so Sven has **zero grounded coaching evidence** and falls to the prompt's "coach the music's direction" branch = **narration dressed as coaching**.

**Measured, real lines, 2026-06-02 capture (137 judged, 0 errors):** grounded **2.08**, but friend **0.09**, earned **0.06**, move **0.10**, voice **0.20**, and **137/137 should-NOT-have-spoken**. Sven is grounded but a narrator. (That fixture even HAD MIDI; audio-only is harder.)

**Your job: make Sven coach from MASTER-MIX AUDIO alone — no MIDI, no two-deck.** The audio replay carries band/LUFS/brightness deltas, energy arc, phase/phrase transitions, BPM, and the library next-suggestion (score/reasons/risks). Turn those into ONE forward coaching read per spoken turn ("you've ridden this groove 6 min, energy's flat, a breakdown resets tension" / "highs have been empty 3 phrases, a brighter layer lifts it"), grounded by a real evidence citation, and SILENCE everything that isn't earned.

## Bounded queue (ordered — do 1+2 before touching the gate)

1. **Energy-read voice receipt (audio-only, no A/B deck requirement).** Add a master-mix branch (new `src/vibemix/runtime/energy_read_voice.py`, or a sibling fn in `runtime/transition_verdict_voice.py`) that builds a citable forward-coaching receipt from `suggestion["transition"]` score/reasons/risks + `render_audio_delta_items(state)` (band/LUFS/brightness) + energy-arc — WITHOUT requiring `source_deck`/`target_deck` (relax `transition_verdict_voice.py:51-54`). Register a NEW grounded evidence source (e.g. `[energy:...]`) in `state/evidence_registry.py` so it survives the strip guard. Attach to `ev.extra` as a new speak-gate grounded key; add that key to `runtime/speak_gate.py:21` `_GROUNDED_VOICE_EXTRA_KEYS`. Wire in `runtime/coach.py:880-901` next to the other voice-line builders.
2. **Coach-vs-narrate per-turn signal.** In `runtime/coach.py` (near the `recorder.log_event` sites ~`:1029/:1065`), log per spoken turn whether the line carried a grounded coaching receipt (which key) vs fell to the no-evidence music-direction branch. This is what lets the QA loop *measure* coach-vs-narrate instead of a human ear. Emit it into `events.jsonl`.
3. **Tighten the speak-gate for "earned" (137/137 should-not-speak is the failure).** Silence the abstention-slop: lines like "I can't tell from this live proof whether the control caused that" must be **silence, not voiced** (the judge correctly scored these 0/useless). Raise the bar so HEARTBEAT/PHASE without a grounded coaching payload stay silent (extend `runtime/speak_gate.py` describe-bank handling). Target: `should_NOT_have_spoken` → 0 and `earned_not_constant` ≥ 2.
4. **(stretch) Non-causal master-mix move-direction receipt** when `moves` is empty (`state/deck_context.py:2688` early-returns `if not moves`) so Sven can say "the lows just pulled back, ride it" from audio deltas alone (positive-framed, no causal claim).

## Self-QA gate (you run this, no human)

- **FAST inner loop (iterate prompt/gate logic, seconds):** `respan_sven_sim.py` — keyless routing floor `uv run python scripts/eval/respan_sven_sim.py --gate-only` (must stay 9/9); keyed quality `--strict-sven-gate` when `RESPAN_API_KEY` is in env (`set -a; . ./.env; set +a`). The sim is authored scenarios — fast, no 98-min replay.
- **AUTHORITATIVE pass (real audio, the driver runs it):** `scripts/eval/qa_loop_run.py --session <audio-only replay capture>` → `vibemix_qa_verdict_v1`. Gate passes only when friend/earned/voice ≥ 2.0, grounded ≥ 2.4, should-NOT-have-spoken == 0.
- **Do NOT commit a "pass" on green tests alone.** Tests-green-but-narrator = 0. The gate is the sim (fast) + the driver's real-audio verdict (authoritative).

## Done-signal (commit trailer, machine-checked — not asserted)

Each completed item ends its commit message with:
```
QA-LANE: backend
QA-ITEM: <energy-read-receipt | coach-vs-narrate-signal | speak-gate-earned>
QA-GATE: sven_prose
QA-VERIFY: set -a; . ./.env; set +a; uv run python scripts/eval/respan_sven_sim.py --strict-sven-gate
QA-PASS: <true|false>
```
"Pass" is trusted only if the driver can re-run QA-VERIFY and reproduce it. A marker without a reproducible verdict = FAIL.

## Island + law

ISLAND: `src/vibemix/` ONLY (runtime/, prompts/, state/, intel/). Do NOT touch `tauri/` or `library_cmds.rs` (UX lane). AVOID `__main__.py` (single-owner; audio-only coaching does NOT need the deck-capture default at `:1503-1507` — skip it). If you must edit `__main__.py`/`config_store.py`, STOP and report instead of clobbering.
LAW: work in your worktree branch `qa/backend`; `git add <exact paths>` NEVER `-A`; verify `git diff --cached --name-only`; one socket `127.0.0.1:8765` (the driver owns the live instance — do not launch a second); commit `-s Kaan Özkan <rahipdotaci@gmail.com>`.
PROMPTING: positive framing only — describe the coaching TARGET, never NOT-X (diffusion latches the negated concept).

## LOOP PROTOCOL (do NOT stop after one item — ship continuously, self-critique, NO regression)

You run a continuous overnight loop. You do not halt to wait for anyone.
1. **Pull** the top item from your on-disk queue `.planning/packets/2026-06-04/qa-loop-map/QUEUE-backend.md`.
2. **Build** it.
3. **Self-QA** the lane gate (sim: `--gate-only` keyless floor + `--strict-sven-gate` keyed). If red, **criticize your own change and fix it** until the gate passes — never advance on a red gate.
4. **REGRESSION GUARD (the no-regression rule):** before committing, re-run the FULL gate and compare every dim to `BASELINE.json` (create it on first pass from the current numbers). If ANY dim dropped vs baseline, you regressed — revert or fix until baseline is held-or-improved. **Never commit a regression.**
5. **Commit** with the trailer (only when gate green AND no regression). Update `BASELINE.json` to the new improved numbers. Append the item to `DONE.log`.
6. **Self-critique → next:** read the latest verdict's worst dim + worst lines (`worst_lines`). If the queue is dry, the lowest-scoring dim becomes your next item. Keep climbing until ALL gate dims ≥ target (friend/earned/voice ≥ 2.0, grounded ≥ 2.4, should-NOT-spoken == 0).
7. **Repeat.** HALT only when (a) all gate dims ≥ target AND queue dry → write a `DONE-ALL` marker, or (b) a hard blocker you cannot resolve (single-owner-file collision, missing dep, genuinely ambiguous spec) → write a `BLOCKED.md` with the reason and continue with any other unblocked queue item. Never sit idle waiting on Claude/Kaan. The keystone ear-pass is Kaan's, but it does NOT gate your loop — keep improving the measured dims.

## Out of scope
- The vision/UX judge, the MOSS→Chatterbox frontend (UX lane).
- Per-deck capture default / two-deck routing (real-rig follow-up, not the audio-only keystone).
- Apple notarize / signing / GA tag (Kaan).
