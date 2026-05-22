---
status: partial
phase: 66-visible-copilot-move
source: [66-VERIFICATION.md]
started: 2026-05-22
updated: 2026-05-22
---

## Current Test

[awaiting human testing — Kaan-action on the live/real-corpus clock]

## Tests

### 1. Transition-shape callback grounds on a real past move (COPILOT-01)
expected: After `export VIBEMIX_RECALL_ENABLED=1` and a live DJ set with at
least one TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL where the memory store has
a relevant past move, the AI emits ONE callback line carrying `[recall:<id>]`
and the recall chip surfaces alongside the existing ev/mix/midi/key chips on
the citation_strip. The past-tense framing must be honest (compares NOW to
THEN, "killed the bass earlier this time around" style — not scripted,
not nagging, not hallucinated). No "you tend to" / "you usually" phrases;
no "next track" recommendation. A fabricated past moment is impossible by
design — the Phase 65 anti-poisoning gate strips the whole turn before the
chip can surface.
result: [pending]

### 2. Vocabulary callback echoes prior phrasing in Kaan's voice (COPILOT-02)
expected: On a PHASE event where the past survivor list carries one of
Kaan's prior phrasings, the AI echoes Kaan's own words (quote-shape, not
Gemini-paraphrased — research §Pitfall 4's explicit anti-paraphrase
failure mode is the load-bearing ear-check here). Citation `[recall:<id>]`
present once; the past signature is read as PAST-tense never as live;
cooldown rare; no nagging.
result: [pending]

### 3. Cooldown discipline by ear (COPILOT-02)
expected: Across a multi-set listen, no more than ~1 recall callback per
~2 minutes; never two callbacks back-to-back inside the same 120s window.
If two callbacks land within 120s of each other (whether transition-shape
or vocabulary), that is a bug — the coach-tier cooldown
(`RECALL_CALLBACK_COOLDOWN_S=120.0`) is broken. The unit test pins the
arithmetic; this ear-test pins the *felt rhythm*.
result: [pending]

### 4. Anti-feature absence by ear (COPILOT-03)
expected: Across the live drive, listen for the locked anti-feature
phrases — "you tend to" / "you usually" / "you always" / "next track" /
"you should play" / "based on your past". If ANY of these surface in
Gemini's emitted reactions, that is a COPILOT-03 failure even if the
static gate at `tests/repo/test_no_recall_antifeatures.py` is green
(the static gate scans CODE; the ear catches Gemini drift at runtime).
The fragment templates explicitly forbid these phrases ("do NOT claim a
tendency", "do NOT recommend a NEXT track or move") — Kaan's ear is the
runtime defense in depth.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

The four ear-tests above are the §RECALL-EAR discharge surface for Phase
66 (see KAAN-ACTION-LEGAL.md §RECALL-EAR). Engineering ships green per
`gsd-autonomous fully`; Kaan flips `VIBEMIX_RECALL_ENABLED=1` and runs
the ear-test pass on his real corpus. Phase 65 §RECALL is the sibling
discharge for the retrieval-seam ear-pass (does the retrieval ground
correctly?); §RECALL-EAR is for the visible-callback ear-pass (does
the callback FEEL right — grounded, rare, in Kaan's voice, no
anti-features?).
