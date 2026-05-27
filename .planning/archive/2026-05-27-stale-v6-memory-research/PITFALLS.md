# Pitfalls Research

**Domain:** Adding a session-memory / embedding-retrieval layer to a real-time, grounded, anti-slop DJ co-host (vibemix v6.0 "The Memory Turn")
**Researched:** 2026-05-22
**Confidence:** HIGH (most pitfalls map to patterns vibemix already shipped — P55/P56/grounding thresholds in Phase 28; external sources corroborate the two load-bearing items)

> **Framing.** This is a SUBSEQUENT milestone. The memory layer does not start from zero — it extends a battle-tested embedding stack that already exists in `src/vibemix/library/` (Gemini Embedding 2 via Bravoh proxy, sqlite-vec storage-only + numpy fallback, shared `cosine_topk`, content-hash embed cache, event-gated grounding with 0.7/0.6 thresholds, €50/mo budget gate). The single biggest meta-pitfall is **re-inventing these seams instead of inheriting them.** Every pitfall below is cross-referenced to the existing mitigation it should reuse. The product's hard line — "grounded, never hallucinating, no AI slop, Kaan blocks release otherwise" — means the *retrieval-poisoning* and *confabulation* pitfalls are not perf concerns, they are **release-gate** concerns.

---

## Critical Pitfalls

### Pitfall 1: Retrieval Poisoning — irrelevant past moments injected into the live prompt

**What goes wrong:**
The retrieval seam grounds the coach prompt with top-k past moments at reaction time. If those moments are low-similarity (the DJ is doing something the library has no good match for), the LLM still receives them as context and treats them as relevant — it references a transition, a track, or a "you usually..." that has no bearing on the current set. Worse, because retrieval *always* returns its top-k regardless of absolute similarity, a brand-new genre/style produces confidently-wrong callbacks. This is the headline anti-slop risk: the AI references things that didn't happen *this* session, sounds scripted/fake, and Kaan blocks release.

**Why it happens:**
Cosine top-k is a *ranking*, not a *relevance gate*. `store.search(qvec, k)` returns the k nearest neighbours even when the nearest is at cosine 0.3. Developers wire "always inject top-k" because it's the RAG default. The failure compounds: the model paraphrases the weak match into a confident statement, which (if it ever feeds back into the store) becomes the amplified-hallucination loop documented in the Mem0 rejection (issue #4573: 808 amplified hallucinations from one seed).

**How to avoid:**
- **Reuse the existing threshold discipline verbatim.** The shipped grounding layer (`library/grounding.py`) already gates at `CITATION_THRESHOLD = 0.7` (cite), `UNCERTAIN_THRESHOLD = 0.6` (no cite, telemetry only), `< 0.6` (drop). The memory retrieval seam MUST apply the **same floor**: a past moment below the threshold is *not injected at all* — not injected-with-a-caveat, not injected. Empty retrieval is the correct, frequent, non-degraded state. (External RAG literature converges on the same: "only trust answers if similarity exceeds 0.75"; "noisy/irrelevant retrieval → hallucination almost guaranteed.")
- **Mark retrieved moments as PAST/citable, structurally separated from live evidence.** The prompt matrix already enforces hard framing seams: live audio is `PAST TENSE` ("that drop just hit"), lookahead is fenced `NOT YET HEARD BY AUDIENCE; do NOT describe as if it happened`. Retrieved memory needs its own fence — e.g. `FROM A PAST SESSION (not happening now)` — so the model can never blend a remembered moment into a live observation. A retrieved moment that is injected must be *citable* (carry a session-id/timestamp the model can attribute to), mirroring the `[track:<id>]` citation token + EvidenceRegistry pattern. If the model can't cite it as past, it shouldn't be in the prompt.
- **Keep the live audio/mic/lookahead as the PRIMARY evidence and memory as a strictly SECONDARY axis.** Memory grounds the *coach's framing*, it never overrides what the audio says is happening now. When live evidence and a retrieved memory conflict, live wins, full stop.
- **Cap injected memory volume.** One or two high-confidence past moments, not a top-10 dump. More retrieved context = more surface for the model to confabulate a connection.

