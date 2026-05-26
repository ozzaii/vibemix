# Phase 82: CURATE — Unify Curator + Co-Host - Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 4 (2 source modifies, 1 source modify-each-backend, 1 test extend)
**Analogs found:** 4 / 4 (all exact in-repo — this is a wiring phase, every analog is a sibling seam)

> **Framing (from RESEARCH).** This is a WIRING phase, not a build phase. Two thin, additive ~10-line reads + a regression pin. Every primitive already exists in the tree. Do NOT invent a `PerceptionContract` dataclass — the existing functions ARE the contract. Both seams live in the SHARED `library/` core, so they reach BOTH curator backends (gemini + codex) + Telegram + MCP for free.

## File Classification

| Modified/New File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/vibemix/library/toolset.py` (`get_track_features`, ~:124) | service (shared tool core) | transform (track_id → deterministic facts) | `state/genre_prototypes`-consumer `state/refresh.py:254`; self (`toolset.py:116` Camelot fact) | exact (same mechanism, sibling fact) |
| `src/vibemix/library/agent.py` (`_system_instruction`, :137-151) | service (gemini backend prompt builder) | transform (lens → system instruction) | self (`_shared_lens` lazy+guarded seam, `agent.py:114-134`) | exact (mirror the lens seam) |
| `src/vibemix/library/codex_curate.py` (`_system_prompt`, :116-127) | service (codex backend prompt builder) | transform (lens → system prompt) | `agent.py:_system_instruction`; self (`_shared_lens`, :95-113) | exact (twin of agent.py) |
| `tests/library/test_toolset.py` (extend) | test | transform-assert | self (existing grounding-gate tests, :63-75) | exact (extend existing fixtures) |

**Why only `toolset.py` for SEAM #1 (not each backend):** `get_track_features` is the SHARED tool core. Both backends construct `LibraryToolset` (gemini `agent.py:320`; codex MCP `mcp_server.py:107`) and dispatch through it. One edit to `toolset.py:124` reaches gemini, codex/MCP, and Telegram (which routes through `ViberAgent`) — that is the CURATE acid test satisfied by construction.

**Why SEAM #2 touches BOTH `agent.py` AND `codex_curate.py`:** the taste hint attaches to the *system instruction* (not a tool), and each backend builds its own instruction string at a separate site (`agent.py:147`, `codex_curate.py:125`). Both build it identically (`build_curator_instruction(lens) + RULES`), so the seam is the same ~3-line append at each — but it must be added at BOTH or one backend is orphaned.

## Pattern Assignments

### `src/vibemix/library/toolset.py` — SEAM #1: genre via the ONE perception mechanism (CURATE-01)

**Role:** service (shared grounded tool core). **Data flow:** transform.

**The gap today** (`toolset.py:108-125`) — `genre` is hardcoded `None`:
```python
def get_track_features(self, args: dict[str, Any]) -> dict[str, Any]:
    track_id = args.get("track_id")
    if not isinstance(track_id, str) or not track_id:
        return {"error": "get_track_features: 'track_id' must be a string"}
    entry = self._library.lookup_by_id(track_id)
    if entry is None:
        return {"error": f"unknown track_id {track_id!r}"}
    # Camelot is deterministic — harmonics.to_camelot, never LLM-computed.
    camelot = harmonics.to_camelot(entry.key) if entry.key else None
    return {
        "track_id": entry.track_id, "title": entry.title, "artist": entry.artist,
        "bpm": entry.bpm if (entry.bpm and entry.bpm > 0) else None,
        "key": camelot,        # honest null when unrecognized/absent
        "duration_s": entry.duration_s or None,
        "genre": None,         # <-- THE SEAM: best-effort null today (Phase 1)
    }
```

**Analog = the SAME mechanism the co-host reads.** The co-host resolves genre via `GenrePrototypeLookup.classify_playing` (`genre_prototypes.py:309-335`); the curator must route through the SAME class so genre derives from ONE mechanism:
```python
# Source: src/vibemix/library/genre_prototypes.py:309-335 (the shared mechanism)
def classify_playing(self, track_id: str) -> tuple[str, float]:
    with self._lock:
        self._inflight_gen += 1
        my_gen = self._inflight_gen
    self._ensure_prototypes()                    # lazy-build, snapshot-keyed, centroid-correct
    if self._protos is None or self._protos.shape[0] == 0 or self._centroid is None:
        return ("unknown", 0.0)                  # abstain — degenerate table
    emb = self._cached_embedding(track_id)       # €0 — read cached vector, NO live embed
    if emb is None:                              # unknown-to-library → abstain (invariant #3)
        return ("unknown", 0.0)
    result = classify(emb, self._protos, self._labels, self._centroid)
    ...
    return result
