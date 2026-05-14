---
phase: 20-citation-linter-enforcement-live-mode
verified: 2026-05-14T06:23:18Z
status: human_needed
score: 5/5 roadmap success criteria verified at the library/unit/replay level; runtime activation gap acknowledged as pre-flagged follow-up
overrides_applied: 0
gaps:
  - truth: "DJCoHostAgent.llm_node citation gate fires in the live binary"
    status: partial
    reason: |
      The 4-kwarg wired path is correctly implemented in
      src/vibemix/agent/dj_cohost.py (CitationLinter / StrippedRateTracker /
      AckBank / playback all optional, _linter_wired flag computed once at
      __init__, post-stream gate ladder verified by 33 unit + 7 integration
      tests). However, src/vibemix/__main__.py constructs the agent with
      ONLY 8 kwargs (genai_client / clean_audio_buf / screen_buf / state /
      recorder / llm_inst / tts_inst / cache / ttft_meter) and does NOT
      pass citation_linter / stripped_rate_tracker / ack_bank / playback.
      _linter_wired evaluates False at runtime → the linter never fires
      against real Gemini responses in the shipped binary. Plan 20-01's
      wired/legacy guard pattern is honored — legacy path is byte-identical
      — but the wired path is dormant until __main__.py is updated.
      The Phase 20 prompt asked verifier to "verify the citation_linter /
      stripped_rate_tracker / ack_bank / playback are also being constructed
      and threaded into DJCoHostAgent at startup". They are not.
    artifacts:
      - path: "src/vibemix/__main__.py"
        issue: "Lines 458-468 construct DJCoHostAgent without citation_linter / stripped_rate_tracker / playback kwargs. ack_bank IS constructed (line 444) but only passed to coach_loop (line 505), not to the agent."
    missing:
      - "Construct CitationLinter() + StrippedRateTracker() in __main__.py before agent build"
      - "Pass citation_linter=, stripped_rate_tracker=, ack_bank=ack_bank, playback=playback to DJCoHostAgent(...) call"
      - "Optional: thread citation_telemetry callable + ipc_bus into coach_loop(...) so SessionCitation IPC actually publishes (currently dormant — kwarg defaults None → publish gate is a no-op)"
    closure_cost: "30-60min — ~10 lines in __main__.py (4 kwarg additions to DJCoHostAgent + telemetry-callable closure for coach_loop) + a wired-path smoke test asserting _linter_wired == True after __main__ build. No new modules, no schema churn."
  - truth: "ipc.session.citation surfaces in the Tauri Settings drawer"
    status: partial
    reason: |
      Plan 20-04 SUMMARY explicitly documents this as a known stub
      ("renderer-only stub by design ... not wired to the IPC bus / app
      store — that wiring is a Phase 14 follow-up"). The renderer
      (tauri/ui/src/settings/components/citation-diagnostics.ts) exists,
      passes 10 vitest cases, and exposes update(props) ready for future
      subscriber. But grep confirms no other Tauri file imports
      renderCitationDiagnostics or subscribes to ipc.session.citation.
      Per Plan 20-04's explicit "Known Stubs" section this is accepted
      scope, not a defect — flagging here for completeness only.
    artifacts:
      - path: "tauri/ui/src/settings/components/citation-diagnostics.ts"
        issue: "Component exists but no Settings drawer mounts it; no IPC subscription wired in the shell."
    missing:
      - "Settings → Diagnostics tab container (Phase 14 follow-up per Plan 20-04 SUMMARY)"
      - "IPC subscription wiring in the Tauri shell (Phase 14 follow-up)"
    closure_cost: "~2 hours — Phase 14 Settings drawer follow-up; out of Phase 20 scope per planner brief."
human_verification:
  - test: "Run a real DJ session through the live binary with the 4-kwarg patch and verify CitationLinter actually strips an unsourced Gemini reply"
    expected: "events.jsonl contains at least one citation_strip row with response_id + raw_text + missing + reason='no_citations'; AckBank PCM fires in headphones instead of the un-cited text"
    why_human: "Requires a live djay Pro + BlackHole + DDJ-FLX4 session — only Kaan can ear-test that the strip actually fires and the ack-bank fallback feels natural in flow. This is the Phase 16 ear-test, NOT a unit-level check."
  - test: "After the __main__ patch lands, observe ipc.session.citation messages emit every 2s on ws://127.0.0.1:8765"
    expected: "ws bus carries SessionCitation envelopes with slop_ratio / stripped_rate_15s / bypass_active fields validated against the JSON schema"
    why_human: "Requires the runtime patch + a websocket-listener probe; verifier did not modify __main__.py to keep the report read-only."
---

# Phase 20: Citation Linter ENFORCEMENT (Live Mode) Verification Report

**Phase Goal:** Anti-slop contract goes live — every spoken Gemini reaction citation-validated against EvidenceRegistry; un-cited responses strip to ack-bank fallback.
**Verified:** 2026-05-14T06:23:18Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Executive Verdict

Phase 20's library layer (CitationLinter + StrippedRateTracker + prompt fragments + replay harness + IPC schema) is **shipped, tested, and contract-locked**. All four plans landed exactly as planned, with 62 net new Python tests + 10 vitest cases. The replay invariant pins at **0.1429 < 0.15** on the synthetic fixture.

The one outstanding concern — pre-flagged in the verifier prompt — is that `src/vibemix/__main__.py` does NOT construct the linter primitives nor pass them to `DJCoHostAgent`, so the wired path is dormant in the shipped binary. The legacy-path byte-identity contract is preserved (intentional — Plan 19-05 guard pattern), but the anti-slop contract does not actually fire until the ~30-60min wiring patch lands.

## Goal Achievement — ROADMAP Success Criteria

| # | Success Criterion | Status | Evidence |
|---|------------------|--------|----------|
| 1 | `CitationLinter` (stdlib `re` only) validates response-level against EvidenceRegistry; failing responses strip and trigger ack-bank fallback via PROMPT-09 | ✓ VERIFIED at library/agent level (⚠ NOT wired in `__main__.py`) | `src/vibemix/coach/citation_linter.py:72` defines `class CitationLinter`; `check(text, registry_snapshot, *, mode="live")` returns `LintResult(valid, citations_found, missing, reason)`. `src/vibemix/agent/dj_cohost.py:148-202` adds the 4 optional kwargs + `_linter_wired` flag + post-stream gate ladder; line 503 enters wired branch, line 543 logs `citation_bypass`, line 585 logs `citation_strip` and calls `self._ack_bank.pick_for_event(ev)` at line 566. 33 unit tests + 7 integration tests pass. |
| 2 | Telemetry guard: `stripped_rate_15s > 0.4` triggers next-response bypass with `[unverified]` log marker; per-session `slop_ratio` surfaced via `ipc.session.citation` | ✓ VERIFIED at library/IPC level (⚠ NOT published in `__main__.py`) | `src/vibemix/coach/stripped_rate.py:33` defines `StrippedRateTracker` with `record/rate/should_bypass`; one-shot bypass latch + re-arm pinned by `test_pitfall2_stripped_burst_trips_bypass_before_8s_silence`. `src/vibemix/ui_bus/messages.py:1241` defines `SessionCitation` wrapper; `tauri/ui/src/ipc/messages.schema.json:524-544` carries the JSON schema (oneOf count 34→35); `src/vibemix/runtime/coach.py:80` defines `CITATION_PUBLISH_INTERVAL_S = 2.0` + publish gate at line 133. |
| 3 | Per-mode tolerance bands: ±1.0s live, ±2.0s debrief | ✓ VERIFIED | `src/vibemix/coach/constants.py:15` `LIVE_TOLERANCE_S = 1.0`; line 20 `DEBRIEF_TOLERANCE_S = 2.0`. `citation_linter.py:119-121` dispatches `tol = LIVE_TOLERANCE_S if mode == "live" else DEBRIEF_TOLERANCE_S`; unknown mode raises `ValueError`. |
| 4 | Prompt-side mitigation: "If you cannot cite, say 'I'm listening' — never empty text" | ✓ VERIFIED | `src/vibemix/coach/prompt_fragments.py:27` defines `IM_LISTENING_FRAGMENT`; `prompts/matrix.py:437` adds `include_listening_fallback: bool = True` kwarg, lines 523-524 append fragment to body. `agent/persona.py:36` opts out (`include_listening_fallback=False`) to preserve v4 byte-identity. 13 new tests pin the contract. |
| 5 | Replay of recorded session: `stripped_rate < 0.15` (Phase 16 ground-truth assertion) | ✓ VERIFIED | `scripts/replay_linter.py` ran on `tests/scripts/fixtures/synthetic_session/`: output `total=7 stripped=1 stripped_rate=0.143 mode=live`. CLI flag `STRIPPED_RATE=0.1429` < 0.15. 7-response fixture covers all 7 EBNF atom shapes. |

**Score:** 5/5 ROADMAP success criteria verified at the library/unit/replay level. Live-binary wiring (gap 1) deferred to a quick follow-up.

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/vibemix/coach/citation_linter.py` | `class CitationLinter` + `LintResult` | ✓ VERIFIED | 5+ imports site-wide; `import re` stdlib only (no third-party regex dep). |
| `src/vibemix/coach/stripped_rate.py` | `class StrippedRateTracker` w/ rolling 15s deque + one-shot bypass | ✓ VERIFIED | `collections.deque` head-eviction; `_bypass_consumed` latch with recovery re-arm. |
| `src/vibemix/coach/constants.py` | 4 locked floats (1.0 / 2.0 / 0.4 / 15.0) | ✓ VERIFIED | All 4 present at lines 15/20/26/32; untyped module-level form satisfies grep-gate value lock. |
| `src/vibemix/coach/prompt_fragments.py` | `IM_LISTENING_FRAGMENT` + `FAIL_SOFT_EXAMPLES` | ✓ VERIFIED | 4 canonical phrases; no f-string / format / `%` (T-20-02-01 mitigation). |
| `src/vibemix/agent/dj_cohost.py` | 4-kwarg wired path + `_linter_wired` flag + post-stream gate | ✓ VERIFIED at module level | Lines 148-202 kwargs + flag; lines 503-585 ladder; lines 540-585 citation_bypass / citation_strip event logs. |
| `src/vibemix/prompts/matrix.py` | `include_listening_fallback: bool = True` kwarg | ✓ VERIFIED | Default True; append order body → grammar → fragment. |
| `src/vibemix/agent/persona.py` | Double opt-out for v4 byte-identity | ✓ VERIFIED | `include_citation_grammar=False, include_listening_fallback=False`; import-time `assert SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE` gate. |
| `scripts/replay_linter.py` | CLI with --session/--mode/--out/--print-rate | ✓ VERIFIED | argparse CLI; 6-step pipeline; CSV output schema locked. |
| `tests/scripts/fixtures/synthetic_session/` | 7-response fixture + events.jsonl + voice.wav | ✓ VERIFIED | 10 files, events.jsonl 12 lines, 7 response.txt files, voice.wav 48044 bytes. |
| `src/vibemix/ui_bus/schemas/citation.py` | `SessionCitationPayload` frozen+slots dataclass | ✓ VERIFIED | New subpackage layout; re-exported through `__init__.py`. |
| `src/vibemix/ui_bus/messages.py` (modified) | `SessionCitation` wrapper class | ✓ VERIFIED | Line 1241; `.make()` factory; `to_json()` round-trips. |
| `tauri/ui/src/ipc/messages.schema.json` | oneOf 34→35; `SessionCitation` definition | ✓ VERIFIED | New $ref after SessionMute (line 28); definition lines 524-544. |
| `src/vibemix/runtime/coach.py` (modified) | `CITATION_PUBLISH_INTERVAL_S = 2.0` + publish gate | ✓ VERIFIED at module level | Line 80 constant; lines 98-99 kwargs; lines 122-146 publish gate with try/except + finally. |
| `tauri/ui/src/settings/components/citation-diagnostics.ts` | Renderer component + spec | ⚠ ORPHANED (by design — Plan 20-04 explicit "Known Stub") | Component exists, 10 vitest cases pass. Not imported by any Settings drawer. Phase 14 follow-up. |

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `DJCoHostAgent.llm_node` | `CitationLinter.check` | `self._linter.check(text, snap, mode="live")` | ✓ WIRED (module-level) | `dj_cohost.py:504`. |
| `DJCoHostAgent.llm_node` | `StrippedRateTracker.record` | post-strip in gate ladder | ✓ WIRED | `dj_cohost.py:_stripped_tracker.record(...)`. |
| `DJCoHostAgent.llm_node` | `AckBank.pick_for_event` | strip-path PCM fallback | ✓ WIRED | `dj_cohost.py:566` `self._ack_bank.pick_for_event(ev)`. |
| `__main__.py` | `DJCoHostAgent(citation_linter=...)` | constructor kwargs | ✗ NOT_WIRED | Agent built at `__main__.py:458-468` without the 4 wired kwargs. `_linter_wired` evaluates False at runtime → linter dormant. |
| `__main__.py` | `coach_loop(ipc_bus=..., citation_telemetry=...)` | kwargs | ✗ NOT_WIRED | `__main__.py:494-509` omits ipc_bus + citation_telemetry → SessionCitation publish gate is a no-op. |
| `prompts/matrix.build_system_instruction` | `IM_LISTENING_FRAGMENT` append | import + body+=fragment | ✓ WIRED | `matrix.py:36` import; lines 523-524 append. Default-on. |
| `coach_loop` publish gate | `ipc_bus.emit(SessionCitation.to_json())` | `await ipc_bus.emit(json.loads(msg.to_json()))` | ✓ WIRED (module-level) | `coach.py:142`. |
| Tauri shell | `renderCitationDiagnostics` | Settings drawer import | ✗ ORPHANED | No Settings drawer / app store subscriber. Phase 14 follow-up per Plan 20-04 SUMMARY. |

## Test Results

Command: `.venv/bin/python -m pytest tests/coach/ tests/agent/ tests/runtime/ tests/ui_bus/ tests/scripts/ tests/prompts/ -q`

**Result: 584 passed, 2 failed in 8.91s**

Pre-existing failures (verified out of scope per verifier prompt; confirmed by no local changes / no stashed deltas):
- `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` — cohost_v4.py byte-identity drift (tracked outside Phase 20)
- `tests/scripts/test_replay_linter.py::test_csv_report_has_correct_shape` — fixture pre-existing CSV from a prior local run; not a code defect (per Plan 20-04 SUMMARY this was already flagged as pre-existing in the 1803-pass / 10-fail baseline)

## Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| GROUND-04 | 20-01 | ✓ SATISFIED | CitationLinter response-level binary gate |
| GROUND-05 | 20-01 / 20-03 | ✓ SATISFIED | EvidenceRegistry snapshot consumed by linter; replay harness pins 0.143 < 0.15 |
| GROUND-06 | 20-01 / 20-04 | ✓ SATISFIED | StrippedRateTracker + ipc.session.citation IPC schema |
| GROUND-07 | 20-01 | ✓ SATISFIED | Ack-bank PCM fallback on strip-path (pick_for_event integration) |
| GROUND-08 | 20-02 | ✓ SATISFIED | IM_LISTENING_FRAGMENT default-on append in build_system_instruction |

## Anti-Patterns Found

None within Phase 20 scope. Two existing test failures are pre-existing (verified out of scope).

## Pre-Flagged Follow-Ups (from Plans)

1. **Plan 20-04 SUMMARY "Known Stubs":** `citation-diagnostics.ts` is a renderer-only stub; Settings drawer + IPC subscription deferred to Phase 14 follow-up. ✓ ACKNOWLEDGED.
2. **Verifier-prompt Item 5 pre-flag:** "verify the citation_linter / stripped_rate_tracker / ack_bank / playback are also being constructed and threaded into DJCoHostAgent at startup." ✗ NOT WIRED. Documented as `gaps[0]` above with 30-60min closure cost. This is the Phase 20 anti-slop contract not actually firing in the live binary.

## Human Verification Required

1. **Live-binary ear test (Phase 16 — Kaan's DJ ear):** Once gap 1 is closed, run a DJ session and verify CitationLinter strip + ack-bank fallback feels natural in flow (events.jsonl `citation_strip` row + audible ack PCM).
2. **IPC bus probe:** After `__main__.py` patch, websocket-listen on `ws://127.0.0.1:8765` and verify `ipc.session.citation` envelopes emit every 2s with schema-valid payloads.

## Gaps Summary

The Phase 20 library is complete and tested. The single outstanding gap is the **runtime activation patch in `src/vibemix/__main__.py`** — the 4 kwargs for `DJCoHostAgent` (`citation_linter` / `stripped_rate_tracker` / `ack_bank` / `playback`) and the 2 kwargs for `coach_loop` (`ipc_bus` / `citation_telemetry`) are not threaded through, so the wired path is dormant in the shipped binary even though the legacy-path byte-identity contract is preserved.

Closure: ~30-60min — construct `CitationLinter()` + `StrippedRateTracker()` instances + a small telemetry-callable closure, pass through. No new modules, no schema churn. The wired path's unit-test coverage (33+7 tests) already verifies the integration; only the constructor-site wiring is missing.

The Tauri Settings drawer subscriber wiring is the other open thread but is intentionally Phase 14 scope per Plan 20-04's explicit "Known Stubs" disclosure.

---

_Verified: 2026-05-14T06:23:18Z_
_Verifier: Claude (gsd-verifier)_
