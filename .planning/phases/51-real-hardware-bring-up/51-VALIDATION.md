---
phase: 51
slug: real-hardware-bring-up
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-21
---

# Phase 51 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (Python sidecar) + `cargo test` (Rust sidecar resolver) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`), `tauri/src-tauri/Cargo.toml` |
| **Quick run command** | `uv run pytest -q tests/runtime/test_ws_bus_empty_frames.py` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~60 seconds (default, excludes `slow`/`integration`/`macos_audio`) |

---

## Sampling Rate

- **After every task commit:** Run the plan's `<automated>` command (quick).
- **After every plan wave:** Run the full suite (`pytest -q`) plus the wave's opt-in markers (`-m integration` / `-m slow` where the plan adds them).
- **Before `/gsd:verify-work`:** Full suite green; `-m integration` ws_bus test green; short soak (`-m slow`) green.
- **Max feedback latency:** 60 seconds for the default suite.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 51-01-01 | 01 | 1 | BRINGUP-04 | — | ws_broadcast never puts `{}` / meter-less frame on the wire | integration | `uv run pytest -m integration tests/runtime/test_ws_bus_empty_frames.py -q` | ❌ W0 | ⬜ pending |
| 51-01-02 | 01 | 1 | BRINGUP-04, BRINGUP-01 | — | boot-smoke: ws_bus reaches phase=silent within N s, no empty frames | integration | `uv run pytest -m integration tests/runtime/test_ws_bus_empty_frames.py -q` | ❌ W0 | ⬜ pending |
| 51-02-01 | 02 | 1 | BRINGUP-04 | T-51-02-01 | dev source-spawn path gated by env; bundled path unchanged when absent | unit | `cargo test --manifest-path tauri/src-tauri/Cargo.toml resolve_sidecar` | ❌ W0 | ⬜ pending |
| 51-02-02 | 02 | 1 | BRINGUP-04 | — | rebuild script + dev-loop doc present and runnable | cli | `bash -n scripts/dev/run_sidecar_from_source.sh` | ❌ W0 | ⬜ pending |
| 51-03-01 | 03 | 2 | BRINGUP-05 | — | soak sampler reports bounded RSS growth + zero underruns | slow | `uv run pytest -m slow tests/runtime/test_soak_stability.py -q` | ❌ W0 | ⬜ pending |
| 51-03-02 | 03 | 2 | BRINGUP-05 | — | slow marker deselects soak from default run; CLI entry exists | slow + cli | `uv run pytest --collect-only -m "not slow" tests/runtime/test_soak_stability.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/runtime/test_ws_bus_empty_frames.py` — new `integration`-marked broadcast tap test (BRINGUP-04/01).
- [ ] `tests/runtime/test_soak_stability.py` — new `slow`-marked soak test (BRINGUP-05), modeled on `tests/recording/test_60min_soak.py`.
- [ ] `tauri/src-tauri/src/sidecar.rs` `#[cfg(test)]` mod — extend with dev-vs-bundled resolver test.
- [ ] Existing infra (`pytest`, `psutil==7.2.2`, `cargo test`) covers everything else — no framework install needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real ≥30-min live DJ-set soak on Kaan's MacBook | BRINGUP-05 | True sign-off needs real audio + Kaan's ears/hands; cannot be automated headlessly with fidelity | Run a full set through BlackHole; run `python -m vibemix.runtime.soak --seconds 1800 --attach` against the live sidecar; confirm zero underruns + bounded RSS + no dropout/hang. |
| App boots to live listening session on real Mac, no boot crash | BRINGUP-01 | Real hardware launch (already observed green this session); full confirmation rides the Kaan-ear surface | `cargo tauri dev`; confirm Rust app + sidecar + Vite `:1420` + ws_bus `:8765` reach `phase=silent` cleanly. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s (default suite)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-21
