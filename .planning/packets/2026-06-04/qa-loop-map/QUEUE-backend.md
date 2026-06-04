# QUEUE — BACKEND/ENGINE lane (Sven keystone first, then deepen). Pull top, loop, no regression.

> Goal: `.planning/packets/2026-06-04/CODEX-GOAL-BACKEND.md`. Sven gate: `respan_sven_sim.py` (fast) + the driver's `qa_loop_run.py` real-audio verdict. Baseline (2026-06-02, MIDI-flattered): friend 0.09 / earned 0.06 / move 0.10 / voice 0.20 / grounded 2.08 / should-NOT-spoken 137. Targets: friend·earned·voice ≥ 2.0, grounded ≥ 2.4, should-NOT-spoken == 0.

## Keystone — Sven coaches from AUDIO alone (do 1+2 before the gate)
- [ ] 1. Energy-read voice receipt — audio-only, no A/B deck, no MIDI. New `[energy:...]` source. (`runtime/energy_read_voice.py`, `transition_verdict_voice.py:51-54`, `coach.py:880-901`, `speak_gate.py:21`, `evidence_registry.py`)
- [ ] 2. Coach-vs-narrate per-turn signal → `events.jsonl`. (`coach.py` ~:1029/1065)
- [ ] 3. Speak-gate "earned" — silence abstention-slop + describe-bank w/o grounded payload → should-NOT-spoken 0. (`speak_gate.py`)

## Then deepen (continuous loop, after Sven gate green — the whole engine, ONE lane)
- [ ] 4. Debrief (overlooked engine): close session→lesson/profile loop + cite real moments. (`debrief/*`; verify `--debrief <session>` TLDR + citations resolve)
- [ ] 5. Viber/library: richer keyless `auto_crate` + real `[viber-tool]` tape + CLAP/CUE coverage. (`library/*`; verify grounded JSON no login)
- [ ] 6. intel→voice: `move_grade` live receipt; per-deck-on for two-deck rigs. (`intel/move_grade.py`, `deck_capture.py:514`)
- [ ] (stretch) Non-causal master-mix move-direction receipt when `moves` empty. (`deck_context.py:2688`)
- [ ] (replenished) lowest verdict dim → next item, from the driver's `qa-verdict.json`.

When queue dry AND all targets met → `DONE-ALL-backend.md`. Hard blocker → `BLOCKED-backend.md` + continue an unblocked item.
