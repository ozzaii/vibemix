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
| 3 | auto-cue DSP detection | **proven** — spectral-flux onset + autocorr beat-grid + RMS energy → intro/breakdown/drop, beat-snapped, confidence-scored. numpy/scipy only (no new dep). Wired into demo. | 5 |

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

## Slice 3 dep decision — RESOLVED: numpy/scipy only (no new dep)

The cue-detection DSP was built on **numpy + scipy** (both already deps) — spectral-flux
onset, autocorrelation tempo/beat-grid, RMS energy curve. No librosa (heavy: numba/llvmlite),
no aubio, no CLAP. Install stays green; Gemini-only-AI constraint untouched (deterministic DSP
is not an "AI provider"). The librosa-vs-aubio-vs-Rust-sidecar question is moot for v1.

Real-track behaviour (the honest finding): on Demo Track 1 it kept INTRO + BREAKDOWN@115s and
**gated the DROP@119.8s at conf 0.83** (just under the 0.85 bar); on Demo Track 2 it gated all
structural cues (conf 0.03 / 0.32) — it only emits what it is confident about. This is anti-slop
working as intended, and exactly the kind of threshold/quality call Kaan's ear-test settles: if
the gated DROP is real, the 0.85 bar (or the detector's surge scaling) is the tuning knob.

A future accuracy lift (deferred, optional): beat-grid from a dedicated model (Beat This! via a
Rust sidecar, already in the v3.x backlog) would tighten downbeat snapping — but it is an
accuracy upgrade, not a prerequisite. The v1 detector ships on numpy/scipy.
