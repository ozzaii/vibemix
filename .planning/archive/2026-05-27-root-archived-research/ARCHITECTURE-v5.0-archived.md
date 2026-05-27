# Architecture Research — v5.0 "The Useful Cut" Integration Design

**Domain:** Local AI DJ co-host (mature codebase; subsequent-milestone integration)
**Researched:** 2026-05-21
**Confidence:** HIGH (read against real current files on branch `live-tuning-or-brain`)

> This is an INTEGRATION design, not a greenfield architecture. Every recommendation
> below is anchored to a real file/line in `src/vibemix/` or `tauri/`. The cardinal
> invariants of the existing system that v5.0 MUST NOT break:
>
> 1. **Single-writer rule** — `state_refresh_loop._tick_once` (`state/refresh.py`) is the
>    ONLY writer to `MusicState`. `EventDetector` + `AICoach` are read-only consumers.
>    The lone locked exception is `coach_loop`'s `state.last_kaan_spoke_at` write.
> 2. **Anti-slop citation grounding** — `EvidenceRegistry` (7 sources: `ev/aud/midi/track/screen/mix/tend`)
>    is the runtime anchor; `CitationLinter` (`coach/citation_linter.py`) does a binary
>    response-level strip against an `EvidenceRegistry.snapshot()`. New evidence must be
>    *written to the registry* before the LLM can be allowed to cite it.
> 3. **"Trust the audio"** — `AICoach.evidence_line` deliberately omits a `phase=` field; ears
>    are the referee, evidence is grounded context. New deck-state fields must follow the
>    same discipline (no fabricated key/transition claims).
> 4. **One socket** — the live runtime serves mascot frame + `ipc.session.snapshot` +
>    `ipc.session.cohost-reaction` + `ipc.session.citation` + `ipc.session.overlay-highlight`
>    ALL on `ws://127.0.0.1:8765` (`runtime/ws_bus.py` `ws_broadcast`). New UI consumes the
>    SAME socket — no second port.

---

## Standard Architecture (current, annotated with v5.0 deltas)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  TAURI SHELL (Rust)            main.rs .setup() builds windows             │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐    │
│  │ main     │  │ mascot   │  │ debrief      │  │ ★ pill (NEW)         │    │
│  │ (session)│  │(opt-in)  │  │ (:8766)      │  │ transparent/on-top   │    │
│  │ index.htm│  │mascot.htm│  │ debrief.html │  │ pill.html  PRIMARY   │    │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  └─────────┬────────────┘    │
│       │ ws:8765     │ ws:8765       │ ws:8766            │ ws:8765         │
└───────┼─────────────┼───────────────┼────────────────────┼─────────────────┘
        └─────────────┴───────────────────────────────────┘
                                  │  (one socket, many frame types)
