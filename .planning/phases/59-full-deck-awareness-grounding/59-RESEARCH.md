# Phase 59: Full Deck Awareness + Grounding - Research

**Researched:** 2026-05-21
**Domain:** Deck-state grounding ladder (pyrekordbox XML → Gemini-vision → numpy key estimator), citable `key:` evidence source + linter rule, single-writer `MusicState` integration, new event-type plumbing — strictly read-only
**Confidence:** HIGH (read directly against branch `live-tuning-or-brain` source + verified pyrekordbox 0.4.4 install + XML fixture key format)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Data-Source Ladder & Scope**
- **Universal primary = Gemini-vision reading the deck panels** in the screenshot the co-host already captures — works for every DJ app (Rekordbox/Serato/djay/Traktor/Engine) with zero user setup; reads loaded-track title + key/BPM badge per visible deck.
- **High-fidelity enrichment = pyrekordbox via the exported XML** (user points at a Rekordbox `collection.xml` / device export) — NOT the live `master.db`. Carries pre-computed key/BPM unencrypted; sidesteps the post-6.6.5 SQLCipher wall AND the `master.db` write-corruption landmine. Live-DB read is **deferred unless the plan-time spike proves it lock-safe while Rekordbox runs**.
- **Last-resort = in-house numpy Krumhansl-Temperley key estimator** (no Essentia/librosa — NOT installed; no CLAP/MERT). Used only when neither a tag nor an on-screen badge yields a key.
- **Scope of "all loaded tracks" = the currently-loaded track per deck** (2–4 decks). Full session/library history is future, not this milestone.
- **Per-deck metadata = title, musical key (Camelot + open-key), BPM, energy/confidence** where resolvable; surfaced honestly as `unknown` when not — never a false-confident guess.

**Grounding / Citation (must land BEFORE any harmonic prompt)**
- **Dedicated `key:` evidence source + linter rule** (resolves the ARCHITECTURE↔PITFALLS divergence in favor of a new source). Harmonic claims are uncitable-by-construction today (`EVIDENCE_SOURCES` has no key/harmonic source); without this the anti-slop strip can't catch a false clash.
- Citation body shape ≈ `key:<deck>:<camelot>` plus the track ref; **skip the timestamp-tolerance check for library-sourced keys** (mirror how the existing `track:` source is treated). Exact EBNF/grammar finalized at plan time.
- Each deck-track carries `{source, confidence}`; below threshold → `unknown`. The LLM may never assert a key the source did not provide.

**State Integration (single-writer preserved)**
- New `DeckState` / `DeckTrack` dataclass in **`state/deck_state.py`**, **embedded as a field of `MusicState`** (zero read-side signature churn; consistency under the existing `state._lock`).
- A **read-only deck poller** writes its own holder + `.snapshot()` (same pattern as `ControllerState` / `TrackInfo`); **`_tick_once` is the ONLY thing that copies it into `MusicState`**, inside the existing lock block.
- Register `KEY_CLASH` (priority ~7, ~25–30s cooldown) + `TRANSITION_OPPORTUNITY` (priority ~5, ~20s) in `EVENT_PRIORITY` / `MIN_EVENT_GAP_PER_TYPE`. **This phase wires the event *types* + plumbing; the firing logic is Phase 60.**
- Existing snapshot golden-equivalence preserved (additive-only fields).

**Failure / Degradation / Safety**
- **Tiered graceful degradation to `unknown`** — when no source resolves, the feature stays silent rather than guessing.
- **Strictly read-only** — a repo test asserts no DJ-software DB is ever opened in write mode; prefer the XML-export file over any live DB.
- **Cross-deck claims suppressed when the second (non-audible) deck cannot be independently resolved** — degrade to single-deck, never guess the other deck.
- Cross-platform: vision + XML + numpy paths are OS-agnostic (mac+win); `nowplaying-cli` stays mac-only current-track enrichment.
- **Deck-poll cadence bounded for cost** — vision read only on a track-change signal / screen-change (not every tick); XML parsed once per session / on file change.

### Claude's Discretion
- Exact `key:` citation EBNF, poll cadence numbers, confidence thresholds, and the deck→track resolution heuristic details — set at plan time from research + existing `track_resolver.py` / `derive_audible_deck` patterns.

### Deferred Ideas (OUT OF SCOPE)
- ProDJ Link / StagelinQ (`prolink-connect`) per-deck telemetry — hardware-gated, future.
- Live audio key-detection promoted to a primary source (cross-checked) — future; only the numpy fallback ships now.
- Per-deck low-band / bass-clash DSP from a single master stream — future (keeps bass-clash note P2).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DECK-01 | Session-wide deck-state (every loaded track + key/BPM/energy), exposed to coach the grounded way `phase`/`bpm`/`mood` are | `DeckState` embedded in `MusicState` as additive field; `evidence_line` deck block. §State Integration, §Architecture Patterns Pattern 1 |
| DECK-02 | Populated from the data-source ladder (XML primary, Gemini-vision fallback, numpy last-resort); honest `unknown` | §Spike 1 (XML), §Spike 2 (vision), §Don't Hand-Roll (numpy KS), §Architecture Patterns Pattern 2 (ladder) |
| DECK-03 | New `key:` evidence source + linter rule; un-cited harmonic feedback stripped (gates harmonic feature) | §Spike 3 (`key:` grammar/EBNF), `EVIDENCE_SOURCES` + `citation_linter._validate_atom` extension. §Code Examples |
| DECK-04 | Integrates into `MusicState` under single-writer rule (poller → `_tick_once` only); new `KEY_CLASH` + `TRANSITION_OPPORTUNITY` types in priority/cooldown maps | §State Integration, §Code Examples (event.py + constants.py edits) |
| DECK-05 | Strictly read-only — never writes any DJ DB; cross-deck claims suppressed when 2nd deck unresolved | §Spike 1 (read-only guarantee), §Validation Architecture (repo test), §Architecture Patterns Pattern 3 (cross-deck suppression) |
</phase_requirements>

## Summary

This is a **pure integration phase on a mature, grounded system** — every new piece bolts onto an existing, well-tested pattern. The four cardinal invariants (single-writer `MusicState`, citation-grounding via `EvidenceRegistry`+`CitationLinter`, "trust the audio", one socket) are all preserved by mirroring established producers: the deck poller is the *third* read-only external source after `ControllerState` and `TrackInfo`, copied into `MusicState` only inside `_tick_once`'s lock batch.

The two flagged spikes are **resolved with concrete recommendations**: (1) **XML-export is the confirmed primary** — `RekordboxLibrary.load_xml()` already exists, already parses `Tonality`/`AverageBpm`, already feeds `EvidenceRegistry.register_library()`, and a grep-gate + dormancy test already forbid the live SQLCipher path. Live-DB read is **NOT recommended** (the SQLCipher key story is unverifiable on a distributed binary and the codebase deliberately bans it). (2) **Gemini-vision deck-read requires re-enabling a path that is currently `screen_jpeg = None`** in `dj_cohost.llm_node` (disabled in v4 because "Screen + MIDI metadata caused hallucination"). This is the single biggest risk in the phase: the vision fallback is the *universal* leg of the ladder but it sits behind a deliberate anti-hallucination kill-switch. The plan MUST treat re-enabling vision as a gated, eval-backed sub-task with a real-screenshot accuracy pass — not a flip of one line.

