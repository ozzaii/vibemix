# Connection Audit — vibemix as ONE product

> Read-only investigation, 2026-05-25. Maps which subsystems are WIRED into a
> live-running surface vs ORPHANED (built but never invoked at runtime), the
> shared layers that DON'T exist yet, and the top-5 missing wires ranked by
> leverage. Evidence is cited as `file:line`.

The vision: **ONE product = two surfaces** (live co-host + library/Viber
curator) sharing **ONE engine** (grounded perception → structured state) +
**ONE taste/personalization layer**, exposed as **three lenses** (hype / coach /
tutor). Today the pieces are strong islands. This maps the gaps.

---

## 1. Subsystem inventory — WIRED vs ORPHANED

### Live co-host — WIRED (this is the running spine)
- `__main__.py:main()` is the live orchestrator. It builds `MusicState`,
  `EventDetector`, `EvidenceRegistry`, the `DJCoHostAgent`, and spawns 6+ async
  tasks: `ws_broadcast`, `diag_loop`, `screen_capture`, `track_poll`,
  `deck_poll`, `state_refresh_loop`, `coach_loop`, `watch_parent`
  (`__main__.py:1231-1299`).
- `state/refresh.py` → `state_refresh_loop` is the single writer of
  `MusicState` (`__main__.py:1260`). Invariant #1 holds.
- `state/event_detector.py` → emits typed events consumed by `coach_loop`
  (`runtime/coach.py`), which builds prompts via `state/coach.py` and calls the
  agent. WIRED end-to-end.
- `agent/dj_cohost.py` `DJCoHostAgent` — constructed and started
  (`__main__.py:1047-1168`). WIRED.
- Session IPC handlers (settings/profile/recordings) — WIRED via the
  `IpcRouterBus` adapter, but note `SessionLoop` is used as a **handler bag
  only**: `register_handlers()` is called, `run()` is deliberately NOT
  (`__main__.py:1219-1221`). This has a downstream orphaning consequence — see
  Memory below.

### Library / Viber curator — WIRED but only as a SEPARATE CLI surface
- `library/agent.py` `ViberAgent`, `library/toolset.py`, `library/telegram_bridge.py`,
  `library/search.py`, `library/similar.py`, `library/folder_ingest.py` — all
  reachable, but ONLY through `vibemix library <sub>` CLI subcommands
  (`__main__.py:1410-1543`) and the Telegram long-poll bridge. None of them run
  inside the live co-host process. They are a parallel app sharing only the
  on-disk `library.db` + `library.pkl`.
- The curator has its OWN hardcoded persona (`library/agent.py:58`
  `_SYSTEM_INSTRUCTION`, `:189` `_INTERACTIVE_SYSTEM_INSTRUCTION`). It does NOT
  import `vibemix.prompts` / `vibemix.coach` / `vibemix.profile` (grep: zero
  hits). The two surfaces share NO persona/taste layer.

### Embeddings / vibe-search — WIRED for the curator, ORPHANED for the co-host
- Production: offline only. `library/embed.py` (`LibraryEmbedder`, 1536-d Gemini
  Embedding 2, 3-excerpt mean or cue-anchored, `embed.py:16-23,86-96`) is driven
  by `library embed-folder` / Rekordbox import. Persisted to `library.db`.
- Query: `vibe_search` / `similar_to` via the CLI. WIRED for the curator.
- **The live co-host does NOT use library embeddings.** The `Grounding` object
  (`library/grounding.py`, `identify_playing` = "what's playing" audio→library
  cosine) is BUILT in `__main__.py:1147` ("-> grounding: armed") but **never
  passed to the agent or coach_loop** — and `DJCoHostAgent.__init__` has **no
  `grounding` parameter at all** (`dj_cohost.py:340-421`). It is a fully
  orphaned object. See Missing Wire #1.

### Genre detection — detector chain runs; result does NOT reach the prompt
- `state/genre/genre_autodetect.py` scores `detected_genre` / `genre_confidence`
  always (for honesty, `genre_autodetect.py:209-210`) and writes them into
  `MusicState` (`music_state.py:55-56`, single-writer via `_tick_once`).
- BUT `state/coach.py` (the prompt builder) **never reads `detected_genre` /
  `genre_confidence` / `active_genre`** (grep over coach.py: zero hits). The
  detected genre selects the active DSP detector chain but never enters the
  co-host's prompt. See Missing Wire #4.

