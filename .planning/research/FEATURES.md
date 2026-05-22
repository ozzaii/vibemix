# Feature Research

**Domain:** Session-memory / retrieval-grounded copilot layer for a live DJ co-host (vibemix v6.0 "The Memory Turn")
**Researched:** 2026-05-22
**Confidence:** HIGH

> **Scope discipline.** This milestone adds a MEMORY LAYER to an already-shipped grounded
> co-host. Live audio/screen/MIDI grounding, hype + coach modes, deck-state awareness,
> harmonic key-clash, evidence-cited reactions, floating pill UI, post-session debrief
> are DONE — not re-researched here. The new thing: every session feeds an embedding
> store; coach prompts ground in PAST sessions; personalization is emergent from the
> retrieval seam (NOT a settings screen — Phase 32's ~2KB DJ profile already covers
> configured prefs).
>
> **Acid test applied to every candidate below** (from `v-next-memory-turn.md` + PROJECT.md):
> *"Does retrieving this close a hallucination class OR unlock a copilot move?"* — if neither,
> it is an anti-feature. Embedding a thing is not free: it is a confabulation surface, a
> distractor that can poison the live reaction, and a cost line. The bar is high.

---

## Executive framing: what the existing codebase already gives us

The memory layer is **not greenfield** — it slots into four existing seams. This is decisive
for every feature call below, so it leads:

| Existing seam | File | What it gives the memory layer |
|---------------|------|-------------------------------|
| **Typed session log** | `audio/recorder.py` → `events.jsonl` | The ingest source. Already typed records: `event` (`type`/`deck`/`track`/`phase`/`track_conf`), `llm_invoke` (full grounded prompt string + `invoke_dir`), `ai_text` (reaction + `latency_s`). A "moment" already exists as a typed triple. |
| **Citation grammar + registry** | `state/evidence_registry.py` | `EVIDENCE_SOURCES` frozenset (`ev aud midi track screen mix tend key`) + the EBNF linter + ack-bank strip. A new `mem:` source slots in by construction — the linter makes a fabricated past-callback *uncitable*. This is how memory inherits the anti-slop contract instead of re-inventing it. |
| **sqlite-vec + Gemini Embedding store** | `library/store.py`, `library/embed.py`, `library/grounding.py` | The exact storage + embedding + cosine-top-k pattern to mirror. `open_store()` already probes sqlite-vec → numpy fallback (one-click-install-green). `LibraryEmbedder` already does Gemini Embedding 2, 768-dim MRL, content-hash cache, audio + text paths. Memory is a *second* vec store, not a new dependency. |
| **Coach prompt + corpus footer** | `state/coach.py` (`evidence_line` / `build_prompt`) | The retrieval injection point. `evidence_line` already appends an "evidence-corpus footer" from a registry snapshot; `build_prompt` already threads `registry_snapshot`. Retrieved past moments become *another footer block* — same discipline as the registry. |

The implication: this milestone is mostly **plumbing into proven seams**, not novel ML. That
keeps complexity honest and the anti-slop contract intact.

---

## Part 1 — INGEST: what unit becomes an embeddable record, and at what cadence

### Recommendation (lead answer)

**Unit: the "reaction moment" — one `event` + its `llm_invoke` evidence + the `ai_text` it produced.** This is the
embeddable record. It already exists as a typed triple in `events.jsonl`; we do not invent a
new shape, we *join* three lines that share a timeline.

**Plus one coarser unit: the "session summary card"** — the existing debrief artifact
(`session_debrief.json` chapters + TL;DR), one record per session.

**Cadence: session-close, batch.** NOT live.

### Granularity decision matrix (acid test per candidate unit)