┌─────────────────────────────────┴──────────────────────────────────────────┐
│  PYTHON SIDECAR — runtime                                                    │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │ ws_broadcast (runtime/ws_bus.py)  30Hz mascot frame + 15Hz snapshot  │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│  ┌──────────────┐   ┌──────────────────┐   ┌────────────────────────────┐  │
│  │ state_refresh│──▶│ MusicState       │◀──│ EventDetector (read-only)  │  │
│  │ _loop (10Hz, │   │ (single source)  │   │  ★ + deck detectors (NEW)  │  │
│  │ SOLE WRITER) │   │ ★ + DeckState    │   └─────────────┬──────────────┘  │
│  └──────┬───────┘   │   (NEW, embedded)│                 │ Event           │
│  ★ deck │poller     └──────────────────┘                 ▼                  │
│         ▼                  │ snapshot                ┌──────────┐            │
│  ┌──────────────┐          ▼                         │coach_loop│            │
│  │EvidenceRegist│◀── writes mix/track obs      ┌────▶│          │            │
│  │ + deck keys  │     (single-writer batch)    │     └────┬─────┘            │
│  └──────┬───────┘                              │          │ generate_reply  │
│         │ snapshot()                           │          ▼                  │
│         ▼                              ┌────────┴───┐  ┌──────────────────┐  │
│  ┌──────────────┐  build_prompt        │ AICoach    │  │ DJCoHostAgent    │  │
│  │CitationLinter│◀─────────────────────│ + deck task│─▶│ .llm_node        │  │
│  │ (binary strip│   (cited deck-state) │ (NEW tasks)│  │ OR/Gemini cascade│  │
│  └──────────────┘                      └────────────┘  └──────────────────┘  │
│                       prompts/matrix.py (★ persona refactor) ────────────────│
└──────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities (NEW vs MODIFIED)

| Component | File | NEW/MODIFIED | v5.0 role |
|-----------|------|--------------|-----------|
| `DeckState` model | `state/deck_state.py` | **NEW** | Session-wide per-deck track facts (key/BPM/energy); embedded in `MusicState` |
| Deck-state poller | `state/deck_poller.py` + platform shim | **NEW** | Reads chosen source (see STACK/FEASIBILITY); feeds `_tick_once` only |
| `_tick_once` | `state/refresh.py` | **MODIFIED** | Writes `DeckState` + `mix`/`track` deck observations inside the single-writer lock batch |
| Camelot/key helpers | `state/harmonics.py` | **NEW** | Pure functions: key→Camelot, clash classification; no I/O, no state |
| New event types | `state/event.py` | **MODIFIED** | `TRANSITION_OPPORTUNITY`, `KEY_CLASH` added to `EVENT_PRIORITY` |
| Deck event detectors | inlined in `state/event_detector.py` | **MODIFIED** | Read `state.deck_state` diffs; emit typed events |
| `AICoach` tasks | `state/coach.py` | **MODIFIED** | `task_for_event` arms for the 2 new events; `evidence_line` gains a deck block |
| Persona cells | `prompts/matrix.py` | **MODIFIED** | Extend the in-flight COACH_* / closing-block work for actionable feedback |
| `EvidenceRegistry` | `state/evidence_registry.py` | **UNCHANGED API** | `mix`/`track` sources already exist; new keys land via `write()` |
| `ws_broadcast` | `runtime/ws_bus.py` | **MODIFIED** | Add deck-state fields to `ipc.session.snapshot` (additive) |
| Pill window | `tauri/src-tauri/src/pill_window.rs` | **NEW** | Transparent/on-top/draggable WebviewWindow builder + geometry persist |
| Pill UI | `tauri/ui/pill.html` + `src/pill/` | **NEW** | Subscribes ws:8765, renders reaction + meters + deck chips |
| Surface toggle | `config.rs` + `tray.rs` + Settings | **MODIFIED** | `primary_surface: "pill"|"mascot"|"none"` persisted state |

---

## A) DECK-STATE MODEL

### Where it sits relative to `MusicState` / `track_resolver.py`

**Decision: a separate `DeckState` dataclass, embedded as a field of `MusicState`.**

`MusicState` (`state/music_state.py`) describes the *audible mix as one signal* — `rms`, `bands`,
`bpm`, `audible_deck`, `audible_track`. It is a per-tick snapshot of "what I am hearing right now."
v5.0 needs the orthogonal axis: "what is *loaded on each deck*, even the silent/cued one." That is a
different lifecycle (track facts persist across the whole load→cue→play→eject cycle, not just the
audible window), so it must NOT be flattened into `MusicState`'s existing single-track fields.

```python
# state/deck_state.py — NEW
@dataclass
class DeckTrack:
    title: str | None = None      # resolved track label (source-dependent)
    track_id: str | None = None   # rekordbox/library id when resolvable — feeds [track:<id>] citations
    bpm: float = 0.0              # from source metadata, NOT audio autocorr
    key: str | None = None        # raw key tag ("8A", "Am", "F#min") as the source gives it
    camelot: str | None = None    # normalized Camelot ("8A") via harmonics.to_camelot()
    energy: int | None = None     # 1..10 if the source exposes it (rekordbox), else None
    loaded_at: float = 0.0        # session-relative load time
    confidence: float = 0.0       # 0..1 — how sure we are this deck holds this track
    source: str = "unknown"       # "rekordbox" | "screen_ocr" | "nowplaying" | "audio" | "manual"

@dataclass
class DeckState:
    decks: dict[str, DeckTrack] = field(default_factory=dict)  # {"A": DeckTrack, "B": ...}
    updated_at: float = 0.0
```

Then in `MusicState` (additive, default-empty so golden-equivalence holds — same discipline as the
Phase 17/31/52 additive fields already in `music_state.py`):

```python
    # v5.0 — session-wide deck awareness. Single-writer (state_refresh_loop only).
    deck_state: DeckState = field(default_factory=DeckState)
```

**Why embed rather than a sibling object passed separately:** every existing consumer
(`EventDetector.detect(state, ...)`, `AICoach.build_prompt(ev)` where `ev.state` is the `MusicState`,
`ws_broadcast`) already receives `MusicState`. Embedding means zero signature churn on the read side,
and the single `with state._lock:` batch in `_tick_once` keeps deck writes consistent with the rest of
the snapshot. A sibling object would need its own lock and would let readers observe a torn view
(deck-A updated, audible_track not yet).

`track_resolver.py` stays as-is for the *audible* inference (`derive_audible_deck` /
`derive_audible_track`). v5.0 adds a parallel resolver for the *loaded* set (the poller below). The two
reconcile naturally: the existing `audible_deck` tells you which `DeckState.decks[X]` is sounding now.

### The deck-state poller — single-writer compliance

The data source is **unresolved** (PROJECT.md flags it; see FEASIBILITY.md for the
pyrekordbox/screen-OCR/nowplaying/audio recommendation). Whatever it is, the integration shape is
fixed by the single-writer rule:

- The poller is a **read-only producer** running on its own cadence — likely a `loop.run_in_executor`
  background task for blocking file/DB reads, mirroring how track polling and screen capture are
  offloaded today (see `refresh.py` TYPE_CHECKING note on `TrackInfo`/`ControllerState` being external
  threads). It writes findings into a **plain holder object** it owns (`DeckSource.snapshot() ->
  dict[str, DeckTrack]`), exactly like `ControllerState.deck_snapshot()` and `TrackInfo.snapshot()` do.
- `_tick_once` is the ONLY thing that copies that holder into `MusicState.deck_state`, inside the
  existing `with state._lock:` block. This mirrors the established pattern: `_tick_once` already calls
  `controller_state.deck_snapshot()` + `track_info.snapshot()` and assigns the results into `MusicState`
  under the lock (refresh.py ~427-460). The deck poller is simply the *third* such external source.

```python
# refresh.py _tick_once — inside `with state._lock:`, alongside the controller/track block
    deck_snap = deck_source.snapshot()        # read-only producer, no lock contention
    for dt in deck_snap.values():
        dt.camelot = harmonics.to_camelot(dt.key)   # pure fn, µs cost — safe inside the lock
    state.deck_state.decks = deck_snap
    state.deck_state.updated_at = now
```

Cardinal rule intact: `EventDetector` and `AICoach` read `state.deck_state` and never write it. No new
lock, no async-safe queue — the established `threading.Lock` boundary already covers it.

### New `Event` types + cooldowns

Add to `EVENT_PRIORITY` in `state/event.py` (the reserved `DROP` slot shows additions are expected here):

```python
    "KEY_CLASH": 7,              # tie with TRACK_CHANGE — a clashing overlay is a "react now"
    "TRANSITION_OPPORTUNITY": 5, # tie with MIX_MOVE — structural, not urgent
```

Add cooldowns to `MIN_EVENT_GAP_PER_TYPE` in `audio/constants.py`:

- `KEY_CLASH` — **long gap (~25-30s)**. A clash persists while both decks play; firing once and
  re-arming only after the clash *clears and recurs* prevents nagging. The detector also gates on the
  *onset* of the clash (both decks newly audible together), not steady-state.
- `TRANSITION_OPPORTUNITY` — **medium gap (~20s)**. Fires when deck B is loaded+cued while deck A is in
  a late-phase window (the moment a blend *could* start), not continuously.

Both inherit the global `EVENT_GLOBAL_MIN_GAP` floor via `_cooldown_ok` — no change to the gate logic.

### Detector wiring (read-only, diff-based)

Two new detectors, **inlined in `event_detector.py`** between the MIX_MOVE block and the genre-chain
loop (so a deck event beats HEARTBEAT but yields to track/phase changes). Inlined rather than
genre-chain detectors because they read `state.deck_state` (not raw audio), so they don't need the
`audio_buf` thread-through that the chain detectors take.

- `KEY_CLASH`: when two decks are simultaneously audible (`audible_deck == "mix"`, or both deck weights
  high) AND both have a resolved `camelot`, call `harmonics.is_clash(a.camelot, b.camelot)`. Camelot
  compatibility = same number (energy boost), ±1 number same letter, or same number opposite letter;
  anything else with strong tonal content = clash. Fire only on the *onset* of the mix into the clash,
  with the long cooldown.
- `TRANSITION_OPPORTUNITY`: when a *new* track is loaded+cued on the silent deck (`DeckTrack.confidence`
  high, deck not in `audible_deck`) while the audible deck is in a `build`/`peak`/late-`groove` phase.
  Carries `extra={"from_deck","to_deck","from_camelot","to_camelot","harmonic":"compatible|clash|neutral"}`.

### How `AICoach` builds grounded, cited deck feedback — and what the linter checks

This is the load-bearing anti-slop piece. Three coordinated changes:

1. **Register the deck observations** so they become citable. In `_tick_once`, when a deck's track
   resolves with confidence, write to the registry inside the same locked batch (mirrors the existing
   change-only `evidence_registry.write("mix", f"audible_deck=...", t)` writes at refresh.py ~441-446):

   ```python
   if evidence_registry is not None and dt.confidence >= DECK_CITE_MIN_CONF:
       evidence_registry.write("mix", f"deck_{side}_track={dt.title}", t_session)
       if dt.camelot:
           evidence_registry.write("mix", f"deck_{side}_key={dt.camelot}", t_session)
       if dt.track_id:
           evidence_registry.write("track", dt.track_id, t_session)   # resolves [track:<id>]
   ```

   The `mix` and `track` sources ALREADY exist in `EVIDENCE_SOURCES`, and the linter treats both as
   existence-only (no `@t`) in `citation_linter._validate_atom`. `EvidenceRegistry.register_library`
   (Plan 25-02) already registers the full rekordbox collection as `track:<id>` observations, so
   `[track:<id>]` citations resolve against the real collection. **No new evidence source, no linter
   grammar change required.** The `KEY_CLASH`/`TRANSITION_OPPORTUNITY` event fires write `[ev:<TYPE>@<t>]`
   via the existing `_fire` registry hook.

2. **Surface deck-state in `evidence_line`** (`state/coach.py`). Add a deck block to the full
   `evidence_line` (NOT the compact diet one — deck feedback is substantive, never an ack). Keep the
   "trust the audio" discipline: present deck facts as *grounded context the LLM may cite*, never as a
   directive to invent. Example field:

   ```
   decks[A='Track X' 8A 128bpm | B='Track Y' 9A 128bpm | harmonic=compatible]
   ```

   Below a confidence floor, print `decks=unknown` exactly like the existing `track=unknown` pattern, so
   the persona's "don't name what you can't confirm" rule extends naturally.

3. **Arm `task_for_event`** for the two new types with prescriptive-but-cited instructions:

   - `KEY_CLASH`: *"Decks A and B are both audible and their keys clash (cite `[mix:deck_A_key=8A]`,
     `[mix:deck_B_key=2A]`). Name the clash and the fix — EQ out the clashing element, or ride a quick
     blend through. Cite the deck-key evidence; if you can't, say nothing."*
   - `TRANSITION_OPPORTUNITY`: *"Deck B (`[mix:deck_B_track=...]`) is cued and harmonically compatible
     (`[mix:deck_B_key=9A]`) with what's playing. Call the blend: where to bring it in, how long, what
     to watch. Cite the deck evidence."*