**Warning signs:**
- AI says "you usually..." / "like last Friday..." in a session whose top-1 retrieval similarity was below threshold (catch via telemetry: log every retrieval's top similarity + whether it was injected).
- Citation linter (already exists: `coach/citation_linter.py`) starts flagging memory-derived claims that don't resolve to a stored session moment.
- Ear-test (Gate 2b) reactions feel "scripted" or reference a vibe the current set doesn't have.
- Replay harness: same audio with an empty store vs. a full store produces materially different reactions in the *wrong* direction.

**Phase to address:**
The Retrieval-seam phase (the phase that wires top-k past moments into the coach prompt). This is the hallucination-gate-relevant phase and should carry an explicit anti-slop success criterion: *a below-threshold session produces zero memory-derived references.*

---

### Pitfall 2: Confabulation via an extraction step (the no-LLM-extraction rule)

**What goes wrong:**
A tempting "improvement" is to run an LLM over each session to *summarize* it ("Kaan likes long blends, prefers tech-house, struggles with key clashes") and embed the summary instead of the raw artifacts. Every such extraction is a generative step that can invent facts not present in the session. Those invented "facts" then get embedded, retrieved, and grounded into future prompts as if they were observed — a confabulation that is now load-bearing and self-reinforcing.

**Why it happens:**
Raw `events.jsonl` / MIDI / track metadata feels "messy" and summaries feel "clean." Managed frameworks (Mem0/Letta/Zep) bake extraction in as core architecture — which is exactly why they were rejected. The recall→re-extract feedback loop is the documented killer: Mem0 issue #4573 found 97.8% junk and an amplified hallucination from a single seed. This is *the* hallucination class vibemix's anti-slop thesis exists to close.

**How to avoid:**
- **Raw-in / raw-out. No LLM between session and embedding.** This is already a *locked decision* (`v-next-memory-turn.md`, `mem0-rejected-2026-05-18.md`). Embed structured artifacts that are already typed: raw event records, raw track metadata, raw transcripts, raw MIDI move sequences. What goes in is what was there.
- **Embeddings of raw text/audio are fine; *generated* summaries are not.** Gemini Embedding 2 turning a raw event into a vector is not extraction — it's a deterministic projection of existing content. The forbidden step is an LLM *writing new prose* about the session.
- **If a human-readable label is needed for display, derive it deterministically** (template string from the typed fields, exactly like `embed.py:_text_signature` builds `"{title} by {artist} | {bpm} BPM | key {key}"`), never via an LLM.
- **Make the rule a CI gate.** Add a test/grep that fails if the ingest pipeline calls any chat/generation model (only `embed_content` is allowed in the ingest path).

**Warning signs:**
- A PR introduces a "summarize session" / "extract preferences" / "tag this session" model call in the ingest path.
- Stored records contain prose that no raw artifact contains.
- Retrieval surfaces a "fact" about the DJ that can't be traced to a specific raw event/timestamp.

**Phase to address:**
The Ingest-pipeline phase (session artifacts → typed embeddable records). The no-extraction invariant is a foundational contract of that phase and should ship with a CI guard.

---

### Pitfall 3: Embedding-everything bloat (cost, latency, storage)

**What goes wrong:**
"It's just embeddings, embed it all" — every audio frame, every 30s window, every event, every screenshot. Embedding cost (audio is $6.50/1M tokens vs $0.20 text — a 32× multiplier), index size, and ingest latency all explode. The €50/mo budget gate breaks, the store grows unbounded per install, and most of the embedded content never closes a hallucination class or unlocks a copilot move — it's pure noise that *also raises* retrieval-poisoning risk (more vectors = more chances for a spurious near-match).

**Why it happens:**
Embedding feels cheap per call. The audio-token cost surprise bites because audio is the expensive modality and DJ sets are long. The acid-test discipline gets skipped under "we'll prune later."

**How to avoid:**
- **Apply the acid test to every artifact, at ingest-design time:** *"Does retrieving this close a hallucination class or unlock a copilot move?"* If neither — don't embed it (`v-next-memory-turn.md`). This is the single most important scoping discipline of the milestone.
- **Start with structured, already-typed artifacts** (events, track metadata, MIDI move shapes), not raw audio. Audio embedding is the expensive path; only embed audio windows that the acid test justifies (e.g., a "transition shape" the copilot move actually calls back).
- **Reuse the budget gate.** `library/budget.py` already ships `project_monthly_cost(dau)` + a CI test `test_monthly_projection_under_50_eur` that blocks merge above €50/mo at 1000 DAU. Extend its call-rate model to include the new memory-ingest path; do not introduce a parallel budget accounting system.
- **Reuse the content-hash embed cache** (`embed.py` keys by SHA256 of file-bytes ‖ model-id ‖ strategy-version → `embeddings.db`) so re-ingesting the same session does zero API calls.
- **Reuse 768-dim MRL truncation** (`_cosine.EMBEDDING_DIM = 768`, 4× smaller than native 3072) for the memory index too — bumping it requires a cache invalidation.

**Warning signs:**
- Budget projection test trends toward the €50 ceiling as the ingest scope grows.
- Per-install DB size grows linearly with session minutes (audio-everything tell).
- Ingest of one session takes minutes, not seconds.
- Most stored vectors never appear in a top-k that crosses threshold (dead weight — instrument this).

**Phase to address:**
The Ingest-pipeline phase decides *what* gets embedded (acid-test enforcement); the budget gate verification rides in the same phase. The "which artifacts ground best" question is explicitly the first phase's research per the milestone notes — resolve scope there, not by default.

---

### Pitfall 4: sqlite-vec one-click-install fragility on Mac + Win

**What goes wrong:**
The memory layer needs a vector store. `sqlite-vec` loads a native extension (`vec0.dylib` / `vec0.dll`) into SQLite at runtime via `enable_load_extension` + `sqlite_vec.load(db)`. This breaks in several install-specific ways that a dev machine never sees: (a) the OS-bundled Python's SQLite is compiled *without* extension support (default macOS Python, and Windows' bundled SQLite); (b) the platform wheel is missing for the host arch (notably ARM64 Windows); (c) on Windows the `.dll` loads but a transitive dependency doesn't — the infamous "The specified module could not be found" (sqlite-vec issues #13, #45); (d) inside the Tauri-sidecar PyInstaller bundle the extension binary isn't collected, or its path resolves wrong; (e) the unsigned `.dylib`/`.dll` trips macOS Gatekeeper/notarization or Windows SmartScreen. Any of these turns the one-click install (a HARD requirement) into a crash-on-first-memory-use.

