# DJ Knowledge RAG — Sources, Legal Posture, and Tool Design

**Research date:** 2026-05-26
**Goal:** Build a retrieval (RAG) knowledge base the vibemix agent can query for **DJ courses and DJ knowledge**, so when a user asks "how do I do X" the agent retrieves *real, grounded, cited* DJ education and teaches it (the **TUTOR lens** — the third lens alongside hype-man and coach). Grounding bar is identical to the live co-host: **Invariant #2 (citation grounding)** — every technique the tutor states must resolve to a real KB chunk, or it strips to "I'm not sure" instead of hallucinating technique.

This is the inverse of the live path. Live co-host = grounded by *audio evidence*. Tutor = grounded by *retrieved knowledge chunks*. Same anti-slop discipline, different evidence source.

---

## 1. Ranked source list — public DJ-education content

Ranked by (a) depth/quality of how-to content, (b) breadth of topics, (c) realistic ingestability. Topic tags: **BM**=beatmatching, **HM**=harmonic/key mixing, **PHR**=phrasing/structure, **EQ**=EQ/filter, **GAIN**=gain/levels, **SET**=set structure/energy/journey, **GEN**=genre theory, **FX**=effects/creative, **GEAR**=hardware/software setup.

### Tier 1 — deep, structured, text-heavy how-tos (best KB substrate)

| Rank | Source | URL | Covers | Notes |
|---|---|---|---|---|
| 1 | **DJ TechTools blog** | https://djtechtools.com/ | EQ, PHR, FX, BM, GEAR, SET | The single richest *text* corpus. Long-form technique essays with theory ("why"), not just steps. Anchor articles: EQ Mixing: Critical Techniques and Theory (`/2012/03/11/eq-critical-dj-techniques-theory/`), How to DJ 101: Why You Must Understand Phrasing (`/2014/11/16/how-to-dj-101-why-you-must-understand-phrasing/`), DJ Fundamentals: How Phrasing Can Make or Break a Mix (`/2019/11/11/dj-fundamentals-how-phrasing-can-make-or-break-a-dj-mix/`), Filter VS EQ: Which, When, Why (`/2011/12/07/filter-vs-eq-which-when-why/`), Mixing Songs That Don't Have a 'DJ Intro' (`/2017/09/11/`), Pro DJ Link setup (`/2018/07/31/`). 15+ years archive, ~310k YT subs mirror the blog. |
| 2 | **Digital DJ Tips** | https://www.digitaldjtips.com/ | BM, HM, EQ, GEAR, SET, PHR | Most *pedagogically structured* — written as graded lessons (beginner→pro), the exact tone the tutor lens wants. Anchor: Beginner's 1-2-3 of Mixing In Key (`/beginner-1-2-3-of-mixing-in-key/`), DJ Mixer Basics free lesson (`/dj-mixer-basics-free-lesson/`). 20k+ students; authors of the Amazon best-selling "Rock The Dancefloor" book. Free blog articles are ingestable; the paid course videos are NOT. |
| 3 | **Mixed In Key — Harmonic Mixing Guide + Wiki** | https://mixedinkey.com/harmonic-mixing-guide/ , https://mixedinkey.com/camelot-wheel/ , https://mixedinkey.com/wiki/harmonic-mixing-explained-everything-you-need-to-know/ | HM, SET (energy levels) | **The canonical harmonic-mixing reference.** Camelot Easymix system, "up/down/around" rules, same-number letter swaps (8A↔8B), energy-level 1–10 sorting, energy-boost & power-block mixing, per-software (Serato/Traktor/rekordbox/Ableton) sections, annotated Armin/Diplo set analyses. **Highest authority for the HM topic** — vibemix already uses Camelot internally (`state/harmonics.py`), so this aligns the *teaching* vocabulary with the *engine* vocabulary. ("Beyond Beatmatching" is the paid book; the web guide + wiki are free.) |
| 4 | **Crossfader (We Are Crossfader)** | https://wearecrossfader.co.uk/blog/ | BM, EQ, FX, HM, GEN, GEAR | "The Complete DJ Course (FREE)" (`/blog/the-complete-dj-course-free/`), free lessons hub (`/blog/free-lessons/`), genre-specific lessons (Techno, House, Hip-Hop + subgenres = good **GEN** theory), creative mixing (hot-cue routines, tone play, mashups, polyrhythmic looping). Beginner→advanced. Strong, modern, electronic-focused. Filmed-from-above video style — transcript ingestion valuable here. |

