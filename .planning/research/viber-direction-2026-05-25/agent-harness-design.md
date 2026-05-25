# vibemix — Per-User Agentic Playlist Curator: Harness Design

**Status:** Design research (read-only). 2026-05-25.
**Scope:** A simple, per-user agentic harness *inside* vibemix that autonomously curates/organizes
playlists from the user's own library — instead of hand-coding a next-song sequencing algorithm.
**One-liner direction (owner):** "Think a simple Hermes-style agent, per user."

---

## 0. TL;DR Recommendation

Build a **bounded Gemini function-calling agent** over a small, typed, read-mostly tool surface that
maps 1:1 to vibemix functions that *already exist*. **Do NOT build a code-writing (Codex-style) agent.**

The agent gets a seed/theme, plans in 1–2 LLM turns, calls deterministic tools (`search_vibe`,
`find_similar`, `get_track_features`, `filter_by_key_bpm`, `order_by_energy_and_key`), and emits a
playlist of **real track IDs that came back from those tools** — never IDs it invented. A final
`create_playlist` tool is the only write, and it validates every track ID against the library before
persisting. This is the minimal surface that satisfies "make sense semantically + technically" while
honoring vibemix's anti-slop / grounding / no-scope-creep / one-click-install / €-cost constraints.

This is essentially the **AIRA pattern minus the server/persona/WhatsApp infra** — a tool-calling
loop over a fixed registry, scoped per user — which is exactly what the owner asked for.

---

## 1. Code-writing (Codex) vs Tool-calling (Gemini function-calling)

| Dimension | Code-writing agent (Codex-style) | **Tool-calling agent (Gemini function-calling)** |
|---|---|---|
| What it does | LLM writes + runs Python per task | LLM selects from a fixed, typed tool set; vibemix runs the code |
| Power ceiling | Very high (arbitrary logic) | Bounded to the tools you ship |
| Grounding | Weak by default — generated code can fabricate, query the wrong thing, or "synthesize" tracks | Strong — tools only return real library rows; agent can only reference what tools returned |
| Install weight | Needs a sandbox/jail (subprocess isolation, resource limits) → heavy on a shipped desktop binary | Zero extra runtime — it's just `generate_content(..., tools=[...])` over `google-genai` (already a dep) |
| Security | Arbitrary-code-exec inside the user's machine; a real attack surface for an OSS binary | No code-exec; the only side effect is writing a playlist file the user asked for |
| Cost (€) | Higher — codegen burns more tokens + may re-run/retry code | Low — short JSON tool-calls; embeddings are **cached locally** (`embeddings.db`), so reasoning is the only spend |
| Scope-creep risk | High — a code agent invites "let it do anything" | Low — the tool list *is* the scope contract; adding a capability is a deliberate new typed tool |
| Fit for "clean utility" | ✗ | ✓ |

**Verdict: tool-calling, decisively.** A playlist curator is a *retrieval + filter + ordering* problem
over a closed catalog — the textbook case where a fixed tool set beats codegen. The code-writing
agent's only advantage (arbitrary logic) is a liability here: it's the most direct path to the exact
failure mode vibemix forbids (inventing tracks, "you might also like" slop, hallucinated BPM/key).

**Why Gemini function-calling specifically fits vibemix:**
- `google-genai` is already the **sole** AI dep — no new provider, no Bravoh-policy violation.
- The codebase already runs the exact primitive the loop needs: `client.models.generate_content(...)`
  with `response_mime_type: "application/json"` + Pydantic validation
  (`src/vibemix/debrief/drills.py:219-244`, `src/vibemix/debrief/tldr.py:123-216`). Native Gemini
  `tools=[FunctionDeclaration(...)]` + manual dispatch is a small step from this — no framework.
- Model resolution already config-driven via `model_router.resolve(...)`
  (`src/vibemix/llm/model_router.py:44`); add one route `library_agent` →
  `_router_config._ROUTES` (`src/vibemix/llm/_router_config.py:26`). **No hardcoded model literal**
  (CI grep-gated).
