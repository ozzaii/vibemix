# Phase 65: Memory Retrieval Seam (ANTI-SLOP RELEASE GATE) - Research

**Researched:** 2026-05-22
**Domain:** Live-reaction-path retrieval grounding — embed a live query → `MemoryStore.query_topk(..., exclude_session=)` → similarity-floor filter → PAST-tense fence → register `recall` record_ids in `EvidenceRegistry` → inject a gated `recall[…]` block into `coach.py::evidence_line`, riding the EXISTING `CitationLinter` with ZERO new linter code. The milestone's hard hallucination gate: retrieval poisoning, defeated structurally.
**Confidence:** HIGH — every load-bearing claim verified against live `src/vibemix/` source (file:line cited inline), not training data. The "zero new linter code" claim is CONFIRMED; the "zero edits beyond adding the source" sub-claim is REFINED (the regex alternation string + grammar block + strip whitelist are 4 schema-mirror sites that each need `recall` added — the linter *logic* is untouched; see §RECALL-01 Proof).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Area 1 — Citability by construction (the anti-slop core)**
- `recall` is an existence-only evidence source added to `EVIDENCE_SOURCES` (`src/vibemix/state/evidence_registry.py`) and registered in the `EvidenceRegistry` exactly like `key:` (Phase 59) and `track:`. Retrieved `record_id`s registered BEFORE the LLM call. A `[recall:<id>]` the registry never saw → the EXISTING `CitationLinter` strips the WHOLE turn. ZERO new linter code — reuse the binary response-level strip verbatim.
- Recall citation token format mirrors existing sources: `[recall:<record_id>]`, where `record_id` is the Phase 63/64 `f"{session_id}:{seq}"`.

**Area 2 — The gated prompt block (byte-identical when cold)**
- Add a `recall[…]` block to `state/coach.py::evidence_line`, copying the Phase 59 `decks[…]` gate structure verbatim: no retrieved moments (cold / empty / all-below-floor) → inject NOTHING → byte-identical to v5.0 baseline (golden test pins this).
- Retrieved moments fenced PAST-tense with an explicit "FROM A PAST SESSION" header. Live audio/deck/now-playing evidence stays primary; recall clearly subordinate.

**Area 3 — Retrieval policy (anti-poisoning by construction)**
- Top-k cap = 2–3.
- Similarity floor ≈ 0.7 (mirror `CITATION_THRESHOLD`) — below floor → inject NOTHING. Exact value Kaan-ear tuned.
- Event-gated to track-aware events (TRACK_CHANGE / PHASE / LAYER_ARRIVAL) — NEVER HEARTBEAT.
- Current session excluded via `query_topk(..., exclude_session=<current_session_id>)` (shipped Phase 63, unused until now).
- Cosine-only vs cosine+time-weight blend + decay half-life (in SESSIONS, not hours) = the in-phase tuning question. Ship a conservative default; Kaan-ear veto decides.

**Area 4 — Off-hot-path / budget / invariants / veto**
- Within €50/mo budget: event-gate + Phase 64 signature embed cache + a HARD DEADLINE (late memory is worse than no memory — miss the deadline → inject nothing). Live query embedding reuses `library/embed.py` (router-resolved, FLEX).
- TTFT p95 unchanged feature-on vs feature-off (offload the embed+query, bound it).
- Four cardinal invariants hold: single-writer (retrieval never writes `MusicState`), citation-grounding (the `recall` source + linter), trust-the-audio (recall subordinate, past-tense, floored), one-socket (no new port).
- Kaan-ear veto on retrieval relevance is the hard quality gate (mirrors Phase 60 harmonic veto). Default posture (autonomous `fully`): ship the seam wired + tested with conservative thresholds; the live-relevance veto flip + threshold/blend tuning are KAAN-ACTION (do not block engineering close).

### Claude's Discretion
- Module placement of the retrieval helper (a `recall`-builder in `state/coach.py` vs a sibling `memory/retrieval.py` that coach imports), the conservative default blend (cosine-only vs light decay), and the precise event-gate set — guided by the Phase 59 `decks[…]`/`key:` precedent and the event taxonomy. The retrieval helper must NOT import anything that breaks single-writer/one-socket.

### Deferred Ideas (OUT OF SCOPE)
- Visible copilot moves → Phase 66 (built ON this seam).
- Exact cosine-vs-time blend / half-life / threshold tuning + the live-relevance veto flip → in-phase research + Kaan-ear (KAAN-ACTION; ship conservative defaults).
- `audio_moment` retrieval → future milestone (text-signature retrieval only in v6.0).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RECALL-01 | A new `recall` evidence source (existence-only) added to `EVIDENCE_SOURCES`, flowing through the EXISTING `CitationLinter` with ZERO new linter code (à la Phase 59 `key:`) — each retrieved `record_id` registered before the LLM call; a fabricated `[recall:<id>]` strips the whole turn. | §RECALL-01 Proof (the linter is data-driven off `EVIDENCE_SOURCES`; `recall` joins the existence-only set by being IN `EVIDENCE_SOURCES` and ABSENT from `_TIME_KEYED_SOURCES`; linter logic byte-unchanged). The 4 schema-mirror edit sites enumerated. |
| RECALL-02 | Coach prompt grounded with top-k (2–3 cap) past moments via a gated `recall[…]` block in `evidence_line` (copying the `decks[…]` gate verbatim → byte-identical cold golden), behind a ~0.7 floor, event-gated to track-aware events. | §The Gated `recall[…]` Block (the verbatim `decks[…]` gate copy + the exact silent-state golden that must stay green), §Retrieval Policy Defaults. |
| RECALL-03 | Anti-poisoning by construction: below-floor → inject nothing; PAST-tense "FROM A PAST SESSION" fence; current session excluded. Cosine-vs-time blend + half-life tuned in-phase. | §Anti-Poisoning Trio (where each guard lives), §Retrieval Policy Defaults (the conservative blend recommendation + deferral). |
| RECALL-04 | Retrieval stays off the hot path / within €50/mo; four cardinal invariants hold; ships behind a Kaan-ear veto on retrieval relevance. | §The Query & Latency Budget (offload + hard deadline), §Four Cardinal Invariants + Budget, §The Kaan-Ear Veto Flag. |
</phase_requirements>

## Summary

Phase 65 is a **wiring + structural-guard phase, not an algorithm phase**. Every primitive ships: the read seam (`MemoryStore.query_topk(query_embedding, k, *, exclude_session=)` — `store.py:312`, with `exclude_session` already correctly implemented at `:329-337` and explicitly reserved for this phase), the embedder (`LibraryEmbedder.embed_query` — `embed.py:362`), the linter (`CitationLinter` — `citation_linter.py`, fully data-driven off `EVIDENCE_SOURCES`), the gate pattern (the Phase 59 `decks[…]` block in `coach.py:96-109`), the existence-only source precedent (`key` — `evidence_registry.py:103`), and the off-path event-gated enrichment-service shape (`library/grounding.py::Grounding` — `grounding.py:169`, the *exact* architectural analog). The genuinely new code is: the `recall` source added to 4 schema-mirror sites, a `recall[…]` evidence_line block (a verbatim copy of the `decks[…]` gate), a small `MemoryRecall` enrichment service (mirror `Grounding`), and the past-tense fence string.

**Three load-bearing findings that sharpen the naive plan:**

1. **"Zero new linter code" is TRUE. "Zero edits beyond adding the source" is FALSE — there are 4 schema-mirror edit sites, not 1.** The CitationLinter logic is genuinely untouched: `_validate_atom` (`citation_linter.py:175-213`) dispatches on `source in _TIME_KEYED_SOURCES` (`:52`) → existence-only branch `body in snapshot.get(source, {})` (`:212`). Adding `recall` to `EVIDENCE_SOURCES` and KEEPING it out of `_TIME_KEYED_SOURCES` is all the *linter* needs. BUT the source vocabulary is mirrored across 4 places that the regex/grammar/strip-whitelist read, and `parse_citations` only matches sources the **regex alternation `_SOURCE_ALT`** whitelists. So `recall` must be added to: (a) `EVIDENCE_SOURCES` frozenset, (b) the `_SOURCE_ALT` regex string + EBNF docstring, (c) `prompts/matrix.py::CITATION_GRAMMAR_BLOCK`, (d) `agent/dj_cohost.py::_build_citation_strip` whitelist. This is the documented "SCHEMA-MIRROR" contract (`evidence_registry.py:100-102`), and three lockstep tests pin it (`test_evidence_11_sources_constant_locked`, `test_o_citation_grammar_block_contains_eight_source_forms`, the strip test). Each is a data/string addition — **none touches linter, registry, or store logic.** [VERIFIED: citation_linter.py:52,194,212; evidence_registry.py:100-135]

