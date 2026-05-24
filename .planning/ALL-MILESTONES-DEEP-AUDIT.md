---
audit: all-milestones-deep
scope: v0.1.0 → v7.0 (Phases 1–70, 9 milestones)
audited: 2026-05-24
head: 58dad2a (branch live-tuning-or-brain)
method: 10 parallel read-only agents verifying each milestone's REQ-IDs against CURRENT code at HEAD (cumulative-integrity lens), + 1 cross-cutting invariant/E2E agent. Central test run as shared ground truth.
test_ground_truth: "4235 passed, 26 skipped, 4 xpassed, 0 failed (uv pytest -q, 222s, exit 0)"
status: tech_debt   # no critical blockers; accumulated intentional-deletion + doc-drift debt
verdicts:
  v0.1.0: holds
  v2.0: partial          # ack-bank cluster deliberately deleted post-ship; REQ traceability now stale
  v2.1: holds
  v3.0: holds
  v3.1: holds
  v4.0: holds            # engineering-side; external-clock items deferred by design
  v5.0: holds
  v6.0: holds
  v7.0: holds            # one doc inaccuracy: Phase 68 has no VERIFICATION.md
  cross_cutting: sound   # 4 cardinal invariants hold; E2E path fully wired
---

# vibemix — All-Milestones Deep Audit (v0.1.0 → v7.0)

A cumulative-integrity re-audit: each milestone's claimed deliverables were re-verified
against the **current** code at HEAD `58dad2a`, not against its own ship-time audit prose.
The question answered is *"does the code today still deliver what each milestone promised,
and did later work regress earlier deliveries?"*

**Headline:** The system is **sound**. 4235 tests green, 0 red. All four cardinal invariants
(single-writer / citation-grounding / trust-the-audio / one-socket) hold against live code.
The full live reaction path is wired end-to-end. No *accidental* regressions across 70 phases.
The only "regression" is a **deliberate** post-v2.0 deletion (ack-bank → strip-to-silence) that
leaves v2.0's REQ traceability stale. Everything else is doc-drift or by-design deferral.

## Per-Milestone Verdicts

| Milestone | Verdict | Notes |
|-----------|---------|-------|
| v0.1.0 MVP Foundation (P1–14) | **holds** | All foundational capabilities live in `src/vibemix/`. Phase-10 HYPE/COACH persona drift the old audit flagged is *resolved* by the matrix dispatcher (later improvement, not regression). |
| v2.0 Research-Driven Ship (P15–26) | **partial** | Anti-slop/grounding/detection/library/debrief spine all holds (several once-"slot-only" items now fully wired). BUT the **Ack Bank latency cluster was deleted** — see Finding #1. |
| v2.1 The Unified Cut (P27–39) | **holds** | Every sampled REQ traces to live code (eval harness, library grounding ≥0.7, hard-tek detectors, mascot additive stack, profile cache-side injection, e2e seam tests). |
| v3.0 Clean OSS Ship (P40–45) | **holds** | Anti-slop grounding gate fully load-bearing in the live turn path. ModelRouter (zero hardcoded SKU literals) means later SKU bumps are the seam working, not drift. |
| v3.1 Distribution-Ready (P46–50) | **holds** | All 44 REQs trace to live artifacts. 23 mascot GLB slots are real glTF binary (not placeholders). Mac+Win installer chain intact. |
| v4.0 SHIP (P51–58) | **holds** (eng) | Real flag-less `main()` confirmed (not a stub); single ws :8765 confirmed; genre autodetect + citation telemetry live. External-clock items (signature, live ear-pass) deferred by design. A completion-audit *does* exist (`v4.0-MILESTONE-COMPLETION-AUDIT.md`). |
| v5.0 The Useful Cut (P59–62) | **holds** | Deterministic Camelot (24-entry table, LLM only narrates), deck-detection ladder, pill-primary/mascot-secondary all survive. Harmonic gate ships default-off (documented Kaan-ear veto). |
| v6.0 The Memory Turn (P63–66) | **holds** | All 3 locked invariants confirmed in code: Gemini-Embedding-002 (no CLAP), sqlite-vec (no managed framework), no-LLM-extraction (CI static gate bans `generate_content` in `memory/*`). |
| v7.0 Open House (P67–70) | **holds** | 19/19 eng-green re-verified. "Zero new capability" claims hold: no runtime deps added, one socket, only `agent/` touched. Tech-debt genuinely deferred. One doc gap — see Finding #2. |
| **Cross-cutting** | **sound** | 4 invariants hold; E2E path fully wired; Python pin `>=3.12,<3.13` confirmed (CLAUDE.md "3.14" is stale); POC scrub enforced, zero root `cohost*.py`. |

## Cardinal Invariants (whole-system)

