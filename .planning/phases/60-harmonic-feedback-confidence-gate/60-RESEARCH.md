# Phase 60: Harmonic-Feedback Confidence Gate — Research

**Researched:** 2026-05-21
**Domain:** Deterministic harmonic (Camelot-wheel) clash + transition-opportunity detection, conservative confidence gating, anti-slop suppression on a grounded local AI DJ co-host (vibemix v5.0)
**Confidence:** HIGH — this is a codebase-internal phase. Every integration point (`harmonics.to_camelot`, `event_detector.detect`, `coach.task_for_event`, the `key:` evidence source + `CitationLinter`, `MusicState.deck_state`, `phase.py`, the constants) was read directly. Camelot-wheel theory cross-verified against FEATURES.md (DJ-authoritative sources) AND re-derived deterministically from the circle of fifths (computation included below). The only MEDIUM items are the exact tuned thresholds (Kaan's discretion at plan time) and the ~57-70% key-tag accuracy band (multiple secondary sources agree, no single benchmark).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Deterministic Camelot Logic (the anti-slop core)**
- Camelot-wheel relationships are a **deterministic Python lookup table** in `harmonics.py` (extends the shipped `to_camelot`). `is_clash(a, b)` / `compatible(a, b)` are pure, unit-table-tested functions. **The LLM NEVER computes key intervals** — it only narrates a clash the code already confirmed, with both decks' keys cited (`[key:A:...]` + `[key:B:...]`).
- The wheel encodes: perfect match (same Camelot), adjacent (±1 number, same letter = energy ±; safe), relative major/minor (same number, swap A/B; safe), +7/−7 (5 hours around = perfect-fifth, reachable). A genuine **clash = the dissonant cases** (notably one-semitone-apart melodic overlap), NOT a one-step Camelot move.
- Critical theory rule: a one-step Camelot move (8A→9A) is SAFE; the disaster is two melodic tracks **a semitone apart overlapping**. Reason about *simultaneous melodic overlap*, not endpoint key.

**Suppression Gate (runs BEFORE any clash note fires)**
- **Percussive/atonal + breakdown suppression runs first.** No clash call on two drum/tool tracks, and none during a breakdown/acapella where keys don't matter. Require simultaneous **melodic** overlap in both decks above an energy floor with `audible_deck == "mix"` (both decks contributing).
- Reuse the existing phase/energy signals (`phase.py` semantics, the `PEAK_FLOOR_RMS` family) — do NOT invent a new detector stack.

**Conservative Confidence Gate (the headline risk control)**
- **Conservative by default.** Suppress: one-step-off-Camelot pairs (adjacent = safe), low-confidence keys (below the deck-cite floor from Phase 59), and ambiguous deck-resolution (cross-deck-suppression path — if the 2nd deck isn't independently resolved, no clash).
- Tuning **accounts for the ~57–70% library key-tag accuracy band** — when in doubt, stay silent. Under-flagging is acceptable; over-flagging (a false clash on a pair Kaan would happily mix) is the failure mode that trips the gate.
- **Ships only after a Kaan-ear veto** pass against his real disagreed-pairs corpus (the one human gate; conservative default = detector stays gated/quiet until validated).

**Transition-Execution Feedback**
- Concrete, actionable **blend notes** (EQ bass-swap, phrase alignment, where to start/end the blend), scoped strictly to what is grounded in deck-state. **Retrospective / past-tense** — no mid-blend present-tense imperatives.
- **No advice emitted when the underlying signals aren't available** (e.g. no phrase grid → no phrase-alignment note). Silence over a guess.
- Anti-features held: no next-track recommendation, no 1–10 transition scoring.

### Claude's Discretion
- Exact clash-confidence thresholds, the energy floor for "melodic content", the cooldown interplay with the Phase-59-registered values (KEY_CLASH 28s / TRANSITION_OPPORTUNITY 20s), and the Kaan-ear corpus format — set at plan time from research + the shipped `phase.py`/`event_detector.py` patterns.

### Deferred Ideas (OUT OF SCOPE)
- Per-deck low-band/bass-clash DSP (dual-deck separation from a single master stream) — future; the bass-clash note stays P2 until feasible.
- Live audio key-detection as a clash input — only the numpy fallback exists; promoting it is future.
- The actionable-not-hype *voice* refactor — Phase 61 (this phase produces grounded facts, not the persona).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARMONIC-01 | Camelot relationships as a deterministic Python lookup table; LLM only narrates a clash the **code already confirmed**, never computes intervals. | §1 (the exact `is_clash`/`compatible` predicate, derived + verified) + §4 (detector hands a pre-decided verdict to coach; LLM gets a cited fact, not a key-math task). |
| HARMONIC-02 | Clash fires **only on simultaneous melodic overlap** in clashing keys; percussive/atonal + breakdown **suppression gate** runs *before* any clash note. | §2 (the suppression predicate built ENTIRELY from shipped signals — `audible_deck=="mix"`, `phase`, RMS floors, `onset_density`, `vocal_active` — no new detector stack). |
| HARMONIC-03 | Conservative by default: suppress one-step-off-Camelot (adjacent = safe), low-confidence keys, ambiguous deck-resolution; tuned for the ~57-70% accuracy band; **Kaan-ear veto** before ship. | §3 (the conservatism gate composed from `DECK_CITE_MIN_CONF`, adjacency=safe, cross-deck suppression) + §6 (the Kaan-ear veto harness shape + ship-gated default). |
| HARMONIC-04 | Transition-execution feedback: concrete actionable blend notes scoped strictly to grounded deck-state; no advice when signals are unavailable. | §5 (the groundable-vs-not matrix — which blend notes deck-state supports today, which require signals we DON'T have → silent). |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Gemini-only.** No CLAP, no Essentia, no librosa-as-key-detector, no other LLM providers. Harmonic verdicts are pure Python; the LLM only narrates.
- **No scope creep / clean utility only.** No next-track recommendation, no 1-10 transition scoring, no headphone-cue analysis (all in REQUIREMENTS Out of Scope).
- **Grounded, never hallucinating, no AI slop.** A false clash is the single most credibility-destroying failure; conservative-by-default is mandatory.
- **Tests:** `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (or `uv run pytest -q`). Opt-in markers skipped by default.
- **GSD workflow enforcement:** changes flow through a GSD command; this phase is `/gsd:plan-phase` → execute.
- **Single-writer rule:** `state.deck_state.decks` is assigned ONLY in `refresh.py::_tick_once`. The detector READS `MusicState`, never writes deck-state.

---

## Summary

Phase 60 is a **pure-logic, codebase-internal phase** — no new dependencies, no new external services, no new evidence sources. Everything it needs already shipped in Phase 59: the `key:` evidence source + `CitationLinter` existence-only rule, `harmonics.to_camelot()`, `MusicState.deck_state` (per-deck camelot + confidence), the `KEY_CLASH` (priority 7, 28s cooldown) + `TRANSITION_OPPORTUNITY` (priority 5, 20s cooldown) event types registered in `EVENT_PRIORITY`/`MIN_EVENT_GAP_PER_TYPE`, and the two stub `task_for_event` arms in `coach.py`. Phase 60 fills the deferred slots: the deterministic `is_clash`/`compatible` predicate, the two detector branches in `event_detector.py`, the suppression + conservatism gates, the real (cited) harmonic task fragments, and the Kaan-ear veto harness.

The headline architectural call (HARMONIC-01) is **already locked by the codebase**: the clash math is deterministic Python and the LLM only narrates. I re-derived the exact predicate from the circle of fifths and verified it against the FEATURES.md theory — the critical "semitone-apart" disaster maps to a **Camelot same-letter number distance of exactly 5 or 7 hours** (which equals 1 semitone in pitch-class), while a one-step adjacent move (±1 hour) is a perfect fifth and SAFE. This is the single most important fact in the phase and it is computable in ~10 lines.

The dominant risk (HARMONIC-03) is a false clash from a wrong key tag (~57-70% library accuracy band) tripping Kaan's release gate. The mitigation is layered conservatism, all of it built from shipped signals: (1) the clash can only be CITED if both decks cleared `DECK_CITE_MIN_CONF=0.6` at write time (Phase 59 made a sub-floor deck uncitable-by-construction), (2) adjacent/relative/fifth pairs are classified SAFE and never fire, (3) `audible_deck=="mix"` + non-breakdown phase + above-floor RMS + tonal (low `onset_density`, not `vocal_active`) is required before a clash can even be considered, and (4) the detector ships **gated/quiet by default** until a Kaan-ear veto pass against his disagreed-pairs corpus.

**Primary recommendation:** Implement `is_clash`/`compatible` as a pure deterministic predicate in `harmonics.py` keyed on the Camelot same-letter hour-distance (clash band = {5, 7} hours = 1 semitone; safe = {0,1,2,7-as-fifth,relative}); wire `KEY_CLASH` + `TRANSITION_OPPORTUNITY` as two new branches in `EventDetector.detect()` placed AFTER `MIX_MOVE` and BEFORE the genre chain, each guarded by a `_melodic_overlap_gate(state)` helper composed from shipped signals; replace the two stub coach arms with cited harmonic fragments that the LLM only narrates; ship the detector behind a default-off `harmonic_clash_enabled` flag (mirroring `DeckPoller._vision_enabled`) that flips only after the Kaan-ear veto corpus passes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Camelot clash/compatible math | Pure logic (`state/harmonics.py`) | — | Deterministic, side-effect-free; the anti-slop core. Already scoped here by Phase 59's module docstring. |
| Melodic-overlap / breakdown suppression | State/detection (`state/event_detector.py` + reads `MusicState`) | `state/phase.py` (semantics) | Reuses shipped phase/energy/audible-deck signals; no new detector stack (locked decision). |
| Clash + transition event firing | State/detection (`state/event_detector.py`) | `state/event.py` (priorities, already registered) | Mirrors the existing `detect()` diff→Event pattern; cooldowns already in constants. |
| Confidence gating (cite-floor, cross-deck) | Already enforced upstream (`state/refresh.py` write site, Phase 59) | `state/event_detector.py` (reads `deck.confidence`) | The cite-floor is enforced at registry-write time; the detector layers adjacency + cross-deck checks on top. |
| Grounded harmonic narration fragment | Prompt/coach (`state/coach.py::task_for_event`) | `prompts/matrix.py` (grammar block already lists `[key:...]`) | LLM narrates a pre-decided verdict; never decides. Phase 61 sharpens the *voice*. |
| Citation strip of uncited harmonic claims | Already shipped (`coach/citation_linter.py`) | — | `key` is in the existence-only set; a fabricated `[key:A:12B]` the registry never saw strips the whole turn. No change needed. |
| Kaan-ear veto harness | Test/eval (`tests/state/` + a disagreed-pairs fixture) | runtime flag | The human gate; detector stays off until it passes. |

## Standard Stack

**No new packages.** This is a pure-Python logic phase on an existing codebase. The "stack" is the shipped vibemix modules:

### Core (all already present, read directly this session)
| Module | Role this phase | Status |
|--------|-----------------|--------|
| `src/vibemix/state/harmonics.py` | Add `is_clash` / `compatible` deterministic predicate on top of `to_camelot` | `to_camelot` shipped; predicate slot reserved by docstring (lines 15-17) |
| `src/vibemix/state/event_detector.py` | Add `KEY_CLASH` + `TRANSITION_OPPORTUNITY` branches + `_melodic_overlap_gate` helper | `detect()` pattern shipped; types not yet fired (`grep -c KEY_CLASH event_detector.py` → 0) |
| `src/vibemix/state/coach.py` | Replace the two stub `task_for_event` arms with cited harmonic fragments | stub arms present (lines 264-273) |
| `src/vibemix/state/deck_state.py` | READ `DeckTrack.camelot` / `.confidence` / `.source` | shipped, no change |
| `src/vibemix/state/event.py` | READ `EVENT_PRIORITY` (KEY_CLASH=7, TRANSITION_OPPORTUNITY=5) | registered Phase 59-03, no change |
| `src/vibemix/audio/constants.py` | READ `MIN_EVENT_GAP_PER_TYPE` (28s/20s) + `SILENT_RMS`/`LOW_RMS`/`PEAK_RMS` | registered, no change (tuning is discretion) |
| `src/vibemix/coach/citation_linter.py` | RELY ON existence-only strip of `key` source | shipped Phase 59, no change |
| `src/vibemix/state/track_resolver.py` | READ `derive_audible_deck` returns `"mix"` semantics | shipped, no change |

### Supporting (read for context, not modified)
| Module | Why relevant |
|--------|--------------|
| `src/vibemix/state/refresh.py` (lines 465-501) | The single-writer site that normalizes `camelot` and writes the change-only, confidence-gated `key:`/`track:` registry observations. The detector trusts that a deck with a `key:` observation cleared `DECK_CITE_MIN_CONF`. |
| `src/vibemix/state/evidence_registry.py` (lines 89-135) | The `key` source body grammar `<deck>:<camelot>` (e.g. `A:8A`); existence-only `has()` semantics. |
| `src/vibemix/prompts/matrix.py` (lines 117, 122-124) | `CITATION_GRAMMAR_BLOCK` already documents `[key:<deck>:<camelot>]`. The event-types-tracked list (line 124) currently OMITS `KEY_CLASH`/`TRANSITION_OPPORTUNITY` from `[ev:<TYPE>]` — see Open Question 1. |
| `src/vibemix/state/deck_poller.py` (lines 66-73, 280, 109-113) | `DECK_CITE_MIN_CONF=0.6`; the `_vision_enabled` default-off-flag pattern to mirror for the Kaan-ear ship gate. |

**Installation:** None.

## Package Legitimacy Audit

> Not applicable — this phase installs zero external packages. All work is in-repo Python against modules read and verified this session. No `npm`/`pip`/`cargo` additions.

## Architecture Patterns

### System Architecture Diagram

```text
                 ┌─────────────────────────────────────────────────────┐
                 │  refresh.py::_tick_once  (THE single writer, 10Hz)   │
                 │  - copies DeckPoller.snapshot() → state.deck_state   │
                 │  - normalizes dt.camelot = to_camelot(dt.key)        │
                 │  - writes [key:A:8A]/[key:B:7A] to EvidenceRegistry  │
                 │    ONLY when confidence ≥ DECK_CITE_MIN_CONF (0.6)   │  ← Phase 59
                 └───────────────────────┬─────────────────────────────┘
                                         │  reads (never writes)
                                         ▼
   MusicState  ──────────────────────────────────────────────────────────────┐
   { deck_state.decks{A:DeckTrack(camelot,confidence,source), B:...},          │
     audible_deck ∈ {A,B,mix,none}, phase, rms, bands, onset_density,          │
     vocal_active, recent_moves, bpm }                                         │
                                         │                                     │
                                         ▼                                     │
   ┌──────────────────── EventDetector.detect(state) ───────────────────┐      │
   │  KAAN_SPOKE > MANUAL > [music-truly-playing gate]                   │      │
   │   > TRACK_CHANGE > PHASE > LAYER_ARRIVAL > MIX_MOVE                  │      │
   │   ┌── NEW: KEY_CLASH branch ─────────────────────────────────┐      │      │
   │   │ 1. _melodic_overlap_gate(state)?  ───── NO ──► skip (§2)  │      │      │
   │   │      (audible_deck=="mix" AND not breakdown AND           │      │      │
   │   │       rms>floor AND tonal[low onset, not vocal])          │      │      │
   │   │ 2. both decks resolved + cited (conf≥floor)? NO ► skip    │ ◄────┼──────┘
   │   │ 3. is_clash(A.camelot, B.camelot)? (deterministic) NO►skip│      │
   │   │ 4. cooldown_ok(KEY_CLASH)? + harmonic_enabled flag        │      │
   │   │ ──► Event("KEY_CLASH", extra={a_cam,b_cam,a_side,b_side}) │      │
   │   └───────────────────────────────────────────────────────────┘      │
   │   ┌── NEW: TRANSITION_OPPORTUNITY branch (retrospective) ─────┐        │
   │   │  groundable-only blend note (§5); no clash; cooldown 20s  │        │
   │   └───────────────────────────────────────────────────────────┘        │
   │   > [genre-chain detectors] > HEARTBEAT                                  │
   └────────────────────────────────┬───────────────────────────────────────┘
                                     │  Event
                                     ▼
   coach.py::task_for_event(ev)  ──► builds a CITED narration instruction:
     "decks clash — A is [key:A:8A], B is [key:B:3A], 1 semitone apart.
      Tell Kaan to cut/kill, don't ride the pads."   (LLM narrates, never computes)
                                     │
                                     ▼
   LLM reply  ──► CitationLinter.check(text, registry_snapshot)
     - [key:A:8A] + [key:B:3A] must EXIST in registry → else STRIP whole turn
     - a fabricated [key:B:12B] the registry never saw → STRIPPED (anti-slop)
```

### Recommended Code Structure
```
src/vibemix/state/
├── harmonics.py        # ADD: is_clash(a,b), compatible(a,b), _hour_distance, semitone_distance
├── event_detector.py   # ADD: KEY_CLASH + TRANSITION_OPPORTUNITY branches + _melodic_overlap_gate
└── coach.py            # MODIFY: task_for_event KEY_CLASH/TRANSITION_OPPORTUNITY arms (cited)
tests/state/
├── test_harmonics.py        # EXTEND: is_clash/compatible table-oracle (the deterministic proof)
├── test_event_detector_harmonic.py  # NEW: gate + firing + cross-deck-suppression + cooldown
├── test_coach_harmonic.py           # NEW: cited fragment shape; uncited claim stripped
└── test_kaan_ear_veto.py            # NEW: disagreed-pairs corpus all suppressed (the ship gate)
tests/fixtures/
└── kaan_disagreed_pairs.json        # NEW: pairs Kaan would mix that must NOT flag
```

### Pattern 1: Deterministic Camelot predicate (HARMONIC-01 — the anti-slop core)

The Camelot wheel IS the circle of fifths relabeled: each +1 hour (same letter) = +7 semitones in pitch. I re-derived the tonic pitch-class for every Camelot number and the semitone distance for every same-letter hour-step (computation run + verified this session):

```text
Camelot same-letter hour-distance → pitch-class semitone distance:
  hour 0 → 0 semitones   (PERFECT — same key)
  hour 1 → 5/7 → fifth   (SAFE — adjacent, one note differs; the bread-and-butter move)
  hour 2 → 2 semitones   (SAFE-ENERGY — the "+2" energy boost; reliable)
  hour 3 → 3 semitones   (drifting — "noticeable but manageable on short blends")
  hour 4 → 4 semitones   (drifting)
  hour 5 → 1 SEMITONE    ◄── CLASH (the dissonant beating overlap)
  hour 6 → 6 semitones   (tritone — also dissonant; FEATURES flags 2-step+ regions)
  hour 7 → 1 SEMITONE    ◄── CLASH (the dissonant beating overlap)  [== the +7 "dominant" reach]
```

**The critical, counter-intuitive fact (locked in CONTEXT + FEATURES line 50-52):**
- An **adjacent +1/-1 Camelot move (8A→9A) is a perfect FIFTH and is SAFE.** Cheap tools that flag "not the same key" are WRONG here.
- The **one-semitone disaster** is two melodic tracks a semitone apart overlapping. In Camelot same-letter terms that is an **hour-distance of exactly 5 or 7** (e.g. 8A vs 3A, 8A vs 1A). This is the move you flag.

```python
# Source: derived from circle-of-fifths (verified computation this session);
# theory cross-checked against FEATURES.md §A + mixedinkey.com/dj.studio.
# Pure, side-effect-free, never raises — mirrors to_camelot's honest contract.

def _parse(code: str | None) -> tuple[int, str] | None:
    """('8A') -> (8, 'A'); honest None on anything to_camelot wouldn't emit."""
    if not code:
        return None
    m = _CAMELOT_RE.match(code.upper())   # reuse the shipped recognizer
    if not m:
        return None
    return int(m.group(1)), code.upper()[-1]

def _hour_distance(n1: int, n2: int) -> int:
    """Circular distance on the 12-hour wheel, 0..6."""
    d = abs(n1 - n2) % 12
    return min(d, 12 - d)

# Same-letter hour-distances that produce a 1-semitone (or tritone) dissonance.
# 5 and 7 hours == 1 semitone apart in pitch; 6 hours == tritone. These are the
# ONLY same-letter relationships that genuinely clash on a melodic overlap.
_CLASH_HOURS = frozenset({5, 6, 7})
# Safe same-letter relationships: same(0), adjacent fifth(1), energy +2(2).
_SAFE_HOURS = frozenset({0, 1, 2})

def compatible(a: str | None, b: str | None) -> bool:
    """True iff a and b can ride a long melodic overlap without dissonance.

    SAFE cases (return True): same key; adjacent ±1 (perfect fifth); relative
    major/minor (same number, swapped letter); +2 energy boost. Everything in
    the clash band returns False. Honest None-in → False (we don't claim
    compatibility we can't verify — but the DETECTOR treats unknown as 'no
    clash' separately; see §3).
    """
    pa, pb = _parse(a), _parse(b)
    if pa is None or pb is None:
        return False
    (na, la), (nb, lb) = pa, pb
    if la == lb:
        return _hour_distance(na, nb) in _SAFE_HOURS
    # different letters
    if na == nb:
        return True            # relative major/minor — same notes, mood swap. SAFE.
    # diagonal ±1 + letter swap is COMPATIBLE-ADVANCED (FEATURES line 38) — treat
    # conservative: only the exact ±1 diagonal is safe; wider cross-letter = not
    # asserted compatible (but is_clash below decides what actually FIRES).
    return _hour_distance(na, nb) == 1

def is_clash(a: str | None, b: str | None) -> bool:
    """True iff a and b are an UNAMBIGUOUS dissonant clash worth flagging.

    Deliberately NARROW (conservative-by-default, HARMONIC-03): only the
    same-letter 1-semitone/tritone band fires. Cross-letter pairs and any
    None-in return False — we never flag what we can't prove dissonant. The
    LLM narrates this verdict; it NEVER computes it.
    """
    pa, pb = _parse(a), _parse(b)
    if pa is None or pb is None:
        return False           # honest unknown — no clash claim (anti-slop)
    (na, la), (nb, lb) = pa, pb
    if la != lb:
        return False           # cross-letter: not in the unambiguous clash band
    return _hour_distance(na, nb) in _CLASH_HOURS
```

**Design notes for the planner:**
- Keep `is_clash` NARROW. The "noticeable but manageable on short blends" drift band (FEATURES line 47-48) is the same-letter hour-3/4 zone — e.g. `8A→11A` (hour-3) or `8A→12A` (hour-4) — which I deliberately exclude from `_CLASH_HOURS` (it sits in the "neither" zone, silent). NOTE: `8A→6A` is hour-distance **2** (`min(|8−6|, 12−2)=2`), which is `_SAFE_HOURS` — a safe +2/−2 energy move, NOT drift; do not lift "hour-4" into any code comment for it. Only the genuine 1-semitone (hours 5/7) + tritone (hour 6) band fires. This is the right conservatism: under-flag, never over-flag.
- `compatible()` and `is_clash()` are NOT exact complements (there's a deliberate "neither" zone — hours 3/4 same-letter, most cross-letter pairs). The detector fires ONLY on `is_clash() == True`; the "neither" zone stays silent. This is intentional — the FEATURES "noticeable but manageable" middle band is exactly where a wrong key tag is indistinguishable from a real drift, so we say nothing.
- The relative-major/minor case (`na==nb`, different letter) is verified against the shipped `to_camelot` table: e.g. `8A`=Am and `8B`=C are relative (same notes). SAFE.

### Pattern 2: Melodic-overlap suppression gate (HARMONIC-02 — built ONLY from shipped signals)

The CONTEXT references "the `PEAK_FLOOR_RMS` family". **There is no constant literally named `PEAK_FLOOR_RMS`** (verified: `grep PEAK_FLOOR src/ tests/` → empty). The family is `SILENT_RMS=0.012`, `LOW_RMS=0.040`, `PEAK_RMS=0.110` in `audio/constants.py`. Use those.

```python
# Source: composed from MusicState fields verified this session
# (music_state.py: audible_deck, phase, rms, onset_density, vocal_active, bands).
# NO new detector stack (locked decision). This is a pure read-gate.

def _melodic_overlap_gate(state: MusicState) -> bool:
    """True iff BOTH decks are plausibly contributing simultaneous MELODIC
    content — the precondition for ANY clash note (HARMONIC-02).

    Every signal here already ships. A clash note CANNOT fire unless this
    returns True. Suppresses: single-deck (no overlap), breakdown/acapella
    (keys don't matter), percussive/atonal (no harmony to clash), silence.
    """
    # 1. Both decks live — derive_audible_deck must say "mix" (Pitfall 3).
    if state.audible_deck != "mix":
        return False
    # 2. Above the breakdown/low floor — a dropped-out section disguises a clash.
    #    LOW_RMS (0.040) is the filtered-breakdown/pre-drop threshold (constants.py:54).
    if state.rms < LOW_RMS:
        return False
    # 3. Not a breakdown phase — keys don't matter where harmony has dropped out
    #    (FEATURES line 57). phase ∈ {silent,low,groove,build,drop,peak,breakdown}.
    if state.phase in ("breakdown", "silent", "low"):
        return False
    # 4. TONAL not percussive — high onset_density + low mid/high share ≈ drum-only
    #    tool track ("hard to clash where there's hardly any harmony", FEATURES 56).
    #    Tuning of the onset/band thresholds is Claude's discretion (use the genre
    #    profile percentiles already in state if a fixed floor proves brittle).
    if state.vocal_active:
        return False   # acapella overlap — suppress (FEATURES line 57)
    # (discretion) require some mid/high tonal energy share, e.g.:
    #   if state.bands["mid"] + state.bands["high"] < TONAL_SHARE_FLOOR: return False
    return True
```

**Why this satisfies "no new detector stack":** every gate reads a field the 10Hz `state_refresh_loop` already populates. `phase` is the shipped `classify_phase` output; `onset_density`/`bands`/`vocal_active`/`rms` are existing audio features; `audible_deck` is `derive_audible_deck`. Nothing new is computed.

### Pattern 3: Detector branch placement (HARMONIC-02/03 firing)

Insert the two branches in `EventDetector.detect()` **after the MIX_MOVE block (line 275) and before the genre-chain loop (line 284)** — so a real structural mix move still beats a clash, and the genre chain + HEARTBEAT remain the fallthrough. Both branches sit INSIDE the `_music_truly_playing` gate (they're auto-events, not bypass events), so they inherit the sustained-audible + valid-BPM guard for free.

```python
# After MIX_MOVE, before the genre chain. Mirrors the existing diff→Event pattern.

# 5a) KEY_CLASH — deterministic harmonic clash on simultaneous melodic overlap.
if self._harmonic_enabled and self._melodic_overlap_gate(state):  # §2 gate first
    decks = state.deck_state.decks
    a, b = decks.get("A"), decks.get("B")
    # Both decks must be INDEPENDENTLY resolved + above the cite floor
    # (cross-deck suppression — Phase 59 made a sub-floor deck have NO key:
    # observation, so a clash citing it would be stripped anyway; we gate here
    # too so we never even emit the turn).
    if (
        a and b
        and a.camelot and b.camelot
        and a.confidence >= DECK_CITE_MIN_CONF
        and b.confidence >= DECK_CITE_MIN_CONF
        and is_clash(a.camelot, b.camelot)          # the deterministic verdict
        and self._cooldown_ok("KEY_CLASH", now)
    ):
        ev = Event("KEY_CLASH", state, extra={
            "a_side": "A", "a_camelot": a.camelot,
            "b_side": "B", "b_camelot": b.camelot,
            "semitones": semitone_distance(a.camelot, b.camelot),
        })
        self._fire("KEY_CLASH", now, state)
        return ev

# 5b) TRANSITION_OPPORTUNITY — retrospective, groundable-only blend note (§5).
#     Fires on the structural conditions deck-state CAN ground (both decks
#     resolved + a recent xfader/EQ move that indicates a blend just happened).
#     past-tense only; no present-tense imperative (Pitfall 3).
# ... (see §5 for what is groundable vs must-stay-silent)
```

`semitone_distance(a, b)` is a tiny helper (`_hour_distance` → semitone via the verified table) so the coach fragment can say "1 semitone apart" without the LLM computing it.

### Pattern 4: Cited harmonic narration (HARMONIC-01 — LLM narrates, never computes)

Replace the two stub arms in `coach.py::task_for_event` (lines 264-273). The fragment must (a) hand the LLM the pre-decided verdict, (b) instruct it to CITE both decks' keys, (c) forbid it from doing key math.

```python
if t == "KEY_CLASH":
    a_side, a_cam = ev.extra["a_side"], ev.extra["a_camelot"]
    b_side, b_cam = ev.extra["b_side"], ev.extra["b_camelot"]
    semis = ev.extra.get("semitones")
    return (
        f"HARMONIC CLASH confirmed by the system (you do NOT decide this): "
        f"deck {a_side} is {a_cam}, deck {b_side} is {b_cam} — {semis} semitone(s) "
        f"apart, they're fighting on the melodic overlap. Tell Kaan the move in "
        f"DJ verbs (kill {b_side}'s mids, cut on the drop, filter one out, don't "
        f"ride the pads). Cite BOTH keys exactly: [key:{a_side}:{a_cam}] and "
        f"[key:{b_side}:{b_cam}]. Do NOT invent a key or compute intervals — "
        f"narrate the clash the code already proved. If it doesn't warrant a call, "
        f"output a single space."
    )
```

**Why the citation linter makes this safe (verified):** `key` is in `EVIDENCE_SOURCES` and in the existence-only set of `CitationLinter` (NOT in `_TIME_KEYED_SOURCES`). The Phase 59 single-writer wrote `[key:A:8A]` to the registry ONLY when deck A cleared `DECK_CITE_MIN_CONF`. So `CitationLinter.check()` validates `[key:A:8A]` via `body in snapshot["key"]` — and a fabricated `[key:B:12B]` the registry never observed strips the WHOLE turn (response-level binary). The anti-slop guarantee is structural, not prompt-dependent.

### Anti-Patterns to Avoid
- **Letting Gemini decide the clash.** It will hallucinate intervals. The verdict is `is_clash()`; the LLM only narrates. (FEATURES line 29 — "the single most important architectural call".)
- **Flagging a clash on percussive/atonal content.** The canonical slop. The `_melodic_overlap_gate` is a HARD precondition, not a nicety (CONTEXT + FEATURES line 56).
- **Flagging adjacent/relative/fifth pairs.** These are SAFE moves pros make freely; flagging them is being "wrong about its expertise" (Pitfall 2). `_SAFE_HOURS = {0,1,2}` + relative-letter case never fire.
- **Resolving the second deck from the audible deck's title.** Cross-deck suppression (Pitfall 4): if deck B isn't independently resolved, `decks.get("B")` is absent / sub-floor → no clash.
- **Present-tense imperatives on transitions.** "Bring the fader down now" arrives 5-10s late (Pitfall 3). Past-tense / retrospective only.
- **Inventing a new energy/tonality detector.** Reuse `phase`, `rms`, `onset_density`, `bands`, `vocal_active` (locked decision).
- **Adding KEY_CLASH/TRANSITION_OPPORTUNITY to the diet/ack path.** Phase 59 deliberately kept them out of `ACK_ELIGIBLE_EVENTS` — they're substantive full-payload. Keep them out.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Key→Camelot normalization | A new parser | `harmonics.to_camelot` (shipped) + `_CAMELOT_RE` | Already handles musical/Camelot/open-key + enharmonic aliases + honest None |
| "Which deck is audible / both?" | A new deck-attribution heuristic | `derive_audible_deck` (returns `"mix"`) | Already trusts fader+xfader over FLX4 play-state desync (Pitfall 4) |
| Breakdown/section detection | A new section classifier | `state.phase` from `classify_phase` | Shipped; CONTEXT explicitly says reuse it |
| "Is this percussive/atonal?" | A spectral tonality DSP module | `state.onset_density` + `state.bands` + `state.vocal_active` | All shipped audio features; no Gemini/CLAP/Essentia (banned) |
| Stripping uncited harmonic claims | A harmonic-specific validator | `CitationLinter` (existence-only `key` source) | Shipped Phase 59; `key` already wired into the strip path |
| Bounded registry growth for keys | New dedup logic | The change-only `key:` write in `refresh.py` | Already written; sub-floor decks already uncitable |
| Event priority / cooldown | New maps | `EVENT_PRIORITY` + `MIN_EVENT_GAP_PER_TYPE` | KEY_CLASH (7/28s) + TRANSITION_OPPORTUNITY (5/20s) registered Phase 59-03 |
| Ship-gating an unvalidated detector | A bespoke env flag scheme | Mirror `DeckPoller._vision_enabled` default-off pattern | Established precedent for "off until Kaan signs off the eval" |

**Key insight:** Phase 60 adds essentially ONE new piece of real logic — the `is_clash`/`compatible` predicate (≈40 lines). Everything else is wiring shipped signals together. Resist the urge to build a "harmonic analysis subsystem"; the value is in the deterministic verdict + the conservatism, not in new machinery.

## Runtime State Inventory

> Not a rename/refactor/migration phase — this is additive logic. No stored data, live-service config, OS-registered state, secrets, or build artifacts carry a string that this phase changes.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — the `key:` observations in the in-memory `EvidenceRegistry` are session-scoped and cleared per session (`registry.clear()` on `VoiceRecorder.close()`). No persisted harmonic state. | None |
| Live service config | None — no external service holds harmonic config. | None |
| OS-registered state | None. | None |
| Secrets/env vars | A NEW runtime flag (`harmonic_clash_enabled`, default off) is introduced for the Kaan-ear ship gate — it is a code-level flag like `vision_enabled`, NOT a secret. No `.env` key. | Define the flag; default False. |
| Build artifacts | None — pure source addition; no package rename, no egg-info impact. | None |

## Common Pitfalls

### Pitfall 1: False clash from a wrong key tag (the headline hallucination)
**What goes wrong:** Library key tag is wrong (~30-43% of tracks; RB ~57%, Traktor ~54%, VirtualDJ ~65%, MIK ~70% — multiple secondary sources, MEDIUM confidence). The co-host confidently flags a clash that isn't real, or worse, calls a good blend wrong. Most credibility-destroying failure possible.
**Why it happens:** Treating the library key field as ground truth. It's a silent third-party estimate, worst on percussion-heavy genres (vibemix's actual genres).
**How to avoid:** Layered conservatism (HARMONIC-03): (1) clash citable only if both decks cleared `DECK_CITE_MIN_CONF=0.6`; (2) `_SAFE_HOURS={0,1,2}` + relative never fire (one-step-off is indistinguishable from a key-detect error); (3) NARROW `_CLASH_HOURS={5,6,7}` — only the unambiguous 1-semitone/tritone band; (4) ship gated until the Kaan-ear veto passes.
**Warning signs:** Clash fires on a pair Kaan knows mixes fine; clash citing a sub-floor deck; clash on hour-distance 3/4 pairs.

### Pitfall 2: Clash on percussive/atonal or breakdown content (canonical slop)
**What goes wrong:** Flagging a key clash on two drum/tool tracks or during a breakdown where keys don't matter. vibemix's genres are percussion-heavy — exactly where this bites.
**Why it happens:** The grounding proves a key *exists*, not that it's *currently sounding melodically against another key*.
**How to avoid:** `_melodic_overlap_gate` runs FIRST and is a hard precondition: `audible_deck=="mix"` + non-breakdown phase + `rms ≥ LOW_RMS` + tonal (not `vocal_active`, mid/high share present). Built entirely from shipped signals.
**Warning signs:** Clash during `deck=A`/`deck=none`; clash during `phase=breakdown`; clash on a kick-and-hat tool track.

### Pitfall 3: Late / context-blind transition advice
**What goes wrong:** A present-tense "bring the fader down now" arrives 5-10s after the blend is done; or a clash callout during a single-deck section.
**Why it happens:** LLM+TTS latency is structural; the codebase already enforces past-tense for this reason.
**How to avoid:** TRANSITION_OPPORTUNITY notes are retrospective/past-tense only; no present-tense imperatives. Clash gated on `audible_deck=="mix"`.
**Warning signs:** Imperative verbs ("bring", "pull", "drop it now") in output; transition critique on a `deck=A` state.

### Pitfall 4: Adding the new types to the diet path or the matrix event list inconsistently
**What goes wrong:** The diet path raises `ValueError` for non-ack events; or the LLM emits `[ev:KEY_CLASH@t]` but the matrix grammar list (matrix.py line 124) doesn't list it, confusing the model.
**Why it happens:** Phase 59 kept these out of `ACK_ELIGIBLE_EVENTS` (correct) but the `CITATION_GRAMMAR_BLOCK` event-types-tracked line still lists only the 7 v4 types.
**How to avoid:** Keep them OUT of `ACK_ELIGIBLE_EVENTS`. Decide (Open Q1) whether to add them to the matrix `[ev:<TYPE>]` list — the clash is cited via `[key:...]` not `[ev:KEY_CLASH]`, so it may not be needed, but consistency is worth a deliberate call.
**Warning signs:** `ValueError` from `build_prompt(diet=True)`; goldens flip; LLM emits an `[ev:KEY_CLASH]` the linter strips (KEY_CLASH IS registered as an `ev` write in `_fire`, so it would actually validate — verify).

### Pitfall 5: Golden / hype-mode regression from touching coach.py
**What goes wrong:** Editing `task_for_event` shifts a shared golden or the hype-mode output.
**Why it happens:** `coach.py` is shared across modes; `test_coach_prompt_grounding.py` + diet goldens pin it.
**How to avoid:** The two arms being edited are CURRENTLY stubs that never fire — replacing them touches only the KEY_CLASH/TRANSITION_OPPORTUNITY paths. Run the full coach/grounding/diet golden set after. Phase 61 owns the persona voice — keep this phase to the grounded *facts*.
**Warning signs:** A golden in `test_coach_prompt_grounding.py` / `test_coach_prompt_diet.py` needs "just to pass" updates.

## Code Examples

### Verifying the semitone predicate (the deterministic proof — run this session)
```python
# Camelot number N -> tonic pitch class (circle of fifths, anchor 8A=Am, A=9).
def pcA(N): return (9 + 7*(N-8)) % 12
def semis(a, b):
    d = abs(pcA(a) - pcA(b)) % 12
    return min(d, 12 - d)
# 8A vs 3A: hour-distance 5 → 1 semitone  → CLASH ✓
# 8A vs 1A: hour-distance 5 → 1 semitone  → CLASH ✓
# 8A vs 9A: hour-distance 1 → fifth (5 st)→ SAFE  ✓ (adjacent)
# 8A vs 10A: hour-distance 2 → 2 semitones→ SAFE-ENERGY ✓ (+2 move)
# Output verified: hours {5,7}→1 semitone, hour 6→tritone, hour {1,2}→safe.
```

### The Kaan-ear veto corpus shape (HARMONIC-03 ship gate)
```json
// tests/fixtures/kaan_disagreed_pairs.json — pairs Kaan would HAPPILY mix
// that the detector MUST NOT flag (over-flagging trips the gate).
[
  {"a": "8A", "b": "9A",  "note": "adjacent fifth — bread and butter"},
  {"a": "8A", "b": "8B",  "note": "relative major — mood lift"},
  {"a": "8A", "b": "10A", "note": "+2 energy boost — the best mix"},
  {"a": "5A", "b": "5A",  "note": "same key — ride it"},
  {"a": "8A", "b": "6A",  "note": "2-step drift — manageable, Kaan rides it"}
]
// Plus a small set of TRUE clashes that SHOULD flag (8A vs 3A, 8A vs 1A)
// so the test proves the gate isn't vacuously suppressing everything.
```
```python
# tests/state/test_kaan_ear_veto.py — the runnable ship gate.
@pytest.mark.parametrize("pair", load_disagreed_pairs())
def test_disagreed_pairs_never_flag(pair):
    assert is_clash(pair["a"], pair["b"]) is False  # MUST NOT clash
def test_true_clashes_do_flag():
    assert is_clash("8A", "3A") is True
    assert is_clash("8A", "1A") is True
```
The detector's runtime `harmonic_clash_enabled` flag stays **False** (mirroring `DeckPoller._vision_enabled`) until Kaan signs off — surfaced as a KAAN-ACTION item, conservative default = quiet/gated.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LLM judges harmonic compatibility | Deterministic Python verdict; LLM only narrates | This phase (locked Phase 59) | The clash is math-checkable → provably-correct anti-slop |
| Library key = ground truth | Confidence-gated (`DECK_CITE_MIN_CONF`) + conservative adjacency suppression | Phase 59→60 | ~57-70% accuracy band no longer trips false clashes |
| Single-stream "what's playing" | Per-deck `deck_state` with cross-deck suppression | Phase 59 | Clash only on independently-resolved both-decks |

**Deprecated/outdated:** Nothing — this is a forward-only additive phase. (Note: CLAUDE.md's auto-generated map block is STALE, describing the retired POC era; trust the live `src/vibemix/` tree, which I read directly.)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The ~57-70% key-tag accuracy band (RB 57 / Traktor 54 / VDJ 65 / MIK 70). | Pitfall 1 | LOW — used only to justify conservatism direction, not a hard threshold. Multiple secondary sources agree (FEATURES + PITFALLS); not benchmarked here. Tuning is Kaan's discretion. |
| A2 | The exact `onset_density` / band-share threshold for "percussive vs tonal". | Pattern 2 | MEDIUM — a too-loose floor lets a clash fire on a percussive track (slop). Mitigation: Claude's-discretion tuning + Kaan-ear veto + the conservative default-off flag catch it before audience. Recommend deriving from the genre-profile percentiles already in `state` rather than a fixed constant. |
| A3 | TRANSITION_OPPORTUNITY can be grounded from `recent_moves` (xfader/EQ) + both-decks-resolved alone. | §5 | MEDIUM — vibemix has NO phrase grid per deck and NO dual-deck low-band, so most "phrase alignment" / "bass swap" notes are NOT groundable. See §5 for the explicit must-stay-silent list. If too little is groundable, scope TRANSITION_OPPORTUNITY to near-zero this phase (acceptable — silence over a guess). |
| A4 | Adding KEY_CLASH/TRANSITION_OPPORTUNITY to the matrix `[ev:<TYPE>]` grammar list is optional (clash cites `[key:...]`, not `[ev:KEY_CLASH]`). | Pitfall 4 / Open Q1 | LOW — verify whether `_fire("KEY_CLASH")` writing an `ev` observation means the LLM *could* validly cite `[ev:KEY_CLASH@t]`; if so, listing it keeps the grammar honest. |

## Open Questions (RESOLVED)

> RESOLVED in planning: Q1 (matrix `[ev:<TYPE>]` grammar list) → Plan 04 Task 2 adds both event types. Q2 (TRANSITION_OPPORTUNITY groundability) → Plans 02/04 scope it to retrospective both-decks-resolved structural moves only (near-zero this phase; no phrase-grid/dual-deck-low-band → silent). Q3 (`compatible()` cross-letter breadth) → conservative, tests-only, does not affect firing.

1. **Matrix grammar event list.** `CITATION_GRAMMAR_BLOCK` (matrix.py:124) lists the 7 v4 event types for `[ev:<TYPE>]` but not the two new ones. Since `_fire` DOES write an `ev` observation for KEY_CLASH (verified — `_fire` writes `[ev:<ev_type>]`), the LLM could validly cite `[ev:KEY_CLASH@t]`. The harmonic narration is anchored on `[key:...]` regardless. Recommendation: add the two types to the list for consistency, behind the same golden re-check; or leave them off and rely solely on `[key:...]` cites. Decide at plan time (low risk either way).

2. **How much of TRANSITION_OPPORTUNITY is actually groundable this phase?** (See §5.) vibemix lacks per-deck phrase grids and dual-deck low-band energy. The honest answer may be "very little" → scope this event to the narrow set that IS groundable (both decks resolved + a recent structural xfader move = "you just blended A→B, the keys sit fine / clash") and stay silent on phrase/bass-swap specifics. This is acceptable and on-thesis (silence over a guess).

3. **Diagonal cross-letter compatibility breadth.** FEATURES line 38 calls the diagonal (±1 + letter swap) "COMPATIBLE-ADVANCED". My `compatible()` only treats exact-±1-diagonal as safe and leaves wider cross-letter pairs in the "neither" zone (no clash, no asserted-compatible). Since `is_clash` is the only thing that FIRES, this is conservative and correct — but confirm the planner doesn't need `compatible()` to assert more (it's currently only used by tests, not the firing path).

## Environment Availability

> Skipped — this phase has no external dependencies. It is pure-Python logic + tests against modules already in the repo. No CLI tools, services, runtimes, or databases beyond the existing test runner (`pytest`, present per CONTRIBUTING.md).

## Validation Architecture

> `nyquist_validation` not disabled in config (treated as enabled). All anti-slop guarantees are observably testable.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (per `[tool.pytest.ini_options]` in `pyproject.toml`) |
| Config file | `pyproject.toml` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/state/test_harmonics.py tests/state/test_event_detector_harmonic.py tests/state/test_coach_harmonic.py` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` (or `uv run pytest -q`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HARMONIC-01 | `is_clash`/`compatible` are deterministic; full Camelot table oracle (every pair) | unit | `pytest tests/state/test_harmonics.py -x` | ❌ Wave 0 (extend existing `test_harmonics.py`) |
| HARMONIC-01 | LLM-narrate-only: clash fragment hands a pre-decided verdict + cite instruction; never asks for key math | unit | `pytest tests/state/test_coach_harmonic.py::test_clash_fragment_is_cited_narration -x` | ❌ Wave 0 |
| HARMONIC-01 | Uncited / fabricated `[key:B:12B]` strips the whole turn | unit | `pytest tests/coach/test_citation_linter*.py -k key_existence -x` | ✅ (linter shipped; add a harmonic case) |
| HARMONIC-02 | No clash when `audible_deck != "mix"` | unit | `pytest tests/state/test_event_detector_harmonic.py::test_no_clash_single_deck -x` | ❌ Wave 0 |
| HARMONIC-02 | No clash during `phase=breakdown` / silent / low | unit | `pytest ...::test_no_clash_in_breakdown -x` | ❌ Wave 0 |
| HARMONIC-02 | No clash on percussive/atonal (high onset, no tonal share) / `vocal_active` | unit | `pytest ...::test_no_clash_percussive -x` | ❌ Wave 0 |
| HARMONIC-03 | Adjacent / relative / +2 pairs never fire (`_SAFE_HOURS`) | unit | `pytest tests/state/test_kaan_ear_veto.py::test_disagreed_pairs_never_flag -x` | ❌ Wave 0 |
| HARMONIC-03 | Sub-floor (`confidence < DECK_CITE_MIN_CONF`) deck → no clash (cross-deck suppression) | unit | `pytest ...::test_no_clash_subfloor_deck -x` | ❌ Wave 0 |
| HARMONIC-03 | Detector OFF by default (`harmonic_clash_enabled=False`) → never fires until enabled | unit | `pytest ...::test_detector_gated_by_default -x` | ❌ Wave 0 |
| HARMONIC-03 | True clashes (8A↔3A, 8A↔1A) DO fire (gate not vacuous) | unit | `pytest tests/state/test_kaan_ear_veto.py::test_true_clashes_do_flag -x` | ❌ Wave 0 |
| HARMONIC-04 | Transition note is past-tense / retrospective; no present-tense imperative verbs | unit | `pytest tests/state/test_coach_harmonic.py::test_transition_is_retrospective -x` | ❌ Wave 0 |
| HARMONIC-04 | No transition advice when the underlying signal is absent | unit | `pytest ...::test_transition_silent_without_grounding -x` | ❌ Wave 0 |
| (regression) | Hype-mode + diet goldens unchanged | golden | `pytest tests/state/test_coach_prompt_grounding.py tests/state/test_coach_prompt_diet.py -q` | ✅ |

### Sampling Rate
- **Per task commit:** the quick-run command (the three harmonic test files).
- **Per wave merge:** full suite green (note: the 7 pre-existing `live-tuning-or-brain` WIP failures documented in Phase 59 `deferred-items.md` — confirm the count is unchanged, do not introduce new failures).
- **Phase gate:** full suite green AND the Kaan-ear veto corpus test green BEFORE flipping `harmonic_clash_enabled` to True (the KAAN-ACTION ship gate).

### Wave 0 Gaps
- [ ] `tests/state/test_harmonics.py` — EXTEND with the `is_clash`/`compatible` table oracle (covers HARMONIC-01). The file exists with the `to_camelot` oracle pattern to mirror.
- [ ] `tests/state/test_event_detector_harmonic.py` — NEW; gate + firing + cross-deck-suppression + cooldown + default-off (HARMONIC-02/03).
- [ ] `tests/state/test_coach_harmonic.py` — NEW; cited fragment shape + retrospective transition + uncited-strip (HARMONIC-01/04).
- [ ] `tests/state/test_kaan_ear_veto.py` + `tests/fixtures/kaan_disagreed_pairs.json` — NEW; the disagreed-pairs ship gate (HARMONIC-03).
- [ ] No framework install needed — pytest is present.

## Security Domain

> `security_enforcement` not disabled; included. This phase processes only the user's own deck metadata, locally, in-memory.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface; local app. |
| V3 Session Management | no | In-memory session state; `registry.clear()` per session already shipped. |
| V4 Access Control | no | Single-user local process. |
| V5 Input Validation | yes | `to_camelot` + `_parse` degrade to honest `None` on malformed key tags; `is_clash` never raises. No external input crosses a trust boundary — deck metadata comes from the user's own library/MIDI. |
| V6 Cryptography | no | None — and DECK-05's repo-scrub already bans any SQLCipher live-DB key extraction. |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Hallucinated harmonic claim reaching the audience | Spoofing (false expertise) | Deterministic verdict + `CitationLinter` existence-only strip + conservative default-off gate (the core anti-slop chain). |
| Prompt injection via track metadata into the clash fragment | Tampering | Camelot codes are validated by `_CAMELOT_RE` before reaching the fragment; the verdict is computed in Python, not from LLM-parsed metadata. The fragment interpolates only validated `a_camelot`/`b_camelot`/`semitones`. |
| Crash on odd key tag | Denial of Service | `to_camelot`/`_parse`/`is_clash` never raise (honest-None contract); the detector branch is exception-safe like the rest of `detect()`. |
| Writing to the user's DJ collection | Tampering (data corruption) | Out of scope — this phase only READS `MusicState`; DECK-05 repo-scrub already pins read-only. |

## Sources

### Primary (HIGH confidence — read directly this session)
- `src/vibemix/state/harmonics.py` — `to_camelot`, `_CAMELOT_RE`, the 24-entry wheel table, the deferred `is_clash`/`compatible` slot.
- `src/vibemix/state/event_detector.py` — the `detect()` diff→Event pattern, `_cooldown_ok`, `_music_truly_playing`, branch ordering.
- `src/vibemix/state/coach.py` — the stub `task_for_event` arms (264-273), `evidence_line` deck block, `ACK_ELIGIBLE_EVENTS`.
- `src/vibemix/state/deck_state.py`, `deck_poller.py` (`DECK_CITE_MIN_CONF=0.6`, `_vision_enabled` gate pattern), `refresh.py` (465-501, the single-writer key: write).
- `src/vibemix/state/evidence_registry.py` (89-135, the `key` source grammar + existence-only `has`), `coach/citation_linter.py` (the existence-only strip of `key`).
- `src/vibemix/state/phase.py` (phase semantics + thresholds), `src/vibemix/audio/constants.py` (SILENT/LOW/PEAK_RMS, KEY_CLASH 28s / TRANSITION_OPPORTUNITY 20s), `src/vibemix/state/event.py` (priorities), `src/vibemix/state/music_state.py` (fields), `src/vibemix/state/track_resolver.py` (`derive_audible_deck` "mix"), `src/vibemix/prompts/matrix.py` (CITATION_GRAMMAR_BLOCK).
- `.planning/phases/60-.../60-CONTEXT.md`, `.planning/REQUIREMENTS.md`, `.planning/phases/59-.../59-03-SUMMARY.md` + `59-04-SUMMARY.md`.
- **Deterministic semitone-distance computation** run this session (circle-of-fifths derivation) — the proof behind `_CLASH_HOURS`.

### Secondary (MEDIUM confidence — research docs, multi-source)
- `.planning/research/FEATURES.md` §A (Camelot theory, +2/+7, percussive exception, USEFUL-vs-ANNOYING table) — cross-verified against MixedInKey / DJ.Studio / Mixgraph / Pioneer DJ.
- `.planning/research/PITFALLS.md` (Pitfalls 1-3, key-accuracy band, recovery strategies).

### Tertiary (LOW confidence — flagged for validation)
- The exact ~57-70% per-app key accuracy figures (A1) and the percussive-vs-tonal numeric threshold (A2) — both deferred to Kaan's tuning + the ear-veto gate.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every module read directly; no new deps.
- Camelot predicate (architecture): HIGH — re-derived deterministically + computation-verified + theory cross-checked.
- Suppression gate: HIGH — composed entirely from verified `MusicState` fields.
- Conservatism gate: HIGH on mechanism (cite-floor + adjacency + cross-deck all shipped/verified); MEDIUM on exact thresholds (Kaan's discretion).
- Transition-execution groundability: MEDIUM — vibemix lacks per-deck phrase grid + dual-deck low-band; scope honestly (Open Q2).
- Pitfalls: HIGH on the false-clash + percussive + latency classes (codebase + PITFALLS); MEDIUM on accuracy numbers.

**Research date:** 2026-05-21
**Valid until:** ~30 days for the codebase facts (stable internal modules); the theory is evergreen. Re-verify if Phase 61's persona refactor lands before this phase executes (it touches `coach.py`/`matrix.py` — coordinate the `task_for_event` edits).