```

**The pattern to copy:**
- Resolve genre from `genre_prototypes` (reuse `GenrePrototypeLookup`, or call `classify(_cached_embedding(track_id), protos, labels, centroid)` directly). The store is already on the toolset (`self._store`, `toolset.py:68`) — construct a `GenrePrototypeLookup(self._store)`.
- **Honest-null on abstain:** `("unknown", 0.0)` → emit `genre: None` (or `"unknown"`) — byte-identical to the co-host's abstain. Same class as the existing Camelot honest-null at `:116`/`:122`.
- **NEVER re-roll centering** (Pitfall 2): call `genre_prototypes`' `classify` / `_ensure_prototypes`, never a fresh `np.mean`/cosine in `toolset.py`. The centroid contract (`genre_prototypes.py:121,166` build/classify share one corpus centroid) lives inside that module.
- **Lazy-import** `genre_prototypes` inside the function (it's already in `library/`, so low-risk, but keep the discipline — Pattern 1).
- **Grounding gate untouched** (Pattern 3, invariant #2): genre is a deterministic library-side fact (not LLM-supplied); the seen-set gate (`toolset.py:134-147`) and `create_playlist` re-validation stay exactly as-is. The model never supplies genre.

**Co-host call pattern for reference** (`state/refresh.py:248-258`) — note the off-loop daemon + abstain-safe shape; the curator call is synchronous (no off-loop needed) but reuses the SAME `classify_playing`/`classify`:
```python
genre_source.clear()
def _worker() -> None:
    try:
        genre_source.classify_playing(track_id)
    except Exception as e:  # never let an off-loop failure escape
        print(f"[genre lookup err] {e}", file=sys.stderr)
threading.Thread(target=_worker, name="genre-lookup", daemon=True).start()
```

---

### `src/vibemix/library/agent.py` + `src/vibemix/library/codex_curate.py` — SEAM #2: taste hint from the ONE profile (CURATE-02 taste half)

**Role:** service (per-backend system-instruction builder). **Data flow:** transform.

**Analog = the EXISTING lazy+guarded lens seam** (`agent.py:114-134`). The new `_taste_hint()` MUST mirror this exactly — lazy import + guarded fallback + per-surface default:
```python
# Source: src/vibemix/library/agent.py:114-134 (the established lazy+guarded seam — COPY THIS SHAPE)
def _shared_lens() -> str:
    """... Lazy-imported so the seam keeps the import-time no-live-path boundary clean.
    WR-03: the read is guarded ... fall back to the "tutor" cold-path default on any exception."""
    try:
        from vibemix.runtime.config_store import load_config
        from vibemix.runtime.settings import read_shared_lens
        return read_shared_lens(load_config(), default="tutor") or "tutor"
    except Exception:  # pragma: no cover — guard: any read fail = cold default
        return "tutor"
```

**The pattern to copy (NEW `_taste_hint`, per RESEARCH Seam #2):**
```python
def _taste_hint() -> str:
    """Compact, privacy-safe profile hint biasing curation 'for this DJ'.
    Cold path (no/consent-off profile) -> "" -> byte-identical to today."""
    try:
        from vibemix.profile import load_profile, render_profile_for_cache
        return render_profile_for_cache(load_profile())  # "" when None
    except Exception:
        return ""
```

**Where it attaches** — both backends build the curator instruction the SAME way; append the hint at the SAME point in each:
```python
# Source: src/vibemix/library/agent.py:143-151 (gemini backend — SEAM attaches here)
with _CACHE_LOCK:
    if _SYSTEM_INSTRUCTION_CACHE is None or _SYSTEM_INSTRUCTION_LENS != lens:
        from vibemix.prompts.matrix import build_curator_instruction
        _SYSTEM_INSTRUCTION_CACHE = (
            build_curator_instruction(lens) + "\n" + _RULES_BLOCK   # <-- append _taste_hint() here
        )
        _SYSTEM_INSTRUCTION_LENS = lens
    return _SYSTEM_INSTRUCTION_CACHE
```
```python
# Source: src/vibemix/library/codex_curate.py:121-127 (codex backend — TWIN seam, must also get it)
with _CACHE_LOCK:
    if _SYSTEM_PROMPT_CACHE is None or _SYSTEM_PROMPT_LENS != lens:
        from vibemix.prompts.matrix import build_curator_instruction
        _SYSTEM_PROMPT_CACHE = build_curator_instruction(lens) + " " + _RULES_BLOCK  # <-- append _taste_hint()
        _SYSTEM_PROMPT_LENS = lens
    return _SYSTEM_PROMPT_CACHE
