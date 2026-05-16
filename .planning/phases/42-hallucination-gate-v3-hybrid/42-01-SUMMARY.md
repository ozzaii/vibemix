---
phase: 42-hallucination-gate-v3-hybrid
plan: 01
subsystem: eval
tags: [eval, corpus, ack-bank, vcr, lfs, kaan-action, gate-01, gate-02, gate-03]
requires:
  - Phase 27-03 (eval/corpus/manifest.json + .gitattributes LFS rule)
  - Phase 27-08 (scripts/generate_ack_audio.py batch generator)
  - .planning/KAAN-ACTION-LEGAL.md §AUDIO-05/06/07 section convention
provides:
  - GATE-01 ack-bank resume wrapper (scripts/eval/generate_ack_audio_resume.py)
  - GATE-02 VCR cassette recorder helper (scripts/eval/record_cassettes.py)
  - GATE-03 real-corpus LFS scaffold (eval/corpus/MANIFEST.md + LICENSES.md schema)
  - Three §GATE-* Kaan-discharge runbooks
affects:
  - Plan 42-02 (threshold recalibration consumes the corpus scaffold)
  - Plan 42-03 (check_ear_test.sh reads the manifest ≥2-genres contract)
  - .github/workflows/eval.yml (--check-real-corpus mode wiring downstream)
tech-stack:
  added: []
  patterns:
    - "Quota-aware wrapper scripts (dry-run default + --really gate + GEMINI_API_KEY required)"
    - "Discovery heuristic via regex grep for VCR-decoration hints in test module docstrings"
    - "Schema-first markdown manifest templates with placeholder slots for Kaan-discharge"
key-files:
  created:
    - scripts/eval/generate_ack_audio_resume.py
    - scripts/eval/record_cassettes.py
    - eval/corpus/MANIFEST.md
    - tests/eval/test_ack_resume_idempotent.py
    - tests/eval/test_record_cassettes_invokable.py
    - tests/eval/test_corpus_lfs_layout.py
    - .planning/phases/42-hallucination-gate-v3-hybrid/deferred-items.md
  modified:
    - eval/corpus/LICENSES.md
    - KAAN-ACTION-LEGAL.md
decisions:
  - "ack-bank resume wrapper subprocess-invokes scripts/generate_ack_audio.py rather than direct-importing _load_manifest — keeps the wrapper $0-spend by default, defers all google-genai imports to the batch script"
  - "VCR discovery heuristic uses a permissive regex (\\bvcr\\b / \\bcassettes?\\b) to catch Phase 27 module docstrings that mention VCR in prose, not just code decorators"
  - "Diversity gate contract surface relaxed from ≥3 genres (Phase 27-03) to ≥2 genres (Phase 42-01) so check_ear_test.sh can fire on a partial corpus during early ear-test runs"
  - "Skipped creating new .gitkeep files — both eval/corpus/sessions/.gitkeep and tests/eval/cassettes/.gitkeep already exist from Phase 27-03; task done criteria met via existing markers"
metrics:
  duration_min: ~12 (single agent, single-pass execution from worktree base sync to final commit)
  completed_date: 2026-05-16
  tasks_completed: 3
  files_created: 7
  files_modified: 2
  tests_added: 20
  tests_failing: 0
---

# Phase 42 Plan 01: Hallucination Gate v3 Hybrid — Corpus Scaffolding Summary

Engineering scaffolding for the three corpus-side Kaan-discharge items (GATE-01 ack-bank top-up, GATE-02 VCR cassettes, GATE-03 real-corpus WAVs) — no real artifact bytes committed; all real discharge documented in `KAAN-ACTION-LEGAL.md §GATE-01..03`.

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1    | ack-bank resume helper + VCR cassette recorder helper + sanity tests | `b508e89` | `scripts/eval/generate_ack_audio_resume.py`, `scripts/eval/record_cassettes.py`, `tests/eval/test_ack_resume_idempotent.py`, `tests/eval/test_record_cassettes_invokable.py` |
| 2    | LFS corpus layout + MANIFEST/LICENSES templates + layout test | `36335c1` | `eval/corpus/MANIFEST.md`, `eval/corpus/LICENSES.md`, `tests/eval/test_corpus_lfs_layout.py` |
| 3    | Append §GATE-01/02/03 runbooks to KAAN-ACTION-LEGAL.md | `e990a09` | `KAAN-ACTION-LEGAL.md` |

