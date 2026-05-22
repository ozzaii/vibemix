# Phase 64: Session Ingest - Research

**Researched:** 2026-05-22
**Domain:** Off-hot-path post-session ingest — turning a finished session's on-disk artifacts (`events.jsonl` + `ai_text` + cited evidence) into deterministic TEXT "reaction moment" records and writing them to the Phase 63 `MemoryStore`. Reader + signature builder + batch writer + boot sweep + gates. ZERO net-new dependency.
**Confidence:** HIGH — every claim below verified by reading live `src/vibemix/` source AND a real on-disk session corpus at `~/Library/Application Support/vibemix/recordings/`, not training data.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Area 1 — What gets ingested (taxonomy) — PARTIALLY DEFERRED TO THIS RESEARCH**
- v1 default is text-only and conservative. Candidate kinds: `coach_line` (a reaction the AI produced + the cited evidence that grounded it) and `moment` (a notable `events.jsonl` event — track-change/phase/layer-arrival + its evidence). `audio_moment` is explicitly DEFERRED to a future milestone.
- The exact taxonomy ("which artifacts ground best") is THIS phase's research question, held to the **acid test**: *only embed a record if retrieving it later closes a hallucination class OR unlocks a copilot move.* If a candidate does neither, do not embed it. Start text-only; do not expand kinds without the acid test clearing. → **Resolved below in §Taxonomy Decision.**
- Signature = deterministic text template assembled from raw fields (`kind | track/context | evidence tokens | the ai_text it produced`) — stable, human-readable, byte-reproducible from the same artifacts (so the content-hash embed cache makes re-ingest free). NO model in the assembly path.

**Area 2 — When/how ingest runs (off the hot path)**
- Trigger 1 — session-close batch: when a session ends, enqueue a single batch ingest of that session's artifacts on the FLEX cost lane via `loop.run_in_executor(None, ...)`. Never inline in the reaction loop.
- Trigger 2 — boot-time sweep: on startup, scan for sessions whose recordings exist but were never ingested (crashed/missed) and ingest them — mirroring the recorder/`recordings_index` crash-sweep pattern. Also `run_in_executor`.
- Idempotency: re-ingesting an already-ingested session costs 0 API calls and is a no-op write — guarded by (a) the content-hash embed cache and (b) a per-session `memory_ingested` marker. Reading an already-marked session short-circuits before any embed call.
- Tagging: every record is `session_id` + timestamp + `kind` tagged (the Phase 63 record shape) for later (a) self-session exclusion (Phase 65) and (b) cascade-delete (`delete_session`).

