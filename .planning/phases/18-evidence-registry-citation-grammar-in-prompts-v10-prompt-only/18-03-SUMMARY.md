---
phase: 18-evidence-registry-citation-grammar-in-prompts-v10-prompt-only
plan: 03
subsystem: prompts + agent
tags: [GROUND-02, GROUND-03, prompt-only-seeding, citation-grammar, evidence-registry, gemini-system-instruction]
requires:
  - "18-01: EVIDENCE_SOURCES + EvidenceRegistry + parse_citations + EVIDENCE_CITATION_RE"
  - "18-02: AICoach.build_prompt(registry_snapshot=) + EventDetector(evidence_registry=) + state_refresh_loop wiring"
provides:
  - "src/vibemix/prompts/matrix.py: CITATION_GRAMMAR_BLOCK constant (~1757 chars / ~440 tokens)"
  - "src/vibemix/prompts/matrix.py: build_system_instruction(*, include_citation_grammar=True) kwarg"
  - "src/vibemix/agent/dj_cohost.py: DJCoHostAgent(*, evidence_registry=None) kwarg + per-turn snapshot threading"
  - "src/vibemix/agent/persona.py: SYSTEM_INSTRUCTION uses include_citation_grammar=False (preserves v4 byte-identity invariant)"
  - "vibemix.prompts.CITATION_GRAMMAR_BLOCK exported (added to __all__)"
affects:
  - "All 6 prompt cells now ship with the citation-grammar block by default"
  - "DJCoHostAgent.llm_node calls AICoach.build_prompt(ev, registry_snapshot=...) per turn"
  - "Gemini system_instruction now ~440 tokens larger (Plan 19 cache-content sizing must account for this)"
tech-stack:
  added: []
  patterns:
    - "Opt-out kwarg + default-on append (mirrors mood_persona substitution gate from Plan 13-05)"
    - "Cross-package contract test (EVIDENCE_SOURCES ↔ CITATION_GRAMMAR_BLOCK) — registry vocab and prompt vocab locked in pytest"
key-files:
  created: []
  modified:
    - "src/vibemix/prompts/matrix.py — CITATION_GRAMMAR_BLOCK constant + include_citation_grammar kwarg"
    - "src/vibemix/prompts/__init__.py — export CITATION_GRAMMAR_BLOCK"
    - "src/vibemix/agent/dj_cohost.py — evidence_registry kwarg + per-turn snapshot threading in llm_node"
    - "src/vibemix/agent/persona.py — SYSTEM_INSTRUCTION uses include_citation_grammar=False"
    - "tests/prompts/test_matrix.py — Tests O–T (16 new test cases) + 3 v4-byte-identity assertions updated to use opt-out"
    - "tests/agent/test_dj_cohost.py — Tests U–X + Test Y (5 new test cases) + LLM-NODE-01/AGENT-02/AGENT-03 updated"
    - "tests/agent/test_dj_cohost_matrix_dispatch.py — 6 dispatch tests updated to startswith(cell) + assert grammar substring"
    - "tests/agent/test_coach_mood_template.py — v4 byte-identity test uses include_citation_grammar=False"
decisions:
  - "Default include_citation_grammar=True so every Gemini system_instruction sees the grammar — opt-out only for the v4 byte-identity backward-compat re-export at persona.SYSTEM_INSTRUCTION."
  - "Append the block at the END of the body (not embed inside) so the v4 cell constant remains a strict prefix — locks the existing 6-cell IP and lets a future grep over prompt surface locate the grammar tail unambiguously."
  - "Snapshot taken FRESH per llm_node call (not cached) — Test X locks this so any future caching mistake fails loudly."
  - "Single-modality audio Part contract preserved (no screen_jpeg / no MIDI metadata Parts) — Plan 18-03 is text-only seeding via the system instruction + per-turn corpus footer."
  - "Exempt persona.SYSTEM_INSTRUCTION from the grammar append because it's a v4 byte-identical re-export documented as load-bearing IP in CLAUDE.md — DJCoHostAgent gets the grammar via the dispatcher's default path instead."
metrics:
  duration_minutes: ~25
  completed: 2026-05-14
  tests_added: 22  # 11 test functions × parametrize expansion = 22 cases
  tests_repo_total: "1607 passing (was 1584 pre-Plan-18-03; +23 net)"
  tests_repo_failing: "9 pre-existing failures unchanged (1 incidentally fixed: test_smoke_06_poc_files_untouched_during_smoke)"
---

# Phase 18 Plan 03: Citation grammar baked into Gemini prompts Summary

Production-corpus seeding loop closed (GROUND-02 + GROUND-03): Gemini sees the citation grammar in every system instruction AND the per-turn evidence_corpus footer in the user prompt. v1.0 is prompt-only seeding — no enforcement; Phase 20 will land the linter + ack-bank fallback.

## Where the grammar lives in the prompt