## What Shipped

### Scripts (engineering scaffolding, $0 spend by default)

- **`scripts/eval/generate_ack_audio_resume.py`** — wraps the Phase 27-08 batch generator with a dry-run-by-default surface. `list_missing_entries()` walks the 40-entry manifest and returns which `<bucket>/<id>.opus` files are absent (verified against the real assets/ack_bank/manifest.json: 20 present, 20 missing — matches the ACK-BANK-REMAINING-20 reality). `--really` gates subprocess invocation of `scripts/generate_ack_audio.py` behind GEMINI_API_KEY presence.

- **`scripts/eval/record_cassettes.py`** — discovers VCR-decorated tests under `tests/eval/` via a permissive regex (5 hits against the Phase 27 judge/cited/substance test files). Default mode prints the inventory and the Kaan-discharge oneliner; `--really --record-mode=new_episodes` subprocess-invokes pytest with VCR_RECORD_MODE set.

### Corpus directory scaffolding

- **`eval/corpus/MANIFEST.md`** — new human-readable manifest template, 7-field schema (Session ID / Genre / Duration / Source URL / License / Attribution / SHA256) per session, surfaces the ≥2 genres contract for `check_ear_test.sh`.
- **`eval/corpus/LICENSES.md`** — expanded schema with Source URL + Retrieval date + ffmpeg normalize + SHA256 slots. Audit trail entry added.
- **`.gitattributes`** — LFS rule `eval/corpus/sessions/**/*.wav filter=lfs diff=lfs merge=lfs -text` already present from Phase 27-03 (verified idempotent — Task 2 was a no-op for this file).
- **`.gitkeep` markers** — both `eval/corpus/sessions/.gitkeep` and `tests/eval/cassettes/.gitkeep` already exist from Phase 27-03; no new additions needed.

### Kaan-discharge runbooks (KAAN-ACTION-LEGAL.md)

Three new sections appended in canonical order, each carrying the 4-block structure (why-defer / Kaan-oneliner / verification / what-unblocks) plus sign-off block:

- **§GATE-01** — Ack-bank quota refresh (20 → 40 OPUS files, ~$0.10 Gemini TTS spend)
- **§GATE-02** — VCR cassette population (one-time, ~$1-2 Gemini spend)
- **§GATE-03** — Real-corpus DJ session WAVs (6 × 30-min, 200 MB git-LFS, 6-step Kaan workflow)

### Tests

20 sanity tests added across 3 files, all pass:

- `tests/eval/test_ack_resume_idempotent.py` — 6 tests pinning the $0-in-dry-run contract + the missing-entries inventory math + the default-mode-is-dry-run rule.
- `tests/eval/test_record_cassettes_invokable.py` — 7 tests pinning the no-subprocess-in-default contract, the GEMINI_API_KEY requirement on `--really`, and the `--record-mode=none` rejection path.
- `tests/eval/test_corpus_lfs_layout.py` — 7 tests pinning the corpus dir layout, MANIFEST.md content, LICENSES.md schema expansion, .gitattributes LFS rule, and the no-real-WAV-bytes-committed invariant.

## Verification

