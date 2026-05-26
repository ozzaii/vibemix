# Phase 82: CURATE — Unify Curator + Co-Host - Research

**Researched:** 2026-05-26
**Domain:** Shared-seam wiring (Python) — perception/state contract + taste/profile layer across two existing surfaces
**Confidence:** HIGH (all claims verified against live code at `file:line`; no external libs introduced)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **CURATE-01 — shared perception engine + structured-state contract:** the shared perception bridge is the Phase-78 `library/genre_prototypes.py` (mean-centered nearest-prototype over the cached library embeddings) + the library's per-track features (key/BPM/energy/vibe-embedding). It already serves the co-host's `detected_genre`; expose it as the ONE perception representation the curator's grounded core (`library/toolset.py`) also reads — so both surfaces share "what is true about this track", not two parallel notions. Define/affirm a small structured-state contract (the shared track-perception shape both conform to); reuse existing dataclasses where possible (don't invent a parallel one). The co-host can QUERY the library's taste representation; the curator can curate "for this DJ" by reading the same profile/perception. Concrete, additive — no new provider, no new port.
- **CURATE-02 — shared taste layer + persona/lens:** the taste layer = the long-term DJ `profile/` (the DJ profile) + the Phase-81 `TASTE_RUBRIC` seam. Both the curator and the co-host read the shared profile/taste — so "what this DJ likes / what clicked" is one source feeding both. The persona/lens is ALREADY shared (Phase 79: `build_lens_instruction` + `ConfigStore.extra["lens"]`, read by both `build_system_instruction` and `build_curator_instruction`). This phase confirms it reaches BOTH curator backends + the transports, and adds the profile/taste sharing on top.
- **Additive / invariants:** existing `library curate` + Telegram + `next_suggestion` (pill) surfaces keep working unchanged — pin with a regression test. No new ws port (invariant #4); no new IPC envelope; single-writer `MusicState` untouched (invariant #1); citation grounding holds (invariant #2). Both curator backends (gemini + codex) + transports reach the shared perception + taste + lens — neither orphaned (the CURATE acid test).

### Claude's Discretion
- The exact shared-contract module location + shape (reuse vs a thin shared interface over existing dataclasses), whether the co-host's library-taste query is a new helper or reuses an existing `library/` entrypoint, how the profile is surfaced to the curator — planner's call after research maps the real seams, smallest additive diff, ship-not-over-engineer.

### Deferred Ideas (OUT OF SCOPE)
- The felt "does it curate like it knows me" judgment → KAAN-ACTION live (parked).
- Acting on the Phase-81 bench verdict (winning arch/model) → KAAN-ACTION (Phase 81's gate).
- Set-prep / sequencing (the €4.99 Pro feature) → Future Requirements (after the engine is unified).
- Any new transport / surface → out (the unification reaches the EXISTING surfaces; no new ones).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CURATE-01 | Curator + co-host share the perception engine + structured-state contract (both read ONE "what is true about this track", not two parallel). Covers BOTH backends (gemini `agent.py` + codex `codex_curate.py`/`mcp_server.py`) + Telegram + `next_suggestion` transports — neither orphaned. | The shared bridge already exists physically: `library/genre_prototypes.py` (Phase 78) sits in `library/` and is consumed by the co-host. The curator's `get_track_features` (in `library/toolset.py`) currently returns `genre: None` (`toolset.py:124`). The smallest seam is to have `toolset.py` resolve the same prototype-based genre the co-host reads, so both surfaces derive genre from one mechanism. See **Concrete Seam #1**. |
| CURATE-02 | Curator (both backends) + co-host share the taste layer + persona/lens. | **Persona/lens half is DONE** (Phase 79 — both curator backends + transports already read `ConfigStore.extra["lens"]` via `read_shared_lens`). **Taste/profile half is the genuine gap:** `profile/` is imported ONLY by the co-host (`__main__.py`, `session_loop.py`, `wizard.py`) — zero curator imports. Smallest seam: the curator lazy-reads `profile/` to bias curation; the Phase-81 `TASTE_RUBRIC` is a fixed constant in `bench/matrix.py`. See **Concrete Seam #2**. |
</phase_requirements>

## Summary

This is a **wiring phase, not a build phase.** The two surfaces (live co-host + library/Viber curator) already physically share their home directory for the perception primitive — `library/genre_prototypes.py` and the 1536-dim embedding store both live under `library/`, the curator's own package. After Phases 77-81, **more is already shared than the charter's connection-map (2026-05-25) reflects**, because that map predated the lens unification.

**What is ALREADY shared (verified, do NOT re-do):**
1. **Persona/lens — fully shared.** Both curator backends read the ONE `ConfigStore.extra["lens"]` selection via `read_shared_lens` (`settings.py:68`), lazily importing `prompts.matrix.build_curator_instruction` (gemini: `agent.py:114,145`; codex: `codex_curate.py:95,123`). Flipping the lens in settings drives co-host AND both curator backends AND the Telegram transport (which routes through `ViberAgent`). The pill (`next_suggestion`) is pure DSP/cosine with no LLM voice — correctly lens-agnostic. **CURATE-02's persona half is DONE.**
2. **The embedding/genre mechanism physically lives in `library/`** — `genre_prototypes.py` (mean-centered nearest-prototype, €0) is already imported by the co-host's `state/refresh.py:254` (via `GenrePrototypeLookup.classify_playing`) and `state/genre/genre_reconcile.py:31`. The co-host already reads the curator's brain for genre.

**What genuinely remains (the two real seams):**
1. **CURATE-01 — perception parity:** The curator's `get_track_features` returns `genre: None` (`toolset.py:124`) — it does NOT use the same prototype-genre the co-host reads. The smallest fix makes `toolset.py` resolve genre from `genre_prototypes` so both surfaces derive "what genre is this track" from ONE mechanism. The co-host already queries the library (genre via prototypes; track-id via `library/grounding.py`); the missing direction is the curator reading the same perception.
2. **CURATE-02 — taste/profile sharing:** `profile/` is co-host-only (grep-confirmed: zero curator imports). The smallest fix lets the curator lazy-read `load_profile()` to bias curation ("for this DJ") — and surfaces the same profile-derived taste the co-host already injects into its cache (`__main__.py:852`).

**Primary recommendation:** Ship two thin, additive seams — (a) `library/toolset.py.get_track_features` resolves genre via `genre_prototypes` (the ONE perception representation both surfaces read), and (b) the curator lazy-reads `profile/` (the ONE taste layer both surfaces read). Both seams reach BOTH curator backends because they live in the shared `toolset.py` / `ViberAgent` core. Pin everything with a regression test that asserts both surfaces import the one module and the existing curate/Telegram/pill surfaces still work. **Resist any "perception contract" dataclass invention — the existing functions ARE the contract.**

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Genre perception (prototype cosine) | `library/genre_prototypes.py` | co-host `state/refresh.py` reads it | €0 mechanism already lives in the curator's package; co-host already a consumer |
| Per-track features (key/BPM/energy) | `library/toolset.py` + `library/rekordbox.py` | — | deterministic facts; Camelot via `state.harmonics` (never LLM) |
| Live "what's playing" state | `state/music_state.py` `MusicState` | single-writer `state/refresh.py` | co-host-only by invariant #1; NOT a curator concern |
| Taste/profile (long-term tendencies) | `profile/` | co-host cache (`__main__.py`), curator (NEW) | allowlisted 2KB JSON; currently co-host-only |
| Persona/lens (hype/critique/tutor) | `prompts/matrix.py` | `runtime/settings.read_shared_lens` | ALREADY shared across both surfaces (Phase 79) |
| Taste rubric (Kaan's reward signal) | `bench/matrix.py` `TASTE_RUBRIC` | — | fixed module constant (Phase 81); a string seam, not state |

**Tier note for the planner:** `MusicState` is the LIVE co-host's perception object and stays single-writer (invariant #1) — the curator must NOT read or write it. The shared perception bridge is the LIBRARY-side representation (`genre_prototypes` + `toolset` features), which both surfaces can read because it lives in `library/` and is derived from the offline embedding store, not from live audio. This is the correct seam: shared = the offline/library representation; not-shared = the live `MusicState`.

## Standard Stack

**No new packages.** This phase introduces ZERO dependencies. Everything is already in `pyproject.toml`:

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `numpy` | (pinned) | prototype cosine math (already used by `genre_prototypes`) | the existing DSP/embedding math layer |
| `google-genai` | (pinned) | sole AI provider (curator backends) | Gemini-only constraint |
| `jsonschema` | (pinned) | `profile/` schema validation (already used) | profile allowlist gate |

**Installation:** None. (Verification step skipped — no packages added. The Package Legitimacy Audit below documents this explicitly.)

## Package Legitimacy Audit

> This phase installs **NO** external packages. It is pure internal wiring across modules already in the tree.

| Package | Registry | Disposition |
|---------|----------|-------------|
| (none) | — | No new packages — phase adds no `pyproject.toml` entries |

**Packages removed due to slopcheck [SLOP] verdict:** none (no packages evaluated)
**Packages flagged as suspicious [SUS]:** none

slopcheck not run because the phase introduces no third-party packages. If the planner discovers a need for a new library during planning, run the Package Legitimacy Gate then.

## Architecture Patterns

### System Architecture Diagram

```
                        ┌─────────────────────────────────────┐
                        │   ConfigStore.extra["lens"]          │  ← ONE shared lens
                        │   (read_shared_lens, settings.py:68) │     (Phase 79 — DONE)
                        └───────────────┬─────────────────────┘
                                        │ both surfaces read
              ┌─────────────────────────┼──────────────────────────┐
              │                         │                          │
        LIVE CO-HOST              CURATOR (Viber)              CURATOR transports
        (state/, agent/)          (library/toolset.py)         (Telegram → ViberAgent,
              │                    ├── gemini: agent.py          pill → next_suggestion DSP)
              │                    └── codex:  codex_curate.py
              │                              + mcp_server.py
              │                         │
   reads ─────┤                         ├───── reads (NEW seam #1)
              ▼                         ▼
     ┌──────────────────────────────────────────────┐
     │   library/genre_prototypes.py  (Phase 78)     │  ← ONE perception representation
     │   mean-centered nearest-prototype genre, €0   │     (co-host ✓ ; curator: NEW)
     │   + library/ per-track features (key/bpm/emb) │
     └──────────────────────────────────────────────┘
              ▲                         ▲
   reads ─────┤                         ├───── reads (NEW seam #2)
   (__main__: │                         │
    cache     │                         │
    inject)   ▼                         ▼
     ┌──────────────────────────────────────────────┐
     │   profile/  (load_profile → ~2KB allowlist)   │  ← ONE taste layer
     │   + bench/matrix.py TASTE_RUBRIC (Phase 81)   │     (co-host ✓ ; curator: NEW)
     └──────────────────────────────────────────────┘

  ─── DO NOT BRIDGE: state/music_state.py MusicState stays single-writer (inv #1).
      The shared perception is the LIBRARY representation, never the live state object.
```

### Recommended Project Structure (touched files — additive only)

```
src/vibemix/
├── library/
│   ├── toolset.py          # SEAM #1 + #2: get_track_features resolves genre via
│   │                       #   genre_prototypes; constructor/handler reads profile taste
│   ├── genre_prototypes.py # UNCHANGED — already the shared perception mechanism
│   ├── agent.py            # construction site of LibraryToolset (agent.py:320)
│   └── mcp_server.py       # construction site of LibraryToolset (mcp_server.py:107)
├── profile/                # UNCHANGED — load_profile() lazy-imported by the curator
└── prompts/matrix.py       # UNCHANGED — lens seam already shared (Phase 79)
```

### Pattern 1: Lazy-import the shared seam (the established import-boundary discipline)

**What:** When `library/` code reaches into `prompts/`, `profile/`, or any heavier module, import LAZILY inside the function, never at module top-level.
**When to use:** every new cross-package read added in this phase.
**Why:** `tests/memory/test_no_live_path_import.py` forbids `vibemix.prompts` / `vibemix.agent` / the live path from leaking into `sys.modules` via the memory storage spine — and the same test documents a historical runtime leak (`library/__init__` → `library.toolset` → `vibemix.state` eagerly importing `state.coach`/`state.refresh`). The lens seam already follows this exactly:

```python
# Source: src/vibemix/library/agent.py:128-134 (the established pattern)
def _shared_lens() -> str:
    try:
        from vibemix.runtime.config_store import load_config
        from vibemix.runtime.settings import read_shared_lens
        return read_shared_lens(load_config(), default="tutor") or "tutor"
    except Exception:  # guard: any read fail = cold default
        return "tutor"
```

The NEW profile read MUST mirror this: lazy import + a guarded fallback (no profile / consent-off → cold-path-identical behaviour).

### Pattern 2: Per-surface default-when-unset (byte-identical cold path)

**What:** A shared read returns a per-surface default when the shared value is unset, so each surface's pre-wire behaviour is byte-identical.
**When to use:** the profile/taste read — when no profile exists (consent default-OFF, `profile/__init__.py`), the curator must behave EXACTLY as today (`genre: None`, no taste bias).
**Example:** `read_shared_lens(store, default="tutor")` (`settings.py:68-91`) — curator passes `default="tutor"`, co-host passes `default=None`. Mirror this for taste: absent profile → no-op.

### Pattern 3: The grounding gate is sacred (invariant #2)

**What:** Any new field the curator surfaces (e.g. genre) must NOT widen the seen-set grounding gate or let the model invent track facts.
**When to use:** seam #1 — adding genre to `get_track_features`.
**Why:** `toolset.py:108-125` returns deterministic facts only; the seen-set gate (`toolset.py:134-147`) and library re-validation (`create_playlist`) are the anti-hallucination spine. Genre derived from `genre_prototypes` is a deterministic library-side fact (not LLM-computed) — same class as the existing Camelot-via-`harmonics` fact. Keep it that way; never let the model supply genre.

### Anti-Patterns to Avoid

- **Inventing a "PerceptionContract" dataclass.** The CONTEXT explicitly says "reuse the existing dataclasses where possible (don't invent a parallel one)." The existing functions (`genre_prototypes.classify`, `toolset.get_track_features`, `next_suggestion.NextSuggestion`) ARE the contract. A new abstract interface is over-engineering and will fail the ship-not-over-engineer bar.
- **Reading `MusicState` from the curator.** Breaks the tier boundary and risks invariant #1. The shared perception is the LIBRARY representation, not the live state object.
- **Eager top-level import** of `prompts`/`profile` from `library/` — trips the import-boundary gate (Pattern 1).
- **Embedding the profile in the per-turn curator prompt as raw JSON.** The co-host puts profile in the CACHE body, never per-turn (Pitfall P60, `profile/__init__.py:6`). The curator is single-shot (no cache), so a compact profile hint in the system instruction is acceptable — but use the `render_profile_for_cache` compact-prose form (`cache_render.py:33`), never raw JSON, and never track titles (P51 — the schema already forbids them).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Genre for a track | a curator-side genre classifier | `library/genre_prototypes.py` `classify` / `GenrePrototypeLookup` | the co-host already uses it; one mechanism = CURATE-01 |
| Camelot key | LLM/curator key math | `state.harmonics.to_camelot` (already in `toolset.py:116`) | deterministic, invariant #2 |
| Profile read | a new curator profile loader | `profile.load_profile()` + `render_profile_for_cache` | allowlisted, privacy-gated, consent-aware |
| Lens resolution | a curator lens read | `runtime.settings.read_shared_lens` (already wired) | ALREADY shared — don't touch |
| Taste rubric text | a new rubric string | `bench/matrix.py` `TASTE_RUBRIC` (Phase 81) | Kaan-authored fixed constant |

**Key insight:** The genuine work is two ~10-line reads, not new subsystems. Every primitive already exists; this phase connects them and proves the connection with a regression.

## Runtime State Inventory

> Not a rename/refactor phase. This is additive wiring; no stored data, OS-registered state, secrets, or build artifacts carry a string that changes.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — the shared reads consume EXISTING stores (`library.db`, `profile.json`); no schema/key change | None |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None — `GEMINI_API_KEY` unchanged; lens/profile are config files, not new env vars | None |
| Build artifacts | None | None |

**Nothing found in any category — verified:** the phase reads existing artifacts through existing loaders; it adds code paths, not state.

## Common Pitfalls

### Pitfall 1: Re-doing the lens unification
**What goes wrong:** Treating CURATE-02 as "make persona shared" — but the connection-map (Missing Wire #3) was written 2026-05-25, BEFORE Phase 79 shipped the lens seam.
**Why it happens:** the charter/connection-map predates the lens work; the docs lag the code.
**How to avoid:** the persona half is DONE (`agent.py:145`, `codex_curate.py:123` both call `build_curator_instruction`). Only the TASTE/profile half is new. Verify by `grep build_curator_instruction src/vibemix/library/` before planning any persona work.
**Warning signs:** a plan task that adds `build_lens_instruction` to a curator backend — that's already there.

### Pitfall 2: Centroid divergence in genre classify
**What goes wrong:** If the curator computes genre with a different centroid than the prototypes were built with, the cosine is garbage.
**Why it happens:** `genre_prototypes` centers BOTH prototype-build and classify with the SAME corpus centroid (`genre_prototypes.py:121,166`). A naive re-implementation breaks this.
**How to avoid:** call `load_or_build_prototypes(store)` / `classify(emb, protos, labels, centroid)` exactly as the co-host does — don't re-roll centering. The `GenrePrototypeLookup` holder (`genre_prototypes.py:241`) already encapsulates this; the curator can reuse `classify` directly on a track's cached embedding (`_cached_embedding`, `genre_prototypes.py:299`).
**Warning signs:** a new `np.mean`/`cosine` call in `toolset.py` instead of a `genre_prototypes` call.

### Pitfall 3: Import-boundary regression
**What goes wrong:** adding `from vibemix.profile import load_profile` at the top of `toolset.py`/`agent.py` could trip the no-live-path import test (and the documented `library/__init__` eager-import leak).
**Why it happens:** `library/__init__.py` has NO lazy `__getattr__` (it eagerly imports `toolset`), so a top-level profile import in `toolset.py` becomes import-time.
**How to avoid:** lazy-import inside the function (Pattern 1). `profile/` itself does not import the live path, but keep the discipline consistent and run `tests/memory/test_no_live_path_import.py` in the validation loop.
**Warning signs:** the no-live-path test goes red, or `sys.modules` after `import vibemix.library.toolset` contains `vibemix.prompts`/`vibemix.agent`.

### Pitfall 4: Consent / privacy on the profile read
**What goes wrong:** the curator reads profile fields that don't exist or leaks track titles.
**Why it happens:** profile is consent-default-OFF and allowlisted to 5 fields (no titles, `schema.py`).
**How to avoid:** `load_profile()` returns `None` when absent/invalid/consent-off — handle `None` as the cold path (no taste bias). Only ever use the allowlisted fields (`preferred_genre`, `tempo_preference_bin`, `mix_style_tags`, …); the schema guarantees no titles exist to leak.
**Warning signs:** a `KeyError` on a missing profile field, or any free-form string in the curator prompt derived from profile.

## Code Examples

### Concrete Seam #1 — curator reads the ONE perception representation (CURATE-01)

The current curator feature surface (the gap):
```python
# Source: src/vibemix/library/toolset.py:108-125 (TODAY — genre is null)
def get_track_features(self, args):
    ...
    return {
        "track_id": entry.track_id, "title": entry.title, "artist": entry.artist,
        "bpm": entry.bpm if (entry.bpm and entry.bpm > 0) else None,
        "key": camelot,        # deterministic via harmonics.to_camelot
        "duration_s": entry.duration_s or None,
        "genre": None,         # <-- THE SEAM: library genre is best-effort null today
    }
```

The co-host already resolves genre from the shared mechanism:
```python
# Source: src/vibemix/library/genre_prototypes.py:309-335 (the shared mechanism)
def classify_playing(self, track_id):
    self._ensure_prototypes()
    emb = self._cached_embedding(track_id)   # €0 — read the cached library vector
    if emb is None: return ("unknown", 0.0)  # abstain, no live embed (invariant #3)
    return classify(emb, self._protos, self._labels, self._centroid)
```

**Smallest seam:** in `toolset.py`, fill `genre` by resolving the track's cached embedding through `genre_prototypes.classify` (or reuse a `GenrePrototypeLookup`-style read). Both surfaces now derive genre from ONE mechanism. Honest-null on abstain (`"unknown"`), exactly like the co-host. Lazy-import `genre_prototypes` to keep the import boundary clean (though `genre_prototypes` is already in `library/`, so this is low-risk).

### Concrete Seam #2 — curator reads the ONE taste layer (CURATE-02)

```python
# Pattern (NEW) — mirror the lens seam's lazy+guarded read (agent.py:128).
def _taste_hint() -> str:
    """Compact, privacy-safe profile hint biasing curation 'for this DJ'.
    Cold path (no/consent-off profile) → "" → byte-identical to today."""
    try:
        from vibemix.profile import load_profile, render_profile_for_cache
        return render_profile_for_cache(load_profile())  # "" when None
    except Exception:
        return ""
```
The curator system instruction (built from `build_curator_instruction(lens)`) appends `_taste_hint()` alongside the verbatim grounding RULES block — so the curator now curates "for this DJ" using the SAME `profile/` the co-host injects into its cache (`__main__.py:852`). The taste rubric (`bench/matrix.py TASTE_RUBRIC`, Phase 81) is a fixed string the planner can also surface here if Kaan wants the reward-signal language in-voice.

### Existing shared lens read (already done — for reference, do NOT modify)

```python
# Source: src/vibemix/runtime/settings.py:68-91 — the ONE shared-lens read
def read_shared_lens(store, default=None):
    lens = store.extra.get("lens")
    if isinstance(lens, str) and lens:
        return lens
    return default
```

## State of the Art

| Old (connection-map, 2026-05-25) | Current (verified 2026-05-26) | When Changed | Impact |
|----------------------------------|-------------------------------|--------------|--------|
| "No shared persona/lens layer; curator hardcodes its voice" | Lens fully shared via `read_shared_lens` + `build_curator_instruction` in BOTH backends | Phase 79 | CURATE-02 persona half DONE — don't re-do |
| "Embeddings orphaned for the co-host" | Co-host reads `genre_prototypes` (`refresh.py:254`); grounding wired | Phases 77-78 | the perception mechanism is already cross-surface — only the curator's `get_track_features` lags |
| "Profile is co-host-only" | STILL co-host-only (grep-confirmed) | unchanged | this is the genuine CURATE-02 work |

**Deprecated/outdated:**
- The connection-map's "Missing Wire #3 (persona)" is OBSOLETE — shipped in Phase 79.

## Assumptions Log

> All structural claims were verified against live code at `file:line`. The only ASSUMED items are forward-looking design choices left to the planner.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The smallest CURATE-01 seam is filling `get_track_features.genre` via `genre_prototypes` (vs a richer perception object) | Seam #1 | LOW — if Kaan wants more perception parity (energy/structure) the planner can extend the same seam; the genre fill is the minimal proof |
| A2 | A compact profile hint in the curator's single-shot system instruction (not a cache) is the right taste injection | Seam #2 | LOW — curator is single-shot so no cache exists; `render_profile_for_cache` prose form is the privacy-safe vehicle either way |
| A3 | `TASTE_RUBRIC` surfacing into the curator voice is optional (planner/Kaan call) | Seam #2 | LOW — it's a fixed string; including or omitting it doesn't affect grounding |

**Note:** the felt "does it curate like it knows me" judgment is a parked KAAN-ACTION (per CONTEXT) — not an engineering assumption.

## Open Questions

1. **Does CURATE-01 need MORE than genre parity?**
   - What we know: the CONTEXT names "key/BPM/energy/vibe-embedding" as the shared per-track features; key+BPM are ALREADY in `get_track_features`, embedding drives search, only genre is null.
   - What's unclear: whether Kaan wants energy/structure also surfaced to the curator.
   - Recommendation: ship genre parity as the CURATE-01 proof (it's the one currently-null field and the one the co-host most visibly uses); leave energy/structure as a trivial follow-up extension of the same seam if desired. Ship-not-over-engineer.

2. **Should the co-host gain a NEW "query the library's taste" entrypoint, or is reading the shared `profile/` sufficient?**
   - What we know: the co-host already QUERIES the library for genre (`genre_prototypes`) and track-id (`grounding.py`). It reads `profile/` for its cache.
   - What's unclear: the CONTEXT mentions "the co-host can lean on what the DJ's library says about their taste" — `profile.preferred_genre` is already library/session-derived and co-host-read.
   - Recommendation: the co-host side of CURATE-01/02 is largely already satisfied (it reads both the perception mechanism AND the profile). The genuine NEW direction is the CURATOR reading them. Verify there's no co-host gap during planning; if not, the co-host needs no new code — only the regression that pins the shared reads.

## Environment Availability

> Pure code/config changes within existing modules. No new external dependencies.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `library.db` (embedding store) | genre_prototypes / curator | ✓ (existing) | — | abstain → `genre: "unknown"` (already the no-store path) |
| `profile.json` | taste seam | optional (consent-OFF default) | — | `load_profile()` → `None` → cold path (no taste bias) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** profile is intentionally optional — absent profile = byte-identical-to-today curator behaviour.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (configured in `pyproject.toml` `[tool.pytest.ini_options]`) |
| Config file | `pyproject.toml` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/library/ tests/profile/ tests/memory/test_no_live_path_import.py` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CURATE-01 | `get_track_features` returns a genre derived from `genre_prototypes` (same mechanism the co-host reads), honest-`"unknown"` on abstain | unit | `pytest tests/library/test_toolset.py -k genre -x` | ❌ Wave 0 (extend `test_toolset.py`) |
| CURATE-01 | Both surfaces resolve genre via the ONE `genre_prototypes` mechanism (no parallel classifier) — static-import/grep assertion | unit | `pytest tests/library/ -k "shared_perception or one_mechanism" -x` | ❌ Wave 0 |
| CURATE-01 | Both curator backends (gemini `agent.py` + codex via `mcp_server.py`) reach the enriched features (neither orphaned) | unit | `pytest tests/library/test_toolset.py tests/library/test_agent.py -x` | ⚠️ extend existing |
| CURATE-02 | Curator reads the shared `profile/` (taste bias present when profile set; cold-path-identical when absent/consent-off) | unit | `pytest tests/library/ -k "taste or profile" -x` | ❌ Wave 0 |
| CURATE-02 | Lens is shared across both backends + Telegram transport (regression — already green from Phase 79) | unit | `pytest tests/library/test_curator_persona_seam.py -x` | ✅ existing |
| CURATE SC#3 | `library curate` + Telegram + `next_suggestion` (pill) surfaces still work unchanged (regression) | unit | `pytest tests/library/test_agent.py tests/library/test_telegram_bridge.py tests/library/test_next_suggestion.py -x` | ✅ existing — pin |
| Invariants | No new ws port (one socket, inv #4); no new IPC envelope; single-writer untouched (inv #1) | unit | `pytest tests/repo/ -k "socket or port" ; pytest -k music_state -x` | ✅ existing |
| Import boundary | curator's new profile/genre reads don't leak the live path into `sys.modules` | unit | `pytest tests/memory/test_no_live_path_import.py -x` | ✅ existing — must stay green |

### Sampling Rate
- **Per task commit:** `pytest -q tests/library/ tests/profile/` (the touched packages, < 30s)
- **Per wave merge:** `pytest -q tests/library/ tests/profile/ tests/memory/test_no_live_path_import.py tests/agent/`
- **Phase gate:** full suite green (baseline at phase start: see CONTRIBUTING.md / last green run) before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/library/test_toolset.py` — extend: CURATE-01 genre-via-prototypes (with monkeypatched `RekordboxLibrary.CACHE_PATH` to tmp — the `library.pkl` gotcha) + honest-`"unknown"` abstain.
- [ ] `tests/library/test_*` — NEW: "one perception mechanism" assertion (static grep/AST that the curator genre path routes through `genre_prototypes`, not a parallel classifier) + "taste/profile read" (profile-set → bias present; profile-absent → cold-path-identical).
- [ ] Regression pins on `test_agent.py` / `test_telegram_bridge.py` / `test_next_suggestion.py` confirming the existing surfaces are byte-unchanged in behaviour.
- [ ] No framework install needed — pytest is configured.

*(The "does curating-for-this-DJ feel personal" judgment is NOT automatable — parked as a KAAN-ACTION live item per CONTEXT.)*

## Security Domain

> `security_enforcement` not set to false in config; included for completeness. This phase is local-only, no network surface added, no auth/session/access-control change.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | no auth surface touched |
| V3 Session Management | no | no sessions |
| V4 Access Control | no | local single-user app |
| V5 Input Validation | yes | profile read is schema-validated (`profile/schema.py` allowlist, `additionalProperties: false`); curator grounding gate (seen-set) unchanged |
| V6 Cryptography | no | none |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Profile data leak (track titles / free-form) into curator prompt | Information Disclosure | `profile/schema.py` forbids titles/free-form (P51); only allowlisted 5 fields exist to read; consent-default-OFF |
| Hallucinated track facts (genre) injected by the model | Tampering | genre is a deterministic library-side fact via `genre_prototypes` (not LLM-computed); seen-set + create_playlist re-validation gates unchanged (invariant #2) |
| Import-boundary breach (live path leaks via curator) | Tampering | `tests/memory/test_no_live_path_import.py` + lazy-import discipline (Pattern 1) |

## Sources

### Primary (HIGH confidence — live code, verified this session)
- `src/vibemix/library/toolset.py:108-185` — curator grounded core; `get_track_features` returns `genre: None` (the CURATE-01 seam); seen-set grounding gate.
- `src/vibemix/library/genre_prototypes.py` (full) — the shared perception mechanism (Phase 78); `classify`, `GenrePrototypeLookup`, centering contract.
- `src/vibemix/library/agent.py:114-180,320` — gemini backend; `_shared_lens`/`build_curator_instruction` lazy seam; `LibraryToolset` construction.
- `src/vibemix/library/codex_curate.py:95-135` — codex backend; identical lens seam.
- `src/vibemix/library/mcp_server.py:75-146` — codex MCP STDIO; `build_toolset()` second construction site.
- `src/vibemix/runtime/settings.py:68-91` — `read_shared_lens` (the ONE shared lens read).
- `src/vibemix/profile/{__init__,schema,cache_render}.py` — taste layer; allowlist, `load_profile`, `render_profile_for_cache`; co-host-only (grep-confirmed).
- `src/vibemix/state/refresh.py:244-482` — co-host consumes `genre_prototypes` (`classify_playing` → `detected_genre`).
- `src/vibemix/__main__.py:104,848-870,1090-1093` — co-host loads profile into cache; `from vibemix.profile import load_profile`.
- `tests/memory/test_no_live_path_import.py` — the import-boundary gate + documented historical leak.
- `tests/library/test_curator_persona_seam.py` — the Phase-79 lens regression (the proof persona is shared).
- `.planning/REQUIREMENTS.md` — CURATE-01/02 verbatim.

### Secondary (MEDIUM — design docs, may lag code)
- `.planning/research/connection-map.md` — the islands analysis (2026-05-25; persona section now OBSOLETE post-Phase-79).
- `.planning/research/one-mind-charter.md` — milestone thesis.

### Tertiary (LOW)
- none.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new packages; all primitives verified in tree.
- Architecture (the two seams): HIGH — both gaps confirmed at `file:line` (curator `genre: None`; zero curator profile imports); both shared mechanisms confirmed.
- "Already shared" claims: HIGH — lens seam grep-confirmed in both backends; co-host genre consumption confirmed in `refresh.py`.
- Pitfalls: HIGH — centroid/import-boundary/privacy pitfalls drawn from in-code docstrings and the live test gate.

**Research date:** 2026-05-26
**Valid until:** 2026-06-09 (stable internal architecture; 14 days — re-verify only if Phases 80/81 land further `library/` or `profile/` changes before planning).
