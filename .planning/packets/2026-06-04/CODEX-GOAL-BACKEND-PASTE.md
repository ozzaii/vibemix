# CODEX GOAL — BACKEND (Sven coaches from AUDIO alone)

Worktree: /Users/ozai/projects/qa-backend (branch qa/backend). Island: `src/vibemix/` ONLY. HEAD 364c55ba. Full ref in-tree: `.planning/packets/2026-06-04/CODEX-GOAL-BACKEND.md`.

KEYSTONE: A real set has NO MIDI + NO per-deck audio → the eq-move guard never fires, Judge+scorer abstain (two-deck-gated) → Sven narrates. Measured on 137 real lines: grounded 2.08 but friend 0.09 / earned 0.06 / voice 0.20, 137/137 should-NOT-spoken. Make Sven COACH from master-mix AUDIO alone (band/LUFS/brightness deltas, energy arc, phrase/phase, BPM, library next-suggestion) — no MIDI, no two-deck.

QUEUE (do 1+2 before touching the gate):
1. Energy-read voice receipt, audio-only, no A/B deck. New `runtime/energy_read_voice.py` (or a fn in `transition_verdict_voice.py`): citable receipt from `suggestion["transition"]` score/reasons/risks + `render_audio_delta_items(state)`; relax `transition_verdict_voice.py:51-54` (drop source/target_deck req); register a NEW `[energy:...]` source in `state/evidence_registry.py`; add its key to `speak_gate.py:21` `_GROUNDED_VOICE_EXTRA_KEYS`; wire in `coach.py:880-901`.
2. Coach-vs-narrate per-turn signal into `events.jsonl` (which grounded key vs the music-direction fallback). `coach.py` ~:1029/1065.
3. Speak-gate "earned": silence abstention-slop ("I can't tell from this live proof" = silence, not voiced) + describe-bank without a grounded payload. Drive should-NOT-spoken → 0. `speak_gate.py`.
4. (stretch) Non-causal master-mix move-direction receipt when `moves` empty. `deck_context.py:2688`.

GATE (self-QA, no human): fast = `uv run python scripts/eval/respan_sven_sim.py --gate-only` (keyless, must stay 9/9) + `--strict-sven-gate` (keyed: `set -a; . ./.env; set +a` first). Targets: friend·earned·voice ≥ 2.0, grounded ≥ 2.4, should-NOT-spoken == 0.

LOOP (do NOT stop): pull `QUEUE-backend.md` top → build → gate green (criticize + fix your own change, never advance red) → REGRESSION GUARD: re-run the full gate vs `BASELINE.json`, never commit if any dim dropped → commit with the trailer → self-critique (worst dim = next item) → repeat. Halt only when queue dry AND all dims ≥ target (write `DONE-ALL-backend.md`) or a hard blocker (`BLOCKED-backend.md` + continue an unblocked item). Never idle waiting on Claude/Kaan.

COMMIT TRAILER (machine-checked, not asserted):
QA-LANE: backend
QA-ITEM: <energy-read | coach-vs-narrate | speak-gate-earned>
QA-GATE: sven_prose
QA-VERIFY: set -a; . ./.env; set +a; uv run python scripts/eval/respan_sven_sim.py --strict-sven-gate
QA-PASS: <true|false>

LAW: `src/vibemix/` ONLY. AVOID `__main__.py` (single-owner; audio-only coaching does NOT need the deck-capture default) — if forced, STOP + report, never clobber. `git add <exact paths>` NEVER `-A`; verify `git diff --cached --name-only`; one socket :8765 (the driver owns the live instance); positive prompt framing (describe the TARGET, never NOT-X); commit `-s Kaan Özkan <rahipdotaci@gmail.com>`.
OUT OF SCOPE: vision judge, MOSS→Chatterbox frontend (UX lane), per-deck routing, notarize/signing (Kaan).
