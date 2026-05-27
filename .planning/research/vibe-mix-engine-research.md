# Vibe Mix Engine — Implementation Research (Energy · Sequencer · Export)

> Hardened findings from 3 parallel research agents (2026-05-26), folded for the wiring effort.
> Companion to `vibe-mix-agent-engine-synthesis.md` (the scope decision). All three engine
> modules are **pure-compute, no Gemini, offline-unit-testable, zero new deps**.

---

## A · Energy model v1 (`library/energy.py`)

**Critical correction:** neither `essentia` nor `librosa` is installed (CLAUDE.md's "essentia in stack"
is WRONG — essentia is **AGPLv3 = poison** for Apache+Bravoh-commercial; do not add it, fix the doc).
The DSP stack is hand-rolled numpy + ffmpeg/PyAV decode. **Reuse existing primitives, add NO deps.**

Reusable primitives:
- `library/cue_detect.py:134` `decode_to_mono(path, sr=16000)` — ffmpeg → mono float32 (the offline decode).
- `audio/features.py:27` `snapshot_features` (RMS + onset rate + 5-band split); `:125` energy curves; `:165` `estimate_bpm` (autocorr → beat-regularity prominence).
- `state/genre/crest_factor.py:31` `crest_factor` (peak/RMS, loudness-war flag).
- `state/detectors/_dsp.py` `sub_share` (:156), `band_spectral_flatness` (:112), `kick_band_centroid` (:60).

**Formula critique:** the spec's v1 over-indexes on level (RMS 0.30 + sub 0.20 = loudness traps; reads a
quiet hypnotic afterhours track as low-energy — the make-or-break failure). Biggest gap: **no spectral
flux**, the single strongest perceived-arousal predictor (flux+entropy ≈ 65% of arousal variance).

**Recommended v1 weights (sum 1.0, → ×100):**

| Feature | Primitive | Weight | Normalization |
|---|---|---|---|
| Loudness (crest-corrected, P80 dBFS) | `energy_curve` + `crest_factor` | 0.18 | fixed dBFS window |
| Sub-bass **share** | `sub_share` (busy-frame mean) | 0.15 | already [0,1] |
| Onset rate | `snapshot_features` onset path | 0.15 | fixed onsets/s window |
| **Spectral flux (NEW, ~15 LOC)** | rfft frame diff, half-wave rectified | **0.22** | per-track P80 |
| Brightness (centroid) | rfft centroid | 0.15 | fixed Hz window |
| Beat regularity | autocorr prominence | 0.08 | z-score clamp |
| RMS dynamic range (CoV) | std/mean of energy_curve | 0.07 | fixed window |

**Normalization = fixed perceptual windows + `np.clip` per track, NOT corpus min-max** (corpus min-max =
"one loud track skews everything" + non-reproducible re-ranking). Aggregate over *busy* frames only
(RMS > 5% of peak — the `cue_detect` mask) so intro/outro dead air doesn't contaminate. Weights live in
`audio/constants.py` as tuning constants (one-line-edit ethos). Genre-robustness levers: demote raw RMS,
promote flux/brightness, crest-correct loudness, use shares/ratios everywhere.

**Validation (cheap, no 200-track hand-label):** pairwise ranking test (~30 known A>B pairs: peak banger >
deep intro), within-track monotonicity (drop window > breakdown window), and a **hypnotic regression
guard** (quiet-energetic afterhours > loud-sparse ambient) as a unit test. Synthetic fixtures
(`bench/fixtures.py`) for DSP unit pins. ~120-180 LOC + ~80 LOC tests.

**Future (NOT v1):** XGBoost regressor (keep the 7 features as its future feature vector → swap linear
combiner for trained); 1001Tracklists position-as-ground-truth (scraping → Bravoh). Both parked.

---

## B · Sequencer (`library/sequencer.py`)

**Problem shape:** NOT TSP/Hamiltonian — it's **fixed-length subset-selection + ordering** under a
*positional* energy target (same track has different cost at slot 3 vs 17) with a non-Markovian
distinctness constraint. Model = depth-N trellis; beam search is the right tool (A* with a hard frontier
cap, no admissible heuristic needed; ILP/CP-SAT rejected = heavy dep).

**`energy` does NOT exist on `TrackEntry`** (only bpm/key/duration_s). → sequencer takes
`energy: dict[str,float] | None`; missing → min-max-normalized **BPM proxy** scaled 0-100; missing BPM too
→ energy term contributes 0 (coherence+harmonic-driven). **Never block sequencing on the DSP energy pass.**

