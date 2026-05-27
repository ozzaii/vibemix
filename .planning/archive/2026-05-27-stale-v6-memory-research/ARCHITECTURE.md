# Architecture Research — v6.0 "The Memory Turn" Integration

**Domain:** Memory / embedding-retrieval layer grafted onto a grounded live-AI co-host
**Researched:** 2026-05-22
**Confidence:** HIGH (every integration point read from live `src/vibemix/` source, not training data)

## Summary verdict

The memory layer is **mostly a wiring milestone, not a greenfield build.** vibemix already ships:

- A working **sqlite-vec store** (`library/index_sqlite_vec.py::SqliteVecStore`) with a numpy fallback (`store.py::open_store`) and the **single-chokepoint top-K math** (`_cosine.py::cosine_topk`).
- A working **Gemini-Embedding-2 client** with a content-hash SQLite cache (`library/embed.py::LibraryEmbedder`).
- An **event-gated embedding→cosine→cited-evidence pattern** already proven end-to-end (`library/grounding.py::Grounding.on_event` → `[track:<id>]` citation). This is the exact shape the retrieval seam copies.
- A **citation-grounding gate** (`EvidenceRegistry` + `CitationLinter`) that already supports an existence-only source type (`track`, `key`) — the model for how a retrieved past moment becomes citable.
- A **per-session artifact writer** (`audio/recorder.py::VoiceRecorder`) that emits `events.jsonl` + `evidence_registry.json` + `voice.wav` + `input.wav` + `session.json` per session under an OS-aware app-data dir, plus a crash-sweep on boot.

So the v6.0 spine is: **(1)** a new post-session ingest job that reads those artifacts and embeds them, **(2)** a new vec0 table in a new per-install DB, **(3)** a new retrieval helper modeled byte-for-byte on `Grounding`, and **(4)** a new `[recall:<id>]` evidence source so retrieved moments pass the *same* linter the audio does. Nothing on the hot reaction path changes shape; the seam is one extra evidence line in `AICoach.evidence_line` and one extra existence-only citation source.

---

## The 4 Cardinal Invariants — how each is preserved

| Invariant | Current owner | How v6.0 preserves it |
|-----------|---------------|------------------------|
| **Single-writer** (`state_refresh_loop._tick_once` is the ONLY writer to `MusicState`) | `state/refresh.py` | Memory layer NEVER touches `MusicState`. Retrieval reads a **frozen `MemoryStore.search()` result** (like `Grounding.get_latest_citation()` returns a snapshot). The memory DB has its OWN single writer — the **ingest job** — which runs *post-session, off-loop*. No concurrent writers to the vec0 table because ingest is one job per session, serialized. |
| **Citation-grounding** (evidence must hit the registry before the LLM may cite it; binary response-level strip) | `state/evidence_registry.py` + `coach/citation_linter.py` | Retrieved moments are registered as a **new existence-only source `recall`** (joins `track`/`key` in `EVIDENCE_SOURCES`, stays OUT of `_TIME_KEYED_SOURCES`). A fabricated `[recall:<id>]` the registry never saw → the existing `CitationLinter.check` strips the whole turn. No new gate code; reuse the proven one. |
| **"Trust the audio"** (ears outrank evidence; never invent) | `prompts/matrix.py` (HYPE_INTERMEDIATE hard gates) + `state/coach.py::evidence_line` | Retrieved moments enter as **labelled prior context, NOT present-tense fact** — past-tense, "you've done this before" framing, explicitly subordinate to the live audio Part. The evidence_line addition is *gated* (emits nothing when retrieval is empty/cold) exactly like the Phase 59 `decks[…]` block, so the v4 byte-identical baseline holds when memory is off. |
| **One-socket** (`ws://127.0.0.1:8765`, single `ws_bus`) | `runtime/ws_bus.py` | Ingest + retrieval are **in-process, no new socket, no new port.** Any UI surfacing of a "copilot recall" rides the existing `ipc.session.*` envelopes through the one bus (`SessionCohostReaction` already carries a `citation_strip`; a recall chip slots in there). Debrief's port 8766 is untouched. |

---

## Standard Architecture