The `mix:`-reuse vs `key:`-source divergence is **resolved in favor of a dedicated `key:` source** (per CONTEXT lock). The key insight that drives the grammar: Rekordbox XML carries `Tonality` as **musical notation** (`Am`, `F#m`, `Cm` — confirmed in the fixture), NOT Camelot codes — so `harmonics.to_camelot()` is a load-bearing pure-function dependency and the citation body must carry the *normalized* Camelot the coach actually reasons on (`key:A:8A`), with the raw tag preserved on the `DeckTrack`.

**Primary recommendation:** Build the spine bottom-up — `harmonics.to_camelot()` (pure, zero-dep) → `DeckState`/`DeckTrack` (additive) → XML-driven deck poller (reuses the *already-shipped* `RekordboxLibrary`) → `_tick_once` wiring + `key:` registry writes → `key:` source + linter rule → event-type plumbing. Gate the Gemini-vision leg behind a separate eval task. Numpy KS estimator is fallback-only; defer its build if the XML+vision ladder covers the live-test set.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Loaded-track identity per deck | API/Backend (Python sidecar — deck poller) | — | Cross-app deck identity is a backend resolution problem; no UI tier owns it |
| Deck metadata (key/BPM/energy) lookup | Database/Storage (RekordboxLibrary XML cache) | API (Gemini-vision read) | Pre-analyzed library tags are the storage oracle; vision is the runtime fallback when no library entry |
| Musical key → Camelot normalization | API/Backend (pure `harmonics.to_camelot`) | — | Deterministic lookup; must run server-side before any citation/event |
| Deck-state consistency / single-writer | API/Backend (`_tick_once` under `state._lock`) | — | The established single-writer invariant; never the poller, never a consumer |
| Citation grounding of keys | API/Backend (`EvidenceRegistry` + `CitationLinter`) | — | The anti-slop contract is a backend gate before the LLM response ships |
| Honest `unknown` degradation | API/Backend (poller confidence + `evidence_line`) | UI (later phases surface the chip) | Degradation decision is grounded at the source; UI only displays it |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pyrekordbox` | 0.4.4 (installed, pinned) | Parse `collection.xml` → `Tonality`/`AverageBpm`/cues per track | Already a dependency; already wired via `RekordboxLibrary.load_xml()`; XML path is the unencrypted, lock-free, post-6.6.5-safe oracle `[VERIFIED: pyproject.toml line 54 + installed venv]` |
| `numpy` | 2.4.4 (installed) | Krumhansl-Temperley chromagram + key-profile correlation (fallback estimator); all deck DSP | Same DSP family as the shipped BPM autocorrelation in `audio/features.py`; zero new dep `[VERIFIED: installed venv]` |
| `scipy` | 1.17.1 (installed) | FFT/resample support for the numpy key estimator if needed | Already used for resampling; `[VERIFIED: installed venv]` |
| `google-genai` | (installed) | Gemini-vision deck-panel read via inline image Part | Gemini-only constraint; the screen-capture path already exists (`platform/screen.py` → `CapturedFrame.jpeg`) `[VERIFIED: src/vibemix/agent/dj_cohost.py screen_buf wiring]` |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `mss` / `pyobjc-Quartz` (mac) / SMTC (win) | (installed) | Screen capture → `CapturedFrame` for the vision leg | Already shipped via `ScreenBackend` protocol; the poller reuses `screen_buf.latest()` |
| `nowplaying-cli` (mac) | Homebrew binary | Current-audible-track title enrichment | mac-only; stays the audible-anchor, NOT a deck-state source |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pyrekordbox XML export | pyrekordbox live `Rekordbox6Database` (SQLCipher) | Live DB gives per-track collection metadata but: post-6.6.5 key obfuscation, undocumented lock-safety while RB runs, write-corruption risk, and the codebase's own grep-gate + dormancy test forbid it. **REJECTED for v5.0** — see Spike 1 |
| In-house numpy KS/Temperley | Essentia `KeyExtractor` | Essentia is best-in-class but a RED-rated heavy C++ binary, platform-fragile on the mac+win one-click installer, not installed. Fallback-only key detection doesn't justify it. **REJECTED** `[VERIFIED: essentia absent from venv]` |
| In-house numpy KS/Temperley | librosa chroma | librosa pulls numba/soundfile/audioread, has no key extractor anyway (still hand-roll correlation), YELLOW install-impact. **REJECTED** `[VERIFIED: librosa absent from venv]` |
| Gemini-vision deck read | tesseract/easyocr OCR engine | Redundant — already sending the screenshot to a multimodal model; separate OCR is scope creep. **REJECTED** `[CITED: STACK.md "What NOT to Use"]` |
| Gemini-vision deck read | Per-app library parsers (Serato `.crate`, Traktor `.nml`, Engine) | Real surface area per app; vision covers them universally for v5.0. **DEFER to v.next** `[CITED: STACK.md]` |

**Installation:**
```bash
# NO new package required. pyrekordbox 0.4.4 + numpy 2.4.4 + scipy 1.17.1 already installed.
# This phase is config + code on already-pinned deps. The numpy KS estimator and the
# Camelot table are new source files (zero deps).
```

**Version verification:**
```bash
.venv/bin/python -c "import pyrekordbox; print(pyrekordbox.__version__)"   # → 0.4.4 [VERIFIED]
.venv/bin/python -c "import numpy, scipy; print(numpy.__version__, scipy.__version__)"  # → 2.4.4 1.17.1 [VERIFIED]
.venv/bin/python -c "import importlib.util as u; print(bool(u.find_spec('essentia')), bool(u.find_spec('librosa')))"  # → False False [VERIFIED]
```

## Package Legitimacy Audit

> No external packages are installed in this phase — all recommended libraries are already
> pinned dependencies, verified present in the venv. slopcheck not required (no new installs).

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pyrekordbox | PyPI | 0.4.4 (2025-08-17) | established | github.com/dylanljones/pyrekordbox | n/a (already pinned + grep-gated) | Already approved (Plan 25-01) |
| numpy | PyPI | mature | massive | github.com/numpy/numpy | n/a (already pinned) | Already approved |
| scipy | PyPI | mature | massive | github.com/scipy/scipy | n/a (already pinned) | Already approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                       DECK-STATE GROUNDING LADDER (read-only)
   ┌────────────────────────────────────────────────────────────────────────┐
   │  SOURCE LADDER (per deck, highest-confidence-wins)                       │
   │                                                                          │
   │   ① pyrekordbox XML        ② Gemini-vision         ③ numpy KS/Temperley  │
   │   RekordboxLibrary cache   deck-panel read         key estimator         │
   │   Tonality→key, BPM        title+key+BPM badge      (last resort, no tag) │
   │   (PRIMARY enrichment)     (UNIVERSAL identity)     (FALLBACK only)       │
   │        │                        │                        │               │
   │        └──── title→library match ──── audible-deck ──────┘               │
   │                          resolution (derive_audible_deck)                │
   └──────────────────────────────────┬───────────────────────────────────────┘
                                       │  DeckSource.snapshot() -> {A:DeckTrack, B:..}
                                       ▼  (read-only producer, own holder)
   ┌──────────────────────────────────────────────────────────────────────────┐
   │  state_refresh_loop._tick_once  (10Hz — THE ONLY WRITER, inside _lock)    │
   │   1. deck_snap = deck_source.snapshot()                                   │
   │   2. for dt: dt.camelot = harmonics.to_camelot(dt.key)   # pure fn        │
   │   3. state.deck_state.decks = deck_snap                  # additive field  │
   │   4. registry.write("key", f"{side}:{dt.camelot}", t)    # NEW source     │
   │      registry.write("track", dt.track_id, t)            # existing        │
   └──────────────────────────────────┬───────────────────────────────────────┘
                                       │ MusicState (single source of truth)
              ┌────────────────────────┼────────────────────────┐
              ▼                        ▼                         ▼
   ┌──────────────────┐    ┌────────────────────┐    ┌─────────────────────┐
   │ EventDetector    │    │ AICoach            │    │ CitationLinter      │
   │ (read-only)      │    │ evidence_line gains│    │ _validate_atom gains│
   │ KEY_CLASH +      │    │ a deck block;      │    │ "key" as existence- │
   │ TRANSITION_OPP   │    │ task_for_event arms│    │ only source (no @t) │
   │ TYPES registered │    │ (Phase 60 fills    │    │ → strips fabricated │
   │ (firing = P60)   │    │  the firing tasks) │    │  [key:A:12B] clash  │
   └──────────────────┘    └────────────────────┘    └─────────────────────┘
```

