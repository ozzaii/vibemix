# Phase 65: Memory Retrieval Seam (ANTI-SLOP RELEASE GATE) - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 8 source files (1 new, 4 schema-mirror edits, 1 prompt edit, 1 agent edit, 1 coach edit) + 5 test files (1 new, 2 updated, 2 new RED)
**Analogs found:** 13 / 13 (every primitive is shipped in-repo and verified file:line against live source)

> **Verification note:** Every analog below was opened and confirmed against live `src/vibemix/` source on 2026-05-22, not from RESEARCH alone. Where the live source diverges from RESEARCH's framing, the divergence is flagged inline (see the `_build_citation_strip` discrepancy under site #4 — it is load-bearing).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/vibemix/memory/retrieval.py` (NEW) | service | request-response (event-gated, off-path) | `src/vibemix/library/grounding.py::Grounding` | **exact** (architectural twin) |
| `src/vibemix/state/coach.py` (EDIT — `recall[…]` block) | prompt-builder | transform | `coach.py::evidence_line` `decks[…]` gate (`:96-109`) | **exact** (verbatim copy, same file) |
| `src/vibemix/state/evidence_registry.py` (EDIT — site 1+2) | config (source vocabulary) | data-driven | the `key` source addition (Phase 59) | **exact** (most-recent precedent) |
| `src/vibemix/prompts/matrix.py` (EDIT — site 3) | config (grammar) | data-driven | `[key:<deck>:<camelot>]` form (`:117`) | **exact** |
| `src/vibemix/agent/dj_cohost.py` (EDIT — site 4 + wiring) | controller | request-response | `register_library` + grounding dispatch + `_build_citation_strip` | role-match (see flag) |
| `tests/memory/test_retrieval.py` (NEW) | test | — | `tests/memory/test_ingest.py` | **exact** (sibling shape) |
| `tests/state/test_coach.py` (EDIT — 2 new + golden) | test | — | `test_evidence_line_silent_state_full_format` (`:47`) | **exact** (same file) |
| `tests/state/test_evidence_registry.py` (UPDATE 8→9) | test | — | `test_evidence_11_sources_constant_locked_GROUND02` (`:210`) | **exact** |
| `tests/prompts/test_matrix.py` (UPDATE 8→9) | test | — | `test_o_citation_grammar_block_contains_eight_source_forms_and_multi_cite` (`:396`) | **exact** |
| `tests/agent/test_dj_cohost_linter.py` (NEW RED) | test | — | existing linter strip tests in same file | role-match |

---

## Pattern Assignments

### `src/vibemix/memory/retrieval.py` (NEW — `MemoryRecall` service, event-gated/off-path/deadline-bounded)

**Analog:** `src/vibemix/library/grounding.py::Grounding` (`grounding.py:169-220`) — the EXACT architectural twin: a stateful, lock-guarded, event-gated enrichment service holding the latest result for the prompt builder to pull, with `on_event` → store → `get_latest` → `clear()`.

**Service-shape pattern to mirror** (`grounding.py:169-220` — VERIFIED):
```python
class Grounding:
    """Stateful grounding service the agent holds. ... Thread-safe (lock-guarded)."""
    def __init__(self, embedder: LibraryEmbedder, store: LibraryStore) -> None:
        self._embedder = embedder
        self._store = store
        self._lock = threading.Lock()
        self._latest: Citation | None = None

    def on_event(self, event_type, audio_bytes, *, event_id=None, mime_type="audio/wav"):
        citation = identify_playing(self._embedder, self._store, audio_bytes, ...)
        if citation is not None and citation.is_cited:
            with self._lock:
                self._latest = citation
        return citation

    def get_latest_citation(self) -> Citation | None:
        with self._lock:
            return self._latest

    def clear(self) -> None:            # called at end of each Gemini turn
        with self._lock:
            self._latest = None
```

