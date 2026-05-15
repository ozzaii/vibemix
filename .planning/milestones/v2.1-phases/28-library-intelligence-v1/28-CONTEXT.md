# Phase 28: Library Intelligence v1 - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — recommended decisions locked at Claude's discretion)

<domain>
## Phase Boundary

vibemix's spoken reactions can cite tracks from the user's library by name + the user can vibe-search the library in plain English — closing the architectural-slot reservation left in v2.0 Phase 25 (LIBRARY-08) with a full feature surface.

**Mapped REQ-IDs (9):** LIBRARY-10, LIBRARY-11, LIBRARY-12, LIBRARY-13, LIBRARY-14, LIBRARY-05 (carry-forward drag-drop UX), LIBRARY-15, LIBRARY-16, LIBRARY-17.

**In scope:**
- Gemini Embedding 2 client (`src/vibemix/library/embed.py`) with content-hash cache, batch ingest, 180s cap-aware 3-excerpt strategy.
- sqlite-vec index (Mac) + numpy fallback (Windows) — identical cosine, stable argsort, float32.
- Library vibe-search query — natural-language English → top-K matches with confidence; CLI + IPC.
- "What's playing" grounding — audio embedding of currently playing track (3-excerpt) → cosine top-K against library → `[track:<id>]` citation at ≥ 0.7.
- Track-to-track similarity — top-K against active deck embedding (USER-ASKED only, never prescriptive).
- Settings → Library tab drag-drop + file-picker + import progress.
- 30-day staleness nudge — UI prompt when stale.
- Cost projection — 24h query cache + sampled grounding + content-hash dedupe; budget ≤ €50/month.
- 4 new IPC schemas on existing ws_bus port 8765 — `ipc.library.import_progress`, `ipc.library.search_result`, `ipc.library.confidence`, `ipc.library.staleness_nudge`.

**Out of scope:**
- "AI suggests next track" prescription (explicit anti-feature watch — only surface on user ask).
- Rekordbox XML re-parse (v2.0 Phase 25 already ships the parser; Phase 28 consumes its output).
- New ports/buses (everything piggybacks on port 8765).
- CLAP embeddings (memory `feedback_no_clap_use_gemini_embedding` — Gemini-only).
- Stems separation, audio fingerprinting (deferred).

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion (locked per gsd-autonomous fully)

All implementation choices at Claude's discretion, grounded in:
- ROADMAP Phase 28 success criteria (verbatim)
- REQUIREMENTS.md LIBRARY-10..17 + LIBRARY-05
- Pitfalls P48 (orphan), P54 (180s cap), P55 (Mac/Win divergence), P56 (cost runaway)
- v2.0 Phase 25 register_library slot + Rekordbox parser (already shipped)
- Memory `project_gemini_embedding_2` — Gemini Embedding 2 is THE embedding for vibemix
- Memory `feedback_no_clap_use_gemini_embedding` — no alt providers

### Embedding model
- **`gemini-embedding-001` (Gemini Embedding 2)** via google-genai SDK `embed_content`. Output dimensionality = 768 (default; supports 3072 but 768 is cost-balanced).
- **Audio embeddings:** Gemini Embedding 2 is natively multimodal — accepts audio Parts up to 180s. Per memory `project_gemini_embedding_2`.
- **3-excerpt strategy (Pitfall P54):** for tracks > 180s, embed 3 excerpts (intro 0-60s, mid 60-120s, outro -60s-end) and average vectors. Configurable via `EMBED_EXCERPT_COUNT` env.

### Storage backend
- **macOS:** sqlite-vec extension via `sqlite-vec==0.1.9` Python binding (locked in STATE.md v2.1 deps). DB path: `~/.cache/vibemix/library.db`.
- **Windows:** numpy fallback (`vibemix/library/index_numpy.py`). DB path: same. Format = sidecar pickle `library_vectors.npy` + JSON metadata.
- **Identical cosine + stable argsort (Pitfall P55):** dedicated `cosine_topk(query, vectors, k)` function shared across both backends. Float32 enforced everywhere. Test parity via fixture-based cross-validation (`test_topk_parity_mac_vs_win.py`).

### Content-hash dedupe + cache (Pitfall P56)
- Track key = SHA256 of (file content + Gemini model ID + excerpt strategy version).
- Hit cache → skip API call. Miss → embed + persist.
- 24h query cache for vibe-search: SHA256(query text + library snapshot hash) → cached top-K result.
- Budget table: tracks/month, queries/month, grounding-frames/sec → projected cost. CI test asserts projection ≤ €50.

### "What's playing" grounding (LIBRARY-13)
- Subscribed to live audio at 3 excerpts/min (sampled, not continuous → Pitfall P56 cost).
- Cross-reference excerpt embedding vs library top-K (k=10).
- `[track:<id>]` citation emitted when top match cosine ≥ 0.7. 0.6-0.7 = "uncertain" (no citation).
- Citation flows into Gemini prompt as audio Part anchor + text reference (per memory `feedback_mic_audio_as_multimodal_part`).

