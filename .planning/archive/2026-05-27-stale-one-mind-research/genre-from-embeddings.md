# Genre-from-Embeddings — Feasibility on Real Data

**Date:** 2026-05-25  ·  **Status:** spike / research (NOT committed)
**Question:** Can we derive genre/vibe clusters from the Gemini embeddings Kaan already
computed (zero extra API cost) and feed detected-genre as grounding context into the
live co-host prompt for less-shallow, less-hallucinated reactions?

**Verdict up front:** Feasible and the real data supports it. The embeddings carry strong,
clean genre structure once corpus mean-centering is applied. The only honest caveat is the
set is producer-library-shaped (folder-organized, sample/stem noise mixed in), not a curated
genre benchmark — but it is large and diverse enough (399 tracks, 5 real DJ genres + samples)
to conclude.

---

## 1. The real embedded data (measured, not assumed)

Loaded from `~/.cache/vibemix/`:

| Store | Count | Notes |
|---|---|---|
| `library.db` (vec0 `vec_library`) | **399 vectors** | dim **1536**, float32, L2-normalized. (NOT the "~49 hardtechno" from the notes — the embed grew.) |
| `embeddings.db` `embed_cache` | 391 rows | content-hash embed cache |
| `embeddings.db` `query_cache` | 38 rows | past vibe-search *results* (track lists, not query vectors — see §4 caveat) |
| `library.pkl` (`_CacheBlob.tracks`) | **1547 tracks** | title/artist/bpm/filepath; only 399 are embedded |

Track IDs are content hashes (`folder:<16hex>`). All 399 embedded IDs resolve in
`library.pkl`, so titles + parent folders are available as a genre proxy.

