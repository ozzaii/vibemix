# QUEUE — BACKEND lane (Sven coach-from-audio). Pull top, loop, no regression.

> Goal contract: `.planning/packets/2026-06-04/CODEX-GOAL-BACKEND.md`. Gate: `respan_sven_sim.py` (fast) + the driver's `qa_loop_run.py` real-audio verdict. Baseline to beat (2026-06-02, MIDI-flattered): friend 0.09 / earned 0.06 / move 0.10 / voice 0.20 / grounded 2.08 / should-NOT-spoken 137. Targets: friend·earned·voice ≥ 2.0, grounded ≥ 2.4, should-NOT-spoken == 0.

- [ ] 1. Energy-read voice receipt — audio-only, no A/B deck, no MIDI. New grounded `[energy:...]` source. (`runtime/energy_read_voice.py` or `transition_verdict_voice.py`, `coach.py:880-901`, `speak_gate.py:21`, `evidence_registry.py`)
- [ ] 2. Coach-vs-narrate per-turn signal into `events.jsonl` (so the loop measures the gap). (`coach.py` ~`:1029/1065`)
- [ ] 3. Speak-gate "earned" — silence abstention-slop + describe-bank without a grounded coaching payload. Drive should-NOT-spoken → 0. (`speak_gate.py`)
- [ ] 4. (stretch) Non-causal master-mix move-direction receipt when `moves` empty. (`deck_context.py:2688`)
- [ ] (replenished) lowest verdict dim → next item, from the driver's `qa-verdict.json`.

When queue dry AND all dims ≥ target → write `DONE-ALL-backend.md`. Hard blocker → `BLOCKED-backend.md` + continue an unblocked item.
