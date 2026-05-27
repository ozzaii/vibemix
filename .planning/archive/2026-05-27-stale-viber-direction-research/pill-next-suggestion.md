# vibemix — Pill "Next Track" Suggestion (the Pill Advancer)

**Status:** build-ready design (READ-ONLY spec; no code edited).
**Repo:** `/Users/ozai/projects/dj-set-ai` @ branch `live-tuning-or-brain`.
**Goal:** the floating pill suggests the NEXT track from the user's own embedded
library, grounded on what's playing now. Hover the pill → "next: <track>". Pick a
similar track (don't jump energy A→C); later refine by harmonic key + BPM window.

This is the FLAGSHIP feature. It reuses the shipped embedding/vibe-search layer
(gemini-embedding-2, dim 1536, mean-centered cosine, sqlite-vec at
`~/.cache/vibemix/library.db`) and the shipped pill UI. Net-new code is small.

---

## 1. THE PILL TODAY — exact data path

### Where it renders
The pill is the **v5.0 Super-Whisper PRIMARY surface**, a Tauri webview under:

- `tauri/ui/src/pill/index.ts` — entrypoint + DOM view + bus subscription (boots
  on `#pill` element).
- `tauri/ui/src/pill/state-machine.ts` — pure reducer: `idle / listening /
  speaking / expand` modes (`applyFrame`, `tickCollapse`, `PillFrame`, `PillState`).
- `tauri/ui/src/pill/deck-chips.ts` — `renderDeckChips(deckState)`: per-deck
  context chips (title · camelot · key · bpm), honest-`unknown` when unresolved.
- `tauri/ui/src/pill/ws-client.ts` — `connectMascotBus("ws://127.0.0.1:8765")`
  (a copy of the mascot client, decoupled so the mascot-audit fence stays green).
- `tauri/ui/src/pill/waveform.ts`, `pill/pill.css`.

The pill is **consume-only** (no message-send path — T-62-14). It does NOT use
the mascot Three.js renderer.

### How it receives data — `ws_bus` on `127.0.0.1:8765`
`src/vibemix/runtime/ws_bus.py :: ws_broadcast()` is the live emitter (the Tauri
shell spawns the sidecar flag-less → `__main__.main()` which runs `ws_broadcast`).
It binds the ONE socket `127.0.0.1:8765` (`WS_HOST`/`WS_PORT` from
`vibemix.audio`). It emits **two frame kinds on the same socket**:

1. **Flat mascot frame** (~30Hz, NO `type` field, **NOT schema-validated**):
   `ws_bus.py:310-343`. Keys: `music/voice/mic` meters, `audible`, `deck`,
   `phase`, `bpm`, `mood`, `bpm_confidence`, `downbeat_phase`, `beat_phase`,
   `active_genre`, `detected_genre`, `genre_confidence`, `emotion`,
   `reaction_intent`, and (Phase 62, PILL-03) **`deck_state`** =
   `_serialize_deck_state(state)` → `{side: {title, camelot, key, bpm,
   confidence}}`. This is the field the deck-chips render from.
2. **`ipc.session.snapshot`** (~15Hz, typed, schema-validated via
   `ui_bus.validator.validate_message`): `ws_bus.py:373-397`. Meters, bpm, track,
   cohost_status, transcript_delta, midi ribbon.
3. **`cohost-reaction`** (event-driven): the only WRITER frame the pill expands
   on (verbatim AI text + citation chips). Carried via the `CitationIpcShim`
   buffer multiplexed onto the same clients.

### What the pill currently shows
- collapsed dot/label: IDLE / LISTENING / SPEAKING (from `cohost_status` + `voice.rms`).
- expand panel (on `cohost-reaction`): verbatim reaction text + citation strip +
  **deck-context chips** (read from `deck_state`, `index.ts:148-156 readDeckState`).

### Exact path
```
audio/midi/track  →  state_refresh_loop (ONLY writer of MusicState + deck_state)
                  →  ws_broadcast reads MusicState (PURE READ at serialize edge)
                  →  flat 30Hz frame (incl. deck_state)  →  ws:8765
                  →  pill/index.ts reduceFrame()/readDeckState()  →  DOM
```

**Key insight for this feature:** the flat mascot frame is the right carrier. It
is additive, not schema-gated, already read by the pill, and already proves the
pattern (`deck_state` rides it exactly the way `next_suggestion` will).

---

## 2. WHAT'S PLAYING → EMBEDDING (recommended grounded path)

Two candidate seeds:

- **(a) Stored vector of the identified track (PREFERRED — ~free).** The
  now-playing path already resolves a `track_id`: `DeckPoller._resolve_title()`
  (`deck_poller.py:134-176`) maps the now-playing title → `RekordboxLibrary`
  entry → `DeckTrack.track_id` (`deck_poller.py:189`), which lands in
  `MusicState.deck_state.decks[side].track_id` via the single-writer. That
  `track_id`'s 1536-dim vector is ALREADY in `library.db` (folder-ingest /
  Rekordbox import embedded it). Look it up — **zero API cost, zero latency.**