### Recommended Project Structure
```
src/vibemix/state/
├── harmonics.py          # NEW — pure: musical-notation → Camelot, open-key; no I/O, no state
├── deck_state.py         # NEW — DeckState / DeckTrack dataclasses
├── deck_poller.py        # NEW — read-only producer; own holder + .snapshot(); XML+vision+numpy ladder
├── music_state.py        # MODIFIED — additive `deck_state: DeckState` field
├── refresh.py            # MODIFIED — _tick_once copies deck_snap + writes key:/track: registry obs
├── event.py              # MODIFIED — KEY_CLASH=7, TRANSITION_OPPORTUNITY=5 in EVENT_PRIORITY
├── evidence_registry.py  # MODIFIED — add "key" to EVIDENCE_SOURCES + _SOURCE_ALT/_INNER_ATOM regex
└── coach.py              # MODIFIED (light) — evidence_line deck block; task_for_event stub arms

src/vibemix/audio/
└── constants.py          # MODIFIED — KEY_CLASH/TRANSITION_OPPORTUNITY in MIN_EVENT_GAP_PER_TYPE

src/vibemix/coach/
└── citation_linter.py    # MODIFIED — "key" is an existence-only source (NOT in _TIME_KEYED_SOURCES)
```

### Pattern 1: Embedded additive deck-state field (zero read-side churn)
**What:** `DeckState` lives as a default-empty field of `MusicState`, not a sibling object.
**When to use:** Always for v5.0 deck-state — every consumer already receives `MusicState`.
**Example:**
```python
# state/deck_state.py — NEW (shape per ARCHITECTURE.md, refined for the verified XML key format)
from dataclasses import dataclass, field

@dataclass
class DeckTrack:
    title: str | None = None       # resolved track label
    track_id: str | None = None    # RekordboxLibrary TrackEntry.track_id — feeds [track:<id>]
    bpm: float = 0.0               # from source metadata (AverageBpm), NOT audio autocorr
    key: str | None = None         # RAW tag as the source gives it ("Am", "F#m" — see Spike 1)
    camelot: str | None = None     # normalized via harmonics.to_camelot() ("8A", "11A")
    open_key: str | None = None    # open-key form ("1m"/"1d") for honesty/UI
    energy: int | None = None      # 1..10 if source exposes it (rekordbox), else None
    loaded_at: float = 0.0
    confidence: float = 0.0        # 0..1 — how sure we are this deck holds this track
    source: str = "unknown"        # "rekordbox_xml" | "screen_vision" | "numpy_key" | "nowplaying" | "unknown"

@dataclass
class DeckState:
    decks: dict[str, DeckTrack] = field(default_factory=dict)  # {"A": DeckTrack, "B": ...}
    updated_at: float = 0.0
```
```python
# state/music_state.py — additive (default-empty preserves golden-equivalence,
# same discipline as Phase 17/31/52 fields already in the file)
    deck_state: DeckState = field(default_factory=DeckState)
```
**Source:** ARCHITECTURE.md §A `[CITED]` + golden-equivalence pattern verified in `music_state.py:53-90` `[VERIFIED: codebase]`

### Pattern 2: Source-ladder with highest-confidence-wins + honest unknown
**What:** Each deck's `DeckTrack` is resolved by trying sources in order, keeping the first that clears its confidence floor; below all floors → `confidence=0`, `source="unknown"`, every harmonic field stays `None`.
**When to use:** Inside the deck poller's `.snapshot()` build.
**Order:** ① XML library match (highest confidence — pre-analyzed tag) → ② Gemini-vision badge read → ③ numpy KS estimate (key only, last resort). The audible-deck attribution (`derive_audible_deck`) decides *which* deck a resolved title belongs to.
**Source:** STACK.md §A "layered grounding" + CONTEXT lock `[CITED]`

### Pattern 3: Cross-deck suppression (degrade to single-deck, never guess)
**What:** A deck-state field is only emitted/citable when that deck is *independently* resolved. The second (non-audible) deck must resolve via its own source signal (vision badge or a confidently-attributed library match), not by "the other now-playing title".
**When to use:** The poller sets `confidence=0` on any deck it cannot independently confirm; the `key:` registry write is gated on `confidence >= DECK_CITE_MIN_CONF`. Phase 60's clash logic then can't cite a deck the registry never saw.
**Source:** PITFALLS Pitfall 4 + CONTEXT "Failure/Degradation/Safety" lock `[CITED]`

