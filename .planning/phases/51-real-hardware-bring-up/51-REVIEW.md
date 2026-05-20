---
phase: 51
slug: real-hardware-bring-up
status: clean
reviewed: 2026-05-21
reviewer: GSD code-review (Opus 4.7)
diff_range: 209a1e2..c029f6a
scope: src/ tauri/ scripts/ tests/
---

# Phase 51 — Code Review

> Deep review of the Phase 51 diff (`git diff 209a1e2..c029f6a -- src/ tauri/
> scripts/ tests/`). 9 commits, +1218/-22 across 6 files. **Verdict: CLEAN** —
> no HIGH or MEDIUM findings. Three LOW notes recorded; none require a fix.

---

## Files reviewed

| File | LOC Δ | Verdict |
|------|-------|---------|
| `src/vibemix/runtime/ws_bus.py` | +54/-22 | clean (emit guard is a genuine root-cause-aware belt-and-suspenders) |
| `tauri/src-tauri/src/sidecar.rs` | +278 | clean (release path byte-identical; dev arm landmine-safe) |
| `src/vibemix/runtime/soak.py` | +374 | clean (growth-based RSS; non-invasive underrun observation) |
| `tests/runtime/test_ws_bus_empty_frames.py` | +245 | clean (real WS bind + real client) |
| `tests/runtime/test_soak_stability.py` | +243 | clean (real queue + real subprocess) |
| `scripts/dev/run_sidecar_from_source.sh` | +46 | clean (env contract in sync with resolver) |

---

## 1. `ws_bus.py` — emit-boundary empty/meter-less frame guard

**Does it drop a valid frame?** No. The guard fires only when `mascot_frame`
is falsy OR is missing one of `music`/`voice`/`mic`. `Levels.snapshot()`
(`src/vibemix/audio/levels.py:65`) always returns exactly
`{"music","voice","mic"}` under its lock, and the frame additionally carries
11 literal static keys — so the frame is structurally incapable of failing the
guard. **The branch is unreachable in normal operation.** It only trips on a
genuine future upstream regression (a snapshot returning `{}`, a vanished
`state` attr). Confirmed by reading `Levels.snapshot`.

**Does it break the 30Hz cadence contract?** No. The normal path is unchanged
— same key set, same ordering, same `await asyncio.sleep(1/30)`. Verified
`tests/runtime/test_ws_bus.py` (cadence/shape pins) still passes alongside the
new tests (27 passed). On the unreachable skip branch the loop still sleeps
`1/30` and `continue`s, so cadence is preserved even there.

**Is the `ipc.session.snapshot` cadence (`SNAPSHOT_EVERY_N=2`) still correct
if a tick is skipped?** In normal operation YES — the guard never fires, so
`tick += 1` always runs and the ~15Hz snapshot cadence is byte-identical. On
the (unreachable) skip branch, `continue` happens *before* `tick += 1`, so a
skipped malformed frame also skips that tick's snapshot. This is the correct
conservative behavior: if the mascot frame is malformed, suppressing the same
tick's snapshot avoids emitting a half-broken pair. Recorded as LOW-1 below
purely because it's a subtle interaction, not a defect.

**Root-cause fix or symptom masking?** Genuine root-cause analysis. SUMMARY
51-01 documents that the live `{}` seen in the `:8765` tap was the **tap
mis-decoding WebSocket control frames** (ping/pong opcodes) as empty text — NOT
a frame the app put on the wire. Greps found no app-level empty-dict emitter.
The guard is an explicit, documented permanent contract at the send boundary,
not a band-aid over an unknown bug.

**Findings:**
- **LOW-1** — On the (unreachable) skip branch, `tick` does not increment, so
  `SNAPSHOT_EVERY_N` cadence would drift by one if the branch ever fired. No
  impact in practice (branch is unreachable; and skipping the paired snapshot
  on a malformed tick is correct). No fix.
- **LOW-2** — The code comment + SUMMARY say the skip is "logged once-per-
  occurrence", but it `print`s on *every* occurrence (no de-dupe). Since the
  branch is unreachable, there is no log-spam risk in practice; this is a
  doc/comment wording inaccuracy only. No fix.

## 2. `sidecar.rs` — env-gated dev source-spawn (`VIBEMIX_DEV_SIDECAR=1`)

**Is the bundled/release path byte-identical when the flag is absent?** YES —
this is the critical safety property and it holds. When `VIBEMIX_DEV_SIDECAR !=
"1"`: `bundled = Some(resolve_sidecar_path(&app)?)` → resolver returns
`SidecarInvocation::Bundled(path)` → the match arm does
`app.shell().command(&bin)` then optional `.args(["--wizard"])`. This is
verbatim the pre-Phase-51 code. Covered by
`resolve_sidecar_flag_absent_returns_bundled` (passing).

**Does the dev arm avoid `resource_dir()` (the documented landmine)?** YES.
When the flag is set, `bundled = None` (the `else` that calls
`resolve_sidecar_path` is skipped entirely), so `resource_dir()` is never
invoked on the dev path. The resolver consumes `bundled` only on the `Bundled`
arm.

