# Vibe Mix Agent Engine — Synthesis, Doability & Wiring Plan

> Source spec: `VibeMix_Discovery_Sequencing_Spec_EN.pdf` (Francesco → Kaan, v1.0, 2026-05-24).
> This doc: assess the spec against the **real vibemix codebase + locked constraints**, decide
> what is buildable NOW vs deferred-commercial vs constraint-conflict, and define the agent
> tool surface to wire. Date: 2026-05-26.

---

## 0 · TL;DR

The spec describes **Vibe Mix = Discovery + Sequencing**, a DJ set-prep engine. vibemix already
ships the *seed* of this: a grounded Gemini function-calling agent (`ViberAgent`) with 3 tools
(`search_vibe` / `get_track_features` / `create_playlist`) + a 1-step harmonic next-track engine
(`next_suggestion`). The spec's **Discovery centroid/MMR/filters, Sequencing energy-curve/beam-search,
Energy model, and Export to DJ software are NOT in the code at all.**

**Decision (scope, value-driven, no-creep):** build the **library-local (Mode A) slice** into the
existing Viber agent engine — turn a flat playlist into a *sequenced, energy-curved, harmonically-valid
set the DJ can export to Rekordbox in one click*. This is the deep, in-scope, Apache-clean, zero-new-dep
value. **Defer the spec's commercial half** (public catalog via Beatport/Spotify/SoundCloud APIs,
affiliate revenue, the 1001Tracklists-scraping "moat", XGBoost energy regressor) to **Bravoh-side** — it
is network/affiliate/IP-moat work that violates vibemix's no-network-API + no-scope-creep + OSS posture.

---

## 1 · Spec ↔ vibemix constraint reconciliation

The PDF was written for the broader BRAVOH/commercial stack and names tools vibemix has explicitly
rejected or replaced. The conflicts (must be honored — they are LOCKED memory decisions):

| Spec says | vibemix reality (LOCKED) | Resolution |
|---|---|---|
| LLM reasoning = **Claude Sonnet** | **Gemini-only. NO Anthropic API in product.** | Reasoning layer = the existing Gemini `ViberAgent`. ✅ already compliant. |
| Personalization = **Mem0** | **Mem0 REJECTED** → sqlite-vec + Gemini-embed DIY (`memory/`), recency via local store. | Recency penalty = local `played_ids` / memory.db, not Mem0. |
| Audio embeddings = **StyleDNA / Pinecone** | **sqlite-vec local + CLAP (audio→audio) / Gemini (text)**. | Vector ops on the existing local `library.db`. |
| Public catalog = **Beatport / SoundCloud / Spotify APIs**, affiliate links | vibemix is **local-only, no network catalog, no affiliate**; that is the Bravoh commercial product. | **DEFER to Bravoh.** OSS vibemix = Mode A (own library) only. |
| Energy moat = **XGBoost regressor + 1001Tracklists scraping** | scraping/IP-moat = commercial; librosa is the only permissive MIR lib (essentia is AGPL → poison). | v1 = librosa/numpy formula (Apache-clean). XGBoost/scraping = Bravoh, parked. |
| Fingerprinting = **Chromaprint / AcoustID** (match local→public catalog) | only needed to inherit *public-catalog* embeddings — which we defer. | DEFER (couples to the deferred public catalog). |

**Net:** the spec's *algorithms* (intent centroid, hard filters, MMR, energy curve, transition graph,
beam search, LLM reasoning, DJ-software export) are all buildable inside vibemix's constraints using
**local library data + numpy + Gemini + Apache-clean libs**. The spec's *data sources & business model*
(public APIs, affiliate, scraping moat) are the commercial Bravoh layer and stay out.

---

## 2 · Current agent engine — what exists

- **`library/agent.py` — `ViberAgent`**: bounded Gemini fn-calling loop (`MAX_TOOL_ITERATIONS=12`,
  per-call + per-tool timeouts), one-shot + interactive (`ask_user`), persona via shared matrix seam +
  lens, consent-gated taste hint. **This IS "the agentic co-host" engine** to extend.
