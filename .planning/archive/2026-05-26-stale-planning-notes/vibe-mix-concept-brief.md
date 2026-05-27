---
title: Vibe Mix — Concept Brief
date: 2026-05-20
context: /goal session — develop the Vibe Mix concept, reconcile with OSS vibemix co-host
status: concept, not yet a milestone
positioning: BRAVOH commercial module (decided 2026-05-20)
---

# Vibe Mix — Concept Brief

**Tagline:** Solving DJing.

The DJing counterpart to **Vibe Producing** — a natural-language interface for set
*creation*, powered by the same semantic grammar that runs the rest of BRAVOH.
Vibe Producing makes the music; Vibe Mix plays it. One grammar, new surface.

---

## ⚠️ Name collision — read first

Three near-identical names exist. Do not conflate them.

| Name | What it is | State |
|------|-----------|-------|
| **vibemix** (lowercase, OSS) | The **live** AI co-host — in your ear *during* the set. | v3.1 engineering-complete; OSS-designed but **not yet public** (awaiting Apple Dev + SignPath; repo `bravoh/vibemix` transfer + `gh release` are pending Kaan-action). |
| **Vibe Producing** | BRAVOH's music-*making* surface. | Existing BRAVOH module. |
| **Vibe Mix** (this brief) | The DJ-*prep* surface — set-building *before* the gig. | Concept. Commercial BRAVOH module. |

**Decision (2026-05-20):** Vibe Mix ships as a **commercial BRAVOH module**, the
"play/prep" sibling of Vibe Producing. The free OSS `vibemix` co-host stays the
top-of-funnel; Vibe Mix is the paid prep surface it upsells into. They **share one
embedding + library substrate** (Gemini Embedding 2 + sqlite-vec), so the marginal
build cost of Vibe Mix is far lower than greenfield.

> Open sub-decision (deferred): the lowercase-`vibemix` name is locked for the OSS
> co-host (README hero, repo, launch copy). "Vibe Mix" as a commercial module name
> either (a) becomes a deliberate brand family with the OSS tool, or (b) the module
> gets a distinct name to avoid market confusion. Kaan's call at milestone-scaffold.

---

## The Flow

1. **Natural-language input** — "Tech house set, Ibiza sunset vibe." No filters, no
   BPM ranges, no genre tags. Just intent.
2. **Smart library filtering (cheap pass)** — lightweight Gemini embeddings surface
   only the tracks in the DJ's *personal* library that match the requested vibe.
