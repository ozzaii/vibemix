# Phase 60: Harmonic-Feedback Confidence Gate - Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 7 (3 modified, 4 new — incl. fixture)
**Analogs found:** 7 / 7 (every file has an in-repo, line-anchored analog — this is a pure-logic, codebase-internal phase)

This phase adds essentially ONE new piece of real logic (`is_clash`/`compatible`, ~40 lines). Everything else is wiring shipped signals together against patterns that already live in the same files being edited. The strongest possible analog for each new symbol is the sibling symbol already in that file.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/vibemix/state/harmonics.py` (MODIFY: `is_clash`/`compatible`/`_hour_distance`/`semitone_distance`) | utility (pure predicate) | transform | **same file** `to_camelot` + `_CAMELOT_RE` (`harmonics.py:82-107`, `:77`) | exact (same file, same pure/table-driven/honest-None contract) |
| `src/vibemix/state/event_detector.py` (MODIFY: `KEY_CLASH` + `TRANSITION_OPPORTUNITY` branches + `_melodic_overlap_gate`) | service (detector) | event-driven | **same file** `detect()` MIX_MOVE / TRACK_CHANGE / PHASE branches (`event_detector.py:187-275`) + `_music_truly_playing` gate (`:129-143`) | exact (same diff→Event pattern, same cooldown discipline) |
| `src/vibemix/state/coach.py` (MODIFY: replace 2 stub `task_for_event` arms) | prompt/builder | request-response | **same file** the live `TRACK_CHANGE`/`MIX_MOVE`/`PHASE` arms (`coach.py:219-251`) + the existing KEY_CLASH/TRANSITION_OPPORTUNITY stubs (`:264-273`) | exact (replacing stub arms with real ones in the same dispatch) |
| `tests/state/test_harmonics.py` (EXTEND: `is_clash`/`compatible` table oracle) | test | transform | **same file** the `to_camelot` table-oracle (`test_harmonics.py:23-129`) | exact (extend the existing parametrized oracle) |
| `tests/state/test_event_detector_harmonic.py` (NEW) | test | event-driven | existing detector tests + the `detect()` source it pins | role-match |
| `tests/state/test_coach_harmonic.py` (NEW) | test | request-response | `test_coach_prompt_grounding.py` / `test_coach_prompt_diet.py` (the coach goldens) | role-match |
| `tests/state/test_kaan_ear_veto.py` + `tests/fixtures/kaan_disagreed_pairs.json` (NEW) | test/eval (ship gate) | batch | `eval/deck_vision/run_eval.py` (`ACCURACY_FLOOR` gate, `run_eval.py:80-126`, `:307-324`) + the `DeckPoller._vision_enabled` default-off flag (`deck_poller.py:97-116`) | role-match (the Phase-59 KAAN-ACTION ship-gate precedent) |

## Pattern Assignments

### `src/vibemix/state/harmonics.py` (utility, transform) — ADD `is_clash`/`compatible`

**Analog:** the SAME file. `to_camelot` (`harmonics.py:82-107`) is the exact pattern to mirror: pure, side-effect-free, table/regex-driven, NEVER raises, honest-`None` on bad input. The new predicate sits ON TOP of it and reuses its `_CAMELOT_RE` recognizer.

**Honest-None / never-raise contract to copy** (`harmonics.py:82-107`, esp. the docstring `:90-94` and the guard clauses):
```python
def to_camelot(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    upper = s.upper()
    if _CAMELOT_RE.match(upper):  # already Camelot — passthrough, upper-cased
        return upper
    ...
    return None  # unrecognized → honest None, never a guess
```

**Recognizer to REUSE for `_parse`** (`harmonics.py:77`):
```python
# Already-Camelot recognizer: 1..12 followed by A or B.
_CAMELOT_RE = re.compile(r"^(1[0-2]|[1-9])[AB]$")
```

**The wheel-table convention to mirror** (`harmonics.py:28-65`): module-level `dict`/`frozenset` lookup tables with a comment citing the canonical source. The new `_CLASH_HOURS = frozenset({5, 6, 7})` / `_SAFE_HOURS = frozenset({0, 1, 2})` follow this exact form.

**Anchor for the relative-major/minor SAFE case** (`harmonics.py:40` vs `:55`): `Am→8A` and `C→8B` are the same number / swapped letter — verified relative pair in the shipped table; `compatible()`'s `na == nb → True` branch is grounded on this.

**Predicate body** (full derivation in RESEARCH §Pattern 1, lines 200-264 — copy verbatim): `_hour_distance` (circular 0..6), `_CLASH_HOURS={5,6,7}` (1-semitone + tritone band = the only same-letter clash), `_SAFE_HOURS={0,1,2}`. `is_clash` is deliberately NARROW (conservative-by-default); `None`-in → `False`.

---

### `src/vibemix/state/event_detector.py` (service, event-driven) — ADD two branches + gate

**Analog:** the SAME file's `detect()` branches. Every new branch mirrors an existing one structurally.

**Diff→Event firing pattern to copy** (the MIX_MOVE branch, `event_detector.py:269-273` — the closest analog: a conditional guard + cooldown + `Event(...)` + `_fire` + `return`):
```python
if new_significant and self._cooldown_ok("MIX_MOVE", now):
    self.last_mix_moves_seen = [m for _, m in state.recent_moves][-12:]
    ev = Event("MIX_MOVE", state, extra={"moves": new_significant[-3:]})
    self._fire("MIX_MOVE", now, state)
    return ev
```
The `KEY_CLASH` branch copies this shape exactly: `if self._harmonic_enabled and self._melodic_overlap_gate(state): ... and is_clash(...) and self._cooldown_ok("KEY_CLASH", now): ev = Event("KEY_CLASH", state, extra={...}); self._fire("KEY_CLASH", now, state); return ev` (RESEARCH §Pattern 3, lines 316-350).

**Branch placement:** insert AFTER the MIX_MOVE block (`event_detector.py:275`) and BEFORE the genre-chain loop (`:284`). Both branches sit INSIDE the `_music_truly_playing` gate (`:183-185`) so they inherit the sustained-audible + valid-BPM guard for free.

**Cooldown helper to REUSE as-is** (`event_detector.py:124-127`) — KEY_CLASH (28s) / TRANSITION_OPPORTUNITY (20s) already registered in `MIN_EVENT_GAP_PER_TYPE`:
```python
def _cooldown_ok(self, ev_type: str, now: float) -> bool:
    gap = MIN_EVENT_GAP_PER_TYPE.get(ev_type, EVENT_GLOBAL_MIN_GAP)
    last = self.last_per_type_at.get(ev_type, 0.0)
    return (now - last) > gap and (now - self.last_event_at) > EVENT_GLOBAL_MIN_GAP
```

**Gate-helper pattern to copy** (`_music_truly_playing`, `event_detector.py:129-143`): a private `bool`-returning method composed entirely from already-populated `MusicState` fields, used as a hard precondition. `_melodic_overlap_gate(state)` follows this exact shape (RESEARCH §Pattern 2, lines 280-307).

**Already-shipped read-only signals the gate composes** (verified in `music_state.py`): `audible_deck` (`:114`, values `'A'/'B'/'mix'/'none'`), `phase`, `rms`, `onset_density` (`:33`), `vocal_active` (`:43`), `bands`, `deck_state` (`:69`). The `not state.vocal_active` suppression precedent already exists in the LAYER_ARRIVAL branch (`event_detector.py:233`) and the `state.rms > LOW_RMS` floor in the same branch (`:232`) — copy both idioms.

**Cross-deck / cite-floor read pattern** — the branch reads `DeckTrack.camelot` + `.confidence` and gates on `DECK_CITE_MIN_CONF` (`deck_poller.py:73`, value `0.6`). `DeckTrack` fields (`deck_state.py:39-46`): `camelot: str | None`, `confidence: float`, `source: str`. The detector READS only — single-writer rule: `deck_state.decks` is assigned ONLY in `refresh.py::_tick_once`.

**`_fire` writes an `[ev:<TYPE>]` observation** (`event_detector.py:296-333`) — already generic over `ev_type`, so `_fire("KEY_CLASH", ...)` works with NO change (best-effort registry write in try/except). This is why Open-Q1 (matrix grammar list) is low-risk.

**New flag (default-off):** add `self._harmonic_enabled = False` to `__init__` (`event_detector.py:82-122`) — see the Shared Patterns / `_vision_enabled` precedent below.

---

### `src/vibemix/state/coach.py` (prompt/builder, request-response) — replace 2 stub arms

**Analog:** the SAME `task_for_event` dispatch. The live arms (`coach.py:219-251`) show the fragment shape; the existing stubs (`:264-273`) are the literal lines to replace.

**The current stubs to REPLACE** (`coach.py:264-273`):
```python
if t == "KEY_CLASH":
    return (
        "React naturally to what you HEAR — ground on the audio and the "
        "decks[...] evidence. (Harmonic clash detection is not live yet.)"
    )
if t == "TRANSITION_OPPORTUNITY":
    return (
        "React naturally to what you HEAR — ground on the audio and the "
        "decks[...] evidence. (Transition cueing is not live yet.)"
    )
```

**Fragment-construction pattern to copy** (the MIX_MOVE arm, `coach.py:238-251` — reads `ev.extra`, builds an instruction string that hands the LLM a grounded fact + a verb-y task + a silence escape "output a single space"):
```python
if t == "MIX_MOVE":
    mv = ", ".join(ev.extra.get("moves", []))
    return (
        f"A move just landed [{mv}]. ... Ground your feedback on what that "
        "change DID to the mix ... If the change did nothing notable, ... or "
        "output a single space to stay silent."
    )
```

**`ev.extra` read precedent** (the TRACK_CHANGE / PHASE arms, `coach.py:219-232`):
```python
if t == "PHASE":
    new = ev.extra.get("new_phase", "?")
    prev = ev.extra.get("prev_phase", "?")
    return f"Phase shifted: {prev}→{new}. ..."
```
The KEY_CLASH arm reads `ev.extra["a_side"/"a_camelot"/"b_side"/"b_camelot"/"semitones"]` the same way and MUST: (a) state the verdict is system-decided ("you do NOT decide this"), (b) instruct CITE both keys `[key:A:8A]`+`[key:B:3A]`, (c) forbid key math. Full fragment in RESEARCH §Pattern 4 (lines 357-370).

**Citation grammar already supports it** (`matrix.py:117`): `[key:<deck>:<camelot>]  deck harmonic key, e.g. [key:A:8A]`. Open-Q1: `matrix.py:124` event-type list omits the two new types (LOW risk — clash cites `[key:...]` not `[ev:KEY_CLASH]`; decide at plan time).

**Anti-slop is structural, not prompt-dependent:** `key` is an existence-only source in `CitationLinter` — a fabricated `[key:B:12B]` the registry never observed strips the WHOLE turn (no `coach/citation_linter.py` change needed).

**Regression guard (Pitfall 5):** these two arms currently never fire; replacing them touches only the KEY_CLASH/TRANSITION_OPPORTUNITY paths. Run the full `test_coach_prompt_grounding.py` + `test_coach_prompt_diet.py` golden set after. Keep both types OUT of `ACK_ELIGIBLE_EVENTS` (diet `ValueError` guard at `coach.py:301-304`).

---

### `tests/state/test_harmonics.py` (test, transform) — EXTEND with the predicate oracle

**Analog:** the SAME file. The `to_camelot` table-oracle (`test_harmonics.py:23-129`) is the exact pattern: a module-level list of `(input, expected)` pairs + a `@pytest.mark.parametrize` test, plus an explicit canonical-anchors smoke test, plus a "never raises on garbage" parametrized test.

**Parametrized-oracle shape to copy** (`test_harmonics.py:63-67`):
```python
@pytest.mark.parametrize("raw,expected", MUSICAL_TO_CAMELOT_PAIRS)
def test_musical_notation_maps_to_camelot(raw, expected):
    assert to_camelot(raw) == expected
```

**Honest-None / never-raise test to mirror for `is_clash`** (`test_harmonics.py:111-129`):
```python
@pytest.mark.parametrize("raw", ["", None, "not-a-key", "13A", "0A", "8C", ...])
def test_unrecognized_input_returns_none_never_raises(raw):
    assert to_camelot(raw) is None
```
Mirror: `is_clash(None, "8A") is False`, `is_clash("garbage", "8A") is False` — never raises.

**Import line to extend** (`test_harmonics.py:19`): `from vibemix.state.harmonics import to_camelot` → add `is_clash, compatible`. The verified clash/safe oracle pairs are in RESEARCH §Code Examples (lines 452-456): `8A↔3A`/`8A↔1A` → clash; `8A↔9A`/`8A↔10A`/`8A↔8B`/`8A↔6A` → safe.

---

### `tests/state/test_event_detector_harmonic.py` (test, event-driven) — NEW

**Analog:** the `detect()` source it pins (`event_detector.py:154-294`) + the existing event-detector test suite. Construct an `EventDetector`, feed `MusicState` snapshots, assert the returned `Event` (or `None`). The cardinal-rule docstring (`event_detector.py:25-41`) names the exact gates to test.

**Test map (RESEARCH lines 533-539):** `test_no_clash_single_deck` (audible_deck != "mix"), `test_no_clash_in_breakdown` (phase∈breakdown/silent/low), `test_no_clash_percussive` (vocal_active / no tonal share), `test_no_clash_subfloor_deck` (confidence < `DECK_CITE_MIN_CONF`), `test_detector_gated_by_default` (`_harmonic_enabled=False` → never fires). Reuse the `_cooldown_ok` semantics (`event_detector.py:124-127`) for the cooldown test.

---

### `tests/state/test_coach_harmonic.py` (test, request-response) — NEW

**Analog:** `tests/state/test_coach_prompt_grounding.py` + `test_coach_prompt_diet.py` (the coach golden suite). Build an `Event("KEY_CLASH", ..., extra={...})`, call `AICoach.task_for_event(ev)` / `build_prompt(ev)`, assert the fragment cites both keys and contains no key-math request; assert TRANSITION fragment is past-tense (no imperative verbs "bring/pull/drop"). Plus a `CitationLinter` case: fabricated `[key:B:12B]` strips the turn.

---

### `tests/state/test_kaan_ear_veto.py` + `tests/fixtures/kaan_disagreed_pairs.json` (test/ship-gate, batch) — NEW

**Analog:** `eval/deck_vision/run_eval.py` — the Phase-59 KAAN-ACTION ship-gate precedent (a documented floor + a default-off flag that flips only after Kaan signs off the eval).

**Floor-gate / conservative-default doc pattern to copy** (`run_eval.py:80-89`, the `ACCURACY_FLOOR` block + WHY-THIS-GATE-EXISTS docstring `:9-17`): a named threshold with a comment that says "below the floor degrades to the conservative default, NOT a failure". The veto harness mirrors this: the disagreed-pairs corpus is the floor; `harmonic_clash_enabled` stays False until it passes.

**Pass/fail + exit-code reporting pattern** (`run_eval.py:307-324`): a harness that scores a corpus and returns non-zero if the gate isn't cleared — surfaces the KAAN-ACTION review.

**Corpus + test shape** (RESEARCH lines 460-481, copy verbatim): `kaan_disagreed_pairs.json` = pairs Kaan would happily mix (`8A/9A`, `8A/8B`, `8A/10A`, `5A/5A`, `8A/6A`) that MUST NOT flag, plus true clashes (`8A/3A`, `8A/1A`) that SHOULD flag (proves the gate isn't vacuous):
```python
@pytest.mark.parametrize("pair", load_disagreed_pairs())
def test_disagreed_pairs_never_flag(pair):
    assert is_clash(pair["a"], pair["b"]) is False
def test_true_clashes_do_flag():
    assert is_clash("8A", "3A") is True
    assert is_clash("8A", "1A") is True
```

## Shared Patterns

### Default-off ship gate (the Kaan-ear veto flag)
**Source:** `DeckPoller._vision_enabled` (`src/vibemix/state/deck_poller.py:97-116`)
**Apply to:** `event_detector.py` (the new `self._harmonic_enabled` flag) + `test_kaan_ear_veto.py` (the gate the flag waits on)
The exact established precedent for "a detector ships gated/quiet by default until Kaan signs off an eval" — copy the rationale comment style and the `bool(...)` default-False construction:
```python
# vision must NOT feed deck-state until the real-screenshot accuracy eval
# clears the documented floor per app — the KAAN-ACTION checkpoint ...
# the gate stays OFF by default until Kaan signs off the eval.
self._vision_enabled = bool(vision_enabled)
```
`harmonic_clash_enabled` mirrors this verbatim (default `False`, code-level flag, NOT a `.env` secret — RESEARCH line 408). The KEY_CLASH branch guards on `if self._harmonic_enabled and ...`.

### Honest-None / never-raise pure-function contract
**Source:** `harmonics.to_camelot` (`harmonics.py:82-107`) + the contract docstring (`:10-13`)
**Apply to:** `is_clash` / `compatible` / `_parse`
Every pure predicate degrades to `False`/`None` on bad input and NEVER raises — `is_clash(None, x) → False` is the anti-slop core ("we never flag what we can't prove dissonant").

### Read-only `MusicState` consumption (single-writer rule)
**Source:** every `detect()` branch reads `state.*` and never mutates deck-state (`event_detector.py:187-275`); `deck_state.decks` is written ONLY in `refresh.py::_tick_once` (`deck_state.py:15-16`)
**Apply to:** `_melodic_overlap_gate` + the KEY_CLASH branch — READ `audible_deck`/`phase`/`rms`/`onset_density`/`vocal_active`/`bands`/`deck_state.decks[*].camelot`/`.confidence`; write nothing.

### Cooldown + `_fire` event bookkeeping
**Source:** `_cooldown_ok` (`event_detector.py:124-127`) + `_fire` (`:296-333`) + `MIN_EVENT_GAP_PER_TYPE` (`constants.py:118-119`, KEY_CLASH=28s / TRANSITION_OPPORTUNITY=20s)
**Apply to:** both new branches — reuse as-is; the cooldowns + the `[ev:<TYPE>]` registry write are already wired and generic over `ev_type`.

### Cited-narration-not-computation fragment
**Source:** the live `task_for_event` arms (`coach.py:219-251`) + `CITATION_GRAMMAR_BLOCK` (`matrix.py:117`)
**Apply to:** the KEY_CLASH / TRANSITION_OPPORTUNITY arms — hand the LLM a pre-decided verdict + a CITE-both-keys instruction + a "single space to stay silent" escape; forbid interval math.

## No Analog Found

None. Every file in this phase has a direct, line-anchored in-repo analog (most in the very file being edited). This is the expected shape of a pure-logic, codebase-internal phase.

## Metadata

**Analog search scope:** `src/vibemix/state/` (harmonics, event_detector, coach, deck_poller, deck_state, music_state, refresh, evidence_registry), `src/vibemix/prompts/matrix.py`, `src/vibemix/audio/constants.py`, `tests/state/`, `eval/deck_vision/`.
**Files scanned:** ~12 source + test modules read directly (RESEARCH had already line-anchored every integration point; this map confirmed each excerpt against the live source).
**Pattern extraction date:** 2026-05-21