### Anti-Patterns to Avoid
- **Poller writes `MusicState` directly:** Violates single-writer; torn snapshots for `EventDetector`/`AICoach`. → Poller writes its own holder; `_tick_once` copies under `state._lock`.
- **Reusing `mix:` for keys (no new source):** CONTEXT locked `key:`. `mix:` is existence-only with no per-deck-per-key grammar; a fabricated `12B` clash would slip through because the linter can't distinguish a real deck key from a hallucinated one. → Dedicated `key:` source (see Spike 3).
- **Flipping `screen_jpeg = None` to live in one line:** That line is a deliberate v4 anti-hallucination kill-switch ("Screen + MIDI metadata caused hallucination" — `dj_cohost.py:546`). → Re-enable behind an eval-gated, scoped vision sub-task (Spike 2).
- **Treating Rekordbox `Tonality` as Camelot:** It's musical notation (`Am`/`F#m`). → Always normalize via `harmonics.to_camelot()` before any citation/event.
- **Putting deck-state in the diet/ack prompt path:** Deck feedback is substantive; `ACK_ELIGIBLE_EVENTS` is the quick-ack path. → Deck events are full-payload (NOT in `ACK_ELIGIBLE_EVENTS`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rekordbox XML parsing | A custom XML reader for `collection.xml` | `RekordboxLibrary.load_xml()` (already exists, `library/rekordbox.py`) | Already parses `Tonality`/`AverageBpm`/cues with schema-drift defense (`_safe_get`), pickle cache, staleness nudge, grep-gate `[VERIFIED: codebase]` |
| Library → registry wiring | A new registry registration path for keys | Extend the existing `register_library` + `track:` resolution (already wired in `__main__.py:886`) | `[track:<id>]` already resolves against the real collection `[VERIFIED: __main__.py + evidence_registry.py:218]` |
| Camelot wheel math | Hardcoded compatibility branches | A deterministic 24-entry lookup table in `harmonics.py` (Phase 60 consumes; this phase ships `to_camelot`) | The wheel is a fixed table; the LLM never computes intervals `[CITED: STACK.md §Camelot]` |
| Screen→Gemini image plumbing | A new capture/encode path | The existing `ScreenBackend` → `CapturedFrame.jpeg` + `types.Part.from_bytes` pattern in `dj_cohost.py` | The capture firewall + JPEG encode + inline-Part wiring already exist (currently `None`-gated) `[VERIFIED: screen.py + dj_cohost.py]` |
| Key detection (fallback) | Essentia/librosa | In-house numpy chromagram + Krumhansl-Temperley/EDMA profile correlation (~80 lines) | Same FFT family as `audio/features.py`/`_dsp.py`; zero dep; fires only when no tag exists `[CITED: STACK.md §B]` |
| Audible-deck inference | A new deck-attribution heuristic | `derive_audible_deck` / `derive_audible_track` (already handles FLX4 desync, fader+xfader weighting) | The v4 fix already trusts fader+xfader as the reliable grounded signal `[VERIFIED: track_resolver.py]` |

**Key insight:** ~70% of this phase's "data" work is *already shipped* (XML parsing, library registration, screen capture, audible-deck resolution). The genuinely new code is small and pure: `harmonics.to_camelot`, the `DeckState` dataclasses, the poller that composes existing sources, the `key:` grammar/linter line, and the event-type constants. Resist re-implementing the existing rails.

## Spike 1 — pyrekordbox data path: XML-export confirmed primary, live-DB rejected

**RESOLUTION: Lean XML-export per CONTEXT. Do NOT activate the live `Rekordbox6Database` SQLCipher path. Live-read is NOT proven lock-safe and the codebase deliberately forbids it.**

### What the codebase already does (ground truth)
- `library/rekordbox.py::RekordboxLibrary.load_xml()` parses `collection.xml` via `pyrekordbox.RekordboxXml` — **XML import path only** `[VERIFIED: codebase]`.
- The SQLCipher `db6`/`Rekordbox6Database` path is **deliberately banned**: a grep-gate (`grep -r "Rekordbox6Database\|pyrekordbox.db6" src/vibemix/` must stay empty) + a subprocess dormancy test `tests/library/test_rekordbox.py::test_no_sqlcipher_module_imported_after_load` (asserts no `*sqlcipher*` module loads) + `pyproject.toml:135` overrides `sqlcipher3-wheels` out via a never-match platform marker `[VERIFIED: codebase + pyproject.toml]`.
- `evidence_registry.register_library()` is already wired in `__main__.py:886` — on session start, if the pickle cache loads, the full collection is registered as `track:<id>` observations `[VERIFIED: codebase]`.

### Exactly what fields the XML yields (verified against the fixture)
`TrackEntry` exposes: `track_id`, `title`, `artist`, `album`, `bpm` (from `AverageBpm`), `key` (from `Tonality`), `duration_s`, `cues`, `filepath` `[VERIFIED: rekordbox.py:69-94]`.

**CRITICAL — the key format is musical notation, NOT Camelot:**
```
Tonality="Am"   Tonality="Cm"   Tonality="Dm"   Tonality="F#m"   Tonality="Gm"
AverageBpm="124.0"  "128.0"  "132.5"  "150.0"  "90.0"
```
`[VERIFIED: tests/library/fixtures/synthetic_collection.xml]`

This means `harmonics.to_camelot("Am") -> "8A"`, `to_camelot("F#m") -> "11A"` is a **load-bearing pure function** that must exist before any `key:` citation. The `DeckTrack` keeps `key` (raw `"Am"`), `camelot` (`"8A"`), and `open_key` (`"1m"`) so the coach reasons on Camelot while honesty/UI can show the raw tag.
> **Note on real-world tags:** Rekordbox can also export `Tonality` in Camelot or open-key form depending on the user's preference setting, and some exports omit `Tonality` entirely. `to_camelot()` must accept all three input forms (musical / Camelot / open-key) and degrade to `None` (→ `key=unknown`) on an unrecognized/empty tag — never raise. `[ASSUMED — A1]`

### How the user supplies the XML
- **Already designed:** the Phase 25 wizard has an optional "Import collection.xml" step; the path feeds `load_xml()` which writes a pickle cache; subsequent sessions use `try_load_cache()` `[VERIFIED: rekordbox.py docstring + __main__.py:887]`.
- **Recommendation:** the deck poller reads from the *already-loaded* `RekordboxLibrary` (cache-warm), not a fresh parse per poll. Title→`TrackEntry` resolution is the join key. No new config surface needed; reuse the existing wizard path + `CACHE_PATH`.

### Why live-DB is rejected (the spike's negative finding)
- **SQLCipher key story is unverifiable for a distributed binary.** Official docs confirm the DB "is encrypted… can't be used without the encryption key" and that the key is local but give **no** version-compat or lock-safety guidance `[CITED: pyrekordbox.readthedocs.io/en/latest/formats/db6.html]`. Secondary research reports the key auto-extraction broke at Rekordbox ≥ 6.6.5 (Pioneer obfuscated `app.asar`), requiring a fragile `download-key` cache `[CITED: STACK.md §pyrekordbox, MEDIUM]`.
- **Lock-safety while RB runs is NOT proven.** No authoritative source confirms concurrent read is safe; prior research flagged live-session file locks `[CITED: PITFALLS Pitfall 5]`.
- **Write-corruption landmine.** Any write corrupts the user's collection (locked memory `project_vibe_mix_bravoh_prep_module`).
- **The codebase actively forbids it** — activating it means tearing down the grep-gate, the dormancy test, and the wheel exclusion, all of which exist precisely to keep this path dead.

**Concrete recommendation:** XML-export primary, full stop. If a future milestone wants live-DB, it must be a *separate, opt-in, best-effort-on-temp-copy, never-default, never-write* path with its own spike — out of scope here.

## Spike 2 — Gemini-vision deck-badge read: gated re-enable of a deliberately-disabled path

**RESOLUTION: Vision is the universal-fallback leg, but it requires re-enabling a path the codebase deliberately killed for hallucination. Treat it as an eval-gated sub-task, not a one-line flip. Cadence: only on track-change/screen-change. Reliability: UNVERIFIED — the plan MUST include a real-screenshot accuracy eval as a task.**

### The load-bearing constraint the milestone research missed
`dj_cohost.py:546-553` sets `screen_jpeg = None` with the comment **"Single-modality: audio only. Screen + MIDI metadata caused hallucination."** The screen Part is currently NOT sent to Gemini at all. The infrastructure exists (`self._screen_buf`, `CapturedFrame.jpeg`, the `types.Part.from_bytes(...)` append site, a `skip_screen` / `SCREEN_SKIP_EVENTS` pre-wiring) but the v4 anti-hallucination invariant disables it `[VERIFIED: dj_cohost.py:546-553 + 83-88]`.

**Implication:** the vision deck-read is NOT "extend the prompt we already send" (as ARCHITECTURE.md assumed) — it is "**re-introduce a vision Part that was removed because it caused hallucination**, scoped narrowly to a structured deck-read, behind its own eval gate." This is the single biggest risk in the phase.

### Recommended shape (de-risked vision read)
- **Separate, structured request — NOT the main reaction turn.** Run the deck-read as a *dedicated* low-frequency Gemini call (its own prompt + structured-output schema), not by re-attaching the screenshot to the reaction prompt that was specifically de-screened. This keeps the anti-hallucination invariant on the reaction path intact while letting a *constrained* vision call populate deck-state.
- **Structured output:** request JSON, e.g. `{"decks":[{"side":"A","title":"...","key":"8A","bpm":128},{"side":"B",...}]}` with an explicit "if a field is not clearly visible, return null" instruction. Map nulls → `confidence=0` / `unknown`. The constrained schema is what closes the free-text hallucination class that killed the original screen Part.
- **Cadence (cost bound):** trigger only on (a) a track-change signal, or (b) a detected screen-change since last read — never per 10Hz tick. CONTEXT locks "vision read only on a track-change signal / screen-change". A reasonable default: debounce to at most ~1 read / 5-10s, and skip entirely when audio-only tier (no decks visible). `[ASSUMED — A2: exact cadence numbers set at plan time against the Gemini cost budget]`
- **Confidence:** vision-sourced keys carry LOWER confidence than XML-matched keys (a misread badge is a silent error, same class as a wrong library tag). Gate `key:` citation on the higher floor for vision than for XML. `[ASSUMED — A3]`

### Reliability across djay/Serato/Traktor UI themes
**UNVERIFIED — no live-screenshot eval has been run.** Badge placement, font, contrast, and key-notation form (Camelot vs musical vs open-key) vary across apps and themes; dark-mode + busy waveforms degrade OCR-style reads. Milestone research rated this MEDIUM with "no live-hardware confirmation" `[CITED: STACK.md confidence note]`.

**The plan MUST include a task:** assemble a small corpus of real screenshots (djay Pro, Serato, Traktor at minimum; light + dark themes) and measure Gemini's deck-title + key/BPM extraction accuracy. Set the vision-confidence floor from that measurement. If accuracy is poor on a target app, that app degrades to XML-or-unknown — never a guessed badge. This is a KAAN-ACTION-adjacent eval (Kaan can supply screenshots from his real rig). `[CITED: SUMMARY.md Research Flags + CONTEXT specifics (c)]`

## Spike 3 — `key:` evidence source: concrete grammar + linter rule

**RESOLUTION: Add a dedicated `key:` source. Existence-only (skip timestamp tolerance, like `track:`). Body shape `key:<deck>:<camelot>`. This resolves the ARCHITECTURE↔PITFALLS divergence in favor of PITFALLS/CONTEXT.**

### Why a dedicated source (not `mix:` reuse)
A harmonic clash is a **relational, per-deck, per-moment** claim the existing 7-source grammar never anticipated. Reusing `mix:` (existence-only) would let a fabricated `[mix:deck_A_key=12B]` slip through whenever *any* `deck_A_key=...` exists in the registry, because `mix:` validation is a bare key-presence check. A dedicated `key:` source with a deck:camelot body makes a hallucinated clash uncitable-by-construction: the exact `key:A:12B` atom must have been written by the poller, or the linter strips the turn `[CITED: PITFALLS Pitfall 1 + CONTEXT lock]`.

### Concrete EBNF / regex additions
The grammar lives in `evidence_registry.py`. Current source list: `{ev, aud, midi, track, screen, mix, tend}` `[VERIFIED: evidence_registry.py:95]`. Additions:

```python
# evidence_registry.py — add "key" to the frozenset
EVIDENCE_SOURCES: frozenset[str] = frozenset(
    {"ev", "aud", "midi", "track", "screen", "mix", "tend", "key"}
)

# add to the regex alternation (line 104) — body still excludes whitespace/comma/]
_SOURCE_ALT = "ev|aud|midi|track|screen|mix|tend|key"
# _INNER_ATOM regex is UNCHANGED — `key:A:8A` matches `(?:...|key):[^\s,\]]+`
# because the body `A:8A` contains no whitespace/comma/bracket. The colon inside
# the body is fine: parse_citations splits on the FIRST `:` only, so
# parse_citations("[key:A:8A]") -> [("key", "A:8A")]  (verified against partition logic)
```

