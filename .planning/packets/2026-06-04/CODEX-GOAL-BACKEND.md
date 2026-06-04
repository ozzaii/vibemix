# CODEX GOAL — ENGINE / BACKEND

Worktree: /Users/ozai/projects/qa-backend (branch qa/backend). Touch `src/vibemix/` ONLY.

MISSION: Make Sven a COACH, not a narrator — then keep deepening the whole engine in this one lane. A real set feeds NO MIDI and no per-deck audio, so Sven must coach from the master mix alone (band/LUFS/brightness deltas, energy arc, phrase/phase, BPM, library next-suggestion). Today he is a grounded narrator.

DONE = your self-check (run it to decide BOTH "what next" and "am I there yet"):
`set -a; . ./.env; set +a; uv run python scripts/eval/respan_sven_sim.py --strict-sven-gate`
clears friend·earned·voice ≥ 2.0, grounded ≥ 2.4, should-NOT-spoken == 0. Baseline measured on 137 real lines: grounded 2.08 but friend 0.09 / 137-of-137 should-not-spoken. When that holds, the engine has more than Sven — keep climbing: Debrief (close session→lesson/profile + cite real moments; verify `uv run python -m vibemix --debrief <session>` makes a TLDR + resolving citations), Viber/library (keyless `auto_crate` returns grounded JSON, no login), intel→voice (`move_grade` gets a live receipt). Each its own measurable check.

HOW TO WORK — do NOT restart, do NOT tunnel:
- Plan your own steps toward the measurable DONE. Pick the next step from the GAP (the lowest failing dim), never from a fixed list.
- Build → run the gate → fix toward the worst number → re-run. Keep a `BASELINE.json`; never commit if any dim regressed (tests-green-but-worse = revert).
- Commit each real gain surgically (`git add <exact paths>`, never `-A`; verify `git diff --cached --name-only`) ending the message with:
  `QA-LANE: backend` / `QA-ITEM: <slug>` / `QA-VERIFY: <the gate cmd>` / `QA-PASS: <true|false>` — a pass is trusted only if QA-VERIFY reproduces it (tests-green-but-dark = 0).
- Loop until the gate is green across the board. Halt only on a hard blocker (write it down, switch to another angle of the mission). Never idle waiting on anyone.

ORIENTATION (pointers to save you time — re-derive, this is NOT a script to execute top-down): energy-read receipt → new `runtime/energy_read_voice.py` from `suggestion["transition"]` score/reasons/risks + `render_audio_delta_items(state)`; relax `transition_verdict_voice.py:51-54` (drop the A/B-deck requirement); register a new `[energy:...]` source in `evidence_registry.py`; add its key to `speak_gate.py:21`; wire in `coach.py:880-901`. Coach-vs-narrate signal → `events.jsonl` (`coach.py` ~:1029/1065). Silence abstention-slop + describe-bank without a grounded payload in `speak_gate.py`.

LAW: `src/vibemix/` only. AVOID `__main__.py` (single-owner — if a step truly needs it, stop + report, don't clobber). One socket `127.0.0.1:8765` (don't launch a second instance). Positive framing always (describe the target, never NOT-X). Commit `-s Kaan Özkan <rahipdotaci@gmail.com>`. Not yours: the frontend (UX lane), notarize/signing/tags (Kaan).
