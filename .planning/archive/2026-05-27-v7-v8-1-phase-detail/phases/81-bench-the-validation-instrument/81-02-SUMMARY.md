---
phase: 81-bench-the-validation-instrument
plan: 02
subsystem: bench
tags: [bench, harness, assemble, run, fail-safe, model-router, offline-green, cli, one-mind]

# Dependency graph
requires:
  - phase: 81-bench-the-validation-instrument
    plan: 01
    provides: "tests/bench/ offline gate — _FakeClient/_RaisingClient, bench_data_dir, 6 .mp3 excerpts, the 7 assemble/run xfail-strict scaffolds this plan flips"
  - phase: 80-ground
    provides: "build_parts_description(secondary_ear=) — the grounding-framing axis"
  - phase: 79-lens
    provides: "build_lens_instruction + LENS_TO_MODE_MOOD — the lens axis"
  - phase: 78-perceive
    provides: "MusicState trajectory_narrative/phase_history/long_arc/detected_genre — the contexting + grounding fixture fields"
provides:
  - "src/vibemix/bench/ harness: BenchCell/BenchResult (cell.py), STUDY_A/STUDY_B/NO_AUDIO_CELL/TASTE_RUBRIC/LENS_ANCHORS (matrix.py), fixture_state_for (fixtures.py), build_cell_prompt (assemble.py), run_study + 429 fail-safe + recorder + SessionMeter feed (run.py)"
  - "the `vibemix bench run --study {A|B|no-audio}` CLI (both __main__ dispatch sites)"
  - "BenchResult.dsp_snapshot + results_to_json — the recorded-cell artifact Plan 03's eval scores + Plan 04's review renders"
affects: [81-03-eval, 81-04-review]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "THIN COMPOSITION: build_cell_prompt calls the real product seams (build_lens_instruction / AICoach.build_prompt / build_parts_description / model_router.resolve) in the verified order — never re-authors prompt text (RESEARCH Pitfall 1)"
    - "Inject-the-client offline-green: run_study takes client by injection; the fake client makes the whole sweep zero-API"
    - "Per-cell 429 fail-safe: except -> error=repr(e)[:160], output='', CONTINUE — never fabricate, never abort (RESEARCH Pitfall 2 / the floor study's billing block)"
    - "Router-alias-only model axis: STUDY_* stores aliases; the assembler resolves via model_router.resolve — zero Gemini literals under bench/ (Pitfall 4)"

key-files:
  created:
    - src/vibemix/bench/__init__.py
    - src/vibemix/bench/cell.py
    - src/vibemix/bench/matrix.py
    - src/vibemix/bench/fixtures.py
    - src/vibemix/bench/assemble.py
    - src/vibemix/bench/run.py
  modified:
    - src/vibemix/__main__.py
    - tests/bench/test_assemble.py
    - tests/bench/test_run_fake.py
    - .planning/codebase/orphans.csv

key-decisions:
  - "generic-prompting control uses include_*=False (the byte-identical bare-builder path) rather than the /tmp/truthtest PROMPT literal — no prompt literal in assemble.py at all, keeping Pitfall 1 airtight and zero literal review surface"
  - "build_cell_prompt stays PURE (no file I/O): the audio Part bytes are attached by the runner, so the assemble tests are offline-green without touching disk; only run.py reads the .mp3"
  - "resolve_track_path resolves a cell's short prefix (track='t1') to t1_*.mp3 via glob — cells stay terse, the on-disk filenames stay descriptive"
  - "fixture_snapshot_for re-derives the cell's own snapshot so each BenchResult carries the exact DSP facts it was grounded on (Plan 03's CitationLinter.check re-runs against it)"
  - "STUDY_A is a focused ~10-cell arch slice (not the 96-cell cartesian) hitting all 3 lenses x dsp_only/audio+dsp grounding + the generic/structured/taste/raw-audio controls (RESEARCH Anti-Pattern: explosion)"