- **`library/toolset.py` — `LibraryToolset`**: the 3 grounded tools + seen-set gate (Invariant #2) +
  library re-validation. Shared verbatim with the Codex MCP backend (`mcp_server.py`) so grounding
  never drifts. **New tools must land here** (single tool core) so both backends inherit them.
- **`library/next_suggestion.py`**: 1-step "what's next" — mean-centered cosine + Camelot/BPM
  post-filter. Already a *transition primitive*: it knows `harmonics.compatible` + a BPM window. The
  sequencer generalizes this from 1 step to an N-slot path.
- **`state/harmonics.py`**: `to_camelot()`, `compatible()` — the transition-graph edge test, done.
- **`library/store.py`**: sqlite-vec store, `search_centered` (mean-centered KNN), `load_all`.
- **`library/rekordbox.py` / `importer.py` / `cue_detect.py`**: library ingest + cue anchors.
- **`audio/features.py`**: RMS / spectral / onset DSP — the energy-model feature substrate.
- **`runtime/suggestion.py` — `SuggestionService`**: surfaces `next_suggestion` to the live pill.

**Gap = everything the spec calls Discovery-pool-building (centroid/filters/MMR) and all of Sequencing
(energy, curve, graph, beam search, export).** Pure-Python, no new deps, Apache-clean.

---

## 3 · Doability matrix (spec element → verdict)

| Spec element | Verdict | Notes |
|---|---|---|
| **Discovery §1** Intent centroid (multi-ref + text blend) | **DOABLE NOW** | weighted mean of stored vectors + α-blend Gemini text embed. numpy. |
| KNN over private index | **DONE** | `store.search_centered`. (public index = DEFER) |
| Hard filters (BPM range, Camelot ±1/rel, duration, recency, exclude) | **DOABLE NOW** | filter step over candidates; `harmonics` + `played_ids`. |
| MMR diversity re-rank | **DOABLE NOW** | `score = λ·sim(intent) − (1−λ)·max_sim(selected)`. ~40 LOC numpy. |
| Public catalog (Beatport/SC/Spotify), purchase links, affiliate | **DEFER → Bravoh** | network APIs + affiliate = commercial, out of OSS scope. |
| Fingerprinting (Chromaprint/AcoustID) | **DEFER** | only needed for public-catalog match (deferred). |
| **Sequencing §2** Energy curve presets + custom | **DOABLE NOW** | array of N targets; presets opener/peak/afterhours/festival. |
| Transition graph (Camelot + BPM±6% + structure) | **DOABLE NOW** | `harmonics.compatible` + BPM window; structure = embedding-coherence proxy / cue overlap. |
| Beam search path-find (multi-objective cost) | **DOABLE NOW** | pure Python ~300 LOC (research agent confirming design). |
| LLM reasoning layer ("the why", clickable swap) | **DOABLE NOW** | Gemini (not Sonnet); a new agent tool / post-pass over the chosen path. |
| **Energy model §3** v1 librosa formula | **DOABLE NOW** | RMS/sub-bass/onset/beat-reg/centroid composite (research agent hardening). |
| XGBoost regressor (phase 2) | **DEFER** | training data + model; later. |
| 1001Tracklists scraping moat (phase 3) | **DEFER → Bravoh** | scraping + IP moat = commercial. |
| **Export §2.5** Rekordbox XML (order + cues) | **DOABLE NOW** | pyrekordbox XML / hand-rolled writer (research agent confirming). In scope (local file). |
| Serato (binary, serato-tools) | **DOABLE LATER** | serato-tools lib (MIT) exists; 2nd export. |
| Engine DJ (SQLite) | **DOABLE LATER** | 3rd export. |
| Traktor | **DEFER** | ~5% share, phase 2 in spec. |

---

## 4 · The wiring vision — agent tool surface

Today the agent flow is: `search_vibe → (peek features) → create_playlist` (a flat list). The wired
flow becomes a real **set-prep co-host**:

```
brief → discover_pool(refs/prompt, mode=library)   # centroid + KNN + hard filters + MMR → ~50 pool
      → sequence_set(pool_ids, curve=peak_time)     # energy + transition graph + beam search → ordered path
      → (LLM reasoning: the "why" per transition, inline)
      → export_set(set_ids, target=rekordbox)       # one-click crate w/ order (+cues/beatgrid)
```

**New tools (land in `LibraryToolset` so both Gemini + Codex backends inherit; grounding gate unchanged
— every track_id still flows through the seen-set):**

1. `discover_pool(query|ref_track_ids, k=50, bpm_min/max, key, exclude_played_days, exclude_ids)`
   → ranked pool (centroid → KNN → hard filter → MMR). Records ids in `seen`.
2. `get_track_energy(track_id)` → energy 0-100 (cached; computed via the v1 formula). Deterministic
   fact, honest-null when no audio.
3. `sequence_set(track_ids, curve_preset|curve_array, n_slots)` → ordered path(s) + per-slot energy +
   transition annotations. Pure-compute, grounded (ids must be in `seen`).
4. `export_set(track_ids_in_order, name, target=rekordbox)` → writes a Rekordbox-importable file.
   The single new validated write (mirrors `create_playlist`'s gate).

**Engine modules (pure compute, unit-testable offline, no Gemini):**
- `library/energy.py` — `compute_energy(audio|features) -> float` + corpus normalization.
- `library/sequencer.py` — `build_transition_graph`, `beam_search_sequence`, energy-curve presets.
- `library/discovery.py` — `intent_centroid`, `hard_filter`, `mmr_rerank`.
- `library/export_rekordbox.py` — XML writer for an ordered set.

The agent (`ViberAgent`) gets a **"set-prep" system-instruction variant** (sequence after discover,
explain the why, offer export) layered on the existing matrix/lens seam — no persona drift.

---

## 5 · Scope decision (what we build NOW)

**IN (this effort, OSS vibemix, Mode A library-local):**
- `library/energy.py` (v1 formula) + cache.
- `library/discovery.py` (centroid + filters + MMR over the local store).
- `library/sequencer.py` (energy curve + transition graph + beam search).
- `library/export_rekordbox.py` (ordered playlist + key/BPM + memory cues; hot-cue color = known gap).
- New `LibraryToolset` tools + agent set-prep flow.
- Tauri UI: a "Build a Set" path in the Curate view (curve preset picker + sequenced result + Export
  button) — wired end-to-end, every control tested live.

**OUT (defer → Bravoh commercial / later phases):**
- Public catalog (Beatport/Spotify/SoundCloud), purchase links, affiliate (Modes B/C).
- Fingerprinting (Chromaprint/AcoustID).
- XGBoost energy regressor + 1001Tracklists scraping moat.
- Serato / Engine DJ / Traktor export (Rekordbox first; others follow once v1 proves out).

**Why this is "deep value, not complication":** the DJ gets the thing they actually pay hours for —
*"give me a sequenced, harmonically-correct, energy-curved set from my own crate, ready to load"* —
using only their library, offline, free, grounded (never a hallucinated track), with the AI explaining
*why* each transition works (mentor not black-box, the spec's competitive delta). No new providers, no
network, no license risk.

---

## 6 · Open inputs (research agents in flight — 2026-05-26)

- **Energy v1 formula** — feature set / weights / normalization / essentia license confirm. *(agent A)*
- **Beam-search sequencer** — select-AND-order design, beam width, dead-ends, 3-5 ranked paths. *(agent B)*
- **Rekordbox XML export** — pyrekordbox write path vs hand-rolled, import UX, cue/beatgrid preservation. *(agent C)*
- **Codebase + UI control map** — agent call sites, IPC surface, full button inventory for the live
  verify pass, sequencing seams. *(agent D)*

→ On return: fold findings in, then `gsd-new-milestone` → `gsd-autonomous` phase-by-phase, each phase
shipping one connected, tested wire. Test deeply per [[feedback_verify_live_app_not_just_tests]]
(real `cargo tauri dev`, ui.log, every button), not just green units.