2. **The threshold to mirror is `CITATION_THRESHOLD = 0.7` in `library/grounding.py:39` — NOT a `coach.py` constant, and NOT `LIVE_TOLERANCE_S`.** `LIVE_TOLERANCE_S = 1.0` (`coach/constants.py:15`) is a *time* tolerance for `@t`-keyed citations, irrelevant to existence-only recall. The real cosine floor precedent is `CITATION_THRESHOLD = 0.7` (the library grounding `cosine >= 0.7 → cite` gate; `__main__.py:939` already prints "threshold=0.7"). Recall's similarity floor should be a NEW constant in the recall module (default `0.7`), conceptually mirroring `CITATION_THRESHOLD` — do NOT import the library one (that couples memory to library); copy the value with a comment pointing at `grounding.py:39`. [VERIFIED: grounding.py:39, coach/constants.py:15, no `CITATION_THRESHOLD` in coach/state]

3. **`embed_query` has NO content-hash cache (`embed.py:362-369`).** This is the same Finding 2 Phase 64 hit. For a *live* query embedding on the reaction path, a cache is the WRONG mitigation anyway (queries are unique per moment). The correct mitigation is the **hard deadline + event-gate** — bound the embed+query to a deadline, miss it → inject nothing (the live audio still grounds the turn). The €50/mo budget holds because the event-gate fires retrieval only on track-aware events (NOT HEARTBEAT, the highest-frequency class), and one FLEX embed per track-aware event is the same order as the existing `Grounding.on_event` embed already shipping. [VERIFIED: embed.py:362, ACK_ELIGIBLE excludes the gate, grounding.py event-gating]

**Primary recommendation:** Add `recall` to the 4 schema-mirror sites. Ship a `MemoryRecall` enrichment service in `src/vibemix/memory/retrieval.py` (sibling of `store.py`/`ingest.py`, so the shipped Phase-63/64 no-live-path + no-extraction gates auto-cover it) that mirrors `library/grounding.py::Grounding`: `on_event(event_type, query_text, current_session_id)` → gated on track-aware events → `embed_query` under a hard deadline → `query_topk(qvec, k=3, exclude_session=current)` → filter `score >= RECALL_SIMILARITY_FLOOR (0.7)` → store the surviving Records (lock-guarded). The agent registers the survivors' `record_id`s in the `EvidenceRegistry` (`registry.write("recall", record_id, t_session)`) BEFORE the LLM call and pulls them via `get_latest()` to build the `recall[…]` block. `evidence_line` gains a `decks[…]`-shaped gated block. Conservative blend: **cosine-only with the 0.7 floor dominating** (defer any time-decay to the Kaan-ear pass). Behind a `recall_enabled` flag (default ON for the seam wiring, the live-relevance *veto* is the KAAN-ACTION flip).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Decide WHEN to retrieve (event-gate) | Live reaction path (agent `llm_node` / event dispatch) | — | Event taxonomy lives here; retrieval is gated to track-aware events, mirroring `Grounding.on_event`. |
| Embed the live query | External API (Gemini Embedding 2 via Bravoh proxy, FLEX) | Hard deadline bound | `embed_query` is off-path-able via `run_in_executor`; no cache (queries unique). |
| Rank past moments | Local storage (`MemoryStore.query_topk` → `cosine_topk`) | `exclude_session` filter | Phase 63 read seam; the single ranking chokepoint (P55). |
| Floor + fence + register | Live reaction path (recall service + agent) | `EvidenceRegistry` | The anti-poisoning guards are structural and live AT the prompt boundary. |
| Inject the gated block | Prompt builder (`coach.py::evidence_line`) | — | Byte-identical-when-cold gate; subordinate past-tense fence. |
| Strip a fabricated `[recall:<id>]` | EXISTING `CitationLinter` (response-level binary) | — | Zero new linter code; data-driven off `EVIDENCE_SOURCES`. |

> No new socket/port (one-socket). No UI tier — the recall *chip* is Phase 66; this phase is backend prompt/linter/retrieval only. **Frontend skill confirmed N/A** (see Project Constraints). The only external network call is the FLEX query embed, identical in shape to the shipping `Grounding` embed.

## Standard Stack

**Net-new third-party dependencies: ZERO.** Everything below already ships.