requirements-worked: [BENCH-01]

# Metrics
duration: 10min
completed: 2026-05-26
---

# Phase 81 Plan 02: BENCH-01 Harness Summary

**Built the `src/vibemix/bench/` harness as THIN COMPOSITION over the real Phase 77-80 seams: a `BenchCell` 6-D point -> `build_cell_prompt` (reuses `build_lens_instruction` / `AICoach.build_prompt` / `build_parts_description` / `model_router.resolve`, never re-authored text) -> `run_study` with an injected client + the mandatory per-cell 429 fail-safe + a verbatim JSON recorder + SessionMeter cost feed -> the `vibemix bench run` CLI. Flipped the 7 BENCH-01 assemble/run xfail scaffolds to real-green; zero model literals under `bench/`.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-05-26T02:57:04Z
- **Completed:** 2026-05-26T03:07:04Z
- **Tasks:** 2
- **Files:** 6 created (`bench/` modules) + 4 modified (`__main__.py`, 2 test files, orphans baseline)

## Accomplishments

- **`cell.py`** — `BenchCell` (frozen 6-D point with `uses_audio`/`secondary_ear`/`structured` derived props) + `BenchResult` (output + `dsp_snapshot` + `usage` + the `error` fail-safe field). `AUDIO_GROUNDINGS` deliberately excludes `dsp_only` (the no-audio cell sends zero audio Parts).
- **`matrix.py`** — `STUDY_A` (10-cell arch slice at the fixed `library_auto_tag` alias: 3 lenses x dsp_only/audio+dsp + the generic/structured/taste/raw-audio controls), `STUDY_B` (model-axis over `live_coach`/`library_auto_tag` aliases), `NO_AUDIO_CELL`, `STUDIES` lookup. `TASTE_RUBRIC` is a tiny FIXED placeholder carrying the `# KAAN-ACTION: ... Kaan's IP (Open Q1)` marker; `LENS_ANCHORS` is a fixed per-lens vocab table (anti-prompt-injection — no literal model, no user input).
- **`fixtures.py`** — `fixture_state_for(contexting, grounding)` builds a REAL `MusicState` (cold for `snapshot`, multi-scale PERCEIVE-02 fields for `trajectory`, genre only when `+genre`) + a grounded `EvidenceRegistry` snapshot carrying `aud/bpm@0.0` (matches the offline `_FakeClient`'s canned `[aud:bpm@0.0]` line so groundedness resolves with zero fixture churn).
- **`assemble.py`** — `build_cell_prompt(cell)` composes the system instruction (`build_lens_instruction` + flags + optional `TASTE_RUBRIC`), the evidence body (`AICoach.build_prompt` with `registry_snapshot=snap` when structured, `None` when generic), the parts suffix (`build_parts_description(secondary_ear=cell.secondary_ear)`), and resolves `model, tier = model_router.resolve(cell.model_path)`. The `dsp_only` branch appends no audio Part. Pure (no disk I/O).
- **`run.py`** — `run_study(cells, client=)` issues one injected-client `generate_content` per cell; audio-grounding cells load `.mp3` bytes from the env-overridable bench data dir (`resolve_track_path` globs `t1_*.mp3`); the per-cell `try/except` records `error=repr(e)[:160]` + `output=""` and CONTINUES; successful calls feed `SessionMeter.record`. `results_to_json` writes prompt+output+usage+snapshot verbatim (never the key).
- **`__main__.py`** — `vibemix bench` wired at BOTH sites: the banner-suppression guard (now `argv[0] in ("library", "bench")`) AND the routing dispatch (`if raw_argv[0] == "bench": sys.exit(_run_bench_cli(...))`), mirroring `_run_library_cli`. `_build_bench_subparsers` + `_cmd_bench_run` + `_run_bench_cli` give `bench run --study {A|B|no-audio} [--out]`; `--help` exits 0 and lists `run`.

## Task Commits

1. **Task 1: cell/matrix/fixtures/assemble — the prompt composer** — `4209ec1` (feat)
2. **Task 2: run.py runner + 429 fail-safe + recorder + SessionMeter + CLI** — `44b9814` (feat)

## Verification

- `pytest tests/bench/test_assemble.py tests/bench/test_no_model_literal.py` → 6 passed (the 4 BENCH-01 assemble xfails flipped real-green; the no-audio cell asserts zero audio Parts + non-empty evidence body)
- `pytest tests/bench/test_run_fake.py` → 3 passed (zero-network sweep records N cells; the 429 fail-safe parks + continues; usage captured)
- `bash scripts/release/check_no_hardcoded_model.sh` → exit 0, no literals under `bench/`; `grep gemini- src/vibemix/bench/` → NONE
- `python3 -m vibemix bench --help` → exit 0, lists `run`, no startup banner
- JSON recorder round-trips via `json.loads` (verified with audio cells loading real .mp3 bytes through the fake client)
- Full suite: **4515 passed, 26 skipped, 8 xfailed** (the 7 remaining bench xfails are Plan 03 eval + Plan 04 review — not this plan; the 4 XPASS are pre-existing live-test markers)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Orphan-inventory baseline drift from new bench/run.py helpers**
- **Found during:** Task 2 full-suite run
- **Issue:** `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline` failed — the three new `bench/run.py` module-level functions (`resolve_track_path`, `fixture_snapshot_for`, `results_to_json`) registered as new orphans vs the committed `.planning/codebase/orphans.csv` baseline. They are genuinely consumed (within `run_study` + by Plan 03's eval), so this is the documented "intentional new public surface" case.
- **Fix:** Refreshed the baseline with the documented command `python scripts/integration_audit.py --orphan-inventory > .planning/codebase/orphans.csv`.
- **Files modified:** `.planning/codebase/orphans.csv`
- **Commit:** `44b9814`

No bugs, no missing critical functionality, no architectural changes.

## Known Stubs

`TASTE_RUBRIC` (matrix.py) is an intentional, clearly-marked placeholder — the final "what clicked means" reward-signal wording is Kaan's IP, parked as a KAAN-ACTION (RESEARCH Open Q1). The `with_rubric` taste axis assembles a distinct prompt today; the real wording is supplied at the live verdict run. This is NOT a goal-blocking stub — BENCH-01's measurement capability is fully shipped; the placeholder only affects the taste-axis text, which Kaan authors.

## Threat Flags

None. No new network endpoints, auth paths, or schema changes beyond the plan's `<threat_model>`. The single network surface (`run.py` -> google-genai) is reached only in the CLI produce path via the existing funded key; the recorder writes prompt+output+usage only (T-81-04 honored); the model axis is router-alias-only (T-81-06 honored); the per-cell fail-safe is in place (T-81-05 honored).

## Self-Check: PASSED

- 6 created `src/vibemix/bench/` files all FOUND on disk
- Both task commits FOUND in git log (`4209ec1`, `44b9814`)
- `vibemix bench --help` exits 0; 9 bench tests green; full suite green (4515 passed)

## Next Phase Readiness

- The harness records each cell's output + its own `dsp_snapshot` — Plan 03's eval re-runs `CitationLinter.check(output, dsp_snapshot)` for groundedness + scores `specificity`/`lens_fidelity` (the `LENS_ANCHORS` table is already in `matrix.py`).
- The `BenchResult` field set (incl. the errored-cell `error`/empty-`output` shape) is the contract Plan 04's `review.py` renders (`ERRORED — parked`, empty VERDICT).
- KAAN-ACTION (parked, soft): the live two-study run on the funded key (`uv run python -m vibemix bench run --study A`) + the BENCH-03 ear verdict — neither blocks the autonomous merge; the offline gate is the honest-green proof. BENCH reqs close after Plans 03/04 + the parked run.

---
*Phase: 81-bench-the-validation-instrument*
*Completed: 2026-05-26*
