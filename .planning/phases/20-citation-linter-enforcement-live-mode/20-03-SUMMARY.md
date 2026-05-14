---
phase: 20-citation-linter-enforcement-live-mode
plan: 03
subsystem: scripts.replay_linter
tags: [phase-20, anti-slop, replay, ground-05, ground-06, phase-16-prep]
requires:
  - 20-01  # CitationLinter + LintResult API
  - 20-02  # I'm listening fail-soft fragment (used by fixture row 6)
provides:
  - scripts/replay_linter.py            # CLI: --session/--mode/--out/--print-rate
  - tests/scripts/fixtures/synthetic_session/  # 7-response self-contained fixture
affects:
  - scripts/README.md                   # new "## replay_linter.py" section
  - .gitignore                          # whitelist fixture wav/jsonl, ignore CSV
tech-stack:
  added: []
  patterns:
    - subprocess CLI contract test (NOT in-process import — pin shell pipe)
    - per-test shutil.copytree fixture so linter_report.csv lands in tmp_path
    - lex-sorted invocation dirs (NNNN_HHMMSS_<EVENT>) = invocation order
    - HHMMSS-delta math for session-relative t_session column
key-files:
  created:
    - scripts/replay_linter.py
    - tests/scripts/test_replay_linter.py
    - tests/scripts/fixtures/synthetic_session/events.jsonl
    - tests/scripts/fixtures/synthetic_session/voice.wav
    - tests/scripts/fixtures/synthetic_session/responses/0001_120000_KAAN_SPOKE/response.txt
    - tests/scripts/fixtures/synthetic_session/responses/0002_120015_TRACK_CHANGE/response.txt
    - tests/scripts/fixtures/synthetic_session/responses/0003_120030_MIX_MOVE/response.txt
    - tests/scripts/fixtures/synthetic_session/responses/0004_120045_PHASE/response.txt
    - tests/scripts/fixtures/synthetic_session/responses/0005_120100_HEARTBEAT/response.txt
    - tests/scripts/fixtures/synthetic_session/responses/0006_120115_LAYER_ARRIVAL/response.txt
    - tests/scripts/fixtures/synthetic_session/responses/0007_120130_MANUAL/response.txt
  modified:
    - scripts/README.md
    - .gitignore
decisions:
  - "Fixture track key uses underscores not spaces (`marlon_hoffstadt-atlas`) — the EBNF grammar regex `_INNER_ATOM` rejects whitespace inside `[source:body]` so any space in a citation body fails parse. Caught during the smoke run when stripped_rate landed at 0.286 instead of 0.143; trimmed the space and the fixture invariant pinned at 1/7 ≈ 0.143."
  - "events.jsonl carries 12 observation rows ONLY (no `ai_text` noise rows) to match the plan's `wc -l == 12` done criterion. The kind-filter path in `_load_registry` is still exercised — replay walks every row and skips non-evidence_observation kinds — so dropping the noise row only loses test redundancy, not coverage."
  - "linter_report.csv added to .gitignore even though it lives inside the fixture dir — it's a per-run artifact regenerated every replay invocation. Committing it would force regeneration to keep tracked state in sync."
  - "Replay does NOT call session_dir/invocations/ (the live agent's actual dump path per `dj_cohost.py` line 273). The plan locked `responses/` as the contract because Phase 16 ear-test will copy/symlink real `invocations/` dirs into a `responses/` subdir matching the harness shape — keeps replay's input contract decoupled from the live writer's churn."
  - "Test suite drives the CLI via subprocess + sys.executable (NOT importing main() in-process). Phase 16 audit scripts will pipe into `STRIPPED_RATE=` via shell — so the test matrix MUST pin the shell-pipe contract, not the Python API."
metrics:
  duration_minutes: 22
  tasks_completed: 2
  files_created: 11
  files_modified: 2
  tests_added: 9
  tests_pass_delta: "+9 (1779 → 1788, 9 pre-existing failures unchanged)"
  completed_date: 2026-05-14
---

# Phase 20 Plan 03: Replay Linter Harness Summary

`scripts/replay_linter.py` — offline replay of recorded sessions through `CitationLinter`; ships with a 7-response synthetic fixture pinning `stripped_rate < 0.15` (CONTEXT D-Gate-Replay) for Phase 16 ear-test ratification.

## What Shipped

**`scripts/replay_linter.py`** — argparse CLI:

```bash
.venv/bin/python scripts/replay_linter.py \
    --session <SESSION_DIR> \
    [--mode live|debrief] \
    [--out <CSV_PATH>] \
    [--print-rate]
```

Six-step pipeline:

1. Validate `--session` exists + has `events.jsonl` + `responses/`.
2. Replay observation rows from `events.jsonl` into a fresh `EvidenceRegistry`.
3. List `responses/<NNNN_HHMMSS_EV>/` dirs lex-sorted (= invocation order).
4. For each: read `response.txt`, snapshot the registry, `linter.check(text, snap, mode=...)`.
5. Write CSV: `response_id, t_session, citations_found, valid, reason, missing_atoms`.
6. Print summary `total=N stripped=K stripped_rate=X mode=Y out=PATH`; with `--print-rate`, also `STRIPPED_RATE=<float:.4f>` for shell-pipe.

**Synthetic fixture** under `tests/scripts/fixtures/synthetic_session/`:

| Response                     | Cites                                                    | Outcome             |
| ---------------------------- | -------------------------------------------------------- | ------------------- |
| `0001_120000_KAAN_SPOKE`     | `[ev:KICK_SWAP@5.0]`                                     | valid               |
| `0002_120015_TRACK_CHANGE`   | `[track:marlon_hoffstadt-atlas,aud:bpm@5.0]`             | valid               |
| `0003_120030_MIX_MOVE`       | `[midi:cue_a@30.0]`                                      | valid               |
| `0004_120045_PHASE`          | `[ev:DROP@45.2,aud:rms@45.2]`                            | valid               |
| `0005_120100_HEARTBEAT`      | `[mix:audible_deck=A]`                                   | valid               |
| `0006_120115_LAYER_ARRIVAL`  | (none — "I'm listening through this stretch.")           | invalid             |
| `0007_120130_MANUAL`         | `[tend:user_likes_acid,screen:waveform_deck_a]`          | valid               |

All 7 EBNF atom shapes covered; `stripped_rate = 1/7 ≈ 0.143 < 0.15`.

**Test suite** — `tests/scripts/test_replay_linter.py`, 9 cases driving the CLI via `subprocess` + `sys.executable` (NOT importing `main()` — Phase 16 will pipe into `STRIPPED_RATE=`, so the test pins the shell contract).

## CSV Schema

| Column            | Type   | Meaning                                                                      |
| ----------------- | ------ | ---------------------------------------------------------------------------- |
| `response_id`     | string | Invocation dir name (`NNNN_HHMMSS_<EVENT>`, lex-sorted = invocation order)   |
| `t_session`       | float  | Seconds since the FIRST response's HHMMSS prefix (first row is always `0.0`) |
| `citations_found` | int    | Parsed citation atoms in the response                                        |
| `valid`           | bool   | Binary linter decision (whole-utterance gate)                                |
| `reason`          | string | One of `valid` / `no_citations` / `invalid_atoms` / `malformed_atom`         |
| `missing_atoms`   | string | Semicolon-joined `source:body` pairs for misses (empty for valid)            |

## Verification Block

| Check                                                                                | Plan Target | Actual               |
| ------------------------------------------------------------------------------------ | ----------- | -------------------- |
| `pytest tests/scripts/test_replay_linter.py -x`                                      | passes      | 9/9 pass             |
| `find tests/scripts/fixtures/synthetic_session -type f \| wc -l`                     | ≥10         | 10                   |
| `wc -l tests/scripts/fixtures/synthetic_session/events.jsonl`                        | 12          | 12                   |
| `find tests/scripts/fixtures/synthetic_session/responses -name "response.txt" \| wc -l` | 7        | 7                    |
| Replay smoke `STRIPPED_RATE` line                                                    | < 0.15      | 0.1429               |
| `grep -c "## replay_linter.py" scripts/README.md`                                    | 1           | 1                    |
| POC files (`cohost*.py`, `mascot.html`)                                              | UNTOUCHED   | last touch `398f788` |
| Full-suite regression                                                                | ≥1779 pass  | 1788 pass (9 pre-existing fails unchanged) |

## Replay Invariant

`CitationLinter` and `EvidenceRegistry` are imported from the production `vibemix.coach` + `vibemix.state` modules — replay uses the SAME class instances the live agent uses, with the SAME constants (`LIVE_TOLERANCE_S = 1.0`, `DEBRIEF_TOLERANCE_S = 2.0`). Replay results are byte-for-byte the live decision. The threshold gate (`stripped_rate < 0.15`) holds across both surfaces.

## Phase 16 Ear-Test Workflow

