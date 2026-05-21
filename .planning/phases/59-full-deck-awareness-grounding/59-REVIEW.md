---
phase: 59-full-deck-awareness-grounding
reviewed: 2026-05-21T14:11:30Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - src/vibemix/state/harmonics.py
  - src/vibemix/state/deck_state.py
  - src/vibemix/state/deck_poller.py
  - src/vibemix/state/deck_vision.py
  - src/vibemix/state/music_state.py
  - src/vibemix/state/refresh.py
  - src/vibemix/state/evidence_registry.py
  - src/vibemix/state/event.py
  - src/vibemix/coach/citation_linter.py
  - src/vibemix/agent/dj_cohost.py
  - eval/deck_vision/run_eval.py
findings:
  critical: 0
  warning: 5
  info: 4
  total: 9
status: issues_found
---

# Phase 59: Code Review Report

**Reviewed:** 2026-05-21T14:11:30Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 59 (Full Deck Awareness + Grounding) is solid work. The four guardrails the prompt
flagged all hold up under adversarial reading:

- **Single-writer invariant:** Verified by grep — `state.deck_state.decks = ...` appears in
  exactly ONE place (`refresh.py:481`), inside `with state._lock:`. The poller writes only its
  own holder; `_tick_once` is the sole copier. PASS.
- **Anti-slop key contract:** `key:` is correctly existence-only (absent from
  `_TIME_KEYED_SOURCES` in `citation_linter.py`, registered as the full `A:8A` body in
  `refresh.py`, gated on `DECK_CITE_MIN_CONF` + non-empty `camelot`). `to_camelot` honestly
  degrades to `None` on junk and never raises — verified against enharmonics, casing, and
  Camelot/open-key collisions. PASS.
- **v4 vision killswitch:** `dj_cohost.py:571 screen_jpeg = None` is UNTOUCHED; the reaction
  path append at line 698 stays gated. `deck_vision.py` is a separate, structured, non-streaming,
  default-OFF call. PASS.
- **Gemini-only:** `deck_vision.py` imports only `google.genai` (local import) + stdlib. No
  openai/anthropic. PASS.
- **Thread-safe read-only poller:** Own `threading.Lock`, `snapshot()` returns deep copies via
  `replace_decktrack`, `poll_once` swallows all exceptions. Mirrors `TrackInfo` discipline. PASS.

96 Phase-59 deck tests pass (`test_deck_poller`, `test_deck_vision`, `test_harmonics`,
`test_refresh_deck`). No BLOCKERs found. Findings below are robustness/maintainability concerns
and one documentation/behavior mismatch worth confirming.

## Warnings

### WR-01: `_title_index` cache is never invalidated on library reload

**File:** `src/vibemix/state/deck_poller.py:117,138-145`
**Issue:** The case-folded title→track_id index is built once (`if self._title_index is None`)
and cached for the poller's lifetime, keyed off the FIRST `self._library.tracks` read. If the
user re-imports a different `collection.xml` mid-session (`RekordboxLibrary.load_xml` overwrites
`self.tracks` in place — see `rekordbox.py:138,156`), the poller keeps resolving titles against
the STALE index, silently mis-attributing track_ids/keys to the wrong tracks. A wrong track_id
feeds a `[track:<id>]` citation and a wrong `camelot` feeds a `[key:A:8A]` citation — a
false-confident grounding error, the exact hallucination class this phase closes.
**Fix:** Invalidate the index when the underlying library object changes. Cheapest robust
approach is to key the cache on library identity/version:
```python
# in __init__: self._index_for_library_id: int | None = None
# in _resolve_title, before using the cache:
if self._title_index is None or id(self._library) != self._index_for_library_id or \
        len(self._title_index) != len(tracks):
    self._title_index = {e.title.casefold(): tid for tid, e in tracks.items() if e.title}
    self._index_for_library_id = id(self._library)
```
A `len()` guard alone catches re-imports that change track count; pairing with `id()` (or a
library `version`/mtime field) covers same-count swaps. Low-likelihood in v1 (library loads
once at startup) but it is a correctness gap with a hallucination consequence.

