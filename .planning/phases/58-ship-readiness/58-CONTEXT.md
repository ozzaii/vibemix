# Phase 58: Ship Readiness - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Orchestrator-grounded (autonomous `fully`). Depends on Phase 54 + 55 (live validation feeds Gate 2b hallucination + Gate 6b e2e report), Phase 57 (polish complete before final artifacts). FINAL phase of v4.0.

<domain>
## Phase Boundary

Get **everything that does not require an external signature** green and proven: (1) `cut_release.sh`'s 6-gate pre-flight + Gate 2b (hallucination) + Gate 6b (e2e report) run green on **real artifacts** (not simulated fixtures) as far as is possible without Kaan's pending live inputs; (2) the **§E2E-50A-WALK** is dischargeable by driving the real app end-to-end (the recipe + harness are ready; the actual recorded walk on the Mac is KAAN-ACTION); (3) the exact **one-button SHIP-CUT sequence is documented + pre-verified** via dry-run so the ONLY thing left after this phase is the external signatures. Covers **REL-01/02/03**.

**Out of this phase:** the literal signed publish (Apple Dev Agreement via Francesco + SignPath OSS cert — external clock, KAAN-ACTION); new features.
</domain>

<decisions>
## Implementation Decisions (autonomous `fully`)

### The engineerable / Kaan-action split (LOCKED)
- **Engineering closes everything not requiring an external signature** (per `gsd-autonomous fully` + STATE blockers). The signed publish stays KAAN-ACTION. This phase makes the release **one-button-after-signatures** and proves the button works minus the signature.
- **REL-01 (gates green on real artifacts):** run `scripts/launch/cut_release.sh`'s pre-flight gates on REAL built artifacts. Build the real artifacts where the dev machine can (the macOS app/DMG + sidecar). Gates that are fully engineering-determinable MUST go green now. Gates that depend on a Kaan input — **Gate 2b (hallucination)** is fed by Kaan's live ear-pass sign-off on Phases 54+55 (`54-HUMAN-UAT` + `55-HUMAN-UAT`), **Gate 6b (e2e report)** is fed by the §E2E-50A-WALK recording — are **PRE-WIRED + dry-run-verified** so they flip green the moment Kaan's input lands, with NO engineering step left to discover. Document exactly which gates are green-now vs gated-on-Kaan-input.
- **REL-02 (§E2E-50A-WALK):** the real end-to-end walk on the MacBook with real DJ-set audio, recorded to `docs/e2e/2026-05-walk.webm`, is **KAAN-ACTION** (needs real hardware + real audio + screen recording). Engineering ships: the exact walk script/checklist, the recording recipe, and confirms the harness/app path the walk exercises is green. Do NOT fake the .webm.
- **REL-03 (one-button SHIP-CUT documented + pre-verified):** document the EXACT one-button ship sequence; run a **dry-run** that confirms everything-but-the-signature is ready (artifacts build, gates wired, version/changelog/notarization-stub paths resolve) — a green dry-run with the signature step stubbed. Surface ALL external-clock + Kaan-action discharge items in ONE consolidated cookbook (Apple Dev Agreement, SignPath OSS cert, the §E2E walk, the Gate-2b ear-passes, + carry-forward v3.0/v3.1 KAAN-ACTION items if still open). The v3.x precedent exists: KAAN-ACTION-LEGAL §SHIP-01..13 cookbook + `audit_ship_v1_decision.py` — extend/reuse, don't reinvent.

### Public release tag = `v0.1.0-rc1` (autonomous recommended call — Kaan can override)
- RESEARCH Open-Q2: the Gate-1 tag regex (currently hardcoded `^v2\.1\.0-rc[0-9]+$`) must be re-pointed to the v4.0 ship tag. **Decision: the PUBLIC release tag is `v0.1.0-rc1`** — vibemix's first public OSS release. Grounded: `pyproject.toml` is `0.1.0-dev0`, the project already references `v0.1.0-rc1` (the rc1 open-bugs surface), and CLAUDE.md frames this as "Bravoh's first open-source release." `v4.0` remains the INTERNAL milestone identity (so Gate 4's milestone audit is `v4.0-MILESTONE-AUDIT.md`; Gate 1's public tag regex is `^v0\.1\.0-rc[0-9]+$`). If Kaan prefers `v4.0.0-rc1` as the public tag, it's a one-line regex flip — surface it as a Kaan-confirm in the SHIP-CUT cookbook, do NOT block.