**Event-gate constant pattern to mirror** (`grounding.py:39,45-47` — VERIFIED):
```python
CITATION_THRESHOLD = 0.7            # the cosine floor to MIRROR (copy value, do NOT import)
TRACK_AWARE_EVENTS: frozenset[str] = frozenset({"TRACK_CHANGE", "LAYER_ARRIVAL", "MIX_MOVE"})
```
> **Recall's gate diverges deliberately:** `RECALL_EVENT_GATE = frozenset({"TRACK_CHANGE", "PHASE", "LAYER_ARRIVAL"})` — RESEARCH §Open-Q1 ships the canonical track-aware trio for v1 (NOT `MIX_MOVE`, which `Grounding` includes; `MIX_MOVE` is in `ACK_ELIGIBLE_EVENTS` diet path). NEVER HEARTBEAT.

**Read-seam to import** (`memory/store.py:312-340` — VERIFIED, `exclude_session` shipped + reserved):
```python
def query_topk(self, query_embedding: np.ndarray, k: int = 8, *,
               exclude_session: str | None = None) -> list[Record]:
    # exclude_session omits one session's records BEFORE cosine_topk ranking (:329-337)
    # returns list[Record] with .record_id, .session_id, .ts, .kind, .signature, .score (cosine)
```

**`Record` carrier** (`memory/store.py:147-162` — VERIFIED — raw-in/raw-out, `.score` = cosine):
```python
@dataclass
class Record:
    record_id: str       # f"{session_id}:{seq}" (Phase 63/64)
    session_id: str
    ts: float
    kind: str
    signature: str       # verbatim stored text, NEVER LLM-extracted
    score: float = 0.0   # cosine from cosine_topk (only on query results)
```

**Live query embed to import** (`library/embed.py:362-369` — VERIFIED — NO content-hash cache):
```python
def embed_query(self, query: str) -> np.ndarray:
    """Embed a natural-language vibe-search query (text-only path). No content-hash cache here..."""
    vec = self._call_gemini_text(query)
    return l2_normalize(vec)
```

**Recall service skeleton** (from RESEARCH §Code Examples, anchored to the verified `Grounding` shape):
```python
import threading
from vibemix.memory.store import MemoryStore, Record
from vibemix.library.embed import LibraryEmbedder

RECALL_SIMILARITY_FLOOR = 0.7   # mirrors library/grounding.py:39 CITATION_THRESHOLD (COPY, do NOT import)
RECALL_TOP_K = 3
RECALL_DEADLINE_S = 0.5
RECALL_EVENT_GATE = frozenset({"TRACK_CHANGE", "PHASE", "LAYER_ARRIVAL"})

class MemoryRecall:
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

    def clear(self) -> None:
        with self._lock:
            self._latest = []
```

**Constraints (verified-coverable):**
- MUST NOT import the live reaction path at module level (no `MusicState`/coach loop/ws_bus/agent). `tests/memory/test_no_live_path_import.py` `rglob("*.py")` over `memory/` (VERIFIED `:51-54`) auto-covers `retrieval.py`.
- MUST make only the `embed_content`-class call (no generation). `tests/memory/test_no_extraction.py` `rglob("*.py")` over `memory/` (VERIFIED `:82`) auto-covers it.
- Copy `0.7` with a `# mirrors library/grounding.py:39 CITATION_THRESHOLD` comment. Do NOT `from vibemix.library.grounding import CITATION_THRESHOLD` (couples memory→library).

---

### `src/vibemix/state/coach.py` — the gated `recall[…]` block (prompt-builder, transform)

**Analog:** the Phase 59 `decks[…]` gate in the SAME function (`coach.py:96-109`) — VERIFIED. The structural twin of "additive + falsy-gate → byte-identical when empty".

**The `decks[…]` gate to copy verbatim** (`coach.py:96-109` — VERIFIED):
```python
if state.deck_state.decks:                       # ← falsy gate: empty → emit NOTHING
    resolved = {s: d for s, d in state.deck_state.decks.items()
                if d.camelot and d.confidence >= 0.3}
    if resolved:
        parts = [f"{s}={d.title!r} {d.camelot} {d.bpm:.0f}bpm" for s, d in sorted(resolved.items())]
        e.append("decks[" + " | ".join(parts) + "]")
    else:
        e.append("decks=unknown")
```