Updated EBNF (documentation):
```
citation := '[' atom ( ',' atom )* ']'
atom     := source ':' body
source   := 'ev' | 'aud' | 'midi' | 'track' | 'screen' | 'mix' | 'tend' | 'key'
body     := one-or-more chars excluding whitespace, ']', ','
key-body := <deck> ':' <camelot>     # e.g. "A:8A" — deck ∈ {A,B,C,D}, camelot ∈ 1A..12B
```

### Linter rule (existence-only, skip timestamp tolerance)
`citation_linter.py` splits sources into time-keyed (`{ev, aud, midi}` — body is `key@t`, looked up with tolerance) vs existence-only (`{track, screen, mix, tend}` — bare presence check) `[VERIFIED: citation_linter.py:45 + _validate_atom:191-205]`.

**`key` joins the existence-only set** (mirror `track:`): it must NOT be added to `_TIME_KEYED_SOURCES`. Then `_validate_atom`'s final branch (`valid = body in snapshot.get(source, {})`) validates `key:A:8A` by exact-body presence — the poller registers `registry.write("key", f"{side}:{camelot}", t_session)` and the linter confirms that exact `A:8A` body was observed. A hallucinated `12B` body that was never written → not in snapshot → atom invalid → whole turn stripped. **No code change to `_validate_atom` beyond `key` being in `EVIDENCE_SOURCES` and absent from `_TIME_KEYED_SOURCES`.** `[VERIFIED: citation_linter.py logic trace]`