### Personas / 3 modes — split-brain, NOT shared
- Co-host: `prompts/matrix.py:698 build_system_instruction` + `dj_cohost.py:308
  _resolve_prompt_cell` resolve a persona cell from `VIBEMIX_SKILL_LEVEL` /
  `VIBEMIX_MODE` / `VIBEMIX_MOOD` (`dj_cohost.py:106-111`). The cache mirrors the
  SAME cell (`__main__.py:850-858`). WIRED for the live surface.
- Curator: separate hardcoded strings (`library/agent.py:58,189`). The 3 lenses
  (hype/coach/tutor) exist ONLY on the live surface; the curator is persona-blind.
  No shared taste/profile is read by both. See Missing Wire #3.

### Memory / recall — wired into the agent, but ORPHANED on the live path
- `memory/retrieval.py` `MemoryRecall` IS built and passed to the agent
  (`__main__.py:1030-1089`), gated by `VIBEMIX_RECALL_ENABLED` (default off).
- **But the store is never populated on the live path.** Memory ingest
  (`memory/ingest.py`, `run_ingest_sweep` / `ingest_session`) is invoked only
  from `SessionLoop.run_boot_sweeps()` / `_fire_ingest()`
  (`session_loop.py:689,723,1304`), and `run_boot_sweeps` is called ONLY inside
  `SessionLoop.run()` (`session_loop.py:1304`) — which the live `main()`
  deliberately never calls (`__main__.py:1219-1221`). So `memory.db` stays empty
  in the real app; recall has nothing to retrieve even if Kaan flips the flag.
  See Missing Wire #5.

### The 8 DSP genre-chain detectors — CONFIRMED double-orphaned
- `state/detectors/` emits 8 event types: `KICK_SWAP`, `SUB_LAYER_ARRIVAL`,
  `KICK_DENSITY_SHIFT`, `BREAKDOWN_KICK_KILL`, `PHRASE_BOUNDARY`,
  `DISTORTION_CLIMB`, `ACID_LINE_ENTRY`, `REENTRY_KICK_LAND` (grep confirmed).
- **Gap A — no registry observation.** `event_detector.py:444-447` iterates
  `self.router.active_chain()` and `return ev` directly — it does NOT call
  `_fire()` (`event_detector.py:456-493`). Every other event path calls `_fire`,
  which writes the `[ev:<TYPE>@t]` observation into `EvidenceRegistry`
  (`:491`). So these 8 detectors' measurements never become citable evidence.
- **Gap B — no prompt task.** `state/coach.py:464-575 task_for_event` has no
  branch for any of the 8 types — they all fall to the default
  `"React naturally."` (`coach.py:575`). The rich measurement (centroid delta,
  kick density, phrase position) that the detector computed is discarded; the
  AI just gets a generic nudge with no idea WHAT was detected.
- Net: 8 detectors fire, gate the event clock, and produce nothing the AI or the
  evidence registry can use. Pure orphan compute. See Missing Wire #2.

---

## 2. Shared layers that DO NOT exist yet

1. **No shared perception→state contract both surfaces read.** The live surface
   reads `MusicState` (live audio/MIDI/screen). The curator reads `library.db`
   (offline embeddings). Neither reads the other's representation. There is no
   single "what is true about the music right now / about this track" object
   that both consume. The audio-embedding engine (`LibraryEmbedder`) is the
   natural shared perception primitive but only the curator uses it.