**The default-None kwarg precedent in the SAME signature** (`coach.py:54-58,156` — VERIFIED):
```python
def evidence_line(state: MusicState, *,
                  registry_snapshot: dict[...] | None = None) -> str:   # :54-58
    ...
    if registry_snapshot:                                               # :156 — falsy gate
        ...append footer...
```
→ Add `recall_moments: list[Record] | None = None` exactly like `registry_snapshot=None`.

**The recall block to append** (RESEARCH §The Gated block — additive, gated identically, PAST-tense fenced):
```python
# Phase 65 — recall[…] block. ADDITIVE + gated (None or [] → emit NOTHING) so the
# silent-state golden at tests/state/test_coach.py:47 stays BYTE-IDENTICAL.
# Mirrors the decks[…] gate. PAST-TENSE fenced (RECALL-03) — never read as live.
if recall_moments:                               # ← None or [] → emit NOTHING
    parts = [f"[recall:{m.record_id}] {m.signature}" for m in recall_moments]
    e.append("FROM A PAST SESSION (not happening now): " + " || ".join(parts))
```

**`build_prompt` threading** (`coach.py:320-353` — VERIFIED): thread `recall_moments=` through `build_prompt(ev, *, registry_snapshot=None, recall_moments=None, diet=False)` → `evidence_line(ev.state, registry_snapshot=snapshot, recall_moments=recall_moments)` at `:351`. The `diet` branch at `:343-350` uses `_evidence_line_compact` (`:166`) which has NO recall block — CORRECT (diet = `ACK_ELIGIBLE_EVENTS` incl. HEARTBEAT, never a retrieval event).

**Golden that MUST stay byte-identical** (`tests/state/test_coach.py:47-53` — VERIFIED EXACT):
```python
out = AICoach.evidence_line(state)   # recall_moments defaults None
assert out == (
    "hearing[silent] | track=unknown | deck=none | set_time=0:00 | recent_moves[8s]: NONE"
)
```

**Past-tense fence precedent** (RESEARCH: Phase 60 `TRANSITION_OPPORTUNITY` "PAST-TENSE only … the moment's already gone" `coach.py:291-316`) — the fence header is structural, not a prompt plea.

---

### `src/vibemix/state/evidence_registry.py` — schema-mirror sites 1 & 2 (config, data-driven)

**Analog:** the `key` source addition (Phase 59) — VERIFIED as the precedent at each site below. The SCHEMA-MIRROR contract is documented in-source at `evidence_registry.py:100-102`.

**Site 1 — `EVIDENCE_SOURCES` frozenset** (`evidence_registry.py:103-105` — VERIFIED, currently 8):
```python
EVIDENCE_SOURCES: frozenset[str] = frozenset(
    {"ev", "aud", "midi", "track", "screen", "mix", "tend", "key"}    # add "recall" → 9
)
```

**Site 2 — `_SOURCE_ALT` regex alternation + EBNF docstring** (`evidence_registry.py:117-128` — VERIFIED):
```python
_SOURCE_ALT = "ev|aud|midi|track|screen|mix|tend|key"   # append "|recall"
_INNER_ATOM = rf"(?:{_SOURCE_ALT}):[^\s,\]]+"            # UNCHANGED — recall:<id> body has no ws/comma/bracket
#   source := 'ev' | ... | 'key'                         # add | 'recall' in the docstring grammar
```
> **THE SILENT POISONING HOLE — flag loudly:** if `recall` is added to `EVIDENCE_SOURCES` (site 1) but NOT to `_SOURCE_ALT` (site 2), `parse_citations` (`:452`) NEVER matches `[recall:…]` → the linter never sees it → a fabricated `[recall:<bogus>]` rides through UN-STRIPPED. This is the exact poisoning the phase exists to prevent, introduced by a half-edit. Sites 1 and 2 MUST land together. (`record_id` is `f"{session_id}:{seq}"` — the inner `:` survives because `parse_citations` splits on the FIRST `:`, exactly like `key:A:8A`.)

