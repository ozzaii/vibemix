# Phase 68 — Plan Index (planning-complete 2026-05-23)

**Phase:** 68 — All Devices Ready
**Mode:** standard · `gsd-autonomous fully`
**Plans:** 5 plans in 5 waves (strict left-to-right dependency)
**REQ coverage:** DEV-01..05 (all 5 mapped to at least one plan)

## Wave structure

| Wave | Plan | Objective | REQ | Autonomous |
|------|------|-----------|-----|------------|
| 0 | 68P01 | Atomic catalog reconciliation: delete `src/vibemix/midi/controllers/` + `map_loader.py` + `schema.json` + 2 orphan tests; rewrite README controller grid + a11y script + test_readme_shape + KAAN-ACTION §LAUNCH-04 + docs/midi-mapping.md + .planning/PROJECT.md; rotate 10 SVG placeholders to new slugs; add docs/contributing/midi-catalog.md migration note. ONE commit. | DEV-02 | yes |
| 1 | 68P02 | 10-row parametrized contract test (`tests/midi/test_profile_contracts.py`) + 10-row synthetic-MIDI smoke (`tests/midi/test_profile_smokes.py`) covering all 10 bundled profiles. Uses `load_profile()` (NOT jsonschema) + `SimpleNamespace`-shaped `mido.Message` factory. | DEV-01 | yes |
| 2 | 68P03 | 3-profile hot-plug matrix (`tests/integration/test_hotplug_matrix.py` — FLX4 + DDJ-400 + Inpulse-500) + 4-fixture audio backend matrix (`tests/integration/test_audio_backends.py` — BlackHole 2ch + 16ch + WASAPI loopback + no-loopback fallback). All `@pytest.mark.integration`. v4.0 P53 callback path read-only. | DEV-03, DEV-04 | yes |
| 3 | 68P04 | Contributor recipe: `scripts/discover_midi_port.py` (≤30-line helper), `docs/contributing/_template.json` (clean copy-target — outside profiles/ to avoid loader pollution), `docs/contributing/add-a-controller.md` (≤200-line 4-step recipe + PR checklist). | DEV-05 | yes |
| 4 | 68P05 | Append §V7-LIVE-07..10 KAAN-ACTION clusters: §V7-LIVE-07 (controller-recipe <30-min smoke), §V7-LIVE-08 (macOS BlackHole live), §V7-LIVE-09 (Windows WASAPI live), §V7-LIVE-10 (live FLX4 hot-plug ear). Mirrors §V7-LIVE-01..06 shape. | DEV-03, DEV-04, DEV-05 | yes |

## Dependency spine

```
68P01 (Wave 0 — catalog reconciliation)
   ↓
68P02 (Wave 1 — contract + smoke tests; parametrize over the canonical 10)
   ↓
68P03 (Wave 2 — hot-plug + audio backend integration matrices)
   ↓
68P04 (Wave 3 — contributor recipe references P02 test files)
   ↓
68P05 (Wave 4 — §V7-LIVE clusters reference P02/P03/P04 artifacts)
```

## Wave-by-REQ coverage

| REQ | Wave coverage | Status post-phase |
|-----|---------------|-------------------|
| DEV-01 | Wave 1 (68P02) | Engineering-side closed (10 contract + 10 smoke GREEN) |
| DEV-02 | Wave 0 (68P01) | Closed (atomic reconciliation; single canonical catalog) |
| DEV-03 | Wave 2 (68P03 T1) + Wave 4 (68P05 §V7-LIVE-10) | Engineering closed; live FLX4 ear rides Kaan's clock |
| DEV-04 | Wave 2 (68P03 T2) + Wave 4 (68P05 §V7-LIVE-08+09) | Engineering closed; live BlackHole + WASAPI ride Kaan's clock per OS |
| DEV-05 | Wave 3 (68P04) + Wave 4 (68P05 §V7-LIVE-07) | Engineering closed; <30-min smoke rides Kaan's clock |

## Anti-shallow guarantees

- Every task has `<read_first>` (the file being modified + 68-CONTEXT.md + 68-RESEARCH.md + the closest shipped analog pattern file).
- Every task has `<acceptance_criteria>` with concrete shell commands or per-row test counts.
- Every task has concrete file paths + concrete test names + concrete commands.
- Zero `src/vibemix/{coach,llm,memory,recall,decks}/` edits (verified per CONTEXT — only `src/vibemix/midi/` reconciliation).
- Zero net-new dependencies (verified against `pyproject.toml` + `uv.lock` — every dep already locked).
- Zero edits to v4.0 P53 hot-plug callback (`_midi_common.py` + `state.py::mark_disconnected`) — pinned by P03 acceptance gate.

## Cardinal invariants (zero-touch verified)

| Invariant | How held |
|-----------|----------|
| single-writer (MusicState) | No phase touches the state-refresh loop |
| citation-grounding (`audio:` / `key:` / `recall:`) | No phase touches the coach or evidence-sources |
| trust-the-audio | No phase touches the audio capture path (only its mock surface) |
| one-socket | No phase touches the ws bus |
