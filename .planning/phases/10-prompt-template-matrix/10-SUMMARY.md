---
phase: 10-prompt-template-matrix
plan: rollup
type: summary
status: complete
completed_at: 2026-05-12
requirements_covered:
  - PROMPT-01   # 6-cell skill × mode prompt matrix with anchor phrases per cell
  - PROMPT-02   # Negative dictionary (~40 banned phrases) + post-hoc filter
  - PROMPT-03   # TurnHistory anti-repetition ring (capacity = 12)
  - PROMPT-04   # <silence/> token short-circuit in llm_node
  - PROMPT-05   # Describe-before-infer + past-tense framing in every cell
  - PROMPT-06   # Coach scorecard at session end (qualitative bands only)
  - PROMPT-07   # Reaction throttle — global 8s min-gap cap on top of per-event cooldowns
wave_commits:
  - 95e6703   # 6-cell prompt matrix + negative-dict filter
  - a885a58   # TurnHistory ring + Coach scorecard
  - c46a3f7   # dj_cohost matrix dispatch + silence/slop short-circuit
  - 6d5bfea   # 10-01 plan SUMMARY
  - (this commit)   # Wave 2 docs + 10-SUMMARY + STATE/ROADMAP advance
test_count: 978
test_delta: "+139 vs Phase 9 baseline (839 → 978)"
---

# Phase 10 — Prompt Template Matrix — Summary

**Verdict:** All 5 ROADMAP success criteria PASS. Phase 10 shipped — 6 prompt cells dispatched by env vars, full anti-slop stack (3-layer enforcement), TurnHistory ring kills opener repetition, `<silence/>` short-circuit suppresses TTS turns, Coach scorecard emits qualitative bands at session end. Phase 16 + 17 are the live verification gates; Phase 10 puts the substrate in place.

## What Phase 10 Delivered

**Production code (`src/vibemix/prompts/`)** — new package:
- `matrix.py` — 6 cells (HYPE_BEGINNER, HYPE_INTERMEDIATE, HYPE_PRO, COACH_BEGINNER, COACH_INTERMEDIATE, COACH_PRO) as module-level constants; `build_system_instruction(skill, mode) -> str` dispatcher. HYPE_INTERMEDIATE byte-identical (8358 bytes) to v4 SYSTEM_INSTRUCTION for backward compat.
- `negative_dict.py` — 40 banned phrases across 3 buckets (Generic AI tells, Empty hype, Slop framings); compiled `NEGATIVE_REGEX` with word-boundary matching.
- `filter.py` — `filter_for_slop(text)` returns `("<silence/>", [matches])` on banned-phrase hit; passes clean text through unchanged.
- `turn_history.py` — TurnHistory class (deque maxlen=12); `push_user`, `push_model`, `as_text()` returning `<recent_turns>` block byte-formatted to POC.
- `scorecard.py` — `summarize_session(events)` returns one of `"clean"` / `"decent"` / `"abrupt"` / `"train-wreck"`. Regex-pinned never-numeric output.

**Production code refactored:**
- `src/vibemix/agent/persona.py` — thin re-export: `SYSTEM_INSTRUCTION = build_system_instruction("intermediate", "hype")`. Backward compat preserved.
- `src/vibemix/agent/dj_cohost.py` — reads `VIBEMIX_SKILL_LEVEL` + `VIBEMIX_MODE` env vars (defaults `intermediate` / `hype`); dispatches to right cell. `llm_node` override accumulates streaming output, runs `filter_for_slop`, suppresses turn on `<silence/>` token or filter match (logs `silence_short_circuit` / `slop_suppressed` events).