**Registration call to mirror** — `register_library` bulk-writes `track` ids via `write("track", id, 0.0)` (`evidence_registry.py:234`); `recall` mirrors this: `registry.write("recall", record.record_id, t_session)` BEFORE the LLM call.

**Tests pinning these sites:**
- `tests/state/test_evidence_registry.py:210` `test_evidence_11_sources_constant_locked_GROUND02` — asserts exact 8-source set (`:218-219`); **UPDATE to 9** (add `"recall"`).
- `tests/state/test_evidence_registry.py:227` `test_evidence_12_registry_grammar_coherence` — auto-iterates `EVIDENCE_SOURCES` asserting each is matchable + writable (`:234`); passes automatically once `recall` is in both sites.

---

### `src/vibemix/prompts/matrix.py` — schema-mirror site 3 (config, grammar)

**Analog:** the `[key:<deck>:<camelot>]` form (`matrix.py:117`) — VERIFIED.

**`CITATION_GRAMMAR_BLOCK` forms list** (`matrix.py:109-117` — VERIFIED, currently 8 forms):
```
Forms (each is a single citation; the linter accepts any of these):
  [ev:<TYPE>@<t>]     ...
  ...
  [key:<deck>:<camelot>]  deck harmonic key, e.g. [key:A:8A]
```
→ Add a 9th form: `[recall:<record_id>]   past-moment reference, e.g. [recall:20260520-2200:7]`.

**Test pinning this:** `tests/prompts/test_matrix.py:396` `test_o_citation_grammar_block_contains_eight_source_forms_and_multi_cite` — **UPDATE 8→9 forms + assert `[recall:` present**.

---

### `src/vibemix/agent/dj_cohost.py` — schema-mirror site 4 + reaction-path wiring (controller)

**Analogs:** `register_library` (registration), the grounding dispatch (`Grounding.on_event` via executor), `_build_citation_strip` (the parse + chip surface).

**Wiring — register survivors before the LLM call** (mirror `register_library`, anchored to `dj_cohost.py:523` snapshot + `:538` build_prompt — per RESEARCH):
```python
recall_moments = self._recall.get_latest() if self._recall is not None else []
for m in recall_moments:
    self._registry.write("recall", m.record_id, ev.state.set_seconds)   # register → linter validates
snapshot = self._registry.snapshot()                                    # same once-per-turn snapshot (:523)
prompt = AICoach.build_prompt(ev, registry_snapshot=snapshot, recall_moments=recall_moments)  # NEW kwarg
```

**Wiring — dispatch off-loop with hard deadline** (mirror `Grounding.on_event` dispatch): pre-dispatch `MemoryRecall.on_event` via `loop.run_in_executor(None, ...)` + `asyncio.wait_for(..., timeout=RECALL_DEADLINE_S)` at the seam that sets `_pending_event` for a track-aware event; `clear()` after each turn. NEVER inline-`await embed_query` in `llm_node` (TTFT regression).