- **(b) On-the-fly embed of recent live master audio (FALLBACK).** Reuse
  `grounding.identify_playing(embedder, store, audio_bytes, ...)`
  (`grounding.py:82`) which embeds the recent buffer (≤80s, under the cap) and
  runs cosine top-1 → returns a `Citation` with `track_id` when cosine ≥ 0.7.
  This costs one embed call per fire; gate it hard.

### Recommendation
Prefer **(a)**. Resolve the current track in this order:
1. `state.deck_state.decks[audible_side].track_id` where `audible_side =
   state.audible_deck` ∈ {A,B}; if "mix"/"none" pick the higher-confidence deck.
2. If a `track_id` resolves AND its vector is in the store → use the **stored
   vector** as the seed (load via `store` backend; see §3 helper).
3. If no `track_id` (folder-only library with no title match, or no Rekordbox) →
   fall back to **(b)** `identify_playing` on the live buffer; use the cited
   `track_id`'s stored vector (still cheap — only the SEED embed costs).
4. If still nothing → emit no suggestion (honest silence; anti-slop).

This keeps the steady state at **~free** (cache hit on the stored seed vector),
spending an embed only when title resolution misses.

---

## 3. SUGGESTION ENGINE — `next_suggestion`

### New module: `src/vibemix/library/next_suggestion.py`
Builds on `library/similar.py :: similar_to` and `store.search_centered` (the
mean-centered anisotropy fix is the DEFAULT — `store.py:63-90`).

```python
# src/vibemix/library/next_suggestion.py   (NEW)
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class NextSuggestion:
    track_id: str
    title: str
    artist: str
    similarity: float        # mean-centered cosine, 4dp
    why: str                 # short grounded reason, e.g. "similar vibe · 8A · 128"
    camelot: str | None      # None unless Rekordbox-resolved (honest-null)
    bpm: float | None        # None unless Rekordbox-resolved
    def to_dict(self) -> dict: ...

def next_suggestion(
    store, library, *,
    seed_vector,                       # np.ndarray (1536,) — the PREFERRED path (cached)
    seed_track_id: str | None,         # to exclude the seed from results
    played_ids: set[str],              # tracks already played this session
    seed_camelot: str | None = None,   # Phase 2 filter input (None → skip)
    seed_bpm: float | None = None,     # Phase 2 filter input (None → skip)
    k: int = 5,
    bpm_window: float = 15.0,
) -> NextSuggestion | None:
    # 1) candidates = store.search_centered(seed_vector, k = k + len(played_ids) + 8)
    #    (over-fetch so post-filters still leave >=1).
    # 2) drop seed_track_id and every id in played_ids.
    # 3) resolve TrackEntry via library.lookup_by_id (rekordbox.py:233) or the
    #    {track_id: TrackEntry} dict; skip ids absent from the library (store/lib skew).
    # 4) Phase-2 post-filter (ONLY when seed_camelot/seed_bpm are present):
    #       keep iff harmonics.compatible(seed_camelot, cand.camelot)  # harmonics.py:196
    #          and (seed_bpm is None or abs(cand.bpm - seed_bpm) <= bpm_window)
    #    Candidates lacking key/bpm PASS the filter (degrade gracefully — never
    #    drop a track for missing metadata; embedding similarity already ranked it).
    # 5) return top survivor as NextSuggestion; None if nothing survives.
```

### Why the seed is a VECTOR (not a track_id like `similar_to`)
`similar_to` re-embeds the seed via `embedder.embed_track` every call. For the
live pill we already have the **stored** seed vector (the cached path, §2a), so
`next_suggestion` takes the vector directly → no embed cost in steady state. A
thin `seed_vector_for_track_id(store, track_id)` helper reads it back from the
backend (`store._backend.load_all()` returns `(ids, vectors)`; index by id).

### Harmonic + BPM filtering — where it slots in
As a **post-filter on the embedding candidates** (step 4 above), NOT a pre-filter:
embedding similarity is the primary ranker (the "similar song, don't jump A→C"
requirement); key/BPM only *refine* the embedding shortlist.

- **Key:** `harmonics.compatible(seed_camelot, cand_camelot)` (`harmonics.py:196`)
  — deterministic Camelot-wheel SAFE verdict (same key, ±1 fifth, +2 energy,
  relative maj/min, ±1 diagonal). LLM never computes keys.
- **BPM:** `abs(cand.bpm - seed.bpm) <= 15` (default; tunable).

