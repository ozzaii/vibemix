# vibemix — Requirements (v8.0 "Proof & Polish")

**Milestone:** v8.0 "Proof & Polish" — Phases 71–76
**Goal:** Take the system from "engineering-sound on paper" to **proven, easy, and live on GitHub**: everything logged · simulated · reported · tested · fixed · re-tested · verified · GitHub-done — plus genuine **ease of use for users** and a **whole-design level-up loop**.
**Baseline:** Deep audit (`.planning/ALL-MILESTONES-DEEP-AUDIT.md`, 2026-05-24) = system **sound**, 4235 tests green, 4 cardinal invariants hold, only housekeeping findings. v8.0 proves it for real and polishes it, it does not rescue it.
**Mode:** `gsd-autonomous fully`. Irreducible human items (Apple Dev + SignPath signatures, real-hardware ear-passes, public signed release publish, social publishes) ride forward to KAAN-ACTION — they never block.

**Anti-creep acid test (v8.0):** *"Does this make an existing capability genuinely logged / simulated / reported / tested / fixed / verified / pushed — or make it easier to use / better-looking — WITHOUT adding a new product capability, a new AI/embedding provider, a new managed framework, a new ws port, or a new IPC envelope?"* If not, defer. Gemini-only holds. No CLAP/MERT/OpenL3/torch, no Mem0/Letta/Zep/Cognee.

---

## v8.0 Requirements

### Observability — "everything logged" (LOG)
- [ ] **LOG-01**: User can view a unified debug-log surface in-app spanning the Python sidecar + Rust parent + TS UI (the in-flight `debug_log.rs` / `debug-log.ts` / `debug-log-ws.ts` surface), landed and wired.
- [ ] **LOG-02**: Every reaction turn logs its evidence packet + citation-gate decision (grounded vs stripped) to the per-session log, auditable after the fact.
- [ ] **LOG-03**: Audio device + backend selection, MIDI connect/hot-plug, and proxy-fallback events are all timestamped in the log.
- [ ] **LOG-04**: A log-level / `--debug-log` switch routes verbose diagnostics without altering default UX or the default console output.

### Simulation — "simulated" (SIM)
- [ ] **SIM-01**: A simulation harness replays a recorded/synthetic DJ session end-to-end through the real reaction path (capture → features → refresh → events → grounded coach → citation gate → reaction) with zero live hardware and zero live Gemini.
- [ ] **SIM-02**: Synthetic device fixtures simulate BlackHole capture + FLX4 controller + device-select, so the §V7-LIVE hardware paths get software-verified in CI.
- [ ] **SIM-03**: A simulated full session emits a deterministic artifact proving the logged + grounded + reaction path works headlessly.

### Reporting — "reported" (RPT)
- [ ] **RPT-01**: The test run produces a saved machine + human report (pass/fail/skip/xfail counts + coverage summary) as a build artifact.
- [ ] **RPT-02**: A simulated-session report summarizes events fired, reactions emitted, citations grounded vs stripped, and latency.
- [ ] **RPT-03**: A v8.0 verification report ties each REQ-ID to concrete evidence (test, artifact, or KAAN-ACTION carveout).

### Tested · Fixed · Verified (TEST)
- [ ] **TEST-01**: Full default `pytest -q` suite green (0 failed) at v8.0 close on Kaan's Mac.
- [ ] **TEST-02**: Full opt-in marker grid exercised (`macos_audio`, `windows_only` (simulated), `integration`, `slow`, `e2e`, `cli`, `network`) — each marker green or justified as a KAAN-ACTION live-hardware carveout.
- [ ] **TEST-03**: TS (vitest/playwright) + Rust (`cargo test`) suites run green for the landed branch work.
- [ ] **TEST-04**: Deep-audit findings closed — #1 v2.0 ack-bank REQ-IDs marked `superseded` + stale comments scrubbed; #2 Phase-68 `VERIFICATION.md` generated; #3 citation one-shot-bypass consciously confirmed (or tightened) with its max emission rate verified; #4 residual doc-drift scrubbed.
- [ ] **TEST-05**: A fix → re-test → fix loop drives every red green; the final green run is verified and committed (no skipped/xfail graveyards introduced).

### Ease of use (UX)
- [ ] **UX-01**: First-run path (install → device select → first reaction) is guided and forgiving, with clear empty / loading / permission states.
- [ ] **UX-02**: Audio device selection + routing is discoverable and self-explanatory — no manual BlackHole guesswork for a new user.
- [ ] **UX-03**: Mode switching (hype/coach, Beginner/Intermediate/Pro) and settings are clear, labeled, and reversible.
- [ ] **UX-04**: Every failure mode (no audio, no API key, proxy down, no MIDI) surfaces actionable guidance instead of a silent dead-end.

### Whole-design level-up loop (DESIGN)
- [ ] **DESIGN-01**: Session UI + floating pill polished to the CDJ-Whisper bar with zero HIGH findings from the paired design auditor.
- [ ] **DESIGN-02**: Mascot overlay + debrief + wizard + settings drawer pass the same design bar.
- [ ] **DESIGN-03**: A review → fix → re-review loop runs until the design auditor returns zero HIGH findings; output reads as crafted, never AI slop.
- [ ] **DESIGN-04**: Design tokens are consistent across all surfaces (Saira + JetBrains Mono, 5 warm blacks + single amber accent, glow-not-bevel tactility).

### GitHub done (GH)
- [ ] **GH-01**: All local history (the ~528-commit backlog ahead of `origin/main`) pushed to origin; `origin/main` brought current with the verified state.
- [ ] **GH-02**: CI is green on the full matrix for the pushed state.
- [ ] **GH-03**: Repo presence finalized — README, badges, and landing reflect current reality with no stale claims.
- [ ] **GH-04**: *(KAAN-ACTION carveout — explicitly NOT auto-fired)* Public signed release (§SHIP-V4 `cut_release.sh` → `gh release create`) + 5-channel social publishes remain gated on the Apple Dev + SignPath signature clock and Kaan's sign-off.

---

## Out of Scope (v8.0)

- Any new product capability, new AI/embedding provider, new managed-memory framework, new ws port, or new IPC envelope (anti-creep acid test).
- Live-hardware ear-passes on real BlackHole / real FLX4 USB / fresh-Mac TCC walk — **simulated** in v8.0; real hardware stays KAAN-ACTION (§V7-LIVE).
- Apple Dev Agreement + SignPath OSS cert acquisition (external clock — Francesco + Kaan).
- The actual public signed-release publish + social launch (GH-04 carveout).
- Server-side proxy hardening (lives in the out-of-tree `api.altidus.world` ops repo — §V7-PROXY).
- `VIBEMIX_RECALL_ENABLED=1` flip (independent §RECALL-EAR Kaan-ear clock).
- Deferred future product items: multimodal moment-audio, cross-session arc priors, ProDJ Link primary source, `/hatch` user-gen mascot.

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| LOG-01, LOG-03 | 71 | pending |
| LOG-02, LOG-04 | 72 | pending |
| SIM-01..03 | 72 | pending |
| RPT-01..03 | 73 | pending |
| TEST-01..05 | 73 | pending |
| UX-01..04 | 74 | pending |
| DESIGN-01..04 | 75 | pending |
| GH-01..03 | 76 | pending |
| GH-04 | 76 | KAAN-ACTION (carveout) |