**Linter contract:** when wired (`DJCoHostAgent._linter_wired`), a prescriptive deck reaction that names
a track/key the registry never observed gets *stripped* — the binary response-level gate in
`citation_linter.check` catches an invented `[mix:deck_A_key=12B]` because `12B` won't be in the
snapshot's `mix` keys. This is exactly the grounding guarantee v5.0 wants: **you cannot give actionable
harmonic feedback unless the deck-state actually saw the keys.** The citation strip (`_build_citation_strip`
in `dj_cohost.py`) already turns `mix:`/`ev:` atoms into UI chips — deck-clash chips fall out for free.

---

## B) FEEDBACK PERSONA REFACTOR

**Architecturally light — it lives entirely in `prompts/matrix.py` + `state/coach.py`, both already
heavily touched by the uncommitted `live-tuning-or-brain` work.** The job is to *extend*, not duplicate.

### Where the voice config lives (verified)

- **System-instruction persona** = the 6-cell matrix in `prompts/matrix.py`, dispatched by
  `build_system_instruction(skill, mode, mood)`. The actionable-feedback voice is the
  `COACH_BEGINNER/INTERMEDIATE/PRO` cells (`mode == "coach"`). The in-flight branch already:
  - rewrote `COACH_PRO` into a deserved-critique+fix / nudge-forward / props structure (matrix.py ~499-540),
  - added `COACH_CLOSING_BLOCK` ("BE A REAL COACH", appended LAST for recency; lifts the old "never name
    a fader" ban) and `COACH_TAG_DSL_BLOCK` (calm-only TTS tags),
  - gated both behind `mode_norm == "coach"` in `build_system_instruction` (matrix.py ~786-799).
- **Per-event task tail** = `AICoach.task_for_event` in `state/coach.py` (the MIX_MOVE task already
  carries the "give the fix, name the EQ/filter if it's worth flagging" actionable language — 2026-05-21).
- **Runtime selection** = `DJCoHostAgent._resolve_prompt_cell` reads `VIBEMIX_SKILL_LEVEL` /
  `VIBEMIX_MODE` / `VIBEMIX_MOOD` env vars (dj_cohost.py ~234-254); `MusicState.mood` overrides at
  agent-build time.
- **Brain/TTS path** = `or_client`/`or_model` kwargs on `DJCoHostAgent` (OpenRouter brain) +
  `agent/tts_chain.py`. The persona cell is passed as the system message on the OR path
  (`self._prompt_body`), so persona changes flow through *both* the direct-genai and OpenRouter paths
  with no extra work.

### How to extend (not duplicate) the in-flight work

1. **Build the v5.0 deck-aware feedback ON TOP of the existing COACH_PRO/INTERMEDIATE cells** — add a
   deck-feedback paragraph (transition mechanics + harmonic vocabulary) to those cells, guarded by the
   same `mode == "coach"` path. Do NOT add a new "coach2"/"feedback" mode; `_CELLS` + `_VALID_MODES`
   are the env-var/Settings contract — a new mode breaks that surface.
2. **The new `task_for_event` arms for KEY_CLASH / TRANSITION_OPPORTUNITY (Part A)** are where the
   prescriptive deck instructions live — the per-event layer, the right home for "what to say about
   *this* deck moment," leaving the cell as the persona substrate.
3. **Keep the anti-slop substrate intact.** `_ANTI_SLOP_FOOTER`, `CITATION_GRAMMAR_BLOCK`,
   `IM_LISTENING_FRAGMENT`, and `COACH_CLOSING_BLOCK` all append via `build_system_instruction` flags —
   the deck-feedback paragraph goes INSIDE the cell body (before those appends) so the citation grammar
   and fail-soft rule still land last. Deck vocabulary reuses the citation grammar already taught
   (`[mix:deck_A_key=8A]`) — no new grammar.

### Staying anti-slop-compliant while prescriptive

The risk with "actionable feedback" is the model inventing a fix for a problem it can't observe (e.g.
"pull deck B's low EQ" when it never saw deck B's key or a clash). Mitigations — all already in machinery:

- **Cite the observed deck-state/event.** The prescriptive task tells the model to cite the deck-key
  evidence; the `CitationLinter` strips the turn if the cited key isn't in the registry snapshot. The
  HYPE_INTERMEDIATE rule "if recent_moves: NONE → never pretend he moved a fader" generalizes: "if
  `decks=unknown` → don't name a key or call a clash."
- **The closing block already says "trust your own ears... YOU decide what's worth saying"** — pair it
  with the hard gate that an *unverifiable* fix gets stripped. The persona is free; the grounding is
  enforced downstream. This is the project's central thesis (grounded Gemini, not better prompting).
- **TTS calm delivery** preserved by `COACH_TAG_DSL_BLOCK` (no `[excited]`/`[fast]` in coach mode).

---

## C) PILL WINDOW INTEGRATION

### What it consumes — the same socket, the existing frames

The pill renders the *same* `ipc.session.*` frames the main session UI already renders. From
`ws_broadcast` (runtime/ws_bus.py) on `ws://127.0.0.1:8765`:

- **`ipc.session.snapshot`** (15Hz, `_build_session_snapshot`) — meters (music/voice/mic), bpm, track
  (title+deck), cohost_status (TALKING/LISTENING/IDLE), grounded flag, MIDI ribbon, transcript delta.
  The pill's live state. v5.0 extends the builder to add a deck block (additive, schema-bumped — below).
- **`ipc.session.cohost-reaction`** (per reaction, emitted from `dj_cohost.llm_node`) — reaction text +
  `citation_strip` chips. The pill's primary content: latest AI line + evidence chips (now including
  deck-clash chips).