### System Overview (memory layer over the existing co-host)

```
┌──────────────────────────────────────────────────────────────────────┐
│  LIVE REACTION PATH (hot loop — UNCHANGED shape)                      │
│  ┌────────────┐   ┌──────────────┐   ┌─────────────────────────────┐ │
│  │ coach_loop │──▶│ EventDetector │──▶│ DJCoHostAgent.llm_node      │ │
│  │ (10Hz)     │   │ .detect()     │   │  builds contents[]:         │ │
│  └────────────┘   └──────────────┘   │   P0 text prompt            │ │
│         │ single-in-flight            │   P1 live audio  (ALWAYS)   │ │
│         ▼                             │   P2 mic / P3 lookahead     │ │
│  ┌──────────────┐                     └──────────────┬──────────────┘ │
│  │ MusicState   │ ◀── single writer:                 │                │
│  │ (refresh._tick_once)                               ▼                │
│  └──────────────┘             ┌──────────────────────────────────┐    │
│         ▲                      │ AICoach.evidence_line(state, …)  │    │
│         │ reads               │   + NEW: recall[…] line (gated)   │◀─┐ │
│  ┌──────────────┐             └──────────────────────────────────┘  │ │
│  │ EvidenceReg. │ ◀─ write(source,key,t)  ── linter reads snapshot   │ │
│  │ + key/track/ │     NEW source: "recall" (existence-only)         │ │
│  │   + recall   │                                                    │ │
│  └──────────────┘                                                    │ │
└──────────────────────────────────────────────────────────────────────┘
                                                                       │
   RETRIEVAL SEAM (read-only, per-turn, event-gated like Grounding) ───┘
   ┌────────────────────────────────────────────────────────┐
   │ MemoryRetriever.recall(query_vec | live_audio, k)       │
   │   → MemoryStore.search() → cosine_topk (shared math)    │
   └────────────────────────────────────────────────────────┘
                                ▲
                                │ reads
   ┌────────────────────────────────────────────────────────┐
   │ STORAGE (per-install, OWN db, single writer = ingest)   │
   │  app_data_dir()/memory.db   (vec0 table: vec_memory)    │
   │  reuses embeddings.db content-hash cache for embed dedupe│
   └────────────────────────────────────────────────────────┘
                                ▲
                                │ writes (post-session, OFF the hot path)
   ┌────────────────────────────────────────────────────────┐
   │ INGEST JOB (boot-time / session-close, async executor)  │
   │  reads recordings/<session>/{events.jsonl,              │
   │    evidence_registry.json, session.json, *.wav}         │
   │  → typed MemoryRecord[] → embed → MemoryStore.add_batch │
   └────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | New / Modified | Real file:function |
|-----------|----------------|----------------|--------------------|
| **MemoryRecord** | Typed embeddable unit (raw, no LLM-extraction). Carries `record_id`, `session_id`, `t_session`, `kind`, `text_signature`, optional audio-clip ref, `wall_clock_unix` | NEW | `src/vibemix/memory/records.py` |
| **SessionIngestor** | Reads one session dir's artifacts → `MemoryRecord[]`; idempotent (content-hash key skips re-ingest) | NEW | `src/vibemix/memory/ingest.py::ingest_session(session_dir)` |
| **Ingest sweep** | Boot-time scan of `recordings/` for un-ingested sessions; mirrors the crash-sweep pattern | NEW | `src/vibemix/memory/ingest.py::sweep_uningested(recordings_root)` |
| **MemoryStore** | vec0-backed store for memory vectors; single chokepoint `search()` via shared `cosine_topk` | NEW (clone of `LibraryStore`) | `src/vibemix/memory/store.py::MemoryStore` + `index_sqlite_vec` reuse |
| **MemoryRetriever** | Per-turn read-only recall: embed live audio (event-gated) → top-k → frozen result; holds latest like `Grounding` | NEW (clone of `Grounding`) | `src/vibemix/memory/retriever.py::MemoryRetriever.recall()` |
| **LibraryEmbedder** | Gemini Embedding 2 calls + content-hash cache. **Reused as-is** for both ingest and query embedding | REUSED | `src/vibemix/library/embed.py::LibraryEmbedder` |
| **EvidenceRegistry** | Add `recall` to `EVIDENCE_SOURCES`; register retrieved moment ids per turn | MODIFIED (1 frozenset entry + register call) | `src/vibemix/state/evidence_registry.py` |
| **CitationLinter** | No code change — `recall` flows through the existence-only branch automatically | UNCHANGED | `src/vibemix/coach/citation_linter.py` |
| **AICoach.evidence_line** | Append a gated `recall[…]` evidence line + grammar primer | MODIFIED (additive, gated) | `src/vibemix/state/coach.py::AICoach.evidence_line` |
| **CITATION_GRAMMAR_BLOCK** | Add `[recall:<id>]` form + lock-step with `EVIDENCE_SOURCES` | MODIFIED (1 grammar line) | `src/vibemix/prompts/matrix.py::CITATION_GRAMMAR_BLOCK` |
| **__main__ wiring** | Build `MemoryStore`/`MemoryRetriever` lazily (mirror Plan 28-04 grounding build); kick ingest sweep on boot | MODIFIED | `src/vibemix/__main__.py` (~line 921 grounding block) |

---

## The four integration points (the heart of the question)

### (1) INGEST hook — where session data becomes embeddable records

**Decision: post-session batch ingest reading existing artifacts, NOT a live tap.**

The hot path already writes everything memory needs. `VoiceRecorder` emits per session:

- `events.jsonl` — every event fire, `ai_text`, `citation_strip`, `mix_part_attached`, etc. (timestamped `t` = seconds-since-start) — `audio/recorder.py::VoiceRecorder.log_event`
- `evidence_registry.json` — the full per-session citable corpus snapshot, serialized at `close()` — `audio/recorder.py::VoiceRecorder.close` (Phase 29-00 path)
- `session.json` — meta (mode/genre/user_level/duration/started_at) — `audio/recorder.py::_finalize_session_meta`
- `voice.wav` / `input.wav` — raw audio (16k input, 24k AI voice)

**Why batch, not live tap:** A live tap would mean an embed API call on (or near) the reaction path — that violates "keep ingest OFF the hot path" and burns the €50/mo budget on the latency-critical loop. The proven cost contract is *event-gated* embedding (`grounding.py` Pitfall P56: €27/mo vs €1500/mo continuous). Ingest at session close has zero latency cost and embeds in a single bounded batch.

**Two trigger points (both off-loop):**
1. **Session-close hook:** after `recorder.close()` in the `__main__` shutdown/`finally` block, schedule `ingest_session(recorder.session_dir)` via `loop.run_in_executor(None, …)` (the established pattern for blocking embed work — see `LibraryEmbedder` thread-safety note). This embeds the *just-finished* session.
2. **Boot-time sweep:** `sweep_uningested(recordings_root)` walks `recordings/*/`, skips dirs already ingested (a `memory_ingested` marker file or a `session_id` row check), and re-ingests anything missed (crash, old sessions). Models `recorder.py::sweep_crashed_sessions` exactly — boot-only, idempotent, best-effort.

**What becomes a record (acid test: "closes a hallucination class OR unlocks a copilot move"):**

| Artifact slice | → MemoryRecord kind | Embed input (RAW, no LLM-extraction) | Why it qualifies |
|----------------|---------------------|--------------------------------------|------------------|
| `ai_text` events | `coach_line` | the spoken text (text embed) | unlocks "AI calls back vocab it used" copilot move |
| `event` + cited `evidence_registry` entries | `moment` | text signature: `"{type} @ {mm:ss} | {track} | {phase} | moves:{…}"` | unlocks "you've made this transition shape N times" |
| audio window around a high-signal event (optional, gated) | `audio_moment` | `input.wav` excerpt via existing 3-excerpt path | strongest grounding; reuse `embed._embed_audio` |
| `session.json` mode/genre/track-arc | `session_arc` | text signature of the set shape | session-to-session continuity |

The "which artifacts ground best" question stays the **first phase's research** per the milestone note — this maps the *seam*, not the final taxonomy. Start narrow (`coach_line` + `moment` text signatures); audio moments are a stretch within v6.0.

**Off-the-hot-path guarantee:** ingest never imports `coach_loop`, never holds `state._lock`, never calls `session.generate_reply`. It runs in an executor thread on dead session data.

### (2) STORAGE placement — per-install vec0 DB, single writer

**Decision: NEW `memory.db` under the OS app-data dir, distinct from the three existing DBs, reusing the embed cache.**

The repo already has a clear three-DB convention (documented in `embed.py` lines 36-39):
- `~/.cache/vibemix/library.db` — vec0 library track vectors (`index_sqlite_vec.py::DB_PATH`)
- `~/.cache/vibemix/embeddings.db` — content-hash embed cache (`embed.py::EMBED_CACHE_DB_PATH`)
- `library.pkl` — Rekordbox parsed cache

**Placement:** `app_data_dir() / "memory.db"` — use the OS-aware resolver `runtime/config_store.py::app_data_dir()` (macOS `~/Library/Application Support/vibemix`, Windows `%APPDATA%/vibemix`), NOT `~/.cache`. Rationale: memory is *user data that should survive* (it's the personalization), and `recordings/` already lives under `app_data_dir()` — the installer's uninstall path preserves `recordings/` unless `--clean` (v3.1 INSTALL-08). Co-locating `memory.db` there gets the same retention semantics for free. (`~/.cache` is acceptable too but is the wrong durability tier — it's the *cache* dir.)

**Reuse:** clone `index_sqlite_vec.py::SqliteVecStore` with a `vec_memory` table (or parameterize the table name + db path on the existing class). **Do NOT fork the cosine math** — `MemoryStore.search()` calls the same `_cosine.py::cosine_topk` chokepoint (Pitfall P55: bit-identical Mac/Win rank order). The numpy fallback (`index_numpy.py::NumpyStore`) comes free via `open_store(prefer_sqlite_vec=…)` — Windows-ARM and any host without the sqlite-vec wheel degrade silently, exactly like the library does today. `sqlite-vec>=0.1.9` is **already a committed dependency** (`pyproject.toml:118`) so there's no new install-surface risk — the one-click-install green rating is unchanged.

**Single-writer discipline for the memory DB:** the ONLY writer is the ingest job. Ingest is serialized (one `ingest_session` per close, sweep is boot-only single-threaded). The retriever is **read-only** (`load_all` + cosine). This mirrors the EvidenceRegistry contract ("single-Lock-guarded sync writer") and the MusicState contract ("one writer") — vibemix's house style. No async write contention because there is no concurrent writer.

**Embed dedupe:** ingest reuses `LibraryEmbedder` which already keys every embed by SHA256 of `(bytes ‖ model_id ‖ strategy_version)` into `embeddings.db`. Re-ingesting a session = 0 API calls if its records were already embedded. This makes the boot sweep cheap and idempotent.

### (3) RETRIEVAL seam — where top-k past moments enter the coach prompt, GROUNDED

**Decision: inject as a gated `recall[…]` evidence line in `AICoach.evidence_line`, registered as a new existence-only citation source `recall` so retrieved moments are citable through the EXISTING linter.**

This is the precise seam. The coach prompt is assembled in two layers:
1. **System instruction** (once at agent build) — `prompts/matrix.py::build_system_instruction` → `DJCoHostAgent.__init__`. This carries `CITATION_GRAMMAR_BLOCK`.
2. **Per-turn evidence + task** — `state/coach.py::AICoach.build_prompt` → `evidence_line` + `task_for_event`, called inside `DJCoHostAgent.llm_node` (line 538).

**The injection point is `AICoach.evidence_line`** — append a `recall[…]` block, gated identically to the Phase 59 `decks[…]` block (lines 96-109 of `coach.py`): emit NOTHING when retrieval is empty/cold, so the v4 byte-identical baseline (and the HYPE_INTERMEDIATE golden test) stays green when memory is off or no match clears threshold.

**Do retrieved moments need to be citable via the registry/linter? YES — and that is the whole point.** This is how they avoid the "trust the audio / no-fabrication" rule. The mechanism is the **proven `grounding.py` pattern**, generalized:

- `library/grounding.py` already embeds live audio → cosine top-1 → if `>= 0.7` injects `[track:<id>]`, and that id resolves against the registry (`EvidenceRegistry.register_library` pre-registers track ids as an existence-only `track` source). A fabricated track id → linter strip.
- v6.0 does the same with a new `recall` source: per turn, `MemoryRetriever.recall()` returns the top-k past moments above a threshold; the agent **registers each returned `record_id` into the registry** (`registry.write("recall", record_id, t_session)`) *before* the LLM call, and the evidence_line shows them. The LLM may cite `[recall:<id>]`. If it invents a recall id the retriever never returned, the existence-only branch of `CitationLinter._validate_atom` (line 211-212) misses → whole turn strips.

**Why `recall` is existence-only (NOT time-keyed):** add `recall` to `EVIDENCE_SOURCES` (line 103) but keep it OUT of `_TIME_KEYED_SOURCES` (`citation_linter.py` line 52). A recall id is a stable record key, not a `key@t` form — identical treatment to `track` and `key` (Phase 59). **Zero new linter code** — `_validate_atom`'s existence branch already handles it, exactly as the Phase 59 comment promises for `key`.

**Anti-slop framing (the "trust the audio" guard):** retrieved moments enter the prompt as **labelled prior context, subordinate to the live audio**, in past tense. The grammar primer + a one-line guard ("`recall[…]` = things you've heard this DJ do before; reference them only when the LIVE audio matches — never assume the past is the present"). This mirrors the lookahead Part's "NOT YET HEARD BY AUDIENCE / do NOT describe as if it played" guard (`matrix.py::build_parts_description`) — the established way vibemix adds a new grounding axis without letting it override the ears.

**Event-gating (cost + relevance):** retrieval fires only on track-aware events (reuse `grounding.py::TRACK_AWARE_EVENTS`: `TRACK_CHANGE`, `LAYER_ARRIVAL`, `MIX_MOVE`), not every `HEARTBEAT`. Caps embed spend and avoids recall noise on steady stretches. The retriever holds the latest result (`get_latest_recall()`, cleared per turn) so `llm_node` reads a snapshot — no blocking the stream.

### (4) Data flow + suggested BUILD ORDER

**Data flow (write side, off-loop):**
```
session ends → recorder.close() writes events.jsonl + evidence_registry.json + *.wav
   → (executor) ingest_session(session_dir)
       → parse artifacts → MemoryRecord[]   (raw, no LLM-extraction)
       → LibraryEmbedder.embed(...)         (content-hash cached in embeddings.db)
       → MemoryStore.add_batch([(record_id, vec), ...])  → memory.db (vec_memory)
       → write `memory_ingested` marker in session_dir
```

**Data flow (read side, per-turn, event-gated):**
```
EventDetector fires track-aware event
   → MemoryRetriever.recall(live_audio_window, k)
       → LibraryEmbedder.embed_query(audio)  (or reuse the turn's audio embed)
       → MemoryStore.search() → cosine_topk → top-k MemoryRecord ids above threshold
   → registry.write("recall", id, t_session) for each returned id
   → AICoach.evidence_line emits recall[id1: "...", id2: "..."]
   → DJCoHostAgent.llm_node builds contents[] (recall line in P0 text, live audio still P1)
   → LLM may cite [recall:<id>]
   → CitationLinter.check strips the turn if any cited recall id wasn't registered
```

**Build order (dependency-correct — ingest → store → retrieve → copilot move):**

1. **STORE first** (`memory/store.py` + `records.py`). It has no dependency on ingest or retrieval and is unit-testable in isolation against an in-memory vec0 table. Clone `SqliteVecStore`/`open_store`/`LibraryStore`; reuse `cosine_topk`. *Gate:* bit-identical top-K parity test (mirror `test_embeddings_parity.py`).

2. **INGEST second** (`memory/ingest.py`). Depends on STORE (writes to it) + the artifact schema (already stable) + `LibraryEmbedder` (already shipped). Build `ingest_session` + `sweep_uningested`. *Gate:* idempotent re-ingest = 0 API calls; ingest never imports the coach loop (grep gate, mirror the POC-scrub gate). Runnable end-to-end against real `recordings/` dirs with zero changes to the live path — fully decoupled, safe to land before any prompt touch.

3. **RETRIEVE third** (`memory/retriever.py` + the `recall` evidence source). Depends on STORE (reads it). Two sub-steps, in order:
   a. Add `recall` to `EVIDENCE_SOURCES` + grammar block (lock-step test `test_matrix.py` Test R) — pure additive, no behavior change yet.
   b. Build `MemoryRetriever` (clone `Grounding`); wire `evidence_line` gated `recall[…]` block + the per-turn registry registration in `llm_node`. *Gate:* v4 byte-identity holds when retrieval empty; a fabricated `[recall:x]` strips the turn (mirror the Phase 59 KEY_CLASH strip test).

4. **COPILOT MOVE last** (the visible proof). Depends on RETRIEVE firing. 1-2 user-noticeable surfaces: (a) a `recall` chip in the existing `SessionCohostReaction.citation_strip` (add `recall` to `_build_citation_strip`'s source allow-list, `dj_cohost.py` line 213) so the UI shows "↩ you've done this before"; (b) the coach naturally referencing a past moment because the recall line is in its evidence. *Gate:* Kaan-ear pass that a recall actually fires grounded and doesn't feel scripted (the hard quality gate).

**Wiring lands in `__main__.py`** mirroring the existing Plan 28-04 grounding block (line 921-942): build `MemoryStore`/`MemoryRetriever` lazily (`if memory_db.exists() or recordings exist`), pass `memory_retriever` into the agent via a kwargs-only `None`-default arg (the established backward-compat pattern — see `grounding`, `mic_audio_buf`, `lookahead` kwargs on `DJCoHostAgent.__init__`). Kick `sweep_uningested` on boot next to `sweep_crashed_sessions`.

---

## Architectural Patterns (reuse, don't reinvent)

### Pattern 1: Event-gated embed→cosine→cited-evidence (the load-bearing reuse)

**What:** Embed a query (audio/text) only on event fire, cosine top-k against a vec0 store, inject the result as a citable evidence source that the linter validates.
**When:** Every retrieval. This is `library/grounding.py` generalized from `track` to `recall`.
**Trade-off:** Per-turn embed cost (capped by event-gating + the content-hash cache) vs. the alternative of continuous embedding (P56: ~50× cost). Event-gating wins.

```python
# memory/retriever.py — clone of library/grounding.py::Grounding
class MemoryRetriever:
    def recall(self, audio_bytes, *, event_type, k=3) -> list[MemoryRecord]:
        if event_type not in TRACK_AWARE_EVENTS:   # reuse grounding's gate
            return []
        qvec = self._embedder.embed_query_audio(audio_bytes)  # cached
        hits = self._store.search(qvec, k)          # shared cosine_topk
        return [r for r in hits if r.cosine >= RECALL_THRESHOLD]
```

### Pattern 2: Gated additive evidence line (preserves v4 byte-identity)

**What:** A new evidence_line block that emits nothing unless populated, so the golden baseline holds when the feature is cold/off.
**When:** The `recall[…]` line. Copies the Phase 59 `decks[…]` gate verbatim (`coach.py` lines 96-109).
**Trade-off:** None — it's the project's standard way to land new grounding without breaking the byte-identical prompt test.

### Pattern 3: Existence-only citation source (citable without time-keying)

**What:** Add a source to `EVIDENCE_SOURCES`, keep it OUT of `_TIME_KEYED_SOURCES`; the linter's existence branch handles it free.
**When:** `recall` (mirrors `track`, `key`). Register ids into the registry before the LLM call; fabricated ids strip the turn.
**Trade-off:** The linter can't validate a *timestamp* on a recall (it's a record id, not `key@t`) — acceptable, recall is "did this happen before", not "at exactly t".

### Pattern 4: Off-loop batch job mirroring the crash-sweep

**What:** A boot-time idempotent sweep + a session-close executor job, both reading dead artifacts, never touching live state.
**When:** Ingest. Mirrors `recorder.py::sweep_crashed_sessions` (boot-only, best-effort, idempotent).
**Trade-off:** Memory is stale until the session closes (no within-session self-recall). Acceptable for v6.0 — within-session continuity is already covered by `_ai_text_history` + `evidence_corpus`.

---

## Recommended new structure

```
src/vibemix/memory/                 # NEW package — the whole memory layer
├── __init__.py                     # exports MemoryStore, MemoryRetriever, ingest_session
├── records.py                      # MemoryRecord dataclass + text_signature builders (raw)
├── store.py                        # MemoryStore + open_memory_store() (clone of library/store.py)
├── ingest.py                       # ingest_session() + sweep_uningested() (off-loop)
└── retriever.py                    # MemoryRetriever (clone of library/grounding.py::Grounding)
```

**Structure rationale:**
- **A sibling of `library/`, not inside it.** `library/` is about *the user's track collection* (Rekordbox import, vibe search). `memory/` is about *the user's past sessions*. Different lifecycle, different DB, different writer. Keep them separate to keep `library/`'s single-chokepoint contract clean — but `memory/` *imports from* `library/` (`embed.py`, `_cosine.py`, `index_sqlite_vec.py`) rather than copying, so the cosine-parity and embed-cache guarantees are shared, not forked.
- **No new top-level config or socket.** Wiring is additive in `__main__.py`; surfacing is additive on the existing `ipc.session.*` envelopes.

---

## Anti-Patterns (specific to this integration)

### Anti-Pattern 1: LLM-extraction between session and embedding
**What people do:** Run a "summarize this session" LLM pass and embed the summary.
**Why it's wrong:** Extraction is a confabulation surface — it invents structure that was never there, violating the anti-slop thesis (locked in the milestone note + memory `feedback_no_managed_memory_frameworks`). It also adds cost + a failure mode.
**Do instead:** Embed RAW typed records (event text, coach lines, audio excerpts). What goes in is what was there.

### Anti-Pattern 2: Retrieved moments injected as fact, not labelled prior
**What people do:** Drop top-k past lines into the prompt as if they're current observations.
**Why it's wrong:** Breaks "trust the audio" — the LLM will narrate a past transition as if it's happening now (the classic latency-hallucination).
**Do instead:** Label the `recall[…]` block as past prior context, past-tense, subordinate to the live audio Part, with the same anti-prediction guard the lookahead Part uses.

### Anti-Pattern 3: A second writer to the memory DB (or worse, to MusicState)
**What people do:** Let the retriever cache write-back, or let ingest run concurrently with retrieval.
**Why it's wrong:** Breaks single-writer; introduces vec0 write races.
**Do instead:** Ingest is the sole writer, serialized (one per close + boot sweep). Retriever is strictly read-only. Memory NEVER writes MusicState — it reads a frozen snapshot like `Grounding`.

### Anti-Pattern 4: Forking the cosine math or opening a new socket/port
**What people do:** Write a bespoke KNN in `MemoryStore`, or add a memory IPC port.
**Why it's wrong:** Breaks Mac/Win bit-identical parity (P55) and the one-socket invariant.
**Do instead:** Call `_cosine.py::cosine_topk`; surface recall on the existing `ws_bus` `ipc.session.*` envelopes.

---

## Integration Points

### Internal boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `memory/ingest.py` ↔ `audio/recorder.py` artifacts | File reads (events.jsonl, evidence_registry.json, session.json, *.wav) | Read-only; artifact schema is stable (Phase 15 + 29-00). Idempotent via `memory_ingested` marker. |
| `memory/store.py` ↔ `library/index_sqlite_vec.py` + `_cosine.py` | Python import / subclass | Reuse SqliteVecStore + cosine_topk; numpy fallback free via open_store. New `memory.db` / `vec_memory` table. |
| `memory/ingest.py` + `retriever.py` ↔ `library/embed.py::LibraryEmbedder` | Python call | Reuse embed + content-hash cache (`embeddings.db`). Audio-aware embed for audio_moment records. |
| `memory/retriever.py` ↔ `state/coach.py::AICoach.evidence_line` | Frozen result read in `llm_node` | Gated `recall[…]` line; populated only above threshold. |
| `memory/retriever.py` ↔ `state/evidence_registry.py` | `registry.write("recall", id, t)` per turn before LLM call | Makes recall citable; reuses existence-only linter branch. |
| recall chip ↔ `runtime/ws_bus.py` | Existing `SessionCohostReaction.citation_strip` | No new socket; add `recall` to `_build_citation_strip` allow-list. |

### External services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Gemini Embedding 2 (via Bravoh proxy) | `LibraryEmbedder` — proxy-only, never reads raw key | Already shipped; ingest + query embeds flow through it. ServiceTier.FLEX for batch ingest (50% cost cut, `ModelRouter`). |

---

## Scaling considerations (per-install, single user)

| Scale | Adjustment |
|-------|------------|
| 0-50 sessions | No tuning. `load_all` + cosine over a few thousand vectors is sub-ms. |
| 50-500 sessions | Add a retention/size budget (TBD per milestone open-Q). Cap `vec_memory` rows; prune oldest `audio_moment` first (largest, least often cited). Reuse `library/budget.py` + `staleness.py` patterns. |
| 500+ sessions | Still single-install scale; `cosine_topk` is O(N) but N is thousands, not millions. If ever slow, the documented path is sqlite-vec's native ANN — but the P55 parity rule means that's a deliberate, tested change, not a default. |

**First bottleneck:** index load time on `MemoryStore.search()` (loads all vectors per query). Mitigation: cache `load_all()` in the retriever for the session's lifetime (memory.db has a single writer = ingest, which never runs during a live session, so the in-session view is immutable — safe to cache). This mirrors the library's snapshot-hash query cache.

---

## Open questions handed to the roadmapper

1. **Artifact taxonomy** — which records ground best (`coach_line` vs `moment` vs `audio_moment`) is the FIRST phase's research, not pre-decided. Recommend starting text-only (`coach_line` + `moment`), audio_moment as a stretch.
2. **Retrieval blend** — cosine-only vs cosine + time-weight (recency boost). Default cosine-only for v6.0; time-weight is a tunable, not a blocker.
3. **Retention/size budget** per install (rows + bytes) — reuse `library/budget.py` machinery.
4. **Recall threshold** — start at `grounding.py`'s 0.7 citation floor; tune by Kaan-ear.

---

## Sources

- `src/vibemix/state/coach.py` (AICoach.evidence_line / build_prompt — the retrieval injection seam) — HIGH (read)
- `src/vibemix/state/evidence_registry.py` (EVIDENCE_SOURCES, write/has/snapshot — citation grounding) — HIGH (read)
- `src/vibemix/coach/citation_linter.py` (existence-only vs time-keyed branch — recall is citable free) — HIGH (read)
- `src/vibemix/agent/dj_cohost.py` (llm_node reaction path, contents[] assembly, _build_citation_strip) — HIGH (read)
- `src/vibemix/library/grounding.py` (the event-gated embed→cosine→cited pattern recall clones) — HIGH (read)
- `src/vibemix/library/{store,index_sqlite_vec,embed,_cosine}.py` (existing sqlite-vec store + embedder + shared math to reuse) — HIGH (read)
- `src/vibemix/audio/recorder.py` (session artifacts + crash-sweep pattern ingest mirrors) — HIGH (read)
- `src/vibemix/debrief/session_loader.py` (proven artifact-read pattern for ingest) — HIGH (read)
- `src/vibemix/prompts/matrix.py` (CITATION_GRAMMAR_BLOCK + build_system_instruction + lookahead labelling guard) — HIGH (read)
- `src/vibemix/runtime/config_store.py::app_data_dir` (storage placement resolver) — HIGH (read)
- `src/vibemix/__main__.py` ~L921 (grounding lazy-build wiring pattern memory mirrors) — HIGH (read)
- `pyproject.toml:118` (sqlite-vec>=0.1.9 already committed) — HIGH (read)
- `.planning/notes/v-next-memory-turn.md` + `.planning/PROJECT.md` (milestone scope + locked decisions) — HIGH (read)

---
*Architecture research for: vibemix v6.0 "The Memory Turn" — memory/embedding-retrieval integration*
*Researched: 2026-05-22*