### Core (all REUSED, not installed)
| Module | Path:line | Purpose | Status |
|--------|-----------|---------|--------|
| `MemoryStore.query_topk(qvec, k, *, exclude_session=)` | `memory/store.py:312` | The read seam. `exclude_session` filters one session before `cosine_topk` ranking (`:329-337`) — shipped Phase 63, explicitly reserved for THIS phase. Returns `list[Record]` with `.score` (cosine), `.signature` (raw), `.session_id`, `.record_id`. | `[VERIFIED: store.py:312,329]` |
| `Record` | `memory/store.py:147` | Raw-out carrier: `record_id, session_id, ts, kind, signature, score`. | `[VERIFIED: store.py:147]` |
| `LibraryEmbedder.embed_query(text)` | `library/embed.py:362` | Live query → 768-dim L2-normalized vec via Gemini Embedding 2, FLEX, proxy-only. **No content-hash cache (`:365`).** | `[VERIFIED: embed.py:362]` |
| `CitationLinter.check(text, snapshot, mode="live")` | `coach/citation_linter.py:94` | Response-level binary strip. Data-driven: existence-only branch handles any source in `EVIDENCE_SOURCES` ∖ `_TIME_KEYED_SOURCES`. | `[VERIFIED: citation_linter.py:94,212]` |
| `EVIDENCE_SOURCES` frozenset | `state/evidence_registry.py:103` | Source-of-truth vocabulary. Add `recall`. | `[VERIFIED: evidence_registry.py:103]` |
| `EvidenceRegistry.write(source, key, t_session)` | `state/evidence_registry.py:200` | Register `recall` record_ids before the LLM call (like `register_library` does for `track`, `:234`). | `[VERIFIED: evidence_registry.py:200,234]` |
| `EvidenceRegistry.snapshot()` | `state/evidence_registry.py:283` | The frozen dict the linter checks. Already snapshotted once-per-turn at `dj_cohost.py:523`. | `[VERIFIED: evidence_registry.py:283; dj_cohost.py:523]` |
| `AICoach.evidence_line(state, *, registry_snapshot=)` | `state/coach.py:53` | The gated-block host. The `decks[…]` gate (`:96-109`) is the verbatim template. | `[VERIFIED: coach.py:96]` |
| `library/grounding.py::Grounding` | `library/grounding.py:169` | The architectural precedent: stateful, lock-guarded, event-gated enrichment service — `on_event` → store latest → prompt pulls → `clear()`. Mirror this shape for `MemoryRecall`. | `[VERIFIED: grounding.py:169-220]` |
| `CITATION_THRESHOLD = 0.7` | `library/grounding.py:39` | The cosine-floor precedent to MIRROR (copy the value, don't import). | `[VERIFIED: grounding.py:39]` |
| `EVENT_PRIORITY` / event types | `state/event.py:32-52` | The 7 canonical types + KEY_CLASH/TRANSITION_OPPORTUNITY. Track-aware gate set drawn from here. | `[VERIFIED: event.py:32]` |
| `ACK_ELIGIBLE_EVENTS` | `state/coach.py:44` | `{HEARTBEAT, MIX_MOVE, LAYER_ARRIVAL, KAAN_SPOKE}` — the diet/cheap path. HEARTBEAT here = NEVER retrieve. | `[VERIFIED: coach.py:44]` |

### Alternatives Considered (all rejected — locked or off-pattern)
| Instead of | Could Use | Verdict |
|------------|-----------|---------|
| `recall` joins existence-only set via `EVIDENCE_SOURCES` + absent from `_TIME_KEYED_SOURCES` | A `@t`-keyed recall body (`recall:<id>@<t>`) | REJECTED — recall has no live timestamp to validate against; existence-only is the correct + precedented (`key`/`track`) shape. Keeping it out of `_TIME_KEYED_SOURCES` is the whole trick. |
| New `RECALL_SIMILARITY_FLOOR = 0.7` constant in `memory/retrieval.py` | Import `CITATION_THRESHOLD` from `library.grounding` | RECOMMEND the copy — importing `library.grounding` couples memory→library and risks pulling library internals into the retrieval helper. Copy `0.7` with a `# mirrors library/grounding.py:39 CITATION_THRESHOLD` comment. |
| `MemoryRecall` in `src/vibemix/memory/retrieval.py` | A `recall`-builder method inside `state/coach.py` | RECOMMEND the sibling module — keeps `coach.py` byte-stable except the gated block, and lands the helper INSIDE `memory/` where the shipped no-live-path + no-extraction gates auto-cover it. `coach.py` only reads the survivors via a passed-in arg/snapshot; it imports nothing new. |
| Cosine-only conservative default | Cosine + exp time-decay blend (half-life in sessions) | RECOMMEND cosine-only for v1 (floor dominates); defer the blend to Kaan-ear. See §Retrieval Policy. |
| Hard-deadline bound on embed+query | Content-hash cache on `embed_query` | REJECTED — live queries are unique per moment, a cache never hits. The deadline + event-gate is the correct budget/latency control. |

**Installation:** none. Confirm `import vibemix.memory.store`, `vibemix.library.embed.LibraryEmbedder`, `vibemix.state.evidence_registry` resolve (they do — Phases 63/64 GREEN).

## Package Legitimacy Audit

> No external packages installed by this phase. All primitives are in-repo modules + stdlib (`threading`, `re`, `time`). slopcheck N/A — no install step.

| Package | Registry | Status | Disposition |
|---------|----------|--------|-------------|
| (none) | — | Wires existing modules + stdlib only | No install — N/A |

**Packages removed due to slopcheck [SLOP]:** none. **Packages flagged [SUS]:** none.

## RECALL-01 Proof: Zero New Linter Code (the load-bearing claim)

**Claim:** adding `recall` makes `[recall:<id>]` ride the existing CitationLinter binary whole-turn strip with ZERO new linter code. **Verdict: TRUE for linter logic; the source vocabulary is mirrored across 4 sites (each a data/string edit, no logic change).**

### The trace: `[key:…]` → registry → prompt → strip (the precedent recall copies)

1. **Register before the LLM call.** Phase 59 registers `key` observations via `registry.write("key", "A:8A", t)`. Phase 25 registers `track` ids via `register_library` (`evidence_registry.py:234-279`) — a bulk `write("track", id, 0.0)`. **Recall copies this:** for each surviving Record, `registry.write("recall", record.record_id, t_session)` BEFORE the LLM call. [VERIFIED: evidence_registry.py:200,271]

2. **Prompt teaches the grammar.** `CITATION_GRAMMAR_BLOCK` (`matrix.py:101`) lists each source form (`[key:<deck>:<camelot>]` at `:117`). Recall adds `[recall:<record_id>]`. [VERIFIED: matrix.py:117]

3. **Gemini emits, linter checks.** At `dj_cohost.py:1034`, `self._linter.check(full_text, snapshot, mode="live")` runs against the once-per-turn snapshot taken at `:523`. `parse_citations` (`evidence_registry.py:452`) walks `EVIDENCE_CITATION_RE` matches; `_validate_atom` (`citation_linter.py:175`) dispatches:
   - `if source in _TIME_KEYED_SOURCES` (`:199`) → `@t` parse. **`recall` is NOT in this set** → falls through.
   - else (existence-only, `:211-213`): `valid = body in snapshot.get(source, {})`. A `[recall:20260520-2200:7]` whose `record_id` the registry never wrote → `body not in snapshot["recall"]` → `valid=False` → `missing` non-empty → `reason="invalid_atoms"` → `LintResult(valid=False)` → **the whole turn strips** (`dj_cohost.py:1112` strip path). [VERIFIED: citation_linter.py:199,212,156-173; dj_cohost.py:1112]

   The linter's existence-only branch is **literally the same code** that already validates `track`/`screen`/`mix`/`tend`/`key`. Adding `recall` to `EVIDENCE_SOURCES` (and keeping it absent from `_TIME_KEYED_SOURCES`) is the entire linter change — and both are data, not logic.

### The 4 schema-mirror edit sites (SCHEMA-MIRROR contract, `evidence_registry.py:100-102`)

`parse_citations` only emits atoms the **regex alternation** whitelists — so `recall` MUST join the alternation, or `[recall:…]` is silently never parsed (and a fabricated one would pass un-stripped — a SILENT POISONING HOLE). The contract names 4 lockstep sites:

| # | Site | Edit | Pinned by test |
|---|------|------|----------------|
| 1 | `EVIDENCE_SOURCES` frozenset (`evidence_registry.py:103`) | add `"recall"` | `test_evidence_11_sources_constant_locked` (`tests/state/test_evidence_registry.py:210`) asserts exact set — UPDATE to 9 sources |
| 2 | `_SOURCE_ALT` regex string + EBNF docstring + `_INNER_ATOM` (`evidence_registry.py:117-135`) | append `\|recall`; doc the `recall:<record_id>` body | `test_evidence_12_registry_grammar_coherence` (every source matchable) |
| 3 | `CITATION_GRAMMAR_BLOCK` (`prompts/matrix.py:101-138`) | add `[recall:<record_id>]  past-moment reference` form | `test_o_citation_grammar_block_contains_eight_source_forms` (`tests/prompts/test_matrix.py:396`) — UPDATE to 9 forms |
| 4 | `_build_citation_strip` whitelist (`agent/dj_cohost.py:146`) | add `recall` | `tests/agent/test_citation_strip_emit.py` |

> **NOTE — Phase 64 already copied `_SOURCE_ALT` into `memory/ingest.py:79`.** That copy is for ingest-time citation *extraction* from past `ai_text`, and `recall` is NOT an ingest-time source (it's a retrieval-time source the LLM emits about past moments). **Do NOT add `recall` to `ingest.py:79`** — a stored past reaction can never have cited `[recall:…]` (recall didn't exist when it was recorded), and adding it there would be dead/confusing. Leave `ingest.py:79` at 8 sources. Flag this asymmetry in the plan so a future maintainer doesn't "fix" the mismatch.

**Conclusion:** RECALL-01 holds. The linter, registry, and store logic are byte-unchanged. The 4 edits are pure vocabulary additions, each guarded by an existing lockstep test that must be updated to expect 9 sources. The `key` source (Phase 59) is the exact, recently-walked precedent.

## The Gated `recall[…]` Block (RECALL-02)

### The verbatim `decks[…]` gate to copy (`coach.py:96-109`)

```python
# Phase 59-04 — copied verbatim as the recall[…] template
if state.deck_state.decks:                       # ← gate: empty → emit NOTHING
    resolved = {s: d for s, d in ... if d.camelot and d.confidence >= 0.3}
    if resolved:
        parts = [f"{s}={d.title!r} {d.camelot} {d.bpm:.0f}bpm" for s, d in sorted(...)]
        e.append("decks[" + " | ".join(parts) + "]")
    else:
        e.append("decks=unknown")                # ← decks present, none resolved
```

### The recall block (additive, gated identically)

The cleanest seam: `evidence_line` gains an optional kwarg `recall_moments: list[Record] | None = None` (default None → byte-identical to v5.0, exactly like `registry_snapshot=None` already does at `coach.py:57,156`). The block appends ONLY when the list is non-empty:

```python
# Phase 65 — recall[…] block. ADDITIVE + gated so an EMPTY/None recall_moments
# emits NOTHING and the v5.0 evidence_line stays byte-identical (the silent-state
# golden at tests/state/test_coach.py:47 stays green). Mirrors the decks[…] gate.
# PAST-TENSE fenced so it can NEVER be read as live evidence (RECALL-03).
if recall_moments:                               # ← None or [] → emit NOTHING
    parts = [f"[recall:{m.record_id}] {m.signature}" for m in recall_moments]
    e.append("FROM A PAST SESSION (not happening now): " + " || ".join(parts))
```

> **The gate semantics that make the cold golden byte-identical:** `if recall_moments:` is falsy for both `None` (cold/feature-off) AND `[]` (event fired but all below floor / deadline missed / current-session-only). In every empty case, ZERO bytes are appended. This is the SAME falsy-gate discipline as `decks` (`if state.deck_state.decks:`) and `registry_snapshot` (`if registry_snapshot:` at `:156`). **No "I don't remember anything" filler — empty is silent.**

### The golden test that MUST stay green

`tests/state/test_coach.py:47` `test_evidence_line_silent_state_full_format`:
```python
assert out == "hearing[silent] | track=unknown | deck=none | set_time=0:00 | recent_moves[8s]: NONE"
```
With `recall_moments=None` (the default), this output is **unchanged** — the recall block is skipped. This is the byte-identical-cold gate. The Phase 59 baseline (`decks` skipped when empty) plus this default-None gate keep ALL of `tests/state/test_coach.py`'s ~20 golden strings green. **A new RED test must pin the populated path** (recall block present + past-tense fence + `[recall:<id>]` tokens) and the empty/below-floor path (no block).

> **`build_prompt` threading:** `build_prompt(ev, *, registry_snapshot=, diet=)` (`coach.py:320`) calls `evidence_line(ev.state, registry_snapshot=snapshot)` at `:351`. Add a `recall_moments=` kwarg threaded through `build_prompt` → `evidence_line`, defaulting None. The agent passes the survivors. `diet` events (HEARTBEAT etc.) use `_evidence_line_compact` (`:166`) which has NO recall block — correct, since HEARTBEAT is never a retrieval event. [VERIFIED: coach.py:320,351,348]

## The Query & Latency Budget (RECALL-04)

### What live context becomes the query

The retrieval query should be the SAME deterministic signature shape the moments were stored as (Phase 64 `coach_line` signature: `coach_line | track=… | phase=… | deck=… | event=… | cite=… | said: …`). At retrieval time there is no `said:` yet (we're about to generate it), so the query is the **context prefix**: build the live `track / phase / deck / event_type` from `ev.state` + `ev.type` into the same template head (omit `cite=`/`said:`). This keeps query and stored vectors in the same semantic neighborhood (track-vibe + event-shape) — embedding asymmetry is minimized because both come from the locked template. Recommend a small `build_recall_query(ev) -> str` helper in `memory/retrieval.py` reusing Phase 64's template constants.

> Alternative considered: embed the live audio (multimodal). REJECTED for v1 — `audio_moment` is deferred (CONTEXT), and text-signature symmetry with the stored corpus is the conservative, anti-poisoning choice.

### Embedding + latency budget

- `LibraryEmbedder.embed_query(query_text)` (`embed.py:362`) — one FLEX text embed, no cache, ~same cost/latency as the shipping `Grounding` embed.
- **Where it sits relative to the turn build:** retrieval must complete (or be abandoned) BEFORE `build_prompt` runs at `dj_cohost.py:538`, because the survivors feed the `recall_moments=` kwarg. Two options:
  - **(Recommended) Pre-dispatch on event arrival.** Mirror `Grounding.on_event`: when a track-aware event is dispatched (before `llm_node`), kick `MemoryRecall.on_event(...)` via `loop.run_in_executor(None, ...)` with a hard deadline (`asyncio.wait_for(..., timeout=RECALL_DEADLINE_S)`). Store survivors lock-guarded. `llm_node` pulls `recall.get_latest()` at prompt-build time — if the executor hasn't finished or timed out, `get_latest()` returns `[]` → no block → no TTFT regression. This is the "late memory is worse than no memory" rule, structurally enforced.
  - **(Rejected) Inline await in `llm_node`.** Would add the embed+query latency directly to TTFT — violates RECALL-04's "TTFT p95 unchanged".
- **`RECALL_DEADLINE_S` default: 0.5s** (conservative — embed round-trip on FLEX is typically sub-300ms; 0.5s leaves margin without ever stalling the turn). Tunable.
- **`clear()` after each turn** (mirror `Grounding.clear()` at `grounding.py:216`) so a stale survivor set isn't replayed on the next HEARTBEAT turn (which never retrieves).

### Budget (€50/mo)

- **Event-gate is the budget control.** HEARTBEAT (the most frequent event class — see `ACK_ELIGIBLE_EVENTS`) NEVER retrieves. Track-aware events (TRACK_CHANGE / PHASE / LAYER_ARRIVAL) fire on the order of once per track / per section — a handful per song. One FLEX embed each is the same order as the already-budgeted `Grounding.on_event` embed. No new sustained cost class.
- **No re-embed of the corpus** — retrieval reads pre-embedded stored vectors via `query_topk` (zero embed cost for the corpus side; only the single live query embeds).

## Anti-Poisoning Trio (RECALL-03) — where each guard lives

| Guard | Mechanism | Where it lives | Verified-against |
|-------|-----------|----------------|------------------|
| **Below-floor → inject nothing** | After `query_topk`, filter `[r for r in hits if r.score >= RECALL_SIMILARITY_FLOOR]`. Empty survivors → `recall_moments=[]` → falsy gate → no block. | `MemoryRecall.on_event` (filter) + `evidence_line` (falsy gate) | `cosine_topk` returns `.score`; the `if recall_moments:` gate is the `decks` pattern. |
| **PAST-tense fence** | The literal `"FROM A PAST SESSION (not happening now): "` header prefixing the block; mirrors the Phase 60 `TRANSITION_OPPORTUNITY` past-tense discipline (`coach.py:291-316`). | `evidence_line` recall block | Phase 60 already enforces "PAST-TENSE only … the moment's already gone" (`coach.py:311`). |
| **Current session excluded** | `query_topk(qvec, k, exclude_session=current_session_id)` — the shipped `:329-337` filter drops the live session's own records before ranking. | `MemoryRecall.on_event` passes `exclude_session` | `store.py:329-337` correctly implemented + reserved for Phase 65. |

> **The fourth structural guard (citability):** a fabricated `[recall:<id>]` strips the whole turn (RECALL-01). So even if a poisoned (irrelevant-but-above-floor) moment is injected, the LLM can only *cite* a record_id the registry actually saw — and if it invents one, the turn is silenced. Floor + fence + exclusion + citability = four independent structural defenses, none a prompt plea.

## Retrieval Policy Defaults (the conservative recommendation + the deferral)

| Knob | Conservative v1 default | Rationale (anti-poisoning) | Tuning owner |
|------|------------------------|----------------------------|--------------|
| **Top-k cap** | **k=3** at `query_topk`, then floor-filter (survivors ≤ 3) | "One good callback beats ten weak ones." k=3 gives the floor room to cut to 1–2 without a second query. | Fixed v1 (Kaan may lower to 2) |
| **Similarity floor** | **0.7** (`RECALL_SIMILARITY_FLOOR`, mirrors `CITATION_THRESHOLD` `grounding.py:39`) | The proven library cite-floor; below it, cosine neighbors are noise. The floor is the dominant poisoning defense. | KAAN-ACTION (tune on real corpus) |
| **Event gate** | `{TRACK_CHANGE, PHASE, LAYER_ARRIVAL}` (+ optionally `KEY_CLASH`/`TRANSITION_OPPORTUNITY` — both track-aware). **NEVER HEARTBEAT, MIX_MOVE, KAAN_SPOKE, MANUAL.** | Track-aware events are where a past-moment callback is meaningful; HEARTBEAT would spam retrieval + burn budget. | Fixed v1 |
| **Current-session exclusion** | always `exclude_session=current_session_id` | A session can't "remember itself" — that's live evidence, not memory. | Fixed (invariant) |
| **Cosine-vs-time blend** | **COSINE-ONLY** (no time-decay term in v1) | A light exp-decay (half-life in *sessions*) is plausible but adds a tuning surface with no evidence it helps; the floor already dominates relevance. Shipping cosine-only keeps the conservative posture and avoids over-engineering. The blend is a Kaan-ear question. | **DEFERRED → KAAN-ACTION** |
| **Decay half-life** | **N/A in v1** (cosine-only) | If Kaan's ear wants recency weighting, the recommended shape is `score' = cosine * exp(-Δsessions / H)` with H≈5 sessions as a STARTING point — but only added if the cosine-only seam proves to surface stale callbacks. Floor stays the gate. | **DEFERRED → KAAN-ACTION** |
| **Hard deadline** | `RECALL_DEADLINE_S = 0.5s` | Late memory is worse than no memory; miss → inject nothing → no TTFT regression. | Tunable |
| **Feature flag** | `recall_enabled` default **ON** (seam wired) | The seam ships wired + tested. The *live-relevance veto* (turning a specific callback class off if Kaan's ear says it didn't matter) is the KAAN-ACTION flip — NOT the engineering gate. | KAAN-ACTION (veto flip) |

> **Why cosine-only is the right conservative default (not a light decay):** the milestone thesis is "every retrieval decision is STRUCTURAL." A decay blend is a *relevance heuristic*, not a structural guard — and an untuned decay can DEMOTE a genuinely relevant old moment (the exact thing recall exists to surface). The floor is the structural guard; cosine-only + 0.7 floor is the minimal, defensible v1. Decay is an additive enhancement gated on Kaan's ear finding cosine-only insufficient — never a default.

## The Kaan-Ear Veto Flag (RECALL-04)

Mirror the Phase 60 harmonic-clash veto: ship the seam wired + tested with conservative thresholds; expose a `recall_enabled: bool = True` agent kwarg (mirrors the `grounding=None` opt-out kwarg pattern, `__main__.py:924` "agent reads `grounding` via kwargs"). The **engineering close** = seam wired, GREEN tests, conservative defaults. The **KAAN-ACTION** = (a) live-relevance veto flip if a callback references a moment Kaan's ear says didn't matter, (b) threshold/blend tuning on his real corpus. Do NOT block phase close on the veto pass (autonomous `fully`).

## Four Cardinal Invariants + Budget (RECALL-04)

| Invariant | How held | Verified |
|-----------|----------|----------|
| **Single-writer** (retrieval never writes `MusicState`) | `MemoryRecall` reads `ev.state` (read-only) + `MemoryStore`; writes only its own lock-guarded `_latest` + the `EvidenceRegistry` (which is the citation registry, NOT MusicState). Never holds `state._lock`, never mutates `MusicState`. Mirrors `Grounding` (also reads, never writes MusicState). | `Grounding` precedent (`grounding.py:178-220`); no-live-path gate auto-covers `memory/retrieval.py`. |
| **Citation-grounding** | The `recall` source + the existing CitationLinter strip (RECALL-01). | `citation_linter.py:212`, the 4 schema-mirror edits. |
| **Trust-the-audio** | Recall is subordinate (appended AFTER the live `hearing[…]`/`track=`/`decks[…]` evidence), PAST-tense fenced, and similarity-floored. The live audio is always primary; recall is a footnote. | `evidence_line` append-order; the fence string; the 0.7 floor. |
| **One-socket** | No new port/IPC. Recall rides the existing prompt + the citation strip; the Phase-66 recall *chip* (if any) surfaces on existing ws envelopes — NOT this phase. | No `websockets`/socket import in `memory/retrieval.py`. |
| **Budget €50/mo** | Event-gate (no HEARTBEAT) + hard deadline + corpus pre-embedded (only the single live query embeds). | §The Query & Latency Budget. |

## Architecture Patterns

### System Architecture Diagram (Phase 65 scope — RETRIEVE)

```
   TRACK-AWARE EVENT FIRES (TRACK_CHANGE / PHASE / LAYER_ARRIVAL)
   EventDetector → event dispatch (live reaction path)
        │
        │  (NOT HEARTBEAT/MIX_MOVE/KAAN_SPOKE/MANUAL — event gate)
        ▼
   MemoryRecall.on_event(ev.type, query_text, current_session_id)   ── memory/retrieval.py
        │   (dispatched via loop.run_in_executor + asyncio.wait_for(timeout=0.5s))
        │
        │   1. build_recall_query(ev)  → "coach_line | track=… | phase=… | deck=… | event=…"
        │   2. qvec = embedder.embed_query(query_text)        [FLEX, proxy, no cache]
        │   3. hits = store.query_topk(qvec, k=3, exclude_session=current)   ── memory/store.py
        │   4. survivors = [r for r in hits if r.score >= 0.7]   ← FLOOR (below → [])
        │   5. lock-guarded: self._latest = survivors
        │   (deadline missed / empty → _latest stays [])
        │
        ▼
   AGENT llm_node (dj_cohost.py)
        │   recall_moments = recall.get_latest()      (── [] if not ready / below floor)
        │   for m in recall_moments: registry.write("recall", m.record_id, t)   ← REGISTER
        │   snapshot = registry.snapshot()            (dj_cohost.py:523, once-per-turn)
        │   prompt = build_prompt(ev, registry_snapshot=snapshot,
        │                         recall_moments=recall_moments)   ← NEW kwarg
        │                              │
        │                              ▼
        │   evidence_line: if recall_moments:  append "FROM A PAST SESSION …[recall:<id>] …"
        │                  else (None/[]):     append NOTHING  ← byte-identical cold golden
        │
        ▼   Gemini emits → full_text
   linter.check(full_text, snapshot)   (dj_cohost.py:1034)
        │   [recall:<id>] in snapshot["recall"]?  ── existence-only branch, ZERO new code
        │      YES → valid → emit
        │      NO (fabricated)  → invalid_atoms → STRIP WHOLE TURN (dj_cohost.py:1112)
        │
        ▼   recall.clear()   (after turn — don't replay on next HEARTBEAT)

   ❌ MemoryRecall writes NO MusicState, holds NO state._lock, opens NO socket.
      Reads ev.state (read-only) + MemoryStore. Mirrors library/grounding.py::Grounding.
```

### Recommended Project Structure
```
src/vibemix/memory/
├── store.py        # (Phase 63) query_topk read seam — UNCHANGED
├── ingest.py       # (Phase 64) — UNCHANGED (do NOT add recall to its _SOURCE_ALT)
├── retention.py    # (Phase 63) — UNCHANGED
└── retrieval.py    # NEW: MemoryRecall service + build_recall_query +
                    #      RECALL_SIMILARITY_FLOOR / RECALL_TOP_K / RECALL_DEADLINE_S
                    #      + RECALL_EVENT_GATE frozenset. Mirrors library/grounding.py.

src/vibemix/state/
├── evidence_registry.py  # EDIT: +recall in EVIDENCE_SOURCES + _SOURCE_ALT + EBNF doc
└── coach.py              # EDIT: evidence_line + build_prompt gain recall_moments= kwarg;
                          #       the gated recall[…] block (verbatim decks[…] shape)

src/vibemix/prompts/matrix.py   # EDIT: +[recall:<record_id>] form in CITATION_GRAMMAR_BLOCK
src/vibemix/agent/dj_cohost.py  # EDIT: +recall in _build_citation_strip whitelist;
                                #       register survivors; thread recall_moments into build_prompt;
                                #       dispatch MemoryRecall.on_event + clear()
```

### Anti-Patterns to Avoid
- **Adding `recall` to `_TIME_KEYED_SOURCES`** — would force a `@t` parse and break existence-only validation. `recall` MUST stay out (like `key`/`track`).
- **Forgetting the `_SOURCE_ALT` regex edit** — silent poisoning hole: a fabricated `[recall:…]` would never be parsed → never stripped. The regex MUST whitelist `recall`.
- **Adding `recall` to `memory/ingest.py:79`** — wrong layer; recall is retrieval-time, not ingest-time. Leave ingest at 8 sources.
- **Inline `await embed_query` in `llm_node`** — TTFT regression. Pre-dispatch + deadline only.
- **"I don't remember anything yet" filler when cold** — breaks the byte-identical golden. Empty = silent.
- **A time-decay blend by default** — over-engineering + a relevance heuristic masquerading as a structural guard. Cosine-only + floor for v1.
- **Importing `library.grounding.CITATION_THRESHOLD`** — couples memory→library. Copy the 0.7 value with a source comment.
- **A generic RAG framework** — this is one service + one gated block + 4 vocabulary edits + tests.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Citation strip for `[recall:…]` | A recall-specific validator | Add `recall` to `EVIDENCE_SOURCES`; the existence-only branch (`citation_linter.py:212`) handles it | Zero new linter code; `key` is the precedent. |
| Top-k cosine ranking | A new ranker | `MemoryStore.query_topk` → `cosine_topk` (`store.py:312`) | The single P55 chokepoint; `exclude_session` shipped. |
| Current-session exclusion | A post-filter on results | `query_topk(..., exclude_session=)` (`store.py:329`) | Filters BEFORE ranking; shipped + reserved for this phase. |
| Live query embedding | A new genai client | `LibraryEmbedder.embed_query` (`embed.py:362`) | Proxy-only, FLEX, 768-dim, L2-normalized, no literal. |
| Event-gated off-path enrichment service | A new pattern | Mirror `library/grounding.py::Grounding` (`grounding.py:169`) | Stateful, lock-guarded, `on_event`/`get_latest`/`clear` — the exact analog already shipping. |
| The cosine floor value | A guessed threshold | Mirror `CITATION_THRESHOLD = 0.7` (`grounding.py:39`) | The proven library cite-floor. |
| Gated evidence block | A new conditional shape | Copy the `decks[…]` gate (`coach.py:96-109`) | Byte-identical-cold guarantee proven by Phase 59. |

**Key insight:** every hard part is solved and shipping. Phase 65's only genuinely new code is the `MemoryRecall` service (a 40-line `Grounding` clone), the gated `recall[…]` block (a 4-line `decks[…]` clone), the past-tense fence string, and the `build_recall_query` template head. The "anti-slop gate" is enforced by *reuse*, not new machinery.

## Runtime State Inventory

> NOT a rename/refactor — a greenfield retrieval seam over the (already-shipped) `memory.db`. Standard categories mostly N/A. Verified explicitly:

| Category | Items Found | Action |
|----------|-------------|--------|
| Stored data | READS `memory.db` `moments` (Phase 64 `coach_line` records) via `query_topk`. Writes NOTHING new to disk — `recall` survivors live in-memory (the `MemoryRecall._latest` field) + as transient `EvidenceRegistry` entries (cleared per-session at `evidence_registry.py:218`). | Read-only over `memory.db`; no new table/schema. |
| Live service config | None — no daemon, no UI-stored config this phase owns. **Verified.** | None. |
| OS-registered state | None — in-process, dispatched by the existing agent/event path. **Verified.** | None. |
| Secrets / env vars | The Bravoh-proxy key (read by the proxy client, NOT by `MemoryRecall` — `LibraryEmbedder` cannot read a raw key by design). No new secret. **Verified.** | None. |
| Build artifacts | None new. **Verified.** | None. |

## Common Pitfalls

### Pitfall 1: The silent regex-alternation poisoning hole
**What goes wrong:** `recall` added to `EVIDENCE_SOURCES` but NOT to `_SOURCE_ALT` (`evidence_registry.py:117`). `parse_citations` never matches `[recall:…]` → the linter never sees it → a fabricated `[recall:<bogus>]` rides through UN-STRIPPED. This is the exact poisoning the phase exists to prevent, introduced by an incomplete edit.
**How to avoid:** edit ALL 4 schema-mirror sites together; the lockstep tests (`test_evidence_11`, `test_o`, `test_evidence_12`) catch it if you update them to 9 sources. **Add a RED test that a fabricated `[recall:<unregistered>]` strips the turn.**
**Warning signs:** a `[recall:…]` token survives in emitted text without a matching registry write.

### Pitfall 2: Recall block leaks into the cold golden
**What goes wrong:** the recall block appends an empty/placeholder string when no moments → the silent-state golden (`test_coach.py:47`) breaks; the v5.0 baseline drifts.
**How to avoid:** `if recall_moments:` falsy gate (None AND []) — copy `decks` exactly. Default the kwarg to None. The golden must stay byte-identical with the default.

### Pitfall 3: TTFT regression from inline retrieval
**What goes wrong:** awaiting `embed_query` + `query_topk` inside `llm_node` adds 200–500ms to TTFT.
**How to avoid:** pre-dispatch `MemoryRecall.on_event` via `run_in_executor` + `asyncio.wait_for(timeout=0.5s)`; `get_latest()` returns `[]` if not ready. **Add a test asserting the retrieve path runs off the loop (executor) and a missed deadline → no block.**

### Pitfall 4: Stale survivors replayed across turns
**What goes wrong:** a TRACK_CHANGE retrieves 3 moments; the next HEARTBEAT turn (which must NEVER retrieve) still sees `_latest` populated → injects a stale recall block.
**How to avoid:** `recall.clear()` after every turn (mirror `Grounding.clear()` at end-of-turn, `grounding.py:216-218`). HEARTBEAT never sets `_latest`, so post-clear it's empty.

### Pitfall 5: Embedding asymmetry (query vs stored)
**What goes wrong:** the live query is free-form text while stored signatures are the locked `coach_line | …` template → cosine scores are systematically depressed and never clear 0.7.
**How to avoid:** build the query from the SAME template head (`build_recall_query` reuses Phase 64's template constants, omitting `said:`). Symmetry keeps the floor meaningful.

### Pitfall 6: Current session "remembers itself"
**What goes wrong:** without `exclude_session`, the live session's own just-ingested moments rank top-1 → the AI "recalls" something from 30s ago as a past-session memory.
**How to avoid:** always pass `exclude_session=current_session_id`. (In practice the current session isn't ingested until close, but the guard is structural — pass it unconditionally.) **Add a test.**

## Code Examples

### The `MemoryRecall` service (mirror `library/grounding.py::Grounding`)
```python
# src/vibemix/memory/retrieval.py  (SHAPE — planner refines)
import threading
from vibemix.memory.store import MemoryStore, Record
from vibemix.library.embed import LibraryEmbedder

RECALL_SIMILARITY_FLOOR = 0.7   # mirrors library/grounding.py:39 CITATION_THRESHOLD
RECALL_TOP_K = 3
RECALL_DEADLINE_S = 0.5
RECALL_EVENT_GATE = frozenset({"TRACK_CHANGE", "PHASE", "LAYER_ARRIVAL"})  # NEVER HEARTBEAT

class MemoryRecall:
    """Event-gated, off-path memory retrieval. Mirrors library/grounding.py::Grounding.
    Reads ev.state + MemoryStore; writes only its own _latest. NO MusicState, NO socket."""
    def __init__(self, embedder: LibraryEmbedder, store: MemoryStore) -> None:
        self._embedder = embedder
        self._store = store
        self._lock = threading.Lock()
        self._latest: list[Record] = []

    def on_event(self, event_type: str, query_text: str, current_session_id: str) -> list[Record]:
        if event_type not in RECALL_EVENT_GATE:        # event gate — HEARTBEAT etc. → []
            return []
        qvec = self._embedder.embed_query(query_text)  # FLEX, proxy, no cache (dispatched off-loop)
        hits = self._store.query_topk(qvec, RECALL_TOP_K, exclude_session=current_session_id)
        survivors = [r for r in hits if r.score >= RECALL_SIMILARITY_FLOOR]   # FLOOR
        with self._lock:
            self._latest = survivors
        return survivors

    def get_latest(self) -> list[Record]:
        with self._lock:
            return list(self._latest)

    def clear(self) -> None:                            # call after each turn
        with self._lock:
            self._latest = []
```

### The gated `recall[…]` block (verbatim `decks[…]` shape, in `coach.py::evidence_line`)
```python
# additive kwarg: def evidence_line(state, *, registry_snapshot=None, recall_moments=None)
if recall_moments:                                      # None or [] → emit NOTHING (cold golden green)
    parts = [f"[recall:{m.record_id}] {m.signature}" for m in recall_moments]
    e.append("FROM A PAST SESSION (not happening now): " + " || ".join(parts))
```

### Register survivors before the LLM call (mirror `register_library`, in `dj_cohost.py:llm_node`)
```python
recall_moments = self._recall.get_latest() if self._recall is not None else []
for m in recall_moments:
    self._registry.write("recall", m.record_id, ev.state.set_seconds)   # register → linter can validate
snapshot = self._registry.snapshot()                                    # the SAME snapshot at :523
prompt = AICoach.build_prompt(ev, registry_snapshot=snapshot, recall_moments=recall_moments)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mirror `LIVE_TOLERANCE_S` for the recall floor | Mirror `CITATION_THRESHOLD = 0.7` (`grounding.py:39`) | This research | LIVE_TOLERANCE_S is a *time* band, irrelevant; 0.7 cosine is the real precedent. |
| "Zero edits beyond adding the source" | 4 schema-mirror vocabulary edits (linter LOGIC still zero) | This research | The regex alternation is a separate lockstep site; missing it = silent poisoning hole. |
| Cache `embed_query` for re-cost | Hard deadline + event-gate | This research | Live queries are unique; a cache never hits. Deadline is the right control. |
| Prompt-plea anti-poisoning | Floor + fence + exclusion + citability (4 structural guards) | Milestone thesis | None of the four is a prompt instruction; all are code. |

**Deprecated/outdated:** none. `gemini-embedding-001` literal stays a CI canary (`resolve("embedding")` only); recall embeds via the same `LibraryEmbedder` path.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The agent has access to `current_session_id` at event-dispatch time (the recorder's session dir basename). | The Query | LOW — `dj_cohost.py` holds `self._recorder.session_dir`; basename is the session_id. Verify the exact attribute in plan. |
| A2 | `EvidenceRegistry.write("recall", record_id, t)` with `t=ev.state.set_seconds` validates fine in the existence-only branch (no `@t` parse). | Register survivors | LOW — existence-only sources ignore `@t` (`citation_linter.py:212` checks `body in snapshot[source]` only). The `t_session` arg is stored but not used for recall validation. |
| A3 | Query↔stored embedding symmetry from a shared template head clears 0.7 on genuinely-relevant moments. | Pitfall 5 | MEDIUM — this is exactly what the Kaan-ear corpus tuning validates; if 0.7 proves too high for the template-head query, lower the floor (KAAN-ACTION) — never remove it. |
| A4 | Pre-dispatching recall on event arrival (before `llm_node`) is wireable without touching the single-in-flight gate. | The Query / Latency | LOW — `Grounding.on_event` is already dispatched this way; recall mirrors it. Plan must locate the exact dispatch seam (likely the event-prep path that sets `_pending_event`). |
| A5 | `recall` must NOT be added to `memory/ingest.py:79` `_SOURCE_ALT`. | RECALL-01 Proof | LOW — recall is retrieval-time; a stored past reaction never cited recall. Adding it is harmless-but-dead; leaving it out is correct. |

## Open Questions

1. **Exact event-gate set: include `KEY_CLASH` / `TRANSITION_OPPORTUNITY`?**
   - What we know: both are track-aware (`event.py:48-49`) and could benefit from a past-moment callback ("last time these keys clashed you…").
   - Recommendation: v1 ship `{TRACK_CHANGE, PHASE, LAYER_ARRIVAL}` only (the canonical track-aware trio); add the deck-state events in Phase 66 when the visible callback consumes them. Keep v1 lean.

2. **Where the recall dispatch seam sits relative to `_pending_event`.**
   - What we know: `llm_node` reads `self._pending_event` (`dj_cohost.py:508`); `Grounding.on_event` is dispatched upstream of the turn.
   - Recommendation: dispatch `MemoryRecall.on_event` at the same seam that sets `_pending_event` for a track-aware event, via `run_in_executor` + `wait_for`. Planner pins the exact line.

3. **Floor value on the real corpus (0.7 vs lower).**
   - What we know: 0.7 is the library cite-floor; template-head queries may score lower than full-signature similarity.
   - Recommendation: ship 0.7; if Kaan's ear finds it suppresses good callbacks, lower to ~0.6 (KAAN-ACTION). Never below the point where noise leaks.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `MemoryStore.query_topk` (Phase 63) | the read seam | ✓ | shipped (`memory/store.py:312`) | none — in-repo, 19/19 GREEN |
| `LibraryEmbedder.embed_query` + Bravoh proxy | live query embed | ✓ | shipped (`library/embed.py:362`) | tests use synthetic 768-dim vectors; no live API |
| `CitationLinter` + `EvidenceRegistry` | the strip + registration | ✓ | shipped (`coach/`, `state/`) | none |
| `library/grounding.py::Grounding` | the architectural template (read, not imported) | ✓ | shipped | n/a (reference only) |
| Phase 64 `coach_line` records in `memory.db` | the corpus to retrieve | ✓ (after a session ingests) | shipped Phase 64 | tests seed synthetic Records via `add_record` |
| sqlite-vec extension | (inherited via MemoryStore) | ✓ dev / ✗ Win ARM64 | `0.1.9` | NumpyStore fallback (Phase 63 abstracts) |

**Missing dependencies with no fallback:** none — unit tests run on synthetic vectors + synthetic Records; no live API required.
**Missing dependencies with fallback:** sqlite-vec on Win ARM64 → numpy backend (Phase 63 handles).

## Validation Architecture

> `workflow.nyquist_validation` not set to false → section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` 9.x (dev dep) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`; `--strict-markers` |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q tests/memory tests/state/test_coach.py tests/agent/test_dj_cohost_linter.py` |
| Full suite command | `uv run pytest -q` (or `PYTHONPATH=src python3 -m pytest -q`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RECALL-02 | **Byte-identical cold golden** — `evidence_line(state)` (recall_moments=None) == the v5.0 silent-state string | unit (golden) | `pytest tests/state/test_coach.py::test_evidence_line_silent_state_full_format -x` | ✅ (`:47` — MUST stay green) |
| RECALL-02 | Populated path — `evidence_line(state, recall_moments=[Record…])` appends the past-tense fence + `[recall:<id>]` tokens | unit (golden) | `pytest tests/state/test_coach.py::test_evidence_line_recall_block_present -x` | ❌ Wave 0 |
| RECALL-02 | Empty/below-floor → no block (gate falsy on `[]`) | unit | `pytest tests/state/test_coach.py::test_evidence_line_recall_empty_no_block -x` | ❌ Wave 0 |
| RECALL-01 | `EVIDENCE_SOURCES` == exactly 9 sources incl. `recall` | unit | `pytest tests/state/test_evidence_registry.py::test_evidence_11_sources_constant_locked_GROUND02 -x` | ✅ (UPDATE 8→9) |
| RECALL-01 | `recall` is matchable + writable (regex + registry coherence) | unit | `pytest tests/state/test_evidence_registry.py::test_evidence_12_registry_grammar_coherence -x` | ✅ (auto-iterates EVIDENCE_SOURCES) |
| RECALL-01 | Grammar block lists `[recall:` form (9 source forms) | unit | `pytest tests/prompts/test_matrix.py::test_o_citation_grammar_block_contains_eight_source_forms_and_multi_cite -x` | ✅ (UPDATE 8→9 + add `[recall:`) |
| RECALL-01 | **Fabricated `[recall:<unregistered>]` strips the whole turn** (poisoning gate) | unit | `pytest tests/agent/test_dj_cohost_linter.py::test_fabricated_recall_strips_turn -x` | ❌ Wave 0 |
| RECALL-01 | Registered `[recall:<id>]` passes the linter | unit | `pytest tests/coach/test_citation_linter.py::test_recall_existence_only_valid -x` | ❌ Wave 0 (extend existing linter tests) |
| RECALL-03 | Below-floor result → survivors `[]` → no block | unit | `pytest tests/memory/test_retrieval.py::test_below_floor_injects_nothing -x` | ❌ Wave 0 |
| RECALL-03 | Past-tense fence present in populated block | unit | covered by `test_evidence_line_recall_block_present` | ❌ Wave 0 |
| RECALL-03 | `current_session_id` excluded from its own retrieval | unit | `pytest tests/memory/test_retrieval.py::test_current_session_excluded -x` | ❌ Wave 0 |
| RECALL-04 | Non-track-aware event (HEARTBEAT) → `on_event` returns `[]` (no embed call) | unit | `pytest tests/memory/test_retrieval.py::test_heartbeat_never_retrieves -x` | ❌ Wave 0 |
| RECALL-04 | **TTFT-unchanged** — retrieve runs off-loop; missed deadline → `get_latest()` `[]` → no block, no inline await in `llm_node` | unit | `pytest tests/memory/test_retrieval.py::test_deadline_miss_injects_nothing -x` + a static assert that `llm_node` does not `await embed_query` | ❌ Wave 0 |
| RECALL-04 | `memory/retrieval.py` imports no live-reaction-path module (auto-covered) | unit (static + subprocess) | `pytest tests/memory/test_no_live_path_import.py -x` | ✅ (globs `memory/*.py` — verify it sees `retrieval.py`) |
| RECALL-04 | `memory/retrieval.py` calls only `embed_query` (no generation) — no-extraction gate | unit (static, auto-covered) | `pytest tests/memory/test_no_extraction.py -x` | ✅ (globs `memory/*.py`) |
| (cross) | no hardcoded model literal in `retrieval.py` | unit (shipped gate) | `pytest tests/repo/test_model_literal_gate.py -x` | ✅ |

### Sampling Rate
- **Per task commit:** `PYTHONPATH=src python3 -m pytest -q tests/memory tests/state/test_coach.py` (sub-second).
- **Per wave merge:** the above + `tests/agent/test_dj_cohost_linter.py` + `tests/prompts/test_matrix.py` + `tests/state/test_evidence_registry.py` + the two memory gates.
- **Phase gate:** full suite green before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/memory/test_retrieval.py` — event-gate (HEARTBEAT→[]), below-floor→[], current-session-excluded, deadline-miss→[], embed-called-once.
- [ ] `tests/state/test_coach.py` — add `test_evidence_line_recall_block_present` (populated, past-tense fence, tokens) + `test_evidence_line_recall_empty_no_block`. **Confirm the existing `:47` silent golden stays green with the default kwarg.**
- [ ] `tests/agent/test_dj_cohost_linter.py` — `test_fabricated_recall_strips_turn` (the poisoning gate; the headline RED).
- [ ] **UPDATE** `tests/state/test_evidence_registry.py::test_evidence_11` (8→9 sources) + `tests/prompts/test_matrix.py::test_o` (8→9 forms + `[recall:`).
- [ ] Verify shipped `tests/memory/test_no_extraction.py` / `test_no_live_path_import.py` actively cover the new `retrieval.py` (they glob `memory/*.py`).
- [ ] Framework install: none.

## Security Domain

> `security_enforcement` not set to false → included. Local-only retrieval over `memory.db`; no auth, no sessions, no web tier. The headline threat is **retrieval poisoning**, mitigated **citably-by-construction**.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — local single-user. |
| V3 Session Management | no | "session" = DJ-set, not a web session. |
| V4 Access Control | no | Single-user per-install. |
| V5 Input Validation | **yes** | The retrieved `signature` is RAW past-session text injected into a live prompt — treated as untrusted (it could contain an injected `[recall:…]` lookalike). Mitigation: the past-tense fence + the linter's whole-turn strip mean the LLM can only *cite* registered record_ids; a fabricated cite strips. `record_id` is `f"{session_id}:{seq}"`; `session_id` was path-traversal-validated on write (`store.py:302`). |
| V6 Cryptography | no | No crypto; the proxy holds the API key (`LibraryEmbedder` cannot read a raw key). |
| V12 File / Resource | **yes** | Reads confined to `memory.db` (under `app_data_dir()`); writes nothing to disk. Never touches the off-limits Hermes/LM-Studio privacy paths. |

### Known Threat Patterns for {live-reaction-path memory retrieval}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| **Retrieval poisoning** (an irrelevant/fabricated past moment injected → the AI references something that didn't happen) — THE headline threat | Spoofing (fabricated "memory") | **Four structural guards, none a prompt plea:** (1) similarity floor 0.7 → below-floor injects nothing; (2) PAST-tense "FROM A PAST SESSION" fence → never read as live; (3) current-session exclusion → can't remember itself; (4) **citable-by-construction** — `recall` source + the existing CitationLinter strips the whole turn on a fabricated `[recall:<id>]` (`citation_linter.py:212`). |
| Silent regex-whitelist gap | Tampering (invariant break) | `recall` added to the `_SOURCE_ALT` alternation, not just `EVIDENCE_SOURCES` — else `parse_citations` never sees `[recall:…]` and a fabricated one rides un-stripped. Pinned by the 4 lockstep tests + a RED fabricated-recall-strips test. |
| Injected text in a retrieved `signature` (prompt-injection via stored past reaction) | Tampering | The fence subordinates recall to live audio; the LLM is instructed PAST-tense; and any citation it emits must resolve to a registered record_id or the turn strips. The signature is raw text (no extraction), so it carries no executable instruction the linter trusts. |
| TTFT regression / live-path stall | DoS (UX) | Off-loop `run_in_executor` + hard deadline (`wait_for` 0.5s); miss → inject nothing. Single-in-flight reaction gate untouched. |
| Live-path coupling via the retrieval import | Tampering (invariant break) | No-live-path import gate (`test_no_live_path_import.py` auto-covers `memory/retrieval.py`); the helper reads `ev.state` (read-only) + `MemoryStore`, never writes `MusicState`, never holds `state._lock`, never opens a socket. One-way agent→memory.retrieval arrow. |
| Budget blowout | DoS (cost) | Event-gate (no HEARTBEAT) + one FLEX query embed per track-aware event + corpus pre-embedded (no re-embed). Same order as the shipping `Grounding` embed. |

## Project Constraints (from CLAUDE.md / memory)

- **Gemini-only.** Query embed = `gemini-embedding-2` via `resolve("embedding")` inside `LibraryEmbedder`; no CLAP/MERT/torch (locked). No audio embedding in v1 (text-signature retrieval only).
- **No managed memory frameworks.** Reuses the Phase-63 DIY store + the Phase-59 DIY citation machine.
- **No-LLM-extraction.** Retrieval reads RAW stored signatures; the only model call is `embed_query`. The no-extraction CI gate auto-covers `memory/retrieval.py`.
- **Four cardinal invariants preserved by construction.** Single-writer (no `MusicState` write), one-socket (no new port), trust-the-audio (recall subordinate/past-tense/floored), citation-grounding (`recall` source + existing linter).
- **No scope creep / clean utility.** One service + one gated block + 4 vocabulary edits + tests. No generic RAG framework. No copilot-move surfacing (Phase 66). No time-decay blend by default.
- **Strict per-file staging.** Commit the 4 schema-mirror edits, `retrieval.py`, the `coach.py` block, the agent wiring, and each test file as separate scoped commits.
- **GSD workflow enforcement.** Phase work under `.planning/phases/65-memory-retrieval-seam/`.
- **Frontend skill: N/A.** Phase 65 is backend prompt/linter/retrieval — no UI, no HTML/CSS/JS. The `frontend-enforcement` skill does not apply. The recall *chip* is Phase 66.

## Sources

### Primary (HIGH confidence — read from live source 2026-05-22)
- `src/vibemix/coach/citation_linter.py` (`check` `:94`, `_validate_atom` `:175`, `_TIME_KEYED_SOURCES` `:52`, existence-only branch `:212`, `EVIDENCE_SOURCES` import `:40`) — the zero-new-linter-code proof
- `src/vibemix/state/evidence_registry.py` (`EVIDENCE_SOURCES` `:103`, SCHEMA-MIRROR contract `:100-102`, `_SOURCE_ALT`/`_INNER_ATOM`/`EVIDENCE_CITATION_RE` `:117-135`, `write` `:200`, `register_library` `:234`, `snapshot` `:283`, `parse_citations` `:452`) — the source vocabulary + the 4 lockstep sites
- `src/vibemix/state/coach.py` (`evidence_line` `:53`, the `decks[…]` gate `:96-109`, the `registry_snapshot` default-None gate `:156`, `_evidence_line_compact` `:166`, Phase 60 PAST-tense `TRANSITION_OPPORTUNITY` `:291-316`, `build_prompt` `:320,351`, `ACK_ELIGIBLE_EVENTS` `:44`) — the gate template + threading
- `src/vibemix/memory/store.py` (`query_topk` `:312`, `exclude_session` filter `:329-337`, `Record` `:147`, `_validate_session_id` `:302`) — the read seam
- `src/vibemix/library/embed.py` (`embed_query` `:362-369` — NO content-hash cache) — the live query embed
- `src/vibemix/library/grounding.py` (`Grounding` `:169`, `on_event` `:188`, `get_latest_citation` `:211`, `clear` `:216`, `CITATION_THRESHOLD = 0.7` `:39`) — the architectural precedent + the cosine-floor value
- `src/vibemix/agent/dj_cohost.py` (`build_prompt` call `:538`, `snapshot` `:523`, linter `check` `:1034`, strip path `:1112`, `_build_citation_strip` `:146`, grounding-via-kwargs comment) — the reaction-path wiring
- `src/vibemix/prompts/matrix.py` (`CITATION_GRAMMAR_BLOCK` `:101-138`, `[key:` form `:117`) — the grammar lockstep site
- `src/vibemix/state/event.py` (7 canonical types + KEY_CLASH/TRANSITION_OPPORTUNITY, `EVENT_PRIORITY` `:32-52`) — the event-gate set
- `src/vibemix/coach/constants.py` (`LIVE_TOLERANCE_S` `:15` — NOT the recall floor) — disambiguates the threshold
- `src/vibemix/__main__.py` (`:921-942` grounding wiring, "threshold=0.7" `:939`, "agent reads grounding via kwargs" `:924`) — the flag/kwarg pattern
- `src/vibemix/memory/ingest.py` (`_SOURCE_ALT` copy `:79` — recall MUST NOT be added here) — the ingest-vs-retrieval source asymmetry
- `tests/state/test_coach.py:47` (the silent-state byte-identical golden), `tests/state/test_evidence_registry.py:210` (the 8→9 source lockstep), `tests/prompts/test_matrix.py:396` (the 8→9 grammar lockstep) — the tests that gate this phase
- `64-RESEARCH.md` (the `coach_line` signature template + `record_id = f"{session_id}:{seq}"` shape) — what is retrieved
- `63-03-SUMMARY.md` (the `exclude_session` read seam shipped + reserved for Phase 65) — the read-seam provenance

### Secondary (HIGH — milestone research, corroborated by source)
- `.planning/research/{SUMMARY,ARCHITECTURE,PITFALLS}.md` (the reuse thesis; STORE→INGEST→RETRIEVE→COPILOT spine; retrieval-poisoning as the headline landmine)
- `.planning/REQUIREMENTS.md` (RECALL-01..04), `.planning/ROADMAP.md` (Phase 65 + the cosine-vs-time flag + the Kaan-ear veto), `65-CONTEXT.md` (locked decisions)

## Metadata

**Confidence breakdown:**
- RECALL-01 (zero new linter code): HIGH — traced `key`→registry→prompt→strip in source; the existence-only branch is byte-identical for any new source. The 4 schema-mirror edits are confirmed against the SCHEMA-MIRROR contract + the lockstep tests.
- RECALL-02 (gated block + byte-identical cold): HIGH — the `decks[…]` gate + the `registry_snapshot=None` default-gate are both shipped, proven byte-identical patterns; the silent golden is exact.
- RECALL-03 (anti-poisoning trio): HIGH — floor (`cosine_topk.score`), fence (Phase 60 precedent), exclusion (`store.py:329` shipped + reserved).
- RECALL-04 (off-path / budget / invariants / veto): HIGH — `Grounding` is the exact event-gated off-path enrichment-service analog; the deadline + event-gate are the established budget controls.
- Retrieval policy defaults: HIGH for the structural defaults (k=3, 0.7 floor, event-gate, exclusion); the cosine-vs-time blend is DEFERRED to Kaan-ear per CONTEXT (cosine-only recommended conservatively).

**Research date:** 2026-05-22
**Valid until:** ~2026-06-21 (stable — built entirely on shipped in-repo primitives; drifts only if `EVIDENCE_SOURCES`/`CitationLinter`/`query_topk`/`evidence_line` change, all of which are locked-contract surfaces).
