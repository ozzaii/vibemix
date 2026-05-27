# Session-end handoff — 2026-05-27 ~19:00 TRT

Terse pickup note. Long version: `.planning/handoffs/2026-05-27-rc1-integration-followup.md`.

## State at session end

- **Branch**: `live-tuning-or-brain` == `main` == origin (`0246e7b1` or whatever the latest of this session's chain is — `git log --oneline -10` to see).
- **App alive for ear-pass**: dev-source path. `cargo run --no-default-features` from `tauri/src-tauri/` with `VIBEMIX_DEV_SIDECAR=1` → `:8765` binds, full session loop active.
- **All bundle-side fixes shipped**: spec blocklist (`3d2900ce`), runtime hook (`99c951a7`), patch_livekit_agents_init + build_sidecar wiring (`d58c722f`), sidecar.rs std::process rewrite + libc kill (`938c822a`), patch script extended to cycle-break agent_session (`0246e7b1`). 9 regression tests in `tests/dist/`.
- **Marketing copy honest**: "Mac + Windows" → "macOS today; Windows ships with v0.1.0 stable" across 11 files (`6114bd0d`); anchor/test fixtures migrated.
- **pretag baseline**: 5 pass / 1 fail (Phase 16 ear-pass) / 2 warn — same as inherited.

## Step 7 (ship) — TWO gates left

1. **Phase 16 ear-pass** — Kaan listens to a live DJ session on the dev-source app (which is healthy + faithful), then edits `.planning/phases/16-hallucination-verification-gate/16-VERIFICATION.md` → `status: passed`.
2. **Ship path** — pick one with Kaan:
   - **A. Ship-as-rc-with-known-flake**: tag now, release notes line "macOS bundle may need 2-3 retries on first launch; v0.1.0 stable closes this." rc1 is "test in the wild" by design; Phase 17 grading is collected against the rc binary anyway. ~0 more code.
   - **B. Half-day vendor fix**: fork `livekit-agents` 1.x into `vendor/`, restructure `cli/cli.py` to not transitively pull `voice`, OR lazy-load all of cli's voice-touching code. The actual root cause. Then tag. (Patch script attempt this session got us close but doesn't fully fix launchd-spawn.)
   - **C. Architectural**: drop `livekit-agents`, use `google-genai` Live API directly for `RealtimeModel`. v0.1.x scope.

## Known bug to NOT forget

`tauri-plugin-shell` 2.3 + macOS `launchd`-spawn both trigger a flaky `livekit.agents` circular `ImportError` in the PyInstaller-frozen bundle that the source-side patches in this session DON'T fully fix. Reproduced 3/3 with a minimal `.app` wrapper around the bundled sidecar + `open` launch. Verified via dis-assembly that the source patches ARE in the bundled bytecode — the bug is deeper than source-level cli/voice import order.

`subprocess.Popen`, plain `std::process::Command::new(bin).spawn()` from an isolated Rust binary, and `vibemix-core </dev/null` standalone ALL boot clean. ONLY the Tauri-shell-as-parent + `.app open` combo crashes. Tauri-plugin-shell DOES use std::process underneath, but something about the CF-initialized parent + bundle spawn path keeps re-triggering the cycle.

Three concurrent Codex sessions on this tree throughout the day shipped intel/ wiring; coordinate before further intel/ work.

## What to do next session

1. `git log --oneline -10` — see what landed since handoff.
2. Read `.planning/handoffs/2026-05-27-rc1-integration-followup.md` for the long version + 6 audit verdicts.
3. Confirm whether Kaan's ear-pass has landed in `16-VERIFICATION.md`.
4. Decide path A/B/C with Kaan. If A: `git tag v0.1.0-rc1 && git push origin v0.1.0-rc1` → release.yml fires. If B/C: pick up where this session left off (patch script in `scripts/dist/patch_livekit_agents_init.py` already handles __init__ + agent_session; next layer is `cli/cli.py` itself).
5. **Post-tag mandatory**: download the signed DMG, `open vibemix.app`, wait 30s, check `lsof -nP -iTCP:8765 -sTCP:LISTEN`. If bound → ship clean. If not → tag delete, fix, retry.
