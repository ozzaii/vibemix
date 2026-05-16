# Phase 40 — Deferred Items

Out-of-scope discoveries logged during execution per executor SCOPE BOUNDARY rule.

## Plan 40-01 — Mic-as-2nd-Gemini-Part

### LFS pointer drift in tauri/ui/assets/mascot/*.glb (21 files)

**Discovered:** Worktree merge of local `main` into `worktree-agent-a1f1006e8be7ee50b`.

**Symptom:** The merge log emitted `Encountered 2 files that should have been
pointers, but weren't: tests/library/fixtures/synthetic_embeddings.npy,
tests/library/fixtures/synthetic_queries.json` and the `git status` of the
worktree shows 21 modified `.glb` files (`Bin 20747776 -> 133 bytes` — LFS
pointer text replacing the binary blob locally).

**Reason it's deferred:**

- The drift is a pre-existing worktree LFS resolution mismatch (the worktree
  branch was created from a much older base; LFS smudge filter content does
  not survive the merge cleanly when the binary files are large).
- Files are unrelated to Plan 40-01 (audio pipeline) — no audio constant, no
  agent code, no test depends on them.
- Re-resolving the LFS pointers is a `git lfs pull` / `git lfs checkout`
  question that requires `git-lfs` to be installed and access to the LFS
  store, not an audio-port code fix.

**What happens if left:**

- The smoke test `test_smoke_06_poc_files_untouched_during_smoke` (Plan 37-06
  POC immutability gate) does NOT cover these `.glb` files (only POC `.py`
  files), so it stays green.
- Future Tauri build / mascot render in Phase 13 would fail; surface it then.

**Action when ready to resolve:** Run `git lfs pull` in the worktree, or
discard the `.glb` modifications via `git checkout -- tauri/ui/assets/mascot/`
once an LFS-aware tool re-fetches the binaries.

### Pre-existing smoke test failures (test_main_smoke 03/04/05)

**Discovered:** Pre-existing on `main` branch tip (commit 00e7b6c).

**Symptom:** `tests/test_main_smoke.py::test_smoke_03_full_wiring`,
`test_smoke_04_no_openrouter_key`, and `test_smoke_05_cleanup_closes_all_streams`
all fail with `AssertionError: assert 0 == 3` against `audio_mocks["find_device"].call_count`.
The driver's `main()` task exits before reaching the mic-stream setup because
the test fixture's mock state doesn't satisfy a downstream init contract.

**Confirmed pre-existing:** Reproduces on `/Users/ozai/projects/dj-set-ai/`
(main project, no Plan 40-01 changes) — the same 3 tests fail there too.
The Plan 40-01 mic-callback signature extension does NOT cause them.

**Reason it's deferred:**

- Pre-existing failure on `main` — Plan 40-01 changes are byte-identical
  backward-compat when `mic_audio_buf=None`, so the callback change isn't
  the cause.
- The fix lives in a different surface (mock fixture setup for
  `_REAL_SLEEP`-based asyncio drivers in smoke 03/04/05), not in the
  audio pipeline this plan targets.
- Plan 40-01's new test `test_callback_backward_compat_when_mic_audio_buf_none`
  covers the byte-identical path directly (passes), giving us the
  invariant the smoke tests would have caught.

**Action when ready to resolve:** Open a separate fix-it task against
`tests/test_main_smoke.py`'s `audio_mocks` fixture chain; not Phase 40
work.

### Pre-existing constants snapshot test failure (test_audio.test_constants)

**Discovered:** Pre-existing on `main` branch tip (commit 00e7b6c).

**Symptom:** `tests/audio/test_constants.py::test_event_gap_dict_shape_and_values`
fails because the test's expected `MIN_EVENT_GAP_PER_TYPE` keys don't include
the Phase 30 SENSE-17/18 additions (`DISTORTION_CLIMB`, `ACID_LINE_ENTRY`).
The constants dict itself is correct; the test snapshot is stale.

**Confirmed pre-existing:** Reproduces on `/Users/ozai/projects/dj-set-ai/`
without any Plan 40-01 changes.

**Reason it's deferred:** Stale-snapshot test in a different surface
(Phase 30 detectors, not Plan 40-01's mic Part). Plan 40-01 adds three
new MIC_AUDIO_PART_* constants but does NOT touch `MIN_EVENT_GAP_PER_TYPE`.

**Action when ready to resolve:** Add `DISTORTION_CLIMB` and `ACID_LINE_ENTRY`
to the expected key-set in `test_event_gap_dict_shape_and_values`. Separate
fix-it task; not Phase 40 work.
