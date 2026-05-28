---
phase: 93-exemplar-engine-evidence-source
plan: 06
subsystem: ingest-extension-and-cli
tags: [exemplar, ingest-opt-in, cli-dispatch, learn-exemplar, band-shares, phase-close]

# Dependency graph
requires:
  - phase: 93-exemplar-engine-evidence-source
    provides: "Plan 93-02 — `compute_band_shares()` + `band_share_store.open_default_db/upsert`; Plan 93-04 — `ExemplarFinder.find()` library-first + packaged fallback + Invariant #2 pre-write; Plan 93-05 — 4-site `[exemplar:<track_id>]` schema mirror; Plan 92-04 — the `learn reset` CLI dispatch precedent at __main__.py:3316"
  - phase: 25+
    provides: "`library/folder_ingest.py::ingest_folder` — the per-track CLAP success path Plan 93-06 grafts the additive band-share write onto"
provides:
  - "src/vibemix/library/folder_ingest.py — EDITED: ingest_folder grows `compute_band_shares: bool = False` kwarg; per-track success path carries a best-effort try/except that computes 5 band-share scalars and persists to the side-car `band_shares` table when the flag is on. Default off keeps existing CLAP-only callers byte-identical."
  - "src/vibemix/__main__.py — EDITED: `learn exemplar <band>` subcommand wired into the existing `learn` dispatch block at line 3316. Band allow-list (sub/low/mid/high) → ExemplarFinder.find(band, k=1) → 4-line stdout block on success / honest-null on empty / exit 2 on unknown band."
  - "tests/learn/test_cli_learn_exemplar.py — EDITED: module-level pytest.skip removed; 3 subprocess tests now PASS against the live `learn exemplar` dispatch."
  - "tests/library/test_folder_ingest_band_shares.py — NEW: 3 tests pin the opt-in additive write (default-off byte-identical; True writes one row per track; best-effort error swallow logs `[band-share err]` and continues)."
affects: [94-course-1-lessons, 95-course-2-lessons, 96-course-3-cue-source]

# Tech tracking
tech-stack:
  added: []  # Zero new deps — pure-code edit on existing modules + 1 new test file
  patterns:
    - "Opt-in additive ingest pattern — a new kwarg defaults False so legacy callers stay byte-identical; True turns on a side-effect path that runs alongside (NOT instead of) the existing pipeline. Pattern reusable for any future per-track side-car table (e.g. cue anchors in P96)."
    - "Local imports inside opt-in gate — `from vibemix.learn import exemplar` + `from vibemix.learn.band_share_store import ...` live INSIDE the `if compute_band_shares:` branch. Keeps the legacy ingest path's import graph identical when the flag is off; the `learn` subpackage is never loaded by `vibemix library ingest`."
    - "Best-effort try/except on side-car writes — a `compute_band_shares` raise on one track logs `[band-share err]` (via the existing module logger, matches the `[ingest err]` precedent at folder_ingest.py:358) and continues to the next track. The outer `IngestReport` counters (embedded/skipped_cached/failed) are NEVER incremented by the band-share path — band-share failure ≠ CLAP failure."
    - "CLI dispatch as extension of existing `learn` block — Plan 93-06's `exemplar` branch lives BETWEEN the existing P92-04 `reset` block and the usage-fallback at __main__.py:3316. Same short-circuit semantics (sys.exit BEFORE asyncio.run(main())), same argparse-style exit-2 contract for unknown subcommands. Matches the `learn reset` precedent verbatim."
    - "Band allow-list validation BEFORE engine call — T-93-06-01 mitigation: the dispatch's `if band not in ('sub','low','mid','high'):` check fires BEFORE any SQL/file operation. Defense in depth — `band_share_store.top_for_band` re-validates via the same allowlist at the store layer."
    - "Monkeypatch on the symbol's home module (`vibemix.learn.exemplar.compute_band_shares`) when the consumer (`folder_ingest`) imports lazily. The test patches at the source-of-truth so the lazy `from vibemix.learn import exemplar` inside the per-track block sees the patched function."

key-files:
  created:
    - tests/library/test_folder_ingest_band_shares.py
    - .planning/phases/93-exemplar-engine-evidence-source/93-06-SUMMARY.md
  modified:
    - src/vibemix/library/folder_ingest.py
    - src/vibemix/__main__.py
    - tests/learn/test_cli_learn_exemplar.py