### Graceful degradation (HARD requirement)
BPM/key exist **only with a Rekordbox `collection.xml`** — folder-ingest sets
them empty (`DeckTrack.bpm` defaults 0.0; `camelot` None). So:
- **No key/BPM available** (folder-only library, or seed/candidate unresolved):
  **embedding-only** suggestion. `why = "similar vibe"`. `camelot/bpm = None`.
- **Key/BPM present:** harmonic-refined. `why = "similar vibe · 8A · 128"`.
This is exactly the honest-null discipline already enforced in `deck_state`.

---

## 4. WHEN TO ADVANCE — trigger + cooldown

Recompute the suggestion on **`TRACK_CHANGE`** (the seed changed → the "next"
must change). Source: `EventDetector` emits `TRACK_CHANGE`
(`event_detector.py:249-266`) gated on `audible_track_confidence >=
TRACK_CHANGE_MIN_CONFIDENCE`. `TRACK_CHANGE` is already a `TRACK_AWARE_EVENT` for
grounding (`grounding.py:46`), so the now-playing `track_id` is freshest exactly
here.

- **Primary trigger:** `TRACK_CHANGE`. On fire → mark the OLD seed `track_id`
  into `played_ids`, recompute `next_suggestion`, emit the new pill frame.
- **Do NOT trigger on:** `PHASE` / `LAYER_ARRIVAL` / `MIX_MOVE` / `HEARTBEAT`
  (the seed track is unchanged — recomputing would just re-rank the same set and
  spam the wire). `KEY_CLASH`/`TRANSITION_OPPORTUNITY` are unrelated.
- **Cooldown:** add `NEXT_SUGGESTION` to the per-type cooldown bucket; reuse the
  `EventDetector._cooldown_ok` pattern with `MIN_EVENT_GAP_PER_TYPE` (set ~20s)
  so a flappy `audible_track` (re-id thrash) can't recompute more than ~once/20s.
  Independent of the seed change: if `TRACK_CHANGE` is debounced upstream, this
  is belt-and-braces.
- **Boot/first-track:** also compute once when the first confident
  `audible_track` resolves (no prior TRACK_CHANGE), so the pill shows a
  suggestion from the start of the set.

`played_ids` is a **session-scoped `set[str]`** owned alongside the engine (NOT
in `MusicState` — see §6 single-writer). Seed every confident `audible_track`'s
`track_id` into it as tracks play.

---

## 5. INTEGRATION SEAM — the build plan

### New module(s)
- `src/vibemix/library/next_suggestion.py` — `NextSuggestion` dataclass +
  `next_suggestion(...)` + `seed_vector_for_track_id(store, track_id)` helper.
- (optional, Phase 1) `src/vibemix/runtime/suggestion.py` — a tiny
  `SuggestionService` holding `played_ids`, the `store`/`library`/`grounding`
  refs, a `_lock`, and `compute(seed_track_id, audio_bytes) -> NextSuggestion |
  None`. Keeps the engine out of the hot single-writer loop.

### Hook point in the session loop
`__main__.py` already builds `store` + `embedder` + `grounding` lazily at
**`__main__.py:1082-1097`** (only when `library_cache` exists). Construct the
`SuggestionService` there using the SAME `_library_store` / `deck_library`
(`__main__.py:1044-1049`). Then drive it from the coach path:

- **Trigger:** `coach_loop` (`runtime/coach.py:84`) already polls `MusicState` at
  10Hz and runs `EventDetector.detect(...)`. On a `TRACK_CHANGE` event (and on
  first confident track), call `suggestion_service.compute(...)` in an executor
  (`loop.run_in_executor` — store/embed is sync, must not block the loop), then
  publish the resulting frame.
- **Publish:** the cleanest carrier is the **flat mascot frame**. Add an optional
  `suggestion_holder` ref (a 1-slot box, e.g. `list` or a small object with a
  lock) that `ws_broadcast` reads at the serialize edge and merges into the flat
  frame as `next_suggestion` (mirrors how `deck_state` rides the frame). The
  coach computes → writes the holder; `ws_broadcast` reads it (PURE READ).
  Alternatively emit a one-shot typed frame; the flat-frame route is preferred
  (no schema change, already-subscribed pill).

### New ws_bus message shape (on the flat 30Hz frame)
```jsonc
// additive field on the flat mascot frame (ws_bus.py:310-343)
"next_suggestion": {
  "track_id": "12345",
  "title": "Rhadoo - Untitled",
  "artist": "Rhadoo",
  "similarity": 0.83,
  "why": "similar vibe · 8A · 128",   // or just "similar vibe" when no key/bpm
  "camelot": "8A",                     // null when not Rekordbox-resolved
  "bpm": 128.0                         // null when not Rekordbox-resolved
}                                      // null/absent when no suggestion (honest)
```
Honest-null discipline: absent / `null` when there is no grounded suggestion —
NEVER a fabricated track. Only `track_id`s present in `library.db` ever appear.