**Area 3 — Reuse & boundaries**
- Reader: reuse / mirror `src/vibemix/debrief/session_loader.py` — it already parses `events.jsonl` + `ai_text` + evidence from a session directory. Do not re-implement session parsing; lift its loader (read-only) or factor a shared helper.
- Writer: `MemoryStore.add_record(...)` from Phase 63 (compose, don't re-open the DB ad hoc). Embedding strictly via `library/embed.py` (router-resolved `embedding` model, FLEX, content-hash cache) — NO hardcoded model literal.
- No-extraction CI guard: add a static test asserting the ingest path imports/calls only `embed_content` — never `generate_content`/`generate_reply`/`.chats.`/`GenerateContentConfig`.
- Import-boundary gate: extend the no-live-path import test to the ingest module (no coach loop / `MusicState` / `ws_bus` / agent / prompts import).

### Claude's Discretion
- Module placement (`src/vibemix/memory/ingest.py` vs a sibling `src/vibemix/ingest/` package), the exact `memory_ingested` marker mechanism (sqlite flag row vs sentinel file), and whether the boot-sweep lives with the recorder sweep or in the ingest module — planner's discretion, guided by `recordings_index`/`debrief` conventions. The session-close enqueue call-site wiring into the runtime may be shipped here (it touches only the session-end seam, not the reaction loop) OR surfaced as a scope note — planner decides, but if wired it must not import the live reaction path.

### Deferred Ideas (OUT OF SCOPE)
- Retrieval seam / `recall` evidence source / coach grounding → Phase 65.
- Visible copilot moves → Phase 66.
- `audio_moment` (multimodal) embedding → future milestone.
- Cross-session "arc" priors / pre-set prep → future milestone.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INGEST-01 | A post-session ingest job turns each session's existing artifacts (`events.jsonl` + cited evidence + `ai_text`) into typed "reaction moment" records as deterministic TEXT signatures — NO audio embedding (v1), NO LLM-extraction between session and embedding (CI guard asserts only `embed_content`). | §Reader Reuse (the `session_loader` analog), §Taxonomy Decision (the resolved `kind` set), §Signature Template Spec (the byte-reproducible templates), §No-Extraction Gate. The on-disk corpus (327 `event` + 131 `ai_text` lines across real sessions) grounds every field. |
| INGEST-02 | Ingest runs off the hot path — at session-close in batch (FLEX) plus a boot-time sweep for crashed sessions (mirrors the recorder sweep), via `run_in_executor`; never touches `MusicState`, never holds `state._lock`, never a live tap. | §Off-Hot-Path Execution. `on_session_close` (`session_loop.py:709`) is the session-end seam; `run_boot_sweeps` (`:685`) is the boot seam; both already dispatch FS work through `loop.run_in_executor`. The wiring direction (runtime imports `memory.ingest`, never the reverse) keeps the no-live-path gate green. |
| INGEST-03 | The moment taxonomy is research-resolved in-phase, held to the acid test — only records that close a hallucination class or unlock a copilot move are embedded; everything `session_id`/timestamp-tagged for later exclusion + deletion. | §Taxonomy Decision (acid-test scorecard per candidate → ONE v1 kind: `coach_line`; `moment` CUT, `audio_moment` DEFERRED). Tagging is automatic via `MemoryStore.add_record(record_id, session_id, ts, kind, signature, embedding)` — the shape already ships. |
</phase_requirements>

## Summary

Phase 64 is a small, mechanical phase: a **reader** (lift the shipped `debrief/session_loader.py` shape — read `events.jsonl`, parse JSONL lines), a **deterministic signature builder** (pure string assembly from raw event fields — NO model), a **batch writer** (call the shipped `MemoryStore.add_record` per record), an **idempotency layer** (a `memory_ingested` marker + the content-hash embed cache), a **boot sweep** (mirror `recordings_index` / `run_boot_sweeps` to ingest crashed/missed sessions), and **two CI gates** cloned from Phase 63 (no-extraction static scan, no-live-path import boundary, extended to the new module). There is essentially **no novel algorithm** — every primitive ships. The genuinely new code is the signature template and the wiring.

The research produced **three load-bearing findings** that change the naive plan:

1. **`evidence_registry.json` is NOT on disk.** Across the entire real recordings corpus (`~/Library/Application Support/vibemix/recordings/`, ~70 sessions), **zero** sessions contain an `evidence_registry.json` file. `session_loader.load_session` treats it as optional and returns `{}` (`session_loader.py:143-156`). The cited evidence that grounds a reaction lives **inline in the `ai_text` line's `text` field** (e.g. `"...that high-mid guitar chord is [aud:rms@96.0] sitting perfectly inside the pocket."`) — matched by the locked `EVIDENCE_CITATION_RE` grammar. The signature builder must read citations from the `ai_text` text, not from an absent registry snapshot. [VERIFIED: filesystem scan + `session_loader.py:143`]

2. **`LibraryEmbedder.embed_query(text)` has NO content-hash cache** (`embed.py:362-369` — "No content-hash cache here"). Only `embed_track(TrackEntry)` caches, and its key is SHA256 of *file bytes* + model + strategy version (`embed.py:569-601`). So the locked "content-hash embed cache makes re-ingest free" idempotency claim **does not hold for free** through `embed_query` — calling `embed_query` on the same signature twice costs 2 API calls. The plan MUST add a content-hash cache for text-signature embeds (reuse the *exact* `embed_cache` table mechanism from `embed.py:146-157,605-623`, keyed on `SHA256(signature || model_id || sig_template_version)`), and combine it with the `memory_ingested` marker so a re-ingest short-circuits before any embed call. This is the single most important plan correction. [VERIFIED: `embed.py:362,569`]

3. **The taxonomy resolves to ONE v1 kind: `coach_line`.** Held to the acid test, `moment` (a bare `events.jsonl` event with no AI reaction) is CUT — retrieving "a PHASE event happened at 36s on deck B" closes no hallucination class and unlocks no Phase-66 copilot move (the two Phase-66 moves are a transition-shape callback and a vocabulary/register callback — both need the *language the AI used*, which only `coach_line` carries). `audio_moment` stays DEFERRED per CONTEXT. See §Taxonomy Decision for the full scorecard. **One good kind beats three weak ones.**

**Primary recommendation:** Ship `src/vibemix/memory/ingest.py` (sibling of `store.py`, inside the existing `memory/` package so the shipped Phase-63 gates auto-cover it). It exposes `ingest_session(session_dir, store, embedder) -> IngestResult` (pure, executor-safe) and a `run_ingest_sweep(...)` boot sweep. The signature builder produces ONE `coach_line` record per emitted `ai_text` line, with a deterministic template stitching the reaction text to its nearest preceding `event` context (track/phase/deck) and its inline citation tokens. Idempotency = a `memory_ingested(session_id, ingested_at, sig_template_version)` marker table in `memory.db` + a signature-keyed text-embed cache. Boot sweep + session-close enqueue both go through `run_in_executor`; the runtime imports `memory.ingest`, never the reverse. Clone `test_no_extraction.py` / `test_no_live_path_import.py` coverage (they already glob `memory/*.py`, so they cover `ingest.py` automatically — verify, then add ingest-specific positive cases).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Read finished session artifacts (`events.jsonl`, `ai_text`) | Local FS read (clone `debrief/session_loader` shape) | — | Dead data on disk; no live state. Read-only. |
| Build deterministic TEXT signature | Pure CPU string assembly (NO model) | — | The no-extraction invariant: signature = raw-field concatenation, byte-reproducible. |
| Embed the signature | External API (Gemini Embedding 2 via Bravoh proxy, FLEX) | Signature-keyed content-hash cache | Reuse `LibraryEmbedder`; off-hot-path; cache makes re-ingest free (NEW cache needed — see Finding 2). |
| Write embedded record + metadata | Local storage (`MemoryStore.add_record`) | — | Phase 63 contract; tags `session_id`/ts/kind atomically (vector-first). |
| Idempotency marker | Local sqlite (`memory_ingested` table in `memory.db`) | — | A re-ingest short-circuits before any embed; survives crashes. |
| Detect un-ingested sessions at boot | Local FS sweep (mirror `recordings_index._scandir` + `run_boot_sweeps`) | — | Crash recovery; never blocks boot; best-effort. |
| Off-hot-path dispatch | `loop.run_in_executor(None, fn)` from the runtime | — | Established idiom (`session_loop.py:751`); ingest never runs on the reaction loop. |
| Call-site wiring (session-close enqueue) | Runtime (`session_loop.on_session_close` seam) imports `memory.ingest` | — | One-way dependency: runtime → memory. Memory never imports runtime live path (gate-enforced). |

> No new socket/port (one-socket invariant). No UI tier (headless backend ingest — frontend skill confirmed **N/A** below). The only external network call is the FLEX embedding call, identical to the library import path.

## Standard Stack

**Net-new third-party dependencies: ZERO.** Everything below already ships, installed and (for `vec0.*`) signed.

### Core (all REUSED, not installed)
| Library / Module | Version / Path | Purpose | Why Standard |
|------------------|----------------|---------|--------------|
| `MemoryStore.add_record` | `src/vibemix/memory/store.py:271` | Write target: `(record_id, session_id, ts, kind, signature, embedding)` | Phase 63 contract; tags + path-traversal-defended + vector-first ordering already shipped. `[VERIFIED: store.py:271]` |
| `LibraryEmbedder.embed_query` | `src/vibemix/library/embed.py:362` | Text-signature → 768-dim L2-normalized float32 via Gemini Embedding 2, FLEX, proxy-only | The ONLY model call ingest may make. **Caveat: no built-in cache (Finding 2).** `[VERIFIED: embed.py:362]` |
| `embed_cache` table mechanism | `src/vibemix/library/embed.py:146,605-623` | The content-hash cache idiom to clone for signature embeds | Idempotency primitive; `SHA256(content)→vector BLOB`. `[VERIFIED: embed.py:605]` |
| `resolve("embedding")` | `src/vibemix/llm/_router_config.py:40` | `("gemini-embedding-2", ServiceTier.FLEX)` | The only sanctioned model id source; CI gate forbids literals. `[VERIFIED: _router_config.py:40]` |
| `session_loader` shape | `src/vibemix/debrief/session_loader.py:74-166` | JSONL parse + optional-evidence handling + invalid-dir guards | The reader analog; `_read_events` skips malformed lines. `[VERIFIED: session_loader.py:74]` |
| `EVIDENCE_CITATION_RE` | `src/vibemix/state/evidence_registry.py:133` | Extract inline `[source:body]` citation tokens from `ai_text` text | The locked grammar; the citations live in the text, not a registry file (Finding 1). `[VERIFIED: evidence_registry.py:133]` |
| `recordings_index` sweep idioms | `src/vibemix/runtime/recordings_index.py:78,120,490` | `SESSION_DIR_RE`, `_scandir_size_sum`, `run_retention_sweep` shape, two-layer path-traversal gate | Mirror (copy, don't import — importing the runtime risks the live path) for the boot ingest sweep. `[VERIFIED: recordings_index.py:78]` |
| stdlib `sqlite3`, `hashlib`, `json` | CPython 3.12 | Marker table, content-hash, JSONL parse | No new dep. `[VERIFIED: CLAUDE.md Python 3.12]` |

### Alternatives Considered (all rejected — locked or off-pattern)
| Instead of | Could Use | Verdict |
|------------|-----------|---------|
| Clone `session_loader` shape into `memory/ingest.py` | Import `debrief.session_loader` directly | **Borderline.** `session_loader.py` imports only stdlib (`json`, `wave`, `logging`) — it does NOT pull the live path. A direct import would NOT trip the no-live-path gate (gate forbids `state.coach`/`agent`/`prompts`/`ws_bus`/`MusicState`/`EventDetector`, none of which `session_loader` touches). HOWEVER: `session_loader.load_session` enforces a 5-min `SessionTooShort` floor and returns a `(events, evidence, voice_meta)` tuple shaped for the debrief UI, not for ingest. **Recommend: import only the malformed-line-tolerant JSONL read pattern (re-implement the ~12-line `_read_events`), OR factor a shared `_read_events_jsonl` helper.** Do NOT inherit the 5-min floor (ingest should ingest short sessions too). Planner's discretion; flag the import-vs-mirror choice. |
| `embed_query` (no cache) + signature marker | `embed_query` alone | REJECTED — re-ingest would cost API calls (Finding 2). MUST add a signature-keyed cache. |
| One `coach_line` kind | `coach_line` + `moment` + `audio_moment` | REJECTED `moment` (fails acid test), DEFERRED `audio_moment` (CONTEXT). See §Taxonomy Decision. |
| New `src/vibemix/ingest/` package | `src/vibemix/memory/ingest.py` | RECOMMEND the latter — the shipped Phase-63 gates already glob `src/vibemix/memory/*.py`, so a module there is auto-covered. A new top-level package needs new gate files. Lower-risk. |

**Installation:** none. The store + embedder + router already ship. Confirm only that `import vibemix.memory.store` and `vibemix.library.embed.LibraryEmbedder` resolve (they do — Phase 63 is GREEN, library is shipped).

## Package Legitimacy Audit

> No external packages are installed by this phase. All primitives are in-repo modules (`vibemix.memory`, `vibemix.library`, `vibemix.state`, `vibemix.runtime`) or stdlib (`sqlite3`, `hashlib`, `json`, `re`). slopcheck is **not applicable** — there is no install step.

| Package | Registry | Status | Disposition |
|---------|----------|--------|-------------|
| (none) | — | This phase wires existing modules + stdlib only | No install — N/A |

**Packages removed due to slopcheck [SLOP] verdict:** none (no install step).
**Packages flagged [SUS]:** none.

## Taxonomy Decision (THE core deliverable — INGEST-03)

The acid test (CONTEXT + ROADMAP): *only embed a record if retrieving it later closes a hallucination class OR unlocks a copilot move.* Phase 66's two locked copilot moves are (a) a **transition-shape callback** and (b) a **vocabulary/register callback** (ROADMAP:44, COPILOT requirements). Both need *the language the AI actually used during a comparable past moment* — to call back to it warmly and in the DJ's register without re-inventing it (= without confabulating).

### Scorecard

| Candidate `kind` | What it stores | Closes a hallucination class? | Unlocks a Phase-66 move? | Verdict |
|------------------|----------------|-------------------------------|--------------------------|---------|
| **`coach_line`** | The `ai_text` reaction text + its preceding-event context (track/phase/deck) + its inline citation tokens | **YES** — retrieving "what I actually said about a comparable groove-phase build last time" lets the coach ground a callback in a *real prior utterance* instead of inventing a memory ("last week you…" with no basis). | **YES — both.** Transition-shape callback: the reaction text is about a transition/mix the AI observed. Vocabulary/register callback: the reaction text *is* the DJ-friend register/vocabulary the move must echo. | **SHIP (v1)** |
| **`moment`** | A bare `events.jsonl` event (TRACK_CHANGE/PHASE/LAYER_ARRIVAL) + evidence, with NO AI reaction text | **NO** — retrieving "a PHASE→groove transition happened at 36s on deck B" is a structural fact already re-derivable live from the current `MusicState`; storing it adds no grounding the live path lacks. | **NO** — neither Phase-66 move consumes a bare structural event; both need the *utterance*. A `moment` with no `ai_text` carries no register and no callback-able language. | **CUT** |
| **`audio_moment`** | Multimodal audio embedding of a session segment | (deferred — text-retrieval-insufficiency-gated) | (deferred) | **DEFER** (CONTEXT — future milestone) |

**Conclusion: v1 ships exactly ONE kind — `coach_line`.** Rationale (lean discipline, CONTEXT "one good kind beats three weak ones"): the only artifact that survives the acid test is a reaction the AI *produced* — because Phase 66's moves are callbacks to *what was said*, not to *what happened*. A bare event is re-derivable live and therefore redundant in memory; embedding it spends FLEX budget and dilutes top-k retrieval with low-signal records. If, in Phase 65 tuning on Kaan's real corpus, `coach_line` retrieval proves insufficient, `moment` can be revisited THEN — but only after the acid test clears with evidence, never by default.

> **Edge case the builder must handle:** a `coach_line` is only worth storing if the reaction was actually **emitted** (the DJ heard it). The corpus shows `ai_text` lines are logged on the emit/bypass paths; stripped (silenced) reactions are logged as `citation_strip` with `raw_text` and were NOT heard. **Ingest the `ai_text`-kind lines (heard), NOT `citation_strip` lines (silenced).** A silenced line never happened from the DJ's perspective — embedding it would let the coach "remember" something the DJ never heard (a subtle confabulation). `[VERIFIED: dj_cohost.py:1054 (ai_text on emit) vs :1123 (citation_strip on silence)]`

## Signature Template Spec (implement verbatim)

**Goal:** a deterministic, byte-reproducible TEXT string assembled from raw fields — NO model in the path. Same artifacts → same bytes → same content-hash → 0-cost re-embed.

### `coach_line` signature

For each emitted `ai_text` line in `events.jsonl`, find the **nearest preceding `event`-kind line** (the context the reaction fired on) and assemble:

```
coach_line | track={track} | phase={phase} | deck={deck} | event={event_type} | cite={citation_tokens} | said: {reaction_text}
```

**Field provenance (all raw, no inference):**

| Token | Source field | On-disk example | Missing-value rule |
|-------|--------------|-----------------|--------------------|
| `{track}` | nearest preceding `event`.`track` | `"Parcels - Topic - Yougotmefeeling (PNAU Remix)"` | `unknown` when `null`/absent |
| `{phase}` | nearest preceding `event`.`phase` | `groove` / `low` / `silent` | `unknown` |
| `{deck}` | nearest preceding `event`.`deck` | `B` / `mix` / `none` | `none` |
| `{event_type}` | nearest preceding `event`.`type` | `PHASE` / `MIX_MOVE` / `TRACK_CHANGE` | `MANUAL` (if the reaction had no preceding event in-window) |
| `{citation_tokens}` | `EVIDENCE_CITATION_RE.findall(ai_text.text)`, joined `,` sorted | `[aud:rms@96.0]` → `aud:rms@96.0` | empty string when none (most `[chill]`-only lines have no real citation) |
| `{reaction_text}` | `ai_text`.`text`, with the leading `[emotion]` TTS tag stripped | `"that high-mid guitar chord is [aud:rms@96.0] sitting perfectly inside the pocket."` | (always present — that's why this line was logged) |

**Determinism rules (load-bearing for the cache):**
- Round NO floats into the signature except where already rounded on disk (`t` is already `round(rel,3)` per `recorder.py:314`). Do NOT include `t` *in the embedded signature text* — `t` goes into the `MemoryStore` `ts` column (metadata), not the embedded string, so two structurally-identical reactions at different times still cache-hit on the embed. (The `record_id` carries uniqueness — see below.)
- Citation tokens MUST be sorted (the regex returns them in text order; sort so re-ordering in the text doesn't change the hash — defensive; in practice order is stable).
- The leading `[emotion]` tag (e.g. `[chill]`, `[hype]`) is a TTS directive, NOT a citation (it has no `source:` colon-form and won't match `EVIDENCE_CITATION_RE`). Strip it from `{reaction_text}` deterministically (regex `^\[[a-z]+\]\s*`) so the embedded text is the actual spoken line. `[VERIFIED: ai_text corpus — every line prefixed with [chill]]`

### Record identity & tagging

- `record_id` = `f"{session_id}:{seq}"` where `seq` is the **0-based index of the emitted `ai_text` line within the session** (stable, monotonic, reproducible from the same file). This matches the Phase-63 locked scheme (`63-RESEARCH.md`: `f"{session_id}:{seq}"`). `[VERIFIED: store.py uses record_id as PK]`
- `session_id` = the session dir basename (`YYYYMMDD-HHMMSS`), validated by `MemoryStore._validate_session_id` on write (already enforced — `store.py:302`).
- `ts` = the `ai_text` line's `t` (seconds since session start).
- `kind` = `"coach_line"`.
- `signature` = the assembled string above (stored verbatim — raw-in/raw-out).

### Embed-cache key (the idempotency fix — Finding 2)

```
embed_cache_key = SHA256(signature.encode() || b"||" || model_id.encode() || b"||" || SIG_TEMPLATE_VERSION.encode())
```

`SIG_TEMPLATE_VERSION = "v1-coach_line"` — bump to re-embed all signatures if the template changes (mirrors `embed.py`'s `EXCERPT_STRATEGY_VERSION`). Reuse the `embed_cache(key, vector, ts)` table shape verbatim (`embed.py:146-157`). On ingest: check cache → hit returns the cached vector at 0 API cost → miss calls `embedder.embed_query(signature)` then `_cache_put`. The cache DB may be the same `~/.cache/vibemix/embeddings.db` the library uses (a shared table is fine — keys are namespaced by the distinct signature text + version) OR a sibling; planner's discretion.

## Off-Hot-Path Execution (INGEST-02)

### The two seams (both already exist, both already use `run_in_executor`)

| Trigger | Seam | Pattern to mirror |
|---------|------|-------------------|
| Session-close batch | `session_loop.py:709 on_session_close` (called from `run_session` shutdown at `:1212`, AFTER `recorder.close()` finalizes `session.json`) | The retention sweep dispatch at `:751` — `result = await loop.run_in_executor(None, fn, args...)`. Enqueue `ingest_session(session_dir, store, embedder)` the same way. |
| Boot sweep (crashed/missed) | `session_loop.py:685 run_boot_sweeps` (called from `run()` at `:1132`, before IPC traffic) | `run_retention_sweep` (`recordings_index.py:490`) — `os.scandir` the recordings root, process un-marked sessions. Add a sibling `run_ingest_sweep` (in `memory/ingest.py`) and call it from a boot-sweep seam via `run_in_executor`. |

### Dependency direction (the gate-safe wiring)

The no-live-path gate (`test_no_live_path_import.py`) forbids `src/vibemix/memory/*.py` from **importing** `state.coach` / `state.refresh` / `agent` / `prompts` / `ws_bus` / `MusicState` / `EventDetector`. It does **NOT** forbid the runtime from importing `memory.ingest`. So:

- `memory/ingest.py` imports: `vibemix.memory.store` (MemoryStore), `vibemix.library.embed` (LibraryEmbedder), `vibemix.state.evidence_registry` (EVIDENCE_CITATION_RE — **check this is gate-safe**: `evidence_registry.py` imports `asyncio`/`re`/stdlib + a TYPE_CHECKING-only `RekordboxLibrary`; it does NOT import the coach loop or MusicState at runtime — but `EVIDENCE_CITATION_RE` is a module-level compiled regex, so importing the *whole module* may be heavier than needed). **Recommend: copy the ~2-line regex constant into `memory/ingest.py`** rather than import `evidence_registry`, to keep the import surface minimal and unambiguously gate-clean. The regex is locked grammar and rarely changes; if copied, add a comment pointing at the source-of-truth (`evidence_registry.py:133`). `[VERIFIED: evidence_registry.py imports — no live-path runtime import, but copy is cleaner]`
- The runtime (`session_loop.py`, already in the live path) imports `memory.ingest` and calls it inside `run_in_executor`. This is the one-way arrow. The session-close enqueue may be wired here (it touches only the session-end seam) per CONTEXT discretion.

### Hard constraints honored by construction

- Ingest reads dead on-disk artifacts only — never `MusicState`, never `state._lock`, never a live tap. ✅
- `run_in_executor(None, ...)` keeps the blocking FS+embed work off the asyncio reaction loop. ✅
- Single in-flight reaction is untouched — ingest is a separate executor thread on dead data. ✅
- The four cardinal invariants: single-writer (`MusicState` never written), one-socket (no new port), trust-the-audio (memory never overrides live ears — it's write-only in this phase), citation-grounding (Phase 65's concern). ✅

## Architecture Patterns

### System Architecture Diagram (Phase 64 scope — INGEST)

```
   SESSION ENDS                          BOOT (crashed/missed sessions)
   recorder.close() finalizes            run_boot_sweeps()
   session.json + events.jsonl                  │
        │                                        │
   on_session_close (session_loop)         run_ingest_sweep (memory/ingest.py)
        │                                        │  os.scandir recordings_root,
        └──► loop.run_in_executor ◄──────────────┘  skip sessions w/ memory_ingested marker
                     │
                     ▼
   ┌─────────────────────────────────────────────────────────────────────┐
   │ ingest_session(session_dir, store, embedder)   — memory/ingest.py     │
   │                                                                       │
   │  1. marker check ─► already ingested? ─► RETURN (0 embeds, 0 writes)  │
   │  2. read events.jsonl  (clone session_loader _read_events;            │
   │       skip malformed lines; NO 5-min floor)                           │
   │  3. for each EMITTED ai_text line (NOT citation_strip):               │
   │       find nearest preceding `event` line → context                   │
   │       extract inline [source:body] citations from text                │
   │       strip leading [emotion] TTS tag                                 │
   │       build deterministic signature  (PURE STRING — no model)         │
   │       embed_cache_key = SHA256(sig || model || tmpl_ver)              │
   │       ┌─ cache hit  ─► reuse vector (0 API)                           │
   │       └─ cache miss ─► embedder.embed_query(sig)  [FLEX, proxy]       │
   │                         └─► _cache_put                                │
   │       store.add_record(f"{sid}:{seq}", sid, ts, "coach_line",         │
   │                          signature, vector)                           │
   │  4. write memory_ingested(sid, now, tmpl_ver) marker                  │
   └──────────────────────────────────┬────────────────────────────────────┘
                                       │
                              MemoryStore.add_record (Phase 63)
                                       │
                          memory.db  (vec0 / numpy + moments + memory_ingested)

   ❌ NO arrow FROM memory/ingest.py TO: coach loop / MusicState / ws_bus /
      EventDetector / agent / prompts.  Gate-enforced. Runtime → ingest only.
```

### Recommended Project Structure
```
src/vibemix/memory/
├── __init__.py                 # (Phase 63) — optionally export ingest_session
├── store.py                    # (Phase 63) MemoryStore.add_record — write target
├── retention.py                # (Phase 63)
├── index_sqlite_vec_memory.py  # (Phase 63) backend
└── ingest.py                   # NEW (this phase): ingest_session + run_ingest_sweep
                                #   + build_coach_line_signature + the embed cache helper
                                #   + the memory_ingested marker schema
```
Placing ingest inside `memory/` means the shipped `test_no_extraction.py` / `test_no_live_path_import.py` (which glob `src/vibemix/memory/*.py`) **auto-cover it** — no new gate files, lower risk. `[VERIFIED: both gates use MEM.rglob("*.py")]`

### Pattern 1: Deterministic signature builder (pure, model-free)
**What:** a free function `build_coach_line_signature(reaction_line, context_event) -> str` doing only string assembly + regex extraction. No client, no `genai`, no I/O.
**Why:** byte-reproducibility powers the content-hash cache; absence of any generation call satisfies the no-extraction gate by construction.

### Pattern 2: Marker-gated idempotent ingest
**What:** a `memory_ingested(session_id TEXT PRIMARY KEY, ingested_at REAL, sig_template_version TEXT)` table in `memory.db`. `ingest_session` checks it first; a hit (with matching `sig_template_version`) short-circuits before any read/embed.
**Why:** the boot sweep re-runs every boot; without the marker it would re-embed every session every boot (the cache prevents API cost, but the marker prevents even the FS read + cache lookups). Two-layer: marker (skip the session) + embed cache (skip the API call if the marker was lost). A `sig_template_version` mismatch forces re-ingest (template changed).

### Pattern 3: Boot sweep mirrors recordings_index (copy, don't import)
**What:** `run_ingest_sweep(recordings_root, store, embedder)` — `os.scandir` the root, filter `SESSION_DIR_RE`, skip sessions with a marker, `ingest_session` the rest. Best-effort per session (one failure logs + continues).
**Why:** `recordings_index.py` is a runtime utility; importing it from `memory/` is borderline (it imports `vibemix.ui_bus.messages` — check that's gate-safe; if not, copy `SESSION_DIR_RE` + the scandir loop). **Recommend copy** — mirror, don't import, exactly as Phase 63 mirrored the retention/path-traversal idioms (`63-03-SUMMARY.md` patterns-established).

### Anti-Patterns to Avoid
- **LLM-summarizing the session before embedding** ("turn this set into 3 insights") — the headline forbidden move. Signature = raw concatenation only.
- **Embedding `citation_strip` (silenced) lines** — confabulation (the DJ never heard them). Ingest only emitted `ai_text`.
- **Calling `embed_query` without a cache** — re-ingest cost (Finding 2). Always cache-check first.
- **Importing the live reaction path into `memory/ingest.py`** — gate failure. One-way arrow only.
- **Inheriting `session_loader`'s 5-min `SessionTooShort` floor** — that's a debrief-UX rule; ingest should ingest short sessions too (a 3-min set still has callback-able reactions). Re-implement the JSONL read, don't reuse `load_session` wholesale.
- **Putting `t` inside the embedded signature text** — defeats cross-time cache hits; `t` belongs in the `ts` metadata column.
- **A generic ETL framework** — over-engineering. This is one reader + one builder + one writer + one sweep + gates.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSONL parse with malformed-line tolerance | A bespoke parser | Clone `session_loader._read_events` (`session_loader.py:74-88`) — `json.loads` per line, skip+log on `JSONDecodeError` | Crash-truncated last lines are expected; the shipped reader handles them. |
| Citation extraction from text | A new regex | `EVIDENCE_CITATION_RE` (`evidence_registry.py:133`) — copy the constant | Locked grammar; keep in lock-step with the source-of-truth. |
| Text → 768-dim embedding | A new genai client | `LibraryEmbedder.embed_query` (`embed.py:362`) | Proxy-only, FLEX, 768-dim, L2-normalized, GA-rename-probe — all shipped. |
| Content-hash embed cache | A new cache schema | The `embed_cache` table shape (`embed.py:146-157,605-623`) | Proven `(key, vector BLOB, ts)` round-trip. |
| Model id | A literal | `resolve("embedding")` via `LibraryEmbedder` (it already does this internally) | CI gate forbids literals. |
| Write a tagged record | A raw `INSERT` | `MemoryStore.add_record` (`store.py:271`) | Path-traversal-defended, vector-first atomic-ish ordering, tags shipped. |
| Boot crash sweep | A new scanner | Mirror `recordings_index` scandir + `run_boot_sweeps` (`session_loop.py:685`) | `SESSION_DIR_RE` + best-effort per-entry + never-raise shipped. |
| Off-loop dispatch | A new thread pool | `loop.run_in_executor(None, fn)` (`session_loop.py:751`) | The established idiom; the asyncio default executor. |

**Key insight:** This phase has near-zero novel logic. The only genuinely new code is the `coach_line` signature template, the `memory_ingested` marker table, and the signature-keyed embed cache (because `embed_query` lacks one). Everything else is wiring shipped primitives.

## Runtime State Inventory

> This is NOT a rename/refactor — it is a greenfield ingest module writing into the (also-new) `memory.db`. The standard categories mostly do not apply. Verified explicitly:

| Category | Items Found | Action |
|----------|-------------|--------|
| Stored data | `memory.db` `moments` table (Phase 63, write target) + a NEW `memory_ingested` marker table this phase adds. The on-disk session corpus (`~/Library/Application Support/vibemix/recordings/*/events.jsonl`) is the READ source — ~70 real sessions, 327 `event` + 131 `ai_text` lines total. | Add marker table; read corpus (read-only). |
| Live service config | None — ingest reads dead files; no service config carries any string this phase owns. **Verified:** no daemon, no UI-stored config. | None. |
| OS-registered state | None — no Task Scheduler / launchd / pm2 registration. Ingest is in-process, dispatched by the existing session loop. **Verified.** | None. |
| Secrets / env vars | The Bravoh-proxy API key (read by the proxy client, NOT by ingest — `LibraryEmbedder` cannot read a raw key by design, `embed.py:9-12`). No new secret. **Verified.** | None. |
| Build artifacts | None new. `memory.db` is a data file. **Verified — no compiled artifact.** | None. |

**Critical READ-side finding (re-stated):** `evidence_registry.json` is **absent from every session on disk** — the cited evidence lives inline in the `ai_text` `text` field, not in a registry snapshot. Any plan that reads `evidence_registry.json` expecting populated evidence will silently get `{}`. Read citations from the `ai_text` text via `EVIDENCE_CITATION_RE`. `[VERIFIED: find ... -name evidence_registry.json → zero results across the corpus]`

## Common Pitfalls

### Pitfall 1: Re-ingest cost (the `embed_query` no-cache trap)
**What goes wrong:** the boot sweep re-embeds every session every boot because `embed_query` has no cache; €50/mo budget bleeds.
**Why:** `embed_query` (`embed.py:362`) explicitly has no content-hash cache — only `embed_track` does, and it keys on file bytes, not text.
**How to avoid:** the `memory_ingested` marker skips already-done sessions entirely; the signature-keyed embed cache makes any miss (lost marker, template bump) re-embed only changed signatures. Ship BOTH.
**Warning signs:** API embed-call telemetry climbs on every boot with no new sessions.

### Pitfall 2: Embedding silenced reactions
**What goes wrong:** the coach later "remembers" a line the DJ never heard → confabulation, the exact anti-slop failure.
**Why:** stripped reactions are logged as `citation_strip` with `raw_text` (`dj_cohost.py:1123`), which looks reaction-like.
**How to avoid:** ingest ONLY `kind=="ai_text"` lines (emitted/heard). Skip `citation_strip`, `citation_bypass` is a judgment call (the user DID hear bypass lines — `dj_cohost.py:1087`; recommend ingest `ai_text` only for v1 and treat `citation_bypass` raw_text as out-of-scope unless it carries a citation).
**Warning signs:** signatures with empty `said:` text or no inline citation that came from a strip path.

### Pitfall 3: Reading the absent evidence_registry.json
**What goes wrong:** plan reads `evidence_registry.json`, gets `{}`, ships `coach_line` signatures with empty `cite=` for every record.
**Why:** the file does not exist on disk (Finding 1); citations are inline in `ai_text` text.
**How to avoid:** extract citations from `ai_text.text` with `EVIDENCE_CITATION_RE`. Note many lines have ONLY a `[chill]` emotion tag and no real citation — that is FINE; `cite=` is legitimately empty for those, and the reaction text is still callback-able.
**Warning signs:** every record's `cite=` token is empty.

### Pitfall 4: Non-deterministic signature → cache thrash
**What goes wrong:** the signature includes `t` or unsorted citations or the `[emotion]` tag inconsistently → identical reactions hash differently → cache never hits → re-ingest cost.
**How to avoid:** follow the determinism rules in §Signature Template Spec exactly — no `t` in the embedded text, sorted citation tokens, deterministic emotion-tag strip.

### Pitfall 5: Boot sweep blocking startup
**What goes wrong:** ingesting 70 sessions synchronously at boot stalls the session loop before IPC.
**How to avoid:** dispatch via `run_in_executor`; mirror `run_boot_sweeps`'s best-effort, never-raise contract; consider a per-session yield. The marker means steady-state boot ingests 0 sessions.

## Code Examples

### Example: deterministic signature builder (the new logic — model-free)
```python
# src/vibemix/memory/ingest.py  (SHAPE — planner refines)
import re

# Copied from evidence_registry.py:133 (locked grammar; keep in lock-step).
_CITATION_RE = re.compile(r"\[(?:ev|aud|midi|track|screen|mix|tend|key):[^\s,\]]+(?:,(?:ev|aud|midi|track|screen|mix|tend|key):[^\s,\]]+)*\]")
_EMOTION_TAG_RE = re.compile(r"^\[[a-z]+\]\s*")          # [chill] / [hype] TTS directive, NOT a citation
SIG_TEMPLATE_VERSION = "v1-coach_line"

def build_coach_line_signature(reaction_text: str, ctx: dict | None) -> str:
    ctx = ctx or {}
    track = ctx.get("track") or "unknown"
    phase = ctx.get("phase") or "unknown"
    deck  = ctx.get("deck") or "none"
    etype = ctx.get("type") or "MANUAL"
    cites = sorted(m.group(0).strip("[]") for m in _CITATION_RE.finditer(reaction_text))
    said  = _EMOTION_TAG_RE.sub("", reaction_text).strip()
    cite_str = ",".join(cites)
    return (f"coach_line | track={track} | phase={phase} | deck={deck} "
            f"| event={etype} | cite={cite_str} | said: {said}")
```

### Example: idempotency marker schema (new)
```python
# memory_ingested marker — in memory.db (or a sibling owned by ingest)
CREATE TABLE IF NOT EXISTS memory_ingested (
    session_id           TEXT PRIMARY KEY,
    ingested_at          REAL NOT NULL,
    sig_template_version TEXT NOT NULL
);
# ingest_session short-circuits when a row exists with sig_template_version == SIG_TEMPLATE_VERSION.
```

### Example: signature-keyed embed cache (clone of embed.py:605-623)
```python
import hashlib
def _embed_cache_key(signature: str, model_id: str) -> str:
    h = hashlib.sha256()
    h.update(signature.encode()); h.update(b"||")
    h.update(model_id.encode());  h.update(b"||")
    h.update(SIG_TEMPLATE_VERSION.encode())
    return h.hexdigest()
# cache table: embed_cache(key TEXT PRIMARY KEY, vector BLOB NOT NULL, ts REAL NOT NULL)
# hit  -> np.frombuffer(blob, dtype=np.float32).copy()   (0 API calls)
# miss -> vec = embedder.embed_query(signature); cache_put(key, vec)
```

### Example: extending the no-extraction gate (already auto-covers ingest.py)
```python
# tests/memory/test_no_extraction.py ALREADY globs src/vibemix/memory/*.py.
# Adding ingest.py is auto-covered. Add a focused positive test that
# ingest.py imports LibraryEmbedder/embed_query and contains NO
# generate_content / generate_reply / .chats. / GenerateContentConfig.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LLM-extracted session "insights" | Raw `coach_line` text signature embedded verbatim | LOCKED milestone thesis | Confabulation surface structurally removed; CI-gated. |
| Multi-kind taxonomy (`coach_line`+`moment`+`audio_moment`) | ONE kind (`coach_line`); `moment` cut, `audio_moment` deferred | This research (acid test) | Lean retrieval, lower FLEX cost, higher signal density. |
| Read evidence from `evidence_registry.json` | Read inline `[source:body]` citations from `ai_text` text | This research (Finding 1 — the file isn't on disk) | Prevents empty-evidence signatures. |
| `embed_query` "for free" idempotency | Signature-keyed content-hash cache + `memory_ingested` marker | This research (Finding 2) | Re-ingest stays 0-cost. |

**Deprecated/outdated:** none specific. `gemini-embedding-001` literal is a CI canary — never hardcode; `resolve("embedding")` only.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `record_id` `seq` = 0-based index of the emitted `ai_text` line within the session is stable and reproducible. | Signature Template Spec | LOW — the file is append-only; line order is fixed. Re-ingest after a template bump regenerates identical ids. |
| A2 | Sharing the library's `~/.cache/vibemix/embeddings.db` `embed_cache` table for signature embeds is safe (keys are namespaced by distinct text+version). | Embed-cache key | LOW — SHA256 of distinct signature text won't collide with track-bytes keys; planner may use a sibling cache to be conservative. |
| A3 | `citation_bypass` lines (heard-but-uncited) are out of scope for v1 ingest. | Pitfall 2 | LOW — they're rare (23 across the whole corpus) and uncited; including them later is additive. Recommend `ai_text`-only for v1. |
| A4 | Default retention/marker interplay: the Phase 63 retention sweep evicts whole sessions; deleting a session's `moments` should also clear its `memory_ingested` marker (else a re-ingest is blocked). | Pattern 2 | MEDIUM — if the marker outlives the moments, an evicted-then-revisited session won't re-ingest. **Plan must clear the marker in `delete_session`'s cascade OR check moment existence alongside the marker.** Flag for the planner. |
| A5 | Copying `EVIDENCE_CITATION_RE` into `ingest.py` (vs importing `evidence_registry`) is the gate-safe choice. | Off-Hot-Path Execution | LOW — `evidence_registry.py` has no live-path runtime import, so an import would also pass the gate; copy is just cleaner/lighter. |

## Open Questions

1. **Marker ↔ retention coupling (A4).**
   - What we know: Phase 63 `delete_session` cascades vectors + `moments`; it does NOT know about a `memory_ingested` table this phase adds.
   - What's unclear: whether to (a) add a `memory_ingested` delete to `delete_session` (touches Phase-63 code), or (b) gate ingest on `moments`-existence-for-session rather than a standalone marker, or (c) make the marker a row whose absence-of-moments is reconciled at boot.
   - Recommendation: **(b) or (c)** — keep `delete_session` untouched. Either check "does this session already have moments rows?" (cheap COUNT) as the idempotency signal, or reconcile the marker against `moments` in the boot sweep (drop markers for sessions with 0 moments). Planner picks; prefer the one that doesn't modify shipped Phase-63 code.

2. **Import vs mirror `session_loader` / `recordings_index`.**
   - What we know: both are gate-safe to import (neither pulls the live reaction path), but both carry UX-shaped behavior (5-min floor; `ui_bus.messages` import).
   - Recommendation: re-implement the ~12-line malformed-tolerant JSONL read inline (or factor a shared `_read_events_jsonl`); copy `SESSION_DIR_RE` + the scandir loop. Mirror, don't import — matches Phase 63's established "copy the FS-safety shapes" pattern.

3. **Where the boot ingest sweep is triggered.**
   - What we know: `run_boot_sweeps` (`session_loop.py:685`) is the existing boot seam; it runs retention. Adding ingest there is natural but mixes concerns.
   - Recommendation: add a sibling boot call (`run_ingest_sweep` via `run_in_executor`) either inside `run_boot_sweeps` or as a parallel boot step in `run()`. Planner's discretion; must stay best-effort + never-raise.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `MemoryStore` (Phase 63) | write target | ✓ | shipped (`memory/store.py`) | none needed — it's in-repo, 19/19 tests GREEN |
| `LibraryEmbedder` + Bravoh proxy | embedding signatures | ✓ | shipped (`library/embed.py`) | at test time use synthetic 768-dim vectors; no live API needed for unit tests |
| `google-genai` + proxy | the FLEX embed call (production) | ✓ | `2.0.1` | none at store/ingest layer — embed is the only network call, identical to library import |
| Real session corpus (`recordings/*/events.jsonl`) | grounding the signature template | ✓ | ~70 sessions on the dev box | tests use synthetic events.jsonl fixtures |
| `ffmpeg` | NOT required (text-signature only; no audio embed in v1) | n/a | — | n/a |
| sqlite-vec extension | (inherited via MemoryStore) | ✓ dev / ✗ Win ARM64 | `0.1.9` | `NumpyStore` fallback (parity-identical) — Phase 63 handles this |

**Missing dependencies with no fallback:** none — unit tests run on synthetic vectors + synthetic events.jsonl; no live API required.
**Missing dependencies with fallback:** sqlite-vec on Win ARM64 → numpy backend (Phase 63 already abstracts this).

## Validation Architecture

> `workflow.nyquist_validation` not set to false → section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` 9.x (already dev dep) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`; `--strict-markers` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/memory` |
| Full suite command | `uv run pytest -q` (or `PYTHONPATH=src python3 -m pytest -q`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INGEST-01 | `build_coach_line_signature` is deterministic (same fields → same bytes) | unit | `pytest tests/memory/test_ingest.py::test_signature_deterministic -x` | ❌ Wave 0 |
| INGEST-01 | ingest reads events.jsonl, emits one `coach_line` per emitted `ai_text`, skips `citation_strip` | unit | `pytest tests/memory/test_ingest.py::test_ingest_emits_coach_lines -x` | ❌ Wave 0 |
| INGEST-01 | `ingest.py` references NO generation surface (only `embed_content`/`embed_query`) | unit (static, auto-covered) | `pytest tests/memory/test_no_extraction.py -x` | ✅ (globs memory/*.py — verify it now sees ingest.py) |
| INGEST-02 | `ingest.py` imports no live-reaction-path module | unit (static + subprocess) | `pytest tests/memory/test_no_live_path_import.py -x` | ✅ (globs memory/*.py — auto-covers ingest.py) |
| INGEST-02 | session-close + boot sweep dispatch through `run_in_executor` (not inline) | unit | `pytest tests/memory/test_ingest.py::test_sweep_uses_executor -x` (or assert no live-path call) | ❌ Wave 0 |
| INGEST-03 | re-ingest of a marked session = 0 embed calls, 0 new records (idempotent) | unit | `pytest tests/memory/test_ingest.py::test_reingest_is_noop -x` | ❌ Wave 0 |
| INGEST-03 | every record carries `session_id` + `ts` + `kind=="coach_line"` | unit | `pytest tests/memory/test_ingest.py::test_records_tagged -x` | ❌ Wave 0 |
| INGEST-03 | embed cache hit on identical signature → 0 API calls | unit | `pytest tests/memory/test_ingest.py::test_embed_cache_hit -x` | ❌ Wave 0 |
| (cross) | no hardcoded model literal in ingest.py | unit (static, shipped gate) | `pytest tests/repo/test_model_literal_gate.py -x` | ✅ (scans all of src/vibemix/) |

### Sampling Rate
- **Per task commit:** `PYTHONPATH=src python3 -m pytest -q tests/memory` (sub-second).
- **Per wave merge:** `tests/memory/` + `tests/repo/test_model_literal_gate.py` + the two memory gates.
- **Phase gate:** full suite green before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/memory/test_ingest.py` — signature determinism, coach_line emission, skip-citation_strip, idempotent re-ingest, tagging, embed-cache hit, executor dispatch.
- [ ] A synthetic `events.jsonl` fixture (mirror the real on-disk shapes documented above: `event` lines with `type/track/phase/deck`, `ai_text` lines with `[emotion]`-prefixed text + optional `[aud:rms@…]` citation, plus a `citation_strip` line to assert it's skipped). Generate in-test to keep the repo lean.
- [ ] Verify the shipped `test_no_extraction.py` / `test_no_live_path_import.py` flip from passing-vacuously-over-existing-files to actively covering the new `ingest.py` (they will — both glob `memory/*.py`).
- Framework install: none.

## Security Domain

> `security_enforcement` not set to false → included. Local-only file ingest; no auth, no sessions, no web tier.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — local single-user ingest. |
| V3 Session Management | no | "session" = DJ-set dir, not a web session. |
| V4 Access Control | no | Single-user per-install. |
| V5 Input Validation | **yes** | `session_id` path-traversal: `MemoryStore.add_record` already validates it (`store.py:302`). The boot sweep must apply `SESSION_DIR_RE` (`^\d{8}-\d{6}$`) + `is_relative_to(root.resolve())` before reading any session dir (copy from `recordings_index.py:388-401`). JSONL lines are parsed with `json.loads` per line + skip-on-error (no `eval`, no schema-trust). |
| V6 Cryptography | no | No crypto; the proxy holds the API key (`LibraryEmbedder` cannot read a raw key by design). SHA256 here is a cache key, not a security control. |
| V12 File / Resource | **yes** | Reads confined to `recordings_root` (under `app_data_dir()`); writes confined to `memory.db` + cache. **Never** read/write the off-limits Hermes/LM-Studio privacy paths. The boot sweep `os.scandir`s only the recordings root. |

### Known Threat Patterns for {local session-artifact ingest + embedding}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| **Confabulation via a generation call in the ingest path** (the headline threat) | Spoofing (fabricated "facts") | **No-extraction static gate** — `ingest.py` calls only `embed_content`/`embed_query`; `test_no_extraction.py` (auto-covers `memory/*.py`) fails the build on any `generate_content`/`generate_reply`/`.chats.`/`GenerateContentConfig`. This is THE invariant the milestone forbids breaking. |
| Embedding a silenced (never-heard) reaction | Spoofing | Ingest `ai_text` (emitted) only; skip `citation_strip`. The coach can only "remember" what the DJ actually heard. |
| Path traversal via crafted session dir name (boot sweep) | Tampering / EoP | `SESSION_DIR_RE` + `is_relative_to(recordings_root.resolve())` before any read; `MemoryStore` re-validates `session_id` on write. |
| Malformed/oversized `events.jsonl` (crash-truncated, partial last line) | DoS / integrity | Per-line `json.loads` + skip-on-error (clone `_read_events`); per-session best-effort in the sweep (one bad session never blocks others or boot). |
| Memory writes leaking outside the sanctioned dir | Information disclosure | All paths derive from `app_data_dir()`; never the privacy paths. Reads scoped to recordings_root. |
| Live-path coupling via ingest import | Tampering (invariant break) | No-live-path import gate (`test_no_live_path_import.py`, auto-covers `ingest.py`); one-way runtime→ingest arrow only. |

## Project Constraints (from CLAUDE.md / memory)

- **Gemini-only.** Embedding = `gemini-embedding-2` via `resolve("embedding")`; no CLAP/MERT/torch (locked). No audio embedding in v1.
- **No managed memory frameworks.** DIY only — this phase reuses the Phase-63 DIY store.
- **No-LLM-extraction.** The ingest path's only model call is `embed_query`; the no-extraction CI gate is the hard enforcement.
- **Four cardinal invariants preserved by construction:** single-writer (ingest never writes `MusicState`), one-socket (no new port), trust-the-audio (memory is write-only here), citation-grounding (Phase 65's concern — ingest only stores raw signatures + their inline citation tokens).
- **No scope creep / clean utility.** ONE kind (`coach_line`); no generic ETL; no `moment`/`audio_moment` in v1.
- **Strict per-file staging.** Commit `ingest.py`, its tests, and any runtime wiring as separate scoped commits.
- **GSD workflow enforcement.** Phase work under `.planning/phases/64-session-ingest/`.
- **Frontend skill: N/A.** Phase 64 is headless backend ingest — no UI, no HTML/CSS/JS. The `frontend-enforcement` skill does not apply. (Pill/mascot citation surfaces are Phase 65/66 territory.)

## Sources

### Primary (HIGH confidence — read from live source + real corpus 2026-05-22)
- `src/vibemix/memory/store.py` (`MemoryStore.add_record` write target, `record_id` scheme, `_validate_session_id`, `moments` shape) — write target
- `src/vibemix/memory/__init__.py` + `63-03-SUMMARY.md` + `63-RESEARCH.md` (Phase 63 contract, lazy-import invariant, mirror-not-import discipline) — composition rules
- `src/vibemix/library/embed.py` (`LibraryEmbedder.embed_query` — NO cache; `embed_track` cache key; `embed_cache` table; `resolve("embedding")`) — Finding 2 + embed seam
- `src/vibemix/debrief/session_loader.py` (`_read_events` malformed-tolerant JSONL parse; optional `evidence_registry.json`; 5-min floor) — reader analog + Finding 1
- `src/vibemix/debrief/chapters.py` + `main.py:143` (`_build_cited_critique` — proves `ai_text` lines carry inline citations; event-kind/type mapping) — taxonomy grounding
- `src/vibemix/agent/dj_cohost.py:1054,1087,1123,1150` (`ai_text` logged on emit/bypass; `citation_strip` on silence) — emit-vs-silence distinction
- `src/vibemix/audio/recorder.py:295-326` (`log_event` → `{t, kind, **fields}` JSONL shape; `t = round(rel, 3)`) — on-disk record shape
- `src/vibemix/state/event.py` (7 canonical event types) + `state/event_detector.py:456` (`_fire` writes `[ev:<TYPE>@<t>]`) — event taxonomy
- `src/vibemix/state/evidence_registry.py:103,133` (`EVIDENCE_SOURCES`, `EVIDENCE_CITATION_RE` locked grammar; `snapshot` shape) — citation extraction
- `src/vibemix/runtime/session_loop.py:685,709,751,1132,1212` (`run_boot_sweeps`, `on_session_close`, `run_in_executor` dispatch, boot/close call sites) — off-hot-path seams
- `src/vibemix/runtime/recordings_index.py:78,120,490` (`SESSION_DIR_RE`, `_scandir_size_sum`, `run_retention_sweep`, two-layer path-traversal gate) — boot-sweep mirror
- `src/vibemix/llm/_router_config.py:40` (`"embedding" → ("gemini-embedding-2", ServiceTier.FLEX)`) — embed routing
- `tests/memory/test_no_extraction.py` + `test_no_live_path_import.py` (the gates; both glob `memory/*.py` → auto-cover ingest.py) — CI gates
- **Real corpus:** `~/Library/Application Support/vibemix/recordings/` — ~70 sessions; verified event/ai_text/citation_strip line shapes, distinct event types, and the ABSENCE of any `evidence_registry.json`
- `.planning/REQUIREMENTS.md` (INGEST-01..03), `.planning/ROADMAP.md:42-73` (Phase 64 + acid test + Phase 66 moves), `64-CONTEXT.md` (locked decisions)

### Secondary (HIGH — milestone research, corroborated by source)
- `.planning/research/{SUMMARY,ARCHITECTURE,PITFALLS}.md` (reuse thesis; STORE→INGEST→RETRIEVE→COPILOT spine)

## Metadata

**Confidence breakdown:**
- Standard stack / reuse: HIGH — every primitive read from shipped source; Phase 63 is GREEN.
- Taxonomy decision (`coach_line` only): HIGH — derived from the acid test against the locked Phase-66 moves + the real corpus (which proves `ai_text` carries the callback-able language and bare events don't).
- Signature template: HIGH — every field grounded in actual on-disk `event`/`ai_text` line shapes.
- Idempotency (Finding 2): HIGH — `embed_query` no-cache confirmed in source; the fix is a verbatim clone of the `embed_track` cache mechanism.
- Pitfalls / security: HIGH — all map to shipped patterns + the locked no-extraction rule; the absent-evidence-registry finding is filesystem-verified.

**Research date:** 2026-05-22
**Valid until:** ~2026-06-21 (stable — built on shipped in-repo primitives + a fixed on-disk artifact shape; drifts only if `recorder.log_event` shape, `EVIDENCE_CITATION_RE`, or the Phase-63 store API change).