**Tests (978 total, +139 vs Phase 9's 839 baseline):**
- `tests/prompts/test_matrix.py` — 6 cells exist + each contains anchor phrases + ban list + describe-before-infer + past-tense + `<silence/>` instruction. HYPE_INTERMEDIATE = v4 verbatim assertion.
- `tests/prompts/test_negative_dict.py` — ≥40 phrases across 3 buckets.
- `tests/prompts/test_filter.py` — synthetic banned outputs suppress; clean outputs pass.
- `tests/prompts/test_turn_history.py` — ring capacity, alternation, format match.
- `tests/prompts/test_scorecard.py` — band classification + never-numeric assertion.
- `tests/agent/test_dj_cohost_matrix_dispatch.py` — env var dispatch.
- `tests/agent/test_dj_cohost_silence_short_circuit.py` — mock LLM yields `<silence/>` → empty stream + event logged.

**Docs:**
- `docs/prompt-templates.md` — user-facing reference: 6-cell table, anti-slop stack explanation, TurnHistory format, `<silence/>` semantics, scorecard bands, reaction throttle.

## Architecture Decisions Pinned

1. **6-cell matrix, not arbitrary persona library.** Skill (Beginner/Intermediate/Pro) × Mode (Hype/Coach). Locks the surface area; UI in Phase 12 surfaces these 6 toggles only.
2. **HYPE_INTERMEDIATE = byte-identical v4 SYSTEM_INSTRUCTION.** Backward compat preserved; default behavior unchanged.
3. **3-layer anti-slop enforcement** — prompt-level enumeration of bans + post-hoc regex filter + per-cell golden tests. Defense in depth.
4. **Filter suppresses whole turn on banned-phrase hit** (not in-place rewrite). Simpler, blunter; can be relaxed in Phase 14 polish if needed.
5. **TurnHistory in-memory only.** No disk persistence v1; ring resets per-session.
6. **`<silence/>` is a literal token the LLM emits.** Cascade `llm_node` checks for it in streamed output; suppresses TTS turn entirely. Most important word a DJ friend can say is sometimes nothing.
7. **Coach scorecard never numeric.** Regex-pinned in tests. Persona of a DJ friend never reduces a set to a score.
8. **Env var dispatch (`VIBEMIX_SKILL_LEVEL` / `VIBEMIX_MODE`)** chosen over runtime API. Simpler for v1; Phase 12 Settings panel writes the env vars on change + signals dj_cohost to rebuild instructions.

## ROADMAP Success Criteria → Acceptance Gates

| # | Criterion | Status |
|---|-----------|--------|
| 1 | 6 prompt cells with anchor vocabulary + negative-dict bans in each | ✅ PASS — all 6 cells exist; per-cell anchor phrase tests green; ban-list grep tests green |
| 2 | TurnHistory ring; no duplicate openers within 10-min session | ✅ PASS — ring + `<recent_turns>` injection; opener-repeat regression test green |
| 3 | `<silence/>` short-circuit fires on low-RMS-variance probes | ✅ PASS — `dj_cohost.py` llm_node intercepts token; silence_short_circuit event logged. Live verification (≥80% on "nothing happening" probes) deferred to Phase 16. |
| 4 | Coach scorecard returns qualitative bands only — never numeric | ✅ PASS — regex-pinned in tests (`\d+\/10` and `\d+\.\d+` patterns find 0 matches in scorecard outputs) |
| 5 | Per-event-type cooldown + max-rate cap + vocal-section gate → no AI utterances during lyrics | ✅ PASS structurally — global 8s gap added on top of Phase 3 per-type cooldowns + Phase 6 vocal gate. Live verification (10-min mixed-genre recording) deferred to Phase 16. |

## Test Count Delta

- Phase 9 baseline: 839 tests
- Phase 10 final: 978 tests (+139)
- Failed: 1 (pre-existing CoreAudio environmental — deferred-items.md entry #3)
- Skipped: 6

## Deferred to Future Phases

- **Live verification of `<silence/>` short-circuit on real "nothing happening" probes** → Phase 16 (≥80% target).
- **Live verification of vocal-section gate on 10-min mixed-genre recording** → Phase 16.
- **In-app UI for picking skill/mode** → Phase 12 Settings panel.
- **A/B test of prompt cells against recorded sets** → Phase 16 + Phase 17 (hallucination + slop-grading gates).
- **Multi-language prompts** → out of v1.
- **Per-genre prompt variants** → not needed (genre is data, not persona).

## What's Next

**Phase 11 — Tauri Shell + Calibration Wizard**: Tauri 2.x scaffold + Python sidecar (PyInstaller `--onedir`) + IPC contract + 3-step calibration wizard (permissions → output device + sample-rate test → controller probe). Phase 11 is the largest Phase remaining — Rust shell + Python embedding + UI work.