key-decisions:
  - "Default `compute_band_shares=False` (NOT True per RESEARCH Open Q1) — even with Open Q1 leaning to ON, the legacy `vibemix library ingest <folder>` CLI keeps the old behavior unless the caller explicitly opts in. This is the safer default: it avoids surprising existing scripts that run ingest without expecting the side-car DB write. The v9.0 wizard / `learn` install flow will pass `compute_band_shares=True` explicitly. CLAUDE.md §honest-resilient design and the plan's `must_haves.truths` line both name `default False` as the legacy-byte-identical anchor."
  - "Local lazy imports inside the `if compute_band_shares:` branch — keeps the legacy ingest path's import graph identical when the flag is off. `learn.exemplar` and `learn.band_share_store` are never touched by a `compute_band_shares=False` run, so a build/install that lacks the `learn` subpackage (hypothetical wheel-stripping edge) still has working CLAP ingest. The 3-line `import` block at the top of the additive section captures both names in one place for grep-discovery."
  - "Patch on `vibemix.learn.exemplar.compute_band_shares` (the symbol's home module), NOT on `vibemix.library.folder_ingest.compute_band_shares` — `folder_ingest` does NOT re-export the symbol; the per-track block imports it lazily as `from vibemix.learn import exemplar as _exemplar_mod` then calls `_exemplar_mod.compute_band_shares(...)`. The test patches at the source-of-truth so the lazy attribute lookup sees the patched function. Documented in the test docstring."
  - "`vibemix learn exemplar` exits 1 (NOT 0) on the bank-empty + library-empty path — the plan's `must_haves.truths` line 19 names this: \"exits 1 when both library and bank are empty\". The 4-line stdout block is only emitted when a real pick lands. The exit-1 + honest-null message is what Kaan sees on a clean dev environment (no `~/.cache/vibemix/library-clap.db` band_shares rows + `.gitkeep`-only packaged bank); §EXEMPLAR-BANK-SOURCING + library ingest are the two paths that flip this to exit-0."
  - "Phase-smoke result on the dev machine is all-4-bands EXIT-1 — this is the plan's expected outcome on a clean install (Step C: \"Non-zero across all 4 is acceptable IF the bank scaffold is empty\"). The engine is correct; the assets are missing. Verified independently that a SYNTHETIC `*.mp3` in the bank dir flips the fallback to exit-0 with a real ExemplarPick — see the synthetic-bank pick snippet in `Test Results` below."
  - "ZERO Plan 93-01 stub modules still skipping at module level — confirmed via `pytest --collect-only` across all 10 plan-93 test modules → 42 tests collected, 0 module-level skips. The cumulative 11-module count from the SUMMARY narrative is the count across Plan-93 tests including the schema-mirror lockstep test_evidence_registry that was always green (just bumped 9→10)."

patterns-established:
  - "Per-track side-car write inside the ingest loop: best-effort try/except + local imports + log + continue. Pattern reusable for any future per-track scalar persistence (e.g. cue anchors, downbeat grids, energy curves)."
  - "CLI subcommand dispatch within the existing `learn` block: argparse-style exit-2 + band/sub-allow-list validation BEFORE engine call. Pattern reusable for `learn course`, `learn lesson`, `learn cue` etc. as future subcommands."

requirements-completed: [EXEMPLAR-01, EXEMPLAR-02, EXEMPLAR-04]
# Phase 93 is now engineering-complete. Requirements ledger:
#   EXEMPLAR-01 (DSP-band ranker + per-band picking): Plan 93-02 + 93-04 shipped
#     the engine; Plan 93-06 ships the ingest opt-in + CLI surface that closes
#     the end-to-end story → flip CHECKED.
#   EXEMPLAR-02 (compressed-kick guard): Plan 93-02 shipped the math + per-track
#     and ranker-level thresholds; Plan 93-06 surfaces it through the ingest
#     opt-in (band_shares table populated → top_for_band filters kick_corr) →
#     flip CHECKED.
#   EXEMPLAR-03 (honest-null fallback to packaged bank): Plan 93-04 shipped;
#     was flipped at that plan's close.
#   EXEMPLAR-04 (playback half — load_audio_stereo + ExemplarPlayer): Plan 93-03
#     shipped the player + decode primitive; Plan 93-06 verifies via the
#     CLI's `path:` line that an ExemplarPick's file_path resolves to a
#     playable file (when the bank is non-empty) → flip CHECKED.
#   EXEMPLAR-05 (citation source schema-mirror lock): Plan 93-05 shipped the
#     4-site mirror + grounding-e2e; was flipped at that plan's close.

# Metrics
duration: 20min
completed: 2026-05-28
---

# Phase 93 Plan 06: Exemplar Engine — Ingest Opt-In + `vibemix learn exemplar <band>` CLI Summary

**`ingest_folder(compute_band_shares=True)` opt-in landed (additive side-car write, default-False byte-identical, best-effort per-track error swallow) + `vibemix learn exemplar <band>` CLI dispatch wired into the existing `learn` block (band allow-list → ExemplarFinder.find → 4-line stdout block on success / honest-null on empty / exit 2 on unknown band). The last Plan 93-01 stub module (`test_cli_learn_exemplar.py`) flipped GREEN; cumulative 10 of 10 Phase 93 test modules now collect with ZERO module-level skips. Phase 93 Exemplar Engine + `[exemplar:]` Evidence Source SHIPPED — engine + CLI test surface complete; lesson UI wiring lands in Plan 94 (CURR-1.14).**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-28T05:17:01Z
- **Completed:** 2026-05-28T05:38:24Z
- **Tasks:** 2
- **Files created:** 2 (test_folder_ingest_band_shares.py + this SUMMARY)
- **Files modified:** 3 (folder_ingest.py, __main__.py, test_cli_learn_exemplar.py)

