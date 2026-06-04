# CODEX GOAL — ENGINE/BACKEND (Sven keystone first, then deepen the WHOLE engine)

Worktree: /Users/ozai/projects/qa-backend (branch qa/backend). Island: `src/vibemix/` ONLY. HEAD 364c55ba.

You own the WHOLE engine, not just Sven — and this stays ONE lane (no extra Codex for the deeper work). Sven is the keystone (the measured soul-gap) — clear it FIRST, then the continuous loop deepens into Debrief, Viber, intel. This lane is the deepest; don't stop at Sven.

KEYSTONE — Sven coaches from AUDIO alone. A real set has NO MIDI + no per-deck audio → eq-move guard silent, Judge+scorer abstain (two-deck) → narrator. Measured on 137 real lines: grounded 2.08 but friend 0.09 / earned 0.06 / voice 0.20, 137/137 should-NOT-spoken. Coach from master-mix audio (band/LUFS/brightness deltas, energy arc, phrase/phase, BPM, library next-suggestion), no MIDI/two-deck.
1. Energy-read voice receipt, audio-only, no A/B deck. New `runtime/energy_read_voice.py`: receipt from `suggestion["transition"]` score/reasons/risks + `render_audio_delta_items(state)`; relax `transition_verdict_voice.py:51-54`; new `[energy:...]` source in `evidence_registry.py`; add key to `speak_gate.py:21`; wire `coach.py:880-901`.
2. Coach-vs-narrate signal → `events.jsonl` (`coach.py` ~:1029/1065).
3. Speak-gate "earned": silence abstention-slop + describe-bank without a grounded payload → should-NOT-spoken 0. `speak_gate.py`.

THEN DEEPEN (continuous loop, after the Sven gate is green — the engine has more than Sven):
4. Debrief (the overlooked engine): close session→lesson/profile loop + cite real moments. `debrief/*`. Verify: `uv run python -m vibemix --debrief <session>` headless produces a TLDR + drill citations that resolve (GEMINI key or seeded cache).
5. Viber/library: richer keyless `auto_crate` + real `[viber-tool]` tape + CLAP/CUE coverage. `library/*`. Verify: auto_crate returns grounded JSON with no login.
6. intel→voice: `move_grade` live receipt (`intel/move_grade.py` has no live caller today); per-deck-capture-on for real two-deck rigs (`deck_capture.py:514`). Verify: sim + unit tests.

GATE (Sven, fast): `uv run python scripts/eval/respan_sven_sim.py --gate-only` (keyless, stay 9/9) + `--strict-sven-gate` (keyed: `set -a; . ./.env; set +a`). Targets: friend·earned·voice ≥ 2.0, grounded ≥ 2.4, should-NOT-spoken == 0. Each deeper surface uses its own verify (above).

LOOP (do NOT stop): pull `QUEUE-backend.md` top → build → gate green (criticize + fix your own change, never advance red) → REGRESSION GUARD: re-run the gate vs `BASELINE.json`, never commit if any dim dropped → commit with the trailer → self-critique (worst dim/surface = next) → repeat. Halt only when queue dry AND targets met (`DONE-ALL-backend.md`) or a hard blocker (`BLOCKED-backend.md` + continue an unblocked item). Never idle on Claude/Kaan.

TRAILER: `QA-LANE: backend` / `QA-ITEM: <...>` / `QA-GATE: <sven_prose|debrief|viber|intel>` / `QA-VERIFY: <the gate cmd>` / `QA-PASS: <true|false>`. Machine-checked, not asserted.

LAW: `src/vibemix/` ONLY. AVOID `__main__.py` (single-owner — if a deeper item needs it, e.g. per-deck default `:1503`, STOP + report, don't clobber). `git add <exact paths>` NEVER `-A`; verify `git diff --cached --name-only`; one socket :8765 (driver owns it); positive framing (describe the TARGET, never NOT-X); commit `-s Kaan Özkan <rahipdotaci@gmail.com>`.
OUT: vision judge, frontend MOSS→Chatterbox (UX lane), notarize/signing (Kaan).
