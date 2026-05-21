# Phase 60 — Deferred Items + KAAN-ACTION ship gate

Per `gsd-autonomous fully`, this surfaces (does NOT pause) — the conservative
default (detector OFF) is already the safe state, so engineering continues.

## KAAN-ACTION: flip `harmonic_clash_enabled` only after the Kaan-ear veto signs off (HARMONIC-03)

The harmonic clash detector ships **gated/quiet**:
`EventDetector(harmonic_clash_enabled=False)` is the default (`src/vibemix/state/event_detector.py:97`).
A false clash on a pair Kaan would happily mix is the release-tripping failure
mode, so the detector stays OFF until Kaan personally clears it.

**The sign-off recipe (Kaan, on his real corpus):**

1. Edit `tests/fixtures/kaan_disagreed_pairs.json` — add the real pairs your ear
   disagrees with. `"verdict": "safe"` = pairs you'd happily mix (MUST NOT flag);
   `"verdict": "clash"` = true clashes (SHOULD flag, keeps the gate non-vacuous).
2. Run the scorer:
   ```bash
   source .venv/bin/activate && PYTHONPATH=src python3 eval/harmonic/run_veto.py
   ```
   It must print `GATE PASS` and exit 0 — zero false clashes, controls flag.
3. Only then flip the runtime flag to `True` at the `EventDetector` construction
   site (wire it in via `__main__.py`) and re-validate live.

Until step 3, the detector is silent — no false clash can reach the audience. The
default-off state is intentional and safe, mirroring the Phase-59
`DeckPoller._vision_enabled` precedent.

## Pre-existing full-suite failures on `live-tuning-or-brain` (count: 7 — unchanged)

The 7 failing tests are pre-existing branch WIP failures (in-flight v4.0
`__main__.py` orchestrator refactor + README feature-matrix not regenerated for
phases 55–58 + cut-release script churn). Documented in full in
`.planning/phases/59-full-deck-awareness-grounding/deferred-items.md`. Plan 60-03
added 13 passing tests (4046 → 4059 passed); the failure count stayed at 7. None
of the 7 reference `harmonics` / `is_clash` / the veto harness.

| Test |
|------|
| `tests/coach/test_main_anti_slop_wiring.py::test_wire13_anti_slop_disabled_path_passes_none_kwargs` |
| `tests/repo/test_cut_release_invokes_bravoh_server.py::test_tag_regex_unchanged_in_this_plan` |
| `tests/repo/test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync` |
| `tests/repo/test_readme_feature_matrix_sync.py::test_feature_matrix_includes_all_completed_phases` |
| `tests/scripts/test_cut_release_preflight.py::test_cut_release_accepts_valid_rc_tag_shape` |
| `tests/scripts/test_cut_release_preflight.py::test_cut_release_blocks_on_missing_milestone_audit` |
| `tests/test_main_smoke.py::test_smoke_08_main_source_wires_cache_create_with_graceful_degradation` |