**Why it happens:**
Extension loading is a runtime, host-dependent operation that works perfectly in the dev venv and fails only on a clean target machine. Native binaries inside a frozen bundle are a classic PyInstaller blind spot. Code-signing a *transitively-loaded* native lib is easy to forget because it's not the main binary.

**How to avoid:**
- **Inherit the existing probe-and-fall-through pattern, do not re-architect storage.** vibemix *already shipped this exact mitigation* in Phase 28: `library/store.py:open_store()` tries `SqliteVecStore`, and on **any** exception from `sqlite_vec.load(...)` logs structured diagnostics and falls through to `NumpyStore` (Assumption A2, "Wave 0 sqlite-vec ARM64 Win probe"). The memory store MUST use the same facade so it inherits the fallback for free. NumpyStore + the shared `cosine_topk` gives bit-identical results — there is no correctness penalty to the fallback, only a perf one at large N.
- **Treat sqlite-vec as storage-only** (P55 mitigation, already in place): never use the extension's internal `vec_distance_cosine` KNN — load vectors out and rank with the shared Python `cosine_topk`. This means the *only* thing the extension does is store blobs, so the numpy fallback is a complete substitute and the extension being unavailable degrades gracefully rather than breaking ranking.
- **Sign + notarize the native binaries.** `vec0.dylib` (Mac) and `vec0.dll` (Win) must be in the Apple notarization set and (where applicable) the SignPath Authenticode set, alongside the main sidecar. This rides the *existing* signing pipeline (`release.yml`, companion-sign workflow) — add the extension binaries to its inputs.
- **Verify collection in the PyInstaller/Tauri sidecar build.** Add the sqlite-vec extension binary to the bundle datas/binaries and assert at runtime that the resolved path exists; the e2e install-matrix harness (`tests/e2e/macbook/`, `install_vm_matrix.sh`) must exercise a *real* memory write/read on a clean VM, not just import the module.
- **Don't assume the system SQLite supports extensions.** The probe already catches this (the `enable_load_extension`/`load` call raises → numpy fallback), but the install-matrix test should confirm the fallback actually triggers on a stock-Python host and the app stays functional.