### Tier 2 — official manufacturer guides (authoritative for GEAR + canonical technique definitions)

| Rank | Source | URL | Covers | Notes |
|---|---|---|---|---|
| 5 | **rekordbox.com tutorials + "connect" articles** | https://rekordbox.com/en/video/ , https://rekordbox.com/en/connect/pete-tong-dj-academy/how-to-start-djing/ | GEAR, BM, SET | Official Pioneer/AlphaTheta. The Pete Tong DJ Academy "connect" articles are written how-to text (e.g., How to Start DJing). Authoritative for the gear vibemix actually maps (DDJ-FLX4 etc.). |
| 6 | **Pioneer DJ News / learn-how-to-DJ** | https://www.pioneerdj.com/en/news/2019/learn-how-to-dj-online/ , https://www.pioneerdj.com/en/news/2019/ddj-400-dj-controller-mixing-technique-tutorials/ | GEAR, FX, BM, FX(loop/drop) | DDJ-400 technique tutorials: FX, transitions, looping, drop mixing/swapping. Mostly video → transcript path. |
| 7 | **Rane DJ Support knowledge base** | https://support.rane.com/ , https://www.rane.com/ | GEAR | Setup/connectivity articles, FAQs. Authoritative gear reference; thin on technique. Good for "how do I set up X" gear questions, low for musicality. |
| 8 | **Native Instruments blog (DJ tips)** | https://blog.native-instruments.com/dj-tips/ | BM, PHR, EQ, SET, GEAR | "Top 25 DJ tips" + Traktor courses (co-produced with Crossfader). Good condensed tip corpus + energy/structure framing. |

### Tier 3 — video-first courses (transcript-ingestion path; see §4)

| Rank | Source | URL | Covers | Notes |
|---|---|---|---|---|
| 9 | **DJcity (YouTube)** | youtube.com/@DJcityTV (Mojaxx, DJ TLM how-tos) | BM, FX, scratch, GEAR | Excellent short how-tos; transcript-only ingest. |
| 10 | **Crossfader YouTube** | youtube.com/@WeAreCrossfader | mirrors blog | Filmed-overhead tutorials; transcripts good. |
| 11 | **DJ TechTools YouTube** | youtube.com/@djtechtools | mirrors blog | 10–15 min insightful clips. |
| 12 | **Pioneer DJ YouTube** | youtube.com/@PioneerDJglobal | GEAR, software | rekordbox/WeDJ instructional playlists. |
| 13 | **Future Female Sounds DJ Academy** | https://www.ffsdjacademy.com/ | BM, EQ, music theory, FX | 70+ tutorials; masterclasses (e.g., looping) surfaced on Beatportal. |
| 14 | **Pete Tong DJ Academy (via Beatport)** | https://www.petetong-djacademy.com/ , https://www.beatportal.com/ | full curriculum | Lessons from Carl Cox, Adam Beyer, Nicole Moudaber, Jamie Jones. **Gated behind Beatport subscription — DO NOT scrape** (see §2). Use only the free Beatportal editorial articles + public lite content. |

### Topic-coverage matrix (where to pull each technique from)

| Topic | Primary source(s) |
|---|---|
| Beatmatching (BM) | Digital DJ Tips, Crossfader, NI blog, Mixcloud guide |
| Harmonic/key mixing (HM) | **Mixed In Key (canonical)** + Digital DJ Tips |
| Phrasing / structure (PHR) | **DJ TechTools (canonical)** — multiple deep essays |
| EQ / filter (EQ) | **DJ TechTools (canonical)** + Crossfader |
| Gain / levels (GAIN) | Digital DJ Tips (mixer basics), Rane/Pioneer manuals |
| Set structure / energy / journey (SET) | **Mixed In Key (energy levels)** + DJ TechTools + NI |
| Genre theory (GEN) | **Crossfader (genre lessons)** + Beatportal editorial |
| Creative FX / hot cues (FX) | DJ TechTools, Crossfader, Pioneer DDJ-400 series |
| Gear/software setup (GEAR) | rekordbox.com, Rane support, Pioneer DJ News |

