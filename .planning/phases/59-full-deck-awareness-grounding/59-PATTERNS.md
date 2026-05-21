# Phase 59: Full Deck Awareness + Grounding - Pattern Map

**Mapped:** 2026-05-21
**Files analyzed:** 12 (4 NEW source + 6 MODIFIED source + N test files)
**Analogs found:** 12 / 12 (every new piece bolts onto a shipped, well-tested rail)

> **One-line thesis (from RESEARCH §Don't Hand-Roll):** ~70% of this phase's data
> work is already shipped. The deck poller is the *third* read-only external source
> after `ControllerState` and `TrackInfo`. The `key:` source mirrors `track:`. The
> read-only repo test extends the SQLCipher-dormancy idiom. Every new file has a
> close, recent analog — resist re-implementing the existing rails.

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `state/harmonics.py` (NEW) | utility (pure fn) | transform | `audio/features.py::snapshot_features` (pure transform, no I/O) | role-match |
| `state/deck_state.py` (NEW) | model (dataclass) | — | `state/music_state.py::MusicState` + `library/rekordbox.py::TrackEntry` | exact |
| `state/deck_poller.py` (NEW) | service (read-only producer) | request-response / batch | `midi/state.py::ControllerState` + `platform/_track_macos.py::TrackInfo` | exact |
| `state/numpy_key.py` (NEW, deferrable) | utility (DSP) | transform | `audio/features.py` (numpy chromagram / autocorr family) | role-match |
| `state/music_state.py` (MOD) | model (dataclass) | — | self (Phase 17/31/52 additive-field precedent) | exact |
| `state/refresh.py` (MOD `_tick_once`) | service (single writer) | event-driven | self — controller/track snapshot-copy block (lines 427-460) | exact |
| `state/evidence_registry.py` (MOD) | config (grammar surface) | — | self — the `track`/`mix` source rows + `_SOURCE_ALT` | exact |
| `coach/citation_linter.py` (MOD) | middleware (response gate) | request-response | self — `track`/`screen`/`mix`/`tend` existence-only branch | exact |
| `state/event.py` (MOD `EVENT_PRIORITY`) | config (map) | — | self — `MIX_MOVE`/`TRACK_CHANGE` rows | exact |
| `audio/constants.py` (MOD `MIN_EVENT_GAP_PER_TYPE`) | config (map) | — | self — `MIX_MOVE`/`BREAKDOWN_KICK_KILL` rows | exact |
| `state/coach.py` (MOD `evidence_line` + `task_for_event`) | service (prompt builder) | transform | self — the `track=unknown` gate (lines 78-81) | exact |
| `prompts/matrix.py` (MOD `CITATION_GRAMMAR_BLOCK`) | config (prompt text) | — | self — the 7 `Forms` block (lines 108-122) | exact |
| `agent/dj_cohost.py` (MOD `_build_citation_strip` + screen leg) | controller (LLM node) | streaming | self — `_build_citation_strip` source allow-list (line 204) + `screen_jpeg=None` killswitch (line 553) | exact |
| `tests/library/test_rekordbox.py` / `tests/repo/test_repo_scrub.py` (MOD) | test | — | `test_no_sqlcipher_module_imported_after_load` subprocess idiom | exact |

---

## Pattern Assignments

### `state/harmonics.py` (NEW — utility, pure transform)

**Analog:** `audio/features.py::snapshot_features` (the established "pure function over data, zero I/O, zero state, returns a dict/scalar" shape). RESEARCH ships the full table verbatim in §Code Examples lines 417-445.

**What to copy:** the *shape* — module-level constant table + a single pure function that NEVER raises and degrades to `None`. The Camelot table itself is given in RESEARCH (do not invent it).

**Degradation discipline to mirror** (from `track_resolver.py:105-115` and `coach.py:78-81` — "honest unknown over false confidence"):
```python
def to_camelot(raw: str | None) -> str | None:
    """Normalize musical 'Am' / Camelot '8A' / open-key '1m' -> Camelot.
    Returns None on empty/unrecognized — NEVER raises (-> key=unknown)."""
    if not raw:
        return None
    # ... table lookup + Camelot regex passthrough ...
    return None  # unrecognized -> honest None, never a guess
```

**License header convention** (every src file): `# SPDX-License-Identifier: Apache-2.0` as line 1, then a module docstring. See any file in `src/vibemix/state/`.

---

### `state/deck_state.py` (NEW — model, dataclass)

**Analog (shape):** `library/rekordbox.py::TrackEntry` (lines 69-94) — the "intentionally narrow field set, typed empties on absence (`bpm=0.0` NOT `None`)" frozen dataclass.
**Analog (additive-default discipline):** `state/music_state.py::MusicState` (every Phase 17/31/52 field uses `field(default_factory=...)` / a default literal so golden-equivalence holds until populated).

**Field set** (RESEARCH §Pattern 1 lines 200-219 ships the exact dataclass — copy it verbatim, it's already refined against the verified XML key format):
- `DeckTrack`: `title`, `track_id` (feeds `[track:<id>]`), `bpm` (from `AverageBpm`, NOT audio autocorr), `key` (RAW tag `"Am"`), `camelot` (`"8A"` via `harmonics.to_camelot`), `open_key`, `energy`, `loaded_at`, `confidence`, `source`.
- `DeckState`: `decks: dict[str, DeckTrack] = field(default_factory=dict)`, `updated_at: float = 0.0`.

**Imports pattern to copy** (from `music_state.py:14-18` — `from __future__ import annotations` + `from dataclasses import dataclass, field`):
```python
from __future__ import annotations
from dataclasses import dataclass, field
```

**Critical:** `source` defaults to `"unknown"` and every harmonic field defaults to `None`/`0.0` — an empty `DeckState()` must serialize to nothing in `evidence_line` (Pitfall 5, golden-equivalence).

---

### `state/deck_poller.py` (NEW — service, read-only snapshot producer)

**Primary analog:** `midi/state.py::ControllerState` — the canonical "own holder, lock-guarded mutation, `.deck_snapshot()` returns a deep copy the caller cannot mutate" producer.
**Secondary analog:** `platform/_track_macos.py::TrackInfo` — the "own `threading.Lock`, `.snapshot()` returns a fresh dict, `poll_once()` swallows all subprocess errors silently, no log spam" producer + its `run_poll_loop(stop_event)` cadence wrapper.

**Snapshot-producer pattern to copy** (`ControllerState.deck_snapshot`, `midi/state.py:378-389`):
```python
def deck_snapshot(self) -> dict:
    """Static snapshot ... caller cannot mutate listener-thread state."""
    with self._lock:
        snap: dict = {d: dict(self.deck[d]) for d in self.deck}
        snap["xfader"] = self.xfader
        snap["connected"] = self._connected
        return snap
```
→ the deck poller exposes `snapshot() -> dict[str, DeckTrack]` (one entry per resolved deck), built under its own `threading.Lock`, returning copies.

**Graceful-degradation pattern to copy** (`TrackInfo.poll_once`, `_track_macos.py:48-66`) — every external read (XML re-stat, Gemini-vision call, numpy estimate) swallows its own exceptions and returns last-known state. No exception escapes the poller.

**Source-ladder + confidence-floor pattern** (RESEARCH §Pattern 2, lines 227-231): try XML library match (highest conf) → Gemini-vision badge → numpy KS (key only). First source clearing its floor wins; below all floors → `confidence=0`, `source="unknown"`, harmonic fields stay `None`.

**XML enrichment — DO NOT hand-roll a parser.** Reuse the already-loaded `RekordboxLibrary` (cache-warm via `try_load_cache()`). Title→`TrackEntry` is the join key; read `TrackEntry.key` (raw `Tonality`) + `TrackEntry.bpm`. See `library/rekordbox.py::RekordboxLibrary` (`lookup_by_id`, `.tracks` dict).

**Audible-deck attribution — DO NOT hand-roll.** Reuse `track_resolver.derive_audible_deck(deck_a, deck_b, xfader, connected)` (already trusts fader+xfader over the FLX4 play-state desync). This decides *which* deck a resolved title belongs to. See `state/track_resolver.py:31-89`.

**Cross-deck suppression** (RESEARCH §Pattern 3 + Pitfall 4): the poller sets `confidence=0` on any deck it cannot *independently* resolve (the silent/non-audible deck needs its own vision badge or a confidently-attributed library match — never "the other now-playing title"). This is what makes Phase 60's cross-deck clash uncitable-by-construction.

**Vision leg (GATED — biggest risk).** See `agent/dj_cohost.py:553` `screen_jpeg = None` — a deliberate v4 anti-hallucination killswitch ("Screen + MIDI metadata caused hallucination"). The vision deck-read MUST be a *separate, structured-output, low-frequency* Gemini call (its own prompt + JSON schema, null→`unknown`), NOT a screenshot re-attached to the reaction turn. Capture infra to reuse: `platform/screen.py::CapturedFrame.jpeg` + `dj_cohost.py self._screen_buf` (line 364). Cadence: track-change/screen-change only, never per-tick. **Eval-gate it** (Spike 2 — KAAN-ACTION real-screenshot corpus).

---

### `state/numpy_key.py` (NEW — utility, DSP transform; build-deferrable per A6/Open-Q2)

**Analog:** `audio/features.py` — same numpy/scipy FFT + autocorrelation family already shipped for BPM estimation. RESEARCH §Don't Hand-Roll: ~80 lines, chromagram + Krumhansl-Temperley profile correlation. Fires ONLY when no tag/badge yields a key (last resort).
**Discretion:** RESEARCH Open Q2 recommends scaffolding the `DeckTrack.source="numpy_key"` slot now but gating the estimator *implementation* on the live test showing real "no-tag" gaps. Keep in scope, low priority within the phase.

---

### `state/music_state.py` (MODIFIED — additive field)

**Analog:** itself. Every Phase 17/31/52 field is precedent. Copy the additive-default pattern exactly (RESEARCH §Pattern 1 line 223):
```python
    # Phase 59 (DECK-01) — embedded deck-state. ADDITIVE: default-empty
    # DeckState (decks={}) preserves golden-equivalence — no output until
    # _tick_once populates it. SINGLE-WRITER rule holds: written ONLY inside
    # state_refresh_loop._tick_once under state._lock.
    deck_state: DeckState = field(default_factory=DeckState)
```
**Existing precedent comment to mirror** (`music_state.py:45-54`, the Phase 52 `detected_genre` field): it documents single-writer ownership + the golden-equivalence rationale inline. Match that comment density.

**Pitfall 5 (RESEARCH lines 408-412):** a default-NON-empty deck field would flip snapshot/prompt goldens. Keep `decks={}` empty by default; the `evidence_line` deck block must be conditional on a resolved deck (mirror the `track=unknown` gate).

---

### `state/refresh.py` (MODIFIED — `_tick_once`, the ONLY writer)

**Analog:** itself — the controller/track snapshot-copy block already inside `with state._lock:` (`refresh.py:427-460`). This is the *exact* pattern the deck copy mirrors. The poller is the third external source after `ControllerState`/`TrackInfo`.

**Snapshot-copy pattern to copy** (`refresh.py:427-432`, controller block):
```python
        # Controller snapshot
        cs = controller_state.deck_snapshot()
        state.deck_a = cs["A"]
        state.deck_b = cs["B"]
        state.xfader = cs["xfader"]
        state.controller_connected = cs["connected"]
```
→ becomes (RESEARCH §Code Examples lines 447-456):
```python
        deck_snap = deck_source.snapshot()           # read-only producer
        for side, dt in deck_snap.items():
            dt.camelot = harmonics.to_camelot(dt.key)  # pure fn, µs cost
        state.deck_state.decks = deck_snap
        state.deck_state.updated_at = now
```

**Change-only registry-write pattern to copy** (`refresh.py:437-446`, the `mix:audible_deck` change-only write — guard `prev != new`, wrap in `try/except`, compute `t_session = max(0.0, now - state.set_start_at)`):
```python
        prev_deck = state.audible_deck
        # ... derive ...
        if evidence_registry is not None and prev_deck != aud_deck:
            try:
                t_session = max(0.0, now - state.set_start_at)
                evidence_registry.write("mix", f"audible_deck={aud_deck}", t_session)
            except Exception:
                pass
```
→ the `key:`/`track:` writes (RESEARCH Spike 3 lines 351-364), gated on `confidence >= DECK_CITE_MIN_CONF` and `(side, camelot)` change-only:
```python
        if evidence_registry is not None:
            for side, dt in state.deck_state.decks.items():
                if dt.confidence >= DECK_CITE_MIN_CONF and dt.camelot:
                    try:
                        t_session = max(0.0, now - state.set_start_at)
                        evidence_registry.write("key", f"{side}:{dt.camelot}", t_session)
                        if dt.track_id:
                            evidence_registry.write("track", dt.track_id, t_session)
                    except Exception:
                        pass
```

**INVARIANT (Pitfall 3):** `state.deck_state.decks = ...` must appear NOWHERE outside this `with state._lock:` block in `refresh.py`. The poller writes its own holder only.

---

### `state/evidence_registry.py` (MODIFIED — grammar surface)

**Analog:** itself — the `track`/`mix` source rows in `EVIDENCE_SOURCES` (line 95-97) + the `_SOURCE_ALT` alternation (line 104).

**Three edit sites (RESEARCH Spike 3 lines 322-334):**
```python
# 1. add "key" to the frozenset (line 95-97)
EVIDENCE_SOURCES: frozenset[str] = frozenset(
    {"ev", "aud", "midi", "track", "screen", "mix", "tend", "key"}
)
# 2. add to the regex alternation (line 104)
_SOURCE_ALT = "ev|aud|midi|track|screen|mix|tend|key"
# 3. extend the EBNF docstring (lines 89-94, 108-116) to document key-body
```
**`_INNER_ATOM` and `parse_citations` are UNCHANGED** — `key:A:8A` matches `(?:...|key):[^\s,\]]+` (body `A:8A` has no whitespace/comma/bracket), and `parse_citations` splits on the FIRST `:` via `.partition(":")` (line 464), so `parse_citations("[key:A:8A]") -> [("key", "A:8A")]`. Verified against the partition logic — no parser change.

**`register_library` (line 218) needs NO change** — `track:<id>` already resolves; the deck poller emits the same `track:` writes via `_tick_once`.

---

### `coach/citation_linter.py` (MODIFIED — response gate)

**Analog:** itself — the existence-only branch `valid = body in snapshot.get(source, {})` (line 204) that already handles `track`/`screen`/`mix`/`tend`.

**The ONLY change:** `key` joins the existence-only set by being in `EVIDENCE_SOURCES` (via the registry edit above) and ABSENT from `_TIME_KEYED_SOURCES` (line 45):
```python
_TIME_KEYED_SOURCES: frozenset[str] = frozenset({"ev", "aud", "midi"})  # key NOT added here
```
**No code change to `_validate_atom` itself** (RESEARCH Spike 3 line 348, verified by logic trace). `_validate_atom`'s final branch already validates `key:A:8A` by exact-body presence: the poller wrote `f"{side}:{camelot}"` so the body `A:8A` is in `snapshot["key"]`; a hallucinated `[key:A:12B]` never written → not in snapshot → atom invalid → whole turn stripped (response-level binary, line 161-166).

---

### `state/event.py` (MODIFIED — `EVENT_PRIORITY` map)

**Analog:** itself — the `MIX_MOVE: 5` / `TRACK_CHANGE: 7` rows (lines 36-45).

**Add (RESEARCH event-plumbing section lines 371-374):**
```python
    "KEY_CLASH": 7,               # tie with TRACK_CHANGE — a clashing overlay is "react now"
    "TRANSITION_OPPORTUNITY": 5,  # tie with MIX_MOVE — structural, not urgent
```
**Plumbing-only:** the `__post_init__` default + `EVENT_PRIORITY.get(type, 0)` fallback (lines 60-62) mean an unregistered type silently gets priority 0; registering them now is the plumbing. **No detector branch, no `task_for_event` firing logic — Phase 60.**

---

### `audio/constants.py` (MODIFIED — `MIN_EVENT_GAP_PER_TYPE` map)

**Analog:** itself — the `MIX_MOVE: 14.0` / `BREAKDOWN_KICK_KILL: 20.0` rows (lines 80-114). Note the convention: every entry carries a one-line `# why` comment.

**Add (RESEARCH event-plumbing section lines 376-378):**
```python
    "KEY_CLASH": 28.0,             # long gap — a clash persists; re-arm after it clears+recurs (~25-30s band)
    "TRANSITION_OPPORTUNITY": 20.0,  # medium — fires at the moment a blend COULD start
```
Both inherit the `EVENT_GLOBAL_MIN_GAP = 22.0` floor (line 58) via `_cooldown_ok` — no gate-logic change.

---

### `state/coach.py` (MODIFIED — `evidence_line` deck block + `task_for_event` stub arms)

**Analog:** itself — the `track=unknown` honest-degradation gate (lines 78-81):
```python
        if state.audible_track and state.audible_track_confidence >= 0.3:
            e.append(f"track={state.audible_track!r}")
        else:
            e.append("track=unknown")
```
**Deck block to add (RESEARCH §Code Examples lines 458-468)** — additive, gated on a resolved deck so empty `deck_state` adds nothing (Pitfall 5):
```python
        resolved = {s: d for s, d in state.deck_state.decks.items()
                    if d.camelot and d.confidence >= 0.3}
        if resolved:
            parts = [f"{s}={d.title!r} {d.camelot} {d.bpm:.0f}bpm"
                     for s, d in sorted(resolved.items())]
            e.append("decks[" + " | ".join(parts) + "]")
        else:
            e.append("decks=unknown")
```
**Anti-pattern (RESEARCH line 243):** deck-state is substantive — do NOT add it to the diet/ack `_evidence_line_compact` path or `ACK_ELIGIBLE_EVENTS`. Deck events are full-payload.
**`task_for_event`:** add the `KEY_CLASH`/`TRANSITION_OPPORTUNITY` stub arms ONLY (no firing logic — Phase 60 fills the task strings).

---

### `prompts/matrix.py` (MODIFIED — `CITATION_GRAMMAR_BLOCK`)

**Analog:** itself — the `Forms` list (lines 108-122). The grammar primer must teach Gemini it can cite `[key:A:8A]`, in lock-step with `EVIDENCE_SOURCES`.

**Add a form line** (mirror line 114 `[mix:<derived>]`):
```
  [key:<deck>:<camelot>]  deck harmonic key, e.g. [key:A:8A]
```
This is touchpoint #4 of the 5 schema-mirror sites (RESEARCH line 366). The comment at matrix.py:96 already states the 7 forms are "kept in lock-step with EVIDENCE_SOURCES" — honor it.

---

### `agent/dj_cohost.py` (MODIFIED — citation strip + gated vision leg)

**Analog:** itself — `_build_citation_strip` source allow-list (line 204: `if source not in ("ev", "mix", "midi"): continue`).

**Touchpoint #5 (RESEARCH line 366):** decide whether `key:` yields a UI chip (like `mix:`/`ev:`). If yes, add `"key"` to the allow-list at line 204 and derive a chip verb from the `A:8A` body. The chip's `timestamp_s` comes from the registry, NOT the citation body (anti-hallucination contract, lines 167-169).

**Vision leg killswitch (Spike 2, biggest risk):** `screen_jpeg = None` at line 553 is the deliberate v4 anti-hallucination invariant. Do NOT flip it to live on the reaction path. The pre-wired `skip_screen` / `SCREEN_SKIP_EVENTS` (line 89) + the `screen_jpeg and not skip_screen` guard (line 680) are the diet rule. The vision deck-read is a SEPARATE structured call (see `deck_poller.py` above), not a re-attach here.

---

### Tests (MODIFIED + NEW — Wave 0)

**Read-only repo assertion (DECK-05) — analog:** `tests/library/test_rekordbox.py::test_no_sqlcipher_module_imported_after_load` (lines 105-132). This is the proven subprocess-dormancy idiom to extend: spawn a fresh interpreter, run the deck path, assert no `*sqlcipher*` module + no DJ-DB write-mode open. Copy the exact `subprocess.run([sys.executable, "-c", script], ...)` + `assert result.stdout.strip() == "DORMANT"` shape:
```python
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True, text=True, check=True,
    )
    assert result.stdout.strip() == "DORMANT", (...)
```
Add a new `tests/repo/test_repo_scrub.py::test_deck_readonly` case mirroring `test_retired_poc_files_stay_gone` + the `_git_ls_files`/grep idiom (lines 73-82, 194-212) to assert no `Rekordbox6Database`/`.commit()`/write-mode open exists in `src/vibemix/`.

**Grammar/linter extensions — analog:** `tests/state/test_evidence_registry.py` (the `test_evidence_07_regex_matches_all_seven_forms` + `test_evidence_11_sources_constant_locked` shape) and `tests/coach/test_citation_linter.py::test_track_atom_existence_only` (lines 149-169) — copy the `track:` existence-only test verbatim, swap to `key:A:8A`.

**Event-map extensions — analog:** `tests/state/test_event_priority.py` (per-type `assert Event(...).priority == N`) + `tests/audio/test_constants.py::test_event_gap_dict_shape_and_values` (lines 84-145, the explicit per-key value asserts).

**Golden-equivalence regression — analog:** `tests/state/test_coach_prompt_grounding.py` — extend to assert empty `deck_state` keeps `evidence_line` byte-identical.

---

## Shared Patterns

### Single-writer `MusicState` (cardinal invariant)
**Source:** `state/refresh.py::_tick_once` `with state._lock:` block (lines 303-487).
**Apply to:** `deck_state.py`, `deck_poller.py`, `refresh.py`.
**Rule:** the poller writes its OWN holder; `_tick_once` is the ONLY thing that copies `deck_source.snapshot()` into `MusicState.deck_state`, inside the lock. Mirrors `ControllerState`/`TrackInfo`.

### Citation grounding (anti-slop gate)
**Source:** `state/evidence_registry.py` (`EVIDENCE_SOURCES`, `write`, `snapshot`, `has`) + `coach/citation_linter.py::_validate_atom` (existence-only branch, line 204).
**Apply to:** `evidence_registry.py`, `citation_linter.py`, `prompts/matrix.py`, `dj_cohost.py`, `refresh.py`.
**Rule:** evidence must hit the registry (via `_tick_once.write("key", ...)`) before the LLM can cite it; a fabricated `[key:A:12B]` is stripped response-level. 5 schema-mirror touchpoints must move in lock-step: (1) `EVIDENCE_SOURCES`, (2) `_SOURCE_ALT` regex, (3) EBNF docstring, (4) `CITATION_GRAMMAR_BLOCK`, (5) `_build_citation_strip` chip whitelist.

### Honest `unknown` over false confidence ("trust the audio")
**Source:** `state/track_resolver.py:105-115` (returns `(None, 0.0)` rather than naming a track that isn't playing) + `coach.py:78-81` (`track=unknown` gate).
**Apply to:** `harmonics.py` (`to_camelot` returns `None`, never raises), `deck_poller.py` (below floor → `confidence=0`, `source="unknown"`), `coach.py` (`decks=unknown` gate).

### Read-only external source (no DJ-DB writes, ever)
**Source:** `library/rekordbox.py` (XML import path only; SQLCipher `db6` banned) + its dormancy test.
**Apply to:** `deck_poller.py` (reuse the cache-warm `RekordboxLibrary`, never the live DB), `test_rekordbox.py`/`test_repo_scrub.py` (extend the dormancy idiom).
**Rule:** XML-export primary; live `Rekordbox6Database`/SQLCipher stays dead behind the grep-gate + dormancy test + `pyproject.toml` wheel exclusion.

### Graceful degradation on every external read
**Source:** `platform/_track_macos.py::TrackInfo.poll_once` (swallows TimeoutExpired/CalledProcessError/FileNotFoundError/OSError silently, returns last-known state, no log spam).
**Apply to:** `deck_poller.py` (XML re-stat, Gemini-vision call, numpy estimate each swallow their own exceptions).

### Additive-field golden-equivalence
**Source:** `state/music_state.py` (Phase 17/31/52 fields default-empty until written) + `coach.py` conditional gates.
**Apply to:** `music_state.py` (`deck_state` field), `coach.py` (`evidence_line` deck block), the golden-equivalence regression test.

---

## No Analog Found

None. Every new/modified file has a close, recent analog in the codebase. The single genuinely-novel-shape concern — the Gemini-vision deck-read — is not a "no analog" case but a "deliberately-disabled analog" case: the capture + inline-Part infra exists (`platform/screen.py::CapturedFrame`, `dj_cohost.py self._screen_buf`, the `types.Part.from_bytes` append site) but sits behind the v4 `screen_jpeg = None` anti-hallucination killswitch. Re-enabling it is an eval-gated sub-task (Spike 2), not a pattern-copy.

---

## Metadata

**Analog search scope:** `src/vibemix/state/`, `src/vibemix/coach/`, `src/vibemix/library/`, `src/vibemix/audio/`, `src/vibemix/midi/`, `src/vibemix/platform/`, `src/vibemix/agent/`, `src/vibemix/prompts/`, `src/vibemix/__main__.py`, `tests/library/`, `tests/state/`, `tests/coach/`, `tests/repo/`, `tests/audio/`
**Files read for excerpts:** `track_resolver.py`, `music_state.py`, `event.py`, `evidence_registry.py`, `citation_linter.py`, `rekordbox.py`, `refresh.py` (`_tick_once`), `midi/state.py` (`ControllerState`), `_track_macos.py` (`TrackInfo`), `audio/constants.py`, `coach.py` (`evidence_line`), `dj_cohost.py` (citation strip + screen killswitch), `prompts/matrix.py` (`CITATION_GRAMMAR_BLOCK`), `test_rekordbox.py` (dormancy idiom), `test_repo_scrub.py` (scrub idiom)
**Pattern extraction date:** 2026-05-21
