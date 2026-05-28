# Phase 93: Exemplar Engine + `[exemplar:]` Evidence Source — Context

**Gathered:** 2026-05-28
**Status:** Ready for planning
**Mode:** Smart discuss (auto-accepted per `gsd-autonomous fully`); decisions cross-checked against `.planning/research/SUMMARY.md` §7 (4-site mirror) + §8 (audio routing) + ROADMAP P93.

<domain>
## Phase Boundary

P93 ships the DSP-band exemplar engine + new `[exemplar:<track_id>]` evidence source. For each EQ band (low/mid/high) it picks the strongest-band track from the DJ's CLAP-embedded library by computing band-share scalars (`sub_share` / `low_share` / `mid_share` / `high_share`). Includes compressed-kick guard (Pearson r > 0.8 between mid-band and sub-band → exclude). Falls back to a packaged ~3–5 MB CC-BY exemplar bank when library is empty / ≤3 tracks pass floor.

Audio plays through a dedicated `ExemplarPlayer` on a SECOND `sd.OutputStream` to a user-picked headphone device — NOT reusing `audio.buffers.PlaybackQueue` (mic-gated at `audio/buffers.py:195`).

**NO UI in this phase.** Engine + CLI test only. Course 1 lessons (P94) and Course 2 lessons (P95) consume the engine in subsequent phases; Course 3 (P96) may add the conditional `[cue:<anchor_id>]` source.

**REQ-IDs delivered:** EXEMPLAR-01, EXEMPLAR-02, EXEMPLAR-03, EXEMPLAR-04, EXEMPLAR-05.

**Out of scope:**
- Lesson scripts that cite `[exemplar:X]` → P94/P95 (consume the citation source)
- UI surfaces for exemplar playback (visualization, scrubber, etc.) → never in v9.0
- `[cue:<anchor_id>]` evidence source → P96 conditional
- Headphone device picker UI in onboarding wizard → P97 (P93 lands the persistent setting + ipc envelope shape ONLY)

</domain>

<decisions>
## Implementation Decisions

### Engine architecture (LOCKED per SUMMARY §1 + ROADMAP)

- **Module:** `src/vibemix/learn/exemplar.py` (NEW) — `ExemplarFinder` class.
- **Compute approach:** DSP-band ranker (NOT CLAP semantic cosine). CLAP is semantic; would mislabel "uplifting trance" as high-band when actually mid+sub. The engine reads existing band-share primitives from `audio/features.py:27-90` (`sub_share` / `low_share` / `mid_share` / `high_share`).
- **Persistence:** new `band_shares` column migration on the sqlite-vec library DB. Computed at ingest time (extends the existing CLAP ingest path additively).
- **Pure-compute:** dim-agnostic; offline-unit-testable on synthetic fixtures.
- **Compressed-kick guard:** if `pearson_r(mid_band_energy, sub_band_energy) > 0.8`, exclude as kick-sideband false-positive. Pinned by `tests/learn/test_exemplar_kick_guard.py`.

### Honest-null fallback (LOCKED per ROADMAP)

- **Packaged exemplar bank:** `assets/learn/band_exemplars/{sub,low,mid,high}/*` (4 tracks, instrumental, no vocals, ≤60s each, CC-BY licensed; ~3-5 MB total).
- **Trigger:** if user library has 0 tracks OR ≤3 tracks pass the band-share floor for a given band.
- **Honest-null copy:** *"Your library doesn't have a great example of this — listen to this one we packaged"*. Tracked as a constant (NOT live-generated).
- **Path verified by:** `tests/learn/test_exemplar_packaged_fallback.py`.
- **CC-BY attribution:** required in repo `NOTICE.md` or equivalent; per-track manifest at `assets/learn/band_exemplars/MANIFEST.json` with title/artist/license/source-url.

### Audio routing (LOCKED per SUMMARY §8)

- **Module:** `src/vibemix/learn/audio_cue.py::ExemplarPlayer` (NEW).
- **Stream:** SECOND `sd.OutputStream` on user-picked headphone device — NOT reusing `audio.buffers.PlaybackQueue` (mic-gated; would mute the user).
- **Format:** stereo float32 @ track sample rate. Decode via PyAV/FFmpeg.
- **Gain:** default-safe -12 dB. -18 dB if master deck audio > -6 dBFS (defer until quiet).
- **Course 3 active-session guard:** NEVER play tutor exemplars while user is mid-set (P96 enforcement; P93 lands the gate scaffolding).
- **Headphone device picker:** persisted as `learn.headphone_device_index` on EXISTING `ipc.settings.set` envelope. Wizard UI lands in P97; P93 ships the persistent setting + IPC payload shape ONLY.

