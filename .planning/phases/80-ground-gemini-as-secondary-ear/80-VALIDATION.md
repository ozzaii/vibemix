---
phase: 80
slug: ground-gemini-as-secondary-ear
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-26
---

# Phase 80 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q -k "ground or secondary or mic_part or citation or linter or model_literal or router"` |
| **Full suite command** | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |
| **Estimated runtime** | ~120 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (scoped `-k`)
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

> Populated by the planner. Both GROUND requirements map to automated proofs — no API key (fake genai stream + fake registry snapshot). The "is the second ear worth it" judgment is the Phase-81 BENCH (audio+DSP vs DSP-only cells) + Kaan's-ear (parked, never faked, never blocks).

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| TBD | — | 0 | GROUND-01/02 | unit | Wave-0 test stubs | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test for GROUND-01 (hallucination guard — the real deliverable): with the audio Part present, a Gemini stream emitting a claim about an event NOT in the `EvidenceRegistry` (e.g. `[ev:PHANTOM@t]`) strips the turn to `<silence/>` — trust-the-audio (invariant #3) wins; audio cannot fabricate.
- [ ] Test for GROUND-01 (gated framing): the secondary-ear framing clause appears in the prompt only when the flag is ON; flag OFF → prompt byte-identical to v8.0 (the audio Part-1 is still fed as today, but no new framing).
- [ ] Test for GROUND-02: the reaction model resolves via `model_router.resolve("live_coach")` with zero hardcoded literals (`test_model_literal_gate.py` stays green); the `live_coach` alias is the documented bench-swap point.
- [ ] Cold-path byte-identity: flag OFF → reaction request + prompt byte-identical to v8.0 baseline (existing `test_dj_cohost*.py` goldens stay green).

*Existing pytest infrastructure covers all phase requirements — build on `tests/agent/test_dj_cohost_mic_part.py` helpers. No framework install needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The second ear actually makes reactions richer/better (worth the cost) | GROUND-01 | Subjective + needs live audio — Phase-16 rule | Phase-81 BENCH audio+DSP vs DSP-only cells + KAAN-ACTION ear verdict; never auto-judged |
| The bench's winning model swaps in cleanly by config | GROUND-02 | The model choice is decided by Phase-81 BENCH | KAAN-ACTION: after the bench, set the `live_coach` alias to the winning model in `_router_config.py` |

*All unit-level phase behaviors have automated verification (no API); the "worth it" + model-choice judgments are Phase-81 BENCH + KAAN-ACTION (parked, never block).*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