```
> Note: `_interactive_system_instruction` (`agent.py:154-170`) is a SECOND build site in the gemini backend — the taste hint should attach there too (or factor the hint into a helper both call) so interactive curation is not orphaned.

**The privacy-safe vehicle** — `render_profile_for_cache` (`cache_render.py:31-57`) returns `""` for `None`/empty and only ever emits the 5 allowlisted fields (preferred_genre, avg_session_duration, mix_style_tags, tempo_preference_bin, event_response_preferences) — NO track titles, NO free-form (Pitfall 4 / P51):
```python
# Source: src/vibemix/profile/cache_render.py:31-57
def render_profile_for_cache(profile: dict[str, Any] | None) -> str:
    if not profile:
        return ""                                  # <-- cold path: empty -> byte-identical to today
    lines = [_HEADER.strip()]
    genre = profile.get("preferred_genre", "unknown")
    lines.append(f"- preferred_genre: {genre}")
    ...  # only allowlisted fields; never titles
    return "\n\n" + "\n".join(lines) + "\n"
```

**Cold-path identity (Pattern 2):** `load_profile()` returns `None` when absent/invalid/consent-OFF (consent default-OFF, `profile/__init__.py:15`). `render_profile_for_cache(None) == ""` → instruction is byte-identical to today. NEVER raw JSON; NEVER per-turn (curator is single-shot — system instruction is the correct vehicle, no cache exists).

**Anti-pattern (avoid):** do not re-read profile keys with `[...]` (KeyError on missing field, Pitfall 4) — `render_profile_for_cache` already uses `.get(..., default)` for every field. Use it; don't hand-roll a profile reader.

---

### `tests/library/test_toolset.py` (extend) — Wave-0 coverage

**Role:** test. **Analog:** the existing grounding-gate tests in the SAME file (`:36-75` fixtures + `test_search_populates_seen_set`).

**Reuse the existing fixtures** (`_make_track` :22, `library` :36, `toolset` :43, `_stub_search` :48). Add:
- CURATE-01 genre-via-prototypes: assert `get_track_features` returns a genre derived from `genre_prototypes` (monkeypatch the prototype lookup / cached embedding) + honest-`None`/`"unknown"` on abstain (no embedding in store).
- **`library.pkl` gotcha (CLAUDE.md):** any test touching `RekordboxLibrary` cache MUST monkeypatch `RekordboxLibrary.CACHE_PATH` to a tmp dir or it overwrites the real `~/.cache/vibemix/library.pkl`. (The current fixture sets `lib.tracks` in-memory and avoids the cache — keep that discipline for new tests.)
- "One mechanism" assertion (static/AST grep): the curator genre path routes through `genre_prototypes`, NOT a parallel `np.mean`/cosine classifier.
- CURATE-02 taste: profile-set → hint present in instruction; profile-absent/consent-OFF → instruction byte-identical (cold path).

**Pin regressions (do NOT break — byte-unchanged behaviour):**
- `tests/library/test_curator_persona_seam.py` (Phase-79 lens — already green, the persona half is DONE).
- `tests/library/test_agent.py`, `tests/library/test_telegram_bridge.py`, `tests/library/test_next_suggestion.py` (the existing curate/Telegram/pill surfaces).
- `tests/memory/test_no_live_path_import.py` (the import-boundary gate — must stay `CLEAN`).

## Shared Patterns

### Pattern 1 — Lazy-import every cross-package read (import-boundary discipline)
**Source:** `library/agent.py:128-134` (`_shared_lens`), `codex_curate.py:109-111`.
**Apply to:** BOTH new seams — `genre_prototypes` read in `toolset.py`, `profile` read in `agent.py`/`codex_curate.py`.
**Why:** `tests/memory/test_no_live_path_import.py` forbids `vibemix.prompts`/`vibemix.agent`/live-path leaking into `sys.modules` via the storage spine, and documents the historical `library/__init__` → `toolset` → `vibemix.state` eager-import leak (`test_no_live_path_import.py:39-45`). `library/__init__.py` eagerly imports `toolset` (no lazy `__getattr__`), so a top-level `from vibemix.profile import ...` in `toolset.py` becomes import-time (Pitfall 3). Import INSIDE the function.
```python
# The shape (agent.py:128-134) — copy verbatim for the profile + genre reads:
def _xxx() -> ...:
    try:
        from vibemix.<pkg> import <fn>      # LAZY — inside the function
        return <fn>(...)
    except Exception:                        # guard: any read fail = cold default
        return <cold-default>
