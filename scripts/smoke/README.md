# scripts/smoke/

Smoke regression scripts that close milestones. Each script verifies that
a specific milestone shipped without regressing prior fixes. Re-run on
every future milestone close.

## sidecar_bundle_smoke.sh — Phase 98 / v9.0 AUDIT-04

rc1 standalone sidecar bundle regression check. Verifies that v9.0
"Lesson One" (13 `ipc.learn.*` envelopes + ExemplarPlayer second
`sd.OutputStream` + Learn `WebviewWindow` + `learn_messages.py` Python
wrapper) did NOT regress the rc1 fixes:

1. `scripts/dist/patch_livekit_agents_init.py` — livekit-agents 1.x
   circular ImportError patch
2. `tauri/src-tauri/src/sidecar.rs` — `std::process::Command` spawn pin
3. `vibemix-core.macos.spec` — `_ANALYSIS_EXCLUDES` blocklist
4. `tauri/ui/tests/mascot/learn-envelope-doesnt-break-mascot.spec.ts` —
   v9.0-specific mascot envelope namespace audit

Run from repo root:

```bash
bash scripts/smoke/sidecar_bundle_smoke.sh
```

Run a specific check while iterating:

```bash
bash scripts/smoke/sidecar_bundle_smoke.sh --only=mascot-envelope
bash scripts/smoke/sidecar_bundle_smoke.sh --only=help-boot
```

Exit codes:

- `0` — all 10 sub-checks PASS; rc1 un-regressed
- `1` — at least one sub-check FAILED (regression surfaced)
- `2` — pre-flight failed (no sidecar binary; build with
  `uv run python scripts/build_sidecar.py --spec vibemix-core.macos.spec`)

Pre-existing baseline drift (e.g. `tests/sidecar/test_build_sidecar_rename.py`
failures flagged in Phase 93 SUMMARY) is **NOT** in scope for this smoke —
it's flagged inline with `[smoke] WARN:` and does not fail the script.
