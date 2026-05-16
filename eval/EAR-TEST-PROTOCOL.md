<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Plan 42-03 — Ear-test protocol for the hybrid hallucination gate. -->

# vibemix Ear-Test Protocol

This document codifies how Kaan signs off on a real DJ session as
**"ear-pass"** for the v3.0 hybrid hallucination gate. It is the slow
lane of the hybrid: the fast lane is the Phase 27 autonomous proxy
(2-judge cross-check). Both must be green before `cut_release.sh`
Gate-2 passes (Plan 42-04, `scripts/release/check_gate.sh`).

The protocol is intentionally low-friction. The capture surface is an
**opt-in** toggle inside the Phase 29 debrief window. There is no
gamification, no streak tracking, no badges — those are Plan 42 CONTEXT
deferred items.

## Why

vibemix's product bar is "real DJ friend in your ear, no AI slop". The
autonomous proxy gate (Phase 27) measures grounding via 2-judge LLM
scoring against a real-corpus replay harness — but no autonomous score
can fully replace Kaan's ear. The hybrid keeps both: autonomous proxy
catches drift on every PR + nightly canary; the ear-test catches the
qualitative failure modes (felt scripted, felt late, felt generic) that
no judge prompt currently captures.

The override that v2.1 used (Phase 16 ear-test memory override) expires
post-v2.1. v3.0 retires it formally (Plan 42-05 / GATE-08) and reinstates
the ear-test as the slow-lane veto.

## When

Run an ear-test session whenever any of the following apply:

- Within 14 days of an intended release cut.
- After a reaction-prompt or coach-prompt change (`src/vibemix/coach/`).
- After a model-router change (`src/vibemix/llm/_router_config.py`).
- After a corpus update (Plan 42-01 / GATE-03).
- Spot-check during normal DJ sessions whenever a reaction "felt off" —
  the structured capture is the bug-report surface.

The **30 min minimum** below is non-negotiable; sessions under 1800 s
are rejected by the JSON Schema and `check_ear_test.sh`.

## Window math (14 days ≥ 2 genres)

`scripts/release/check_ear_test.sh` accepts iff **all** of the following
hold against the JSON log files under `eval/ear-test-logs/`:

1. **≥ 2 sessions** signed within the last **14 days** (`WINDOW_DAYS=14`).
2. **≥ 2 distinct genres** across those signed-in-window sessions —
   "two house sessions" alone does **not** pass.
3. **Every captured `slop_flags` value is `false`** — zero of
   `felt_slop`, `felt_scripted`, `felt_late`, `felt_generic` reported
   across the in-window set.

Each ear-test log is a JSON file at
`eval/ear-test-logs/<session-id>.json` matching
`eval/ear-test-logs/schema.json` (JSON Schema draft 2020-12). Required
keys:

| Field | Type | Constraint |
|-------|------|------------|
| `session_id` | string | regex `^[a-zA-Z0-9_-]{1,64}$` |
| `started_at` | string | ISO 8601 UTC |
| `duration_s` | integer | ≥ 1800 (30 min minimum) |
| `genre` | string | enum: `hard_tek`, `techno`, `house`, `hip_hop`, `dnb`, `dubstep`, `other` |
| `slop_flags` | object | 4 required boolean keys (see below) |
| `free_form` | string | maxLength 4000 |
| `signed_by` | string | enum: `kaan` (single-DJ v3.0; cross-DJ deferred to v3.x) |
| `signed_at` | string | ISO 8601 UTC |

`additionalProperties: false` — unknown keys reject.

## Slop-flag taxonomy

The 4 boolean checkboxes in the debrief toggle UI. `true` = "I noticed
this slop class somewhere in the session"; `false` = "session was clean
on this dimension". A single `true` value blocks the gate.

- **`felt_slop`** — generic AI noise, not grounded in the actual mix.
  Reaction quoted a track / phase / move that didn't happen.
- **`felt_scripted`** — reaction felt pre-canned; not responsive to this
  specific moment. Same beat-drop reaction could have applied to any
  drop in any set.
- **`felt_late`** — reaction landed ≥ 3 s after the trigger event,
  breaking the flow.
- **`felt_generic`** — reaction could apply to any track in any set; no
  specificity to the actual transition / layer arrival / phase.

These four classes are the load-bearing definition of "AI slop" for
v3.0. They are intentionally narrow — Plan 42 CONTEXT deferred per-genre
threshold bands + 3-judge cross-checks to v3.x.

## Capture surface

Capture is wired into the existing Phase 29 debrief window, **not** a
new modal. Flow:

1. Kaan runs a DJ session ≥ 30 min in any supported genre.
2. After the session, the Phase 29 debrief window opens automatically
   (or via Settings → Recordings → "View debrief").
3. The debrief layout exposes an opt-in toggle: **"Bu session'ı
   release-gate için işaretle / Rate this session for release-gate"**.
4. Toggling it ON expands a form:
   - Header: "Ear-test sign-off — 30 min minimum, ≥ 2 genres in 14d window".
   - 4 checkboxes (one per slop-flag class above), all unchecked by
     default (= no slop detected).
   - Free-form textarea, max 4000 chars: "what worked, what didn't".
   - Submit button: "Sign off".
5. On submit, the UI sends the structured payload to the Python writer
   (`src/vibemix/debrief/ear_test_capture.py::write_ear_test_log`) via
   the existing Tauri IPC channel (or, in dev mode, via the debrief WS
   client on 127.0.0.1:8766).
6. The writer atomically persists `eval/ear-test-logs/<session-id>.json`.

The toggle is opt-in: every regular session save proceeds without
prompting for ear-test sign-off. The signal is captured **only when
Kaan actively rates the session**.

## Privacy

Per `feedback_privacy_scope_narrow`, ear-test log file CONTENT lives in
the repo as an audit trail — the structured JSON (timestamps, genres,
slop-flag booleans, free-form notes) is committed and visible in git
history. What gets REDACTED is the **descriptive text in the public
`eval/README.md`** (Plan 42-06): the public doc names the protocol
shape, but does not republish individual session evaluations.

Why this split? The structured logs are the audit chain for the gate;
they need to live in repo so reviewers can verify the gate fired on
real signed sessions. The free-form notes are Kaan's personal critique
of specific reactions — that content stays in the repo (single-DJ regime,
Kaan owns the repo) but is not redistributed in public-facing eval docs.

If a free-form note contains anything that should not be in repo (rare),
edit before sign-off — the writer treats the file as immutable once
committed.

## Cross-references

- `scripts/release/check_ear_test.sh` — bash gate that reads
  `eval/ear-test-logs/` and enforces the 14d ≥ 2 sessions ≥ 2 genres +
  zero-slop-flag contract.
- `scripts/release/check_gate.sh` — Plan 42-04, the umbrella Gate-2
  cut script that combines this ear-test result with the 7-nightly
  autonomous-proxy result.
- `eval/THRESHOLD-LOCK.md` — autonomous-proxy thresholds (Phase 27 lock).
- `eval/README.md` — Plan 42-06 public-facing eval doc with the anti-slop
  manifesto (redacted ear-test content).
- `KAAN-ACTION-LEGAL.md §GATE-05` — Kaan-discharge runbook for the
  first two ear-test sessions (real DJ play required).