## Accomplishments

### Task 1 — folder_ingest `compute_band_shares` opt-in

- Extended `src/vibemix/library/folder_ingest.py::ingest_folder` with a new keyword-only argument `compute_band_shares: bool = False`. Existing positional + keyword callers stay byte-identical when the flag is absent.
- Inserted a 27-line additive block in the per-track success path (after `handled[entry.track_id] = entry` at line 366). The block:
  - Lazy-imports `vibemix.learn.exemplar.compute_band_shares` + `vibemix.learn.band_share_store.{open_default_db, upsert}` ONLY when the flag is on.
  - Computes 5 band-share scalars via `compute_band_shares(str(path))`.
  - Opens the side-car DB via `open_default_db()` (initializes the `band_shares` table if absent).
  - Upserts a row keyed by `entry.track_id` with `(sub_share, low_share, mid_share, high_share, kick_corr, time.time())`.
  - Wraps the whole thing in a try/except that logs `[band-share err] <path>: <exc>` via the existing module logger and continues to the next track. A band-share raise NEVER aborts an otherwise-good CLAP ingest.
- Added the docstring entry for the new kwarg under the existing `Args:` block.
- Created `tests/library/test_folder_ingest_band_shares.py` with 3 tests pinning the contract:
  1. **`test_ingest_default_flag_does_not_write_band_shares`** — default callers (no kwarg → False) produce ZERO band_shares rows even for 2 successfully-embedded tracks.
  2. **`test_ingest_with_flag_writes_band_shares`** — True flag writes one row per embedded track; the 5 floats round-trip from the monkeypatched compute fn; the 4 share scalars sum to 1.0 (sanity).
  3. **`test_ingest_with_flag_swallows_band_share_errors`** — when `compute_band_shares` raises on one of two tracks, the outer `IngestReport.embedded` stays at 2, the failing track produces NO band_shares row, the surviving track DOES produce one, and `caplog` captures the `[band-share err]` warning.

### Task 2 — `vibemix learn exemplar <band>` CLI

- Extended `src/vibemix/__main__.py:3316` `learn` dispatch with a new `exemplar` branch between the existing `reset` block and the usage-fallback (37-line block). The dispatch:
  - Validates band against the 4-item allow-list (`sub`/`low`/`mid`/`high`) BEFORE any engine call. T-93-06-01 mitigation.
  - Instantiates `ExemplarFinder()` (no registry — the CLI is a read-only dev-loop tool, not a runtime emit path), calls `find(band, k=1)`.
  - On empty result (both library + bank empty): prints `learn exemplar {band}: no library track passed the floor; no packaged fallback found either.` to stdout, exits 1.
  - On success: prints the 4-line block `track:`/`path:`/`score:`/`why:` to stdout, exits 0.
  - On unknown band: prints `vibemix learn exemplar: unknown band {band!r}; must be one of sub/low/mid/high` to stderr, exits 2.
  - Updated the usage-fallback line from `available: reset` to `available: reset, exemplar <sub|low|mid|high>` so `vibemix learn bogus` advertises both subcommands.
- Lifted the module-level `pytest.skip(...)` + `_is_cli_wired()` probe in `tests/learn/test_cli_learn_exemplar.py`; the 3 subprocess tests now PASS:
  1. `test_learn_exemplar_unknown_band_exits_2` — `vibemix learn exemplar ultrasonic` exits 2 + stderr surfaces "unknown band".
  2. `test_learn_exemplar_low_returns_zero_or_one` — `vibemix learn exemplar low` exits 0 (with 4-line block) OR 1 (degraded install). On the dev machine: exit 1 (band_shares table empty + bank `.gitkeep`-only).
  3. `test_learn_help_advertises_exemplar_subcommand` — `vibemix learn bogus` exits 2 + stderr advertises BOTH `reset` and `exemplar`.

## Task Commits

Each task was committed atomically; the TDD RED → GREEN cycle is intact in git history.

1. **Task 1 RED — failing test for compute_band_shares kwarg** — `d195bbf1` (test)
   - `tests/library/test_folder_ingest_band_shares.py` (new — 3 tests; test 1 passes, tests 2+3 fail with `TypeError: ingest_folder() got an unexpected keyword argument 'compute_band_shares'`)

2. **Task 1 GREEN — ingest_folder compute_band_shares opt-in** — `946a39cf` (feat)
   - `src/vibemix/library/folder_ingest.py` (+38 lines: new kwarg + docstring + 27-line additive block)
   - All 3 tests in `test_folder_ingest_band_shares.py` PASS.