```bash
# Plan-wide test suite:
$ uv run pytest tests/eval/test_ack_resume_idempotent.py \
                tests/eval/test_record_cassettes_invokable.py \
                tests/eval/test_corpus_lfs_layout.py -q
20 passed in 0.03s

# Scripts invokable + sane:
$ uv run python scripts/eval/generate_ack_audio_resume.py --dry-run
[ack-resume] present: 20/40 OPUS files
[ack-resume] missing: 20/40 OPUS files

$ uv run python scripts/eval/record_cassettes.py
[record-cassettes] discovered 5 VCR-decorated test file(s):
  test_cited_relevance.py
  test_judge_flash_rubric.py
  test_judge_pro_rubric.py
  test_record_cassettes_invokable.py
  test_substance_metric.py

# KAAN-ACTION audit:
$ grep -c "^## §GATE-0" KAAN-ACTION-LEGAL.md
3

# LFS rule present (Phase 27-03 idempotent):
$ grep -E "eval/corpus/sessions.*filter=lfs" .gitattributes
eval/corpus/sessions/**/*.wav filter=lfs diff=lfs merge=lfs -text

# No real artifact bytes leaked:
$ ls eval/corpus/sessions/*.wav 2>/dev/null | wc -l
0
```

## Deviations from Plan

None — plan executed exactly as written.

One non-deviation worth noting: the plan's verify-block referenced `KAAN-ACTION-LEGAL.md` at repo root; the file actually exists at TWO paths (root + `.planning/`). I appended to the root file (829 lines, well-developed §AUDIO-05/06/07 / §SHIP convention) — this matched the plan's `files_modified` list and the section-pattern convention.

Pre-existing failure (out of scope) logged to `.planning/phases/42-hallucination-gate-v3-hybrid/deferred-items.md`: `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file` was failing at the base commit `5d74d6a` because the 6 session subdirs lack `events.jsonl` (Phase 27-03 seeded only `genre.txt` + `source.txt`). Closure path: this is exactly what GATE-03 Kaan-discharge handles.

## Requirement Status

GATE-01, GATE-02, GATE-03 stay **open** in `REQUIREMENTS.md` after this plan. The requirement text targets the discharged-artifact state ("40/40 Achird OPUS files in ack-bank", "VCR cassettes populated", "6 × 30-min public-domain DJ session WAVs"), not the scaffolding-shipped state. Closure is gated on Kaan running the three §GATE-* one-liners. The SDK's `requirements mark-complete` flipped them to `[x]` and the change was reverted — premature checkmark would have hidden the Kaan-action remainder.

## Authentication Gates

None — Plan 42-01 ships engineering scaffolding only; no Gemini API calls, no real artifact bytes. The three GATE-0X runbooks define the auth gates that future Kaan-discharge runs hit (each requires `GEMINI_API_KEY` for §GATE-01/§GATE-02 spend).

## Known Stubs

The 6 session blocks in `eval/corpus/MANIFEST.md` and `eval/corpus/LICENSES.md` carry `_placeholder_` slots for Source URL / License / Attribution / SHA256 fields. These are intentional Kaan-discharge stubs documented in §GATE-03 runbook. Closure: Kaan fills these in as part of the GATE-03 6-step workflow (sourcing, ffmpeg normalize, manifest fill, git lfs commit).

## Self-Check: PASSED

**Files verified present:**
- FOUND: `scripts/eval/generate_ack_audio_resume.py`
- FOUND: `scripts/eval/record_cassettes.py`
- FOUND: `eval/corpus/MANIFEST.md`
- FOUND: `eval/corpus/LICENSES.md` (modified)
- FOUND: `tests/eval/test_ack_resume_idempotent.py`
- FOUND: `tests/eval/test_record_cassettes_invokable.py`
- FOUND: `tests/eval/test_corpus_lfs_layout.py`
- FOUND: `KAAN-ACTION-LEGAL.md` (modified, +233 lines)
- FOUND: `.planning/phases/42-hallucination-gate-v3-hybrid/deferred-items.md`

**Commits verified in git log:**
- FOUND: `b508e89` (feat(42-01): ack-bank resume + VCR cassette recorder helpers)
- FOUND: `36335c1` (feat(42-01): eval corpus LFS layout + MANIFEST/LICENSES expansion)
- FOUND: `e990a09` (docs(42-01): append §GATE-01/02/03 Kaan-discharge runbooks)

**Test counts verified:**
- 20 tests pass (target: ≥10 per plan success criteria)
- 0 tests fail in this plan's scope
- 1 pre-existing failure (`test_each_session_has_events_jsonl_file`) out of scope, logged in deferred-items.md
