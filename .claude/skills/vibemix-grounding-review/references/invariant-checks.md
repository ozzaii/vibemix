# Invariant checks — commands, failure signatures, file map

All Python commands run from repo root with the venv active:

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <paths>
# equivalent:  uv run pytest -q <paths>
```

The single TypeScript invariant (#5) runs from `tauri/ui/`:

```bash
cd tauri/ui && npm test          # vitest run --reporter=dot (full ~886-test suite)
cd tauri/ui && npx vitest run tests/session/grounding-failure.spec.ts   # just #5
```

Default pytest run skips opt-in markers (`macos_audio`, `windows_only`,
`integration`, `slow`, `e2e`, `cli`, `network`, `parity`, `flaky` — see
`[tool.pytest.ini_options]` in `pyproject.toml`). None of the five invariant
gates below need a marker; they are static/unit and run by default.

Do NOT launch `uv run python -m vibemix` to verify — it binds `127.0.0.1:8765`
and collides with any running session. Every gate here is static or unit-level.

---

## Invariant #2 — Citation grounding

**Sources**
- `src/vibemix/state/evidence_registry.py` — `EvidenceRegistry` (append-only,
  `threading.Lock`-guarded), `EVIDENCE_SOURCES` frozenset (12 sources: `ev`,
  `aud`, `midi`, `track`, `screen`, `mix`, `tend`, `key`, `recall`, `exemplar`,
  `cue`, `judge`), `EVIDENCE_CITATION_RE`, `parse_citations`, `register_library`,
  `has(source, key, t, tol)`, `snapshot()`.
- `src/vibemix/coach/citation_linter.py` — `CitationLinter.check(text, snapshot,
  mode="live"|"debrief")` → frozen `LintResult(valid, citations_found, missing,
  reason)`. Response-level binary; one bad atom strips the whole turn.
  `_TIME_KEYED_SOURCES = {"ev","aud","midi"}` (need `@t` + tolerance lookup);
  the rest are existence-only. Tolerances from `coach/constants.py`
  (`LIVE_TOLERANCE_S`, `DEBRIEF_TOLERANCE_S`).
- `src/vibemix/agent/dj_cohost.py` — the chokepoint. `llm_node` runs the linter
  after the silence/slop gate; on invalid → `citation_strip` (no audio, silence
  pad if a speculative head was in flight), one-shot bypass via
  `StrippedRateTracker.should_bypass()`. `_build_citation_strip` builds the UI
  chip strip (cap 3, empty list never None, never fabricates a timestamp).
- `src/vibemix/state/coach.py` — `AICoach.build_prompt(..., registry_snapshot=)`
  bakes the citation grammar into the prompt.
- `src/vibemix/prompts/matrix.py` — `CITATION_GRAMMAR_BLOCK` (the prompt-side
  copy of the source list).

**Commands**

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
  tests/state/test_coach_anti_slop.py \
  tests/state/test_hype_anti_slop.py \
  tests/agent/test_citation_strip_emit.py \
  tests/agent/test_dj_cohost_grounding.py \
  tests/agent/test_dj_cohost_linter.py \
  tests/agent/test_citation_strip_emit.py \
  tests/state/test_evidence_registry.py \
  tests/coach/test_citation_linter.py \
  tests/coach/test_citation_zero_orphan_replay.py
```

**Key pins**
- `test_spine_unbacked_coach_citation_is_stripped` — fabricated cite → no voice.
- `test_spine_grounded_coach_citation_passes` — real cite → emits.
- `test_empty_registry_yields_empty_list` / `test_fabricated_key_citation_yields_no_chip_DECK03`
  — strip-builder never fabricates a chip for an unobserved claim.
- `test_cited_track_id_resolves_in_evidence_registry` — `register_library` seeds
  `track:<id>` at `t_session=0.0` so live `[track:<id>]` resolves.

**Failure signatures**
- `AssertionError` in `test_spine_*` → a fabricated citation reaches TTS, or a
  grounded one was wrongly stripped.