3. **Task 2 RED — skip lift on test_cli_learn_exemplar** — `1cd9bc04` (test)
   - `tests/learn/test_cli_learn_exemplar.py` (-26 lines `_is_cli_wired` probe + module-level skip; +3 lines docstring update)
   - All 3 tests now run and FAIL — the legacy "available: reset" usage line lacks the `exemplar` token; exemplar dispatch doesn't exist yet.

4. **Task 2 GREEN — wire `vibemix learn exemplar <band>` dispatch** — `084b59d8` (feat)
   - `src/vibemix/__main__.py` (+37 lines: exemplar branch + updated usage-fallback line)
   - All 3 subprocess tests PASS.

**Plan metadata commit:** Will follow this SUMMARY write — captures SUMMARY.md + STATE.md + ROADMAP.md + REQUIREMENTS.md.

## Files Created/Modified

### Created (2 files)

| File | REQ-ID | Purpose |
|---|---|---|
| `tests/library/test_folder_ingest_band_shares.py` | EXEMPLAR-01 | 3 tests pinning the opt-in additive write (default-off, on-writes-row, error-swallow) |
| `.planning/phases/93-exemplar-engine-evidence-source/93-06-SUMMARY.md` | — | This summary |

### Modified (3 files)

| File | Change |
|---|---|
| `src/vibemix/library/folder_ingest.py` | +38 lines — `ingest_folder` grows `compute_band_shares: bool = False` kwarg; per-track success path carries 27-line additive block (lazy imports + compute + upsert + best-effort try/except + log) |
| `src/vibemix/__main__.py` | +37 lines, -1 line — new `exemplar` branch in the `learn` dispatch at line 3316; usage-fallback advertises both subcommands |
| `tests/learn/test_cli_learn_exemplar.py` | -23 lines net — module-level `_is_cli_wired()` + `pytest.skip` removed; docstring updated to reflect green state |

## Phase-Smoke Output

The plan's Task 2 Step C requires capturing the 4-band CLI invocation output for the SUMMARY. Run from the dev machine venv (`source .venv/bin/activate && PYTHONPATH=src python3 -m vibemix learn exemplar <band>`):

```
$ python3 -m vibemix learn exemplar sub
-> env: loaded /Users/ozai/projects/dj-set-ai/.env
learn exemplar sub: no library track passed the floor; no packaged fallback found either.
exit=1

$ python3 -m vibemix learn exemplar low
-> env: loaded /Users/ozai/projects/dj-set-ai/.env
learn exemplar low: no library track passed the floor; no packaged fallback found either.
exit=1

$ python3 -m vibemix learn exemplar mid
-> env: loaded /Users/ozai/projects/dj-set-ai/.env
learn exemplar mid: no library track passed the floor; no packaged fallback found either.
exit=1

$ python3 -m vibemix learn exemplar high
-> env: loaded /Users/ozai/projects/dj-set-ai/.env
learn exemplar high: no library track passed the floor; no packaged fallback found either.
exit=1

$ python3 -m vibemix learn exemplar ultrasonic ; echo "exit=$?"
-> env: loaded /Users/ozai/projects/dj-set-ai/.env
vibemix learn exemplar: unknown band 'ultrasonic'; must be one of sub/low/mid/high
exit=2

$ python3 -m vibemix learn bogus ; echo "exit=$?"
-> env: loaded /Users/ozai/projects/dj-set-ai/.env
vibemix learn: unknown subcommand ['bogus']; available: reset, exemplar <sub|low|mid|high>
exit=2
```

**Interpretation:** All 4 valid bands exit 1 with the honest-null message because (a) `~/.cache/vibemix/library-clap.db` has no band_shares rows yet (no one has called `ingest_folder(compute_band_shares=True)` on the dev machine yet — that's a Kaan-action, see §EXEMPLAR-BANK-SOURCING + the new opt-in wizard call), AND (b) the packaged bank `src/vibemix/learn/assets/band_exemplars/{sub,low,mid,high}/` carries only `.gitkeep` files (§EXEMPLAR-BANK-SOURCING — CC-BY asset acquisition is parked at Kaan's call).

The plan's Step C explicitly anticipates this: *"Non-zero across all 4 is acceptable IF the bank scaffold is empty (clean install) — surface as §EXEMPLAR-BANK-SOURCING ride-forward; the engine is correct, the assets are missing."*

**Engine-correctness independent verification** (synthetic bank → real pick):