### Pill UI change (render + hover)
- `pill/index.ts`: add `readNextSuggestion(msg)` (mirror `readDeckState`,
  `index.ts:148`) — read `msg.next_suggestion ?? null`, hold latest on the view
  (replace-not-merge; `null`/absent → keep last, `{}`-clear semantics if desired).
- Add a `next-suggestion` chip/row to the COLLAPSED pill (or a small "↑ next"
  affordance) so the suggestion is glanceable. Render `title` via `textContent`
  ONLY (T-62-11 trust boundary — never innerHTML from wire data).
- **Hover:** on pointer-enter of the pill (or the next-chip), expand a compact
  card showing `title — artist`, `why`, and (when present) `camelot · bpm`. Reuse
  the expand panel mount; gate on a `next_suggestion`-present view flag so hover
  shows the suggestion even when there's no active `cohost-reaction`.
- Add `pill/next-suggestion.ts` (pure renderer, unit-testable like
  `deck-chips.ts`) + a test in `pill/`.

### Phasing
- **Phase 1 — embedding-only suggestion in the pill.** `next_suggestion.py`
  (vector seed + `played_ids` + `store.search_centered`), `SuggestionService`,
  `TRACK_CHANGE` hook in `coach_loop`, `next_suggestion` flat-frame field, pill
  read + collapsed chip + hover card. `why = "similar vibe"`. No key/BPM filter.
  Works for folder-only libraries. **This is the shippable flagship slice.**
- **Phase 2 — harmonic/BPM refine.** Wire `seed_camelot`/`seed_bpm` from
  `deck_state.decks[side]` into `next_suggestion` post-filter
  (`harmonics.compatible` + ±15 BPM). `why` gains `· 8A · 128`. Active only when
  a Rekordbox collection is imported (degrades to Phase-1 behavior otherwise).
- **Phase 3 — "enter on hot cue X".** Use `library/cue_detect.py` +
  Rekordbox `CuePoint`/`TrackEntry.cues` to suggest the entry cue on the
  candidate (e.g. "enter on hot cue 2"). Extends the `why` / card. Out of scope
  for the first build.

---

## 6. RISKS & INVARIANTS

- **Single-writer (cardinal invariant #1):** ONLY `state_refresh_loop` writes
  `MusicState`. **Do NOT store the suggestion or `played_ids` in `MusicState`.**
  Keep them in the `SuggestionService` (coach-loop owned) and publish via a
  dedicated `suggestion_holder` box that `ws_broadcast` PURE-READS at the
  serialize edge — exactly the read-only discipline `_serialize_deck_state`
  follows (`ws_bus.py:71-112`). No new writer of `MusicState`.
- **In-flight Gemini gate:** `coach_loop` enforces a single in-flight generation
  (`trigger_state["in_flight"]`). The suggestion compute must NOT touch that gate
  and must NOT block the loop — run the (sync) store/embed work in
  `loop.run_in_executor`. In the **preferred** path (cached stored vector) there
  is NO Gemini call at all, so no interaction with the gate.
- **Cost:** steady state = stored-vector lookup = **~free** (no API). An embed
  fires only on the fallback path (title didn't resolve) via
  `grounding.identify_playing`, and only on `TRACK_CHANGE` (event-gated, the same
  cost contract as grounding: ~€27/mo @ 1000 DAU per `grounding.py` docstring).
  Prefer the cached vector everywhere; never embed per-frame.
- **One-socket (cardinal invariant #4):** the suggestion rides the EXISTING
  `127.0.0.1:8765` flat frame. Bind NO new listener. Debrief stays on 8766.
- **Anti-slop / citation grounding (#2, #3):** only `track_id`s that exist in
  `library.db` are ever suggested; honest-`null` when nothing grounds. No
  fabricated tracks, no key/BPM invented (Camelot is deterministic; LLM never
  computes it). The pill renders wire data via `textContent` only.
- **Schema:** the flat mascot frame is NOT schema-validated (unlike
  `ipc.session.snapshot`), so adding `next_suggestion` to it needs no
  `messages.schema.json` change. If a typed `ipc.*` frame is chosen instead, the
  schema + validator (`ui_bus/validator.py`) MUST be extended first — extra work,
  hence flat-frame is recommended.
- **Store/library skew:** a `track_id` in the store but absent from the library
  (post-reimport) must be skipped, not rendered (the `vibe_search`/`similar_to`
  paths already do this — mirror it).
- **Privacy:** unaffected — this reads the user's own music library
  (`~/.cache/vibemix/library.db`) and `~/Music`, none of the off-limits
  Hermes/LM-Studio transcript paths.
```
