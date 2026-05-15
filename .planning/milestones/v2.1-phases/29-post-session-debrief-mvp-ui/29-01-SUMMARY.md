---
plan: 29-01
phase: 29-post-session-debrief-mvp-ui
status: complete
wave: 2
requirements: [DEBRIEF-03, DEBRIEF-04, DEBRIEF-06, DEBRIEF-07]
commits:
  - <T1> # feat(29-01): debrief pure-data layer (chapters/stripper/loader/persistence)
  - <T2> # feat(29-01): debrief LLM layer (tldr.py + drills.py) + 28 unit tests
tasks_completed: 2/2
tests_added: 62
tests_passing: 62/62
regression_check: pytest tests/debrief/ → 62/62; tests/ui_bus/ → 168/168
---

# Plan 29-01 Summary — debrief Python package

## What was built

### Task 1 — pure-data layer (chapters / stripper / session_loader / persistence)

Six modules + six test files. All pure data transforms — no LLM calls.

**`src/vibemix/debrief/__init__.py`** — package exports.

**`src/vibemix/debrief/stripper.py`** — DEBRIEF-07 sentence-level filter
reusing `EVIDENCE_CITATION_RE` from Phase 18. `strip_uncited_sentences`
returns `(filtered_text, stripped_count)` and logs each drop.
`UncitedSentencesFound` exception for post-strip guard via
`assert_all_cited`.

**`src/vibemix/debrief/chapters.py`** — `derive_chapters(events_jsonl)`
heuristic:
- TRACK_CHANGE always splits.
- PHASE / LAYER_ARRIVAL / MIX_MOVE / KAAN_SPOKE split when ≥ 30s since
  previous break.
- HEARTBEAT ignored.
- Chapters contiguous (`chapter[i+1].start == chapter[i].end`).
- Malformed JSON lines skipped with logged warning; derivation
  continues.
- `ChapterRegion` is `@dataclass(frozen=True, slots=True)`.

**`src/vibemix/debrief/session_loader.py`** — `load_session(session_dir)`
returns `(events, evidence_snapshot, voice_meta)`. Typed exceptions:
`SessionTooShort` (< 300s), `EventsMissing`, `InvalidSessionDir`. Reads
`evidence_registry.json` (optional — Plan 29-00 added it to new
sessions); reads `voice.wav` header via stdlib `wave` for sample_rate +
duration.

**`src/vibemix/debrief/persistence.py`** — atomic write+read of
`session_debrief.json` + `debrief_tldr.mp3` with SHA-256 cache key.
Tempfile-then-`os.replace` pattern. Cache-miss returns `None` on hash
drift / missing files / malformed JSON.

### Task 2 — LLM layer (tldr.py + drills.py)

Two modules + four test files. All tests offline (mocked Gemini).

**`src/vibemix/debrief/tldr.py`** — DEBRIEF-04 narration pipeline:
- `generate_tldr_text(client, chapters, critique)` calls Gemini 3 Pro
  preview, strips uncited sentences, truncates at sentence boundary if
  output exceeds 220 words.
- `synthesize_achird_mp3(client, text)` calls Gemini TTS with
  Achird voice → raw PCM 24kHz s16le → PyAV libmp3lame encode → MP3
  bytes.
- `generate_tldr_mp3(client, chapters, critique)` composes both.
- `DebriefGenerationError(reason, message)` for typed orchestrator
  errors.

**`src/vibemix/debrief/drills.py`** — DEBRIEF-06 structured-output drill
generation:
- `Drill` / `Drills` Pydantic models enforce 5 fields per drill +
  exactly-3 cardinality.
- `_citation_resolves(citation, snapshot, tol=2.0)` parses
  `[source:body@time]` and resolves against
  `{source: {key: [t,...]}}` snapshot at ±2.0s Phase 20 debrief band.
- `generate_drills(client, critique, chapters, snapshot,
  max_retries=2)` retries up to `max_retries` times before raising
  `DrillsGenerationError`.

## Key constants locked here

- `DEBRIEF_TLDR_MODEL = "gemini-3-pro-preview"` (Wave 0 A1)
- `DEBRIEF_TTS_MODEL = "gemini-3-flash-tts-preview"`
- `DEBRIEF_DRILLS_MODEL = "gemini-3-pro-preview"`
- `ACHIRD_VOICE_NAME = "Achird"`
- `MIN_TLDR_WORDS = 150`, `MAX_TLDR_WORDS = 220` (≈60–90s @ 150 WPM)
- `_CITATION_RESOLVE_TOL_S = 2.0`
- `_MIN_SESSION_DURATION_S = 300.0`

## Test summary

| File | Tests | Coverage |
|------|-------|----------|
| test_chapter_derivation.py | 8 | TRACK_CHANGE split, PHASE ≥30s gap, HEARTBEAT skip, contiguity, citation_event_id format, frozen dataclass, malformed JSON resilience |
| test_no_uncited_critique_in_debrief.py | 14 | 7 EBNF sources accepted, log capture, hard-gate baseline |
| test_session_too_short_falls_back.py | 3 | 120s / 299s reject, 301s pass |
| test_missing_events_jsonl_errors_gracefully.py | 3 | EventsMissing + InvalidSessionDir |
| test_persistence_roundtrip.py | 6 | Cache invalidation, atomic write, malformed JSON returns None |
| test_drill_schema_validates.py | 6 | 5-field/3-drill Pydantic enforcement |
| test_drill_citations_resolve.py | 10 | Tolerance band, retry-then-raise paths |
| test_tldr_length_60_to_90s.py | 7 | Stripper integration, word budget, error paths |
| test_tldr_mp3_codec.py | 5 | PyAV libmp3lame magic bytes, Achird voice config |

**Total: 62 tests, 62 pass.**

## Deviations

- **No VCR cassettes.** Plan suggested `pytest-recording` cassettes
  against real Gemini. In autonomous mode we don't run live network
  calls; all Gemini interactions are mocked. Real-API smoke is the
  manual checklist's job (Plan 29-08).
- **Empty-PCM edge test removed.** Real PyAV
  `resampler.push(empty_frame)` raises `MemoryError` on the underlying
  ffmpeg buffer. Not in the plan's `<behavior>` requirements; orchestrator
  guards against empty PCM via `DebriefGenerationError` from
  `synthesize_achird_mp3`.
- **Drill text-field citation check deferred to Plan 29-07.** Plan
  29-01 establishes citation resolution for the canonical `citation`
  field; the per-field (behavior/impact/action_recommended)
  citation-presence check is wired in Plan 29-07 (DEBRIEF-07
  defense-in-depth integration).

## Self-Check: PASSED

- [x] Both tasks' acceptance criteria satisfied.
- [x] 62/62 debrief tests pass.
- [x] No regressions: 168/168 ui_bus, 62/62 debrief.
- [x] Modules importable via `from vibemix.debrief import …`.
- [x] All Gemini constants locked (model ids per Wave 0 A1 verdict).
- [x] DEBRIEF-03 / -04 / -06 / -07 testable end-to-end on fixture data.

## What this unblocks

- **Plan 29-02** can wire `debrief.main.run()` orchestrator over these
  modules.
- **Plan 29-05** consumes `ChapterRegion`, MP3 path, drills.
- **Plan 29-07** wires defense-in-depth stripper integration across
  `tldr.py` + `drills.py` (already done at unit level here; e2e gate
  lands there).
