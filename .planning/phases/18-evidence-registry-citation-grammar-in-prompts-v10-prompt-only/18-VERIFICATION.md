---
status: passed
phase: 18
phase_name: Evidence Registry + Citation Grammar in Prompts (v1.0 prompt-only)
verified_at: 2026-05-14
mode: gsd-autonomous fully
must_haves_total: 4
must_haves_verified: 4
---

# Phase 18: Evidence Registry + Citation Grammar in Prompts (v1.0 prompt-only) Verification Report

**Phase Goal:** Every Gemini reaction in v2.0 emits `[ev:.../@t]`-style citations grounded in real MusicState events — corpus seeding for Phase 20 enforcement.
**Verified:** 2026-05-14
**Status:** passed
**Re-verification:** No — initial verification
**Mode:** gsd-autonomous fully

## Goal Achievement

The full prompt-only seeding loop is shipped end-to-end: the runtime writes citable observations to `EvidenceRegistry` from the two single-source writers (`state_refresh_loop._tick_once` for `aud`/`mix`, `EventDetector._fire` for `ev`); Gemini receives the EBNF citation grammar in its system instruction every turn AND the per-turn `evidence_corpus[ev=N,aud=M,mix=K]` footer in the user prompt; and `events.jsonl` records `citation_count` per turn with a rolling-50 mean exposed via `EvidenceRegistry.citation_telemetry()` for Phase 16 ear-test consumption.

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `EvidenceRegistry` is a SIBLING write-target to `MusicState` — `state_refresh_loop` and `EventDetector._fire` write synchronously every tick; no separate writer coroutine. | VERIFIED | `src/vibemix/state/refresh.py:367-376` writes 7 `aud` keys per audible tick INSIDE `with state._lock:`; `:312-316`/`:333-336` write `mix:phase=`/`mix:audible_deck=` on change. `src/vibemix/state/event_detector.py:296-331` `_fire` writes `ev:<TYPE>` AFTER cooldown bookkeeping (try/except). `EvidenceRegistry` uses `threading.Lock` (single-writer-per-source contract); no async queue, no separate writer coroutine. Lock ordering documented: `state._lock` OUTER, `registry._lock` INNER. |
| 2 | Citation grammar EBNF locked: `[ev:<TYPE>@<t>]`, `[aud:<key>@<t>]`, `[midi:<event>@<t>]`, `[track:<id>]`, `[screen:<key>]`, `[mix:<derived>]`, `[tend:<profile-fact>]` + multi-citation form. | VERIFIED | `src/vibemix/state/evidence_registry.py:69-93` defines `EVIDENCE_SOURCES = frozenset({"ev","aud","midi","track","screen","mix","tend"})` (all 7 sources) and `EVIDENCE_CITATION_RE` regex matches single-atom + comma-joined multi-citation form. Spot-check 3 confirms `parse_citations("...[ev:KICK_SWAP@45.2,aud:bpm@45.2]...[mix:audible_deck=A]")` returns the 3 expected pairs. Test R cross-package contract (`tests/prompts/test_matrix.py`) locks `EVIDENCE_SOURCES ↔ CITATION_GRAMMAR_BLOCK`. |
| 3 | Citation grammar baked into Gemini system instruction in `AICoach.build_prompt`; v1.0 = prompt-only seeding, NO enforcement yet. | VERIFIED | `src/vibemix/prompts/matrix.py:99-…` defines `CITATION_GRAMMAR_BLOCK`; `:430-501` `build_system_instruction(..., include_citation_grammar=True)` appends grammar block to body. `src/vibemix/agent/dj_cohost.py:182` snapshots registry FRESH per `llm_node` invocation; `:186/189-192` calls `AICoach.build_prompt(ev, registry_snapshot=snapshot)` per turn. `src/vibemix/state/coach.py:119-124` emits `evidence_corpus[ev=N,aud=M,mix=K]` footer when snapshot non-empty. Spot-check 6 confirms grammar in default `build_system_instruction` output and absent under opt-out (used by `persona.SYSTEM_INSTRUCTION` for v4 byte-identity). No linting/stripping in this phase — Phase 20 owns enforcement. |
| 4 | `events.jsonl` records `citation_count_per_response` per AI turn; Phase 16 ear-test consumes the rolling average as Phase 20 readiness signal. | VERIFIED | `src/vibemix/agent/dj_cohost.py:303-323` post-stream block: `parse_citations(full_text) → citation_count`, `recorder.log_event("citation_count", count=…, response_id="NNNN_TS")`, then `registry.record_citation_count(count)` (all best-effort try/except). Telemetry fires BEFORE the silence/slop suppression gate so suppressed turns are counted (Phase 16 needs Gemini's true emission rate). `src/vibemix/state/evidence_registry.py:128/206-247` `_citation_buffer = deque(maxlen=50)` + `_total_turns` counter + `record_citation_count()` + `citation_telemetry()` returning `{window_size, mean, total_turns_observed}`. Spot-check 4 confirms `record_citation_count(3)+record_citation_count(5) → mean=4.0`. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/vibemix/state/evidence_registry.py` | EvidenceRegistry + EBNF regex + parse_citations + telemetry | VERIFIED | 297 lines; class with `write/snapshot/has/clear/__len__/record_citation_count/citation_telemetry`; `EVIDENCE_SOURCES` frozenset; `EVIDENCE_CITATION_RE` compiled regex; `parse_citations` helper. |
| `src/vibemix/state/__init__.py` | Re-exports | VERIFIED | `EVIDENCE_CITATION_RE`, `EVIDENCE_SOURCES`, `EvidenceRegistry`, `parse_citations` all in `__all__`. |
| `src/vibemix/state/refresh.py` | aud + mix writes inside `state._lock`, optional kwarg | VERIFIED | `evidence_registry: EvidenceRegistry \| None = None` kwarg on both `_tick_once` and `state_refresh_loop`; 7 aud writes inside `with state._lock:` block, gated by `state.audible`; mix writes change-only on phase + deck-change branches. |
| `src/vibemix/state/event_detector.py` | _fire writes ev after cooldown bookkeeping | VERIFIED | `evidence_registry` kwarg on constructor; refactored `_fire(ev_type, now, state, *, cooldown_key=None)`; 7 `_fire` call sites updated; KAAN_SPOKE preserves `cooldown_key="MIC"` while emitting ev_type=`"KAAN_SPOKE"` to registry. |
| `src/vibemix/state/coach.py` | registry_snapshot kwarg on evidence_line + build_prompt | VERIFIED | Both methods accept `registry_snapshot` kwarg; footer `evidence_corpus[ev=N,aud=M,mix=K]` appended when non-empty (zero-suppression preserved). |
| `src/vibemix/prompts/matrix.py` | CITATION_GRAMMAR_BLOCK + opt-out kwarg | VERIFIED | `CITATION_GRAMMAR_BLOCK` constant (~1757 chars); `build_system_instruction(..., include_citation_grammar=True)` default-on append at end of body. |
| `src/vibemix/prompts/__init__.py` | Export CITATION_GRAMMAR_BLOCK | VERIFIED | In `__all__`. |
| `src/vibemix/agent/dj_cohost.py` | Per-turn snapshot + telemetry block | VERIFIED | `evidence_registry` kwarg on `__init__`; per-turn `snapshot()` at line 182; post-stream telemetry block at 287-323 emits `events.jsonl` `citation_count` line + updates registry buffer; all best-effort. |
| `src/vibemix/agent/persona.py` | v4 byte-identity preserved via opt-out | VERIFIED | `SYSTEM_INSTRUCTION = build_system_instruction("intermediate", "hype", include_citation_grammar=False)`; `assert SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE` import-time guard still passes. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `state_refresh_loop._tick_once` | `EvidenceRegistry.write` | sync write inside `state._lock` | WIRED | refresh.py:367-376 (aud) + 312-316/333-336 (mix). |
| `EventDetector._fire` | `EvidenceRegistry.write` | sync write after cooldown bookkeeping | WIRED | event_detector.py:331 with try/except wrapper at 329-333. |
| `DJCoHostAgent.llm_node` | `EvidenceRegistry.snapshot` | per-turn fresh call | WIRED | dj_cohost.py:182, threaded into `AICoach.build_prompt(ev, registry_snapshot=…)` line 186/189-192. |
| `AICoach.build_prompt` | `evidence_corpus` footer | `evidence_line(state, registry_snapshot=…)` | WIRED | coach.py:119-124 emits footer when snapshot non-empty. |
| `build_system_instruction(default)` | `CITATION_GRAMMAR_BLOCK` | `body + "\n\n" + CITATION_GRAMMAR_BLOCK` | WIRED | matrix.py:500-501. Default-on; persona.py opts out for v4 backward-compat. |
| `DJCoHostAgent.llm_node` (post-stream) | `events.jsonl citation_count` line | `recorder.log_event("citation_count", count=…, response_id="NNNN_TS")` | WIRED | dj_cohost.py:309-317. |
| `DJCoHostAgent.llm_node` (post-stream) | `EvidenceRegistry.record_citation_count` | rolling buffer update | WIRED | dj_cohost.py:319-323; registry.py:206-219. |
| `EvidenceRegistry.citation_telemetry` | rolling-50 mean for Phase 16 | `deque(maxlen=50)` + `sum/window_size` | WIRED | registry.py:221-247; cold-start returns `mean=0.0` (no NaN). |
| `vibemix.state.EVIDENCE_SOURCES` ↔ `vibemix.prompts.matrix.CITATION_GRAMMAR_BLOCK` | Cross-package vocab contract | Test R parametrize | WIRED | All 7 source identifiers `[ev:`, `[aud:`, `[midi:`, `[track:`, `[screen:`, `[mix:`, `[tend:` present in grammar block (spot-check 5 confirms). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Registry write+snapshot round-trip | `EvidenceRegistry.write` × 3 → `snapshot()` returns expected dict | exact match | PASS |
| `has()` boundary tolerance | `has('ev','KICK_SWAP',46.0,tol=1.0)` True; `has(...,47.0,tol=1.0)` False | inclusive at boundary | PASS |
| `parse_citations` multi+single | Multi-citation `[ev:KICK_SWAP@45.2,aud:bpm@45.2]` + single `[mix:audible_deck=A]` → 3 pairs | exact match | PASS |
| `citation_telemetry` mean | `record_citation_count(3); record_citation_count(5)` → `{'window_size':2,'mean':4.0,'total_turns_observed':2}` | exact match | PASS |
| `EVIDENCE_SOURCES ↔ CITATION_GRAMMAR_BLOCK` vocab contract | All 7 `[<src>:` present in grammar | all 7 present | PASS |
| `build_system_instruction` grammar bake + opt-out | Default contains "CITATION GRAMMAR"; opt-out does NOT; default is strict superset of opt-out | grammar-tail append confirmed | PASS |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| Phase 18 plan-touched test files | `.venv/bin/python -m pytest tests/state/test_evidence_registry.py tests/state/test_event_detector.py tests/state/test_refresh.py tests/state/test_coach.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_matrix_dispatch.py tests/agent/test_coach_mood_template.py tests/prompts/test_matrix.py -q` | 266 passed | PASS |
| Full Phase 18 verification scope | `.venv/bin/python -m pytest tests/state/ tests/agent/ tests/prompts/ -q` | 667 passed, 1 failed (pre-existing `test_persona_02_byte_identical_to_v4` — out of scope per user instructions; v3/v4 POC drift, not introduced by Phase 18), 1 skipped | PASS (1 pre-existing failure explicitly out of scope) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| GROUND-01 | 18-01 + 18-02 | EvidenceRegistry + sync writers | SATISFIED | Registry skeleton (18-01) + sync wiring into refresh/EventDetector (18-02) shipped, P12 race closed via single-writer-per-source contract. |
| GROUND-02 | 18-01 + 18-03 + 18-04 | Citation grammar baked into prompt + telemetry | SATISFIED | EBNF regex + grammar block + per-turn snapshot + per-turn `citation_count` events.jsonl line + rolling-50 mean all wired. |
| GROUND-03 | 18-03 | Grammar in Gemini system instruction in AICoach.build_prompt | SATISFIED | `CITATION_GRAMMAR_BLOCK` baked into default `build_system_instruction`; per-turn snapshot threading in `llm_node` confirmed. |

### Anti-Patterns Found

None in Phase 18 modified files. All 7 modified source files (`evidence_registry.py`, `refresh.py`, `event_detector.py`, `coach.py`, `matrix.py`, `dj_cohost.py`, `persona.py`) checked for `TBD/FIXME/XXX` debt markers — none found.

The `try/except: pass` patterns in dj_cohost.py:303-323 and event_detector.py:329-333 are intentional (per CONTEXT.md threats T-18-02-04 + T-18-04-03: telemetry exceptions MUST NOT break the LLM response stream or corrupt cooldown gates), not anti-patterns.

### Human Verification Required

None for the prompt-only seeding loop itself — the 4 ROADMAP success criteria are observable in code + tests. Phase 16 (Kaan's DJ-ear test against real DJ sets) is the eventual subjective gate for whether Gemini actually learns the citation grammar in prod, but that's explicitly Phase 16's scope per `project_phase_16_kaan_dj_testing.md` memory and CONTEXT.md ("v1.0 = prompt-only seeding, no enforcement"). It is NOT a Phase 18 verification gap.

### Gaps Summary

No gaps. All 4 ROADMAP success criteria for Phase 18 are met by the shipped code:
1. Registry is a sibling write-target to MusicState; sync writers in refresh.py + event_detector.py.
2. EBNF locked + 7 sources + multi-citation form in `EVIDENCE_CITATION_RE` and `CITATION_GRAMMAR_BLOCK`.
3. Grammar baked into Gemini system instruction; per-turn snapshot threading wired in `DJCoHostAgent.llm_node`.
4. `events.jsonl` gets `citation_count` per turn; rolling-50 mean exposed via `EvidenceRegistry.citation_telemetry()`.

The single failing test (`test_persona_02_byte_identical_to_v4`) was pre-existing v3/v4 POC drift before Phase 18 started and is explicitly listed as out-of-scope in the user's verification instructions and in every Plan 18-01/02/03/04 SUMMARY.

---

_Verified: 2026-05-14_
_Verifier: Claude (gsd-verifier)_