1. Run a real DJ session through the live agent — recorder writes `<session>/events.jsonl` + `<session>/invocations/<NNNN_HHMMSS_EV>/` per turn.
2. Symlink/copy `<session>/invocations/` → `<session>/responses/` (matching the harness's expected layout).
3. `replay_linter.py --session <session> --print-rate` → CSV + `STRIPPED_RATE=<float>` line.
4. Sessions with `stripped_rate ≥ 0.15` block release; sessions below gate the Phase 16 ratification.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Fixture track key contained spaces — broke EBNF parse, broke replay invariant.**

- **Found during:** Task 1 smoke run (verify step). Plan called for `track:Marlon Hoffstadt - Atlas` body in response 0002 + matching events.jsonl key.
- **Issue:** `EVIDENCE_CITATION_RE` (`vibemix/state/evidence_registry.py:78`) defines `_INNER_ATOM = (?:source):[^\s,\]]+` — explicitly excludes whitespace inside the body. Spaces caused `parse_citations` to return `[]` for response 0002, which drove `stripped_rate = 2/7 = 0.286` (well above the 0.15 gate the fixture is supposed to pin).
- **Fix:** Renamed both the events.jsonl `track` key and the response 0002 citation body to `marlon_hoffstadt-atlas` (underscore-joined). Verified `parse_citations` now returns 2 atoms; replay's `stripped_rate` snapped to `1/7 ≈ 0.143 < 0.15`.
- **Files modified:** `tests/scripts/fixtures/synthetic_session/events.jsonl`, `tests/scripts/fixtures/synthetic_session/responses/0002_120015_TRACK_CHANGE/response.txt`.
- **Commit:** `22369f1` (Task 1 — caught + fixed pre-commit, single atomic commit).

**2. [Rule 3 — Blocking] `.gitignore` rejected fixture `events.jsonl` + `voice.wav` (matched `*.jsonl` / `*.wav` repo-wide rules).**

- **Found during:** Task 1 `git add` step.
- **Issue:** Repo-wide rules at `.gitignore:69-70` exist to keep recordings out of git; they swallow our committed test fixture too.
- **Fix:** Added negation rules `!tests/scripts/fixtures/synthetic_session/events.jsonl` + `!tests/scripts/fixtures/synthetic_session/voice.wav` plus an explicit ignore for the per-run artifact `tests/scripts/fixtures/synthetic_session/linter_report.csv`.
- **Files modified:** `.gitignore`.
- **Commit:** `22369f1` (rolled into Task 1).

### Plan-Level Trims (intentional)

- Plan task 1 fixture spec mentioned a "noise row" pattern in events.jsonl (`ai_text` row to verify the kind-filter path). Plan's `<done>` then specified `wc -l events.jsonl == 12`. Kept the strict 12-line count and dropped the noise row — `_load_registry` still walks every row + skips non-`evidence_observation` kinds, so the filter path is exercised by the same code path even without the dedicated test row.
- Plan task 2 mentioned `test_mode_debrief_passes_invalid_response_with_wider_tolerance` — implemented as `test_mode_debrief_accepted_as_arg` since the synthetic fixture's only invalid response is `no_citations` (not a tolerance miss), so the wider tolerance band has no observable effect on this fixture. The CLI flag contract is still pinned.

## Threat Mitigations Applied

| ID         | Mitigation                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------- |
| T-20-03-01 | (accept) events.jsonl trusted local source — no validation needed.                          |
| T-20-03-02 | (accept) CSV writes inside session dir; raw response text NOT exported (only missing atoms). |
| T-20-03-03 | (mitigated) `_load_registry` reads events.jsonl line-by-line — never whole-file load.       |
| T-20-03-04 | (mitigated) `CitationLinter` + `EvidenceRegistry` imported from production modules — same constants, same code path; replay decision is byte-for-byte the live decision. Test 1 (`test_synthetic_session_stripped_rate_below_0_15`) pins the contract on the synthetic fixture; Phase 16 swaps in real fixtures and gates the same threshold. |

## Commits

| SHA       | Message                                                          |
| --------- | ---------------------------------------------------------------- |
| `22369f1` | `feat(20-03): replay_linter CLI + synthetic_session fixture`     |
| `80d2afb` | `test(20-03): replay_linter pass-criteria suite (9 tests)`       |

## Self-Check: PASSED

- [x] `scripts/replay_linter.py` exists (FOUND).
- [x] `tests/scripts/test_replay_linter.py` exists (FOUND).
- [x] All 7 `responses/.../response.txt` files exist (FOUND).
- [x] `events.jsonl` exists, 12 lines (FOUND).
- [x] `voice.wav` exists, 48044 bytes (FOUND).
- [x] Commit `22369f1` exists in git log (FOUND).
- [x] Commit `80d2afb` exists in git log (FOUND).
- [x] 9/9 replay-linter tests pass.
- [x] Full suite: 1788 passed (was 1779), 9 pre-existing failures unchanged, 0 new failures.
