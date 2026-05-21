# Phase 59: Full Deck Awareness + Grounding - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous `fully` — recommended grey-area answers auto-accepted; technical spikes routed to plan-time research)

<domain>
## Phase Boundary

This phase lands the **spine** of v5.0: a grounded, session-wide **deck-state** — every track currently loaded across the decks (title, key, BPM, energy where resolvable) — populated from a real data-source ladder, integrated into `MusicState` under the single-writer rule, and made **citable** so the harmonic feature (Phase 60) can be built on it.

**In scope:** the deck-state model + poller; the data-source ladder (pyrekordbox XML → Gemini-vision deck-read → numpy key estimator); the new `key:` evidence source + `CitationLinter` rule; embedding deck-state into `MusicState`; registering the `KEY_CLASH` + `TRANSITION_OPPORTUNITY` event *types* (priority/cooldown plumbing). Strictly read-only.

**Out of scope (later phases):** the actual clash *detection logic* + conservative confidence gate + Kaan-ear veto (Phase 60); the prescriptive coach persona that consumes deck-state (Phase 61); the pill UI (Phase 62). This phase delivers grounded *data + plumbing*, not the feedback itself.
</domain>

<decisions>
## Implementation Decisions

### Data-Source Ladder & Scope
- **Universal primary = Gemini-vision reading the deck panels** in the screenshot the co-host already captures — works for every DJ app (Rekordbox/Serato/djay/Traktor/Engine) with zero user setup; reads loaded-track title + key/BPM badge per visible deck.
- **High-fidelity enrichment = pyrekordbox via the exported XML** (the user points at a Rekordbox `collection.xml` / device export) — NOT the live `master.db`. This carries pre-computed key/BPM unencrypted and sidesteps the post-6.6.5 SQLCipher wall AND the `master.db` write-corruption landmine. Live-DB read is **deferred unless the plan-time spike proves it lock-safe while Rekordbox runs**.
- **Last-resort = in-house numpy Krumhansl-Temperley key estimator** (no Essentia/librosa — they are NOT installed; no CLAP/MERT). Used only when neither a tag nor an on-screen badge yields a key.
- **Scope of "all loaded tracks" = the currently-loaded track per deck** (2–4 decks). Full session/library history is future, not this milestone.
- **Per-deck metadata = title, musical key (Camelot + open-key), BPM, energy/confidence** where resolvable; surfaced honestly as `unknown` when not — never a false-confident guess.

### Grounding / Citation (must land BEFORE any harmonic prompt)
- **Dedicated `key:` evidence source + linter rule** (resolves the ARCHITECTURE↔PITFALLS divergence in favor of a new source). Harmonic claims are uncitable-by-construction today (`EVIDENCE_SOURCES` has no key/harmonic source); without this the anti-slop strip can't catch a false clash.
- Citation body shape ≈ `key:<deck>:<camelot>` plus the track ref; **skip the timestamp-tolerance check for library-sourced keys** (mirror how the existing `track:` source is treated). Exact EBNF/grammar finalized at plan time.
- Each deck-track carries `{source, confidence}`; below threshold → `unknown`. The LLM may never assert a key the source did not provide.

### State Integration (single-writer preserved)
- New `DeckState` / `DeckTrack` dataclass in **`state/deck_state.py`**, **embedded as a field of `MusicState`** (per ARCHITECTURE.md — zero read-side signature churn; consistency under the existing `state._lock`).
- A **read-only deck poller** writes its own holder + `.snapshot()` (same pattern as `ControllerState` / `TrackInfo`); **`_tick_once` is the ONLY thing that copies it into `MusicState`**, inside the existing lock block.
- Register `KEY_CLASH` (priority ~7, ~25–30s cooldown) + `TRANSITION_OPPORTUNITY` (priority ~5, ~20s) in `EVENT_PRIORITY` / `MIN_EVENT_GAP_PER_TYPE`. **This phase wires the event *types* + plumbing; the firing logic is Phase 60.**
- Existing snapshot golden-equivalence preserved (additive-only fields).

### Failure / Degradation / Safety
- **Tiered graceful degradation to `unknown`** — when no source resolves, the feature stays silent rather than guessing.
- **Strictly read-only** — a repo test asserts no DJ-software DB is ever opened in write mode; prefer the XML-export file over any live DB.
- **Cross-deck claims suppressed when the second (non-audible) deck cannot be independently resolved** — degrade to single-deck, never guess the other deck.
- Cross-platform: vision + XML + numpy paths are OS-agnostic (mac+win); `nowplaying-cli` stays mac-only current-track enrichment.
- **Deck-poll cadence bounded for cost** — vision read only on a track-change signal / screen-change (not every tick); XML parsed once per session / on file change. Plan-time sets exact cadence against the Gemini-vision cost budget.

### Claude's Discretion
- Exact `key:` citation EBNF, poll cadence numbers, confidence thresholds, and the deck→track resolution heuristic details — set at plan time from research + existing `track_resolver.py` / `derive_audible_deck` patterns.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/state/` — `MusicState` (single-writer dataclass), `state_refresh_loop._tick_once` (the only writer), `track_resolver.py` (`derive_audible_deck` + documented FLX4 play-state desync), `coach.py`.
- Grounding stack — `EvidenceRegistry` + `CitationLinter` + `EVIDENCE_SOURCES` set (currently `{ev, aud, midi, track, screen, mix, tend}` — no `key`); `track:` source is library-registered (Plan 25-02) and skips timestamp tolerance.
- Read-only snapshot producers to mirror — `ControllerState`, `TrackInfo` (own holder + `.snapshot()`, copied in `_tick_once`).
- `pyrekordbox` already a dependency (XML import path; SQLCipher path deliberately banned + grep-gated).
- Screen capture (`mss` + Quartz crop) already feeds Gemini — extend the prompt to read both deck panels.

### Established Patterns
- Single-writer `MusicState`; lock-protected batch in `_tick_once`; additive snapshot fields with golden-equivalence tests.
- Citation grounding: evidence must hit the registry before the LLM can cite it; `CitationLinter` does a binary response-level strip.
- "Trust the audio" / honest `unknown` over false confidence; one socket `ws://127.0.0.1:8765`.

### Integration Points
- `state/deck_state.py` (NEW) ← deck poller (NEW, read-only) → `_tick_once` copies into `MusicState.deck` field.
- `EVIDENCE_SOURCES` + linter grammar gain `key:`; `EVENT_PRIORITY` / `MIN_EVENT_GAP_PER_TYPE` gain the two new event types.
- Research: `.planning/research/{SUMMARY,STACK,ARCHITECTURE,PITFALLS}.md` (4-agent convergent).
</code_context>

<specifics>
## Specific Ideas

- Camelot wheel will be a **deterministic Python lookup table** (Phase 60 consumes it; this phase ensures the *key data* feeding it is grounded + citable).
- The "all loaded tracks" promise is bounded to **per-deck currently-loaded** — this is what "loaded in the deck" means to a DJ; it keeps scope tight and grounding tractable.
- Two plan-time spikes are mandatory: (a) pyrekordbox live-DB read safety + XML-primary confirmation; (b) Gemini-vision deck-badge accuracy across djay/Serato/Traktor UI themes on real screenshots.
</specifics>

<deferred>
## Deferred Ideas

- ProDJ Link / StagelinQ (`prolink-connect`) per-deck telemetry — hardware-gated, future.
- Live audio key-detection promoted to a primary source (cross-checked) — future; only the numpy fallback ships now.
- Per-deck low-band / bass-clash DSP from a single master stream — future (keeps bass-clash note P2).
</deferred>
