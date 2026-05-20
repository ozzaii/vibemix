# Phase 51: Real-Hardware Bring-Up — Research

**Researched:** 2026-05-21
**Mode:** Orchestrator-grounded (subagent spawning unavailable in this runtime — research conducted inline against live source + the grounded CONTEXT.md). Findings verified against HEAD (`688427e`), not guesses.

This phase is **boot + stability only**: BRINGUP-01 (boot to listening — already verified green this session), BRINGUP-04 (triage + fix runtime errors; close the ws_bus empty-frame issue + the stale-sidecar dev loop), BRINGUP-05 (≥30-min stability soak harness; the real run is Kaan-action). Audio-path is Phase 52, controller is Phase 53.

---

## 1. ws_bus empty-`{}` frame emission (BRINGUP-04)

### Where frames originate
`src/vibemix/runtime/ws_bus.py::ws_broadcast` is the **only** WS emitter under the live `main()` (Tauri spawns the sidecar flag-less). It emits **two** frame kinds on the same socket:

1. **Mascot frame** (30 Hz, `ws_bus.py:262-277`): `json.dumps({**levels.snapshot(), "audible":..., "deck":..., "phase":..., "bpm":..., "mood":..., ...})`. This payload **always carries ≥12 keys** — it can never serialize to `{}` as long as `levels.snapshot()` and `state` are well-formed.
2. **`ipc.session.snapshot` frame** (15 Hz, every `SNAPSHOT_EVERY_N=2` ticks, `ws_bus.py:291-311`): built by `_build_session_snapshot`, schema-validated, then `json.dumps(snap_msg, separators=(",",":"))`. Always a typed envelope (`{"type":"ipc.session.snapshot","payload":{...}}`).

### Root-cause hypotheses (ranked)
The live tap showed `{}` interleaved with real frames. Neither emitter above can *intentionally* produce `{}`. The realistic sources, in priority order:

- **H1 — `levels.snapshot()` returns an empty dict during the warm-up window.** If `Levels.snapshot()` can return `{}` (e.g. before the first EMA update, or under a lock-contention/early-return path), the mascot frame degrades to `{"audible":...}` — *not* `{}` — because the static keys are always present. So this is **unlikely to be the literal `{}` source** but must be ruled out (a snapshot that returns `{}` would still merge with the static keys). **Action: confirm `Levels.snapshot()` always returns the 3 meter keys.**
- **H2 — A *separate* writer is interleaving frames on `:8765`.** The mascot webview (`mascot.html`) and the Tauri `ws_client.rs` both subscribe; if any client *echoes* or any code path sends a bare `json.dumps({})` heartbeat/keepalive, the tap would see `{}`. **Action: grep the whole tree for `json.dumps({})` / empty-dict sends / ping frames.** websockets library ping/pong frames are control frames (opcode 0x9/0xA), not text `{}`, so a naive text tap that decodes only `message` events should not surface those — but a tap printing every frame including control frames could misreport. **Action: confirm the tap semantics and that no app code emits a literal empty object.**
- **H3 — The snapshot path emits an under-populated frame that *looks* empty in the tap.** `_build_session_snapshot` always returns a populated typed dict (verified: `type` + `payload` always present), so the validated snapshot can't be `{}`. Ruled out for the validated path. But if `_validate_snapshot` ever raised and a **partial** `json.dumps` had already been queued, that's a bug — verified it cannot, because `json.dumps` happens *after* validation (`ws_bus.py:300-301`).

### Decision (autonomous `fully`)
The fix must be **defensive at the emit boundary**: the broadcaster must never put an empty or whitespace-only payload on the wire. Concretely — guard the mascot send so a frame is only sent when the serialized payload is a non-empty JSON object with at least the meter keys; and add a regression test that taps a real `ws_broadcast` server over a sample window and asserts **zero** frames decode to `{}` (or to a dict missing the meter keys). This closes the symptom regardless of which hypothesis is the literal cause, and the test makes the contract permanent. Pair it with a root-cause grep so we *also* fix the source, not just the boundary.

### Existing test surface to extend
- `tests/runtime/test_ws_bus.py` — pins mascot frame shape + 30 Hz cadence (`test_ws_07`). The new empty-frame regression belongs here or in a sibling, marked `integration` (it binds a real `:8765`-style server via the websockets test harness already used by these tests).
- `tests/runtime/test_ws_bus_snapshot.py` (already committed at HEAD) — pure builder tests; the snapshot path is already proven non-empty. **Do not duplicate; extend the broadcast-level coverage instead.**