| Invariant | Status | Evidence |
|-----------|--------|----------|
| Single-writer state | **HOLDS** | `MusicState` @ `state/music_state.py:24`; sole writer `state_refresh_loop` @ `state/refresh.py:532` ("the ONLY writer"). `EventDetector` reads only. |
| Citation-grounding | **HOLDS** | `CitationLinter.check(...)` gates the live hot path @ `agent/dj_cohost.py:1613`; invalid citations → strip → no TTS. See risk #3. |
| Trust-the-audio | **HOLDS** | Real DSP ground truth: `audio/features.py:27` (RMS/FFT/onset/autocorr-BPM) feeds the refresh loop. |
| One-socket | **HOLDS** | Single `WS_PORT=8765` (`audio/constants.py:50`), one `websockets.serve` (`runtime/ws_bus.py:273`). Debrief :8766 is pre-v7.0 + non-concurrent. |

E2E live reaction path verified hop-by-hop (capture → features → single-writer refresh →
typed events → grounded coach prompt → Gemini llm_node → citation gate → TTS → playback;
and state → ws :8765 → mascot/pill). **No broken hops.**

## Findings (actionable, ordered by value)

### 1. v2.0 ack-bank cluster deleted — REQ traceability now stale  *(housekeeping)*
Commit `24ec863` (2026-05-19) retired `agent/ack_bank.py`, the 24-OPUS `audio/ack_bank/` tree,
and all ack tests. This was a **deliberate anti-slop decision** ("silence > pre-canned ack"),
but it means v2.0's **LATENCY-01..05**, **GROUND-05** (ack-bank fallback), and **MASCOT-15**
(ack-only fallback) reference code that no longer exists. Stale doc-comment refs linger at
`agent/dj_cohost.py:465` and `runtime/coach.py:3`. Also MIDI-15's `MidiMapLoader` class →
renamed to `ControllerProfile`+`find_mapping` (functionally equivalent).
→ **Action:** mark those v2.0 REQ-IDs `superseded` in `v2.0-REQUIREMENTS.md`; scrub the two stale comments.

### 2. v7.0 Phase 68 has no VERIFICATION.md  *(doc-traceability, low impact)*
`68-VERIFICATION.md` doesn't exist (only `68-PLAN-INDEX.md` + 5 per-plan SUMMARYs). The
v7.0 audit frontmatter implies all 4 phases have a VERIFICATION.md on disk — inaccurate for 68.
Underlying DEV-01..05 artifacts all verify live; impact is documentation only.
→ **Action:** generate `68-VERIFICATION.md` from the plan SUMMARYs, or correct the audit note.

### 3. Citation bypass one-shot path  *(confirm-intent, bounded risk)*
`agent/dj_cohost.py:1652` allows one uncited emission per breach window (`StrippedRateTracker`).
Bounded and logged, but it is the single place the hard "no hallucination" gate can leak under
sustained linter failure.
→ **Action:** none required if intended; worth a conscious confirm + verifying the bypass window's max emission rate.

### 4. Stale doc-drift  *(cosmetic)*
- `pyproject.toml:74-79` comment says sqlite-vec "ships v2.1 / not exercised in v2.0" — false now (shipped v6.0).
- `CLAUDE.md` Technology-Stack block still says Python 3.14 / single-file POC era — reality is 3.12 + packaged `src/vibemix/`. (CLAUDE.md already carries a STALE warning banner.)
- `KAAN-ACTION-LEGAL.md` has no literal `SHIP-V4`/`cut_release` heading though it's cited as holding that runbook.

## By-Design Deferrals (NOT failures — Kaan's external clock)
- **§SHIP-V4 / OSS-04**: real `cut_release.sh v0.1.0-rc1` publish gated on Apple Dev + SignPath. `cut_release.sh` has a hard guard against auto `gh release create`. v4.0 closes alongside when this fires.
- **§V7-LIVE-01..11**: live-hardware ear-passes + first-CI-green (CI-mocked tests pass; awaiting hardware).
- **§V7-PROXY**: server-side proxy hardening lives in the out-of-tree `api.altidus.world` ops repo.
- **v5.0**: harmonic-clash detector default-off (Kaan-ear veto), deck-vision leg dormant, numpy KS key-estimator = documented unimplemented ladder slot.
- **Phase 16**: hallucination ear-test = human judgment by design, no code artifact.

## Bottom Line
No critical blockers anywhere across 70 phases. The product's anti-slop spine — the thing Kaan
said would make-or-break vibemix — is intact and actually enforced in the live path. Recommended
status: **tech_debt accepted**; the only true cleanup is the v2.0 ack-bank traceability (#1) and
the Phase-68 doc gap (#2). Everything else is intentional deferral or cosmetic drift.