```

### Pattern 2 — Per-surface default-when-unset (byte-identical cold path)
**Source:** `runtime/settings.py:68-91` (`read_shared_lens(store, default=...)`).
**Apply to:** the profile/taste read — absent profile → `""` (no bias); abstain genre → `None`/`"unknown"`.
**Why:** each surface's pre-wire behaviour must be byte-identical. Curator lens passes `default="tutor"`; co-host passes `default=None`. Mirror this: curator taste → `""` when no profile; curator genre → `None` when abstain (exactly today's `genre: None`).
```python
# Source: src/vibemix/runtime/settings.py:88-91
lens = store.extra.get("lens")
if isinstance(lens, str) and lens:
    return lens
return default        # <-- per-surface cold default
```

### Pattern 3 — Grounding gate is sacred (invariant #2)
**Source:** `library/toolset.py:108-125` (deterministic facts) + `:134-147` (seen-set gate).
**Apply to:** SEAM #1 — genre must be a deterministic library-side fact (via `genre_prototypes`), same class as Camelot-via-`harmonics` (`:116`). It must NOT widen the seen-set gate or let the model invent genre.
```python
# Source: src/vibemix/library/toolset.py:137-147 — gate #1 (NEVER weaken)
invented = [t for t in track_ids if not (isinstance(t, str) and t in self.seen)]
if invented:
    return {"error": ("rejected: these track_ids were never returned by "
                      f"search_vibe this run (invented): {invented}. ...")}
```

### Persona/lens — ALREADY SHARED (Phase 79 — regression pin only, do NOT re-do)
**Source:** `prompts/matrix.build_curator_instruction` read by BOTH backends (`agent.py:145`, `codex_curate.py:123`) via the ONE `read_shared_lens` (`settings.py:68`).
**Apply to:** nothing — confirm-and-pin via `tests/library/test_curator_persona_seam.py`. Verify with `grep build_curator_instruction src/vibemix/library/` before planning ANY persona work. A plan task that adds `build_lens_instruction` to a curator backend is a Pitfall-1 mistake (it's already there). The pill (`next_suggestion`) is pure DSP/cosine — correctly lens-agnostic, untouched.

## Construction-Site Map (why both seams reach both backends)

| Backend / transport | LibraryToolset construction | Instruction build site | SEAM #1 (genre) reaches? | SEAM #2 (taste) reaches? |
|---------------------|-----------------------------|------------------------|--------------------------|--------------------------|
| Gemini (`agent.py`) | `agent.py:320` | `_system_instruction` :137-151 + `_interactive_system_instruction` :154-170 | ✓ via shared toolset | ✓ append at :147 (+:166) |
| Codex MCP (`mcp_server.py`) | `mcp_server.py:107` (`build_toolset`) | `codex_curate.py:_system_prompt` :116-127 | ✓ via shared toolset | ✓ append at :125 |
| Telegram | routes through `ViberAgent` (gemini) | (inherits gemini) | ✓ | ✓ |
| Pill (`next_suggestion`) | pure DSP — no toolset, no LLM voice | n/a | n/a (lens-agnostic by design) | n/a |

**Key:** SEAM #1 is ONE edit (shared `toolset.get_track_features`) → reaches all LLM backends + Telegram + MCP. SEAM #2 is TWO edits (`agent.py` + `codex_curate.py`) because each backend builds its own instruction string at a separate site.

## No Analog Found

None. Every file in this phase has an exact in-repo sibling seam — this is a wiring phase, not a build phase. (The "perception contract" the CONTEXT names is the EXISTING set of functions: `genre_prototypes.classify`, `toolset.get_track_features`, `profile.render_profile_for_cache`. Do NOT invent a dataclass — that fails the ship-not-over-engineer bar / Anti-Pattern in RESEARCH.)

## Do-NOT-Bridge (tier boundary — RESEARCH Tier note)

| Surface | Rule |
|---------|------|
| `state/music_state.py` `MusicState` | The curator MUST NOT read or write it (invariant #1, single-writer). The shared perception is the LIBRARY representation (`genre_prototypes` + `toolset` features, derived from the offline embedding store), never the live state object. |

## Metadata

**Analog search scope:** `src/vibemix/library/` (toolset, agent, codex_curate, mcp_server, genre_prototypes), `src/vibemix/profile/` (`__init__`, cache_render, storage), `src/vibemix/runtime/settings.py`, `src/vibemix/state/refresh.py`, `tests/library/`, `tests/memory/`.
**Files scanned:** ~12 (all in-tree, all verified at `file:line` this session).
**Line numbers verified against live source:** 2026-05-26 — `toolset.py:108-185`, `genre_prototypes.py:241-348`, `agent.py:114-180,306-320`, `codex_curate.py:95-135`, `mcp_server.py:90-148`, `settings.py:68-91`, `cache_render.py:31-57`, `profile/__init__.py:1-67`, `refresh.py:248-258`, `test_toolset.py:1-75`, `test_no_live_path_import.py` (full).
**Pattern extraction date:** 2026-05-26