---

## 2. Legal posture — scrapable vs paywalled vs ToS-restricted

**Bottom line for vibemix:** the safest, defensible posture for an **open-source, public** project is **NOT a bulk scrape of full articles**. Build the KB from (a) content you have a license/permission for, (b) short *factual* technique extracts under fair-use posture, with (c) prominent attribution + deep links back to the source. The high-value move is **"link-out RAG"**: store enough chunked summary to *retrieve and cite*, then send the user to the original article/video for the full lesson. That sidesteps most copyright exposure while still teaching.

### Per-class assessment

| Class | Examples | Scrapable? | Posture |
|---|---|---|---|
| **Public free blog articles** | DJ TechTools, Digital DJ Tips (free posts), Crossfader free lessons, NI blog, Mixed In Key guide/wiki | Technically yes (robots.txt on DJTips only blocks `/wp-admin/`, `/search/`, `/?s=` — **not** content paths). | Robots permits crawling content. BUT copyright still applies to the *expression*. Store **paraphrased/summarized chunks + short quotes**, not verbatim full articles. Always attribute + deep-link. |
| **Official manufacturer docs** | rekordbox tutorials, Rane support, Pioneer News | Yes (public, factual setup info). | Factual procedural content (how to connect gear, what a knob does) has **thin copyright** — facts/procedures aren't protected, only expression. Lowest risk class. Still attribute. |
| **Paid courses / memberships** | Digital DJ Tips paid course, Crossfader Complete DJ Package, Pete Tong Academy / Beatport-gated lessons | **NO — do not scrape.** | Behind paywall/login = ToS-restricted + clear market-harm under fair-use factor 4. Hard line: never ingest gated content. Free preview articles only. |
| **YouTube transcripts** | DJcity, Crossfader, DJTechTools, Pioneer channels | Public auto-captions are fetchable. | Transcripts are *derivative works owned by the video owner*. Free transcript-API tiers are typically **non-commercial only**. See §4 — prefer official YouTube Data API for owned/permissioned content; for third-party, treat as link-out + timestamp citation, store minimal text. |

### Legal factors that shape the design (2025–2026 climate)

- **Fair use is narrowing for AI.** *Thomson Reuters v. Ross* (2025): unlicensed use of proprietary content to build a *competing* AI product was **not** fair use — market-harm (factor 4) dominated. Lesson for vibemix: a *teaching tutor that links back to and drives traffic to* DJ TechTools is complementary, not competitive; a tutor that *replaces* reading DJ TechTools by reproducing full articles is competitive. Design for the former.
- **Copyright covers expression, not facts/procedures.** "Phrasing aligns on 8/16/32-beat boundaries" is a *fact* you can teach freely. The specific prose explaining it is protected. So: **extract the technique as structured fact, attribute the source, quote sparingly.**
- **robots.txt = the crawl signal; ToS = the contract.** Respect both. DJTips robots.txt allows content; but read each site's ToS for explicit no-scrape clauses before any automated pull.
- **EU AI Act / TDM:** transparency obligations on training data; the TDM exception requires honoring machine-readable opt-outs. Honor robots + any `tdm-reservation`.

### Recommended legal stance (de-risked path, in priority order)

1. **Link-out RAG (default):** KB stores *summaries + short attributed quotes + source URL + (for video) timestamped URL*. Retrieval teaches the gist and cites; user clicks through for the full lesson. This is the launch posture.
2. **Permission/partnership for depth:** reach out to Crossfader / DJ TechTools / Mixed In Key for explicit permission to mirror content (vibemix is OSS + drives traffic — a real win-win pitch; Mixed In Key already shares the Camelot vocabulary). Upgrade those sources to full-text chunks once permitted.
3. **First-party content:** the cheapest clean corpus — Kaan/Francesco write vibemix's own DJ-knowledge articles (Francesco has the DJ network/expertise). 100% owned, 100% ingestable, zero risk, and becomes SEO + waitlist content.
4. **Never** ingest paywalled/gated course bodies.