### Registry write site (inside `_tick_once` lock batch)
```python
# refresh.py _tick_once — inside `with state._lock:`, after deck_snap is copied
if evidence_registry is not None:
    for side, dt in state.deck_state.decks.items():
        if dt.confidence >= DECK_CITE_MIN_CONF and dt.camelot:
            try:
                t_session = max(0.0, now - state.set_start_at)
                evidence_registry.write("key", f"{side}:{dt.camelot}", t_session)
                if dt.track_id:
                    evidence_registry.write("track", dt.track_id, t_session)
            except Exception:
                pass
```
Change-only or per-tick? Mirror the `mix:audible_deck` change-only pattern (write only when a deck's `(side, camelot)` changes) to keep the registry bounded `[CITED: refresh.py:441 change-only pattern]`. `[ASSUMED — A4: DECK_CITE_MIN_CONF value set at plan time]`

**Schema-mirror touchpoints:** the `key:` grammar appears in (1) `EVIDENCE_SOURCES`, (2) `_SOURCE_ALT` regex, (3) the EBNF docstring, (4) the prompt-side `CITATION_GRAMMAR_BLOCK` in `prompts/matrix.py` (so the LLM is taught it can cite `[key:A:8A]`), (5) any IPC/citation-strip whitelist that turns atoms into UI chips (`dj_cohost.py` `_build_citation_strip` — `key:` should yield a chip like `mix:`/`ev:` do). The plan must touch all five in lock-step (PITFALLS "schema-mirror" gotcha). `[CITED: ARCHITECTURE anti-pattern table]`

## Spike resolution — event types (plumbing only, firing is Phase 60)

Add to `event.py::EVENT_PRIORITY` (current map verified: MANUAL/DROP=10, KAAN_SPOKE=9, TRACK_CHANGE=7, PHASE=6, MIX_MOVE/DISTORTION_CLIMB/ACID_LINE_ENTRY=5, LAYER_ARRIVAL=4, HEARTBEAT=1) `[VERIFIED: event.py:32-46]`:
```python
    "KEY_CLASH": 7,               # tie with TRACK_CHANGE — a clashing overlay is "react now"
    "TRANSITION_OPPORTUNITY": 5,  # tie with MIX_MOVE — structural, not urgent
```
Add to `audio/constants.py::MIN_EVENT_GAP_PER_TYPE` (current map verified: TRACK_CHANGE=5, PHASE=10, MIX_MOVE=14, HEARTBEAT=45, etc.) `[VERIFIED: constants.py:77-115]`:
```python
    "KEY_CLASH": 28.0,             # long gap — a clash persists; re-arm only after it clears+recurs (~25-30s band)
    "TRANSITION_OPPORTUNITY": 20.0,  # medium — fires at the moment a blend COULD start, not continuously
```
Both inherit the `EVENT_GLOBAL_MIN_GAP=22.0` floor via `_cooldown_ok` — no gate-logic change `[VERIFIED: event_detector.py:124-127]`. **This phase registers the types + cooldowns ONLY. No detector branch, no `task_for_event` firing logic — those are Phase 60.** The `__post_init__` priority default + the `EVENT_PRIORITY.get(type, 0)` fallback mean an unregistered type would silently get priority 0; registering them now is the plumbing. `[ASSUMED — A5: exact 28/20 cooldown numbers; tune at Phase 60]`

## Common Pitfalls

### Pitfall 1: Treating Rekordbox `Tonality` as Camelot
**What goes wrong:** Citing `key:A:Am` and asking the LLM to reason on it as a Camelot code.
**Why:** The XML carries musical notation (`Am`, `F#m`), confirmed in the fixture — not `8A`.
**How to avoid:** `harmonics.to_camelot()` normalizes raw tag → Camelot before any citation/event. `DeckTrack.key` keeps the raw tag; `DeckTrack.camelot` is what gets cited.
**Warning signs:** `key:` citations with letter-name bodies; `to_camelot` raising on an empty/odd tag instead of returning `None`.

### Pitfall 2: Re-enabling the screen Part as a one-line flip
**What goes wrong:** Changing `screen_jpeg = None` to live re-introduces the exact hallucination class v4 removed it for.
**Why:** The line is a deliberate kill-switch ("Screen + MIDI metadata caused hallucination").
**How to avoid:** Vision deck-read is a *separate, structured-output, low-frequency* call — not a screenshot re-attached to the reaction turn. Eval-gate it (Spike 2).
**Warning signs:** The reaction prompt regains a screen Part; deck reads run per-tick; vision keys cited at XML-confidence.

### Pitfall 3: Poller writes `MusicState` directly
**What goes wrong:** Single-writer violation → torn snapshots for read-only consumers.
**Why:** The poller runs on its own cadence (executor); writing `MusicState` outside `_tick_once` races the 10Hz writer.
**How to avoid:** Poller writes its own holder; `_tick_once` copies `deck_source.snapshot()` into `state.deck_state` inside `with state._lock:` — the third such external source after `ControllerState`/`TrackInfo` `[VERIFIED: refresh.py:427-460 pattern]`.
**Warning signs:** `state.deck_state.decks = ...` anywhere outside `refresh.py`.

### Pitfall 4: Cross-deck claim on an unresolved second deck
**What goes wrong:** The clash/transition logic (Phase 60) cites a deck the registry never independently saw → false clash.
**Why:** `derive_audible_deck` returns `none`/`mix` often (FLX4 play-state desync); the silent deck is hard to resolve.
**How to avoid:** Poller sets `confidence=0` on any deck not independently confirmed; `key:` write gated on `confidence >= DECK_CITE_MIN_CONF`. No write → no citation → linter strips → degrade to single-deck `[CITED: PITFALLS Pitfall 4]`.
**Warning signs:** Second deck resolved by "most recent now-playing title"; `key:` citations for a deck at `confidence < floor`.

### Pitfall 5: Golden-equivalence break from non-additive `MusicState` change
**What goes wrong:** Snapshot/prompt goldens flip because a default-non-empty deck field changes serialized output.
**Why:** `evidence_line`/snapshot tests assert v4 byte-identity until a field is populated.
**How to avoid:** `deck_state: DeckState = field(default_factory=DeckState)` (empty `decks={}` → no output until populated); the `evidence_line` deck block must be conditional on a resolved deck, exactly like the existing `track=unknown`/registry-footer gates `[VERIFIED: coach.py:133 gate pattern]`.
**Warning signs:** Hype/coach prompt goldens needing updates "just to pass".

## Code Examples

### Camelot normalization (the load-bearing pure function)
```python
# state/harmonics.py — NEW. Deterministic table; accepts musical / Camelot / open-key input.
# Phase 60 consumes is_clash/compatible on top of this; Phase 59 ships to_camelot only.
# Source: Camelot wheel canonical mapping [CITED: mixedinkey.com/camelot-wheel + dj.studio/blog/camelot-wheel]
_MUSICAL_TO_CAMELOT = {
    # minors (inner wheel, "A")
    "Abm": "1A", "G#m": "1A", "Ebm": "2A", "D#m": "2A", "Bbm": "3A", "A#m": "3A",
    "Fm": "4A", "Cm": "5A", "Gm": "6A", "Dm": "7A", "Am": "8A", "Em": "9A",
    "Bm": "10A", "F#m": "11A", "Gbm": "11A", "C#m": "12A", "Dbm": "12A",
    # majors (outer wheel, "B")
    "B": "1B", "F#": "2B", "Gb": "2B", "Db": "3B", "C#": "3B", "Ab": "4B", "G#": "4B",
    "Eb": "5B", "D#": "5B", "Bb": "6B", "A#": "6B", "F": "7B", "C": "8B",
    "G": "9B", "D": "10B", "A": "11B", "E": "12B",
}
_CAMELOT_RE = __import__("re").compile(r"^(1[0-2]|[1-9])[AB]$")

def to_camelot(raw: str | None) -> str | None:
    """Normalize a key tag (musical 'Am' / Camelot '8A' / open-key '1m') to Camelot.
    Returns None on empty/unrecognized — NEVER raises (degrades to key=unknown)."""
    if not raw:
        return None
    s = raw.strip()
    if _CAMELOT_RE.match(s.upper()):           # already Camelot
        return s.upper()
    if s in _MUSICAL_TO_CAMELOT:               # musical notation
        return _MUSICAL_TO_CAMELOT[s]
    # open-key ("1m"/"1d") → Camelot handled here too; table omitted for brevity
    return None
```

### `_tick_once` deck wiring (single-writer batch)
```python
# refresh.py _tick_once — inside `with state._lock:`, alongside the controller/track block
deck_snap = deck_source.snapshot()           # read-only producer, no lock contention
for side, dt in deck_snap.items():
    dt.camelot = harmonics.to_camelot(dt.key)  # pure fn, µs cost — safe inside the lock
state.deck_state.decks = deck_snap
state.deck_state.updated_at = now
# ... then the change-only key:/track: registry writes (Spike 3) ...
```

### `evidence_line` deck block (DECK-01 — coach sees decks the grounded way)
```python
# coach.py evidence_line — additive block, gated on a resolved deck (mirrors track=unknown)
resolved = {s: d for s, d in state.deck_state.decks.items()
            if d.camelot and d.confidence >= 0.3}
if resolved:
    parts = [f"{s}={d.title!r} {d.camelot} {d.bpm:.0f}bpm" for s, d in sorted(resolved.items())]
    e.append("decks[" + " | ".join(parts) + "]")
else:
    e.append("decks=unknown")   # honest unknown — extends the existing discipline
```

## Runtime State Inventory

> This phase is **read-only and additive** — it creates new state, does not rename/migrate existing state.
> The relevant question is the inverse: *does this phase touch anything that lives outside the repo?*

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | RekordboxLibrary pickle cache at `~/.cache/vibemix/library.pkl` — already exists, READ-only here | None — read existing cache; never write the DJ DB |
| Live service config | Rekordbox `collection.xml` path (user-supplied via Phase 25 wizard) — READ-only | None — reuse existing wizard import path; no new config surface |
| OS-registered state | None | None — verified: no OS registrations touched (no Task Scheduler / launchd / pm2) |
| Secrets/env vars | `GEMINI_API_KEY` (vision call), `OPENROUTER_API_KEY` (existing) — used, not changed | None — existing keys, no new env var names |
| Build artifacts | None new — `harmonics.py`/`deck_state.py`/`deck_poller.py` are new source, compiled on next run | None — `uv run` picks them up; no egg-info/package rename |

**The canonical question for this phase:** *Does anything write to a DJ-software database?* Answer: **NO — and a repo test must assert it (DECK-05).** See Validation Architecture.

## State of the Art

| Old Approach (assumed in milestone research) | Current Reality (verified in code) | Impact |
|--------------|------------------|--------|
| "Extend the screenshot prompt we already send to Gemini" | The screen Part is `None` — vision was DISABLED in v4 for hallucination | Vision is a *re-enable behind an eval gate*, not an extension. Biggest phase risk. |
| Rekordbox `Tonality` is Camelot-adjacent | `Tonality` is musical notation (`Am`/`F#m`) in the fixture | `to_camelot()` is mandatory before any `key:` citation |
| `mix:` reuse might suffice (ARCHITECTURE) | CONTEXT locked dedicated `key:` | New source + grammar + linter line + prompt-block + chip-whitelist (5 touchpoints) |
| pyrekordbox live-DB is "PRIMARY metadata oracle" (STACK TL;DR) | Codebase bans it (grep-gate + dormancy test + wheel exclusion); XML is the wired path | XML-export is the only sanctioned path; live-DB out of scope |

**Deprecated/outdated:**
- The STACK.md TL;DR row recommending live `Rekordbox6Database` read as primary is **superseded** by the CONTEXT lock and the codebase's active ban. Use XML.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `to_camelot()` must handle musical/Camelot/open-key input forms (some exports omit `Tonality`) | Spike 1 | If an export uses a form not handled → silent `key=unknown` for those tracks (safe-fail, but reduces coverage) |
| A2 | Vision read cadence ~1/5-10s, debounced on track/screen-change | Spike 2 | Too frequent → Gemini cost overrun; too rare → stale deck-state. Plan-time tunes against budget |
| A3 | Vision-sourced keys carry lower confidence than XML-matched keys | Spike 2 | If set wrong, vision misreads could cite at high confidence → false clash (Phase 60) |
| A4 | `DECK_CITE_MIN_CONF` confidence floor for `key:` write (suggest ~0.6, mirror `audible_track_confidence` 0.5 gate) | Spike 3 | Too low → cites uncertain keys; too high → feature feels dead. Tune at plan time |
| A5 | KEY_CLASH cooldown 28s, TRANSITION_OPPORTUNITY 20s | Event plumbing | Plumbing only this phase; real tuning is Phase 60 with Kaan-ear |
| A6 | Numpy KS/Temperley estimator is build-deferrable if XML+vision cover the live test set | Don't Hand-Roll | If both upstream legs fail on Kaan's rig, fallback becomes load-bearing sooner |

**If this table looks long:** all six are Claude's-Discretion tuning values explicitly delegated by CONTEXT, plus the vision-reliability unknown that the eval task resolves. None contradict a locked decision.

## Open Questions

1. **Does Kaan's real rig expose a readable second-deck badge to Gemini-vision?**
   - What we know: djay Pro is the primary app; FLX4 desyncs play-state; vision is the only universal second-deck identity source.
   - What's unclear: whether the silent/cued deck's key badge is reliably visible+readable in his actual djay layout.
   - Recommendation: the vision eval task uses *his* screenshots; if the second deck isn't reliably readable, cross-deck claims degrade to single-deck (DECK-05) and the harmonic feature waits for XML-resolved both-deck cases — which is the conservative-by-design path anyway.

2. **Should the numpy KS estimator ship in Phase 59 or defer to Phase 60?**
   - What we know: it's fallback-only, fires only when no tag/badge yields a key, zero-dep.
   - What's unclear: whether the XML+vision ladder already covers Kaan's library coverage.
   - Recommendation: scaffold `harmonics.to_camelot` + the `DeckTrack.source="numpy_key"` slot in Phase 59 (cheap), but the estimator *implementation* can be a small task gated on the live test showing real "no-tag" gaps. Keep it in scope but low-priority within the phase.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pyrekordbox | XML deck-state primary | ✓ | 0.4.4 | — (already pinned) |
| numpy | KS key estimator + deck DSP | ✓ | 2.4.4 | — |
| scipy | FFT/resample for KS | ✓ | 1.17.1 | — |
| Essentia | (rejected) | ✗ | — | numpy KS estimator (intended) |
| librosa | (rejected) | ✗ | — | numpy KS estimator (intended) |
| Gemini API (vision) | Universal vision fallback | ✓ (key in `.env`) | google-genai | XML-or-unknown if vision unavailable/unreliable |
| `mss`/Quartz screen capture | Vision badge capture | ✓ | installed | XML-only tier if screen unavailable |
| `nowplaying-cli` (mac) | Audible-track anchor | ✓ (Homebrew) | — | mac-only; degrades on Windows (SMTC) |

**Missing dependencies with no fallback:** none — every required dep is present.
**Missing dependencies with fallback:** Essentia/librosa absent by design → numpy KS estimator is the intended path.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`addopts = "-ra --strict-markers"`) |
| Quick run command | `PYTHONPATH=src python3 -m pytest tests/state/ -q` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (or `uv run pytest -q`) |