- `ImportError`/`AttributeError` after editing `evidence_registry.py` → you
  changed `EVIDENCE_SOURCES`/`parse_citations` shape; check the four lock-step
  copies below.

**THE LOCK-STEP RULE (silent-poisoning hole).** A citation source must appear in
ALL of these IN THE SAME COMMIT, or a fabricated `[src:...]` is never matched,
never stripped, and rides through un-validated:
1. `evidence_registry.py::EVIDENCE_SOURCES` (the source of truth)
2. `evidence_registry.py::_SOURCE_ALT` (regex alternation feeding
   `EVIDENCE_CITATION_RE`)
3. `evidence_registry.py` EBNF docstring (`source := ...`)
4. `prompts/matrix.py::CITATION_GRAMMAR_BLOCK`
5. `agent/dj_cohost.py::_build_citation_strip` (chip allow-list)

Intentional asymmetry: `memory/ingest.py`'s alternation stays at 8 sources —
`recall`/`exemplar`/`cue`/`judge` are narration-time, never ingest-time. Do NOT
"fix" it to 12.

A new time-keyed source also needs adding to
`citation_linter.py::_TIME_KEYED_SOURCES`; an existence-only source must stay
OUT of it.

---

## Invariant #3 — Trust the audio / no speculative phrasing

**Sources**
- `src/vibemix/prompts/negative_dict.py` — `NEGATIVE_PHRASES` (63 entries:
  16 AI tells, 16 empty hype, 8 slop framings, 23 stop-slop) + `NEGATIVE_REGEX`
  (word-boundary, case-insensitive). Seeded from the `stop-slop` skill.
- `src/vibemix/prompts/filter.py` — `filter_for_slop(text)` → `(<silence/>,
  matches)` if any phrase matches, else `(text, [])`. Whole-turn suppression,
  NOT in-place rewrite. `dj_cohost.llm_node` short-circuits TTS + logs
  `slop_suppressed`.
- `src/vibemix/state/event_detector.py` — typed events with per-type cooldowns;
  the detector refuses to fire on silence / out-of-range BPM / inside the
  presence window (the "no hallucinated event" floor).
- `src/vibemix/state/refresh.py` + `CueAnchor` — the ONLY source of phrase
  structure. `learn/` consumes it; never computes its own.

**Commands**

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
  tests/learn/test_no_speculative_phrase.py \
  tests/prompts/test_negative_dict.py \
  tests/state/test_hype_anti_slop.py \
  tests/state/test_coach_anti_slop.py \
  tests/state/test_event_detector.py
```

**Key pins**
- `tests/learn/test_no_speculative_phrase.py::test_learn_package_imports_no_phrase_guessing_primitives`
  — the AST gate. Forbidden under `src/vibemix/learn/`: `numpy.fft`,
  `scipy.signal`, `scipy.fft`, `librosa.beat`, `librosa.onset` (all three import
  syntactic forms reddened).
- `test_negative_dict_01_at_least_forty_phrases` — `len(NEGATIVE_PHRASES) >= 40`.
- `test_negative_dict_11_no_single_adverb_false_positives` — single adverbs
  ("really", "just", "actually") stay OUT (whole-turn suppression would nuke
  natural DJ speech).
- `test_empty_evidence_silent_state_does_not_fire` /
  `test_weak_evidence_out_of_range_bpm_does_not_fire` — detector floor.

**Failure signatures**
- AST gate `AssertionError` listing `path:line: import ...` → a learn module
  imports a phrase-guessing primitive. Move the math to `state/` if genuinely
  needed; the tutor must read grounded phrase data.
- `test_negative_dict_01` fail → you dropped the phrase count below 40.
- detector-floor `AssertionError` → an event fired on silence/out-of-range BPM
  (a hallucinated event the co-host would react to).

---

## Invariant #1 — Single-writer

**Sources**
- `src/vibemix/state/music_state.py` — `MusicState`, the single source of truth.
  Docstring: "written ONLY by state/refresh.py … learn/ never writes." Genre /
  phrase / mood / emotion fields are set only inside the single-writer block in
  `state_refresh_loop._tick_once`.
- `src/vibemix/state/refresh.py` — `state_refresh_loop` / `_tick_once`, the sole
  writer (writes `state.audible`, `state.rms`, `state.bands`, `state.bpm`, …).
- `src/vibemix/learn/runtime.py` — sole writer of `LearnState`.

**Commands**

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
  tests/learn/test_runtime_invariants.py \
  tests/state/test_refresh.py \
  tests/state/test_music_state.py
```