---

## 2. Stale-sidecar dev loop (BRINGUP-04 / dev-loop)

### Confirmed mechanism
- `tauri/src-tauri/src/sidecar.rs::resolve_sidecar_path` resolves the sidecar **only** via `app.path().resource_dir()` → `binaries/vibemix-core-<triple>/vibemix-core-<triple>` — i.e. the **pre-built PyInstaller onedir binary** copied in by `scripts/build_sidecar.py::install_into_tauri_binaries`.
- There is **no source-execution path**. `cargo tauri dev` therefore runs whatever binary was last built into `tauri/src-tauri/binaries/` (or `target/debug/binaries/`), so `src/vibemix/` edits (e.g. the Phase-52 BPM stabilizer `fd25337`) are invisible until a rebuild.
- `build_sidecar.py` runs PyInstaller (`dist/vibemix-core/` onedir) then copies into the tauri binaries dir. It's the canonical rebuild route — but it's a full PyInstaller build (slow), not a fast dev iteration.

### Options
- **Opt A — Dev-mode source spawn (env-gated).** In `resolve_sidecar_path` (or the spawn path), when a `VIBEMIX_DEV_SIDECAR=1` (or `tauri::is_dev()`) env is set, spawn `uv run python -m vibemix` (or `python -m vibemix` against the repo `src/`) instead of the bundled binary. Pros: instant reflection of HEAD; no PyInstaller round-trip. Cons: requires `uv`/venv present in the dev shell; a second code path in `sidecar.rs` (must keep prod path untouched — Pitfall: don't let dev path leak into release builds).
- **Opt B — Explicit fast-rebuild step + doc.** A `scripts/dev/rebuild_sidecar.sh` (or a make/just target) that runs `build_sidecar.py` for the host triple only, plus a documented "rebuild before `cargo tauri dev`" note. Pros: zero new runtime code path; uses the proven build route. Cons: still slow (full PyInstaller), and easy to forget — the exact failure mode that bit this session.
- **Opt C — Both: a thin dev spawn (A) as the default dev loop, with the rebuild script (B) as the fallback / pre-release verification.**

### Decision (autonomous `fully`)
**Opt C, A-first.** Add an env-gated dev source-spawn path in `sidecar.rs` (`VIBEMIX_DEV_SIDECAR=1` → spawn the repo Python entrypoint), guarded so the **release/bundled path is byte-for-byte unchanged** when the flag is absent. Ship a small `scripts/dev/run_sidecar_from_source.sh` (or equivalent) + a `docs/` / CONTRIBUTING note documenting the dev loop, and keep `build_sidecar.py` as the rebuild-for-prod route. Add a Rust unit test (in the existing `sidecar.rs` `#[cfg(test)]` mod) asserting the resolver picks the source path when the env flag is set and the bundled path otherwise. This makes "live testing reflects HEAD" the default dev experience without risking the shipped binary.

> **Landmine:** the prod path resolves through `resource_dir()` and `sidecar_triple()`; the dev path must NOT call `resource_dir()` (it errors / points at a non-existent bundle in `cargo tauri dev`). Branch *before* the `resource_dir()` call. Exit-code sentinels 2 (port-in-use) and 3 (audio-device-missing) must still work in both paths.

---

## 3. ≥30-min stability soak harness (BRINGUP-05)

### Reference pattern (proven, in-repo)
`tests/recording/test_60min_soak.py` is the template:
- `@pytest.mark.slow` so the default `pytest -m "not slow"` run skips it (the `slow` marker is registered in `pyproject.toml:203`).
- A second test asserts the slow marker actually deselects the soak from the default run (belt-and-braces).
- Uses `tracemalloc` for a memory ceiling assertion (peak < budget).
- Pre-allocates reusable buffers so allocator pressure is test-bounded.

### What BRINGUP-05 specifically needs (per CONTEXT)
A **headless stability soak harness** that, over a **configurable duration**:
- Samples **sidecar RSS** (resident memory). `psutil==7.2.2` is already a dep (`pyproject.toml:63`) — use `psutil.Process(pid).memory_info().rss`. No new dependency.
- Counts **playback-queue underruns / dropouts**. The harness asserts **zero** underruns and **bounded RSS growth** (e.g. final RSS ≤ baseline × factor, or slope under threshold) over the window.
- Is **duration-configurable** via env (e.g. `VIBEMIX_SOAK_SECONDS`, default short for the automated run) so the orchestrator can run a short automated soak in CI/locally, and Kaan can run the full ≥30-min real soak.

### Two layers (the autonomous carveout)
1. **Engineering ships:** the soak harness (sampler + assertions) + a **short automated run** (e.g. 60–120 s synthetic) wired as a `slow`/`integration`-marked test, plus a runnable CLI/script so Kaan can point it at a live session for the real ≥30-min run.
2. **Kaan-action (deferred):** the real **≥30-min live DJ-set soak** on his MacBook (his ears + hands) is the true BRINGUP-05 sign-off, per `project_phase_16_kaan_dj_testing`. Engineering does NOT block on it; it rides the live-drive / Kaan-ear surface.

### Decision (autonomous `fully`)
Ship a `vibemix.runtime` soak sampler module (RSS + underrun counters, duration-configurable) + a `slow`-marked test running a short synthetic soak that asserts bounded RSS + zero underruns + the marker-deselect guard. Provide a thin CLI entry (`python -m vibemix.runtime.soak --seconds N --pid <sidecar-pid>` or attach-to-live) so the real run is one command. Underrun counting hooks into the existing `PlaybackQueue` — research the queue's existing drop/underrun accounting before inventing a new counter (reuse `Levels`/queue stats if present; otherwise add a minimal monotonic counter exposed for sampling).

> **Landmine:** RSS on macOS includes shared pages; assert on **growth** (delta/slope), not absolute RSS, to avoid flaky failures from the PyInstaller runtime footprint. Mirror `test_60min_soak.py`'s tolerance philosophy.

---

## 4. BRINGUP-01 — boot to listening (already green)

Verified live this session (per CONTEXT): `cargo tauri dev` boots the Rust app, the `vibemix-core` sidecar, Vite UI on `:1420`, and the ws_bus on `:8765` broadcasting ~30 Hz (`phase=silent`, `mic≈0.003`, no input) with a clean boot and no crash. BRINGUP-01's remaining engineering value is a **boot-smoke regression** that confirms ws_bus reaches `phase=silent` cleanly within N seconds of launch and emits no empty frames over a sample window — which **folds into the empty-frame test** (§1) rather than needing its own plan. The "launch on real Mac, no boot crash" success criterion is satisfied by the live observation + the boot-smoke assertion; the full real-hardware confirmation is the same Kaan-ear surface as BRINGUP-05.

---

## Pitfalls (consolidated)

1. **Don't fix only the symptom.** Pair the empty-frame emit-guard + regression test with a root-cause grep (`json.dumps({})`, empty sends, keepalive frames) so the actual source is found, not just masked.
2. **Don't touch the mascot frame shape or its 30 Hz cadence** — `mascot.html` + `test_ws_bus.py::test_ws_07` pin both. The fix must be additive/defensive, not a reshape.
3. **Dev-sidecar path must not leak into release.** Branch before `resource_dir()`; gate on an env flag; assert the prod path is unchanged when the flag is absent.
4. **Soak asserts on RSS *growth*, not absolute** (macOS shared-page noise + PyInstaller footprint).
5. **Reuse `psutil` (already a dep)** — no new dependency for RSS sampling.
6. **The real ≥30-min run is Kaan-action** — engineering ships the harness + a short automated run; do not gate the phase on the live run.

## Validation Architecture

The phase's truth is observable behavior on the wire and in memory:
- **ws_bus cleanliness:** a real `ws_broadcast` server, tapped over a sample window, emits **zero** `{}` frames and zero frames missing the meter keys; reaches `phase=silent` within N seconds of start. (Pinned by an `integration`-marked test.)
- **Runtime-error triage:** every error surfaced in Tauri console / sidecar stderr is either fixed or explicitly logged-and-handled; verified by a clean startup-log assertion + the dev-loop now reflecting HEAD (so source fixes are observable, not masked by a stale binary).
- **Stability:** short automated soak asserts bounded RSS growth + zero playback underruns over a configurable window; the `slow` marker deselects it from the default run; the real ≥30-min run is Kaan-action.