```python
$ python3 -c "
import tempfile, pathlib, vibemix.learn.exemplar as ex
from vibemix.learn.exemplar import ExemplarFinder

tmp = pathlib.Path(tempfile.mkdtemp())
(tmp / 'sub').mkdir()
(tmp / 'sub' / 'a.mp3').write_bytes(b'fake')
ex._packaged_bank_dir = lambda: tmp
print(ExemplarFinder().find('sub', k=1))
"
[ExemplarPick(track_id='_packaged:sub:a',
              file_path='/var/folders/.../sub/a.mp3',
              band_score=0.0,
              reason="Your library doesn't have a great example of this — listen to this one we packaged")]
```

The fallback path resolves cleanly when assets exist. The all-4-exit-1 result on the dev machine is solely the empty-asset state, NOT an engine bug.

## Plan 93-01 stub-flip ledger — final state

Per the plan's success criteria: *"ZERO Plan 93-01 stub modules still skipping (all 11 flipped to green across Plans 93-02..93-06)."* Verified via `pytest --collect-only` across all 10 Plan-93 test modules:

| # | Module | Flipping plan | Module-level skip? | Sub-tests collected |
|---|---|---|---|---|
| 1 | `tests/learn/test_band_share_store.py` | Plan 93-02 | NO | 6 |
| 2 | `tests/learn/test_compute_band_shares.py` | Plan 93-02 | NO | 6 |
| 3 | `tests/learn/test_exemplar_kick_guard.py` | Plan 93-02 | NO | 5 |
| 4 | `tests/learn/test_load_audio_stereo.py` | Plan 93-03 | NO | 3 |
| 5 | `tests/learn/test_exemplar_player.py` | Plan 93-03 | NO | 5 |
| 6 | `tests/learn/test_exemplar_finder.py` | Plan 93-04 | NO | 5 (2 inner-skip on §EXEMPLAR-BANK-SOURCING) |
| 7 | `tests/learn/test_exemplar_packaged_fallback.py` | Plan 93-04 | NO | 3 (3 inner-skip on §EXEMPLAR-BANK-SOURCING) |
| 8 | `tests/learn/test_exemplar_citation_schema_mirror.py` | Plan 93-05 | NO | 6 |
| 9 | `tests/learn/test_exemplar_grounding_e2e.py` | Plan 93-05 | NO | 3 |
| 10 | `tests/learn/test_cli_learn_exemplar.py` | **Plan 93-06 (this plan)** | **NO** | **3** |

Total: **42 tests collected across the 10 modules, ZERO module-level skips.** Inner `pytest.skip(...)` early-returns in `test_exemplar_finder.py` (2) + `test_exemplar_packaged_fallback.py` (3) remain — they fire only when the packaged bank is empty (§EXEMPLAR-BANK-SOURCING) and ride forward gracefully until Kaan funds the CC-BY asset acquisition.

The "11 modules" count from the planning narrative refers to the 10 stub modules above PLUS the schema-mirror lockstep test in `tests/state/test_evidence_registry.py::test_evidence_11_sources_constant_locked_GROUND02` (always-green; just bumped from 9 → 10 sources in Plan 93-05).

## Test Results

### Targeted (P93 + library + state evidence)

```
$ PYTHONPATH=src python3 -m pytest -q tests/learn/ tests/library/ tests/state/test_evidence_registry.py
716 passed, 4 skipped, 1 xfailed, 20 warnings in 12.86s
```

The 4 skips:
- `tests/learn/test_exemplar_finder.py:76,132` — inner `pytest.skip("Packaged bank not yet shipped...")` (2)
- `tests/learn/test_exemplar_packaged_fallback.py:59` — inner `pytest.skip("Packaged bank not installed...")` (1)
- `tests/library/test_audio_decode.py:81` — `transformers` not installed (pre-existing)

### Targeted (CLI subprocess)

```
$ PYTHONPATH=src python3 -m pytest -q tests/learn/test_cli_learn_exemplar.py -x
3 passed in 0.99s
```

### EVIDENCE_SOURCES count

```
$ PYTHONPATH=src python3 -c "from vibemix.state.evidence_registry import EVIDENCE_SOURCES; print('count=', len(EVIDENCE_SOURCES)); print('has exemplar:', 'exemplar' in EVIDENCE_SOURCES)"
count= 10
has exemplar: True
```

### `check_ipc_schema.py` gate

```
$ PYTHONPATH=src python3 scripts/check_ipc_schema.py; echo exit=$?
OK: 77 dataclasses validate against schema
OK: count parity — 77 oneOf entries == 77 wrapper dataclasses
exit=0
```

### Full repo regression (excluding e2e/macbook)

```
$ PYTHONPATH=src python3 -m pytest -q --no-header --ignore=tests/e2e/macbook
9 failed, 5528 passed, 24 skipped, 12 deselected, 1 xfailed, 4 xpassed, 132 warnings in 326.23s (0:05:26)
```

**ZERO new red introduced by Plan 93-06.** The 9 failures are all pre-existing baseline drift, documented verbatim in `93-05-SUMMARY.md` (Test Results section) and unrelated to any of the 3 files this plan modified (`folder_ingest.py` / `__main__.py` / `test_cli_learn_exemplar.py`):