**Key pins**
- `test_learn_package_never_writes_music_state_or_controller_state` — grep gate;
  reddens on any `MusicState.<field> =` or `ControllerState.<field> =` under
  `src/vibemix/learn/`.
- `test_learn_state_writes_are_only_inside_runtime_py` — `LearnState` writes
  confined to `runtime.py`/`state.py`.

**Failure signatures**
- grep-gate `AssertionError` listing `path:line: <assignment>` → a consumer
  writes a live-deck-owned object. Make it read-only; route the write through
  the single-writer loop.

---

## Invariant #4 — One socket

**Sources**
- `src/vibemix/audio/constants.py` — `WS_HOST = "127.0.0.1"`, `WS_PORT = 8765`.
- `src/vibemix/runtime/ws_bus.py` — the single bus: mascot `websockets.serve` +
  `IpcRouterBus` both bind `127.0.0.1:8765` and never run at once. Debrief uses
  `8766` (`src/vibemix/debrief/`).

**Commands**

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
  tests/learn/test_no_new_ws_port.py \
  tests/runtime/test_ws_bus.py
```

**Key pins**
- `test_no_websockets_serve_in_learn_subpackage` — reddens on any non-comment
  `websockets.serve` under `src/vibemix/learn/`. New surfaces piggy-back the
  `ws_broadcast` producer on `8765`.

**Failure signatures**
- grep-gate `AssertionError` listing a `websockets.serve` offender → a surface
  opened its own listener. Reuse the bus.
- A hardcoded `8765`/`8766` literal instead of importing `WS_PORT` → fragile;
  import the constant.

---

## Invariant #5 — Idle ≠ fault (TypeScript)

**Sources**
- `tauri/ui/src/session/SessionLayout.ts` — `mountSessionLayout`,
  `renderSessionFrame`, `groundedFalseSinceMs` (the grounding-failure timer).
- `tauri/ui/src/session/components/cohost.ts` — `renderCohostPanel`, `setCohost`,
  `GROUNDING_FAILURE_MS` (= 5000).

**Command**

```bash
cd tauri/ui && npx vitest run tests/session/grounding-failure.spec.ts
# or the full gate:  cd tauri/ui && npm test
```

**Key pins** (in `tauri/ui/tests/session/grounding-failure.spec.ts`)
- `an IDLE co-host never faults on grounded=false (empty-screen regression guard)`
  — `groundedFalseSinceMs` stays `null` at idle; deck reads `data-mode="silent"`,
  never `"fault"`.
- `after >= 5s of grounded=false on an ACTIVE co-host the deck flips to fault`
  — the timer arms only while ACTIVE (status `"LISTENING"`).
- `screen=denied lights the badge but never faults the deck` — audio-only is a
  valid mode; screen-denied is badge-only.

**Failure signatures**
- `expected "silent" … received "fault"` on the IDLE test → the timer is arming
  at idle. Gate the timer on co-host ACTIVE status (mirror the `t0` mount checks
  in the spec).
- The full `npm test` failing here = the recurring "AI service unreachable" /
  blank-hero regression. Do not ship.

---

## After a review

Report, per invariant you touched: command run, pass/fail, offending file:line
on failure, and the fix. Never relax a gate to make it green — the gate is the
release contract.