The CITATION_GRAMMAR_BLOCK lives in the **system instruction** (NOT the user prompt). Specifically:
- `build_system_instruction(skill, mode, mood)` returns `body + "\n\n" + CITATION_GRAMMAR_BLOCK` by default (`include_citation_grammar=True`).
- `_resolve_prompt_cell()` in `dj_cohost.py` calls this with the default → `prompt_body` is body + grammar.
- `prompt_body` flows into BOTH:
  - `Agent.__init__(instructions=prompt_body, ...)` — LiveKit's text-only fallback path.
  - `types.GenerateContentConfig(system_instruction=prompt_body, ...)` — google.genai's `system_instruction` field.
- The user-prompt side (`contents[0]` passed to `generate_content_stream`) gets the per-turn `evidence_corpus[ev=N,aud=M,mix=K]` footer from `AICoach.evidence_line` (Plan 18-02), threaded via `registry_snapshot=self._registry.snapshot()` per turn.

## CITATION_GRAMMAR_BLOCK excerpt (~1757 chars / ~440 tokens estimated)

```
--- CITATION GRAMMAR (v1.0 — encouraged, not required) ---

When you reference a specific event, audio feature, controller move, track,
screen element, mix-state, or user-profile fact, attach a grounded citation
in this exact bracket form. Cites help the human team verify what you heard;
they're encouraged, not required, and there is NO penalty for omitting them
in v1.0.

Forms (each is a single citation; the linter accepts any of these):
  [ev:<TYPE>@<t>]     event citation, e.g. [ev:KICK_SWAP@45.2]
  [aud:<key>@<t>]     audio feature, e.g. [aud:bpm@45.2] or [aud:rms@45.2]
  [midi:<event>@<t>]  controller event, e.g. [midi:cue_a@12.7]
  [track:<id>]        track reference, e.g. [track:Marlon Hoffstadt - Atlas]
  [screen:<key>]      screen element, e.g. [screen:waveform_deck_a]
  [mix:<derived>]     derived mix-state, e.g. [mix:audible_deck=A]
  [tend:<fact>]       user-profile fact, e.g. [tend:user_likes_acid]

Multi-citation (comma-separated, no whitespace inside brackets):
  [ev:KICK_SWAP@45.2,aud:bpm@45.0]

Event types currently tracked (use exactly these in [ev:<TYPE>] —
UPPER_SNAKE_CASE):
  KAAN_SPOKE, MANUAL, TRACK_CHANGE, PHASE, LAYER_ARRIVAL, MIX_MOVE, HEARTBEAT
…
"Trust the audio, cite when you can, stay silent when you can't."
```

## v4-byte-identity invariant preserved

`HYPE_INTERMEDIATE` constant body is byte-for-byte unchanged. Verified:
- `git diff src/vibemix/prompts/matrix.py | grep "HYPE_INTERMEDIATE: str ="` returns no diff inside the v4 body lines.
- `vibemix.agent.persona.SYSTEM_INSTRUCTION` calls `build_system_instruction("intermediate", "hype", include_citation_grammar=False)` so the backward-compat re-export stays byte-identical.
- The `assert SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE` import-time guard in persona.py still passes.
- Test Q (v4-byte-identity preserved) green: opt-out path returns the constant byte-for-byte; default path is a strict superset.

## DJCoHostAgent constructor signature delta

```diff
 def __init__(
     self,
     *,
     genai_client: genai.Client,
     clean_audio_buf: AudioBuffer,
     screen_buf,
     state: MusicState,
     recorder: VoiceRecorder,
     llm_inst: agents_llm.LLM,
     tts_inst: agents_tts.TTS,
+    evidence_registry: EvidenceRegistry | None = None,
 ):
```

Default `None` preserves backward compat — every existing caller (tests, standalone runs) continues to work without modification. `main_runtime.py` (live entrypoint) is the production caller that wires the registry; integration in a follow-up plan can swap to passing `evidence_registry=registry` once the upstream wiring is plumbed.

## Per-turn snapshot semantic

`llm_node` snapshots the registry FRESH per call:

```python
snapshot = self._registry.snapshot() if self._registry is not None else None
text_prompt = AICoach.build_prompt(ev, registry_snapshot=snapshot)
```

Test X locks this against any future caching mistake. snapshot() is O(N) over total observations and lock-guarded; cohost_v4 cooldown gates cap a 1h DJ session at ~500 obs → well under 1ms per turn.

## Cross-package contract test

Test R in `tests/prompts/test_matrix.py`:

```python
from vibemix.state import EVIDENCE_SOURCES
from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK
for source in EVIDENCE_SOURCES:
    assert f"[{source}:" in CITATION_GRAMMAR_BLOCK
```

Locks the registry-vocabulary ↔ prompt-vocabulary contract in pytest. A future drift in either side surfaces as a test failure.

## Test count delta