3. **Calibration via 3-track sampling** — from the filtered pool, surface 3 candidates
   pulled from distinct sub-clusters of the vibe space (not just top/middle/bottom of
   one axis — three k-means cluster centroids read as "three readings of the same
   vibe"). The DJ picks the one closest to their intent.
4. **Centroid-based re-extraction (expensive pass, focused)** — the chosen track
   becomes the centroid; re-run deep audio analysis using it as the anchor, but **only
   on the curated subset**, never the full library. Cost-optimized by design.
5. **Narrative arc ordering** — auto-order to a real set arc: opener → builder → peak
   → cooldown. Set storytelling, not BPM matching. Fully manual reorder/swap/replace.
6. **Auto hot cues — the killer feature** — auto-place hot cues on key transition
   points (downbeats, breakdowns, drops), written back to the DJ software's library so
   they trigger cleanly on a controller. This is the hours-per-set unpaid prep labor we
   eliminate.

---

## Reality check: this is ~60% already shipped in OSS vibemix

The cheap-filter → calibrate → expensive-on-subset pattern is largely live today.

| Brief step | Status in vibemix |
|------------|-------------------|
| 1. NL input | Trivial. |
| 2. Cheap embedding filter | **Shipped** — Gemini Embedding 2 + sqlite-vec (Mac) / numpy (Win), NL vibe-search CLI + drag-drop UX, 30-day staleness nudge, €50/mo CI cost gate (Phase 28, v2.1). |
| 3. 3-track calibration | **New, cheap** — k-means over the filtered embedding pool, sample cluster centroids. The UX is the clever part, not the math. |
| 4. Centroid re-extraction | **Architecture exists** — two-tier Gemini routing + `ModelRouter` + ServiceTier.FLEX for batch paths (Phase 41, v3.0). Wire the focused re-run on the subset. |
| Library priors | **Shipped** — pyrekordbox XML import (Phase 25, v2.0). |

**Genuinely new and hard — only two things:**

### 5. Narrative arc ordering — needs harmonic grounding, not just an energy curve
An energy curve alone produces AI slop ("yapay playlist"). Real DJs care about
**harmonic mixing** (Camelot/key compatibility). Arc ordering must be
`energy progression + key-adjacency constraint` (Camelot ±1 / relative major-minor),
or it sounds like a machine guessed. Key/BPM come free from pyrekordbox priors where
present; derive only where missing. **This is a constraint-satisfaction problem, not a
ranking problem.**

### 6. Auto hot cues — the moat AND the minefield
- **Detection** is the *easy* half: downbeat / breakdown / drop. Solvable with
  beat-grid + spectral-flux / structural-segmentation DSP. (Gemini-only constraint
  applies to the *AI brain*; deterministic DSP for beat/structure is fine and is
  already how vibemix grounds phase detection — no CLAP/MERT needed.)
- **Write-back** is the *hard* half and the real risk: persisting cues into
  **Rekordbox DB / Serato GEOB tags / Engine DJ / Traktor NML** without corrupting
  the user's collection. `pyrekordbox` is read-leaning; writing to a live Rekordbox
  master DB can break it. **The moat is here; so is the live grenade.** Launch likely =
  **read priors + write to one format behind a backup-first, non-destructive guard**,
  expand formats only once bulletproof.

---

## Anti-slop mapping (this is BRAVOH/vibemix's central law)

vibemix's governing principle: *"no reaction beats a hallucinated reaction."*
Vibe Mix inherits the exact mirror:

> **A wrong hot cue is worse than no hot cue.**

If a DJ hits a cue button mid-set and it fires off-beat or in the wrong place, that's a
catastrophe in front of a crowd — strictly worse than the manual prep we removed. So:

- **Confidence-gated cueing.** If detection confidence < threshold, **place no cue**
  and surface it as "needs your ear" rather than guessing.
- **Never destructive.** Back up the target library before any write; every auto-cue is
  reversible; the DJ reviews before commit.
- Every Vibe Mix feature passes the same acid test as the rest of the stack:
  *what hallucination class does it close, or what does it ground against?*

---

## Open questions — DECIDED (Kaan, 2026-05-20)

1. **Library scope → Personal library only at launch.** ✅ LOCKED. A hot cue is only
   meaningful on a file you own and can load onto a controller; Spotify/Beatport/
   Beatsource streams are DRM'd, not local, can't be cued or played from a controller.
   Beatport/Beatsource become a *separate later discovery feature* ("fill the gap in
   your set"), not part of the cueing core.
2. **Hot cue conservatism → Strict + confidence-gated.** ✅ LOCKED. Downbeat / breakdown
   / drop only at launch. Creative cueing (loop points, mash-up cues) ships after the
   basics are bulletproof, behind the same anti-slop gate.
3. **Launch scope → "whatever we can confidently ship and test together."** ✅ LOCKED —
   the governing principle. This is the anti-slop law applied to product scope: *don't
   ship what you can't confidently stand behind.* It makes the build sequence
   self-selecting — see below. Not a calendar; a confidence bar.
4. **Prep vs. live → Prep-first; "live mode" is NOT a rebuild.** The live surface
   **already exists** — it's the free OSS `vibemix` co-host. The two-product spine is:
   **Vibe Mix (before the gig) ↔ vibemix (during the gig)**, sharing one library/
   embedding substrate. Don't rebuild a live mode; integrate the one we shipped.
5. **Positioning → Commercial BRAVOH module.** Vibe Producing's prep sibling; OSS
   vibemix is the free funnel into it. Shared substrate.

### What "confidently ship and test together" selects for

The launch surface is **not pre-decided by feature ambition — it's decided by what
passes the confidence bar when we test it together.** Concretely:

- **Slice 0 (write-back spike) is the fork.** If auto-cues can be written back
  safely (backup-first, reversible, non-destructive) and *we test it together and trust
  it*, hot cues are in the launch. If they can't be made trustworthy, **the killer
  feature waits** and we launch the prep MVP without it.
- **Either outcome is a real launch.** Slice 1 (NL → vibe filter → 3-track calibrate →
  focused re-extract → manually-orderable set) already beats "scroll 3000 files" and is
  fully testable together. Shipping *that* confidently > shipping cues we don't trust.
- The bar is **mutual**: "test together" = Kaan + Francesco run real sets through it and
  it earns the same "real DJ friend" trust the live co-host is held to.

---

## Why it matters

- **Real, recurring, expensive pain.** DJs spend hours of unpaid prep per gig; hot
  cueing alone can eat 3-4 h/week. We delete it.
- **Extends the BRAVOH thesis.** One semantic grammar across the creative stack — Vibe
  Producing to make, Vibe Mix to play. Same logic, new surface.
- **Defensible moat.** Quality auto hot cueing is genuinely hard (the write-back layer
  especially). Done well, it retains by itself.
- **Architecturally elegant + cheap.** cheap-filter → user-calibration →
  expensive-analysis-on-subset keeps compute low; ~60% rides existing vibemix substrate.

---

## Relationship to the Memory Turn thesis

Vibe Mix and the **v.next Memory Turn** (`.planning/notes/v-next-memory-turn.md`) are
two faces of the same pivot. Memory Turn makes the *free* co-host forward-leaning via a
retrieval seam over session history; Vibe Mix is the *paid* prep surface over the *same*
embedding + sqlite-vec substrate. The library index, the embedding model, and the
"ground, don't confabulate" law are shared. Build the substrate once; both faces draw on
it. Sequencing the two (which lands first, what's shared infra vs. surface) is the first
milestone-scaffold question.

---

## Hard constraints carried in (do not re-litigate)

- **Gemini-only AI brain.** No CLAP / MERT / OpenL3 / OpenAI / Anthropic. (Deterministic
  DSP for beat-grid/structure is not an "AI provider" and is allowed — it already grounds
  vibemix phase detection.)
- **No managed memory frameworks** (Mem0 / Letta / Zep / Cognee rejected). sqlite-vec +
  Gemini Embedding 2 DIY wrapper.
- **No raw-key shipping.** Bravoh-side proxy with per-client rate limit.
- **One-click install** discipline carries to any desktop surface.

---

## Recommended build sequence (MVP slice → moat)

The ~60%-shipped substrate means the right first cut is a **thin vertical slice** that
proves the *new* value, not a re-pour of the existing library plumbing.

- **Slice 0 — Write-back spike (de-risk first, ship nothing).** Prove a single library
  format (recommend **Rekordbox** — pyrekordbox is furthest along, and it's the DDJ-FLX4
  / Pioneer-CDJ world Kaan already lives in) can take an auto-placed cue **backup-first,
  reversible, non-destructive**. If this can't be made safe, the killer feature is a
  promise we can't keep — kill or re-scope *before* building anything on top.
- **Slice 1 — Prep MVP on existing substrate.** NL input → cheap embedding filter
  (already shipped) → 3-track calibration (new, cheap) → focused re-extraction on the
  subset (architecture already shipped). Output: a *vibe-matched, manually-orderable*
  set. **No arc, no cues yet** — this alone already beats "scroll 3000 files."
- **Slice 2 — Arc ordering with harmonic grounding.** Add the constraint-satisfaction
  ordering (energy progression + Camelot key-adjacency). Manual override always on.
- **Slice 3 — Auto hot cues (the moat).** Detection (DSP) + confidence-gated placement +
  write-back from Slice 0, strict cue set only (downbeat/breakdown/drop), DJ reviews
  before commit.

Each slice is independently demoable and shippable. Slice 0 gates everything.

## Two real forks — recommendations (Kaan decides)

1. **Module home.** *Recommend: BRAVOH product, sharing the vibemix library/embedding
   substrate as a pulled-in package — not a paid layer bolted into the OSS desktop app.*
   Reason: keeps the OSS funnel clean (no paywall inside a "free" tool, which corrodes
   the GitHub-stars / trust play), and Vibe Mix's prep workflow is a web/desktop BRAVOH
   surface, not an in-ear runtime. The substrate is the shared dependency; the surfaces
   stay separate.
2. **Write-back format at launch.** *Recommend: Rekordbox-only at launch* (above), Serato
   GEOB next once the safety pattern is proven. Don't fan out formats before Slice 0
   holds on one.

## Next steps

- This is a **concept**, not a milestone. Convert via `/gsd-new-milestone` (or a BRAVOH-
  side equivalent) when Kaan commits scope.
- **Gate everything on the Slice 0 write-back spike.** It's the highest-risk,
  highest-moat unknown — derisk it before promising the killer feature publicly.