| Candidate ingest unit | Closes a hallucination class? | Unlocks a copilot move? | Verdict | Why |
|---|---|---|---|---|
| **Reaction moment** (`event`+`llm_invoke`+`ai_text` triple) | YES — grounds "have I seen this transition shape before?" against real past evidence, not vibes | YES — the "you ran this shape 30×, last time you killed bass 2 bars earlier" move | **INGEST (primary)** | Already typed; carries deck state, MIDI move labels, phase, track, the actual reaction text. The richest joinable atom. |
| **Session summary card** (debrief chapters + TL;DR) | Soft — grounds "what kind of sets does this DJ play" (genre/energy-arc priors) | YES — the cross-session "your last 3 Friday sets all peaked then died at 40min" arc callback | **INGEST (secondary)** | One record/session = cheap. Already produced by debrief pipeline. Gives the "arc" copilot move without storing every moment forever. |
| **Transition record** (a `TRACK_CHANGE` + the MIX_MOVE cluster around it) | YES — "did this A→B blend clash last time" | YES — the headline "transition shape" callback | **DERIVE from reaction moments, do not store separately** | A transition is a *view* over a window of moment records (TRACK_CHANGE bracketed by MIX_MOVEs). Storing it as a third record type duplicates data and creates a drift surface. Compute at retrieval/ingest time as a tag, don't double-store. |
| **Track-load record** | Already covered | No new move | **SKIP** | The library store (`library/grounding.py`) already embeds tracks + does identify_playing. A track-load is just a `track` field on a moment. Embedding it again in the memory store is redundant — fails acid test (closes nothing new, unlocks nothing new). |
| **Raw `voice.wav` / `input.wav` audio chunks** | No — and *adds* a class | No | **ANTI (do not embed)** | `v-next-memory-turn.md` says it explicitly: "Not a 'embed every audio sample' play." Continuous audio embedding is the €1500/month path that `library/grounding.py:P56` already rejected for live grounding. The audio is *already* on disk for replay; embedding it buys a fuzzy similarity that the structured moment record gives more precisely and far cheaper. |
| **LLM-extracted "insights"** (summarize the session into bullet facts, embed those) | NO — *opens* the worst class | Seems to, but fake | **ANTI (hard no)** | This is the single most important anti-feature. `v-next-memory-turn.md` locks it: "No LLM-extraction layer between session and embedding. Extraction = confabulation surface = violates anti-slop thesis." An extracted "Kaan tends to rush breakdowns" is an *unverifiable assertion* the AI then cites as fact. Raw moment records keep the citation honest: the AI can only call back a move that literally happened, with a `mem:` id that resolves to a real event. |

### Cadence decision

| Option | Verdict | Rationale |
|---|---|---|
| **Live (embed each moment as it fires)** | NO | The live reaction path is latency-budgeted (`LIVE_TTFT_BUDGET_MS=1500`, `thinking_level=MINIMAL`). Adding an embed round-trip per event spends the budget and the cost line for zero in-session benefit — you cannot retrieve a moment that hasn't finished happening. |
| **Session-close batch** | **YES** | Mirrors the existing FLEX-tier batch paths (`debrief / library_auto_tag / embedding` already run `ServiceTier.FLEX` at 50% cost — PROJECT.md LAT-07). Embed the whole session's moment records in one batch when the session ends, alongside the debrief generation that already runs there. Content-hash cache (mirror `embed.py`) makes re-runs free. |
| **Idle/deferred** | Acceptable fallback | If session-close embed adds noticeable shutdown lag, defer to next app launch (idle). The retrieval seam degrades gracefully — a not-yet-embedded last session is simply not retrievable yet, identical to a first-ever session. |

### What gets embedded for a reaction-moment record

A short **text signature** of the moment (mirrors `embed.py:_text_signature` for streaming tracks),
NOT raw audio. Example signature, assembled deterministically from the typed fields (no LLM):

```
TRACK_CHANGE | deck=mix | A$AP ROCKY → Baby's On Fire (FANTASM remix)
| phase peak→build | moves: A_low killed, A_filter boost, B_low boost
| bpm 150→128 | set_time 12:46
```

This is cheap (text embed, not audio), deterministic (no confabulation), and carries exactly the
structural shape a transition-callback needs to match on. Audio embedding stays in the *library*
store for "what's playing" grounding — two stores, two jobs. (Optionally, the moment's 18s audio
window could be embedded multimodally via Gemini Embedding 2 for richer similarity — but that is a
**v6.x stretch**, gated on whether text-signature retrieval proves insufficient. Start text-only;
scope hard.)

