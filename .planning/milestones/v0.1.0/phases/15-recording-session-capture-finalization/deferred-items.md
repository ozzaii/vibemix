# Phase 15 — Deferred / out-of-scope items discovered during execution

## Pre-existing environmental: cargo check fails on missing PyInstaller sidecar binary

**Discovered during:** Plan 15-02 Task 2 (cargo check sanity gate)
**Symptom:** `cargo check` inside `tauri/src-tauri/` fails with
`resource path 'binaries/vibemix-core-aarch64-apple-darwin' doesn't exist`.
**Root cause:** The Phase 11 W1 PyInstaller spec produces a sidecar binary
at `tauri/src-tauri/binaries/vibemix-core-<triple>/...` which `tauri.conf.json5`
declares as `bundle.externalBin = ["binaries/vibemix-core"]`. The build script
asserts the resource path exists; in this worktree (and any clean checkout)
the binary has not been built.
**Out of scope for Plan 15-02:** This pre-existed Plan 15-02 — `cargo check`
on the pre-edit state of `tauri/src-tauri/` fails identically. Resolution is
to run `python scripts/build_sidecar.py` first, which is Phase 11 W1's
established workflow. Plan 15-02 only verified the *configuration-level*
correctness of the assetProtocol + CSP additions (via the JSON5 parse check
and the `tauri = { features = [..., "protocol-asset"] }` feature flag — see
Cargo.toml comment).

## Pre-existing environmental — Plan 15-03 scope-boundary observations

**Discovered during:** Plan 15-03 final test sweep.
**Symptoms:**
1. `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` fails
   with `FileNotFoundError: 'cohost_v4.py'` — POC file is `.gitignore`-listed
   / untracked and not present in fresh worktree checkouts (same artifact
   Plan 15-02 SUMMARY noted for `test_smoke_06_poc_files_untouched_during_smoke`).
2. `tests/test_phase05_verification.py::test_g5_poc_files_untouched` fails
   with the same root cause.
3. `tests/test_audio_macos_live.py::test_open_voice_output_completes_without_real_audio_device`
   fails because the test rig expects an exact-name "Headphones" output
   device that isn't available in this worktree's CoreAudio environment.

**Out of scope for Plan 15-03:** None of these failures are caused by Plan
15-03 changes. Verified by `git stash && pytest <failing tests>` reproducing
identical errors before any Plan 15-03 edits land. Resolution is upstream
in tooling (POC-file distribution / live-device CI marker), not in this
plan's scope.