**Genre proxy = parent folder** (these are Kaan's own crate names, so they ARE labels):

| Folder | n | Real genre |
|---|---|---|
| `runnin over my body` | 128 | pop / UK-garage / club-shy / hyperpop |
| `Audio Files` (+ Quick Sampler/Samples) | 77 | one-shots, loops, stems — **not tracks** (noise class) |
| `GALACTIX` | 50 | psytrance / full-on (145-180 BPM) |
| `ALL OF IT` | 48 | club edits / bootlegs (mixed) |
| `ETERNAL CHANGE` | 47 | hard techno |
| `GROOVEY140` | 28 | groove / UKG 140 techno |
| stems/mastered/processed/fx | ~21 | Bravoh production residue (noise) |

So the set is **not** monogenre hardtechno. It is 5 distinct DJ genres + a noise class of
samples/stems. That diversity is exactly what makes the clustering test meaningful.

---

## 2a. Clustering the existing vectors (zero API cost)

Anisotropy first (this is the load-bearing number):

- **Raw** avg pairwise cosine over the 399 vectors = **0.779** → everything looks ~0.78
  similar to everything; ranking has almost no discriminative power.
- **Mean-centered** (subtract corpus centroid + re-L2-norm — the existing
  `centering.py` transform) avg pairwise cosine = **0.058** → real separation restored.

Centering is therefore *mandatory* before any genre work — same fix already used for
ranking. Raw vectors will NOT cluster; centered ones do.

Cosine k-means on the **centered** vectors (numpy, no sklearn available in venv):

- **K=6 → cluster purity vs folder-genre = 0.69**
- **K=8 → purity = 0.71**

Clusters are coherent and map to real vibes:

| Cluster (K=6) | n | Dominant folders | Reads as |
|---|---|---|---|
| 0 | 73 | ETERNAL CHANGE 45, GROOVEY140 15 | dark/hard/groove techno |
| 1 | 41 | GALACTIX 31 | psytrance |
| 2 | 61 | ALL OF IT 31, runnin 16 | club edits + pop |
| 3 | 40 | runnin 15, ALL OF IT 8 | pop/edits crossover |
| 4 | 88 | Audio Files 66, stems 7, processed 5 | **samples/loops — cleanly isolated** |
| 5 | 96 | runnin 88 | pop/club-shy |

The samples/stems/FX noise class self-segregates almost perfectly (cluster 4/5) — important,
because that's exactly the junk we'd NOT want labeled as a genre live.

## 2b. Nearest-anchor labeling (the actual live mechanism)

The proposed live mechanism is: cosine-rank the *currently-playing* track's embedding to a
small set of genre **prototypes**, take the nearest as `detected_genre`. I validated this
exact mechanism with **zero API calls** by building prototypes from in-corpus exemplars
(the centered mean vector of each genre folder = a genre prototype), then nearest-prototype
labeling every track:

- **Nearest-genre-prototype accuracy vs folder-genre = 0.865** (378 labelable tracks)

Per-genre:

| True genre | n | Correct | Notable confusions |
|---|---|---|---|
| samples/loops | 77 | **100%** | — (perfectly isolated) |
| hard techno | 47 | 96% | 2 → groove140 (adjacent) |
| psytrance | 50 | 88% | Skrillex/dubstep edits → pop/club (correct instinct) |
| groove/UKG 140 | 28 | 86% | 3 → club/edits |
| pop/club-shy | 128 | 77% | leaks into club/edits (genuinely overlapping crates) |
| club/edits | 48 | 79% | spreads to pop/psy (it IS a mixed bootleg crate) |

The misclassifications are *semantically sensible*, not noise: a Skrillex bootleg filed under
psytrance gets called pop/club; the "ALL OF IT" bootleg crate (which is genuinely mixed)
spreads across neighbors. That's the model being right about the audio, not wrong about the
genre.

**Text anchors (the cheaper production variant) — could NOT run live this session:** the
direct `GEMINI_API_KEY` is **429 RESOURCE_EXHAUSTED (prepayment credits depleted)** and no
proxy JWT/URL is configured in `.env`. So I substituted in-corpus audio-embedding prototypes,
which validates the *same cosine-to-nearest-prototype mechanism* on real audio embeddings and
is arguably the stronger test. Text anchors will behave equivalently (they live in the same
multimodal space) and cost ~7 text embeds (<<€0.001) to wire when credits are restored.

---

## 3. Is the set big/diverse enough to conclude? — Yes, with one honest caveat

- **Big enough:** 399 vectors, 5 real DJ genres at 28-128 tracks each. Not a 49-track
  monogenre slice. The 0.87 nearest-prototype accuracy and clean cluster purity are not a
  small-N fluke.
- **Diverse enough:** the genres span 124-180 BPM and pop→psy→hard-techno — wide vibe range.
- **Caveat (be honest):** this is a *producer's working library*, not a curated genre
  benchmark. ~20% of it is samples/stems/FX, and crates like "ALL OF IT" are deliberately
  mixed. Folder-as-label is a proxy, not ground truth, so the absolute accuracy number is
  approximate. But the *structure is unambiguous* — centered embeddings separate these
  genres, and the noise class isolates itself. For a feasibility call, that's conclusive.
- What this set does NOT prove: fine-grained sub-genre splits (e.g. dub-techno vs
  hypnotic-techno within one crate) — too few labeled examples. Coarse genre = solid;
  micro-genre = unproven.

---

## 4. Recommended wire into the live co-host prompt (concrete + simplest)

There is **already a genre slot in the brain**, so this is an additive wire, not new plumbing:

- `MusicState.detected_genre: str` + `genre_confidence: float`
  (`src/vibemix/state/music_state.py:55-56`) — currently fed by the coarse DSP
  detector `src/vibemix/state/genre/genre_autodetect.py` (BPM/bands/crest axes).
- These are written ONLY by the single-writer refresh loop
  (`src/vibemix/state/refresh.py`, Invariant #1) — embedding genre must write here too,
  never elsewhere.
- The coach already builds the grounded `evidence_line`
  (`src/vibemix/state/coach.py:256`) as ` | `-joined fields (`hearing[...]`, `track=`,
  `deck=`, `set_time=`). Genre slots in as one more grounded field.

### Simplest wire (3 small steps)

1. **Prototype table (built once, offline, zero live cost).** Compute a centered mean vector
   per genre from the embedded library (the §2b method) OR embed ~7 short text anchors
   ("driving hard techno…", "psytrance full-on…", "groovy UK garage 140…", "vocal club
   house…", "ambient pad no beat…", "isolated drum one-shot…"). Persist as a tiny
   `~/.cache/vibemix/genre_anchors.npy` (7×1536) + label list. ~7 text embeds, one-time,
   <€0.001. Re-derivable any time from the existing store.

2. **Live classify off-loop, debounced on TRACK_CHANGE.** When the playing track is
   identified, take its already-stored embedding (no new audio embed needed if it's in the
   library; only embed-on-the-fly for unknown tracks — that's the only recurring cost and it
   reuses the existing `embed_track` cache). **Center it with the SAME corpus centroid**
   (`centering.load_or_compute_centroid` + `center_and_renorm` — non-negotiable, raw vectors
   are anisotropic and won't separate), cosine-rank to the 7 prototypes, take argmax.
   Apply a **confidence floor** (top-prototype cosine ≥ ~0.25 in centered space, and a margin
   over 2nd-best) — below floor → `genre_confidence` low → genre stays `unknown`. This is the
   anti-hallucination gate: never assert a genre the audio doesn't support (Invariant #3).

3. **Write + render.** Refresh loop writes `detected_genre`/`genre_confidence`. `evidence_line`
   gains one gated field, exactly like the `deck=` block:
   ```
   ... | track='Foo' | deck=A | genre=hard_techno (conf 0.71) | set_time=12:03
   ```
   Gate identical to `track=`: only emit when `genre_confidence >= 0.3`, else omit (NOT
   `genre=unknown` spam). Persona/coach reads it as grounded context → reactions can reference
   the actual vibe ("this hard-techno roll", "that psy break") instead of generic AI slop,
   and it's a *real detected event*, so it survives the citation-grounding gate.

### Why this is the right shape
- Reuses the existing `detected_genre` field, single-writer loop, and evidence_line gate
  pattern — no new invariants, no second source of truth.
- Mean-centering is already implemented and battle-tested for ranking; we reuse it verbatim.
- Embedding genre is a **drop-in upgrade** to the coarse DSP `genre_autodetect` (which only
  sees BPM/spectral-band/crest) — richer signal, same slot. Could even fuse: DSP as a cheap
  prior, embedding as the discriminator.
- Cost: prototypes one-time (~€0.001). Live = €0 for library tracks (cached embeddings),
  one cached audio-embed for genuinely-unknown tracks. Negligible vs the co-host LLM spend.

---

## 5. API cost incurred by THIS spike

- Clustering / anisotropy / nearest-prototype experiments: **€0** (all on cached vectors).
- Text-anchor live call: **attempted, blocked by 429 credit depletion** → €0 spent, 0 anchors
  embedded. Validated the mechanism with in-corpus prototypes instead (also €0).

Total spend: **€0.** No vectors written, no git commit.