---

## 3. RAG architecture for the DJ-knowledge KB

### 3.1 Reuse, don't reinvent

vibemix already has the entire spine of this system:
- **Embeddings + vector store:** the library layer (`library/`) already runs sqlite-vec (macOS) / numpy (Windows) with bit-identical top-K parity, content-hash embed caching, and mean-centering for anisotropy. The DJ-knowledge KB is **a second vector collection in the same store** — `knowledge.db` alongside `library.db` under `~/.cache/vibemix/`.
- **Grounding primitive:** `state/evidence_registry.py` + Invariant #2 (citation grounding) is *exactly* the mechanism the tutor needs. Knowledge chunks become evidence entries; a tutor answer that cites a chunk-id that doesn't resolve gets stripped — same anti-slop gate as live reactions.
- **Tool/agent core:** `library/toolset.py` (shared grounded tool core, seen-set + re-validation) and `library/mcp_server.py` (MCP STDIO) already exist for the Viber curator. The new `retrieve_dj_knowledge` tool slots into that same pattern (§3.5).

**Embedding choice:** Use **Gemini text embedding** for *this* KB (NOT CLAP). CLAP is audio-domain; DJ knowledge is text. This does not violate the "CLAP is the similarity engine" decision — that decision is about *track/audio similarity*. Text knowledge retrieval is a different modality. Gemini text-embedding is already wired (`library/embed.py` pre-CLAP path) and is the in-house, Gemini-only-brain-consistent choice. Persist embeddings, mean-center query side only (consistent with existing convention).

### 3.2 Chunking strategy for DJ how-tos

DJ how-tos are **procedural + conceptual**, structured by heading/step. Naive fixed-size chunking shreds a 6-step beatmatching procedure mid-step. Use **structure-aware (recursive) chunking with metadata**, not blind fixed-size:

- **Split on document structure first:** H2/H3 headings, numbered steps, list items. A "How to phrase a mix" article → chunks per heading section, each a self-contained teachable unit.
- **Target size:** ~256–400 tokens per chunk with ~15% overlap (matches RAG best practice: 256–512 tokens preserves context for analytical/how-to queries; overlap prevents boundary loss). Keep a procedure's steps together when under budget; only split long sections.
- **Atomic-concept rule:** each chunk should answer one "how do I X" cleanly. "EQ bass-swap on transition" = one chunk; don't merge with "filter sweeps."
- **Rich metadata per chunk (this is what makes citation + filtering work):**
  ```
  {
    chunk_id, source_name, source_url, video_timestamp (if video),
    title, section_heading, topic_tags: [BM|HM|PHR|EQ|GAIN|SET|GEN|FX|GEAR],
    skill_level: [beginner|intermediate|pro],
    text (paraphrased + short quote), license_class
  }
  ```
- **Skill-level tagging** lets the tutor match vibemix's existing Beginner/Intermediate/Pro user levels — retrieve `skill_level <= user_level` so a beginner doesn't get pro jargon.
- **Topic-tag filtering** lets retrieval pre-filter by detected intent (user asks about keys → filter `topic_tags contains HM`) before vector search — sharper recall, fewer off-topic chunks.

### 3.3 Retrieval + grounding flow (anti-hallucination)

```
user question ("how do I mix tracks that are in different keys?")
  → intent/topic classify (cheap Gemini Flash or keyword map → topic_tags=[HM])
  → metadata pre-filter (topic_tags ∩ skill_level<=user_level)
  → vector search (Gemini-embed query, mean-centered) → top-K chunks
  → grounding gate: register chunks in EvidenceRegistry, pass ONLY them to prompt
  → Gemini Flash answers USING ONLY retrieved chunks, MUST cite chunk_ids
  → post-check (Invariant #2): every citation resolves → keep; any un-cited
     technical claim → strip / fall back to "I don't have a grounded answer for
     that — here's what I can cite" + the closest sources
```