Default run skips opt-in markers (`macos_audio`, `integration`, `slow`, `e2e`, `cli`, `network`, `windows_only`). The deck-state spine is pure-Python and runs in the default fast suite.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DECK-01 | `MusicState.deck_state` populated + surfaced in `evidence_line` decks block | unit | `pytest tests/state/test_deck_state.py -x` | ❌ Wave 0 |
| DECK-01 | Golden-equivalence: empty `deck_state` keeps `evidence_line` byte-identical | unit (regression) | `pytest tests/state/test_coach_prompt_grounding.py -x` | ✅ (extend) |
| DECK-02 | Source ladder: XML match > vision > numpy; honest `unknown` below floors | unit | `pytest tests/state/test_deck_poller.py -x` | ❌ Wave 0 |
| DECK-02 | `to_camelot("Am")=="8A"`, `to_camelot("F#m")=="11A"`, `to_camelot("")` is None | unit | `pytest tests/state/test_harmonics.py -x` | ❌ Wave 0 |
| DECK-03 | `"key"` in `EVIDENCE_SOURCES`; `parse_citations("[key:A:8A]")==[("key","A:8A")]` | unit | `pytest tests/state/test_evidence_registry.py -k key -x` | ✅ (extend) |
| DECK-03 | Linter STRIPS a fabricated `[key:A:12B]` not in registry; ACCEPTS a registered one | unit | `pytest tests/coach/test_citation_linter.py -k key -x` | ✅ (extend) |
| DECK-03 | `key` is existence-only (NOT in `_TIME_KEYED_SOURCES`) — no `@t` required | unit | `pytest tests/coach/test_citation_linter.py -k existence -x` | ✅ (extend) |
| DECK-04 | `KEY_CLASH`/`TRANSITION_OPPORTUNITY` in `EVENT_PRIORITY` + `MIN_EVENT_GAP_PER_TYPE` | unit | `pytest tests/state/test_event.py tests/audio/test_constants.py -x` | ✅ (extend) |
| DECK-04 | Single-writer: deck-state only mutated inside `_tick_once`; poller writes own holder | unit | `pytest tests/state/test_refresh_deck.py -x` | ❌ Wave 0 |
| DECK-05 | **Read-only repo assertion: no DJ DB opened in write mode** (extend the SQLCipher-dormancy idiom) | repo/subprocess | `pytest tests/repo/test_repo_scrub.py -k deck_readonly -x` AND `tests/library/test_rekordbox.py::test_no_sqlcipher_module_imported_after_load` | ✅ (extend) + ❌ Wave 0 |
| DECK-05 | Cross-deck suppression: 2nd-deck `confidence<floor` → no `key:` write → no citation possible | unit | `pytest tests/state/test_deck_poller.py -k suppress -x` | ❌ Wave 0 |