### Sidecar binary rebuild (carried from Phase 57)
- The **sidecar binary rebuild** (`scripts/build_sidecar.py`) deferred from Phase 57 lands here as part of producing real artifacts for the gates. Rebuild + verify the sidecar is current before the gate run.

### Don't reinvent the release machinery — verify + wire + document
- `scripts/launch/cut_release.sh` + the gate scripts + the v3.x KAAN-ACTION cookbook already exist. This phase VERIFIES they run green on real artifacts, WIRES the two Kaan-input-gated gates to flip cleanly, and DOCUMENTS + dry-runs the one-button sequence. Any change is surgical + test-pinned.

### Kaan's parallel WIP is OFF-LIMITS
- Kaan has ~17 uncommitted WIP files this session (persona/cooldown/audio tuning + tauri rust). Phase 58 must NOT touch them. Release-gate/doc work is in `scripts/launch/`, `docs/`, release config — disjoint from his WIP.
</decisions>

<code_context>
## Existing Code Insights
- **Release driver:** `scripts/launch/cut_release.sh` (the 6-gate pre-flight + SHIP-CUT). Research must map its exact gates + which are engineering-determinable vs Kaan-input-gated.
- **Ship-decision audit:** `scripts/audit/audit_ship_v1_decision.py` (610 lines, v3.x — pre-fills rubric cells) + the KAAN-ACTION-LEGAL §SHIP-01..13 discharge cookbook (v3.x precedent for the consolidated KAAN-ACTION surface).
- **E2E:** `docs/e2e/` (has README; the walk artifact target is `docs/e2e/2026-05-walk.webm`). The e2e harness from prior phases (`tests/e2e/*`).
- **Sidecar build:** `scripts/build_sidecar.py` (rebuild deferred from Phase 57).
- **Gate 2b feed:** `54-HUMAN-UAT.md` + `55-HUMAN-UAT.md` (Kaan's hype + coach ear-pass sign-offs). **Gate 6b feed:** the §E2E-50A-WALK recording.
</code_context>

<specifics>
## Specific Ideas
- **Gate inventory task:** enumerate every `cut_release.sh` gate; mark green-now / gated-on-Kaan; run the green-now ones on real artifacts; assert the gated ones are wired to flip with no hidden engineering step.
- **Dry-run task:** a SHIP-CUT dry-run (signature step stubbed) that exits green = "everything but the signature is ready."
- **KAAN-ACTION cookbook task:** one consolidated, exact discharge runbook covering Apple Dev Agreement, SignPath OSS cert, §E2E-50A-WALK recording, Gate-2b ear-passes (54+55), + any open v3.x carry-forwards.
- **Sidecar rebuild task:** rebuild + verify the sidecar binary is current.

<deferred>
## Deferred Ideas (KAAN-ACTION — external clock / real hardware)
- **External signatures:** Apple Developer Program Agreement update (Francesco) + SignPath OSS Foundation cert (Kaan) — the literal signed publish. The SHIP-CUT is one-button-after-these.
- **§E2E-50A-WALK recording** on the real Mac with real DJ-set audio → `docs/e2e/2026-05-walk.webm` (feeds Gate 6b).
- **Gate 2b hallucination sign-off** — Kaan's live ear-pass on hype (54) + coach (55) across ≥2 genres (the `*-HUMAN-UAT` items from this session's 54/55).
- Carry-forward v3.0/v3.1 KAAN-ACTION items still open (SignPath cert shared with v3.x; Tart VM walk; etc.).
</deferred>