**Grounding rules (lifted from the live co-host anti-slop discipline):**
1. **Closed-book prohibition:** prompt explicitly says *answer only from provided context; if the answer isn't in context, say so and offer the nearest sources.* (Standard RAG cuts hallucination ~35%; this is the gate, not a nice-to-have.)
2. **Mandatory citation:** every technique statement carries a `[chunk_id]` that must resolve in EvidenceRegistry. Un-resolvable citation = stripped, exactly like un-cited live reactions strip to the ack-bank.
3. **No technique invention:** the tutor never states a mixing technique that isn't in a retrieved chunk. This is the tutor-lens analogue of Invariant #3 ("trust the audio") — here it's "trust the KB."
4. **Confidence floor:** if top-K similarity is below threshold, the tutor admits it doesn't know rather than stretching a weak chunk. (Better "I'm not sure" than slop — Kaan's release gate.)

### 3.4 Surfaces

- **Live tutor lens:** during a set, user asks a question (voice/text) → retrieve → speak the grounded answer in the co-host's voice. Same ws-bus surface as hype/coach.
- **Set-prep / Viber:** "teach me harmonic mixing for this playlist" → tutor retrieves HM knowledge + grounds it against the *actual* tracks' Camelot keys from the library. Knowledge KB ∩ user's real library = grounded, personalized teaching.

### 3.5 MCP tool: `retrieve_dj_knowledge`

Slots into the existing `library/toolset.py` grounded-tool core + `library/mcp_server.py` STDIO server (same pattern as the Viber curate tools). Signature:

```
retrieve_dj_knowledge(
    query: str,                 # the user's "how do I X" question
    topic: str | None = None,   # optional pre-filter: BM|HM|PHR|EQ|GAIN|SET|GEN|FX|GEAR
    skill_level: str = "intermediate",  # caps complexity to user level
    k: int = 5
) -> list[KnowledgeChunk]       # each: text + source_name + source_url + timestamp + chunk_id
```

- Returns **grounded chunks with citations**, never prose — the *agent* composes the teaching answer from them, so grounding stays enforceable (the tool can only return real chunks = seen-set guarantee, identical to how `search_vibe` can only return real track IDs).
- Both backends (Gemini built-in fn-calling + Codex-via-MCP) get it for free since they share the toolset core.
- Telegram/Viber mobile surface inherits it: "how do I mix in key?" answered from your phone, cited.

---

## 4. YouTube-course ingestion + Bravoh quoting-engine angle

### 4.1 Why video matters here

The deepest DJ technique (scratch routines, FX chains, live phrasing demos) lives on YouTube (DJcity, Crossfader, DJ TechTools, Pioneer), not in text. Transcripts unlock that corpus for retrieval.

### 4.2 Ingestion pipeline

1. **Fetch transcripts** with timestamped segments. Each segment = `{start, end, text}`. Two paths:
   - **Owned/permissioned channels:** official **YouTube Data API** (compliant, commercial-OK once you own/license the content) — the clean path. Pursue this with partner channels.
   - **Third-party public videos:** auto-caption fetch (e.g. `youtube-transcript-api` Python lib). **Caveat:** free transcript-API tiers are commonly **non-commercial only**, and transcripts are the video owner's derivative work. So for third-party: **store minimal text + timestamp, treat as link-out citation**, don't reproduce whole transcripts.
2. **Chunk by transcript window** aligned to ~30–60s of speech (≈256–400 tokens), carrying `video_id`, `start_ms`, `end_ms`, `channel`, `title` into metadata (same schema as §3.2, with `video_timestamp` populated).
3. **Embed + store** in the same `knowledge.db` collection. ASR captions are noisy — optionally pass through Gemini Flash to clean/normalize before embedding (improves recall) while keeping the raw timestamp.

### 4.3 Timestamped citation = the killer grounding feature

Because each chunk carries `video_id + start_ms`, the tutor can cite **the exact moment**:

```
"To bass-swap on the transition, cut the incoming track's lows while
 bringing the fader up — DJ TechTools demos this at 4:12.
 → https://youtube.com/watch?v=<id>&t=252s"
```

The `&t=<seconds>` URL param deep-links to the exact second. This is the *strongest possible grounding*: the user can verify the technique by watching the source moment. It also keeps the legal posture clean — we're **driving views to the creator**, not replacing the video.