### Anti-slop guarantees (observable tests)
- **Citable key:** a fabricated `[key:A:12B]` the poller never wrote is STRIPPED by `CitationLinter.check` (binary response-level) — the headline grounding guarantee, testable without a live session.
- **Honest `unknown`:** below the confidence floor, `evidence_line` prints `decks=unknown` and no `key:` observation is written — assertable on a low-confidence fixture state.
- **Read-only:** a repo test asserts no `Rekordbox6Database`/`sqlite3 ... write`/`.commit()` against any DJ DB; the existing subprocess dormancy test (`*sqlcipher* == DORMANT`) is the proven idiom to extend.
- **Cross-deck suppression:** a fixture with deck A resolved + deck B unresolved produces zero deck-B `key:` writes → Phase 60's clash cannot cite deck B.

### Sampling Rate
- **Per task commit:** `PYTHONPATH=src python3 -m pytest tests/state/ tests/coach/ -q`
- **Per wave merge:** full suite `uv run pytest -q` (must be green; includes the golden-equivalence + repo-scrub gates)
- **Phase gate:** full suite green + the DECK-05 read-only assertion green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/state/test_harmonics.py` — `to_camelot` correctness (musical/Camelot/open-key/empty) — covers DECK-02
- [ ] `tests/state/test_deck_state.py` — `DeckState`/`DeckTrack` defaults + additive-field golden-equivalence — covers DECK-01
- [ ] `tests/state/test_deck_poller.py` — source ladder ordering, confidence gating, cross-deck suppression — covers DECK-02/05
- [ ] `tests/state/test_refresh_deck.py` — `_tick_once` single-writer copy + change-only `key:`/`track:` registry writes — covers DECK-04
- [ ] `tests/repo/test_repo_scrub.py::test_deck_readonly` (new case) — no DJ-DB write-mode open — covers DECK-05
- [ ] Extend `tests/state/test_evidence_registry.py` + `tests/coach/test_citation_linter.py` for the `key:` source/grammar/strip — covers DECK-03
- [ ] Extend `tests/state/test_event.py` + `tests/audio/test_constants.py` for the two new event types — covers DECK-04
- [ ] (deferred-decision) vision-eval harness task — real-screenshot accuracy pass for the Gemini deck-read (Spike 2); KAAN-ACTION corpus

## Security Domain

> `security_enforcement` is not explicitly false in config — included. This phase is local-only,
> read-only, no network ingress beyond the existing Gemini calls.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No new auth; Gemini key already managed (Bravoh-proxy model) |
| V3 Session Management | no | Local single-machine app, no sessions |
| V4 Access Control | no | No new access surface |
| V5 Input Validation | yes | `to_camelot` validates/degrades key tags (never raises); `_safe_get` already defends XML schema drift; vision JSON parsed defensively (null→unknown) |
| V6 Cryptography | no (and deliberately so) | **Do NOT touch SQLCipher** — the live-DB encryption path stays banned; never bundle/extract a key |

### Known Threat Patterns for {Python sidecar + DJ-library + Gemini-vision}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Write to user's `master.db`/collection (corruption) | Tampering | Read-only always; repo test asserts no write-mode open (DECK-05) |
| Bundling/extracting the SQLCipher key (EULA grey zone) | Tampering/Repudiation | XML-export only; SQLCipher path stays dormant + grep-gated |
| Hallucinated key/clash claim (false expertise) | Spoofing (of grounded fact) | `key:` source + linter strip; deterministic Camelot; conservative confidence gate (Phase 60) |
| Library data exfiltration | Information Disclosure | Library stays local; only derived deck-state (titles/keys) reaches Gemini, never the raw collection file |
| Vision-call cost runaway (DoS-on-budget) | Denial of Service (budget) | Cadence-bounded vision read (track/screen-change only); audio-only tier skips vision entirely |

## Sources

### Primary (HIGH confidence)
- Live code on branch `live-tuning-or-brain` (read directly):
  - `src/vibemix/state/{music_state,event,event_detector,refresh,coach,track_resolver,evidence_registry}.py`
  - `src/vibemix/coach/citation_linter.py`, `src/vibemix/audio/constants.py`, `src/vibemix/audio/features.py`
  - `src/vibemix/library/rekordbox.py`, `src/vibemix/agent/dj_cohost.py`, `src/vibemix/platform/screen.py`
  - `src/vibemix/__main__.py` (register_library wiring), `pyproject.toml`
  - `tests/library/test_rekordbox.py` (SQLCipher dormancy idiom), `tests/library/fixtures/synthetic_collection.xml` (KEY FORMAT verified: `Tonality="Am"`)
- Installed venv verification: pyrekordbox 0.4.4, numpy 2.4.4, scipy 1.17.1, Essentia/librosa ABSENT
- `.planning/research/{SUMMARY,STACK,ARCHITECTURE,PITFALLS}.md` (4-agent convergent milestone research)
- `.planning/phases/59-.../59-CONTEXT.md`, `.planning/REQUIREMENTS.md`, CLAUDE.md, MEMORY.md

### Secondary (MEDIUM confidence)
- [pyrekordbox db6 docs](https://pyrekordbox.readthedocs.io/en/latest/formats/db6.html) — SQLCipher key required, local-but-unspecified acquisition (confirms live-DB is gated)
- [pyrekordbox PyPI](https://pypi.org/project/pyrekordbox/) — v0.4.4, 2025-08-17
- Camelot conversion: [Mixed In Key Camelot Wheel](https://mixedinkey.com/camelot-wheel/), [DJ.Studio Camelot Wheel](https://dj.studio/blog/camelot-wheel), [regorxxx Camelot-Wheel-Notation](https://github.com/regorxxx/Camelot-Wheel-Notation) (notation↔Camelot mapping)

### Tertiary (LOW confidence)
- Key-tag accuracy band (~57-70%) and post-6.6.5 SQLCipher obfuscation — multiple agreeing secondary sources, no single authoritative benchmark (carried from milestone PITFALLS.md)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep verified present/absent against the venv; no new installs
- Architecture / integration: HIGH — read directly against branch source; every edit site line-anchored
- Spike 1 (pyrekordbox XML): HIGH — XML path + grep-gate + dormancy test + key format all verified in code/fixture
- Spike 2 (Gemini-vision): MEDIUM — infrastructure verified, but the path is currently DISABLED and reliability is UNVERIFIED (eval task required)
- Spike 3 (`key:` source): HIGH — grammar/linter changes traced against actual regex + `_validate_atom` logic
- Pitfalls: HIGH — codebase- and CONTEXT-verified; key-accuracy numbers MEDIUM (carried)

**Research date:** 2026-05-21
**Valid until:** 2026-06-20 (stable codebase; re-verify if `live-tuning-or-brain` merges or pyrekordbox bumps)