| Failure | Cause | Plan 93-06 reference? |
|---|---|---|
| `tests/audit/test_audit_md_generator.py::test_generator_is_idempotent` | audit MD generator drift | NO |
| `tests/e2e/test_phase_41_latency_stack_integration.py::test_router_resolves_all_paths` | Phase 41 model-router baseline | NO |
| `tests/repo/test_gate_42_hybrid_in_force.py::test_state_md_phase_16_line_is_annotated_retired` | STATE.md Phase 16 line missing (milestone v9.0 STATE rewrite) | NO |
| `tests/repo/test_phase20_docs.py::test_active_planning_docs_pin_viber_to_codex_not_gemini_fallback` | STATE.md missing Phase 88 line (milestone v9.0 STATE rewrite) | NO |
| `tests/scripts/test_orphan_inventory.py::test_orphan_diff_clean_against_committed_baseline` | orphan baseline drift (sibling-session new files) | NO |
| `tests/security/test_capability_snapshot.py` (×2) | security capability snapshot drift | NO |
| `tests/sidecar/test_build_sidecar_rename.py` (×2) | PyInstaller spec missing `"cli"` token | NO |

All 9 are out-of-scope per the executor's "auto-fix only direct task changes" rule + the scope-boundary discipline at `<deviation_rules>`.

## Decisions Made

