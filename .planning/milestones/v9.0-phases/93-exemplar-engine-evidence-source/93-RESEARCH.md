# Phase 93: Exemplar Engine + `[exemplar:]` Evidence Source — Research

**Researched:** 2026-05-28
**Domain:** DSP band-share ranker + sqlite-vec metadata-column migration + dedicated `sd.OutputStream` audio routing + atomic 4-site citation-source schema mirror (v6 `[recall:]` precedent)
**Confidence:** HIGH on engineering spine (every file:line verified in-tree). HIGH on the 4-site mirror pattern (v6 commits `2016e36b → 977c0140 → 0bfc8bd0` are the exact blueprint — sites 1+2 atomic + site 3 + site 4). MEDIUM on compressed-kick guard threshold (Pearson r > 0.8 picked by CONTEXT lock; Kaan ear-pass tunes it on real hardtechno library = `§EXEMPLAR-KICK-GUARD-EAR`). LOW only on CC-BY exemplar bank sourcing (asset-acquisition is out-of-tree work — flagged for `§EXEMPLAR-BANK-SOURCING` ride-forward).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Engine architecture:**
- Module: `src/vibemix/learn/exemplar.py` (NEW) — `ExemplarFinder` class.
- Compute approach: **DSP-band ranker** (NOT CLAP semantic cosine). CLAP is semantic; would mislabel "uplifting trance" as high-band when actually mid+sub.
- The engine reads existing band-share primitives from `src/vibemix/audio/features.py:27-90` (`sub_share` / `low_share` / `mid_share` / `high_share`).
- Persistence: new `band_shares` column migration on the sqlite-vec library DB. Computed at ingest time (extends the existing CLAP ingest path additively).
- Pure-compute: dim-agnostic; offline-unit-testable on synthetic fixtures.
- **Compressed-kick guard:** if `pearson_r(mid_band_energy, sub_band_energy) > 0.8`, exclude as kick-sideband false-positive. Pinned by `tests/learn/test_exemplar_kick_guard.py`.

**Honest-null fallback:**
- **Packaged exemplar bank:** `assets/learn/band_exemplars/{sub,low,mid,high}/*` (4 tracks per band, instrumental, no vocals, ≤60s each, CC-BY licensed; ~3-5 MB total).
- **Trigger:** if user library has 0 tracks OR ≤3 tracks pass the band-share floor for a given band.
- **Honest-null copy (constant, NOT live-generated):** *"Your library doesn't have a great example of this — listen to this one we packaged"*.
- **Path verified by:** `tests/learn/test_exemplar_packaged_fallback.py`.
- **CC-BY attribution:** required in repo `NOTICE.md` or equivalent; per-track manifest at `assets/learn/band_exemplars/MANIFEST.json` with title/artist/license/source-url.

**Audio routing:**
- Module: `src/vibemix/learn/audio_cue.py::ExemplarPlayer` (NEW).
- Stream: **SECOND** `sd.OutputStream` on user-picked headphone device — NOT reusing `audio.buffers.PlaybackQueue` (mic-gated; would mute the user).
- Format: stereo float32 @ track sample rate. Decode via PyAV/FFmpeg (existing `library/audio_decode.py::load_audio_mono` extended to stereo).
- Gain: default-safe -12 dB. -18 dB if master deck audio > -6 dBFS (defer until quiet).
- Course 3 active-session guard: NEVER play tutor exemplars while user is mid-set (P96 enforcement; **P93 lands the gate scaffolding** as a `can_play()` check that returns False when `state.session_active and state.audible_deck != none` — P96 wires it).
- **Headphone device picker:** persisted as `learn.headphone_device_index` on EXISTING `ipc.settings.set` envelope. Wizard UI lands in P97; **P93 ships the persistent setting + IPC payload shape ONLY**.

**`[exemplar:<track_id>]` evidence source (4-site mirror — atomic single-commit add):**

The new citation source mirrors v6 `[recall:]` EXACTLY across 4 schema-mirror sites:

1. **`src/vibemix/state/evidence_registry.py:111`** — add `"exemplar"` to `EVIDENCE_SOURCES` frozenset.
2. **`src/vibemix/state/evidence_registry.py:137`** — add `|exemplar` to `_SOURCE_ALT` regex.
3. **`src/vibemix/prompts/matrix.py`** (`CITATION_GRAMMAR_BLOCK`) — add `[exemplar:<track_id>]` form.
4. **`src/vibemix/agent/dj_cohost.py`** (`_build_citation_strip`) — add `"exemplar"` to strip set + branch.

Pinned by:
- `tests/learn/test_exemplar_citation_schema_mirror.py` — 4-site lock test (greps each site for the exemplar reference).
- `tests/learn/test_exemplar_grounding_e2e.py` — Invariant #2 binding: fabricated `[exemplar:bogus]` strips the whole turn.

**CLI test surface:**
- New CLI subcommand: `vibemix learn exemplar <band>` — prints the chosen track + reasoning (honest-null fallback included).
- Wired through existing CLI dispatch (`__main__.py:3316` `learn` block — extend the if/elif tree alongside `reset`).
- Used for Kaan dev-loop validation before P94 lesson scripts consume the engine.

### Claude's Discretion

- Exact sqlite-vec migration mechanics (alembic-style? raw SQL?). **Recommendation:** match the existing `recreate_table()` pattern at `index_sqlite_vec.py:145-160` — raw SQL `ALTER TABLE ... ADD COLUMN` is NOT supported by vec0 virtual tables; we use a **side-car table** `band_shares (track_id TEXT PRIMARY KEY, sub_share REAL, low_share REAL, mid_share REAL, high_share REAL, kick_corr REAL, updated_at REAL)` in the SAME `library-clap.db` so it inherits the vec0 store's backup/rotate lifecycle (Pitfall §M2 — single DB, two tables).
- Per-band track ranking tie-break (e.g. when two tracks tie on `low_share` — by BPM-stability? by play count?). **Use simple-but-defensible:** track_id alphabetical for determinism.
- Exact CC-BY exemplar bank track selection (4 tracks per band × 4 bands = 16 tracks max; can ship fewer initially if licensing takes time). **Recommendation:** start with 1 track/band (4 total) — meets EXEMPLAR-03's "at least one" floor, attribution easier, KAAN-ACTION can grow the bank later.

### Deferred Ideas (OUT OF SCOPE)