---

## Part 2 — RETRIEVAL: how past moments enter the live coach prompt

### Recommendation (lead answer)

**Top-k = 2–3, hard cap.** **Blend = cosine relevance × exponential time-decay, with a relevance
floor.** **Injection = a dedicated `mem:` footer block in `evidence_line`, behind the citation
linter, event-gated to the same TRACK_AWARE_EVENTS the library grounding already uses.**

### The retrieval blend

The canonical formula is Stanford's Generative Agents memory score
([Park et al. 2304.03442](https://ar5iv.labs.arxiv.org/html/2304.03442)):

```
score = α_relevance · cosine  +  α_recency · exp_decay(age)  +  α_importance · importance
```

For vibemix, simplify to **two terms** (relevance + recency); **importance is implicit** in the
event taxonomy (a TRACK_CHANGE moment is inherently more important than a HEARTBEAT — we ingest the
important ones and weight recency/relevance):

| Term | Source | Rationale |
|---|---|---|
| **relevance** | cosine top-k of the current moment's signature vs stored moments | The core "have I seen this shape" match. |
| **recency** | exponential decay on session age (decay over *sessions*, not game-hours — the DJ's last few sets matter more than one from 6 months ago) | The temporal-RAG literature ([Towards Data Science](https://towardsdatascience.com/rag-is-blind-to-time-i-built-a-temporal-layer-to-fix-it-in-production/)) is unanimous: cosine-only retrieval surfaces stale context. Half-life in *sessions* (e.g. ~10 sessions) is the tunable. |
| **importance** | (folded into ingest selection) | Stanford set all α=1; we get importance for free by *what we choose to embed* (typed events, not heartbeats-only). Don't build an LLM importance-scorer — that's an extraction layer. |

**The blend is the FIRST PHASE's research to *tune*, not invent** (per `v-next-memory-turn.md`:
"Hybrid (cosine + time-weight) TBD per research"). The recommendation here is the *shape*: two-term,
exp-decay-on-sessions, relevance floor. Exact half-life + weights get A/B'd on Kaan's real session
corpus.

### Keeping retrieval from poisoning the live reaction

This is the make-or-break risk. The RAG poisoning/distractor literature is blunt: **more retrieved
docs improves recall but decreases precision — irrelevant retrieved context acts as "data poisoning"
that dilutes attention and degrades output** ([arxiv 2412.16708](https://arxiv.org/pdf/2412.16708),
[Elastic context-poisoning](https://www.elastic.co/search-labs/blog/context-poisoning-llm),
[arxiv 2512.14313 distractors](https://arxiv.org/pdf/2512.14313)). For a product whose entire thesis
is "no AI slop, no hallucination," a poisoned memory footer is an existential failure. Five hard guards:

1. **Small k (2–3), never more.** Recall is not the goal; *one good callback* is. The literature shows
   precision collapse with large k. A DJ co-host needs at most "the one most-similar past moment."
2. **Relevance floor (mirror `library/grounding.py` thresholds).** Below cosine ~0.7, inject **nothing** —
   exactly like `CITATION_THRESHOLD`. No weak match is better than a forced one. A first-ever session,
   or a genuinely novel moment, gets an *empty* mem-footer and the AI behaves exactly as v5.0 does today.
3. **`mem:` source behind the existing citation linter.** A retrieved moment becomes citable evidence
   `[mem:<event_id>]`; the linter (`evidence_registry.py` + Phase 20 strip) makes a fabricated callback
   uncitable-by-construction — same mechanism that makes a fabricated `[key:8A]` clash uncitable today.
   This is the structural anti-slop guarantee, not a prompt plea.
4. **Event-gated, not per-tick.** Retrieve only on TRACK_AWARE_EVENTS (`TRACK_CHANGE`, `LAYER_ARRIVAL`,
   `MIX_MOVE`) — the same gate `library/grounding.py` uses for cost (P56). HEARTBEAT never triggers a memory
   lookup. This bounds cost AND prevents the AI from constantly straining to "remember something."
5. **Footer says "optional context," prompt task stays primary.** The mem-footer is grounding the AI *may*
   use, not an instruction it *must* satisfy. The live moment always wins; memory is a seasoning, never the
   dish. (Mirrors how `evidence_line` frames the corpus footer as something to cite *against*, not a script.)

### Where it injects

Into `state/coach.py:evidence_line`, as a new optional block (same pattern as the existing
`registry_snapshot` corpus footer), threaded through `build_prompt` exactly like `registry_snapshot`
is today. Retrieval runs in the executor (off the live loop), result cached on the Grounding-style
service (mirror `library/grounding.py:Grounding.get_latest_citation`), pulled at prompt-build time.
Zero new architectural pattern.

---

## Part 3 — The 1–2 VISIBLE COPILOT MOVES that prove retrieval is firing

`v-next-memory-turn.md` asks for "one or two end-user-noticeable proofs that retrieval is firing."
Two recommended, ranked. Both pass the acid test (both *unlock a copilot move* AND the `mem:` citation
*closes the "AI invents your history" hallucination class*).

### Move 1 (headline) — Transition-shape callback

> *"You've run this A→B blend a bunch — last time you killed the bass two bars earlier and it landed
> harder."*

- **What proves it:** the AI references a *structural pattern* (transition shape) it can only know from
  past sessions, cited `[mem:<id>]` to a real prior moment.
- **Why it's the headline:** it's the literal example in both PROJECT.md and the thesis note. It is the
  most "copilot, not co-host" moment — forward-leaning ("do X"), grounded in *the DJ's own* repeated behavior.
- **Grounding integrity:** the callback's claim ("killed bass 2 bars earlier") must resolve to a real
  past moment's MIDI-move evidence. If the retrieved moment's signature doesn't support the comparison,
  the linter strips it. **No hallucinated "you usually do X" — only verifiable "last time the record shows Y."**
  This is the difference between a copilot and a horoscope.
- **Frequency discipline:** rare and earned. Fires only on a strong relevance match (high cosine, recent).
  A callback every transition would feel scripted — the exact failure mode the Core Value forbids.

### Move 2 (texture) — Vocabulary / phrasing callback

> The DJ (or the AI, in a prior session) called a certain drop "filthy" / "industrial chaos" — the AI
> reuses *the DJ's own* register when a matching moment recurs.

- **What proves it:** continuity of voice across sessions — the AI sounds like it *remembers you*, not
  like a fresh instance. Episodic-memory personalization, exactly the
  ["Last time we worked on..." pattern](https://navryn.com/en/blog/persistent-context-ai) from AI-coach
  literature.
- **Why secondary:** lower stakes, lower risk, but it's the *felt* proof — the thing that makes a user say
  "wait, it remembered." It's cheap (the vocabulary is already in the stored `ai_text` / any KAAN_SPOKE
  transcript signature) and it can't really "lie" (reusing a register is a style choice, not a factual claim).
- **Caveat:** keep it subtle. Parroting the DJ's slang too eagerly reads as AI-slop mimicry. One well-placed
  echo > constant callbacks.

### Anti-move (explicitly NOT a copilot move)

> *"Play [specific track] next."* / *"Mix into [recommendation]."*

- **Why it's tempting:** "copilot" connotes suggestion; memory of past sets makes track-suggestion *feel*
  unlocked.
- **Why it's forbidden:** PROJECT.md "Out of Scope" — *"Track recommendation / library scanner AI feedback...
  defers to v1.1."* And it fails the acid test: a next-track recommendation is a *prediction*, not a
  *retrieval of a real past moment* — it re-opens the hallucination class the whole product exists to close.
  The copilot moves above are **retrospective and grounded** ("last time you did Y"), never **prospective and
  invented** ("you should play Z"). Hold this line hard.

---

## Feature Landscape

### Table Stakes (the memory layer is incomplete without these)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Session-close ingest of reaction-moment records | Without ingest there is no memory | MEDIUM | Join `event`+`llm_invoke`+`ai_text` from `events.jsonl`; build deterministic text signature; batch-embed (FLEX tier). Reuses `embed.py` patterns. |
| Second sqlite-vec store for moments (per-install) | Storage spine | LOW | Mirror `library/store.py:open_store()` (sqlite-vec→numpy fallback). Separate DB file from `library.db` / `embeddings.db`. |
| Retrieval seam into coach prompt (top-k 2–3, relevance floor) | The mechanism IS the product | MEDIUM | New `mem:` footer in `evidence_line`; thread through `build_prompt` like `registry_snapshot`. Executor-run, cached. |
| `mem:` evidence source + linter coverage | Anti-slop contract must extend to memory | LOW–MEDIUM | Add `mem` to `EVIDENCE_SOURCES`; the SCHEMA-MIRROR comment lists the 4 lock-step sites to update. The linter then guarantees uncitable→stripped. |
| Cosine + recency (exp-decay-on-sessions) blend | Cosine-only surfaces stale moments (temporal-RAG consensus) | MEDIUM | Two-term score; half-life tunable. The *shape* is recommended; exact weights are first-phase tuning on Kaan's corpus. |
| Graceful empty-memory behavior | First session / novel moment must behave exactly like v5.0 | LOW | Below relevance floor → empty footer → identical to today. No "I don't remember anything" filler. |
| Retention + size budget per install | One-click-install green; don't grow unbounded | LOW–MEDIUM | TBD per research (`v-next-memory-turn.md`). Cap by session count or DB size; sweep oldest. Mirror library staleness sweep pattern. |

### Differentiators (this is where "copilot, not co-host" is won)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Transition-shape callback** (Move 1) | The headline "it remembers your patterns" moment; the demo clip that sells v6.0 | MEDIUM–HIGH | Requires transition-shape signature + strong-match gate + linter-backed comparison claim. The risk surface — get the grounding integrity right or it becomes a horoscope. |
| **Vocabulary/register callback** (Move 2) | The *felt* "it remembers me" texture; cross-session voice continuity | LOW–MEDIUM | Cheap; signature already carries the DJ's words. Keep subtle. |
| **Cross-session arc priors** (from session-summary cards) | "Your last 3 sets peaked then sagged at ~40min" — coaching the DJ's *macro* habits | MEDIUM | Uses the coarse session-card store. Genuinely forward-leaning. Defer if Moves 1–2 land first. |
| **Emergent personalization (no settings screen)** | The whole thesis: personalization falls out of retrieval, zero config | (property, not a build) | This is the *result* of the above, not a separate feature. Explicitly NOT a settings UI (Phase 32 covers configured prefs). |

### Anti-Features (seem good, fail the acid test, or violate locked scope)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **LLM-extracted session "insights" / facts** | "Summarize what the DJ tends to do, embed that" feels smart | Extraction = confabulation surface; the AI then cites an *invented* tendency as fact. Locked-out in `v-next-memory-turn.md`. | Embed raw deterministic moment signatures; tendencies emerge from retrieval, not assertion. |
| **Embed every audio sample / continuous audio memory** | "Richer similarity from the actual sound" | €1500/month path (P56 rejected it for live); a fuzzy match the structured record gives more precisely and cheaper; explicit anti in the thesis note | Text-signature embed of typed moment fields. Audio stays in the library store for "what's playing." Multimodal moment-audio embed = v6.x stretch only if text proves insufficient. |
| **Next-track / "play this next" recommendation** | "Copilot should suggest" | Prediction, not retrieval — re-opens the core hallucination class; PROJECT.md Out-of-Scope (defers to v1.1) | Retrospective grounded callbacks only ("last time you did Y"), never prospective invention. |
| **Settings-screen personalization tuned by memory** | "Let the user configure what it remembers" | Phase 32's ~2KB DJ profile already covers configured prefs; thesis says memory is emergent, NOT configured | Personalization is a property of the retrieval seam. No new settings surface. |
| **Large-k retrieval (5–10 past moments)** | "More context = better grounding" | Precision collapse + distractor poisoning ([RAG poisoning lit]); for an anti-slop product this is fatal | k = 2–3 hard cap; one good callback beats ten weak ones. |
| **Live (per-event) embedding** | "Remember in real time" | Spends the live latency + cost budget for zero in-session value (can't retrieve an unfinished moment) | Session-close batch embed (FLEX tier), idle-deferred if shutdown lag. |
| **Managed memory framework (Mem0/Letta/Zep/Cognee)** | "Don't reinvent the wheel" | All rejected (`mem0-rejected-2026-05-18.md`, memory `feedback_no_managed_memory_frameworks`); 97.8% junk + hard openai dep audited; vibemix is Gemini-only | sqlite-vec + ~50-line DIY wrapper, mirroring `library/store.py`. |
| **Cross-user / cloud-shared memory** | "Learn from all DJs" | Privacy violation; per-install local-only is the contract; no server | Per-install local sqlite-vec, never leaves the machine. |
| **Separate transition / track-load record types** | "Model each thing explicitly" | Data duplication + drift surface vs the moment record | Derive transitions as a *view/tag* over moment records; track-load is a field, not a record. |

---

## Feature Dependencies

```
events.jsonl (DONE — recorder.py)
    └──feeds──> Reaction-moment ingest (session-close batch)
                    └──requires──> Moment sqlite-vec store (mirror library/store.py)
                    └──requires──> Gemini Embedding 2 text-signature embed (mirror library/embed.py)
                                       └──enables──> Retrieval seam (top-k 2-3 + recency blend)
                                                        └──requires──> mem: source + linter coverage (evidence_registry.py)
                                                        └──injects-into──> coach.py evidence_line / build_prompt (DONE seam)
                                                                              └──unlocks──> Move 1: transition-shape callback
                                                                              └──unlocks──> Move 2: vocabulary callback

debrief session_debrief.json (DONE — debrief/)
    └──feeds──> Session-summary card ingest (one record/session)
                    └──enables──> Cross-session arc priors (differentiator, deferrable)

library audio embed store (DONE) ──stays-separate-from──> moment memory store (two stores, two jobs)
```

### Dependency Notes

- **Retrieval requires `mem:` linter coverage FIRST.** Do not ship retrieval injection before the
  `mem` source is in `EVIDENCE_SOURCES` and the linter strips uncitable callbacks. Otherwise the first
  copilot move that mis-fires is an un-caught hallucination — release-gate failure.
- **Ingest requires the moment store, which requires nothing new** — `open_store()` and `LibraryEmbedder`
  already exist; the work is a second store-file + a deterministic signature builder, not new infra.
- **Moves unlock only after the full seam is wired** — they are the *proof*, the last thing built, the
  thing Kaan ear-tests.
- **Cross-session arc priors depend on the session-card store**, which is independent of the moment store —
  can be a later phase without blocking Moves 1–2.

---

## MVP Definition

### Launch With (v6.0 spine — per `v-next-memory-turn.md` "ships the spine")

- [ ] Reaction-moment ingest at session-close (batch, FLEX tier) — no memory without ingest
- [ ] Moment sqlite-vec store, per-install, retention-capped — the spine's storage
- [ ] Retrieval seam: top-k 2–3, cosine × recency, relevance floor, event-gated — the mechanism IS the product
- [ ] `mem:` evidence source + linter coverage — anti-slop contract extends to memory (hard gate)
- [ ] **Move 1: transition-shape callback** — the one visible proof retrieval fires (demo-able)
- [ ] Graceful empty-memory behavior — first session behaves identically to v5.0

### Add After Validation (v6.x)

- [ ] **Move 2: vocabulary/register callback** — once Move 1's grounding integrity is ear-confirmed
- [ ] Session-summary-card ingest + cross-session arc priors — once moment-level memory proves out
- [ ] Multimodal moment-audio embedding — only if text-signature retrieval proves insufficient

### Future Consideration (v7+ / explicitly deferred)

- [ ] Next-track suggestion grounded on memory — PROJECT.md defers to v1.1; needs the prediction
      hallucination class solved first (it is not)
- [ ] Multi-session debrief progress reports as a UI surface — depends on arc priors landing

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Reaction-moment ingest (session-close) | HIGH | MEDIUM | P1 |
| Moment sqlite-vec store | HIGH | LOW | P1 |
| Retrieval seam (k 2-3, recency blend, floor) | HIGH | MEDIUM | P1 |
| `mem:` source + linter coverage | HIGH (gate) | LOW–MEDIUM | P1 |
| Move 1: transition-shape callback | HIGH | MEDIUM–HIGH | P1 |
| Graceful empty-memory | MEDIUM (avoids regression) | LOW | P1 |
| Retention/size budget | MEDIUM | LOW–MEDIUM | P1 |
| Move 2: vocabulary callback | MEDIUM | LOW–MEDIUM | P2 |
| Session-card ingest + arc priors | MEDIUM | MEDIUM | P2 |
| Multimodal moment-audio embed | LOW (until proven needed) | HIGH | P3 |

## Competitor / prior-art feature analysis

| Pattern | Stanford Generative Agents | Episodic-memory AI coaches | vibemix v6.0 approach |
|---------|----------------------------|----------------------------|------------------------|
| Memory unit | Natural-language observation records | Indexed interaction-log episodes | Typed reaction-moment (event+evidence+reaction) — no LLM extraction |
| Retrieval score | relevance + recency + importance (α=1 each, exp decay 0.995) | time/topic/sentiment indexed surface | cosine × exp-recency, importance folded into ingest selection |
| Callback move | reflection-driven behavior | "Last time you skipped gym..." | "Last time you killed bass 2 bars earlier" — linter-grounded |
| Anti-hallucination | (not a focus) | (not a focus) | `mem:` citation linter — fabricated callback = uncitable = stripped (vibemix's differentiator) |

## Sources

- [Park et al., Generative Agents (2304.03442)](https://ar5iv.labs.arxiv.org/html/2304.03442) — canonical relevance+recency+importance retrieval score, exponential decay (HIGH)
- [RAG Is Blind to Time — temporal layer in production (Towards Data Science)](https://towardsdatascience.com/rag-is-blind-to-time-i-built-a-temporal-layer-to-fix-it-in-production/) — cosine-only surfaces stale; time-decay reranking (MEDIUM)
- [temporal-rag (GitHub)](https://github.com/Emmimal/temporal-rag/) — validity filter + time decay + hybrid rerank pipeline (MEDIUM)
- [Solving Freshness in RAG: recency prior (arxiv 2509.19376)](https://arxiv.org/html/2509.19376) — recency prior shape (MEDIUM)
- [Evaluating RAG Under Adversarial Poisoning (arxiv 2412.16708)](https://arxiv.org/pdf/2412.16708) — irrelevant retrieved context degrades generation (HIGH for the small-k guard)
- [Dynamic Context Selection: mitigating distractors (arxiv 2512.14313)](https://arxiv.org/pdf/2512.14313) — distractors dilute attention; precision collapse with large k (HIGH)
- [Context poisoning in LLMs (Elastic Search Labs)](https://www.elastic.co/search-labs/blog/context-poisoning-llm) — semantic-noise / overflow mechanisms (MEDIUM)
- [The AI Coach That Remembers You (NAVRYN)](https://navryn.com/en/blog/persistent-context-ai) — "Last time we worked on..." episodic callback pattern (MEDIUM)
- [Memory Power Asymmetry in Human–AI Relationships (arxiv 2512.06616)](https://arxiv.org/html/2512.06616v1) — strategic surfacing of specific past episodes (MEDIUM)
- Existing vibemix code (HIGH, primary): `src/vibemix/audio/recorder.py` (events.jsonl schema), `src/vibemix/state/evidence_registry.py` (citation grammar + linter), `src/vibemix/library/{store,embed,grounding}.py` (sqlite-vec + Gemini Embedding 2 + event-gated cost pattern), `src/vibemix/state/coach.py` (evidence_line corpus-footer injection seam), `src/vibemix/debrief/{chapters,persistence}.py` (session-card unit), real `recordings/20260515-112139/events.jsonl` sample
- `.planning/notes/v-next-memory-turn.md` (locked thesis + acid test + anti-feature list); `.planning/PROJECT.md` (v6.0 milestone block + Out-of-Scope)

---
*Feature research for: session-memory / retrieval-grounded copilot layer (vibemix v6.0 "The Memory Turn")*
*Researched: 2026-05-22*