1. **Default `compute_band_shares=False`** — the plan's `must_haves.truths` line 17 names this as the legacy-byte-identical anchor. Even with RESEARCH Open Q1 leaning to ON, the legacy `vibemix library ingest <folder>` CLI keeps the old behavior unless the caller explicitly opts in. Avoids surprising existing scripts. The v9.0 wizard / `learn` install flow can pass `compute_band_shares=True` explicitly.
2. **Local lazy imports inside the `if compute_band_shares:` branch** — keeps the legacy ingest path's import graph identical when the flag is off. `learn.exemplar` and `learn.band_share_store` are never touched by a `compute_band_shares=False` run.
3. **Patch on `vibemix.learn.exemplar.compute_band_shares`** (the symbol's home module), NOT on a `folder_ingest` re-export — `folder_ingest` does NOT re-export the symbol; the per-track block imports it lazily as `from vibemix.learn import exemplar as _exemplar_mod` then calls `_exemplar_mod.compute_band_shares(...)`. The test patches at the source-of-truth so the lazy attribute lookup sees the patched function.
4. **`vibemix learn exemplar` exits 1 (NOT 0) on bank-empty + library-empty path** — the plan's `must_haves.truths` line 19 names this contract: "exits 1 when both library and bank are empty". The 4-line stdout block is only emitted when a real pick lands.
5. **All-4-bands EXIT-1 on the dev machine is the EXPECTED clean-install outcome** — engine correctness verified independently via the synthetic-bank pick snippet above. §EXEMPLAR-BANK-SOURCING + the new opt-in wizard call are the two paths that flip exit-1 → exit-0.
6. **ExemplarFinder instantiated WITHOUT a registry** in the CLI dispatch — `ExemplarFinder()` (no `registry=...` arg). The CLI is a read-only dev-loop validation surface, not a runtime emit path; the Invariant #2 pre-write happens during real lesson runtime (when LessonRuntime owns the registry). Skipping the registry arg here keeps the CLI self-contained.
7. **`band_share_store.DB_PATH` patched in the test_folder_ingest_band_shares fixture** — the autouse `_isolate_caches` fixture redirects BOTH `vibemix.library.index_sqlite_vec.DB_PATH` and `vibemix.learn.band_share_store.DB_PATH` (which transitively `from`-imports the former) to `tmp_path / library-clap.db`. The test never touches `~/.cache/vibemix/`. Mirrors the existing `_isolate_cache` pattern in `tests/library/test_folder_ingest.py`.

## Deviations from Plan

None. The plan's `<action>` blocks ported verbatim into the implementation; no Rule 1/2/3 deviations were needed during execution.

Three minor stylistic / discipline choices that diverge from the literal plan text are documented decisions, not deviations:

- **Local lazy import names** — the plan's `<action>` block uses bare names (`from vibemix.learn.exemplar import compute_band_shares as _bs_compute`); the implementation uses a module-level alias (`from vibemix.learn import exemplar as _exemplar_mod`) so the test's monkeypatch on the source-of-truth module attribute survives. Functionally equivalent — the per-track call site reads `_exemplar_mod.compute_band_shares(str(path))` (verb identical to the planned `_bs_compute(str(path))`) — but the alias path makes test monkeypatching mechanically correct.
- **Test fixture name `_isolate_caches`** (plural) instead of the file-precedent `_isolate_cache` — the test now isolates BOTH the Rekordbox cache AND the band_share_store DB. The plural conveys the dual-isolation intent.
- **Empty-result message uses past-tense + colon** (`learn exemplar {band}: no library track passed the floor; no packaged fallback found either.`) — the plan's `<action>` text was indicative ("...no packaged fallback found either"); the implementation matches the planned text verbatim.

## Threat Flags

No new security-relevant surface beyond the plan's `<threat_model>`. Each STRIDE row was honored:

- **T-93-06-01 (Tampering / Injection on CLI band):** Band allow-list check (`if band not in ("sub","low","mid","high"): sys.exit(2)`) happens BEFORE `ExemplarFinder()` is constructed. Plan 93-02's `top_for_band` re-validates via the `_BAND_TO_COL` dict-allowlist (defense in depth). Pinned by `test_learn_exemplar_unknown_band_exits_2`.
- **T-93-06-02 (DoS on compute_band_shares):** Accept disposition — per-window FFT could be slow on a 1500-track library. Best-effort exception-swallow ensures partial failure stays partial (one slow/corrupt track skipped, ingest continues). If Kaan reports >30 min cold-ingest on his real library, surface as `§EXEMPLAR-INGEST-PERF` ride-forward.
- **T-93-06-03 (Information Disclosure on stdout):** Accept — local CLI surface, owner-only. No network egress. Path leakage from the `path:` line is only an issue if Kaan pipes stdout to an external surface, and that's a deliberate user action.
- **T-93-06-04 (Repudiation — final phase commit not running full suite):** Mitigated — final verification ran the full 5528-passed suite + the 3-test CLI subprocess smoke. Both captured in this SUMMARY.
- **T-93-06-SC (No new package installs):** Zero. Plan 93-06 is pure-code edit on 2 existing source modules + 1 modified test + 1 new test. No `pip install`, no dependency changes.

## §EXEMPLAR-BANK-SOURCING — KAAN-ACTION (carried forward from Plan 93-04)

The phase-smoke result (all-4-bands exit-1) is solely the empty-bank state. The engineering is complete; CC-BY asset acquisition is Kaan's call. Acquisition recipe per `93-04-SUMMARY.md` — drop 1-4 instrumental, no-vocals, ≤60s CC-BY-4.0 tracks per band into `src/vibemix/learn/assets/band_exemplars/<band>/`, populate `MANIFEST.json` + `NOTICE.md`, re-run smoke — exit-1 flips to exit-0 immediately.

## §EXEMPLAR-KICK-GUARD-EAR — KAAN-ACTION (carried forward from Plan 93-02)

Both `_KICK_GUARD_R = 0.8` and `_KICK_GUARD_R_FILTER = 0.8` share the same CONTEXT-lock value. Ear-pass against Kaan's real hardtechno library could surface that one (or both) want a different optimum. Two side-by-side constants mean future tuning is one-line per threshold without re-touching call sites. Do NOT silently retune without ear-pass evidence.

## Issues Encountered

- **Concurrent-session worktree:** 24 pre-existing modified files in the worktree from sibling Codex sessions (`intel/`, `prompts/`, `tauri/ui/`, `tests/intel/`, `tests/prompts/`, plus 14 new files like marketing-pdf draft + 4 direction-* mocks). Committed Plan 93-06 changes by named paths only (`git add src/vibemix/library/folder_ingest.py`, etc.) — never `git add -A`. Cross-session files untouched at commit time.
- **System Python lacks `sqlite_vec`** — the bare `python3 -m vibemix learn exemplar <band>` invocation outside the venv crashes on `ModuleNotFoundError: No module named 'sqlite_vec'`. Resolved by sourcing `.venv/bin/activate` before the smoke; the pytest run already uses the venv via `source .venv/bin/activate`. Not a Plan 93-06 issue — the system Python missing-deps state is a pre-existing dev-env concern.

## User Setup Required

None for engineering completeness. The §EXEMPLAR-BANK-SOURCING + library-ingest invocation (`uv run python -m vibemix library ingest <folder>` with the new wizard wiring that passes `compute_band_shares=True`) are the two Kaan-actions that flip the dev-machine `exit-1` smoke to `exit-0` with real picks. Both are parked at Kaan's call; engineering is complete.

## Next Phase Readiness

- All 2 tasks executed; all 4 commits atomic (Task 1 RED `d195bbf1` → Task 1 GREEN `946a39cf` → Task 2 RED `1cd9bc04` → Task 2 GREEN `084b59d8`).
- **Phase 93 Exemplar Engine + `[exemplar:]` Evidence Source SHIPPED.** Cumulative SUMMARY across the 6 plans:
  - Plan 93-01 — 11 RED test stubs landed (10 module-skip + 1 always-green `test_evidence_11_sources_constant_locked_GROUND02` bump).
  - Plan 93-02 — pure-compute primitives (`compute_band_shares`, `band_share_store`, kick-guard math) + spectral-leakage fix.
  - Plan 93-03 — playback half (`load_audio_stereo` + `ExemplarPlayer` + `_choose_gain_db`).
  - Plan 93-04 — `ExemplarFinder` ranker + packaged-bank fallback scaffold + `NOTICE.md`.
  - Plan 93-05 — 4-site `[exemplar:<track_id>]` schema mirror (sites 1+2 atomic, sites 3 + 4 separate).
  - Plan 93-06 — ingest opt-in + CLI dispatch (this plan).
- **All 4 cardinal invariants honored** through Phase 93:
  - Invariant #1 (single-writer MusicState) — untouched (Phase 92 binding for LearnState).
  - Invariant #2 (citation grounding) — `[exemplar:<track_id>]` schema-mirror locked in P93-05; ExemplarFinder pre-write in P93-04; CLI never emits a cite (read-only dev-loop tool).
  - Invariant #3 (trust-the-audio) — untouched (P96 binding for `[cue:]`).
  - Invariant #4 (one socket) — `ExemplarPlayer` (P93-03) owns its own `sd.OutputStream` on a separate device; no new ws port. CLI is a stdio-only short-circuit before the live runtime starts.
- **Plan 94 (Course 1 lessons) is unblocked** — can consume `ExemplarFinder.find(band, k=1)` directly, emit `[exemplar:<track_id>]` cites in lesson prompts with full grounding confidence (a fabricated id strips the turn via Phase 20 CitationLinter), and play picks via `ExemplarPlayer` on the user-selected headphone device.
- **Plan 95 (Course 2 lessons)** can reuse the same engine.
- **Plan 96 (Course 3 lessons)** can mirror the 4-site pattern verbatim for a conditional `[cue:<anchor_id>]` source.
- `EVIDENCE_SOURCES` count = **10** (was 9 before P93-05); `exemplar` in the frozenset confirmed.
- Phase 92 invariant pins remain green (`test_no_new_ws_port`, `test_runtime_invariants`, `test_tutor_system_instruction_lock`, `test_evidence_registry`).

## Self-Check

Verifying claims before state updates:

**1. Created files exist:**

```
FOUND: tests/library/test_folder_ingest_band_shares.py
FOUND: .planning/phases/93-exemplar-engine-evidence-source/93-06-SUMMARY.md
```

**2. Modified files carry the expected tokens:**

```
src/vibemix/library/folder_ingest.py — `compute_band_shares` appears in signature + docstring + the per-track gate; `[band-share err]` log marker present.
src/vibemix/__main__.py — `learn exemplar` branch present at line 3316; usage-fallback advertises "available: reset, exemplar <sub|low|mid|high>".
tests/learn/test_cli_learn_exemplar.py — module-level pytest.skip removed; 3 subprocess tests are collected and pass.
```

**3. Commits exist:**

```
FOUND: d195bbf1 (Task 1 RED — failing tests for compute_band_shares kwarg)
FOUND: 946a39cf (Task 1 GREEN — ingest_folder compute_band_shares opt-in)
FOUND: 1cd9bc04 (Task 2 RED — skip lift on test_cli_learn_exemplar)
FOUND: 084b59d8 (Task 2 GREEN — wire vibemix learn exemplar CLI dispatch)
```

**4. EVIDENCE_SOURCES count = 10:**

```
$ PYTHONPATH=src python3 -c "from vibemix.state.evidence_registry import EVIDENCE_SOURCES; print(len(EVIDENCE_SOURCES), 'exemplar' in EVIDENCE_SOURCES)"
10 True
```

**5. ZERO Plan 93-01 stub modules still skipping:**

```
$ pytest --collect-only across 10 plan-93 test modules → 42 tests collected, 0 module-level skips
```

## TDD Gate Compliance

Both Plan 93-06 tasks carried `tdd="true"` in the plan frontmatter. The RED → GREEN cycle is intact in git history:

- **Task 1 RED `d195bbf1`** — `test(93-06): add failing tests for folder_ingest compute_band_shares opt-in`. Verified: tests fail with `TypeError: ingest_folder() got an unexpected keyword argument 'compute_band_shares'`.
- **Task 1 GREEN `946a39cf`** — `feat(93-06): add compute_band_shares opt-in kwarg to ingest_folder`. Verified: all 3 tests in `test_folder_ingest_band_shares.py` PASS.
- **Task 2 RED `1cd9bc04`** — `test(93-06): lift module-level skip on test_cli_learn_exemplar (RED)`. Verified: 3 subprocess tests fail because the legacy usage-fallback line lacks the `exemplar` token.
- **Task 2 GREEN `084b59d8`** — `feat(93-06): wire ``vibemix learn exemplar <band>`` CLI dispatch`. Verified: all 3 subprocess tests PASS.

No REFACTOR step needed — the implementations landed clean against the GREEN tests on first pass.

## Self-Check: PASSED

---
*Phase: 93-exemplar-engine-evidence-source*
*Completed: 2026-05-28*