- Embeddings are **already cached on disk** (`~/.cache/vibemix/embeddings.db`,
  `embed.py:150`), so the agent's tool calls are local + free; only the planning text costs tokens.

---

## 2. The Tool Surface (minimal, typed, mostly read-only)

Six tools. All but the last are pure reads over already-built functions; the last is the single,
validated write. Every tool returns **real track IDs from the library** — the grounding spine.

| Tool (FunctionDeclaration) | Purpose | Backed by (file:line) |
|---|---|---|
| `search_vibe(query: str, k: int)` | NL → seed candidates by semantic vibe | `library/search.py:84` `vibe_search(...)` (mean-centered, 24h-cached) |
| `find_similar(track_id: str, k: int)` | Expand from a seed track by embedding similarity | `library/similar.py:45` `similar_to(...)` (mean-centered) |
| `get_track_features(track_id: str)` | BPM / key→Camelot / genre / duration / cues for one track | `library/rekordbox.py:69` `TrackEntry` (+ `lookup_by_id` :233); `state/harmonics.py:83` `to_camelot(...)`; folder tracks have bpm/key empty → honest `null` |
| `filter_by_key_bpm(track_ids, bpm_min, bpm_max, key=None)` | Technical winnowing of a candidate pool | new ~30-line pure helper over `TrackEntry.bpm` + `harmonics.compatible(...)` (`state/harmonics.py:196`) |
| `order_by_energy_and_key(track_ids)` | Sequence the chosen set into a mixable order | new pure helper: greedy nearest-neighbour on `harmonics.is_clash`/`compatible` (`harmonics.py:196,219`) + BPM monotonic ramp |
| `create_playlist(name, track_ids)` | Persist the curated list (the ONLY write) | **new** — validates every id via `RekordboxLibrary.lookup_by_id`; writes M3U/JSON to `~/.cache/vibemix/playlists/` |

**What already exists vs what's new:**
- Exists, reuse as-is: `vibe_search`, `similar_to`, `TrackEntry`/`lookup_by_id`, the full Camelot
  predicate kit (`to_camelot`, `compatible`, `is_clash`, `semitone_distance`).
- New, but trivial pure functions: `filter_by_key_bpm`, `order_by_energy_and_key`, `create_playlist`.
  **No playlist/M3U writer exists today** (grep found none) — `create_playlist` is the one genuinely
  new persistence path. Genre is available per-track only for live audio
  (`state/genre/genre_autodetect.py`); library tracks expose genre only if Rekordbox tagged it, so
  `get_track_features` returns genre as best-effort/null (honest-unknown, never guessed).

