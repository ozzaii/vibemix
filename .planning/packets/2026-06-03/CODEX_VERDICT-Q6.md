# CODEX VERDICT — Q6 octave-fold phase bug

- Item: Q6 — fold half/double beatmatch phase into a common beat domain.
- SHA: `44e1ecd3 fix(learn): fold octave phase comparison`
- User value: a beginner practicing half/double tempo matching no longer gets a false trainwreck when the decks are actually locked.
- Proof: `uv run pytest -q tests/learn/test_beatmatch_judge.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_practice_loop.py tests/learn/test_runtime_evidence_grounding.py` -> 34 passed.
- By-eye/by-ear note: this is the math layer under the B1 audible deck path; no new speech or UI was added. Full audible L2.01 proof remains part of the fused Q3/B1/B2/B3 ship gate.
- Grounding: no co-host say/when change.
- Packet assumptions: correct. The bug was the un-folded phase compare, not the octave multiplier.
