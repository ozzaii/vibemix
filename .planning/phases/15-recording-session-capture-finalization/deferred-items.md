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