2. **No shared taste/profile layer.** `profile/` (long-term DJ profile) is loaded
   into the co-host cache (`__main__.py:839-858`) but NEVER read by the curator
   (`library/agent.py` doesn't import `profile`). The curator can't curate "for
   this DJ"; the co-host can't lean on what the DJ's library says about their
   taste. The profile is co-host-only.

3. **No shared persona/lens layer.** `prompts/matrix.py` defines the hype/coach/
   tutor lenses for the co-host only. The curator hardcodes its own voice. A
   mode switch in the app does not reach the curator.

4. **No shared store contract.** `library.db` (curator embeddings, `library/store.py`)
   and `memory.db` (session recall, `memory/store.py:83`) are separate sqlite-vec
   stores with separate ingest paths. The co-host's session memory and the
   curator's track library never cross-reference, even though both are
   Gemini-Embedding-2 vectors in the same 1536-d space.

---

## 3. TOP 5 MISSING WIRES (ranked by leverage)

### #1 — Wire `Grounding` ("what's playing") into the live agent  ⭐ highest leverage
**Files:** `src/vibemix/__main__.py:1134-1162` (build site), `src/vibemix/agent/dj_cohost.py:340-421` (constructor — add `grounding` kwarg), `src/vibemix/runtime/coach.py` (event dispatch), `src/vibemix/library/grounding.py:46,82` (`TRACK_AWARE_EVENTS`, `identify_playing`).
This is the single biggest island. The co-host's whole anti-slop thesis is
"react to the track that's actually playing," and the exact engine for that
(`identify_playing` → cosine vs `library.db` → `[track:<id>]` citation) is built,
armed, and logged at boot — then thrown away because the agent has no parameter
to receive it. Connecting it makes the live co-host SHARE the curator's embedding
brain: the AI would cite the real track from the library on TRACK_CHANGE/
LAYER_ARRIVAL/MIX_MOVE, which is the through-line's "one engine" in concrete form.
Add a `grounding` kwarg to `DJCoHostAgent.__init__`, pass the built object, and
call `identify_playing` on track-aware events to inject the citation.

### #2 — Make the 8 genre-chain detectors produce evidence + a real task
**Files:** `src/vibemix/state/event_detector.py:444-447` (call `_fire`), `src/vibemix/state/coach.py:464-575` (`task_for_event` branches), `src/vibemix/state/detectors/*.py` (event `extra` payloads).
The detectors are the co-host's deepest perception (kick character, phrase
boundary, sub-bass arrival) and they currently feed nothing. Two-line-class fix
with outsized payoff: (a) route the 8 returned events through `_fire` so their
`[ev:<TYPE>@t]` observations land in `EvidenceRegistry` (makes them citable,
satisfies Invariant #2), and (b) add `task_for_event` branches that hand Gemini
the specific measurement ("kick character swapped clean→distorted",
"phrase boundary at bar 16") instead of "React naturally." This turns generic
nudges into grounded, genre-aware reactions — directly the anti-slop bar.

### #3 — Unify the persona/lens layer across both surfaces
**Files:** `src/vibemix/prompts/matrix.py:698`, `src/vibemix/agent/dj_cohost.py:308`, `src/vibemix/library/agent.py:58,189` (replace hardcoded strings with matrix calls).
The curator hardcodes its voice while the co-host has a structured
hype/coach/tutor matrix. Make `ViberAgent` resolve its system instruction from
`prompts/matrix.py` (a curator-context variant of the same lens), so flipping
the mode flows to BOTH surfaces. This is the "three lenses over one product"
requirement — today the lens only exists on one surface.

### #4 — Feed detected genre into the co-host prompt
**Files:** `src/vibemix/state/coach.py:255-421` (`evidence_line`), `src/vibemix/state/music_state.py:55-56` (`detected_genre`/`genre_confidence` already present).
`detected_genre` + `genre_confidence` are computed every tick and sit in
`MusicState`, but `evidence_line` never emits them, so the AI never knows it's
reacting to hardtechno vs house. Add a gated `genre=<name>(conf)` field to
`evidence_line` (mirror the existing `track=`/`decks=` confidence-gated pattern
at `coach.py:293-324`). Cheap, and it grounds the AI's vocabulary to the actual
style — a recurring slop source ("generic music commentary").

### #5 — Populate memory.db on the live path (close the recall loop)
**Files:** `src/vibemix/__main__.py:1219-1221` (handler-bag-only wiring), `src/vibemix/runtime/session_loop.py:689,723,1304` (`run_boot_sweeps`/`_fire_ingest`), `src/vibemix/memory/ingest.py`.
Recall is wired into the agent but the store is never filled: the live `main()`
uses `SessionLoop` only as a handler bag and never calls `run()`, so the boot +
session-close ingest sweeps that write `memory.db` never fire in the real app.
Lift `run_boot_sweeps()` / the session-close `_fire_ingest("close")` out of
`SessionLoop.run()` and call them directly from `main()` (boot after recorder
init, close in the `finally` block alongside the retention sweep at
`__main__.py:1361-1377`). Without this, the personalization layer has empty
fuel — lowest of the five because it's gated off by default, but it's the wire
that makes "the co-host remembers your past sets" real.

---

## TL;DR for the milestone
The live co-host is the running spine. The curator is a parallel CLI sharing only
a disk file. The single shared engine the vision needs (audio embeddings) is
built and used by the curator but **orphaned on the co-host** (#1). The co-host's
own deep perception (8 DSP detectors) **produces nothing** (#2). Persona (#3),
genre (#4), and memory (#5) are each half-wired. Connecting #1 and #2 alone
turns the two strongest islands into one grounded mind.