### WR-02: Confidence-elevation comment contradicts the code (weak attribution is raised to the citation floor)

**File:** `src/vibemix/state/deck_poller.py:231-234`
**Issue:** The comment says "Confidence is bounded by the attribution confidence so a
weakly-attributed deck never cites at full XML trust." The code is
`conf = max(XML_CONF_FLOOR, min(1.0, deck_conf))`. `derive_audible_deck` can return a
dominant-deck confidence as low as `0.4` (`track_resolver.py:88-89`). `max(0.6, 0.4) == 0.6`,
which RAISES a 0.4-attributed deck to 0.6 — clearing `DECK_CITE_MIN_CONF=0.6` and making it
citable. The comment describes a `min`-style cap; the code does the opposite (a floor). This is
asserted-as-intended by `test_deck_poller.py:145,221` (`confidence >= XML_CONF_FLOOR`), so it is
NOT a behavior bug — but the misleading comment will cause a future maintainer to "fix" the line
toward `min(...)` and break the cite gate, or to trust that weak attribution stays sub-floor when
it does not.
**Fix:** Rewrite the comment to match reality, e.g. "An XML tag is high-trust regardless of
attribution strength, so a matched deck always clears the citation floor; attribution confidence
only caps the UPPER bound (a weak attribution never reaches 1.0)." If the intent is genuinely to
let weak attribution stay sub-floor and uncitable, change the formula and the two test
assertions instead — but confirm with the design before touching the gate.

### WR-03: Hand-rolled `_DECK_READ_SCHEMA` dict diverges from the repo's Pydantic-`response_schema` pattern and may be silently ignored by the SDK

**File:** `src/vibemix/state/deck_vision.py:76-92,186-190`
**Issue:** Every other structured Gemini call in the codebase passes a Pydantic model as
`response_schema` (`debrief/drills.py:223-224` → `Drills`). This module passes a raw dict using
OpenAPI-style `"nullable": True`. Depending on the installed `google-genai` SDK version, a plain
dict with `nullable` keys may be partially or fully ignored (the SDK validates/coerces schemas;
`nullable` is not the field-presence mechanism the genai schema layer expects — it uses optional
fields / `Optional[...]`). If the schema is dropped, the model falls back to free-text JSON,
weakening guardrail ② ("STRUCTURED output ... closes the free-text hallucination class"). The
null-defensive parse (`_parse`) still protects deck-state, so this is not a correctness BLOCKER
— but it erodes the central safety claim of the vision leg.
**Fix:** Mirror the established pattern — define a Pydantic model (e.g. `class DeckRead(BaseModel)`
with `Optional[str]`/`Optional[float]` fields and a `decks: list[DeckSlot]`) and pass the class as
`response_schema`, as `debrief/drills.py` does. Validate the schema is actually honored against
the SDK version pinned in `pyproject.toml` before the eval gate (Task 3) measures accuracy —
otherwise the eval scores a different (unstructured) call than what ships.

### WR-04: `replace_decktrack` is a field-by-field hand copy that silently drops new `DeckTrack` fields

**File:** `src/vibemix/state/deck_poller.py:317-331`
**Issue:** `replace_decktrack` enumerates all 10 `DeckTrack` fields by hand. If a future change
adds a field to `DeckTrack` (e.g. an `artist` or `analyzed_at`), the copy silently omits it —
the snapshot returns a `DeckTrack` with the new field at its default, NOT the holder's value.
This is a classic copy-drift bug that the type checker will not catch (the call still type-checks).
Since the snapshot is the boundary the single-writer reads from, a dropped field becomes a silent
data-loss-on-read.
**Fix:** Use `dataclasses.replace(dt)` (a true field-complete shallow copy) — `DeckTrack` is a
non-frozen dataclass, all fields are immutable scalars, so `replace(dt)` with no overrides yields
exactly the desired copy and stays correct as fields are added:
```python
from dataclasses import replace
def replace_decktrack(dt: DeckTrack) -> DeckTrack:
    return replace(dt)
```