### 4.4 Bravoh quoting-engine angle

This is the strategic tie-in. **Bravoh's quoting engine** (the system that cites *video moments* with timestamps) is the same primitive vibemix needs for video-grounded teaching:
- vibemix's tutor lens proves out **"cite the exact second of a video as evidence"** on a narrow, friendly domain (DJ how-tos).
- The chunk→timestamp→deep-link→verify loop is reusable: vibemix is the OSS testbed for Bravoh's quoting engine, the same way vibemix as a whole warms an audience into Bravoh's waitlist.
- Design the `KnowledgeChunk` schema's video-citation fields to **match Bravoh's quoting-engine contract** so the work transfers directly into the main product. (Worth a look at Bravoh's existing quoting-engine schema before finalizing the field names.)

---

## Recommended next step

A **link-out RAG slice**: ingest Tier-1 text sources (DJ TechTools + Digital DJ Tips + Mixed In Key) as **paraphrased+attributed chunks** into a `knowledge.db` collection in the existing library store, wire `retrieve_dj_knowledge` into `library/toolset.py` + `mcp_server.py`, and ground it through `EvidenceRegistry` under Invariant #2. That ships the tutor lens with zero legal exposure (summaries + deep links), reuses 90% of existing infra, and sets up the YouTube/Bravoh-quoting-engine expansion as phase 2. First-party articles (Francesco-authored) + a permission ask to Crossfader/Mixed In Key are the clean path to full-text depth.

---

## Sources

- DJ TechTools — https://djtechtools.com/ (EQ theory `/2012/03/11/eq-critical-dj-techniques-theory/`, phrasing `/2014/11/16/how-to-dj-101-why-you-must-understand-phrasing/`, `/2019/11/11/dj-fundamentals-how-phrasing-can-make-or-break-a-dj-mix/`, Filter vs EQ `/2011/12/07/filter-vs-eq-which-when-why/`, Pro DJ Link `/2018/07/31/`)
- Digital DJ Tips — https://www.digitaldjtips.com/ (Mixing In Key `/beginner-1-2-3-of-mixing-in-key/`, Mixer Basics `/dj-mixer-basics-free-lesson/`, robots.txt reviewed)
- Mixed In Key — https://mixedinkey.com/harmonic-mixing-guide/ , https://mixedinkey.com/camelot-wheel/ , https://mixedinkey.com/wiki/harmonic-mixing-explained-everything-you-need-to-know/
- Crossfader — https://wearecrossfader.co.uk/blog/the-complete-dj-course-free/ , /blog/free-lessons/ , genre lessons
- Native Instruments blog — https://blog.native-instruments.com/dj-tips/ , https://blog.native-instruments.com/crossfader-traktor-courses/
- rekordbox tutorials — https://rekordbox.com/en/video/ , https://rekordbox.com/en/connect/pete-tong-dj-academy/how-to-start-djing/
- Pioneer DJ News — https://www.pioneerdj.com/en/news/2019/learn-how-to-dj-online/ , /2019/ddj-400-dj-controller-mixing-technique-tutorials/
- Rane DJ Support — https://support.rane.com/ , https://www.rane.com/
- Beatportal / Pete Tong DJ Academy — https://www.beatportal.com/ , https://www.petetong-djacademy.com/ , https://www.ffsdjacademy.com/
- RAG chunking & grounding — Weaviate chunking strategies (https://weaviate.io/blog/chunking-strategies-for-rag), Atlan (https://atlan.com/know/chunking-strategies-rag/), Towards Data Science grounding guide, Ingest-And-Ground (arxiv.org/pdf/2410.02825)
- YouTube transcript RAG — https://use-apify.com/blog/youtube-transcripts-llm-rag-pipelines-2026 , https://customgpt.ai/ingest-youtube-video-data-ai-knowledge-base/ , https://www.youtube-transcript.io/terms-of-service
- Web-scraping legal — Thomson Reuters v. Ross ruling coverage; Sage journal "Web scraping for research" (2025); tendem.ai / groupbwt.com / infomineo.com legal guides