**Design (~280-320 LOC, pure stdlib + numpy + harmonics + _cosine):**
- **Pool prep:** one bulk `store._backend.load_all()` → `(ids, vecs)`; per track build `PoolTrack(vec=l2_normalize, bpm or None, camelot=to_camelot(key), energy)`. Skip ids absent from store/library (Invariant #2 grounding).
- **Precompute two M×M matrices once** (M≈50, trivial): `coh = V @ V.T` (pairwise cosine = `sonic_coherence`, vectors are unit-norm so dot = cosine) and `valid[a,b]` (transition gate).
- **Transition gate** (`_transition_valid`): Camelot — reject ONLY when both keys known and `not harmonics.compatible(a,b)` (mirror `next_suggestion.py:119-126` both-known degrade; `compatible` returns False on unknown so missing-key must be a pass, or the graph collapses). BPM — reject only when both known and `|Δ| > 6%·bpm_a`. Structure — placeholder True until cue data wired.
- **Cost:** node `α·(energy−curve[slot])² − γ·surprise + δ·recency + ε·library_bias`; edge `β·(1−coh[a,b])`. **Normalize each term to [0,1] across pool** so α..ε are sane [0,1] taste dials (else the squared energy term, range ~10⁴, silently dominates 1−cos, range ~2).
- **Beam loop:** seed slot 0 with cheapest node-cost tracks (width ~48, adaptive `min(W, max(8,M))`); expand each beam by valid distinct neighbors; **dominance dedup** on signature `(last_track, used_set)` (two partials with same tail+used-set are interchangeable for the future → keep cheaper) — this is exact pruning AND diversity; optional prefix-cap for visible variety.
- **Curve** parameterized by **normalized set-position**: `np.interp` resample preset → exactly `n_slots`. Cleanly handles "fewer tracks than pool" + variable-length. Optional duration-weighting for a true time-based 90-min arc.
- **3-5 candidate paths:** Jaccard-diverse final selection (`jaccard_max≈0.7` → each ≥30% different tracks), OR re-run with weight presets (coherence-heavy "smooth journey" / surprise-heavy "peak roller" / strict-curve) for character-diverse optionality. Each carries `cost`, `energy_fit`, `avg_coherence` for honest UI labels.

**Edge cases (relaxation ladder, never fabricate):** sparse graph → widen BPM 6→8→12%, then drop
cross-letter strictness, then allow unknown-key bridges (penalized), then lowest-`is_clash` with big
penalty — each relaxation TAGGED so UI warns ("BPM jump here"); whole frontier dead → `break`, return
honest short set; pool < slots → shorten + resample curve; near-dup tracks (cos>0.995 + same title) →
pre-dedup so the set can't "mix a track into itself".

**Curve presets** (0-100, resampled): opener (low→max~75), peak-time (med→sustained 85-95), after-hours
(med-high, hypnotic oscillation, no big drops), festival (multi-peak, fast recovery), custom (DJ-drawn).

Runtime: ~10k partial evals × microsecond cosine → **<100ms**, huge margin under the 2s budget.

---

## C · Rekordbox export (`library/export_rekordbox.py` + `harmonics.to_classical`)

**pyrekordbox 0.4.4 `RekordboxXml` WRITE path works under our `--no-deps` install** (verified end-to-end;
`rbxml.py` is pure-stdlib `xml.etree` + `bidict`, ZERO SQLCipher coupling). **Do NOT hand-roll
ElementTree** — the library handles URI encoding, Rating bidict, Type bidict, Entries bookkeeping, dedup.

**Format decision:** emit a self-contained `collection.xml` (`DJ_PLAYLISTS → PRODUCT + COLLECTION +
PLAYLISTS`) — the ONLY format carrying order **+ cues + beatgrid** in one file. M3U = order only, zero
cues (rejected for the rich path; keep `create_playlist`'s M3U as the neutral fallback).

**API:**
```python
from pyrekordbox.rbxml import RekordboxXml
xml = RekordboxXml(name="vibemix", version="1.0.0", company="Bravoh")
t = xml.add_track(location="/abs/path.wav",  # plain path; SETTER URI-encodes (never pre-encode)
                  Name=..., Artist=..., AverageBpm=128.0, Tonality="Am",  # CLASSICAL key, not Camelot
                  TotalTime=312, Genre=..., Colour="0xFF007F")
t["Rating"] = 4                              # use SETTER for byte-mapping (kwargs bypass it → pass 204)
t.add_tempo(Inizio=0.012, Bpm=128.0, Metro="4/4", Battito=1)   # beatgrid (single node = constant tempo)
t.add_mark(Name="DROP", Type="cue", Start=64.5, Num=0)          # hot cue A; Num=-1 = memory; loop needs End
pl = xml.add_playlist("vibemix — Saturday Set", keytype="TrackID")
pl.add_track(t["TrackID"])                   # repeat in SET ORDER
xml.save("/path/set.xml")                    # pretty, 3.12 takes xml.indent branch
```
Gotchas: dedup by Location BEFORE add_track (raises `XmlDuplicateError`; reference TrackID multiple times
in the playlist for repeats); don't mutate the tree (Entries assertion); kwargs must be in `Track.ATTRIBS`.

**Camelot→classical inverse needed** (we have `to_camelot`, not the reverse). Add to `harmonics.py` next
to `to_camelot` — a 24-entry `_CAMELOT_TO_MUSICAL` dict + `to_classical(camelot)->str|None` (honest-null;
canonical spelling per code: `8A→Am, 8B→C, 11A→F#m`...). Round-trip-testable against the forward table.

**Import UX (Rekordbox 6/7):** Preferences → View → enable "rekordbox xml"; Advanced → Database →
rekordbox xml → point "Imported Library" at our file; the playlist appears under the xml node →
right-click "Import To Collection". Preserves order + memory cues + hot cues (A-H) + beatgrid + key/BPM/
genre/rating/track-colour. Location must match the file's real disk path (own-library tracks → already
correct). For already-cued tracks, our cues may not override the DJ's (and shouldn't) — the guaranteed
win is **order**; cues are most valuable for not-yet-analyzed tracks.

**v1 scope:** order + Tonality(classical)/BPM/TotalTime/Name/Artist/Genre/Colour/Rating + memory & hot
cues + single TEMPO. **Hot-cue COLOR = 0.4.4 gap** (`PositionMark.ATTRIBS` has no RGB) → document
"colors assigned by Rekordbox". ~1 focused day. Serato (binary GEOB via `serato-tools` MIT) + Engine DJ
(SQLite) = separate future phases, Rekordbox first (zero new dep, no file mutation).
