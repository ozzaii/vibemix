---
phase: 80
slug: ground-gemini-as-secondary-ear
status: planned
nyquist_compliant: true
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
| **Quick run command** | `PYTHONPATH=src python3 -m pytest -q -k "ground or secondary or mic_part or citation or linter or model_literal or router or 3part_labeling"` |
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

> Both GROUND requirements map to automated proofs — no API key (fake genai stream + fake/real registry snapshot). The "is the second ear worth it / which model wins" judgment is the Phase-81 BENCH (audio+DSP vs DSP-only cells) + Kaan's-ear (parked, never faked, never blocks).

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 80-01-T1 | 80-01 | 1 | GROUND-01 (cold-path byte-identity pin) + GROUND-02 (router-resolve pin) | unit (real-green) | `PYTHONPATH=src python3 -m pytest tests/agent/test_dj_cohost_ground_secondary.py -k "flag_off_byte_identical or model_via_router" -x` | ⬜ pending |
| 80-01-T2 | 80-01 | 1 | GROUND-01 (flag-ON framing scaffold + un-backed-claim strip guard) | unit (xfail-strict) | `PYTHONPATH=src python3 -m pytest tests/agent/test_dj_cohost_ground_secondary.py -q` | ⬜ pending |
| 80-02-T1 | 80-02 | 2 | GROUND-01 (gated secondary_ear framing in build_parts_description) | unit (TDD) | `PYTHONPATH=src python3 -m pytest tests/prompts/test_matrix_3part_labeling.py tests/repo/test_model_literal_gate.py -q` | ⬜ pending |
| 80-02-T2 | 80-02 | 2 | GROUND-01 (flag thread + guard flip) + GROUND-02 (bench-alias doc) | unit (TDD) | `PYTHONPATH=src python3 -m pytest tests/agent/test_dj_cohost_ground_secondary.py tests/agent/test_dj_cohost.py tests/repo/test_model_literal_gate.py -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Test for GROUND-01 (hallucination guard — the real deliverable): with the audio Part present, a Gemini stream emitting a claim about an event NOT in the `EvidenceRegistry` (e.g. `[ev:PHANTOM_DROP@45.2]`) strips the turn to `<silence/>` — trust-the-audio (invariant #3) wins; audio cannot fabricate. → `test_unbacked_audio_claim_strips` (80-01-T2 scaffold, flips real-green in 80-02-T2).
- [ ] Test for GROUND-01 (gated framing): the secondary-ear framing clause (`"secondary grounding signal"`) appears in the prompt only when the flag is ON; flag OFF → prompt byte-identical to v8.0 (the audio Part-1 is still fed as today, but no new framing). → `test_flag_on_audio_framed` (scaffold) + `test_flag_off_byte_identical` (real-green pin).
- [ ] Test for GROUND-02: the reaction model resolves via `model_router.resolve("live_coach")` with zero hardcoded literals (`test_model_literal_gate.py` stays green); the `live_coach` alias is the documented bench-swap point. → `test_model_via_router` (80-01-T1, real-green) + doc comment (80-02-T2).
- [ ] Cold-path byte-identity: flag OFF → reaction request + prompt byte-identical to v8.0 baseline (existing `test_dj_cohost*.py` + `test_matrix_3part_labeling.py` goldens stay green).

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

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