- Lesson scripts citing `[exemplar:X]` → P94/P95
- Headphone device picker WIZARD UI → P97 (P93 ships setting key + IPC payload shape only)
- Course 3 active-session guard enforcement (mid-set exemplar block) → P96
- `[cue:<anchor_id>]` evidence source (conditional fifth citation source) → P96
- Exemplar visualization UI (scrubber, waveform, EQ overlay) → never in v9.0

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **EXEMPLAR-01** | For each EQ band lesson (low/mid/high), the system picks the strongest-band track from the DJ's CLAP-embedded library by computing band-share scalars at ingest time and persisting them in a new sqlite-vec band-share column. Engine: `src/vibemix/learn/exemplar.py::ExemplarFinder` (NEW, pure-compute, dim-agnostic, offline-unit-testable). | §DSP Band-Share Engine (algorithm + verbatim numpy port from `audio/features.py:75-89`), §Persistence (side-car table migration pattern), §Code Examples §1 + §3. |
| **EXEMPLAR-02** | DSP-band ranker (NOT CLAP semantic cosine). Compressed-kick guard: Pearson r > 0.8 between mid-band and sub-band → exclude. Pinned by `tests/learn/test_exemplar_kick_guard.py`. | §Compressed-Kick Guard (full implementation + synthetic test fixture), §Code Example §2. |
| **EXEMPLAR-03** | Honest-null fallback to packaged CC-BY exemplar bank when library is empty / ≤3 tracks pass floor for a given band. ~3-5 MB at `assets/learn/band_exemplars/{sub,low,mid,high}/*`. Honest-null reasoning copy. Path verified by `tests/learn/test_exemplar_packaged_fallback.py`. | §Honest-Null Fallback Packaging (hatchling wheel-include pattern), §Asset Manifest schema, §Code Example §4. |
| **EXEMPLAR-04** | Exemplar audio plays through dedicated `src/vibemix/learn/audio_cue.py::ExemplarPlayer` (NEW) on a SECOND `sd.OutputStream` to a user-picked headphone device — NOT reusing `audio.buffers.PlaybackQueue` (mic-gated at `audio/buffers.py:195`). Stereo float32 @ track sample rate via PyAV/FFmpeg decode. Default -12 dB (-18 dB if master > -6 dBFS). Device picker persists as `learn.headphone_device_index` on existing `ipc.settings.set`. | §ExemplarPlayer Architecture (verbatim `_audio_macos.py:298-326` `open_passthrough_output` precedent + headphone device-index seam), §Settings Persistence (`ipc.settings.set` envelope shape extension), §Code Example §5 + §6 + §7. |
| **EXEMPLAR-05** | NEW `[exemplar:<track_id>]` evidence source — atomically added to 4 schema-mirror sites in a single commit (mirrors v6 `[recall:]` precedent EXACTLY). Pinned by `tests/learn/test_exemplar_citation_schema_mirror.py` (4-site lock test) + `tests/learn/test_exemplar_grounding_e2e.py` (fabricated `[exemplar:bogus]` strips whole turn — Invariant #2 binding). | §4-Site Schema Mirror (verbatim v6 `[recall:]` commit diffs from git history), §Code Example §8 + §9 + §10 + §11. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

| Directive | Source | How P93 Honors |
|-----------|--------|----------------|
| **One-socket invariant (#4)** | CLAUDE.md §Architecture | P93 adds NO new ws envelopes (P92 shipped the schema for `exemplar_play` / `exemplar_stop`; P93 emits them from the existing `IpcRouterBus`). CI gate `tests/learn/test_no_new_ws_port.py` already green. |
| **Single-writer invariant (#1)** | CLAUDE.md §Architecture | `ExemplarFinder` is READ-ONLY against `LibraryStore` + the new `band_shares` table. Writes the band-share row in the SAME loop as the CLAP embedding (single-writer per track row). Never mutates `MusicState` or `LearnState`. |
| **Citation grounding (#2)** | CLAUDE.md §Architecture | **THIS PHASE IS THE INVARIANT #2 BINDING for v9.0.** The 4-site mirror lands `[exemplar:]` so a fabricated cite strips the whole turn via the existing CitationLinter. Pinned by `tests/learn/test_exemplar_grounding_e2e.py`. |
| **Trust the audio (#3)** | CLAUDE.md §Architecture | P93's exemplar engine is OFFLINE band-share computation on existing audio files. Real audio drives the band-share scalar; no LLM/heuristic invents a band. The agent's `[exemplar:<track_id>]` cite must resolve to a `EvidenceRegistry.write("exemplar", track_id, ...)` write that happened BEFORE the LLM emitted the cite. |
| **No model literals — `model_router` only** | CLAUDE.md §Configuration | N/A in P93 (no AI calls; the engine + player are pure-compute / pure-I/O). |
| **Frontend settings controls must repaint OPTIMISTICALLY** | CLAUDE.md §Conventions | The headphone-device picker UI lands in P97; P93 only ships the persistent setting + IPC payload shape, so optimistic-repaint discipline lives downstream. |
| **`codegen:ipc` mandatory after schema edit** | CLAUDE.md §Commands | P93 extends `ipc.settings.set` payload (adds optional `learn.headphone_device_index` field). After the `messages.schema.json` edit, run `cd tauri/ui && npm run codegen:ipc`. |
| **`cargo tauri dev` = STALE frozen sidecar** | CLAUDE.md §Commands | Verify backend wiring by running `python -m vibemix` on current source. The CLI `vibemix learn exemplar <band>` provides a direct Python-side verification surface (no Tauri shell required). |
| **Concurrent sessions on `live-tuning-or-brain`** | CLAUDE.md §Project Skills | Shared file edits (`state/evidence_registry.py`, `prompts/matrix.py`, `agent/dj_cohost.py`, `library/folder_ingest.py`, `__main__.py`, `messages.schema.json`) must be solo+sequential. New-file islands at `src/vibemix/learn/exemplar.py`, `src/vibemix/learn/audio_cue.py`, `assets/learn/band_exemplars/`, `tests/learn/test_exemplar_*.py`. Commit by NAMED paths only. |
| **Apache-clean: CC-BY attribution required** | CLAUDE.md §Constraints | `NOTICE.md` MUST list each CC-BY track shipped under `assets/learn/band_exemplars/`. Per-track JSON manifest carries title/artist/license/source-url. CI gate `tests/learn/test_exemplar_bank_attribution.py` (NEW) greps `NOTICE.md` for each MANIFEST entry. |

## Summary

P93 lands the **DSP-band exemplar engine + the `[exemplar:<track_id>]` evidence source** — the marquee/moat enabler for Course 1 lesson 1.14 ("EQ-as-Tutor Demo") and the Course 2 transition demos. The phase is **engine + CLI only — NO UI**. It splits cleanly into four near-orthogonal work-streams that the planner can parallelize:

1. **Band-share computation extension** of the existing CLAP ingest path (`library/folder_ingest.py:336-374`) — at the same loop where each track's CLAP vector is computed, also write a 5-tuple `(sub, low, mid, high, kick_corr)` to a NEW `band_shares` side-car table in the SAME `library-clap.db`. Pure-compute additive; existing CLAP ingest stays byte-identical when the new flag is off.
2. **ExemplarFinder ranker** (`src/vibemix/learn/exemplar.py`) — pure-compute over the side-car table. Reads `band_shares`, applies the compressed-kick guard (`kick_corr > 0.8` exclude), ranks by target band's share, ties broken by track_id alphabetical, returns top-K. Falls back to packaged CC-BY bank when ≤3 tracks pass floor.
3. **ExemplarPlayer audio routing** (`src/vibemix/learn/audio_cue.py`) — verbatim mirror of `_audio_macos.py:298-326` `open_passthrough_output(device_index, sample_rate, channels=2, ...)` precedent. Owns its own `sd.OutputStream` (NOT `PlaybackQueue`); stereo float32 decode via PyAV/FFmpeg (extends `library/audio_decode.py::load_audio_mono` to return stereo); -12 dB safe default; gate scaffolding for active-session guard.
4. **4-site `[exemplar:]` mirror** — atomic single commit replicating v6 `[recall:]` commits `2016e36b → 977c0140 → 0bfc8bd0` byte-for-byte. Adds 1 frozenset element + 1 regex alternation token + 1 grammar block line + 1 strip-set element + 1 elif branch. CitationLinter + Phase 20 strip gate work without further change — the registry-existence-only contract is what makes a fabricated `[exemplar:bogus]` uncitable-by-construction.

The acid test for the phase: every new file lands inside `src/vibemix/learn/` or `assets/learn/band_exemplars/` or `tests/learn/`; shared-file edits to evidence_registry / matrix / dj_cohost / folder_ingest / __main__ are surgical (1-5 lines each, mirror the recall: commits); the 4-site mirror lands in ONE atomic commit; the CLI `vibemix learn exemplar low` resolves to a real track from Kaan's library OR falls back to the packaged bank with the honest-null copy printed.

**Primary recommendation:** Adopt the **v6 `[recall:]` 4-site commit sequence verbatim** (Pattern §1 below) — sites 1+2 first (atomic, MUST land together to close the silent-poisoning hole), then site 3, then site 4. The compressed-kick guard is the anti-slop gate: WITHOUT it, hardtechno tracks with sub-heavy distorted kicks get labeled "high-band exemplar" because their kick fundamentals splash energy across the mid+high spectrum. The packaged CC-BY bank starts at **1 track/band (4 total)** to minimize licensing surface; KAAN-ACTION `§EXEMPLAR-BANK-EAR-PASS` grows it on real ear-pass. The `ExemplarPlayer` uses `audio_backend.open_passthrough_output(headphone_idx, ...)` — same shape as the existing `pass_stream` at `__main__.py:929` — NOT `open_voice_output` (which is mono int16 for Gemini TTS and the wrong format for stereo CC-BY music).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Band-share scalar computation | **Python sidecar** (`audio/features.py:71-90` — EXISTING) | — | Already exists; verbatim reuse. The engine only *consumes* `snapshot_features()` output. |
| Compressed-kick guard (Pearson r) | **Python sidecar** (`learn/exemplar.py::_kick_correlation` — NEW) | — | Pure-compute; offline-unit-testable on synthetic 4-channel band fixtures. |
| Per-track band-share persistence | **Python sidecar** (`library/folder_ingest.py:355-365` — EDIT, +6 lines) | — | Extends the existing CLAP ingest loop additively; SAME `library-clap.db` (no second DB). |
| Side-car `band_shares` table schema + I/O | **Python sidecar** (`learn/band_share_store.py` — NEW) | — | New module pattern mirrors `library/embed_cache.py` (raw sqlite3 helper, opens shared DB by path). |
| ExemplarFinder ranking | **Python sidecar** (`learn/exemplar.py::ExemplarFinder` — NEW) | — | Pure-compute over the side-car table; reads CLAP store for track-id resolution. |
| Honest-null fallback selection | **Python sidecar** (`learn/exemplar.py::ExemplarFinder._fallback` — NEW) | — | Deterministic: same input always returns same packaged track. |
| Packaged CC-BY bank assets | **Python sidecar** (`assets/learn/band_exemplars/{sub,low,mid,high}/*.mp3` — NEW) | — | Bundled via hatchling default include (verified in pyproject.toml §Hatchling-includes comment at line 211). |
| Asset attribution manifest | **Python sidecar** (`assets/learn/band_exemplars/MANIFEST.json` — NEW) | — | Source of truth for `NOTICE.md` attribution lines. CI gate verifies sync. |
| Audio decode (file → stereo float32) | **Python sidecar** (`library/audio_decode.py::load_audio_stereo` — NEW; mirrors existing `load_audio_mono`) | — | PyAV/FFmpeg; existing `av.open` pattern reused. |
| ExemplarPlayer stream lifecycle | **Python sidecar** (`learn/audio_cue.py::ExemplarPlayer` — NEW) | — | Own `sd.OutputStream` on headphone device_index; never touches `PlaybackQueue`. |
| Master-deck gain gate | **Python sidecar** (`learn/audio_cue.py::_choose_gain_db` — NEW) | — | Reads `MusicState.audio_rms` (read-only); returns -12 dB or -18 dB. |
| Active-session guard | **Python sidecar** (`learn/audio_cue.py::ExemplarPlayer.can_play` — NEW) | — | P93 lands the gate; P96 wires the actual `state.session_active` check. |
| Headphone device-index persistence | **Python sidecar** (`runtime/config_store.py` — EDIT, +1 settings key) + **Browser webview** (settings drawer envelope shape) | — | Same pattern as existing `mascot.enabled` / `recording.dir` settings keys. P97 lands the UI. |
| `[exemplar:<track_id>]` evidence source | **Python sidecar** (`state/evidence_registry.py:111+137` — EDIT, +1 frozenset element + 1 regex token) + (`prompts/matrix.py` — EDIT, +1 grammar line) + (`agent/dj_cohost.py:255+277` — EDIT, +1 allow-list element + 1 elif branch) | — | 4-site atomic mirror. Source-of-truth = `EVIDENCE_SOURCES`. |
| Exemplar evidence registration | **Python sidecar** (`learn/exemplar.py::ExemplarFinder.find` → `EvidenceRegistry.write("exemplar", track_id, t_session)`) | — | Mirrors the `recall` registration pattern at `recall_messages` (Phase 65 wiring). Engine calls registry write BEFORE the LLM emits the cite. |
| CLI `vibemix learn exemplar <band>` | **Python sidecar** (`__main__.py:3316-3330` — EDIT, +1 elif branch) | — | Mirrors `vibemix learn reset` precedent at the same site (P92-04 Task 2). |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard | Provenance |
|---------|---------|---------|--------------|------------|
| `numpy` | already pinned in `pyproject.toml` | Band-share float math, Pearson correlation | Existing; verbatim reuse from `audio/features.py:21`. | `[VERIFIED: in-tree]` |
| `sounddevice` | `^0.5.5` (already pinned) | `sd.OutputStream` on headphone device | Existing `open_passthrough_output` pattern at `_audio_macos.py:298-326`. | `[VERIFIED: in-tree]` |
| `av` (PyAV) | already pinned via `[ai-local]` extra | Stereo audio decode | Existing `library/audio_decode.py::load_audio_mono` uses `av.open` at line 64. | `[VERIFIED: in-tree]` |
| `sqlite3` (stdlib) | Python 3.12 stdlib | Side-car `band_shares` table | Existing pattern at `library/embed_cache.py` (raw sqlite3, no extension). | `[VERIFIED: stdlib]` |
| `sqlite-vec` | already pinned | (Indirect — we extend the SAME `library-clap.db`, do NOT touch the vec0 table) | The `band_shares` side-car table sits next to `vec_library` in the SAME DB file so backup/rotate stays a single-file operation. | `[VERIFIED: in-tree, via index_sqlite_vec.py]` |

**ZERO new dependencies in P93.** Every library above is already pinned in `pyproject.toml` and has been shipping since v0.1.0 / Phase 28.

### Supporting

| Library | Version | Purpose | When to Use | Provenance |
|---------|---------|---------|-------------|------------|
| `pytest` | already pinned | Test framework for the 4 new test files | Existing pattern; matches `tests/learn/test_*.py` shape. | `[VERIFIED: in-tree]` |
| `pytest.mark.slow` / `pytest.mark.macos_audio` | existing opt-in markers | Real-audio CC-BY-bank playback tests | Skip-by-default on CI; opt-in via `pytest -m macos_audio` for Kaan's local verification. | `[VERIFIED: pyproject.toml [tool.pytest.ini_options]]` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Side-car `band_shares` table in `library-clap.db` | Separate `band_shares.db` file | Two-file lifecycle (backup, rotate, dim-mismatch wipe at `index_sqlite_vec.py:145`). The CLAP DB already gets nuked on dim change; side-car table inside it inherits that lifecycle cleanly. **REJECTED — single-DB simpler.** |
| Side-car `band_shares` table | `ALTER TABLE vec_library ADD COLUMN sub_share REAL` | vec0 virtual tables do NOT support `ALTER TABLE ADD COLUMN`. Verified in `index_sqlite_vec.py:122-127` doc — vec0 schema is fixed at `CREATE VIRTUAL TABLE`. **REJECTED — sqlite-vec API limitation.** |
| Pearson correlation for kick-guard | Spectral flux / autocorr-based "kick fundamental dominance" | Pearson over band energies is well-understood, deterministic, fast (no extra FFT pass — the band energies are already computed). CONTEXT lock'd > 0.8 threshold; KAAN ear-pass tunes. **LOCKED — CONTEXT.md decision.** |
| Dedicated `sd.OutputStream` on headphone device | Reuse `playback: PlaybackQueue` (the AI voice queue at `__main__.py:925`) | `PlaybackQueue` is mic-gated at `audio/buffers.py:195` — the mic mutes when the AI voice queue has content (feedback suppression). Routing a CC-BY exemplar track through it would silence Kaan's mic and the AI voice for the duration of the exemplar — wrong contract. **REJECTED — LOCKED in CONTEXT.md §8 and SUMMARY §8.** |
| Live-generated honest-null copy | Constant string | Constant means: byte-equality test, no LLM call needed, ship-deterministic. **LOCKED — CONTEXT.md.** |
| Ship 16 CC-BY tracks (4/band) day-one | Ship 4 (1/band) day-one | License-acquisition surface scales with track count. CONTEXT.md §discretion explicitly allows fewer initially. **RECOMMENDED — 1/band day-one, KAAN-ACTION grows it.** |
| New `[exemplar:]` source via a NEW 5th schema-mirror site | 4-site mirror (frozenset + regex + grammar + strip) | The 4-site pattern is the established v6 contract — adding a 5th site would diverge from the lock-step invariant comment at `evidence_registry.py:108-110`. **REJECTED — match precedent.** |
| Split the 4-site mirror across 4 commits (one per site) | Single atomic commit | The 1+2 pair is the **silent-poisoning hole** comment block at `evidence_registry.py:120-131` — they MUST land together or a fabricated `[exemplar:<id>]` rides through unmatched. v6 actually split into 3 commits (`2016e36b` for 1+2 atomic, `977c0140` for 3, `0bfc8bd0` for 4) — Phase 93 plan should follow the same split: ONE commit for sites 1+2 (atomic), then sites 3 and 4 can be separate but in the SAME plan to keep them under one phase. **RECOMMENDED — sites 1+2 atomic; sites 3 + 4 separable but same-phase.** |

**Installation:**
```bash
# Nothing new to install. P93 uses 100% existing dependencies.
# Verify by running:
PYTHONPATH=src python3 -m pytest -q tests/state/ tests/learn/   # existing tests pass
PYTHONPATH=src python3 -c "import av; import sounddevice; import numpy; print('ok')"
```

**Version verification:**
```bash
grep -E "(numpy|sounddevice|av|sqlite-vec)" pyproject.toml
```

All packages verified `[VERIFIED: in-tree, already shipping]`.

## Package Legitimacy Audit

> **N/A — P93 installs ZERO new packages.** Every library used is already pinned in `pyproject.toml` and has been in production since prior phases. The slopcheck gate doesn't apply because there is no new install to verify.

| Package | Registry | Disposition |
|---------|----------|-------------|
| `numpy` | PyPI | Pre-existing — no change |
| `sounddevice` | PyPI | Pre-existing — no change |
| `av` (PyAV) | PyPI | Pre-existing — no change |
| `sqlite-vec` | PyPI | Pre-existing — no change |

If the planner later proposes a new dep, the Package Legitimacy Gate MUST run before that install lands. For P93 as scoped, no slopcheck invocation is required.

**CC-BY exemplar bank — asset (not package) legitimacy gate:**
Each MP3/OGG file shipped under `assets/learn/band_exemplars/` must carry a corresponding entry in `MANIFEST.json` with `license: "CC-BY-4.0"` (or compatible CC-BY variant) + `source_url`. The CI gate `tests/learn/test_exemplar_bank_attribution.py` (NEW) walks the bank directory, asserts every file has a manifest entry, asserts every manifest entry has its file present, and greps `NOTICE.md` for each track's attribution line.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Python sidecar (src/vibemix/)                                                │
│                                                                              │
│  Existing live runtime (UNCHANGED) ───── main() in __main__.py               │
│                                                                              │
│  ──── ingest-time additive extension (folder_ingest.py:355-365) ─────        │
│                                                                              │
│        For each track in folder ingest:                                      │
│         ┌─────────────────────────────────────────┐                          │
│         │ 1. Load audio (existing) → np.ndarray   │                          │
│         │ 2. ClapEmbedder.embed_track → 512-d vec │                          │
│         │ 3. store.add_batch([(track_id, vec)])   │ ← EXISTING               │
│         │                                          │                          │
│         │ 4. snapshot_features(audio) → band-shares│ ← NEW                   │
│         │ 5. _kick_correlation(audio) → r ∈ [-1,1] │ ← NEW                   │
│         │ 6. band_share_store.upsert(              │ ← NEW                   │
│         │      track_id, sub, low, mid, high, r)  │                          │
│         └─────────────────────────────────────────┘                          │
│                                                                              │
│  ──── runtime engine ──────────────────────────────────────                  │
│                                                                              │
│  lesson runtime (LessonRuntime — P92)                                         │
│         │                                                                    │
│         │   for EQ-band lesson L1.14:                                         │
│         ▼                                                                    │
│  ExemplarFinder.find(band="low", k=3)                                        │
│         │                                                                    │
│         │   1. SELECT ... FROM band_shares WHERE                              │
│         │      kick_corr < 0.8  (compressed-kick guard)                       │
│         │      ORDER BY low_share DESC, track_id ASC LIMIT 10                 │
│         │   2. if len(rows) < 3 → fallback to CC-BY bank                      │
│         │   3. for top-k, register w/ EvidenceRegistry:                       │
│         │      evidence.write("exemplar", track_id, t_session)                │
│         │   4. return [(track_id, file_path, band_score, reason), ...]        │
│         ▼                                                                    │
│  ExemplarPlayer.play(file_path)                                               │
│         │                                                                    │
│         │   1. decode via av.open → stereo float32 @ track sr                 │
│         │   2. gain = _choose_gain_db(state.audio_rms) (-12 or -18 dB)        │
│         │   3. sd.OutputStream(device=headphone_idx, channels=2, ...)        │
│         │      ← NOT PlaybackQueue (would mute mic via audio/buffers.py:195)  │
│         │   4. emit ipc.learn.exemplar_play {track_id, started_at}            │
│         │   5. on EOF: emit ipc.learn.exemplar_stop                           │
│         ▼                                                                    │
│  AI tutor (P94/P95 — NOT P93) emits "this track's lows hit hard               │
│  [exemplar:track_id_X]" → CitationLinter checks                               │
│  EvidenceRegistry.has("exemplar", track_id_X) → grounded                      │
│         │                                                                    │
│         │   fabricated [exemplar:bogus] → registry.has() = False             │
│         ▼                                                                    │
│  → linter STRIPS whole turn (anti-slop gate)                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pattern 1 — `[exemplar:]` 4-Site Schema Mirror (THE critical pattern)

**What:** Atomic mirror of the v6 `[recall:]` precedent. Adds one new citation source to the EBNF grammar across 4 sites in lock-step.

**When to use:** This pattern is invoked ONCE per new citation source. P93 = `[exemplar:]`. P96 (conditional) = `[cue:]` if Course 3 needs proactive count-ins.

**Why atomic for sites 1+2:** The `EVIDENCE_SOURCES` frozenset (site 1) and the `_SOURCE_ALT` regex alternation (site 2) MUST land in the SAME commit. The frozenset gates which sources the registry accepts via `write()`; the regex gates which sources `parse_citations()` matches. If site 1 lands without site 2, the registry accepts `exemplar` writes but `parse_citations` never extracts the `[exemplar:<id>]` atom — so the CitationLinter never sees it, never validates it against the registry, never strips it. A fabricated `[exemplar:bogus]` would ride through un-validated. The lock-step comment at `evidence_registry.py:120-131` calls this out as **"the silent-poisoning-hole pair."**

**The verbatim v6 precedent (commits in chronological order):**

```
2016e36b  feat(65-02): add recall evidence source to EVIDENCE_SOURCES + _SOURCE_ALT (sites 1+2)
           ↑ ATOMIC — sites 1 and 2 in ONE commit
977c0140  feat(65-02): add [recall:<record_id>] form to citation grammar block (site 3)
0bfc8bd0  feat(66-02): land recall chip allow-list + coach-tier cooldown wiring in dj_cohost.py (site 4)
           ↑ Note: v6 landed site 4 in Phase 66, not 65 — recall cooldown was its own concern.
             For exemplar, sites 4 lands in P93 alongside sites 1+2+3 (one phase, three commits).
```

### Pattern 2 — DSP Band-Share Engine (verbatim numpy port from existing `snapshot_features`)

**What:** The band-share scalars (`sub_share`, `low_share`, `mid_share`, `high_share`) the engine ranks tracks by ALREADY EXIST in `src/vibemix/audio/features.py:75-89`. The engine extracts them once per track at ingest time, persists in side-car table.

**Existing primitive (verbatim, `audio/features.py:71-89`):**

```python
def band_energy(lo: float, hi: float) -> float:
    mask = (freqs >= lo) & (freqs < hi)
    return float(np.sqrt(np.mean(spec[mask] * spec[mask]))) if mask.any() else 0.0

sub = band_energy(20, 100)       # ← sub-bass band
low = band_energy(100, 300)      # ← low band (kick fundamentals + bass)
mid_low = band_energy(300, 1000)
mid_hi = band_energy(1000, 4000)
high = band_energy(4000, 8000)
total = sub + low + mid_low + mid_hi + high + 1e-9

return {
    ...
    "sub_share": round(sub / total, 2),
    "low_share": round(low / total, 2),
    "mid_share": round((mid_low + mid_hi) / total, 2),   # ← note: mid is the SUM of two FFT bands
    "high_share": round(high / total, 2),
}
```

**Key facts the planner must know:**
1. **Per-call shape:** `snapshot_features(buf, seconds=5.0)` returns ONE dict per call — a 5-second snapshot of the buffer. For library-track band-shares, we need to process the ENTIRE track, not the last 5 seconds.
2. **Per-track aggregate strategy:** Decode the full track audio (via `av.open` — existing pattern at `library/audio_decode.py:64`), then either (a) compute `snapshot_features`-equivalent FFT over the full track, OR (b) chunk into 30s windows and average band-shares per chunk. **Recommendation: (a) — single full-track FFT** because (1) tracks are 3-7 min so FFT cost is one-time, (2) it matches the "per-track scalar" persistence shape, (3) the existing `snapshot_features` is parameterized on `seconds` — passing `seconds=track_duration` gets the right behavior.
3. **Mid-band aggregation:** `mid_share = (mid_low + mid_hi) / total` — the EXISTING engine sums two FFT bands (300-1000 Hz + 1000-4000 Hz) into one mid label. P93's exemplar engine preserves this verbatim — DO NOT split mid into two scalars (would diverge from the v4 port and break the snapshot_features contract).
4. **Values are normalized:** Each band-share is `band_energy / total_energy` so they sum to ~1.0 (within float epsilon). Rounded to 2 decimals at the v4 port site. **For the band_shares table, store raw float (not rounded)** — the 2-decimal rounding is a display affordance, not a storage decision.

**The engine's new helper (NEW file `learn/exemplar.py`):**

```python
# src/vibemix/learn/exemplar.py
import numpy as np
from vibemix.audio.features import snapshot_features
from vibemix.audio.buffers import AudioBuffer
from vibemix.library.audio_decode import load_audio_mono

def compute_band_shares(audio_path: str) -> dict:
    """Return {sub,low,mid,high}_share + kick_corr for one track file.

    Single full-track FFT (verbatim math port of audio/features.py:71-89);
    side-loads the existing snapshot_features primitive by building an
    AudioBuffer just large enough to hold the whole track."""
    sr = 48000  # standard ingest sr
    samples = load_audio_mono(audio_path, target_sr=sr)
    duration_s = len(samples) / sr
    # Build a transient buffer sized to the full track. AudioBuffer is a ring,
    # so size it to the exact sample count and push all samples in.
    buf = AudioBuffer(seconds=duration_s, sample_rate=sr, dtype="int16")
    # snapshot_features expects int16 samples; cast float32 → int16 once.
    buf.push((samples * 32767).clip(-32768, 32767).astype(np.int16))
    feats = snapshot_features(buf, seconds=duration_s)
    if feats.get("silent"):
        return {"sub_share": 0.0, "low_share": 0.0,
                "mid_share": 0.0, "high_share": 0.0, "kick_corr": 0.0}
    return {
        "sub_share": feats["sub_share"],
        "low_share": feats["low_share"],
        "mid_share": feats["mid_share"],
        "high_share": feats["high_share"],
        "kick_corr": _kick_correlation(samples, sr),
    }
```

### Pattern 3 — Compressed-Kick Guard (Pearson r between mid-band and sub-band)

**What:** A hardtechno track with a sub-heavy distorted kick has energy in the sub band (kick fundamental) PLUS spillover energy in the mid band (kick harmonics + transient overtones). Both bands move together over time, so their per-window energies are correlated. If `pearson_r(mid_band_per_window, sub_band_per_window) > 0.8`, the mid-band energy is mostly KICK SPILLOVER not real mid content (vocals, leads, pads, snare), so the track is a **bad exemplar for mid-band lessons** — playing it would teach the user "this is mid" but they'd hear a sub-heavy kick.

**The guard implementation (verbatim — copy this into `learn/exemplar.py`):**

```python
def _kick_correlation(samples: np.ndarray, sr: int) -> float:
    """Compute Pearson r between per-window mid-band and sub-band energy.

    Returns r ∈ [-1, 1]. r > 0.8 means mid-band energy tracks sub-band
    energy too tightly — the mid is mostly kick spillover, not real mid
    content. Compressed-kick guard at ExemplarFinder.find() excludes
    tracks with r > 0.8 from MID band lessons.

    Same windowing as audio/features.py:49 — sr // 50 samples per window
    (~20 ms windows). Per-window band energy is computed via the SAME
    FFT-mask approach as snapshot_features, but we want a TIME SERIES of
    energies per band (not a single aggregate), so we slide non-overlapping
    windows across the track.
    """
    if samples.size < sr * 2:
        return 0.0  # too short — no honest correlation

    win = sr // 50  # ~20 ms
    n_win = samples.size // win
    if n_win < 10:
        return 0.0  # too few windows for meaningful correlation

    # Per-window FFT → band energy time-series for mid and sub.
    # Window the FFT inside snapshot_features uses 16384-sample FFT; we
    # downsample per-window to match — too expensive otherwise. Use a
    # smaller 1024-sample FFT for the per-window probe (sufficient for
    # band-energy resolution at 48 kHz: ~46 Hz/bin).
    spec_win = 1024
    sub_series = np.zeros(n_win, dtype=np.float32)
    mid_series = np.zeros(n_win, dtype=np.float32)
    for i in range(n_win):
        start = i * win
        end = start + win
        # Pad to spec_win for FFT
        x = samples[start:end]
        if x.size < spec_win:
            x = np.pad(x, (0, spec_win - x.size))
        x = x[:spec_win] * np.hanning(spec_win)
        spec = np.abs(np.fft.rfft(x))
        freqs = np.fft.rfftfreq(spec_win, d=1.0 / sr)
        sub_mask = (freqs >= 20) & (freqs < 100)
        # mid = the combined mid_low + mid_hi band (300-4000 Hz) — same
        # aggregation as snapshot_features
        mid_mask = (freqs >= 300) & (freqs < 4000)
        sub_series[i] = float(np.sqrt(np.mean(spec[sub_mask] ** 2))) if sub_mask.any() else 0.0
        mid_series[i] = float(np.sqrt(np.mean(spec[mid_mask] ** 2))) if mid_mask.any() else 0.0

    # Pearson r — guard against zero variance (silent or DC-only signals)
    sub_std = float(np.std(sub_series))
    mid_std = float(np.std(mid_series))
    if sub_std < 1e-9 or mid_std < 1e-9:
        return 0.0
    r = float(np.corrcoef(sub_series, mid_series)[0, 1])
    return r
```

**Synthetic test fixture (verbatim — copy this into `tests/learn/test_exemplar_kick_guard.py`):**

```python
# tests/learn/test_exemplar_kick_guard.py
import numpy as np
from vibemix.learn.exemplar import _kick_correlation

SR = 48000
DUR_S = 5

def _make_kick_only(distortion: float = 0.0) -> np.ndarray:
    """Synthetic sub-heavy kick: 60 Hz fundamental, gated 4-on-floor at 130 BPM.

    distortion=0.0 → pure sine sub kick (mid bands quiet).
    distortion=0.8 → soft-clipped (mid bands track sub bands — should fire guard).
    """
    n = SR * DUR_S
    t = np.arange(n, dtype=np.float32) / SR
    # 130 BPM = 130/60 Hz beat rate → kick every 60/130 = 0.4615 s
    period_s = 60.0 / 130.0
    # Kick envelope: exponential decay 0.1 s per hit
    kick_env = np.zeros(n, dtype=np.float32)
    for hit in range(int(DUR_S / period_s) + 1):
        start = int(hit * period_s * SR)
        end = min(start + int(0.1 * SR), n)
        decay = np.exp(-np.arange(end - start) / (0.02 * SR))
        kick_env[start:end] += decay
    # 60 Hz sine fundamental
    sub_sine = np.sin(2 * np.pi * 60 * t)
    kick = sub_sine * kick_env
    if distortion > 0:
        kick = np.tanh(kick * (1 + 10 * distortion)) / (1 + distortion)
    return kick.astype(np.float32)

def _make_balanced_mid_track() -> np.ndarray:
    """Synthetic mid-heavy track: 1 kHz lead over quiet sub.
    Should NOT fire the guard — mid and sub uncorrelated."""
    n = SR * DUR_S
    t = np.arange(n, dtype=np.float32) / SR
    sub_kick = _make_kick_only(distortion=0.0) * 0.2  # quiet sub
    # 1 kHz mid lead with independent envelope
    lead = np.sin(2 * np.pi * 1000 * t) * 0.5
    # Modulate lead at 2 Hz (independent of kick rate)
    lead_env = 0.5 + 0.5 * np.sin(2 * np.pi * 2.0 * t)
    return (sub_kick + lead * lead_env).astype(np.float32)

def test_clean_sub_kick_no_mid_passes_guard():
    """A clean 60 Hz sub-only kick has nothing in the mid band → r ≈ 0."""
    samples = _make_kick_only(distortion=0.0)
    r = _kick_correlation(samples, SR)
    assert r < 0.3, f"clean sub kick should have low r, got {r}"

def test_distorted_kick_fires_guard():
    """A heavily distorted sub kick spills into mid → r > 0.8."""
    samples = _make_kick_only(distortion=0.9)
    r = _kick_correlation(samples, SR)
    assert r > 0.8, f"distorted kick should fire guard at r > 0.8, got {r}"

def test_balanced_mid_track_passes_guard():
    """Independent mid lead over quiet kick → r below threshold."""
    samples = _make_balanced_mid_track()
    r = _kick_correlation(samples, SR)
    assert r < 0.8, f"balanced track should pass guard, got {r}"
```

### Pattern 4 — Side-Car `band_shares` Table (sqlite-vec migration)

**What:** Add a NEW non-vec sqlite table inside the EXISTING `library-clap.db` for per-track band-share scalars. vec0 virtual tables don't support `ALTER TABLE ADD COLUMN` (verified at `index_sqlite_vec.py:122-127`), so we use a side-car table joined by `track_id`.

**Why same DB file (not a separate `band_shares.db`):**
- Single backup/rotate lifecycle.
- The dim-mismatch wipe at `index_sqlite_vec.py:145-160` (`recreate_table`) drops `vec_library` but leaves the side-car table alone — orphaned band-shares are cheap (no vector data, just 7 floats per row) and a re-ingest re-writes them.
- Future grounding queries can JOIN `vec_library` and `band_shares` on `track_id` for "find tracks similar to this AND with high low-band" composite queries.

**The schema (verbatim — copy this into `src/vibemix/learn/band_share_store.py`):**

```python
# src/vibemix/learn/band_share_store.py
import sqlite3
from pathlib import Path
import numpy as np
from vibemix.library.index_sqlite_vec import DB_PATH  # shared library-clap.db

BAND_SHARE_TABLE = "band_shares"

def init_schema(conn: sqlite3.Connection) -> None:
    """Create the band_shares side-car table inside library-clap.db.

    Mirror of library/embed_cache.py::init_cache_schema. NOT a vec0 virtual
    table — plain sqlite3 row table. Joined to vec_library by track_id.
    """
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {BAND_SHARE_TABLE} (
            track_id   TEXT PRIMARY KEY,
            sub_share  REAL NOT NULL,
            low_share  REAL NOT NULL,
            mid_share  REAL NOT NULL,
            high_share REAL NOT NULL,
            kick_corr  REAL NOT NULL,
            updated_at REAL NOT NULL
        )
    """)
    conn.commit()

def open_default_db() -> sqlite3.Connection:
    """Open the shared library-clap.db with band_shares schema initialized."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    init_schema(conn)
    return conn

def upsert(conn: sqlite3.Connection, track_id: str,
           sub: float, low: float, mid: float, high: float,
           kick_corr: float, ts: float) -> None:
    """Insert or replace band-share row for one track. Idempotent."""
    conn.execute(f"""
        INSERT INTO {BAND_SHARE_TABLE}
            (track_id, sub_share, low_share, mid_share, high_share,
             kick_corr, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(track_id) DO UPDATE SET
            sub_share=excluded.sub_share,
            low_share=excluded.low_share,
            mid_share=excluded.mid_share,
            high_share=excluded.high_share,
            kick_corr=excluded.kick_corr,
            updated_at=excluded.updated_at
    """, (track_id, sub, low, mid, high, kick_corr, ts))
    conn.commit()

def top_for_band(conn: sqlite3.Connection, band: str, k: int = 3,
                 max_kick_corr: float = 0.8) -> list[tuple[str, float, float]]:
    """Top-k tracks for a band, excluding compressed-kick false-positives.

    Returns [(track_id, band_share, kick_corr), ...] ordered by band_share
    DESC, ties broken by track_id ASC for determinism.

    `band` must be one of {'sub','low','mid','high'}; raises ValueError otherwise.
    `max_kick_corr` is the compressed-kick guard threshold (CONTEXT 0.8 lock).
    For 'mid' lessons the guard is active; for 'sub' and 'low' it's still
    applied because a sub-heavy kick on a "low-band" lesson would teach the
    wrong band relationship (kick fundamentals dominate, not bass synth).
    """
    if band not in ("sub", "low", "mid", "high"):
        raise ValueError(f"unknown band {band!r}; must be one of sub/low/mid/high")
    col = f"{band}_share"
    rows = conn.execute(f"""
        SELECT track_id, {col}, kick_corr
        FROM {BAND_SHARE_TABLE}
        WHERE kick_corr < ?
        ORDER BY {col} DESC, track_id ASC
        LIMIT ?
    """, (max_kick_corr, k)).fetchall()
    return [(r[0], float(r[1]), float(r[2])) for r in rows]
```

### Pattern 5 — Honest-Null Fallback Packaging (hatchling wheel-include)

**What:** Ship ~3-5 MB of CC-BY audio under `assets/learn/band_exemplars/{sub,low,mid,high}/*.mp3`. Hatchling includes non-Python files inside the package directory by default (see `pyproject.toml` comment at line 211).

**Wait — `assets/` is NOT inside `src/vibemix/`.** The default include only catches files INSIDE the package tree. P93 needs to either:
- **(a)** Move the bank under `src/vibemix/learn/assets/band_exemplars/` (inside the package — auto-included).
- **(b)** Add an explicit `[tool.hatch.build.targets.wheel.force-include]` for `assets/learn/`.

**Recommendation: (a) — `src/vibemix/learn/assets/band_exemplars/`** because:
1. No pyproject.toml change required (the package-level include catches it).
2. The bank ships INSIDE the wheel by the same mechanism that ships `state/genre/profiles/*.json` (which the comment at line 211-214 explicitly verified).
3. Code paths can resolve via `importlib.resources` instead of file-system paths (cleaner for the bundled-installer case).

**The path resolver (verbatim — copy into `learn/exemplar.py`):**

```python
def _packaged_bank_dir() -> Path:
    """Return the path to the bundled CC-BY exemplar bank.

    Uses importlib.resources so the resolution works both:
      - in development (running from src/vibemix/)
      - in the bundled wheel (PyInstaller / pip-installed)
    """
    try:
        from importlib.resources import files
        return Path(str(files("vibemix.learn.assets.band_exemplars")))
    except Exception:
        # Dev-time fallback
        return Path(__file__).parent / "assets" / "band_exemplars"

def _fallback_for_band(band: str) -> tuple[str, str, str] | None:
    """Return (synthetic_track_id, file_path, reason) for the packaged
    fallback track for `band`, or None if the bank dir is empty.

    Deterministic: sorts files in the band's subdir alphabetically and
    picks the first. Reason copy is a CONSTANT (NOT live-generated).
    """
    bank_dir = _packaged_bank_dir() / band
    if not bank_dir.exists():
        return None
    files = sorted(bank_dir.glob("*.mp3")) + sorted(bank_dir.glob("*.ogg"))
    if not files:
        return None
    path = files[0]
    # Synthetic track_id so the registry write doesn't collide with library tracks
    synthetic_id = f"_packaged:{band}:{path.stem}"
    reason = "Your library doesn't have a great example of this — listen to this one we packaged"
    return (synthetic_id, str(path), reason)
```

**Per-track attribution manifest (verbatim — copy into `assets/learn/band_exemplars/MANIFEST.json` — wait, into `src/vibemix/learn/assets/band_exemplars/MANIFEST.json` per recommendation (a)):**

```json
{
  "schema_version": 1,
  "tracks": {
    "sub/sub_example_01.mp3": {
      "title": "Title here",
      "artist": "Artist here",
      "license": "CC-BY-4.0",
      "source_url": "https://...",
      "duration_s": 45.0,
      "band_dominance": "sub",
      "notes": "Source attribution + license verified 2026-XX-XX"
    },
    "low/...": { ... },
    "mid/...": { ... },
    "high/...": { ... }
  }
}
```

### Pattern 6 — ExemplarPlayer Second `sd.OutputStream` (precedent: `open_passthrough_output`)

**What:** A dedicated `sd.OutputStream` on the user-picked headphone device. NOT `PlaybackQueue` (mic-gated). NOT `open_voice_output` (mono int16, wrong format for stereo music).

**The precedent (verbatim from `src/vibemix/platform/_audio_macos.py:298-326`):**

```python
def open_passthrough_output(
    self,
    device_index: int,
    *,
    sample_rate: int,
    channels: int,
    block_size: int,
    callback: AudioCallback,
) -> AudioStream:
    """Open passthrough output (sd.OutputStream @ float32 — djay → speakers stereo)."""
    assert_device_sample_rate(device_index, sample_rate)
    stream = sd.OutputStream(
        device=device_index,
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
        blocksize=block_size,
        latency="low",
        callback=callback,
    )
    if int(stream.samplerate) != sample_rate:
        negotiated = int(stream.samplerate)
        stream.close()
        raise SampleRateMismatchError(...)
    stream.start()
    return _SoundDeviceStreamHandle(stream)
```

**ExemplarPlayer (NEW file `src/vibemix/learn/audio_cue.py`):**

```python
# src/vibemix/learn/audio_cue.py
from __future__ import annotations
import threading
import time
import numpy as np
import sounddevice as sd
from pathlib import Path

from vibemix.audio.constants import SILENT_RMS
from vibemix.state.music_state import MusicState

# Default-safe gain (CONTEXT.md lock).
_DEFAULT_GAIN_DB = -12.0
# Lower-by-6 gain when master deck is loud (avoid hot-mix bleed into headphones).
_LOUD_MASTER_GAIN_DB = -18.0
# Master-RMS threshold above which we drop to -18 dB. -6 dBFS in linear ≈ 0.5
# (RMS of a full-scale sine is 0.707; -6 dBFS RMS ≈ 0.5).
_LOUD_MASTER_RMS_LINEAR = 0.5

def _db_to_gain(db: float) -> float:
    return float(10 ** (db / 20.0))

def _choose_gain_db(master_rms: float) -> float:
    """Pick -12 dB by default; -18 dB when master deck audio is hot."""
    if master_rms is None or master_rms < SILENT_RMS:
        return _DEFAULT_GAIN_DB
    if master_rms > _LOUD_MASTER_RMS_LINEAR:
        return _LOUD_MASTER_GAIN_DB
    return _DEFAULT_GAIN_DB

class ExemplarPlayer:
    """Plays a packaged or library track on a dedicated headphone OutputStream.

    Owns its own sd.OutputStream — does NOT reuse PlaybackQueue (mic-gated
    at audio/buffers.py:195; reuse would silence Kaan's mic during exemplar
    playback). Stereo float32 @ track sample rate; PyAV/FFmpeg decode.

    Course 3 active-session guard (P96 wires; P93 scaffolds): can_play()
    returns False when state.session_active and state.audible_deck != "none".
    """

    def __init__(self, device_index: int, *, state: MusicState):
        self._device_index = device_index
        self._state = state
        self._stream: sd.OutputStream | None = None
        self._buffer: np.ndarray | None = None
        self._cursor = 0
        self._lock = threading.Lock()
        self._on_stop = None  # set by caller for ipc.learn.exemplar_stop emit

    def can_play(self) -> bool:
        """Active-session guard scaffolding. P93 returns True for non-active
        sessions; P96 wires the real check against state.session_active +
        state.audible_deck."""
        # P93 scaffolding: always allow. P96 lands the real guard.
        return True

    def play(self, file_path: str, *, on_stop=None) -> None:
        """Decode + start playback. Idempotent — stops any prior playback first."""
        self.stop()
        if not self.can_play():
            return
        # Decode via PyAV/FFmpeg → stereo float32 at native sample rate.
        from vibemix.library.audio_decode import load_audio_stereo
        samples, sr = load_audio_stereo(file_path)  # NEW — see Pattern 7

        gain = _db_to_gain(_choose_gain_db(self._state.audio_rms))
        samples = (samples * gain).astype(np.float32)

        with self._lock:
            self._buffer = samples
            self._cursor = 0
            self._on_stop = on_stop

        def _callback(outdata, frames, time_info, status):
            with self._lock:
                buf = self._buffer
                cur = self._cursor
                if buf is None:
                    outdata.fill(0)
                    raise sd.CallbackStop
                end = cur + frames
                if end >= buf.shape[0]:
                    # Tail of buffer; pad with zeros then stop on next callback.
                    tail = buf[cur:]
                    outdata[: tail.shape[0]] = tail
                    outdata[tail.shape[0]:] = 0
                    self._buffer = None
                    on_stop_local = self._on_stop
                    self._on_stop = None
                    # Stop OUTSIDE the lock to avoid reentrancy
                    if on_stop_local is not None:
                        # Schedule on caller's event loop — emit in stop()
                        pass
                    raise sd.CallbackStop
                outdata[:] = buf[cur:end]
                self._cursor = end

        self._stream = sd.OutputStream(
            device=self._device_index,
            samplerate=sr,
            channels=2,
            dtype="float32",
            latency="low",
            callback=_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        """Stop any in-flight playback. Idempotent."""
        with self._lock:
            stream = self._stream
            self._stream = None
            self._buffer = None
            on_stop_local = self._on_stop
            self._on_stop = None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        if on_stop_local is not None:
            try:
                on_stop_local()
            except Exception:
                pass
```

### Pattern 7 — Stereo Decode Extension (`library/audio_decode.py`)

**What:** The existing `load_audio_mono(path, target_sr)` at `library/audio_decode.py:45-64` decodes to MONO float32. ExemplarPlayer needs STEREO for music quality (the CC-BY bank tracks are stereo; library tracks are usually stereo).

**The extension (NEW function in `library/audio_decode.py`):**

```python
def load_audio_stereo(path: str | Path) -> tuple[np.ndarray, int]:
    """Decode an audio file to stereo float32 at native sample rate.

    Returns (samples, sr) where samples.shape = (N, 2). Mono inputs are
    duplicated across channels. Uses PyAV/FFmpeg (existing av.open pattern
    at line 64).
    """
    import av
    container = av.open(str(Path(path).expanduser()))
    stream = container.streams.audio[0]
    sr = int(stream.sample_rate)
    resampler = av.AudioResampler(
        format="flt",         # float32 planar
        layout="stereo",
        rate=sr,
    )
    chunks = []
    for frame in container.decode(audio=0):
        resampled = resampler.resample(frame)
        for r in resampled:
            # r.to_ndarray() returns shape (channels, samples) for planar;
            # transpose to (samples, channels)
            arr = r.to_ndarray().T
            chunks.append(arr.astype(np.float32))
    container.close()
    if not chunks:
        raise ValueError(f"load_audio_stereo: no audio frames in {path!r}")
    samples = np.concatenate(chunks, axis=0)
    return samples, sr
```

### Pattern 8 — Settings Persistence: `learn.headphone_device_index` on existing `ipc.settings.set`

**What:** A new optional field `learn.headphone_device_index: int | null` on the EXISTING `ipc.settings.set` envelope. P93 lands the field; P97 lands the wizard UI that writes it.

**The envelope shape extension (`tauri/ui/src/ipc/messages.schema.json`):**

The existing `ipc.settings.set` envelope has a `payload` with a `learn.*`-prefixed key. The pattern matches existing `mascot.*` / `recording.*` / `lens` / `mood` keys.

```json
// Pseudo-patch — actual JSON-Schema edit lives in messages.schema.json
{
  "$id": "#/definitions/SettingsSetPayload",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    ...
    "learn.headphone_device_index": {
      "type": ["integer", "null"],
      "minimum": 0,
      "description": "Headphone output device index for tutor exemplar playback. null = system default."
    }
  }
}
```

**The config_store extension (`src/vibemix/runtime/config_store.py`):**

```python
# Pseudo-patch — add to ConfigStore dataclass or extra dict:
@dataclass
class LearnSettings:
    headphone_device_index: int | None = None

# Or, if using the extra-dict pattern:
# extra["learn.headphone_device_index"] = int | None
```

**The reader helper (NEW in `src/vibemix/learn/settings.py` or extension of `runtime/settings.py`):**

```python
def read_learn_headphone_device_index() -> int | None:
    """Read the headphone device index from ConfigStore. None = system default."""
    from vibemix.runtime.config_store import load_config
    try:
        cfg = load_config()
        return cfg.extra.get("learn.headphone_device_index")
    except Exception:
        return None
```

### Pattern 9 — Ingest-Time Band-Share Computation (additive edit to `folder_ingest.py`)

**What:** At the SAME point in the existing CLAP ingest loop where each track's vector is added to the store, also compute the band-shares + kick-correlation and upsert into the side-car table.

**The edit (verbatim — surgical 8-line addition to `library/folder_ingest.py:355-365`):**

```python
# library/folder_ingest.py — context around line 355-365
# (EXISTING)
try:
    vec = embedder.embed_track(entry)
except Exception as e:
    ...
    continue

# Honest store: only persist a real vector.
store.add_batch([(entry.track_id, vec)])
handled[entry.track_id] = entry

# === NEW (P93) — additive: compute + persist band-shares for the same track ===
# Gated by an opt-in flag on the IngestReport / ingest_folder() arg so the
# CLAP-only ingest path (legacy callers) stays byte-identical.
if compute_band_shares:  # NEW kwarg on ingest_folder()
    try:
        from vibemix.learn.exemplar import compute_band_shares as _bs_compute
        from vibemix.learn.band_share_store import open_default_db, upsert
        feats = _bs_compute(str(path))
        with open_default_db() as bs_conn:
            upsert(
                bs_conn, entry.track_id,
                feats["sub_share"], feats["low_share"],
                feats["mid_share"], feats["high_share"],
                feats["kick_corr"], time.time(),
            )
    except Exception as e:
        # P93 band-share is best-effort — never abort an otherwise-good ingest
        logger.warning("[band-share err] %s: %s", path, e)

# === END NEW ===

if was_cached:
    ...
```

**Why `compute_band_shares` kwarg (not always-on):** Existing folder_ingest callers (e.g. the `vibemix library ingest <folder>` CLI) shouldn't pay the FFT cost unless they need exemplar engine support. Default `False` keeps the existing CLAP-only ingest byte-identical; the v9.0 wizard sets `True`. The CLI test surface `vibemix learn exemplar <band>` instructs the user to re-ingest with the flag if the side-car table is empty.

## The 4-Site Mirror — Verbatim Code

Below are the EXACT diffs the planner should land. These mirror the v6 `[recall:]` commits `2016e36b` (sites 1+2 atomic), `977c0140` (site 3), and `0bfc8bd0` (site 4).

### Site 1 + 2 (ATOMIC — must land in ONE commit)

**File:** `src/vibemix/state/evidence_registry.py`
**Lines:** 90-113 (frozenset + docstring) and 116-138 (regex + docstring)

```python
# --- existing line 96-99 (docstring update for the new source) ---
# Add this stanza BETWEEN the existing `key` and `SCHEMA-MIRROR` lines:
#: ``exemplar`` = packaged or library band-exemplar reference, body
#: ``<track_id>`` — Phase 93 (EXEMPLAR-05). Existence-only retrieval-time
#: source that makes a fabricated ``[exemplar:<id>]`` uncitable-by-construction:
#: it joins the linter's EXISTENCE-ONLY set purely by being IN this frozenset
#: and ABSENT from ``citation_linter.py::_TIME_KEYED_SOURCES`` (mirrors
#: ``key``/``track``/``recall``). The ExemplarFinder writes ``("exemplar",
#: track_id, t_session)`` BEFORE the LLM emits the cite so unregistered ids
#: strip the turn.

# --- existing line 111-113 (the frozenset itself) ---
EVIDENCE_SOURCES: frozenset[str] = frozenset(
    {"ev", "aud", "midi", "track", "screen", "mix", "tend", "key", "recall", "exemplar"}
    # ↑ APPEND "exemplar" — 9 → 10 sources
)

# --- existing line 137 (the regex alternation) ---
_SOURCE_ALT = "ev|aud|midi|track|screen|mix|tend|key|recall|exemplar"
# ↑ APPEND |exemplar — MUST land in SAME commit as the frozenset change.

# --- existing line ~145-150 (the EBNF docstring) ---
#:   source   := 'ev' | 'aud' | 'midi' | 'track' | 'screen' | 'mix' | 'tend'
#:             | 'key' | 'recall' | 'exemplar'
# ↑ APPEND ' | 'exemplar'' in the source rule

#:   exemplar-body := <track_id>          # e.g. "library:Marlon Hoffstadt - Atlas"
#:                                        # or "_packaged:low:track_03" — full
#:                                        # body survives parse_citations (no
#:                                        # whitespace/comma/bracket; P93)
# ↑ APPEND this body-rule stanza after the recall-body line
```

### Site 3 — `CITATION_GRAMMAR_BLOCK`

**File:** `src/vibemix/prompts/matrix.py`
**Lines:** ~93-110 (docstring) and 110-148 (the grammar block)

```python
# --- existing line ~93-98 (the lock-step comment) ---
# Anti-prompt-injection (T-18-03-01): the block is a fixed string with NO
# interpolation — no user input can mutate it (mirrors MOOD_PERSONAS pattern).
# The 10 source forms are kept in lock-step with EVIDENCE_SOURCES (Plan 18-01,
# + `key` added Phase 59 / DECK-03, + `recall` added Phase 65 / RECALL-01,
# + `exemplar` added Phase 93 / EXEMPLAR-05) via Test R cross-validation in
# tests/prompts/test_matrix.py.
# ↑ Update count "9" → "10" and append "+ exemplar Phase 93"

# --- existing line ~118-128 (the Forms list) ---
Forms (each is a single citation; the linter accepts any of these):
  [ev:<TYPE>@<t>]     event citation, e.g. [ev:KICK_SWAP@45.2]
  [aud:<key>@<t>]     audio feature, e.g. [aud:bpm@45.2] or [aud:rms@45.2]
  [midi:<event>@<t>]  controller event, e.g. [midi:cue_a@12.7]
  [track:<id>]        track reference, e.g. [track:Marlon Hoffstadt - Atlas]
  [screen:<key>]      screen element, e.g. [screen:waveform_deck_a]
  [mix:<derived>]     derived mix-state, e.g. [mix:audible_deck=A]
  [tend:<fact>]       user-profile fact, e.g. [tend:user_likes_acid]
  [key:<deck>:<camelot>]  deck harmonic key, e.g. [key:A:8A]
  [recall:<record_id>]  past-moment reference, e.g. [recall:20260520-2200:7]
  [exemplar:<track_id>]  band-exemplar track, e.g. [exemplar:library:Marlon Hoffstadt - Atlas]
  # ↑ APPEND this line as the 10th form
```

### Site 4 — `_build_citation_strip`

**File:** `src/vibemix/agent/dj_cohost.py`
**Lines:** 255 (the allow-list set) and 277 (the elif branch insertion point)

```python
# --- existing line 240-256 (allow-list set) ---
# In _build_citation_strip(), the source allow-list at line 255 — add "exemplar":
if source not in ("ev", "mix", "midi", "key", "recall", "exemplar"):
    continue
# ↑ APPEND "exemplar" — mirrors the recall:" landing at this same site
# in commit 0bfc8bd0 (Phase 66 COPILOT-01).

# --- existing line 270-290 (the per-source verb derivation switch) ---
# After the elif source == "recall": branch (lines 277-290), add a new branch:
elif source == "exemplar":
    # Phase 93 (EXEMPLAR-05) — mirrors the ``recall`` and ``key`` precedents
    # above for opaque/structured bodies. The ``exemplar`` body shape is
    # ``<track_id>`` (e.g. ``library:Marlon Hoffstadt - Atlas`` or
    # ``_packaged:low:track_03``). The full track_id rides in ``event_id``
    # for the click→tutor-context deep-link. The chip verb is a fixed
    # letters-only ``"exemplar"`` label — deriving a verb from a track-id
    # string is meaningless and would leak embedding-internal values to
    # the UI surface (P93-RESEARCH.md §4-Site Mirror Pattern). A single
    # lowercase word trivially matches the locked verb-format regex
    # ``^[a-z]+( [a-z]+){0,2}$``.
    verb = "exemplar"
```

## The 4-Site Lock Test (Pattern 10)

**File (NEW):** `tests/learn/test_exemplar_citation_schema_mirror.py`

```python
# SPDX-License-Identifier: Apache-2.0
"""Phase 93 — 4-site schema-mirror lock for the `[exemplar:]` evidence source.

Mirrors the v6 [recall:] precedent EXACTLY. Each site MUST carry the
``exemplar`` token; if ANY site drifts, the grammar lock breaks and a
fabricated [exemplar:<id>] can ride through un-validated (the silent-poisoning
hole that the multi-site lock-step contract exists to prevent).

REQ-ID: EXEMPLAR-05 (citation source schema-mirror lock).
"""
from __future__ import annotations
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent


def test_site_1_evidence_sources_frozenset_contains_exemplar() -> None:
    """Site 1: EVIDENCE_SOURCES frozenset @ state/evidence_registry.py:111."""
    from vibemix.state.evidence_registry import EVIDENCE_SOURCES
    assert "exemplar" in EVIDENCE_SOURCES, (
        "EVIDENCE_SOURCES drift — `exemplar` missing from the frozenset. "
        "Phase 93 4-site mirror is broken; fabricated [exemplar:<id>] rides "
        "through un-validated."
    )


def test_site_2_source_alt_regex_includes_exemplar() -> None:
    """Site 2: _SOURCE_ALT regex alternation @ state/evidence_registry.py:137."""
    from vibemix.state.evidence_registry import _SOURCE_ALT
    assert "exemplar" in _SOURCE_ALT.split("|"), (
        "_SOURCE_ALT regex drift — `exemplar` missing from the alternation. "
        "parse_citations() will not match [exemplar:<id>] atoms; the linter "
        "never sees them."
    )


def test_site_2b_evidence_citation_re_matches_exemplar_atom() -> None:
    """Sanity: a synthetic [exemplar:<id>] passes the compiled regex."""
    from vibemix.state.evidence_registry import EVIDENCE_CITATION_RE, parse_citations
    assert EVIDENCE_CITATION_RE.fullmatch("[exemplar:library:Marlon-Atlas]") is not None
    # Inner colon survives as part of the body (mirrors recall: behavior)
    parsed = parse_citations("[exemplar:library:Marlon-Atlas]")
    assert parsed == [("exemplar", "library:Marlon-Atlas")]


def test_site_3_citation_grammar_block_includes_exemplar() -> None:
    """Site 3: CITATION_GRAMMAR_BLOCK @ prompts/matrix.py."""
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK
    assert "[exemplar:" in CITATION_GRAMMAR_BLOCK, (
        "CITATION_GRAMMAR_BLOCK drift — `[exemplar:` form missing from the "
        "system instruction. Gemini will not know the citation shape exists."
    )


def test_site_4_citation_strip_allow_list_includes_exemplar() -> None:
    """Site 4: _build_citation_strip allow-list @ agent/dj_cohost.py:255.

    AST/grep parity test — reads the source file directly and asserts the
    allow-list tuple contains "exemplar". The runtime `_build_citation_strip`
    can't be unit-tested without standing up a full agent; this static test
    pins the source-of-truth membership.
    """
    src = (_REPO / "src" / "vibemix" / "agent" / "dj_cohost.py").read_text()
    # The allow-list tuple at line ~255 — match the FULL tuple shape
    # ("ev", "mix", "midi", "key", "recall", "exemplar")
    pattern = re.compile(
        r'if source not in\s*\(\s*("ev"\s*,\s*"mix"\s*,\s*"midi"\s*,\s*"key"\s*,\s*"recall"\s*,\s*"exemplar"\s*)\)',
        re.MULTILINE,
    )
    assert pattern.search(src) is not None, (
        "Site 4 drift — `exemplar` missing from the _build_citation_strip "
        "allow-list tuple in dj_cohost.py. Chip-strip will silently drop "
        "valid [exemplar:<id>] grounded citations."
    )


def test_all_four_sites_lockstep() -> None:
    """Cross-validation: EVIDENCE_SOURCES is the source-of-truth — every
    source in the frozenset must appear in the grammar block."""
    from vibemix.state.evidence_registry import EVIDENCE_SOURCES
    from vibemix.prompts.matrix import CITATION_GRAMMAR_BLOCK
    for source in EVIDENCE_SOURCES:
        assert f"[{source}:" in CITATION_GRAMMAR_BLOCK, (
            f"EVIDENCE_SOURCES drift: source {source!r} not in prompt grammar block"
        )
```

## The Grounding E2E Test (Pattern 11)

**File (NEW):** `tests/learn/test_exemplar_grounding_e2e.py`

```python
# SPDX-License-Identifier: Apache-2.0
"""Phase 93 — Invariant #2 binding: fabricated [exemplar:bogus] strips the whole turn.

Mirrors the v6 test_fabricated_recall_strips_turn pattern at
tests/agent/test_dj_cohost_linter.py:250-330.

REQ-ID: EXEMPLAR-05 (citation grounding via 4-site mirror).
"""
from __future__ import annotations
from vibemix.state.evidence_registry import EvidenceRegistry, parse_citations


def test_fabricated_exemplar_id_not_in_registry_means_unmatched() -> None:
    """A fabricated [exemplar:bogus] resolves to no registry observation.

    The runtime contract: ExemplarFinder.find() calls
    registry.write("exemplar", track_id, t_session) for every track it
    recommends; the LLM only sees track_ids it has been TOLD about via
    the lesson prompt; a track_id the LLM invents → registry.has() returns
    False → the CitationLinter strips the whole turn.

    This test verifies the lower half of that contract: an unregistered
    [exemplar:<id>] is NOT marked as grounded by the registry. The linter's
    "strip whole turn on any unresolved cite" behavior is already tested
    in tests/coach/test_citation_linter.py — when sites 1+2 land, the
    linter automatically gates [exemplar:] atoms because parse_citations
    now matches them and the existence check runs.
    """
    reg = EvidenceRegistry()
    # Register one real exemplar
    reg.write("exemplar", "library:track_real", 10.0)

    # Real cite resolves
    assert reg.has("exemplar", "library:track_real", 10.0, tol=2.0)

    # Fabricated cite does NOT
    assert not reg.has("exemplar", "library:track_bogus", 10.0, tol=2.0)


def test_parse_citations_extracts_exemplar_atom() -> None:
    """Sanity: parse_citations() returns the exemplar atom for the linter."""
    text = "the lows hit hard [exemplar:library:Marlon-Atlas] right there"
    parsed = parse_citations(text)
    assert ("exemplar", "library:Marlon-Atlas") in parsed


def test_parse_citations_extracts_exemplar_in_multi_atom() -> None:
    """[ev:KICK_SWAP@45.2,exemplar:library:foo] — multi-citation form."""
    text = "[ev:KICK_SWAP@45.2,exemplar:library:foo]"
    parsed = parse_citations(text)
    assert ("ev", "KICK_SWAP@45.2") in parsed
    assert ("exemplar", "library:foo") in parsed
```

## CLI Subcommand Wiring (Pattern 12)

**File (EDIT):** `src/vibemix/__main__.py` lines 3316-3330 (extend the existing `learn` subcommand block from P92-04 Task 2).

**The verbatim diff:**

```python
# Phase 92 (LESSON-03) — `vibemix learn <sub>` dispatch.
# Phase 93 (EXEMPLAR-01..05) — extends with `learn exemplar <band>` subcommand.
if raw_argv and raw_argv[0] == "learn":
    if len(raw_argv) >= 2 and raw_argv[1] == "reset":
        from vibemix.learn.progress import reset_progress

        reset_progress()
        print("learn progress reset.", file=sys.stdout, flush=True)
        sys.exit(0)
    # === NEW (P93) — `learn exemplar <band>` ===
    if len(raw_argv) >= 3 and raw_argv[1] == "exemplar":
        band = raw_argv[2]
        if band not in ("sub", "low", "mid", "high"):
            print(
                f"vibemix learn exemplar: unknown band {band!r}; "
                "must be one of sub/low/mid/high",
                file=sys.stderr,
                flush=True,
            )
            sys.exit(2)
        from vibemix.learn.exemplar import ExemplarFinder
        finder = ExemplarFinder()
        result = finder.find(band, k=1)
        if not result:
            print(
                f"learn exemplar {band}: no library track passed the floor; "
                "no packaged fallback found either.",
                file=sys.stdout, flush=True,
            )
            sys.exit(1)
        track_id, file_path, score, reason = result[0]
        print(f"track: {track_id}", file=sys.stdout)
        print(f"path:  {file_path}", file=sys.stdout)
        print(f"score: {band}_share={score:.3f}", file=sys.stdout)
        print(f"why:   {reason}", file=sys.stdout)
        sys.exit(0)
    # === END NEW ===
    # Unknown `learn` subcommand — surface usage + exit 2 (argparse-style).
    print(
        f"vibemix learn: unknown subcommand {raw_argv[1:]!r}; "
        "available: reset, exemplar <sub|low|mid|high>",
        file=sys.stderr,
        flush=True,
    )
    sys.exit(2)
```

## Code Examples

### Example 1 — `ExemplarFinder.find()` (the public API)

```python
# src/vibemix/learn/exemplar.py
from dataclasses import dataclass
from pathlib import Path
import time
import numpy as np

from vibemix.audio.features import snapshot_features
from vibemix.audio.buffers import AudioBuffer
from vibemix.library.audio_decode import load_audio_mono
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.learn.band_share_store import open_default_db, top_for_band
from vibemix.state.evidence_registry import EvidenceRegistry

# Minimum tracks that must pass the band floor before we trust library results.
_LIBRARY_FLOOR = 3
# Compressed-kick guard threshold (CONTEXT lock).
_KICK_GUARD_R = 0.8


@dataclass
class ExemplarPick:
    track_id: str
    file_path: str
    band_score: float       # the band-share scalar for the picked band
    reason: str             # "from your library — strongest low-band" / honest-null


class ExemplarFinder:
    """Picks band-exemplar tracks for EQ lessons. Pure-compute over the
    side-car band_shares table; falls back to the packaged CC-BY bank
    when library has < 3 tracks passing the floor."""

    def __init__(self, *, registry: EvidenceRegistry | None = None) -> None:
        self._registry = registry
        # Lazy load the library cache (cheap — pickle, ~1ms)
        self._library: RekordboxLibrary | None = None

    def _load_library(self) -> RekordboxLibrary | None:
        if self._library is not None:
            return self._library
        try:
            self._library = RekordboxLibrary.try_load_cache()
        except Exception:
            return None
        return self._library

    def find(self, band: str, k: int = 1,
             t_session: float | None = None) -> list[ExemplarPick]:
        """Return top-k band exemplars for `band` ∈ {'sub','low','mid','high'}.

        Side effects:
          - For each picked track, calls
            registry.write("exemplar", track_id, t_session) so the LLM's
            subsequent [exemplar:<track_id>] cite resolves to a registered
            observation. This is the LOAD-BEARING grounding contract.

        Returns:
          List of ExemplarPick. Length ≤ k. May fall back to packaged bank
          (still returned as ExemplarPick with synthetic track_id "_packaged:...")
          if library has < 3 tracks passing the floor.

          Empty list ONLY if both library and packaged bank are empty (degraded
          install — should never happen in production).
        """
        if t_session is None:
            t_session = time.time()
        try:
            with open_default_db() as conn:
                rows = top_for_band(conn, band, k=max(k, _LIBRARY_FLOOR),
                                    max_kick_corr=_KICK_GUARD_R)
        except Exception:
            rows = []

        picks: list[ExemplarPick] = []
        if len(rows) >= _LIBRARY_FLOOR:
            # Library has enough — pick top-k. Resolve track file paths.
            lib = self._load_library()
            for track_id, score, _kick in rows[:k]:
                file_path = self._resolve_library_path(lib, track_id)
                if file_path is None:
                    continue
                if self._registry is not None:
                    self._registry.write("exemplar", track_id, t_session)
                picks.append(ExemplarPick(
                    track_id=track_id,
                    file_path=file_path,
                    band_score=score,
                    reason=f"from your library — strongest {band}-band track",
                ))

        if picks:
            return picks

        # Honest-null fallback — packaged CC-BY bank
        fb = _fallback_for_band(band)
        if fb is None:
            return []
        synthetic_id, file_path, reason = fb
        if self._registry is not None:
            self._registry.write("exemplar", synthetic_id, t_session)
        return [ExemplarPick(
            track_id=synthetic_id,
            file_path=file_path,
            band_score=0.0,  # synthetic — packaged bank
            reason=reason,
        )]

    def _resolve_library_path(self, lib: RekordboxLibrary | None,
                              track_id: str) -> str | None:
        if lib is None:
            return None
        entry = lib.tracks.get(track_id)
        if entry is None:
            return None
        return entry.path


# Defined earlier in module (see Pattern 5)
def _packaged_bank_dir() -> Path: ...
def _fallback_for_band(band: str) -> tuple[str, str, str] | None: ...
def _kick_correlation(samples: np.ndarray, sr: int) -> float: ...
def compute_band_shares(audio_path: str) -> dict: ...
```

### Example 2 — Packaged-Fallback Test

```python
# tests/learn/test_exemplar_packaged_fallback.py
import shutil
from pathlib import Path
import pytest
from vibemix.learn.exemplar import ExemplarFinder


def test_empty_library_falls_back_to_packaged_bank(tmp_path, monkeypatch):
    """When the side-car band_shares table is empty, the engine falls back
    to the packaged CC-BY bank with the honest-null reason."""
    # Point the side-car DB at a tmp empty file
    monkeypatch.setattr(
        "vibemix.learn.band_share_store.DB_PATH", tmp_path / "library-clap.db"
    )
    # Block library cache load
    monkeypatch.setattr(
        "vibemix.library.rekordbox.RekordboxLibrary.try_load_cache",
        lambda: None,
    )

    finder = ExemplarFinder()
    picks = finder.find("low", k=1)
    # Must return a packaged-bank pick if the bank exists
    if not picks:
        pytest.skip("Packaged bank not installed — CC-BY assets not yet shipped")
    assert picks[0].track_id.startswith("_packaged:low:")
    assert "Your library doesn't have a great example" in picks[0].reason


def test_packaged_bank_directory_layout():
    """The bank must have all 4 band subdirs and a MANIFEST.json."""
    from vibemix.learn.exemplar import _packaged_bank_dir
    bank = _packaged_bank_dir()
    if not bank.exists():
        pytest.skip("Packaged bank not yet shipped")
    for band in ("sub", "low", "mid", "high"):
        assert (bank / band).exists(), f"Missing band subdir: {band}"
    assert (bank / "MANIFEST.json").exists()


def test_manifest_attribution_present_in_notice():
    """Every track in MANIFEST.json must have an attribution line in NOTICE.md."""
    import json
    from vibemix.learn.exemplar import _packaged_bank_dir
    bank = _packaged_bank_dir()
    if not (bank / "MANIFEST.json").exists():
        pytest.skip("Manifest not yet shipped")
    manifest = json.loads((bank / "MANIFEST.json").read_text())
    notice = Path(__file__).parent.parent.parent / "NOTICE.md"
    if not notice.exists():
        pytest.skip("NOTICE.md not yet authored")
    notice_text = notice.read_text()
    for track_rel, meta in manifest.get("tracks", {}).items():
        # NOTICE.md must contain the track's title + artist + license
        assert meta["title"] in notice_text, f"NOTICE.md missing: {meta['title']}"
        assert meta["artist"] in notice_text, f"NOTICE.md missing artist: {meta['artist']}"
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FFT-based band-energy computation | Custom FFT loop | Reuse `audio/features.py::snapshot_features` band-energy block (lines 71-89) | Verbatim port from v4; already tuned; CI-pinned; producing this differently would diverge from the live event-detector path. |
| Audio file decode | `subprocess.run(ffmpeg)` shell-out | `library/audio_decode.py::load_audio_mono` + new `load_audio_stereo` | PyAV is already the in-tree FFmpeg binding; subprocess shell-out is fragile (path resolution, output parsing). |
| Mic-gated audio output | Reusing `PlaybackQueue` | NEW `sd.OutputStream` in ExemplarPlayer | `PlaybackQueue.push()` triggers `MicBuffer._current_gain` mute at `audio/buffers.py:226` — would silence Kaan's mic during exemplar playback. |
| sqlite-vec ALTER TABLE | `ALTER TABLE vec_library ADD COLUMN band_shares ...` | Side-car `band_shares` table joined by track_id | vec0 virtual tables don't support ALTER TABLE ADD COLUMN — verified at `index_sqlite_vec.py:122-127`. |
| New ws envelope for exemplar | New `ipc.exemplar.*` family | `ipc.learn.exemplar_play` / `exemplar_stop` (P92 shipped schema) + `ipc.settings.set` (existing) | One-socket invariant + zero-new-IPC-family acid test. |
| Citation source linter / strip logic | New linter for `[exemplar:]` | Existing `state/citation_linter.py` + Phase 20 strip gate | The 4-site mirror is what makes existing infra work for the new source. No new linter needed. |
| Atomic 4-site landing | Bespoke "deploy these 4 changes" script | Single commit (or 3-commit pattern matching v6 `[recall:]` precedent) | Atomic git commit IS the deploy mechanism. |

**Key insight:** P93's "engine + evidence source" responsibilities ride entirely on existing primitives. The DSP math, the sqlite-vec store, the registry, the linter, the citation grammar — all exist. P93 is **wiring + one new helper module per concern (exemplar.py, audio_cue.py, band_share_store.py)** — NOT new infrastructure.

## Runtime State Inventory

> Skip — P93 is a greenfield-additive phase. New module, new tests, new asset bundle. No rename/refactor/migration concerns.

## Common Pitfalls

### Pitfall 1: Sites 1+2 split across commits

**What goes wrong:** A fabricated `[exemplar:bogus]` rides through unmatched by `parse_citations()` because `_SOURCE_ALT` hasn't been updated yet. The CitationLinter never sees the atom; the strip gate never fires.

**Why it happens:** Splitting "evidence source schema" across logical commits (one for the frozenset, one for the regex) feels reasonable but breaks the lock-step contract.

**How to avoid:** ONE commit for sites 1+2. The v6 precedent is `2016e36b` — read its commit message.

**Warning signs:** Test `test_site_2_source_alt_regex_includes_exemplar` failing while `test_site_1_evidence_sources_frozenset_contains_exemplar` passes.

### Pitfall 2: `PlaybackQueue` reuse silencing Kaan's mic

**What goes wrong:** During exemplar playback, Kaan's mic input gets gated (set to `MIC_GAIN_AT_AI_TALK`) by `MicBuffer._current_gain` at `audio/buffers.py:226` because `Levels.voice` rises when the queue has content.

**Why it happens:** `PlaybackQueue` was designed for AI VOICE (mic must mute to prevent feedback). It's not a generic audio sink.

**How to avoid:** ExemplarPlayer owns its own `sd.OutputStream` on a DIFFERENT device (headphones). Never touch `PlaybackQueue`.

**Warning signs:** Kaan reports "the app stops listening when the exemplar plays."

### Pitfall 3: Computing band-shares from a 5-second snapshot (not full track)

**What goes wrong:** `snapshot_features(buf, seconds=5.0)` was designed for LIVE event detection — the last 5 seconds of the audio buffer. For a library track, that snapshots a random 5s window (the END of the file as decoded), which may be the OUTRO (low energy in everything) or a BREAKDOWN (lots of high band).

**Why it happens:** Reusing the function naively.

**How to avoid:** Pass `seconds=duration_s` (full track duration) so the FFT covers the entire file. See Pattern 2.

**Warning signs:** Inconsistent band-share values for the same track across re-ingests; "obvious bass-heavy" tracks ranking low for low band.

### Pitfall 4: CC-BY bank ships without `NOTICE.md` attribution

**What goes wrong:** Apache 2.0 ships fine but CC-BY 4.0 REQUIRES attribution. Distributing a CC-BY track without attribution = license violation = Bravoh exposure.

**Why it happens:** Asset acquisition is async (Kaan / Francesco grab tracks; engineering writes attribution later).

**How to avoid:** CI gate `test_manifest_attribution_present_in_notice` (Pattern 11 / Example 2) blocks merge if MANIFEST entries lack NOTICE.md lines. Belt + suspenders.

**Warning signs:** Manifest entries appear but `NOTICE.md` is empty or doesn't reference the track.

### Pitfall 5: Compressed-kick guard too aggressive (false-positives)

**What goes wrong:** Pearson r > 0.8 excludes legit tracks where mid energy genuinely tracks the kick rhythm (e.g. a punchy electro track with mids riding the kick). Library shrinks; falls to packaged bank too often.

**Why it happens:** The 0.8 threshold is CONTEXT-locked but unproven on Kaan's specific library.

**How to avoid:** Surface the threshold as a one-line tunable constant in `learn/exemplar.py` (mirror of `RECALL_CALLBACK_COOLDOWN_S` pattern at `dj_cohost.py:173`). Flag `§EXEMPLAR-KICK-GUARD-EAR` KAAN-ACTION for Kaan to tune on real hardtechno set.

**Warning signs:** `vibemix learn exemplar mid` always falls back to packaged bank even though Kaan has 1500+ tracks.

### Pitfall 6: Headphone device-index settings collision with existing settings keys

**What goes wrong:** The `learn.headphone_device_index` settings key conflicts with `mascot.*` or `recording.*` namespace conventions, or the `additionalProperties: false` ajv validator rejects it.

**Why it happens:** Schema-additive changes need codegen:ipc + schema namespace check.

**How to avoid:** Use `learn.` prefix (consistent with `learn.*` IPC namespace). Run `cd tauri/ui && npm run codegen:ipc` IMMEDIATELY after schema edit. Add `tests/ipc/test_settings_set_envelope_learn_field.py` to pin the field shape.

**Warning signs:** Settings drawer drops the field silently when persisting; or codegen-regenerated `validator.generated.mjs` rejects the envelope.

### Pitfall 7: `compute_band_shares` slow on ingest (8000+ FFT calls per track if windowed naively)

**What goes wrong:** The kick-correlation per-window FFT (Pattern 3) walks 250+ windows per track at 1024-sample FFT. For a 1500-track library, that's ~375k FFTs — minutes of ingest time.

**Why it happens:** Two FFT passes per track (the snapshot_features one + the per-window kick-correlation one).

**How to avoid:** Profile first. If slow, vectorize the kick-correlation per-window FFT using `scipy.signal.stft` or `np.fft.rfft` over a reshaped matrix in ONE call instead of a Python loop. KAAN-ACTION `§EXEMPLAR-INGEST-PERF` rides forward if measured ingest time on Kaan's library exceeds 30 min.

**Warning signs:** Kaan reports "the ingest got way slower."

## Runtime State Inventory

> N/A — greenfield-additive phase (new module + new asset bundle). No rename/refactor.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `numpy` | Band-share math, kick-correlation | ✓ | already pinned | — |
| `sounddevice` | ExemplarPlayer stream | ✓ | ^0.5.5 already pinned | — |
| `av` (PyAV) | Stereo decode | ✓ | already pinned via `[ai-local]` extra | — |
| `sqlite3` (stdlib) | Side-car `band_shares` table | ✓ | Python 3.12 stdlib | — |
| `sqlite-vec` | Shared `library-clap.db` access | ✓ | already pinned | — |
| Audio output device (system default OR user-picked) | ExemplarPlayer playback target | ✓ on macOS via CoreAudio | — | system default if none selected |
| BlackHole 2ch | NOT required for exemplar — exemplar plays to headphones, not BlackHole | — | — | — |

**All dependencies available — no install steps required.**

## Validation Architecture

> Required (workflow.nyquist_validation absent → defaults enabled per planning/config.json line check).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python) + vitest (TS, not used in P93 — engine has no UI) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `PYTHONPATH=src python3 -m pytest -q tests/learn/test_exemplar_*.py tests/learn/test_band_share_store.py` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEMPLAR-01 | `ExemplarFinder.find(band)` returns top-K from band_shares table | unit | `pytest tests/learn/test_exemplar_finder.py -x` | ❌ Wave 0 |
| EXEMPLAR-01 | `compute_band_shares(path)` returns 5-key dict for a synthetic track | unit | `pytest tests/learn/test_compute_band_shares.py -x` | ❌ Wave 0 |
| EXEMPLAR-01 | `band_share_store.upsert + top_for_band` roundtrip | unit | `pytest tests/learn/test_band_share_store.py -x` | ❌ Wave 0 |
| EXEMPLAR-02 | Pearson r > 0.8 → exclude from top_for_band results | unit | `pytest tests/learn/test_exemplar_kick_guard.py -x` | ❌ Wave 0 |
| EXEMPLAR-02 | `_kick_correlation` returns ≈0 for clean sub-only kick | unit | `pytest tests/learn/test_exemplar_kick_guard.py::test_clean_sub_kick_no_mid_passes_guard -x` | ❌ Wave 0 |
| EXEMPLAR-02 | `_kick_correlation` returns >0.8 for distorted (compressed) kick | unit | `pytest tests/learn/test_exemplar_kick_guard.py::test_distorted_kick_fires_guard -x` | ❌ Wave 0 |
| EXEMPLAR-03 | Empty library → packaged-bank fallback with honest-null reason | unit | `pytest tests/learn/test_exemplar_packaged_fallback.py -x` | ❌ Wave 0 |
| EXEMPLAR-03 | All 4 band subdirs + MANIFEST.json present in packaged bank | integration | `pytest tests/learn/test_exemplar_packaged_fallback.py::test_packaged_bank_directory_layout -x` | ❌ Wave 0 |
| EXEMPLAR-03 | Every MANIFEST entry has corresponding NOTICE.md attribution | integration | `pytest tests/learn/test_exemplar_packaged_fallback.py::test_manifest_attribution_present_in_notice -x` | ❌ Wave 0 |
| EXEMPLAR-04 | `ExemplarPlayer.play()` opens own `sd.OutputStream` on configured device | unit (mocked sd) | `pytest tests/learn/test_exemplar_player.py -x` | ❌ Wave 0 |
| EXEMPLAR-04 | `_choose_gain_db` returns -12 default, -18 when master_rms > 0.5 | unit | `pytest tests/learn/test_exemplar_player.py::test_choose_gain_db -x` | ❌ Wave 0 |
| EXEMPLAR-04 | `load_audio_stereo` returns (N, 2) float32 at native sr | unit | `pytest tests/learn/test_load_audio_stereo.py -x` | ❌ Wave 0 |
| EXEMPLAR-04 | `learn.headphone_device_index` settings key persists through `ipc.settings.set` | integration | `pytest tests/ipc/test_settings_set_envelope_learn_field.py -x` | ❌ Wave 0 |
| EXEMPLAR-05 | EVIDENCE_SOURCES frozenset contains "exemplar" | unit | `pytest tests/learn/test_exemplar_citation_schema_mirror.py::test_site_1_evidence_sources_frozenset_contains_exemplar -x` | ❌ Wave 0 |
| EXEMPLAR-05 | _SOURCE_ALT regex includes "exemplar" | unit | `pytest tests/learn/test_exemplar_citation_schema_mirror.py::test_site_2_source_alt_regex_includes_exemplar -x` | ❌ Wave 0 |
| EXEMPLAR-05 | CITATION_GRAMMAR_BLOCK includes "[exemplar:" | unit | `pytest tests/learn/test_exemplar_citation_schema_mirror.py::test_site_3_citation_grammar_block_includes_exemplar -x` | ❌ Wave 0 |
| EXEMPLAR-05 | _build_citation_strip allow-list includes "exemplar" | static-grep | `pytest tests/learn/test_exemplar_citation_schema_mirror.py::test_site_4_citation_strip_allow_list_includes_exemplar -x` | ❌ Wave 0 |
| EXEMPLAR-05 | Fabricated [exemplar:bogus] not grounded; real cite resolves | integration | `pytest tests/learn/test_exemplar_grounding_e2e.py -x` | ❌ Wave 0 |
| EXEMPLAR-05 | EVIDENCE_SOURCES × CITATION_GRAMMAR_BLOCK lock-step holds for all 10 sources | unit | `pytest tests/prompts/test_matrix.py -x` | ✓ (existing — extends to 10) |
| (cross) | `vibemix learn exemplar low` CLI returns a real or fallback pick + exits 0 | integration | `pytest tests/learn/test_cli_learn_exemplar.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `PYTHONPATH=src python3 -m pytest -q tests/learn/test_exemplar_*.py` (~3 sec for unit slice)
- **Per wave merge:** `PYTHONPATH=src python3 -m pytest -q tests/learn/ tests/state/ tests/prompts/ tests/agent/` (~10 sec)
- **Phase gate:** Full suite green before `/gsd:verify-work` — `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (~30 sec)

### Wave 0 Gaps

- [ ] `tests/learn/test_exemplar_finder.py` — covers EXEMPLAR-01 (top-K + tie-break determinism)
- [ ] `tests/learn/test_compute_band_shares.py` — covers EXEMPLAR-01 (5-key dict from synthetic track audio)
- [ ] `tests/learn/test_band_share_store.py` — covers EXEMPLAR-01 (upsert + top_for_band roundtrip)
- [ ] `tests/learn/test_exemplar_kick_guard.py` — covers EXEMPLAR-02 (3 sub-tests: clean, distorted, balanced)
- [ ] `tests/learn/test_exemplar_packaged_fallback.py` — covers EXEMPLAR-03 (3 sub-tests: layout, attribution, fallback path)
- [ ] `tests/learn/test_exemplar_player.py` — covers EXEMPLAR-04 (mock `sd.OutputStream`)
- [ ] `tests/learn/test_load_audio_stereo.py` — covers EXEMPLAR-04 (PyAV stereo decode)
- [ ] `tests/learn/test_exemplar_citation_schema_mirror.py` — covers EXEMPLAR-05 (4-site lock + lockstep)
- [ ] `tests/learn/test_exemplar_grounding_e2e.py` — covers EXEMPLAR-05 (Invariant #2 binding)
- [ ] `tests/learn/test_cli_learn_exemplar.py` — covers cross-cutting CLI
- [ ] `tests/ipc/test_settings_set_envelope_learn_field.py` — covers EXEMPLAR-04 (settings persistence)

*(Existing tests `tests/state/test_evidence_registry.py::test_evidence_11_sources_constant_locked_GROUND02` and `tests/prompts/test_matrix.py::test_prompt_R_evidence_sources_in_grammar_block_lockstep` are EXTENDED to cover 10 sources — the lockstep test loops over EVIDENCE_SOURCES so it auto-covers `exemplar` once site 1 lands.)*

## Security Domain

> Per project config: `security_enforcement` defaults enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — no auth surface in P93 |
| V3 Session Management | no | N/A |
| V4 Access Control | no | N/A — exemplar engine is read-only over local DB |
| V5 Input Validation | yes | `band` CLI arg validated against the 4-element set; `track_id` lookups parameterized via sqlite `?` placeholders (existing pattern in `band_share_store.py::top_for_band`) |
| V6 Cryptography | no | N/A — no crypto in P93 |

### Known Threat Patterns for vibemix/learn

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| sqlite injection via `band` arg | Tampering | `band` allow-list check before SQL; bind via parameter, not f-string interpolation. `top_for_band` raises ValueError on unknown band. |
| Path traversal via CLI `<track_id>` | Tampering | `_resolve_library_path` looks up via `RekordboxLibrary.tracks` dict — no filesystem walk on user-controlled input. ExemplarPlayer only opens paths the library / packaged bank knows about. |
| Audio decoder DoS (zip-bomb-style malformed file) | Denial of Service | PyAV's `av.open` has a configurable timeout; the existing `library/audio_decode.py` has not exhibited DoS issues across the 1500-file library; if `compute_band_shares` is invoked on a malicious file, the outer ingest loop already catches all exceptions and skips (existing pattern at `folder_ingest.py:357-362`). |
| CC-BY license violation | Compliance | CI gate `test_manifest_attribution_present_in_notice` blocks merge if MANIFEST entries lack `NOTICE.md` lines. |
| Prompt injection via fabricated `[exemplar:<id>]` | Tampering / Misinformation | 4-site mirror + CitationLinter strip-whole-turn-on-unresolved (existing Phase 20 gate). The cite must resolve to a real `EvidenceRegistry.write("exemplar", ...)` write — fabricated track_ids strip the turn. |
| Headphone playback to wrong device (privacy: leaks music to speakers) | Information Disclosure | `learn.headphone_device_index` defaults to None (system default); user explicitly picks via P97 wizard. The packaged bank tracks are CC-BY (no privacy leak) but library tracks may be DRM-acquired — never log file paths in ipc envelopes outside the local sidecar. |

## Assumptions Log

> All claims tagged `[ASSUMED]` in this research need user confirmation before locking.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The single full-track FFT in `snapshot_features(buf, seconds=track_duration)` yields meaningful band-shares for tracks 3-7 min long | Pattern 2 | If FFT resolution is wrong at long windows, band-shares may underweight transients. **Mitigation:** profile-and-fix during execution; can switch to per-chunk averaging if needed. |
| A2 | Pearson r > 0.8 is the correct compressed-kick threshold | Pattern 3 | Could be too aggressive (excludes legit tracks) or too lax (lets compressed kicks through). **Mitigation:** Constant is one-line tunable; KAAN-ACTION `§EXEMPLAR-KICK-GUARD-EAR`. |
| A3 | 4 packaged CC-BY tracks total (1/band) is enough for the v9.0 ship | Standard Stack §discretion | If 1 track per band feels too thin to Kaan, scaling to 4/band is a content-only follow-on (no code change). |
| A4 | Hatchling's default include catches `src/vibemix/learn/assets/band_exemplars/*.mp3` | Pattern 5 | If the wheel doesn't include the assets, the bundled installer ships without the bank — fallback path returns empty. **Mitigation:** `uv build` + `unzip -l dist/*.whl \| grep band_exemplars` verification step in the plan. |
| A5 | `load_audio_stereo` via PyAV produces correctly-channelized stereo for mono input files | Pattern 7 | Mono → stereo upmix is a small detail; if `AudioResampler(layout="stereo")` doesn't duplicate, the resulting stream is silent on one channel. **Mitigation:** test on a mono fixture in `test_load_audio_stereo.py`. |
| A6 | The existing `ipc.settings.set` envelope accepts arbitrary `learn.*`-prefixed keys via `additionalProperties` on a sub-property | Pattern 8 | The settings envelope schema may need explicit per-key definitions. **Mitigation:** check `messages.schema.json` SettingsSetPayload definition; if strict, extend with explicit `learn.headphone_device_index` property. |
| A7 | The single-DB side-car table strategy survives the `recreate_table()` dim-mismatch wipe at `index_sqlite_vec.py:145-160` | Pattern 4 | If `recreate_table` drops the whole DB (not just `vec_library`), the `band_shares` table goes with it. **Mitigation:** verify in implementation that the wipe is table-scoped, not DB-scoped (the existing code does `DROP TABLE IF EXISTS vec_library` which is table-scoped — confirmed). |

## Open Questions

1. **`compute_band_shares` opt-in default — on or off at folder_ingest level?**
   - What we know: P93 wants band-shares populated for the exemplar engine to work.
   - What's unclear: Should the default `vibemix library ingest` CLI also populate band-shares, or only the v9.0 wizard?
   - Recommendation: **Default ON** — the FFT cost is small (1 extra FFT per track), and band-shares are useful for future v9.x lessons too. KAAN-ACTION `§EXEMPLAR-INGEST-PERF` only if measured cost > 30 min on Kaan's library.

2. **Where do the CC-BY tracks come from?**
   - What we know: 1-4 tracks per band, ≤60s each, instrumental, no vocals, ~3-5 MB total.
   - What's unclear: Source archive (Free Music Archive? ccMixter? Wikimedia? Kaan / Francesco's own production?). 
   - Recommendation: **Defer to KAAN-ACTION** `§EXEMPLAR-BANK-SOURCING`. Engineering ships the engine with empty bank dirs; Kaan / Francesco populate during P97 / P98 ear-pass. The honest-null fallback path is the v0.1 surface; once tracks land, manifest + notice gates auto-validate.

3. **Active-session guard wiring in P93 vs P96?**
   - What we know: CONTEXT.md says P93 lands "the gate scaffolding" — the `can_play()` method returns True by default. P96 implements the real check.
   - What's unclear: Does P93 need to wire `MusicState` into `ExemplarPlayer.__init__` for the future state-read, or is it a Plan-level scaffold-only?
   - Recommendation: P93 wires the `state: MusicState` kwarg (Example 6 / Pattern 6) — adds a dependency that P96 just needs to read, no constructor change later.

4. **Should the exemplar registration use `t_session=0.0` (library-load semantics, like `[track:]`) or `t_session=time.time()` (live timestamp)?**
   - What we know: `[track:]` uses `t_session=0.0` per `evidence_registry.py::register_library` (line 293).
   - What's unclear: Whether the linter's mode-aware tolerance (`tol=1.0` live / `tol=2.0` debrief) gates exemplar cites or treats them as existence-only.
   - Recommendation: Follow the `[recall:]` precedent — `t_session=time.time()` at write site; the linter treats `exemplar` as existence-only via absence from `_TIME_KEYED_SOURCES` (same path as `recall` / `key` / `track`). Confirm this during plan-write by re-reading `state/citation_linter.py::_TIME_KEYED_SOURCES`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| CLAP semantic cosine for "find me a sub-heavy track" | DSP-band ranker (FFT band-share scalars) | P93 (this phase) | CLAP is semantic ("uplifting trance") not spectral ("sub-heavy") — semantic-to-spectral query never produces reliable results. The DSP path is direct, deterministic, fast. |
| Single `PlaybackQueue` for all AI audio | Dedicated `sd.OutputStream` for tutor exemplars | P93 (this phase) | The mic-gating coupling makes `PlaybackQueue` AI-voice-specific; CC-BY music exemplars on a headphone device need their own stream. |
| 7 evidence sources (Phase 18) → 8 (Phase 59 `key`) → 9 (Phase 65 `recall`) → 10 (Phase 93 `exemplar`) | 10 sources via 4-site mirror | P93 (this phase) | Each new source rides the proven `[recall:]` 4-site pattern. |

**Deprecated/outdated:**
- "Use CLAP for everything similarity-related" — superseded by the DSP-band approach for band-specific lessons (CLAP stays the engine for the conversational similarity layer; it's NOT the exemplar engine).
- "Reuse `PlaybackQueue` for any audio output" — superseded; multiple `sd.OutputStream` instances (one per output device, with their own purpose) is the documented pattern (`open_voice_output` + `open_passthrough_output` already coexist).

## Sources

### Primary (HIGH confidence)
- `src/vibemix/state/evidence_registry.py:90-157` — EVIDENCE_SOURCES, _SOURCE_ALT, EVIDENCE_CITATION_RE, EBNF docstring (the 4-site source-of-truth)
- `src/vibemix/audio/features.py:27-90` — `snapshot_features` band-share computation (verbatim port from v4)
- `src/vibemix/audio/buffers.py:170-230` — `MicBuffer._current_gain` mic-gating (why PlaybackQueue is wrong for exemplars)
- `src/vibemix/platform/_audio_macos.py:298-326` — `open_passthrough_output` (the ExemplarPlayer precedent)
- `src/vibemix/library/index_sqlite_vec.py:1-174` — sqlite-vec store; vec0 ALTER TABLE limitation documented at lines 122-127
- `src/vibemix/library/embed_cache.py:1-34` — side-car SQL table pattern (raw sqlite3 inside library cache)
- `src/vibemix/library/folder_ingest.py:336-374` — the additive ingest extension point
- `src/vibemix/library/audio_decode.py:45-65` — `load_audio_mono` (PyAV pattern for stereo extension)
- `src/vibemix/library/clap_engine.py:1-456` — CLAP ingest path (extends additively)
- `src/vibemix/prompts/matrix.py:93-148` — `CITATION_GRAMMAR_BLOCK` (site 3 of the mirror)
- `src/vibemix/agent/dj_cohost.py:140-305` — `_build_citation_strip` (site 4 of the mirror) + RECALL_CALLBACK_COOLDOWN_S precedent
- `src/vibemix/__main__.py:3283-3330` — `cli_entry` learn subcommand dispatch
- `src/vibemix/learn/` — existing P91/P92 modules (`midi_mirror.py`, `runtime.py`, `progress.py`, `prompts.py`, etc.)
- Git history — v6 `[recall:]` 4-site commits: `2016e36b` (sites 1+2 atomic), `977c0140` (site 3), `0bfc8bd0` (site 4)
- `tests/state/test_evidence_registry.py:200-300` — existing schema-mirror lock test (extends to 10 sources)
- `tests/prompts/test_matrix.py:434-525` — `test_prompt_R_evidence_sources_in_grammar_block_lockstep` (auto-extends)
- `tests/agent/test_dj_cohost_linter.py:240-380` — `test_fabricated_recall_strips_turn` (the grounding e2e pattern)
- `.planning/phases/91-controller-renderer-midi-mirror/91-RESEARCH.md` — P91 RESEARCH (precedent for learn-package module shape)
- `.planning/phases/92-lesson-runtime-ai-highlight-contract/92-RESEARCH.md` — P92 RESEARCH (precedent for FSM + IPC envelope patterns)
- `.planning/research/SUMMARY.md` §7 (4-site mirror) + §8 (audio routing) — v9.0 locked decisions

### Secondary (MEDIUM confidence)
- `pyproject.toml:208-217` — Hatchling default-include behavior for non-Python files
- `src/vibemix/runtime/config_store.py` — settings persistence pattern for `learn.headphone_device_index` (read referenced; full file not opened — see Open Q 4 for verification step)

### Tertiary (LOW confidence)
- CC-BY-4.0 attribution requirements — guidance based on standard Creative Commons attribution practice; legal review by `§LEARN-LEGAL-DISCLAIMER` KAAN-ACTION (Francesco/lawyer P98 sight-check) covers the bank attribution too.

## Metadata

**Confidence breakdown:**
- 4-site mirror: HIGH — verbatim v6 precedent commits in tree, exact line numbers verified.
- DSP band-share engine: HIGH — extends existing `snapshot_features` primitive; reuses verbatim FFT math.
- Compressed-kick guard: MEDIUM — algorithm is standard Pearson correlation, threshold (0.8) is CONTEXT-locked but Kaan-ear-pass tunable.
- ExemplarPlayer audio routing: HIGH — verbatim mirror of `open_passthrough_output`; second `sd.OutputStream` is well-trodden.
- Side-car sqlite table: HIGH — same pattern as existing `library/embed_cache.py`; vec0 ALTER TABLE limitation documented.
- Honest-null fallback packaging: MEDIUM — hatchling include is verified by comment but `src/vibemix/learn/assets/` placement is a P93 decision (not yet shipped).
- Settings persistence: MEDIUM — `ipc.settings.set` extension pattern is standard but exact JSON-Schema shape needs verification at plan-time.
- CLI subcommand: HIGH — mirrors `vibemix learn reset` precedent at the same `__main__.py:3316` site.

**Research date:** 2026-05-28
**Valid until:** 30 days (stable Python/sqlite-vec/CLAP/sounddevice stack; no fast-moving deps).