**Hard tool-contract rules (enforce in the dispatcher, not the prompt):**
1. Any `track_id` the agent passes to `filter_*`/`order_*`/`create_playlist` MUST have come from a
   prior `search_vibe`/`find_similar` result *in this session*. IDs not in the session's seen-set are
   rejected → the agent cannot smuggle in invented tracks. **This is the citation-grounding invariant
   (Cardinal Invariant #2) applied to the agent.**
2. `create_playlist` re-validates every id against the live library and drops/aborts on any miss.
3. Tools never autosurface — `similar_to` already documents this anti-feature guard
   (`library/similar.py:1-14`); the agent is an explicit user-invoked flow, not a background loop.

---

## 3. The Loop (bounded + grounded + per-user)

```
INPUT:  seed/theme  (NL string e.g. "warm-up set, hypnotic, 122-126, ~70 min")
        + user scope (which library cache / which user profile)

PLAN (LLM turn 1, function-calling):
  agent reads the theme, calls search_vibe(query, k=~25)  → seed pool (real IDs)
  optionally find_similar(best_seed, k) to widen          → candidate pool

FILTER (tool calls, deterministic):
  filter_by_key_bpm(candidates, bpm range, optional key)  → technically-valid pool
  get_track_features on a few to reason about contour     → grounded facts

SEQUENCE (tool call, deterministic):
  order_by_energy_and_key(chosen_ids)                     → mixable order
    (greedy: BPM ramp + Camelot-compatible adjacency, is_clash=hard-avoid)

EMIT (LLM turn 2 → single write):
  create_playlist(name, ordered_ids)                      → validated, persisted

OUTPUT: playlist file + a short rationale ("122→125 ramp, all 8A/9A/8B neighbours")
```

**Bounds (cost + safety):**
- Hard cap on tool-call iterations (e.g. ≤ 8) and one `create_playlist` per run.
- Single in-flight generation (mirror the existing `in_flight` discipline in the agent loop).
- Target length / BPM window / key come from the theme; the agent fills, it does not invent tracks.
- All embedding work hits the local cache → typical run = a handful of cheap text turns (well within
  the ~50 €/mo budget; embeds are already paid for at ingest time).

**Per-user scope:** "per user" here = per-library + per-profile, all **local**. Scope = the user's
`library.pkl` + `embeddings.db` (`~/.cache/vibemix/`) + their long-term DJ profile (`profile/`).
There is no multi-tenant server; each desktop install is its own single user. The agent reads that
user's library and writes that user's playlists folder — nothing crosses machines. (Contrast AIRA,
which is genuinely multi-tenant on a server; vibemix doesn't need that.)

---

## 4. AIRA Reuse — what transfers, what doesn't

**Source:** `agentanalytics/CLAUDE.md` "AIRA Agent Platform" section (L774-816) + the 37-tool MCP
registry it describes. AIRA = a Hermes-based agent: a brain (codex/gpt-5.5, deepseek fallback) driving
a **fixed registry of typed tools** (`aa_query_duckdb_readonly`, `aa_kb_search`, `aa_send_audio_to_wa`,
…) over a tool-calling loop, with a 3-layer prompt (`SOUL.md` persona / `AGENTS.md` canon /
`skills/*` intent recipes) and per-session state in `state.db`.

**Transfers (conceptually):**
- **The core pattern itself:** tool-calling loop over a *fixed, typed, read-mostly* registry, with
  the one mutating tool tightly scoped. This is exactly the playlist-curator shape.
- **Read-only-by-default tool discipline:** AIRA's data tool is `aa_query_duckdb_readonly` — reads
  can't corrupt state. vibemix's analogue: every tool but `create_playlist` is a pure read.
- **Skills-as-intent-recipes layering:** AIRA puts "infra bugs in skills, persona in SOUL." vibemix
  can mirror this lightly — a short system prompt (persona/tone, reused from `coach/`/`prompts/`
  per user level) + a small "curation recipe" prompt block (the §3 loop spelled out) + the tool
  schemas. No need for AIRA's full 3-file split.
- **Grounding-via-tools:** AIRA's anti-bias fix (gotcha #58) was "the model can't reproduce ground
  truth → make it *verify at runtime via tools* instead of defaulting." Same lesson: the playlist
  agent must *retrieve* tracks via tools, never list them from memory.

**Does NOT transfer (and shouldn't — scope-creep traps):**
- Server/Docker/Hermes runtime, container volumes, env-shovel, `state.db` persona caches, MCP
  reconnect machinery, WhatsApp bridge, multi-tenant profiles. vibemix is a single-user desktop
  sidecar — none of that infra applies.
- A separate brain provider (codex/deepseek). vibemix is **Gemini-only**; use Gemini
  function-calling. No second provider, ever.
- Long-lived self-modifying persona files / autonomous background operation. The curator is an
  explicit, user-invoked, short-lived run — not a daemon.

**Net:** reuse the *idea* (typed tool-calling loop, read-only default, grounding via retrieval,
light persona layer), drop the *plumbing* (server, MCP transport, multi-tenant, second LLM).

---

## 5. Risk Register & how the simple design defuses each

| Risk | How tool-calling design avoids it |
|---|---|
| **Scope creep** | The tool list *is* the scope. Six tools, one of them a validated write. New capability = a deliberate new typed tool reviewed against "clean utility." No codegen = no "it can do anything" drift. |
| **Slop / hallucination** | Agent can only reference IDs returned by tools (session seen-set enforced in dispatcher); `create_playlist` re-validates against the library. Key math is deterministic (`harmonics.py`), never LLM-computed — same contract as the live coach. Honest-`null` for missing bpm/key/genre. |
| **€-cost** | Embeddings cached locally (`embeddings.db`); the run is a few short JSON text turns on Flash via the FLEX tier route. No per-tick cost, no codegen retries. |
| **Install weight** | No sandbox, no new dep — it's `generate_content(tools=[...])` on the `google-genai` client already shipped. One-click install unaffected. |
| **Security (OSS binary)** | No arbitrary code execution. The only write is a playlist file in the user's own cache dir, gated on library validation. API key stays behind the planned Bravoh proxy (no raw key in the loop). |
| **"Single source of truth" / invariants** | Agent is read-only against `MusicState` (never writes it — Invariant #1 intact). Citation-grounding (Invariant #2) is reused verbatim as the seen-set rule. |

---

## 6. Phased build plan

**Phase 1 — smallest shippable agent (the wedge).**
- Tools: `search_vibe`, `get_track_features`, `create_playlist` (3 only).
- Loop: theme → `search_vibe(k)` → present candidates → `create_playlist`. No auto-sequencing yet
  (preserve `search_vibe`'s confidence order, or sort by BPM).
- New code: `create_playlist` (M3U/JSON writer + id validation) + a ~120-line
  `library/agent.py` harness (FunctionDeclaration schemas, dispatch loop, seen-set guard, iteration
  cap). Add `library_agent` route to `_router_config`. CLI entry `vibemix library curate "<theme>"`.
- Ship gate: every emitted track resolves in the library (zero invented IDs across a test corpus) —
  the anti-slop gate, reusing the citation-grounding test idiom.

**Phase 2 — technical coherence.**
- Add `find_similar` (seed expansion) + `filter_by_key_bpm`. Agent can now widen then winnow.

**Phase 3 — mixable ordering.**
- Add `order_by_energy_and_key` (greedy Camelot-adjacent + BPM ramp using `harmonics.compatible`/
  `is_clash`). Output a short human rationale. This is the "makes sense technically" payoff.

**Phase 4 (optional) — per-user taste.**
- Feed the user's `profile/` long-term DJ profile + (gated) `memory/` recall into the system prompt
  so curation leans toward their style. Stays read-only; reuses existing modules.

**Later / explicitly NOT now:** Rekordbox-XML write-back of playlists (the master.db-write-unsafe
problem — keep export to neutral M3U/JSON), any background/auto-curation, any second provider.

---

## 7. Key file references

- `src/vibemix/library/search.py:84` — `vibe_search` (→ `search_vibe` tool)
- `src/vibemix/library/similar.py:45` — `similar_to` (→ `find_similar` tool; note anti-autosurface guard L1-14)
- `src/vibemix/library/rekordbox.py:69` `TrackEntry` / `:233` `lookup_by_id` (→ `get_track_features`, id validation)
- `src/vibemix/library/folder_ingest.py` — folder-ingested tracks (bpm/key empty → honest null)
- `src/vibemix/state/harmonics.py:83` `to_camelot`, `:196` `compatible`, `:219` `is_clash`, `:179` `semitone_distance` (deterministic key math)
- `src/vibemix/state/genre/genre_autodetect.py` — live genre (library genre best-effort only)
- `src/vibemix/library/store.py:63` `search_centered` / `embed.py:150` `EMBED_CACHE_DB_PATH` (local cached embeddings)
- `src/vibemix/llm/model_router.py:44` `resolve` / `llm/_router_config.py:26` `_ROUTES` (add `library_agent` route)
- `src/vibemix/debrief/drills.py:219` / `debrief/tldr.py:123` — existing `generate_content` + JSON-schema pattern to extend with `tools=`
- `agentanalytics/CLAUDE.md:774-816` — AIRA pattern reference (tool-calling loop, read-only default, 3-layer prompt)