**Warning signs:**
- Memory works in dev, crashes on a fresh VM (the canonical tell).
- Logs show `backend=NumpyStore reason=sqlite_vec_unavailable (...)` on machines that *should* support the extension (signing/packaging gap, not a true unsupported host).
- "The specified module could not be found" in Windows logs.
- Gatekeeper/SmartScreen blocks first launch after a memory feature ships.

**Phase to address:**
The Storage phase owns the store wiring (reuse `open_store()` facade). The install-fragility *verification* belongs to whichever phase touches the installer/sidecar bundle + signing for the memory feature — the e2e install-matrix must add a "memory round-trip on clean VM" gate. This is on the external-clock critical path (signing), so flag it early.

---

### Pitfall 5: Embedding cost/latency on the hot path

**What goes wrong:**
If retrieval embeds the query (the current audio window) *synchronously inside the reaction turn*, every reaction now waits on a Gemini embedding round-trip before it can even build the prompt. The live path already has a strict TTFT budget (`LIVE_TTFT_BUDGET_MS = 1500`); a blocking embed (network + audio-token processing) blows it, and the co-host reacts *late* — which is itself a release-blocking failure mode ("reactions feel late"). Audio embeds are the slow + expensive modality, so this is doubly bad on the hot path.

**Why it happens:**
The naive retrieval loop is "embed query → search → inject → generate," run inline per reaction. It works in tests with a warm cache and fast network; it fails live on a venue's flaky wifi.

