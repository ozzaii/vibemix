# Phase 40 — Deferred Items

Out-of-scope discoveries logged during execution. Each item names the plan
that discovered it; the phase planner / verifier triages.

---

## DEFERRED-40-01-01: LFS pointer drift in `tauri/ui/assets/mascot/*.glb`

**Discovered by:** Plan 40-01 worktree-merge sync.

**Symptom:** Worktree shows 21 `.glb` files as `Bin 20747776 -> 133 bytes` — LFS pointer text replacing the binary blob locally. Two fixture files (`tests/library/fixtures/synthetic_embeddings.npy`, `synthetic_queries.json`) also flagged "should have been pointers, but weren't".

**Root cause:** Worktree base was much older; LFS smudge filter content doesn't survive the merge cleanly when binaries are large.

**Why deferred:** Pre-existing LFS resolution issue unrelated to Plan 40-01. POC immutability gate (Phase 37-06) does not cover `.glb` files. Future Tauri build / mascot render (Phase 43) would surface it then.

**Fix when ready:** `git lfs pull` in worktree, or `git checkout -- tauri/ui/assets/mascot/` once LFS re-fetches binaries.

---

## DEFERRED-40-01-02: `test_main_smoke` 03/04/05 fixture drift

**Discovered by:** Plan 40-01 verification sweep.

**Symptom:** `tests/test_main_smoke.py::test_smoke_03_full_wiring`, `test_smoke_04_no_openrouter_key`, `test_smoke_05_cleanup_closes_all_streams` all fail with `AssertionError: assert 0 == 3` on `audio_mocks["find_device"].call_count`.

**Confirmed pre-existing:** Reproduces on `main` without Plan 40-01 changes.

**Why deferred:** Mock fixture chain bug in smoke tests, not in audio pipeline. Plan 40-01's `test_callback_backward_compat_when_mic_audio_buf_none` directly covers the byte-identical-when-None invariant.

**Fix when ready:** Repair `audio_mocks` fixture chain in `tests/test_main_smoke.py`.

---

## DEFERRED-40-01-03 / DEFERRED-40-02-01: `test_event_gap_dict_shape_and_values` stale snapshot

**Discovered by:** Plans 40-01 + 40-02 (independent confirms).

**Symptom:** `tests/audio/test_constants.py::test_event_gap_dict_shape_and_values` fails on `MIN_EVENT_GAP_PER_TYPE.keys()` — expected set misses Phase 30 SENSE-17/18 additions:

```
Extra items in the left set:
'ACID_LINE_ENTRY'
'DISTORTION_CLIMB'
```

**Confirmed pre-existing:** Reproduces on `main` from at least 200 commits back. Test snapshot never updated when Phase 30 landed.

**Why deferred:** Stale-snapshot test in Phase 30's surface. Plan 40-01 adds new `MIC_AUDIO_PART_*` constants but doesn't touch `MIN_EVENT_GAP_PER_TYPE`. Plan 40-02 is strictly additive. **Plan 40-04 will retune the values and naturally update this test** — fold the snapshot fix into 40-04.

**Fix when ready:** Update expected key set in `tests/audio/test_constants.py:87-101` to include `DISTORTION_CLIMB` (6.0) and `ACID_LINE_ENTRY` (8.0). Plan 40-04 should also retune the values per AUDIO-03 (PHASE 18→10, LAYER_ARRIVAL 16→10, MIX_MOVE 20→14, HEARTBEAT 70→45, TRACK_CHANGE 6→5).

---

## DEFERRED-40-01-04: `test_persona_02_byte_identical_to_v4` post-Phase-18 drift

**Discovered by:** Plan 40-01 verification sweep.

**Symptom:** `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` fails because in-repo `SYSTEM_INSTRUCTION` no longer matches the extracted-from-`cohost_v4.py` body byte-for-byte.

**Confirmed pre-existing:** Reproduces on `main` without Plan 40-01 changes.

**Why deferred:** Persona path is not in Plan 40-01's scope. Drift is expected — Phases 18-20+ intentionally evolved the system prompt beyond v4 baseline. Test is now an outdated byte-identity gate.

**Fix when ready:** Either delete the test (persona no longer byte-identical post-Phase-18) or update the expected baseline.

---

## DEFERRED-40-04-01: `test_each_session_has_events_jsonl_file` missing corpus fixture

**Discovered by:** Plan 40-04 verification sweep (`pytest tests/eval/`).

**Symptom:** `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file` fails with `AssertionError: missing events.jsonl in eval/corpus/sessions/hard_tek_01`.

**Confirmed pre-existing:** The `eval/corpus/sessions/hard_tek_01/` directory was scaffolded with `input.wav` + `genre.txt` + `responses/` but the `events.jsonl` ground-truth labels have not been written yet. Plan 40-04 touched neither the corpus dir nor this test.

**Why deferred:** Corpus labeling is a separate workstream (eval harness Phase 27 / 31 corpus-build plans). Plan 40-04's scope is constants + replay-harness tooling; adding a label file would be an unrelated content commit.

**Fix when ready:** Either (a) commit a real labeled `eval/corpus/sessions/hard_tek_01/events.jsonl` (preferred — closes the diversity-gate); or (b) commit a placeholder `events.jsonl` with `{}` per line and a `WIP_LABELS=true` flag the diversity-gate test honors.

---

## DEFERRED-40-04-02: `tests/eval/fixtures/synthetic_session/genre.txt` regenerated as untracked

**Discovered by:** Plan 40-04 task-2 commit sweep.

**Symptom:** `git status` shows `tests/eval/fixtures/synthetic_session/genre.txt` as untracked after `pytest tests/eval/` runs. The conftest autouse fixture `synthetic_session_fixture_dir` regenerates the file but it's not in `.gitignore`'s `!tests/eval/fixtures/synthetic_session/` allowlist alongside `events.jsonl`.

**Confirmed pre-existing:** Reproduces on `main` without Plan 40-04 changes — the conftest pattern has always emitted this file. Plan 27-01 committed `events.jsonl` and `.gitignore`'d the rest implicitly.

**Why deferred:** Out of Plan 40-04's scope — touching `.gitignore` to whitelist `genre.txt` is a Phase 27 housekeeping fix.

**Fix when ready:** Either (a) add `!tests/eval/fixtures/synthetic_session/genre.txt` to `.gitignore` and `git add` the file once; or (b) extend `tests/eval/conftest.py::_ensure_synth_session` to write `genre.txt` only when missing AND mark it as a fresh-clone bootstrap file (matches current behavior — no change needed, just whitelist).