### WR-05: Vision leg can never run today — `_latest_screen_jpeg` is hard-wired to return `None`

**File:** `src/vibemix/state/deck_poller.py:266-280`
**Issue:** Even when `vision_enabled=True` and a `vision_reader` is injected, `_maybe_apply_vision`
calls `self._latest_screen_jpeg()` which unconditionally `return None`, so the early `if jpeg is
None: return` short-circuits before any read. The entire vision-apply path is therefore dead at
runtime regardless of the gate. This is documented as intentional ("dormant until a screen source
is wired at the eval gate, Task 3"), so it is not a defect against the current plan — but it means
the `vision_enabled` flag is currently a no-op and the path has NO runtime coverage. A reviewer or
future dev flipping `vision_enabled` expecting vision to work will get silent nothing, not an
error.
**Fix:** Either (a) raise/log a clear "vision enabled but no screen source wired" diagnostic when
`vision_enabled and self._latest_screen_jpeg() is None`, so the no-op is observable; or (b) leave
as-is but add an assertion in the eval-gate wiring task that screen-source injection lands
together with `vision_enabled=True`. Track explicitly so the flag and its data source ship as a
pair.

## Info

### IN-01: `defaultdict` factory in `run_eval` is dead — `setdefault` never triggers it

**File:** `eval/deck_vision/run_eval.py:209,212`
**Issue:** `scores: dict[str, AppScore] = defaultdict(lambda: AppScore(app="unknown"))` is created,
but the only insertions use `scores.setdefault(app, AppScore(app=app))`, which never invokes the
defaultdict factory (and would produce a wrong `app="unknown"` label if it did). The defaultdict
behavior is unused and slightly misleading.
**Fix:** Use a plain `dict` (`scores: dict[str, AppScore] = {}`) since `setdefault` already handles
the missing-key case with the correct `app` label.

### IN-02: `to_camelot` rejects lowercase musical notation (e.g. `"am"`) — fine for XML, lossy for vision

**File:** `src/vibemix/state/harmonics.py:103`
**Issue:** Musical-notation matching is case-sensitive (`s in _MUSICAL_TO_CAMELOT`), so a vision
read returning `"am"` / `"f#m"` (lowercase) degrades to `None` (honest unknown) rather than `8A`/
`11A`. This is correct for Rekordbox XML (proper-case `"Am"`) and the honest-unknown fallback is
safe, but vision badges in mixed case lose recoverable keys. Note for the eval gate: if real
screenshots show lowercase keys, accuracy will under-report.
**Fix:** Optional — if the vision eval shows lowercase key reads, add a case-folded musical lookup
(`_MUSICAL_TO_CAMELOT_CF = {k.casefold(): v ...}`) consulted after the exact match. Defer until the
eval corpus shows it matters; current behavior is safe (no false key).

### IN-03: `_build_decks` reads `track_info.snapshot()` title before the `cs is None` guard

**File:** `src/vibemix/state/deck_poller.py:210-219`
**Issue:** The now-playing title is fetched (lines 210-213) before the `if cs is None: return decks`
guard (line 218). When there is no controller, the title read is wasted work. Harmless (no
correctness impact, `snapshot()` is cheap and exception-swallowing) but slightly out of order.
**Fix:** Move the title read below the `cs is None` guard. Minor.

### IN-04: `EVENT_PRIORITY` `KEY_CLASH`/`TRANSITION_OPPORTUNITY` entries are plumbing-only and currently unreachable

**File:** `src/vibemix/state/event.py:44-49`
**Issue:** The two Phase 59 event types are registered in `EVENT_PRIORITY` but no detector emits
them yet (firing logic is Phase 60). This is documented and intentional (pre-registering avoids the
`.get(type, 0)` priority-0 fallback when Phase 60 lands). No defect — flagged only so the unused
entries are not mistaken for dead code to delete.
**Fix:** None needed. Keep as-is; the inline comment already explains the intent.

---

_Reviewed: 2026-05-21T14:11:30Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