**How to avoid:**
- **Keep embedding off the hot path.** Reuse the **event-gated** discipline from `library/grounding.py`: grounding embeds fire only on specific events (`TRACK_AWARE_EVENTS`), not every 30s, and the cost-gate comment (P56) is explicit that this is the difference between ~€27/mo and ~€1500/mo. The same applies to latency: gate memory-query embeds to events, don't run them every tick.
- **Run embeds in the executor, never blocking the loop.** The existing pattern wraps embed calls in `loop.run_in_executor(None, ...)` (documented in `embed.py`'s thread-safety note). Memory retrieval must do the same — the asyncio loop never blocks on an embed.
- **Reuse the query-embedding cache** (Phase 28 Plan 03's 24h LRU keyed on query + library-snapshot-hash). If the live audio window hasn't materially changed, don't re-embed it.
- **Precompute where possible.** Past-session vectors are computed *at ingest* (post-session, off the hot path), never at reaction time. The only hot-path embed is the *query* vector, and even that should be gated + cached + executor-offloaded.
- **Treat retrieval as best-effort with a hard deadline.** If the query embed or search doesn't return within a small budget, the turn proceeds with *no* memory grounding (live evidence is always sufficient on its own). Late memory is worse than no memory.

**Warning signs:**
- TTFT meter p95 regresses after the memory feature lands.
- Reactions arrive visibly after the moment they reference.
- Embed calls appear on the synchronous coach-turn stack trace.
- Latency spikes correlate with network conditions (hot-path network dependency tell).

**Phase to address:**
The Retrieval-seam phase. Success criterion: memory retrieval adds **zero** measurable latency to the live reaction path (verified against the existing TTFT budget) — i.e., it's event-gated, executor-offloaded, cached, and deadline-bounded.

---

### Pitfall 6: Privacy / retention of stored session embeddings + raw artifacts

**What goes wrong:**
The memory layer persistently stores embeddings *and* (per the raw-in/raw-out rule) raw session artifacts: `events.jsonl`, `voice.wav`, `input.wav` (the DJ's master output — which can include a mic capturing the DJ talking, and copyrighted music), MIDI moves, track metadata. This is sensitive user data accumulating on disk forever, per install, with no user-visible control. Privacy + storage-budget violations follow: unbounded disk growth, no delete path, embeddings that are hard to "forget," and the possibility of artifacts landing somewhere unexpected.

**Why it happens:**
Memory features bias toward "keep everything so retrieval gets richer." Deletion is an afterthought. Embeddings *feel* anonymized but are derived from (and can be associated back to) raw audio/transcripts, so they're not exempt from privacy/retention.

**How to avoid:**
- **Local-only, no exfiltration.** Storage stays on-device (`~/.cache/vibemix/`, the existing convention) — the only network egress is the *embedding API call through the Bravoh proxy*, which the existing proxy-only contract already constrains. No session artifact or embedding is uploaded for storage.
- **Inherit the retention + delete machinery already shipped.** Phase 15's `runtime/recordings_index.py` already does: deterministic session listing, **user-triggered delete** (regex + `is_relative_to` path-traversal defense, post-delete verification incl. Windows file-in-use), `compute_usage()` byte accounting, and `run_retention_sweep(root, retention_days)` with an ∞ sentinel. The memory store MUST hook into the *same* delete + retention sweep so that deleting a session **also deletes its embeddings** (no orphaned vectors), and so the existing retention slider governs memory too.
- **Size budget per install.** Define and enforce a max store size; the existing `compute_usage()` pattern and the install-uninstall contract (uninstall preserves user data unless `--clean` opt-in, INSTALL-08) extend to the memory DB.
- **User-deletable + transparent.** A user must be able to wipe memory (and see its size) from the same recording-browser surface. "Forget this session" deletes raw + vectors atomically.
- **Respect the hard privacy rule.** Memory storage paths must never overlap the off-limits Hermes/LM-Studio transcript paths; the e2e privacy fixture (asserts zero writes to `~/.hermes/`, `~/hermes-rig/logs/`, `~/.lmstudio/`) must extend to confirm memory writes only go to the sanctioned vibemix cache dir.

**Warning signs:**
- Per-install storage grows without bound across sessions.
- Deleting a session leaves its vectors in the store (orphan tell — query for vectors with no backing session).
- No UI affordance to view/wipe memory.
- Uninstall leaves the memory DB behind without the `--clean` opt-in (or wipes it without).

**Phase to address:**
The Storage phase (retention + size budget + delete-cascades-to-embeddings, reusing `recordings_index.py`). Privacy-fixture extension belongs to the e2e/install phase.

---

### Pitfall 7: Stale / cross-session leakage

**What goes wrong:**
Two distinct failure shapes. (a) **Stale leakage:** the retrieval surfaces an old moment that's no longer representative (the DJ changed style months ago) and the coach grounds in an outdated pattern — "personalization" calcifies into being wrong. (b) **Cross-session contamination:** the *current* session's own just-recorded moments leak into its retrieval (a moment from 30s ago is "remembered" as a past-session fact), or — on a shared/multi-user install — one person's sessions ground another's. Either way the AI references "history" that's irrelevant or self-referential, which reads as slop.

**Why it happens:**
A naive store is a flat bag of vectors with no time or session scoping. Hybrid time-weighting is listed as TBD in the milestone notes, so the default risk is "all history weighted equally forever." Ingesting the live session into the same store it retrieves from creates the self-reference loop.

**How to avoid:**
- **Resolve the retrieval blend deliberately** (cosine-only vs cosine + time-weight is an explicit open research question in `v-next-memory-turn.md`). Time-decay weighting down-ranks stale moments so recent style dominates; this is a research-then-decide item, not a default. Newer sessions should be able to out-rank old ones at equal cosine.
- **Scope the store per-install, and exclude the live session from its own retrieval.** Ingest happens *post-session* (off the hot path anyway, per Pitfall 5), so the current session is not even in the store while it's being played — this naturally prevents self-reference. Make that ordering an invariant: a session is embeddable only after it ends.
- **Tag every record with session-id + timestamp** (also required for the PAST-marking citation discipline of Pitfall 1). This makes "exclude current session," "time-weight," and "delete-this-session's-vectors" all trivial filters on the same metadata.
- **Don't over-engineer multi-user.** The install is single-user/local by design; the per-install scope is the boundary. Document that shared-machine multi-user is out of scope rather than building account separation.

**Warning signs:**
- The coach "remembers" a moment from earlier in the *same* live set as if it were a past session.
- Callbacks reference a style the DJ has clearly moved on from.
- Equal-cosine ties always resolve to the oldest session (no time-weight tell).
- Retrieval results include records with the current session's id.

**Phase to address:**
The Retrieval-seam phase owns the blend (cosine + time-weight) and the exclude-current-session invariant. Session-id/timestamp tagging is set in the Ingest-pipeline phase (so it's available to everything downstream).

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Always inject top-k, no similarity floor | Simpler retrieval code; "always has context" | Retrieval poisoning → release-blocking slop; the headline failure | **Never** — the threshold floor is the whole point |
| LLM-summarize sessions before embedding | "Cleaner" records, smaller index | Confabulation surface; amplified-hallucination loop (Mem0 #4573) | **Never** — locked decision, CI-guarded |
| Embed audio for everything | Richer retrieval | 32× cost of text; budget breach; index bloat; more poisoning surface | Only audio windows the acid test justifies |
| Synchronous query-embed in the reaction turn | Easiest wiring | Blows TTFT budget; reactions late on bad wifi | **Never** on the live path — gate + executor + cache |
| New parallel vector store instead of reusing `open_store()` | "Clean" memory module | Loses the sqlite-vec→numpy fallback + P55 parity for free; re-solves solved install fragility | Never — extend the facade |
| Flat store, no session-id/timestamp tags | Fewer columns | Can't exclude current session, can't time-weight, can't cascade-delete | Never — tags are cheap and load-bearing |
| Keep all sessions forever | Maximal recall | Unbounded disk; privacy exposure; stale-leakage | Only with a retention sweep + user-visible size + delete |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Gemini Embedding 2 (via Bravoh proxy) | Reading an AIza key directly in the ingest path; bypassing the proxy | All embeds go through `build_proxy_genai_client` — the proxy-only contract (`embed.py`) is the cost + privacy invariant; ingest inherits it |
| Gemini Embedding 2 | Forgetting the 180s audio cap → 400 on long clips | Reuse `embed.py`'s 3-excerpt-mean path + `_is_audio_cap_error` fallback (already handles the cap) |
| Gemini Embedding 2 | Dimension drift (768 vs 3072) silently corrupting cosine | Lock to `EMBEDDING_DIM = 768` via the shared constant; dimension changes require a cache-version bump (`EXCERPT_STRATEGY_VERSION`) |
| sqlite-vec | Trusting the extension to be present; using its internal KNN | Probe + numpy fallback (`open_store()`); storage-only, rank in Python (`cosine_topk`) — P55 |
| sqlite-vec native binary | Not signing/collecting `vec0.dylib`/`vec0.dll` in the bundle | Add to notarization + Authenticode set + PyInstaller binaries; verify on clean-VM e2e |
| ModelRouter | Hardcoding the embedding model literal | Resolve via `model_router.resolve("embedding")` (CI grep gate forbids literals) |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `load_all()` + full-scan cosine on every retrieval | Search latency grows with store size | Acceptable at small N (current pattern); revisit ANN only if a single install's store gets large | Linear scan starts to bite at tens of thousands of vectors per install |
| Audio-everything ingest | Disk + embed-cost growth linear in session minutes | Acid-test scope; embed structured artifacts first, audio only when justified | Per-install at a few hundred long sessions |
| Hot-path query embed | TTFT p95 regression; late reactions | Event-gate + executor-offload + 24h query cache + hard deadline | Immediately, on any network jitter |
| Re-embedding unchanged sessions | Repeated API spend; budget breach | Content-hash embed cache (`embeddings.db`) — already shipped | On every re-ingest / app restart without cache |
| No time-weight, store grows | Old moments dominate retrieval | Time-decay blend (research-decided) | Gradually, as history accumulates |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing raw `voice.wav`/`input.wav` with no delete path | Sensitive audio (DJ's mic, copyrighted music) accumulates forever, unrecoverable by user | User-triggered delete + retention sweep (reuse `recordings_index.py`); delete cascades to embeddings |
| Path traversal on session-id when deleting/reading memory | Arbitrary file delete/read via crafted id | Reuse the regex (`^\d{8}-\d{6}$`) + `is_relative_to(resolved_root)` two-layer gate already in `recordings_index.py` |
| Memory writes leaking outside the sanctioned cache dir | Could write to off-limits privacy paths | Extend the e2e privacy fixture to assert memory writes only hit `~/.cache/vibemix/`; never `~/.hermes/`, `~/hermes-rig/logs/`, `~/.lmstudio/` |
| Embeddings treated as "anonymous," exempt from privacy | Vectors derived from raw audio/transcripts are still personal data | Subject embeddings to the same retention + delete + local-only contract as raw artifacts |
| Unsigned native extension binary | Gatekeeper/SmartScreen block; supply-chain trust gap | Sign + notarize `vec0.*` in the existing pipeline |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| AI references "past sessions" the user can't see or verify | Feels like hallucinated slop even when correct | Make memory-derived references *citable* (surface which past moment, like the live citation strip) so the user can trust/verify |
| Memory feature is invisible — no proof it's working | "Personalization" claim with no evidence; feels gimmicky | The milestone's "1–2 visible copilot moves" — concrete, user-noticeable proof retrieval fired (calls back a real vocabulary/transition shape) |
| No way to see or wipe stored memory | Privacy anxiety; "what does it know about me?" | Memory size + per-session delete in the existing recording-browser surface |
| Cold-start: new user, empty store, AI tries to "remember" | Forced/fake callbacks with nothing to recall | Empty/below-threshold retrieval = silent (no memory references); the co-host is fully functional with zero memory |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Retrieval seam:** Often missing the *similarity floor* — verify a below-threshold session injects zero memory references (replay: empty-store vs full-store reactions diverge only when above threshold).
- [ ] **Ingest pipeline:** Often missing the no-extraction CI guard — verify the ingest path calls only `embed_content`, never a chat/generation model.
- [ ] **sqlite-vec storage:** Often "works in dev" only — verify a real memory write+read on a clean Mac + Windows VM (incl. ARM64 Win) and that the numpy fallback keeps the app functional when the extension is unavailable.
- [ ] **Native binary signing:** Often missed for transitively-loaded libs — verify `vec0.dylib`/`vec0.dll` are in the notarization + Authenticode set.
- [ ] **Hot-path latency:** Often regresses silently — verify TTFT p95 is unchanged with the memory feature on vs off.
- [ ] **Delete cascade:** Often leaves orphans — verify deleting a session removes its embeddings (no vectors with a missing backing session).
- [ ] **Current-session exclusion:** Often leaks — verify retrieval never returns the in-progress session's own records.
- [ ] **Budget gate:** Often unmeasured for the new path — verify `project_monthly_cost` still ≤ €50/mo at 1000 DAU with memory-ingest call rates included.
- [ ] **Privacy fixture:** Often not extended — verify memory writes are confined to the vibemix cache dir.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Retrieval poisoning shipped | HIGH (release-blocking) | Raise/enforce the similarity floor; add PAST/citable fences; cap injected count; re-run ear-test + replay gate before any release |
| LLM-extraction crept in | MEDIUM | Rip the extraction step; re-ingest raw; purge extraction-derived vectors (cache-version bump invalidates them); add the CI guard |
| sqlite-vec install breakage | LOW (fallback exists) | Confirm `open_store()` fell through to numpy and app is functional; fix signing/packaging; re-run install-matrix; no data loss (storage-only) |
| Hot-path latency regression | MEDIUM | Move embed to executor; event-gate it; add query cache + deadline; re-verify TTFT |
| Unbounded storage | LOW | Run retention sweep; expose size + delete UI; set size budget |
| Stale/cross-session leakage | MEDIUM | Add session-id/timestamp tags; add time-weight; enforce current-session exclusion; re-ingest with tags |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls. (Phase names are scope-spine roles from `v-next-memory-turn.md`, not yet numbered.)

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 1. Retrieval poisoning | Retrieval-seam phase | Below-threshold session → zero memory references (replay + ear-test Gate 2b); PAST-fence present in prompt; injected count capped |
| 2. Confabulation / extraction | Ingest-pipeline phase | CI guard: ingest path calls only `embed_content`; no prose in stored records |
| 3. Embedding bloat | Ingest-pipeline phase (acid-test scope) | Budget projection ≤ €50/mo at 1000 DAU; every embedded artifact passes the acid test |
| 4. sqlite-vec install fragility | Storage phase + installer/sidecar/signing phase | Clean-VM (Mac+Win+ARM64 Win) memory round-trip; numpy fallback keeps app functional; `vec0.*` signed |
| 5. Hot-path cost/latency | Retrieval-seam phase | TTFT p95 unchanged vs feature-off; embeds event-gated + executor-offloaded + cached + deadline-bounded |
| 6. Privacy / retention | Storage phase + e2e/privacy phase | Delete cascades to embeddings; size budget enforced; privacy fixture confines writes to vibemix cache dir |
| 7. Stale / cross-session leakage | Retrieval-seam phase (blend + exclusion) + Ingest (tagging) | Retrieval excludes current session; time-weight down-ranks stale; records carry session-id + timestamp |

## Sources

- `.planning/notes/v-next-memory-turn.md` — locked decisions, acid test, "what this is NOT" (HIGH — project source of truth)
- `.planning/notes/mem0-rejected-2026-05-18.md` — confabulation evidence: Mem0 #4573 (97.8% junk, 808 amplified hallucinations), #4099 Gemini ghost memories, #4540 silent fact loss; managed-framework rejection (HIGH)
- `src/vibemix/library/grounding.py` — shipped event-gated grounding, 0.7/0.6 thresholds, citation discipline (HIGH — existing code to inherit)
- `src/vibemix/library/store.py` + `index_sqlite_vec.py` + `_cosine.py` — shipped sqlite-vec→numpy fallback (Assumption A2), storage-only P55 parity, 768-dim lock (HIGH)
- `src/vibemix/library/embed.py` — shipped proxy-only embeds, content-hash cache, 180s audio cap 3-excerpt path, executor thread-safety note (HIGH)
- `src/vibemix/library/budget.py` — shipped €50/mo CI gate, audio vs text cost (32×), event-gating cost rationale (P56) (HIGH)
- `src/vibemix/runtime/recordings_index.py` — shipped delete (path-traversal defense), retention sweep, usage accounting (HIGH)
- `src/vibemix/prompts/matrix.py` — shipped PAST-TENSE + "NOT YET HEARD BY AUDIENCE" framing fences (the seams memory PAST-marking plugs into) (HIGH)
- [sqlite-vec issue #45 — extension does not load on Windows 11 ("specified module could not be found")](https://github.com/asg017/sqlite-vec/issues/45) (MEDIUM)
- [sqlite-vec issue #13 — pre-compiled extension won't load on Python/Win11](https://github.com/asg017/sqlite-vec/issues/13) (MEDIUM)
- [Using sqlite-vec in Python — Alex Garcia (default macOS/Windows SQLite lacks extension support)](https://alexgarcia.xyz/sqlite-vec/python.html) (MEDIUM)
- [RAGuard / RAGPart / RAGMask — retrieval-stage poisoning defenses (arXiv)](https://arxiv.org/pdf/2512.24268) (MEDIUM — corroborates threshold/filtering discipline)
- [PoisonedRAG — knowledge poisoning attacks (arXiv)](https://arxiv.org/html/2402.07867v1) (MEDIUM)
- [How to Stop LLM Hallucinations in RAG — similarity-threshold (>0.75) gating](https://sharur7.medium.com/how-to-stop-llm-hallucinations-in-retrieval-augmented-generation-rag-5ef2894f9cd6) (LOW — single source, corroborative only)

---
*Pitfalls research for: vibemix v6.0 "The Memory Turn" — session-memory/embedding-retrieval layer on a grounded anti-slop DJ co-host*
*Researched: 2026-05-22*
