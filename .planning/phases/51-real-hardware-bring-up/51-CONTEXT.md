# Phase 51: Real-Hardware Bring-Up - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Orchestrator-grounded — real-hardware findings from a live session injected directly (autonomous `fully`), so planning works against observed reality, not guesses.

<domain>
## Phase Boundary

Boot the app + Python sidecar on Kaan's real Mac, reach a stable live "listening" session with clean startup logs, and survive a ≥30-min full-set run with zero unhandled exceptions or unbounded memory. Covers **BRINGUP-01** (boot to listening), **BRINGUP-04** (triage + fix runtime errors surfaced in Tauri console / sidecar logs), **BRINGUP-05** (≥30-min stability, no dropout/hang/leak).

Audio-path (BRINGUP-02) is Phase 52; controller (BRINGUP-03) is Phase 53. This phase is boot + stability only.
</domain>

<decisions>
## Implementation Decisions (Claude's discretion, autonomous `fully`)

- **Fix the ws_bus empty-frame emission.** Live tap of `ws://127.0.0.1:8765` showed intermittent empty `{}` frames interleaved with real level frames. The broadcaster must not emit empty payloads — skip or fully populate each frame. (BRINGUP-04)
- **Add a headless stability soak harness** — sample sidecar RSS + count playback-queue underruns/dropouts over a configurable duration; assert bounded RSS growth and zero underruns. Orchestrator can run a short automated soak; the real ≥30-min DJ-set soak is Kaan-action. (BRINGUP-05)
- **Address the stale-sidecar dev loop.** The running dev sidecar is a *pre-built* PyInstaller binary (`tauri/src-tauri/target/debug/binaries/vibemix-core-*`) that does NOT reflect `src/vibemix/` source edits — so source fixes (e.g. the Phase-52 BPM stabilizer `fd25337`) are invisible in `cargo tauri dev` until rebuilt. Provide a dev path that runs the Python sidecar from source (or an explicit rebuild step) so live testing reflects HEAD. (BRINGUP-04 / dev-loop)
- Triage Tauri console + sidecar stderr for unhandled exceptions across a session; every surfaced error gets fixed or explicitly logged-and-handled.
</decisions>

<code_context>
## Existing Code Insights (verified live this session)

- **Boot is already green (BRINGUP-01).** `cargo tauri dev` runs: Rust app (`target/debug/vibemix`), the `vibemix-core` sidecar, Vite UI on `:1420`, and the mascot/levels ws_bus **listening on `:8765`** broadcasting at ~30 Hz (`phase=silent`, `mic≈0.003` with no input). Clean boot, no crash.
- **ws_bus**: `src/vibemix/runtime/ws_bus.py` — `ws_broadcast` + `ipc.session.snapshot` frames (the snapshot carries the transcript_delta landed in `e2d1156`). The empty-`{}` frames originate here.
- **Sidecar entry**: `src/vibemix/__main__.py` (`main()`); device wiring `INPUT_DEVICE="BlackHole 2ch"`, `OUTPUT_DEVICE="MacBook Pro Speakers"`, `MIC_DEVICE="MacBook Pro Microphone"`.
- **Tauri externalBin** points at the built sidecar binary (stale-binary root cause above).
</code_context>

<specifics>
## Specific Ideas

- Live-drive validation recipe (orchestrator, no controller needed): play audio into **BlackHole 2ch** and tap **ws://127.0.0.1:8765** for level + snapshot frames.
- Boot smoke: confirm ws_bus reaches `phase=silent` cleanly within N seconds of launch; assert no empty frames over a sample window.
</specifics>

<deferred>
## Deferred Ideas (Kaan-action — real hardware, autonomous carveout)

- The real **≥30-min live DJ-set soak** on Kaan's MacBook (his ears + hands) is the true BRINGUP-05 sign-off. Engineering ships the soak harness + a short automated run; the full-length real run rides the live-drive / Kaan-ear surface (per `project_phase_16_kaan_dj_testing`).
</deferred>