- The mascot frame (the flat `{music,voice,mic,...,emotion,reaction_intent}` 30Hz blob) is ALSO on this
  socket. The pill filters for `ipc.session.*` envelopes and ignores the flat mascot frame — exactly
  what `index.html`/`main.ts` already do.

**No new port, no Python wiring change to deliver frames to the pill** — it's another WS client on 8765.
The only Python-side change is *additive deck fields* in the snapshot builder + schema.

### Rust window management — model it on `mascot_window.rs`

Create `tauri/src-tauri/src/pill_window.rs` as a near-clone of `mascot_window.rs` (the proven
transparent/on-top/draggable precedent):

- `transparent(true) + always_on_top(true) + decorations(false) + skip_taskbar(true) +
  visible_on_all_workspaces(true)` — identical builder flags to mascot.
- Smaller default geometry (a pill, ~360×72, not 300×400); min/max bounds tuned for a pill shape.
- `data-tauri-drag-region` on the pill body (the same mechanism `mascot.html` uses on its `<body>` /
  `.mascot-window` divs) makes the whole pill draggable — no custom drag handler.
- Geometry persistence: reuse the exact debounced `install_geometry_listener` pattern (200ms Tokio task,
  compare-and-skip). Persist to a new `pill_window` key in `config.json` via a `PillWindowState` struct
  mirroring `MascotWindowState` (config.rs).