### Vibe-search (LIBRARY-12)
- CLI: `vibemix library search "driving acid techno around 138 BPM, dark intro"` → JSON top-K with `{track_id, title, artist, bpm, confidence, snippet}`.
- IPC: `ipc.library.search_result` on port 8765 — renderer subscribes from Tauri.
- Query embedded via Gemini Embedding 2 (text mode). 24h cache.

### Drag-drop UX (LIBRARY-05)
- Tauri Settings → Library tab. React component with drag-target + file-picker fallback (per memory `project_visual_direction_cdj_whisper` — Pioneer-grade restraint, single amber accent on import progress bar).
- Import progress via `ipc.library.import_progress` — emits `{total, done, current_track_name}` per track.
- Cancel button — sets `cancel_flag` consumed by importer worker.

### Staleness nudge (LIBRARY-15)
- Background poll: last `library_import_timestamp` > 30 days → emit `ipc.library.staleness_nudge` → UI banner.
- Snooze for 7 days on dismiss; persistent in `~/.config/vibemix/state.json`.

### Track-to-track similarity (LIBRARY-14)
- USER-ASKED only. Surfaces via `vibemix library similar <track_id>` CLI + IPC `ipc.library.similar_request` → `ipc.library.similar_result`.
- Active-deck binding: when MIDI controller signals a deck has loaded a known library track, prepare suggestion cache for that track's similar-K. UI does NOT autosurface — only on explicit ask.

### IPC schemas (LIBRARY-17)
- All on port 8765 (no new ports — STATE.md decision).
- Versioned via top-level `schema_version: "1"` field.
- Definitions in `src/vibemix/ipc/schemas/library.py` (pydantic models) + TS counterparts in `frontend/src/types/library.ts` (auto-generated via pydantic-to-typescript).

### Visual direction (memory)
- Per memory `project_visual_direction_cdj_whisper`: Pioneer-grade hardware in library mode. 5 warm blacks, single amber accent (4 intensities). Mocks/vibemix-direction-final.html is baseline.
- Import progress bar: thin 2px line, amber-1 background → amber-3 fill. No gradient flash.
- Match confidence: text-only badge "0.83" no progress bar.

</decisions>

<code_context>
## Existing Code Insights

- **`EvidenceRegistry.register_library`** (defined in v2.0 Phase 25, wired in Phase 27 — research-verified at `evidence_registry.py:168`, invocation at `__main__.py:~668-689`).
- **Rekordbox parser** shipped in v2.0 Phase 25 — `src/vibemix/library/rekordbox_xml.py` (assumed; verify in plan-phase).
- **sqlite-vec dep** already in v2.1 STATE.md lockfile.
- **ws_bus port 8765** is the live IPC bus (mascot, levels). Port 8766 reserved for debrief (Phase 29).
- **Tauri Settings panel** exists from v2.0 Phase 11 (wizard) — Library tab is additive.
- **Frontend conventions:** project-local `frontend-enforcement` skill enforces vibemix design standards (CDJ Whisper visual direction).
- **Gemini SDK** = `google-genai==2.0.1` (CLAUDE.md tech stack).

Codebase maps under `.planning/codebase/` feed plan-phase research.

</code_context>

<specifics>
## Specific Ideas

- **Anti-feature watch (LIBRARY-14):** Never autosurface "next track suggestion". Only on user ask. This is explicit user preference + project principle.
- **180s cap is non-negotiable** — Gemini Embedding 2 hard limit (memory `project_gemini_embedding_2`). 3-excerpt avg is the documented mitigation.
- **Cost ceiling is hard:** €50/month is the cap (STATE.md). Budget exceeded = degrade gracefully (sampled grounding rate reduces) before failing.
- **Mac/Win parity test is required gate** — `test_topk_parity_mac_vs_win.py` runs on both CI matrix legs with same fixture → identical top-K results.
- **Tauri-side drag-drop:** use `webview2` (Windows) + `WKWebView` (macOS) native drag-target hooks via Tauri's `tauri-plugin-drag-drop`.

</specifics>

<deferred>
## Deferred Ideas

- **CLAP / LAION-CLAP / MERT / OpenL3:** rejected (memory `feedback_no_clap_use_gemini_embedding`).
- **Audio fingerprinting (acoustid-style):** out of scope. v2.2 stretch.
- **Bravoh-side embedding service:** v2.2 — for now, direct Gemini API.
- **Stems separation:** v2.2 backlog (memory `project_v2_open_candidates`).
- **Track segment retrieval (within-track search):** v2.2.
- **Multi-user library merging / sharing:** out of scope, no multi-user model.
- **Spotify / Apple Music API:** never — privacy + scope creep.

</deferred>