**Are exit-code sentinels 2 (port-in-use) / 3 (audio-device-missing) preserved
in both arms?** YES. The match produces only the `cmd` binding; all watchdog
supervision — stdout/stderr drain, the `exit_code == 2 || exit_code == 3`
sentinel handling (`sidecar.rs:236`), and the wizard handoff — lives *after*
`cmd.spawn()` (line 157) and is fully shared. Neither arm bypasses it.

**Any way the dev path leaks into a release build?** The gate is a runtime
`std::env::var("VIBEMIX_DEV_SIDECAR")` check, not `cfg!(debug_assertions)`. So
a *release* binary could be told to dev-spawn if someone explicitly exports the
env var at runtime. This is the documented opt-in design (the env contract is
also exported by `scripts/dev/run_sidecar_from_source.sh`). The release
*default* (flag absent) is unchanged, and in a shipped `.app` the dev arm has
no `uv`/source/`pyproject.toml` to run against, so it would fail-loud through
the existing spawn-error path rather than corrupt anything. Recorded as LOW-3.

**Findings:**
- **LOW-3** — Dev spawn is runtime-env-gated, not compile-gated, so a release
  build technically honors `VIBEMIX_DEV_SIDECAR=1` if set. Default-safe and
  fail-loud in a shipped bundle. Acceptable per the documented opt-in design;
  could optionally `&& cfg!(debug_assertions)` in a future hardening pass. No
  fix now.

Compile check: `cargo check --manifest-path tauri/src-tauri/Cargo.toml` →
clean. The `cmd` construction in both match arms type-checks against the real
Tauri `Command` API.

## 3. `soak.py` + `test_soak_stability.py` — stability soak harness

**RSS assertion on growth/slope not absolute?** YES. `SoakResult.growth_bytes
= final_rss - baseline_rss`; `assert_healthy` raises only when
`growth > max_growth_bytes`. Absolute RSS is reported (baseline/final/max +
raw sample series) but never asserted on. Docstrings explicitly call out macOS
shared-page / allocator noise as the reason.

**Underrun counter observes the real PlaybackQueue WITHOUT mutating the hot
path?** YES. `run_soak` drives a real `PlaybackQueue` via its public
`push()`/`pull()` and classifies the *returned bytes* with `is_underrun`. The
prod queue code is untouched (verified `audio/buffers.py:337` unchanged in the
diff). `is_underrun` correctly accounts for `pull()` always returning exactly
`n` bytes (zero-padded) — it compares `held < requested` rather than chunk
length, with an all-zero-chunk fallback only when `held` is unknown.

**Does the `slow` marker deselect from the default run?** YES.
`test_short_synthetic_soak_bounded_rss_zero_underruns` is `@pytest.mark.slow`;
`test_slow_marker_deselects_soak_from_default_pytest_run` proves it via a real
`pytest --collect-only -m "not slow"` subprocess. Confirmed empirically:
`pytest -q tests/runtime/` (default markers) → 175 passed, soak loop never ran.

## 4. Test quality — real vs shallow

All new tests exercise REAL behavior, not mocks:
- `test_ws_bus_empty_frames.py` binds a **real** `ws_broadcast` server on an
  ephemeral free port (monkeypatching `ws_bus.WS_PORT` to avoid colliding with
  a live `:8765` dev session) and connects a **real** `websockets` client. Has
  a non-zero frame-count guard (`len(frames) > 0`) so a silent no-op cannot
  pass green. Boot-smoke reads the real `MusicState().phase` default rather
  than hard-coding, with a sanity pin so a future default change is loud.
- `test_soak_stability.py` uses a **real** `PlaybackQueue` + `Levels`, a
  **real** subprocess `pytest --collect-only` for the deselect guard, and a
  **real** CLI subprocess (`python -m vibemix.runtime.soak --seconds 1`).
- `sidecar.rs` tests inject a fake env *closure* into a pure resolver (correct
  — never touches process env); `repo_root_from_manifest_is_two_levels_up`
  asserts the real repo root contains `pyproject.toml`.

None tautological.

---

## Test evidence (re-run this review)

- `pytest -m "slow or integration or cli or not slow" tests/runtime/{test_ws_bus,test_ws_bus_empty_frames,test_ws_bus_snapshot,test_soak_stability}.py` → **27 passed**
- `pytest -q tests/runtime/` (default markers) → **175 passed** (slow/integration/cli deselected)
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml resolve_sidecar` → **5 passed** (incl. `resolve_sidecar_flag_absent_returns_bundled`)
- `cargo test ... repo_root_from_manifest` → **1 passed**
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml` → clean
- `python -c "import vibemix.runtime.ws_bus, vibemix.runtime.soak, vibemix.__main__"` → imports OK

---

## Findings summary

| Severity | Count | Items |
|----------|-------|-------|
| HIGH | 0 | — |
| MEDIUM | 0 | — |
| LOW | 3 | LOW-1 (skipped-tick snapshot cadence, unreachable), LOW-2 ("logged once" comment vs every-occurrence, unreachable), LOW-3 (dev gate is runtime-env not compile-gated, default-safe) |

No fixes committed — all findings are LOW and informational. The diff is clean,
well-documented, and the load-bearing safety properties (release path
byte-identical; landmine `resource_dir()` avoided on dev arm; exit sentinels
preserved; hot path unmodified) all hold.