**Site 4 — the citation-strip whitelist** (`dj_cohost.py:146,213` — VERIFIED):
```python
def _build_citation_strip(*, reaction_text: str, registry: EvidenceRegistry) -> list[dict]:
    ...
    for source, body in parse_citations(reaction_text):   # parse is regex-driven (needs site-2 _SOURCE_ALT)
        ...
        if source not in ("ev", "mix", "midi", "key"):     # :213 — the CHIP allow-list
            continue
```
> **⚠️ DISCREPANCY — flag for planner (deviates from RESEARCH's "add recall to the strip whitelist"):** there are TWO distinct concerns in `_build_citation_strip`, and the RESEARCH framing conflates them:
> 1. **Parsing** — `parse_citations` at `:207` is regex-driven off `_SOURCE_ALT` (site 2). Once `recall` joins the alternation, `[recall:…]` is parsed automatically — **no edit here**.
> 2. **The chip allow-list at `:213`** (`ev, mix, midi, key`) is a NARROWER UI-surface gate: only sources with a clear "DJ-action verb" yield visible chips. The docstring (`:179-183`, VERIFIED) explicitly states `aud`/`track`/`screen`/`tend` "parse correctly but do not yield chips — they're either too noisy or carry no obvious DJ-action verb."
>
> **`recall` is existence-only with no DJ-action verb — it parallels `track`/`tend`, NOT `ev`/`key`.** Adding `recall` to the `:213` allow-list would surface a recall *chip* — but the recall chip is **explicitly Phase 66** (CONTEXT/RESEARCH: "NO copilot move surfacing … Phase 66 builds the visible callbacks"). So for v1, `recall` should NOT be added to the `:213` chip allow-list — leaving it out is correct and on-pattern with `track`/`tend`. The linter strip (the anti-poisoning gate) is wholly independent of this chip allow-list; it runs through `CitationLinter.check` (see Shared Patterns) which is data-driven off `EVIDENCE_SOURCES`. **Planner: confirm whether RESEARCH's "site 4 = strip whitelist" means the `:213` chip gate (→ defer to Phase 66) or simply that the parse must reach the linter (→ already covered by site 2). The conservative, Phase-66-respecting reading: site 4 is a NO-OP for v1 chips; the only `dj_cohost.py` changes are the wiring + registration above.** Pin with `tests/agent/test_citation_strip_emit.py`.

---

### `tests/memory/test_retrieval.py` (NEW)

**Analog:** `tests/memory/test_ingest.py` (VERIFIED shape). Same fixture conventions: `MemoryStore(db_path=tmp_path / "memory.db", prefer_sqlite_vec=False)` (`:205`), a `_FakeEmbedder` (`:83`), synthetic 768-dim L2-normalized vectors via `library._cosine.l2_normalize` (`:59`), `add_record` seeding.

**Cases to cover** (RESEARCH §Test Map): `test_heartbeat_never_retrieves` (gate→`[]`, no embed call), `test_below_floor_injects_nothing`, `test_current_session_excluded`, `test_deadline_miss_injects_nothing`, embed-called-once.

### `tests/state/test_coach.py` (EDIT)

**Analog:** `test_evidence_line_silent_state_full_format` (`:47`). Add `test_evidence_line_recall_block_present` (populated path — past-tense fence + `[recall:<id>]` tokens) and `test_evidence_line_recall_empty_no_block` (`[]` → no block). The `:47` golden MUST stay green with the default kwarg.

### `tests/agent/test_dj_cohost_linter.py` (NEW RED — the headline poisoning gate)

**Analog:** existing linter strip tests in the same file. Add `test_fabricated_recall_strips_turn` — a `[recall:<unregistered>]` the registry never wrote strips the WHOLE turn.

---

## Shared Patterns

### Citation grounding (the anti-slop core — ZERO new linter code)
**Source:** `src/vibemix/coach/citation_linter.py::_validate_atom` (`:175-213`) — VERIFIED data-driven.
**Apply to:** the `recall` source (RECALL-01).
```python
_TIME_KEYED_SOURCES: frozenset[str] = frozenset({"ev", "aud", "midi"})   # :52 — recall MUST stay OUT
...
if source in _TIME_KEYED_SOURCES:        # :199 — @t parse; recall falls through (existence-only)
    ...
valid = body in snapshot.get(source, {})  # :212 — existence-only branch; handles ANY new source
```
A `[recall:<id>]` whose `record_id` was never registered → `body not in snapshot["recall"]` → `valid=False` → `LintResult(valid=False)` → whole-turn strip (`dj_cohost.py:1112`). **The linter LOGIC is byte-unchanged.** The entire linter "change" is: add `recall` to `EVIDENCE_SOURCES` (site 1) and KEEP it out of `_TIME_KEYED_SOURCES`. Both are data.

### Off-path event-gated enrichment service
**Source:** `src/vibemix/library/grounding.py::Grounding` (`:169-220`).
**Apply to:** `MemoryRecall` (lock-guarded `_latest`, `on_event`/`get_latest`/`clear`, dispatched off-loop, never writes `MusicState`).

### Falsy-gate → byte-identical-when-empty
**Source:** `coach.py` `decks` (`:96`), `registry_snapshot` (`:156`), `track=` (`:78`).
**Apply to:** the `recall[…]` block (`if recall_moments:`) — None AND `[]` both falsy → zero bytes appended.

### Cosine floor (mirror, do NOT import)
**Source:** `CITATION_THRESHOLD = 0.7` (`grounding.py:39`).
**Apply to:** `RECALL_SIMILARITY_FLOOR = 0.7` copied with a source comment (avoid memory→library coupling).

### SCHEMA-MIRROR contract (the source vocabulary lives in 4 lock-step sites)
**Source:** `evidence_registry.py:100-102` (the contract docstring).
**Apply to:** sites 1–4 above. Missing site 2 (`_SOURCE_ALT`) = silent poisoning hole.

---

## Do-NOT (off-pattern — explicitly excluded)

| Anti-pattern | Why | Source |
|--------------|-----|--------|
| Add `recall` to `memory/ingest.py:79` `_SOURCE_ALT` | INGEST-time extraction of past `ai_text`; a stored past reaction could never have cited `[recall:…]` (recall didn't exist then). Harmless-but-dead + confusing. Leave ingest at 8 sources. | RESEARCH §RECALL-01 NOTE + Pitfall, Assumption A5 |
| Add `recall` to `_TIME_KEYED_SOURCES` | Forces a `@t` parse, breaks existence-only validation. MUST stay out (like `key`/`track`). | `citation_linter.py:52,199` |
| New linter / validator code for `[recall:…]` | The existence-only branch (`:212`) already handles it. ZERO new linter code. | `citation_linter.py:212` |
| New dependency / new socket / new ws port | One-socket invariant; recall rides existing prompt + citation strip. | RESEARCH §Four Cardinal Invariants |
| Import `library.grounding.CITATION_THRESHOLD` | Couples memory→library. Copy the value. | RESEARCH §Alternatives |
| Inline `await embed_query` in `llm_node` | TTFT regression. Pre-dispatch + hard deadline only. | RESEARCH §Pitfall 3 |
| Time-decay blend by default | Relevance heuristic, not a structural guard. Cosine-only + 0.7 floor for v1 (decay = Kaan-ear KAAN-ACTION). | RESEARCH §Retrieval Policy |
| Add `recall` to `_build_citation_strip:213` chip allow-list (v1) | The recall *chip* is Phase 66; recall is verb-less existence-only (parallels `track`/`tend`, which parse but don't chip). See discrepancy flag above. | `dj_cohost.py:179-183,213` |

---

## No Analog Found

None. Every file has a strong in-repo analog — this is a wiring + structural-guard phase, not an algorithm phase. The "anti-slop gate" is enforced by REUSE of shipped primitives.

---

## Metadata

**Analog search scope:** `src/vibemix/{memory,library,state,prompts,agent,coach}/`, `tests/{memory,state,prompts,agent,coach}/`
**Files scanned/opened:** `library/grounding.py`, `state/coach.py`, `memory/store.py`, `library/embed.py`, `state/evidence_registry.py`, `coach/citation_linter.py`, `prompts/matrix.py`, `agent/dj_cohost.py`, `tests/state/test_coach.py`, `tests/memory/test_ingest.py`, `tests/memory/test_no_live_path_import.py`, `tests/memory/test_no_extraction.py` + grep over the test lockstep sites
**Pattern extraction date:** 2026-05-22
