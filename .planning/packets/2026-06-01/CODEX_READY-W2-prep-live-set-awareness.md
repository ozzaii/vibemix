# CODEX_READY — Prep→Live Set Awareness: the Viber-built set, visible to the live coach (W2)

> The friend who prepped the set with you **forgets it the moment you go live.** The Viber set-builder produces a sequenced, energy-curved plan; the live co-host is **blind to it** — `built_set`/`set_plan`/`planned_curve` are absent from `state/`, `runtime/coach.py`, and `agent/` (verified NOT-FOUND at HEAD `e49b2f63`). Both halves exist; they were never joined. This is the wire that lets the co-host say *"you're ahead of your curve — your plan has the breakdown two tracks out."*
> **Owner: Codex A.** Claude read-only (packet + LIVE verify). Re-verified at HEAD `e49b2f63`. CRITIQUE M2, FUTURE W2.

## Why (the gap, precisely)
- The plan exists: `library/sequencer.py:126` `SetCandidate(track_ids: list[str], energy_fit, ...)` sequenced on a resampled energy curve (`resample_curve:141`, presets `:59`), built via `codex_curate.py:1074 build_set_with_codex` and serialized through `_BUILD_SET_SCHEMA` (the `library build-set` / `export-set` JSON).
- The live brain never sees it: `MusicState` (`state/music_state.py:23`) carries `phase_history`/`track_history` (last 6) but **no set-plan**; `coach.py` has no planned-curve reference. So the co-host can't relate *where you are* to *where you planned to be*.

## Design that respects the cardinal invariants
**Single-writer (Invariant #1):** only `state/refresh.py` writes `MusicState` (`refresh.py:24` "the ONLY function that writes MusicState fields"). So the set-plan is **DI input** to the refresh loop (like the DJ profile), and refresh computes a *derived, consumer-readable* `set_progress` and writes THAT to MusicState. The coach reads it. Do **not** let coach.py or the agent write the plan into state.

## 1. Load the plan — a `SetPlan` value
- New small `state/set_plan.py` (or `library/set_plan.py`) `SetPlan`: ordered `slots` of `(track_id, title, planned_energy, camelot, bpm)` + the resampled `curve`. Parse it from the existing build-set JSON (reuse `_BUILD_SET_SCHEMA`/`SetCandidate` — do not invent a new format).
- Load at session start when the user has designated "tonight's set" (a path/flag, mirror how the profile is loaded in `__main__.py`). No plan loaded → feature simply off (no behavior change).

## 2. Compute `set_progress` in the single writer
In `refresh.py` (pass `SetPlan` in via DI):
- Match the live track to a plan slot: live `track_history` title → library `track_id` (the library already maps title↔id) → the slot whose `track_id` matches. No confident match → `set_progress = None` (the DJ is off-script; say nothing — abstain).
- When matched, compute derived facts: current slot index, **energy delta vs the planned curve at this position** (live energy − `curve[slot]`), and the **next planned track** (`slots[i+1]`).
- Write a derived `set_progress` field to `MusicState` (consumer-readable evidence, per Critical Constraint 7 — bounded, not raw history).

## 3. Speak it — grounded, in the coach loop
- A coach line built from `set_progress`, gated abstain-first: only when a slot is confidently matched. Cite what resolves: **`[track:<next_planned_id>]`** (already a citation source, resolves in the library registry `__main__.py register_library`) for "next up per your plan", and the measured energy delta for "ahead/behind your curve." If neither cites, abstain.
- **Off-script is the default-silent case:** if live tracks don't match the plan (the DJ deviated), the co-host must NOT nag or hallucinate the plan — it goes quiet on this axis (Invariant #3). The plan is a *reference the DJ may abandon*, not a script to enforce.
- Mirror the existing grounded-line helper shape (`runtime/suggestion_voice.py` — `[track:]` citation, abstain when un-citable).

## 4. Guardrails
- Single-writer: refresh computes+writes `set_progress`; coach/agent read-only.
- Citation grounding: every spoken plan fact cites a resolving atom (`[track:]` / measured energy) or is not spoken.
- Abstain-first: no confident slot match → no line. Off-script → no line. Never enforce, never guilt-trip.
- No new third-party dep; reuse `SetCandidate`/`_BUILD_SET_SCHEMA`. Don't touch the embedder or the genre detectors.

## Acceptance
**SRC (Codex):** `tests/state/test_set_plan.py` + a refresh test — `set_progress` matches the right slot from a synthetic plan + live `track_history`; energy delta computed vs the resampled curve; off-plan tracks → `set_progress None`. `tests/runtime` — the coach line speaks a `[track:]`-cited "next up / ahead of curve" only when matched, abstains when off-script; the citation resolves. Single-writer test stays green (coach/agent never write the plan). ruff clean.
**LIVE (Claude verifies on Kaan's rig):** load a built set, play tracks from it → co-host references the plan with a resolved `[track:]`; play an off-plan track → no plan line (silent, not nagging). Prep→live amnesia cured.
**Proof tiers:** SRC → LIVE → PKG.

## Gate
**`vibemix-grounding-review` REQUIRED** — changes what the co-host SAYS and adds a new spoken evidence axis; the review must confirm abstain-first on off-script and that every plan fact cites a resolving atom. Effort ~1d (both halves built; this is the join + a refresh computation + one coach line).