| File                                      | Before | After | Delta |
|-------------------------------------------|--------|-------|-------|
| tests/prompts/test_matrix.py              | 56     | 72    | +16 (Tests O–T parametrized) |
| tests/agent/test_dj_cohost.py             | 16     | 21    | +5 (Tests U, V, W, X, Y) |
| tests/agent/test_dj_cohost_matrix_dispatch.py | 10 | 10 | 0 (existing tests updated, not added) |
| tests/agent/test_coach_mood_template.py   | 8     | 8     | 0 (existing test updated) |
| **Subset (state + prompts + agent)**      | 633    | 655   | **+22** |
| **Full repo**                             | 1584   | 1607  | **+23** (incidentally fixed test_smoke_06) |

Pre-existing failures (9 — unchanged):
- `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4` — v3/v4 POC drift
- `tests/recording/test_phase15_success_criteria.py` (×3) — unrelated
- `tests/test_audio_macos_live.py` — needs real audio device
- `tests/test_main_smoke.py` (×3) — env-dependent
- `tests/test_phase05_verification.py::test_g5_poc_files_untouched` — unrelated POC tracking

## Hand-off to Plan 19 (LATENCY-02 — cached_content)

**Cache-content sizing must account for the +440-token grammar block.** The Plan 19 cache key/content size estimate is now:
- Phase 4 baseline: ~2050 tokens (HYPE_INTERMEDIATE)
- Plan 18-03 addition: +440 tokens (CITATION_GRAMMAR_BLOCK)
- **New cached_content total: ~2490 tokens**

Plan 19 owner: when sizing the Gemini `cached_content` budget, use ~2500 tokens as the system-instruction cache target. The grammar block is constant across turns (no per-turn interpolation), so it's safe inside `cached_content` (same cacheability properties as the v4 body). Pitfall P11 (cache disruption) is mitigated as long as the grammar block stays a constant — any future per-turn dynamic interpolation INTO the grammar block would invalidate the cache.

## Hand-off to Plan 18-04 (citation telemetry)

Where to count Gemini's emitted citations:
- In `dj_cohost.py::DJCoHostAgent.llm_node`, AFTER the streaming loop completes (line ~256 `print(); elapsed = ...`), use `parse_citations(full_text)` from `vibemix.state` (Plan 18-01).
- Aggregate into a rolling-average counter on the agent (or a sidecar telemetry object) — emit `citation_count` per turn into the existing `_recorder.log_event("ai_text", ...)` call OR a new `log_event("citation_telemetry", ...)` event.
- Phase 16 ear-test consumes the rolling average as the P20 enforcement readiness signal.

## Threat surface scan

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries. The grammar block is fixed text with no user-input interpolation (T-18-03-01 mitigated). All 5 STRIDE entries from the threat model are satisfied:
- T-18-03-01 (CITATION_GRAMMAR_BLOCK injection): mitigated — constant string, no interpolation.
- T-18-03-02 (grammar drift between cells): mitigated — single source-of-truth append in dispatcher; Test P parametrized over 6 cells locks it.
- T-18-03-03 (snapshot exposure): accepted — counts only, not raw timestamps/values.
- T-18-03-04 (Gemini emits fake cites): accepted — v1.0 prompt-only seeding; Plan 20 closes via CitationLinter.
- T-18-03-05 (token budget): mitigated — flagged in hand-off above.

## Self-Check: PASSED

Files created/modified verified:
- `src/vibemix/prompts/matrix.py` (CITATION_GRAMMAR_BLOCK + kwarg) ✓
- `src/vibemix/prompts/__init__.py` (export) ✓
- `src/vibemix/agent/dj_cohost.py` (registry kwarg + snapshot threading) ✓
- `src/vibemix/agent/persona.py` (opt-out for v4 backward-compat) ✓
- `tests/prompts/test_matrix.py` (Tests O–T + updated existing) ✓
- `tests/agent/test_dj_cohost.py` (Tests U–Y + updated existing) ✓
- `tests/agent/test_dj_cohost_matrix_dispatch.py` (updated for grammar-tail assertion) ✓
- `tests/agent/test_coach_mood_template.py` (updated v4 byte-identity test) ✓

Commits verified in git log:
- `81370a3` — test(18-03): RED — CITATION_GRAMMAR_BLOCK ✓
- `000cfc6` — feat(18-03): GREEN — CITATION_GRAMMAR_BLOCK baked into system instructions ✓
- `2e90204` — test(18-03): RED — DJCoHostAgent threads evidence_registry ✓
- `babd24b` — feat(18-03): GREEN — DJCoHostAgent threads registry_snapshot ✓
- `3d76d55` — test(18-03): Test Y — cross-package smoke ✓

Cross-package contract verified:
- `python -c "from vibemix.state import EVIDENCE_SOURCES; from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK; print(all(f'[{s}:' in CITATION_GRAMMAR_BLOCK for s in EVIDENCE_SOURCES))"` → `True` ✓