### `[exemplar:<track_id>]` evidence source (LOCKED per SUMMARY §7 — 4-site mirror)

The new citation source mirrors v6 `[recall:]` EXACTLY across 4 schema-mirror sites — atomic single-commit add:

1. **`src/vibemix/state/evidence_registry.py:111`** — add `"exemplar"` to `EVIDENCE_SOURCES` frozenset.
2. **`src/vibemix/state/evidence_registry.py:137`** — add `|exemplar` to `_SOURCE_ALT` regex.
3. **`src/vibemix/prompts/matrix.py`** (`CITATION_GRAMMAR_BLOCK`) — add `[exemplar:<track_id>]` form.
4. **`src/vibemix/agent/dj_cohost.py`** (`_build_citation_strip`) — add `"exemplar"` to strip set.

Pinned by:
- `tests/learn/test_exemplar_citation_schema_mirror.py` — 4-site lock test (greps each site for the exemplar reference).
- `tests/learn/test_exemplar_grounding_e2e.py` — Invariant #2 binding: fabricated `[exemplar:bogus]` strips the whole turn.

### CLI test surface

- New CLI subcommand: `vibemix learn exemplar <band>` — prints the chosen track + reasoning (honest-null fallback included).
- Wired through existing CLI dispatch (e.g. `__main__.py` arg parsing).
- Used for Kaan dev-loop validation before P94 lesson scripts consume the engine.

### Claude's Discretion

- Exact sqlite-vec migration mechanics (alembic-style? raw SQL?). Match existing `library-clap.db` migration pattern.
- Per-band track ranking tie-break (e.g. when two tracks tie on `low_share` — by BPM-stability? by play count?). Use simple-but-defensible: track_id alphabetical for determinism.
- Exact CC-BY exemplar bank track selection (4 tracks per band × 4 bands = 16 tracks max; can ship fewer initially if licensing takes time).

</decisions>

<code_context>
## Existing Code Insights

### Reusable assets
- `src/vibemix/audio/features.py:27-90` — band-share primitives (sub/low/mid/high_share)
- `src/vibemix/state/evidence_registry.py:111+137` — the 2 evidence-source sites to extend (atomic with 3+4)
- `src/vibemix/prompts/matrix.py::CITATION_GRAMMAR_BLOCK` — site 3 of 4
- `src/vibemix/agent/dj_cohost.py::_build_citation_strip` — site 4 of 4
- `src/vibemix/library/clap_engine.py` (or wherever the CLAP ingest lives) — extend additively with band-share column
- `src/vibemix/platform/_audio_macos.py::open_voice_output(device_index, ...)` — exposes per-call device index (verified at lines 298-380); ExemplarPlayer uses this
- `src/vibemix/runtime/ws_bus.py` — IpcRouterBus exists; settings handlers already there (extend for `learn.headphone_device_index` setting persistence)
- `tests/learn/` — existing test layout precedent from P91/P92
- v6 `[recall:]` precedent — git log + state/evidence_registry.py history will show the exact 4-site commit pattern to mirror

### Concurrent-session discipline
- Shared file edits (NEW for P93): `state/evidence_registry.py`, `prompts/matrix.py`, `agent/dj_cohost.py`, sqlite-vec migration, `__main__.py` (ExemplarPlayer instantiation + CLI subcommand).
- New-file islands: `src/vibemix/learn/exemplar.py`, `src/vibemix/learn/audio_cue.py`, `assets/learn/band_exemplars/` (whole tree), `tests/learn/test_exemplar_*.py` (4+ test files).

</code_context>

<specifics>
## Specific Ideas

- The 4-site schema mirror MUST land atomically (single commit). v6 `[recall:]` precedent shows the pattern.
- The compressed-kick guard is the key anti-slop gate — without it, hardtechno tracks with sub-heavy kicks get labeled "high-band exemplar" (false-positive).
- CC-BY exemplar bank tracks: source from existing CC-BY archives (Free Music Archive, ccMixter, Wikimedia). Each ~30-60s loop with one band dominant.

</specifics>

<deferred>
## Deferred Ideas

- Lesson scripts citing `[exemplar:X]` → P94/P95
- Headphone device picker WIZARD UI → P97
- Course 3 active-session guard enforcement (mid-set exemplar block) → P96
- `[cue:<anchor_id>]` evidence source (conditional fifth citation source) → P96
- Exemplar visualization UI (scrubber, waveform, EQ overlay) → never in v9.0

</deferred>