- Off-screen guard (`primary_logical_size` / `default_top_right`) — lift verbatim; a pill that saves
  off-screen is the same failure mode the mascot already guards against.

### Pill-vs-mascot toggle (config/state)

Add a **new top-level `surface` key** to config.json (parallel to `mascot_window`), value
`"pill" | "mascot" | "none"`. The existing `MascotWindowState.visible` bool is mascot-specific; a
tri-state `primary_surface` cleanly expresses "pill is primary, mascot is opt-in secondary" (the
milestone goal) without overloading the mascot bool.

- `main.rs .setup()` reads `primary_surface` (default **`"pill"`** for v5.0 — the milestone makes the
  pill the primary surface), builds the pill window when `"pill"`, the mascot when `"mascot"` (existing
  `create_mascot_window` already gates on `MascotWindowState.visible`). Both can coexist: pill primary +
  mascot opt-in-on means both windows exist.
- Toggle command: add `set_primary_surface(surface)` to config.rs alongside `set_mascot_visible`,
  following the same lazy-create pattern (build the window on demand if it doesn't exist, so switching
  doesn't need a restart). The tray menu (`tray.rs`) and Settings drawer get the toggle UI.
- The mascot stays fully functional as secondary — `set_mascot_visible(true)` independently brings it up
  regardless of `primary_surface`. Nothing about the mascot path is removed (milestone: "kept, not retired").

### Shared frontend assets

- `pill.html` + a `tauri/ui/src/pill/` TS module, built by the existing Vite multi-entry config
  (`vite.config.ts` already emits `index.html`, `mascot.html`, `debrief.html`, `overlay.html` into
  `dist/`). Add `pill.html` as a 5th entry.
- Reuse `src/tokens.css` (CDJ-Whisper v5 design tokens) so the pill visually belongs to the family
  (Saira + JetBrains Mono, warm blacks, single amber accent). The transparent-overlay invariant
  (`background: transparent !important`, disable `body::before` film grain) is the SAME override
  `mascot.html` documents — copy that style block verbatim.
- The WS-client + `ipc.session.*` parsing is shared with the main session UI — extract the frame parser
  into a small shared module (`src/ipc/session-frames.ts`) consumed by both `main.ts` and the pill, so
  deck-snapshot field additions are parsed in one place.

### `tauri.conf.json5` / `mascot_window.rs` changes

- **`tauri.conf.json5`**: the CSP `connect-src` already allows `ws://127.0.0.1:8765` — **no CSP change**
  for WS. Like the mascot, the pill is built at runtime in `main.rs .setup()`, so it gets **no static
  `app.windows[]` entry** (the file's own comment notes a static entry would collide with the runtime
  builder). The capability allowlist (`capabilities/default.json` `"windows": ["main","mascot"]`) MUST
  add `"pill"` — the one place the new label is declared (mirrors the mascot
  `label_constant_matches_capability_allowlist` test).
- **`mascot_window.rs`**: UNCHANGED in behavior. The pill is a sibling module, not a modification of the
  mascot builder. The only cross-cutting touch is `main.rs .setup()` choosing which to build based on
  `primary_surface`.

---

## Anti-Patterns to Avoid (v5.0-specific)

| Anti-pattern | Why it breaks the system | Instead |
|--------------|--------------------------|---------|
| `DeckState` written outside `_tick_once` (poller writes `MusicState` directly) | Violates single-writer rule; torn snapshots for `EventDetector`/`AICoach` | Poller writes its own holder; `_tick_once` copies under `state._lock` |
| New evidence source for deck (`deck:`) | `EVIDENCE_SOURCES` + linter grammar + `CITATION_GRAMMAR_BLOCK` + schema-mirror all break in lock-step | Reuse `mix:` (existence-only) + `track:` (already library-registered) |
| New WS port for the pill | Splits the one-socket contract; complicates sidecar lifecycle (wizard/session bus already share 8765) | Pill is another client on 8765, filters `ipc.session.*` |
| New `"coach2"`/`"feedback"` mode in the matrix | Breaks `_CELLS`/`_VALID_MODES` env-var + Settings contract | Extend the existing COACH_* cells + per-event task tails |
| Prescriptive feedback without citing deck-state | Linter strips it (good) but the persona feels broken/silent | Always cite `[mix:deck_X_key=...]`; gate on `decks=unknown` like `track=unknown` |
| Putting deck-state in the diet/ack prompt path | Deck feedback is substantive; `ACK_ELIGIBLE_EVENTS` is the quick-ack path | Deck events are full-payload (NOT in `ACK_ELIGIBLE_EVENTS`) |
| Static `app.windows[]` entry for the pill | Collides with runtime `WebviewWindowBuilder::new(app,"pill",...)` | Build at runtime in `.setup()`; add label to capability allowlist only |

---

## Scalability / Robustness Considerations

| Concern | Approach |
|---------|----------|
| Deck source unavailable (rekordbox closed, OCR fails) | `DeckTrack.confidence=0` / `decks=unknown`; detectors no-op; feedback degrades to existing audible-mix coaching. Same graceful-degrade discipline as `_HAS_VISION`/`controller_connected`. |
| Poller cost (DB/file/OCR read) | Run on `loop.run_in_executor` like screen/track polling; cache the title→key map per session (the rekordbox-collection / lookahead title-cache precedent). Poll cadence ≪ 10Hz tick. |
| Registry growth from deck writes | Change-only writes (mirror `mix:audible_deck` pattern) keep it bounded; `EvidenceRegistry.snapshot()` stays sub-1ms at ~500 obs/hr. |
| Two always-on-top windows (pill + mascot) | Both `skip_taskbar` + `visible_on_all_workspaces`; geometry persisted separately; off-screen guards on both. |

---

## Suggested BUILD ORDER (dependency-respecting)

The pill is **independent** of deck-state and can parallelize; the feedback persona **depends on**
deck-state existing first.

```
Track 1 (deck-state spine — gating path)
  1. harmonics.py (pure Camelot/key/clash functions — no deps, fully unit-testable)
  2. DeckState/DeckTrack model + embed in MusicState (additive, golden-equivalence preserved)
  3. Deck-state poller + chosen source shim (FEASIBILITY.md picks source) → holder.snapshot()
  4. Wire poller into _tick_once under state._lock + registry writes (mix/track deck obs)
  5. New Event types (event.py) + cooldowns (constants.py)
  6. KEY_CLASH + TRANSITION_OPPORTUNITY detectors, inlined into EventDetector.detect
     ── checkpoint: deck events fire on a real loaded set; registry holds deck obs ──

Track 2 (feedback consumes Track 1)
  7. AICoach.evidence_line deck block + task_for_event arms (depends on 4+5+6)
  8. prompts/matrix.py COACH_* deck-feedback paragraphs (extends in-flight work)
     ── checkpoint: cited, linter-passing actionable deck feedback live ──

Track 3 (pill — PARALLEL with Track 1/2; only soft-depends on the snapshot deck fields)
  A. pill_window.rs (clone mascot_window.rs) + PillWindowState in config.rs
  B. pill.html + src/pill/ + shared src/ipc/session-frames.ts parser; Vite 5th entry
  C. primary_surface tri-state + set_primary_surface command + tray/Settings toggle
  D. capabilities/default.json add "pill"; main.rs .setup() surface selection
     ── pill renders snapshot + cohost-reaction; mascot intact as secondary ──
  E. (after step 4) extend _build_session_snapshot + IPC schema with deck fields; pill renders deck chips
```

**Critical path:** Track 1 → Track 2 (feedback can't cite deck-state that doesn't exist). Track 3 ships
in parallel; only its final polish step (E, deck chips in the pill) waits on Track 1 step 4. The pill's
core (reaction text + meters) needs nothing from deck-state.

---

## Sources

- Live code on branch `live-tuning-or-brain` (HIGH — read directly):
  - `src/vibemix/state/music_state.py`, `event.py`, `event_detector.py`, `refresh.py`, `coach.py`,
    `track_resolver.py`, `evidence_registry.py`
  - `src/vibemix/coach/citation_linter.py`
  - `src/vibemix/prompts/matrix.py`
  - `src/vibemix/agent/dj_cohost.py`, `src/vibemix/runtime/coach.py`, `src/vibemix/runtime/ws_bus.py`
  - `src/vibemix/ui_bus/schemas/cohost_reaction.py`
  - `tauri/src-tauri/src/mascot_window.rs`, `config.rs`, `overlay.rs`, `tauri.conf.json5`
  - `tauri/ui/mascot.html`, `tauri/ui/vite.config.ts` (entry layout)
- `.planning/PROJECT.md` — v5.0 milestone goals + open feasibility flag (HIGH)
- Deck-source recommendation deferred to FEASIBILITY.md / STACK.md. Confirmed gap: the MIDI
  `ControllerState` (`platform/_midi_macos.py`) only tracks vol/play/xfader/EQ moves — it does NOT
  expose per-deck loaded-track titles, so deck-track *identity* must come from an external source
  (rekordbox/screen/nowplaying), exactly as PROJECT.md flags.
