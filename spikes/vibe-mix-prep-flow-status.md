# Vibe Mix prep flow — spike status (2026-05-20)

Autonomous build session. The Vibe Mix prep flow from `.planning/notes/vibe-mix-concept-brief.md`
proven slice-by-slice as offline, deterministic spikes under `spikes/` (out of the
`src/vibemix/` grep gate; nothing wired into the shipping package yet, pending the
module-home decision). **48 tests green.**

## Slice status

| Slice | What | Status | Tests |
|-------|------|--------|-------|
| 0 | Rekordbox cue write-back | **proven** — XML round-trip (master.db writes ruled out), backup-first, confidence-gated. Demo XML on Desktop. | 9 |
| 1 | 3-track calibration | **proven** — centroid-anchored farthest-first over the embedding pool; reuses shipping cosine math. | 5 |
| 1 | end-to-end `prep_flow` | **proven** — NL → filter → calibrate → pick → focused re-extract → arc, dependency-injected. | 2 |
| 2 | harmonic arc ordering | **proven** — full Camelot wheel + compatibility; energy tent guarantees the arc, harmonic reorder within equal-energy runs. | 32 |
| 3 | auto-cue DSP detection | **NOT started** — see decision below. | — |

Concrete `prep_flow` output on a fake pool: calibration surfaced the off-vibe
outlier as an anchor (so the DJ can reject it), the pick dropped it via focused
re-extraction, and the final set chained `8A → 9A → 10A → 11A` over a rising energy
plateau — i.e. "a real DJ built this", not an energy-sorted list.

## Two real gates still owned by Kaan (deferred, not blocked)

1. **Slice 0 manual import test** — `spikes/vibe-mix-slice0-cue-writeback.md` verdict:
   import `~/Desktop/vibemix-cues-demo.xml` into Rekordbox, confirm cues land on the
   right beats and trigger cleanly on the DDJ-FLX4. Decides whether auto-cues are in launch.
2. **Module home** — Vibe Mix in the BRAVOH product vs a paid layer in the vibemix app
   (recommendation in the brief: BRAVOH product, shared substrate). Decides where this
   spike code graduates to.

## Automation ceiling — DECIDED (Kaan, 2026-05-20): "1-click import OK (safe)"

The *intelligence* is fully automatic (track pick + arc + cue detection); the only
non-auto step is handing cues to Rekordbox. Investigated whether that hand-off can be
zero-click by auto-configuring Rekordbox's XML bridge path:

- pyrekordbox `read_rekordbox6_options` does **not** expose the imported-XML path.
- It lives in an opaque Pioneer `.settings` file (not the prefs plist, not the options DB),
  with no documented/clean write API. Setting it programmatically is fragile and means
  writing into Rekordbox's own settings — rejected (corrupts-user-setup risk, low confidence).

**Locked product flow (safe, never touches master.db or Rekordbox settings):**
1. **One-time setup:** vibemix writes every set to a STABLE path (e.g.
   `~/Music/vibemix/current-set.xml`). The user points Rekordbox → Preferences → Advanced →
   `rekordbox xml` → Imported Library at that file **once**.
2. **Per set = 1 click:** the app overwrites that file with the new set + auto-detected cues;
   the user clicks the `rekordbox xml` node (refreshes) and drags/imports. Non-destructive,
   reversible, master.db untouched.

So: "set up once, 1-click forever." Zero-click is only achievable via direct master.db writes
(Slice 0 verdict: unsafe) or on more-open software (Serato/Mixxx/Engine) — both deferred.

## Deferred decision — Slice 3 cue-detection DSP dependency

The auto-cue *detection* half (downbeat / breakdown / drop) needs beat-grid + structural
DSP. `librosa` is the obvious choice but is **not installed** and is heavy (numba/llvmlite),
which is a one-click-install-budget concern (every dep is rated green/yellow/red). Did not
pull it unilaterally. Options to weigh before Slice 3:

- **librosa** — fast to prototype, heaviest install footprint (yellow/red).
- **aubio** — lighter beat/onset C lib, smaller footprint.
- **Beat This! via a Rust sidecar** — already in the v3.x backlog ("closes AI-reacts-off-beat
  class; gated on install-size budget"); deterministic, no Python DSP dep, Gemini-compliant.
- Recommendation: do the cue-detection spike with **aubio or a Rust beat sidecar**, not
  librosa, to keep the install green — but this is a Kaan call before Slice 3 starts.

Detection is also the half gated on the Slice 0 manual verdict: no point perfecting cue
detection until write-back is confirmed trustworthy in real Rekordbox.
