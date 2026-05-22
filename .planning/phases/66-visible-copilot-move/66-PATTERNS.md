# Phase 66: Visible Copilot Move - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 7 (3 source edits + 4 test additions/creations + 1 doc)
**Analogs found:** 7 / 7 (every change has an exact in-repo precedent)

This phase is a thin **wiring + prompt-fragment** layer on top of the Phase 65 retrieval seam. Every load-bearing edit follows a precedent already shipped (`key` chip, Phase 60 prompt fragments, Phase 65 `recall_moments` falsy gate, `_strip_comments_and_docstrings` static gate, Phase 54 HUMAN-UAT shape). The planner should reference the analog excerpts verbatim and only adapt token-level details (verb string, fragment text, forbidden phrases).

## File Classification

| File (Created / Modified) | Role | Data Flow | Closest Analog | Match Quality |
|---------------------------|------|-----------|----------------|---------------|
| `src/vibemix/agent/dj_cohost.py` (MODIFY: allow-list + verb branch + cooldown state/gate/arm) | controller / agent | request-response (per-turn LLM call) | self (`_build_citation_strip:215-243` `key` branch) | exact (one-char + sibling branch) |
| `src/vibemix/state/coach.py` (MODIFY: add `recall_fragment_for_event` helper + `build_prompt` integration) | service (prompt-builder) | transform (Event → prompt string) | self (`evidence_line:220-226` recall falsy gate + `task_for_event:332-381` KEY_CLASH/TRANSITION_OPPORTUNITY fragments) | exact (clone falsy-gate + branch shape) |
| `src/vibemix/prompts/matrix.py` | config (LLM grammar) | NO EDIT | n/a — Phase 65 already added `[recall:<record_id>]` form | n/a (deliberately untouched per research §Recommended Project Structure) |
| `src/vibemix/ui_bus/messages.py` | wire-format | NO EDIT | n/a — `CitationChipPayload` already payload-shape-identical to `key` | n/a |
| `tests/agent/test_citation_strip_emit.py` (MODIFY: +2 tests) | test | unit | self (`test_key_citation_yields_chip_with_registry_timestamp_DECK03` + `test_fabricated_key_citation_yields_no_chip_DECK03` at :164-203) | exact |
| `tests/agent/test_dj_cohost_linter.py` (MODIFY: +2 cooldown tests) | test | integration | self (`test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall:333+`) — stub-recall-service + multi-turn drive | exact |
| `tests/state/test_coach.py` (MODIFY: +3 fragment/byte-identity tests) | test | unit | self (existing `test_evidence_line_audible_no_recall_byte_identical_v5_baseline` style — golden-pin) | exact |
| `tests/repo/test_no_recall_antifeatures.py` (CREATE) | test (static-gate) | batch (file-tree scan) | `tests/memory/test_no_extraction.py` (cloned `_strip_comments_and_docstrings` + positive-control + offenders dict) | exact (verbatim shape) |
| `.planning/phases/66-visible-copilot-move/66-HUMAN-UAT.md` (CREATE) | doc | n/a | `.planning/phases/54-hype-mode-live/54-HUMAN-UAT.md` (front-matter + numbered ear-tests + Summary) | exact |
| `KAAN-ACTION-LEGAL.md` (MODIFY: +§RECALL-EAR entry) | doc | n/a | existing Phase 60 / Phase 65 carry-forward entries in same file | exact |

## Pattern Assignments

### `src/vibemix/agent/dj_cohost.py` — chip allow-list + `recall` verb branch + cooldown wiring

**Analog (verbatim precedent, same file):** `src/vibemix/agent/dj_cohost.py:215-243` (the `key` source allow-list + fixed-verb branch — Phase 59 DECK-03).

**Allow-list edit site** (`_build_citation_strip:215`):

```python
# CURRENT (src/vibemix/agent/dj_cohost.py:212-243)
# Source allow-list — only sources with a clear "DJ action" verb
# yield UI chips. Quiet sources (aud/screen/tend) parse but do
# not surface as user-visible evidence tags.
if source not in ("ev", "mix", "midi", "key"):
    continue
# Registry lookup uses the body verbatim (KEY@t form). Drop the
# chip when the registry has no matching observation — closes
# "invented timestamps" hallucination class.
inner = snapshot.get(source, {})
timestamps = inner.get(body)
if not timestamps:
    continue  # citation parsed but not grounded → no chip
timestamp_s = float(timestamps[0])
# Derive verb from the KEY portion of the body.
if source == "key":
    # Phase 59 (DECK-03): body is ``<deck>:<camelot>`` (e.g. A:8A),
    # not the ``KEY@t`` shape. The chip verb is a fixed,
    # letters-only "key" label (keeps the locked verb format
    # `^[a-z]+( [a-z]+){0,2}$` — camelot codes carry digits).
    verb = "key"
else:
    key, _, _ = body.partition("@")
    verb_tokens = key.lower().split("_")
    verb = " ".join(verb_tokens[:CITATION_VERB_MAX_WORDS])
```

**Phase 66 edit** — append `"recall"` to the allow-list tuple at line 215 AND add an `elif source == "recall":` branch immediately after the existing `if source == "key":` branch (line 230). Body shape is `<session_id>:<seq>` (opaque); fixed letters-only `"recall"` verb mirrors the `key` precedent. The registry write at `dj_cohost.py:771` already lands `("recall", record_id, t_session)` BEFORE the snapshot so `inner.get(body)` will resolve to `(t_session,)` for grounded survivors and `None` for fabricated ids (which then `continue` and yield no chip — the same anti-hallucination shape `key` uses).

**Cooldown state + gate + arm** — analog: existing `_invoke_counter`/`_ai_text_history`/`_ttft_meter` per-agent state on `DJCoHostAgent`:

```python
# ANALOG: agent state in dj_cohost.py:388-432 (per-instance scalars)
self._registry: EvidenceRegistry | None = evidence_registry
self._cache: GeminiContextCache | None = cache
self._ttft_meter: TTFTMeter | None = ttft_meter
self._llm_to_tts_meter: LLMToTTSDeltaMeter = LLMToTTSDeltaMeter()
# ... self._invoke_counter is bumped in llm_node per-turn (line 842)
```

**Phase 66** adds a single `float` field (`self._last_recall_callback_at: float = 0.0`) — the same idiom as `_invoke_counter` (one extra attribute, no new class). The cooldown CONSTANT lives at module scope mirroring `INVOKE_AUDIO_SECONDS` / `DIET_AUDIO_SECONDS` / `MIC_AUDIO_PART_RECENCY_S` shape (one-line knob).

**Cooldown gate site** — INSIDE the existing `try:` at line 676, AFTER `recall_moments = self._recall.get_latest()` at line 715 and BEFORE the registry write loop at line 754:

```python
# Existing context (dj_cohost.py:686-754, abridged):
if self._recall_enabled and self._recall is not None:
    if self._registry is not None:
        try:
            self._registry.clear_source("recall")   # iter-3 BLOCKER fix
        except Exception as _e:
            ...
    try:
        recall_moments = self._recall.get_latest()
    except Exception as _e:
        recall_moments = []
        try:
            self._recall.clear(bump_generation=False)
        except Exception:
            pass
    if self._registry is None:
        recall_moments = []
    # >>> PHASE 66 INSERT POINT <<<
    # if recall_moments and cooldown active: recall_moments = []
    if recall_moments and self._registry is not None:
        # existing strict-subset registration loop at :754-778
        ...
```

**Cooldown arm site** — research §Pitfall 2 mandates arming AFTER emit (not at dispatch). The emit path is `dj_cohost.py:1497-1514` where `_build_citation_strip(...)` is called for the `SessionCohostReaction`. The agent already calls `parse_citations(emitted_text)` via `from vibemix.state import ... parse_citations` (line 70). After the strip is built, scan it for `event_id.startswith("recall:")` (or equivalently `source == "recall"` from a re-parse) and arm `self._last_recall_callback_at = time.time()`.

**Error-handling pattern (Phase 66 inherits, does not change):** every `try/except Exception as _e: print(f"[<tag> err] {_e}", file=sys.stderr)` block follows the project idiom — failures in the recall path NEVER perturb the reaction turn (best-effort wrapper). Phase 66's cooldown gate is a pure `if/else` on already-validated state (no new exceptions surfaced).

**Call-site reference for `_build_citation_strip`:** `dj_cohost.py:1497-1514` (the only production call; one test-only call exists). The Phase 66 chip surfaces through this call unchanged.

---

### `src/vibemix/state/coach.py` — `recall_fragment_for_event` helper + `build_prompt` integration

**Analog 1 (falsy-gate / cold-path byte-identity):** `src/vibemix/state/coach.py:220-226` — the existing Phase 65 recall block in `evidence_line`:

```python
# Phase 65 byte-identity gate (state/coach.py:220-226)
if recall_moments:
    parts = [
        f"[recall:{m.record_id}] {m.signature}" for m in recall_moments
    ]
    e.append(
        "FROM A PAST SESSION (not happening now): " + " || ".join(parts)
    )
```

The Phase 66 helper MUST clone this falsy-gate shape so a cold-memory turn (no survivors) returns `""` and the prompt is byte-identical to v5.0. Any new test asserting `task_for_event(..., recall_moments=None) != task_for_event(..., recall_moments=[])` is the regression bug — both must produce identical output.

**Analog 2 (prompt-fragment shape — cited / narrate-only / past-tense):** `src/vibemix/state/coach.py:323-381` — Phase 60 `KEY_CLASH` + `TRANSITION_OPPORTUNITY` branches. These are the gold-standard precedent for "cited, system-grounded, narrate-only, do NOT invent" prompt fragments:

```python
# ANALOG: TRANSITION_OPPORTUNITY at state/coach.py:363-381 (Phase 60 HARMONIC-04)
# Cited, PAST-TENSE only, the verdict is the system's (not the LLM's), the
# system gives the cite, the LLM does NOT invent it. This is the shape the
# Phase 66 transition-shape + vocabulary fragments inherit verbatim.
if t == "TRANSITION_OPPORTUNITY":
    a_side = ev.extra.get("a_side", "A")
    a_cam = ev.extra.get("a_camelot", "?")
    b_side = ev.extra.get("b_side", "B")
    b_cam = ev.extra.get("b_camelot", "?")
    clash = ev.extra.get("clash")
    verdict = (
        "harmonically those keys were clashing"
        if clash
        else "harmonically the keys sat fine together"
    )
    return (
        f"You just blended deck {a_side} ({a_cam}) into deck {b_side} "
        f"({b_cam}) — {verdict}. Give Kaan the PAST-TENSE read on how that "
        f"blend sat harmonically — nothing else, no present-tense advice, "
        f"the moment's already gone. Cite both keys: [key:{a_side}:{a_cam}] "
        f"and [key:{b_side}:{b_cam}]. Do NOT invent a key. If there's "
        f"nothing worth saying, output a single space to stay silent."
    )
```

**Phase 66 fragment templates** — the research file already supplies the exact strings (`TRANSITION_SHAPE_RECALL_FRAGMENT_TPL` + `VOCABULARY_RECALL_FRAGMENT_TPL`); they share the Phase 60 shape:
- Past-tense framing ("compare what you heard NOW vs. what's in the past signature")
- The system gives the cite (`[recall:{record_id}]` — registry-validated, fabricated id strips the whole turn)
- LLM does NOT invent (explicit "do NOT invent a past moment, paraphrase the past signature, or describe it as live")
- Anti-feature rules baked in (no "tendency", no "next track")
- Single citation cap baked in ("cite [recall:{record_id}] EXACTLY ONCE")

**Build_prompt integration point** (`state/coach.py:423-429`):

```python
# CURRENT (state/coach.py:423-429)
evidence = AICoach.evidence_line(
    ev.state,
    registry_snapshot=registry_snapshot,
    recall_moments=recall_moments,
)
task = AICoach.task_for_event(ev)
return f"[{evidence} | event={ev.type}] {task}"
```

**Phase 66 edit** — insert `recall_frag = recall_fragment_for_event(ev, recall_moments)` and concatenate it onto the existing return: `f"[{evidence} | event={ev.type}] {task}{recall_frag}"`. The `recall_frag` returns `""` on cold path (preserves byte-identity) and a leading-space-prefixed string on hot path.

**TRACK_CHANGE overlap resolution** (research §Pitfall 5 + §Open Question 1): inside `recall_fragment_for_event`, transition-shape WINS on the TRACK_CHANGE+vocabulary overlap. The branch order in the helper is:
1. `if ev.type in ("TRACK_CHANGE", "MIX_MOVE", "LAYER_ARRIVAL"):` → transition fragment
2. `elif ev.type == "PHASE":` → vocabulary fragment
3. `else:` → `""`

**Diet path** — `build_prompt`'s diet branch at `state/coach.py:415-422` returns BEFORE the recall path; the existing `_bp_kwargs` logic at `dj_cohost.py:827` already withholds `recall_moments` from diet calls. Phase 66 does NOT touch the diet branch.

---

### `src/vibemix/prompts/matrix.py` — NO EDIT

**Why no edit:** Phase 65 (site 3) already added the `[recall:<record_id>]` form to `CITATION_GRAMMAR_BLOCK` at `prompts/matrix.py:118`. The grammar is in the system instruction; Gemini already knows the syntax. Phase 66's fragments INVITE use of that grammar — they do not add new grammar. (Research §Recommended Project Structure makes this explicit.)

**Static-gate impact:** the new `tests/repo/test_no_recall_antifeatures.py` scans `prompts/matrix.py` for forbidden phrases. The file is unchanged this phase, but the gate runs against it every commit. (Mirror the `tests/memory/test_no_extraction.py` approach — read-only over existing files.)

---

### `src/vibemix/ui_bus/messages.py` — NO EDIT

**Why no edit:** `SessionCohostReaction.make()` at `ui_bus/messages.py:1388-1417` accepts `citation_strip: list[dict]` and converts to `tuple[CitationChipPayload, ...]`. Each chip is `{event_id, verb, timestamp_s}` (the exact shape `_build_citation_strip` produces). A new `recall`-source chip flows through with zero wire changes — it is **payload-shape-identical** to a `key` chip. The frontend renderer receives the chip and renders it per the existing template; visual differentiation is a v6.1+ touch (research §Open Question 4).

---

### `tests/agent/test_citation_strip_emit.py` — ADD 2 tests

**Analog:** `test_key_citation_yields_chip_with_registry_timestamp_DECK03` + `test_fabricated_key_citation_yields_no_chip_DECK03` at `tests/agent/test_citation_strip_emit.py:164-203`. Phase 66's recall-chip tests mirror this shape verbatim.

**Analog excerpt** (lines 164-203):

```python
def test_key_citation_yields_chip_with_registry_timestamp_DECK03() -> None:
    """A grounded `[key:A:8A]` citation yields a chip.

    Anti-hallucination contract: the chip ``timestamp_s`` is sourced from the
    registry observation, NOT parsed from the citation body (the body has no
    @t). The verb is the fixed letters-only "key" label.
    """
    reg = EvidenceRegistry()
    # The deck poller registers the EXACT body `A:8A` at a session-relative time.
    reg.write("key", "A:8A", 128.5)

    strip = _build_citation_strip(
        reaction_text="locked in harmonically [key:A:8A], ride it",
        registry=reg,
    )

    assert len(strip) == 1
    assert strip[0]["event_id"] == "key:A:8A"
    assert strip[0]["timestamp_s"] == pytest.approx(128.5, abs=0.01)
    assert strip[0]["verb"] == "key"


def test_fabricated_key_citation_yields_no_chip_DECK03() -> None:
    reg = EvidenceRegistry()
    reg.write("key", "A:8A", 60.0)
    strip = _build_citation_strip(
        reaction_text="big clash [key:A:12B] watch out",
        registry=reg,
    )
    assert strip == []
```

**Phase 66 tests (clone shape, swap source token):**
- `test_recall_citation_yields_chip_with_registry_timestamp_COPILOT01` — register `("recall", "20260520-2200:7", 128.5)`, drive `_build_citation_strip(reaction_text="great recall, [recall:20260520-2200:7]", ...)`, assert `event_id == "recall:20260520-2200:7"`, `verb == "recall"`, `timestamp_s == pytest.approx(128.5)`.
- `test_fabricated_recall_yields_no_chip_COPILOT01` — register one body, cite a different one, assert `strip == []`.

**Verb-format regression guard** — `test_verb_format_is_two_to_three_lowercase_words` at lines 211-231 already pins `^[a-z]+( [a-z]+){0,2}$`. `"recall"` matches (single lowercase word) — adding it does NOT break this gate; verify by running the existing test after the source change.

---

### `tests/agent/test_dj_cohost_linter.py` — ADD 2 cooldown tests

**Analog:** `test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall` at `tests/agent/test_dj_cohost_linter.py:333+`. This is the cross-turn integration shape Phase 66's cooldown tests clone.

**Analog excerpt** (lines 367-410, stub recall service pattern):

```python
# ANALOG: stub recall service from test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall
class _StubRecord:
    def __init__(self, record_id: str, signature: str) -> None:
        self.record_id = record_id
        self.signature = signature
        self.session_id = "20260520-2200"
        self.ts = 0.0

record_a = _StubRecord("20260520-2200:A", "past sig A")
record_b = _StubRecord("20260520-2200:B", "past sig B")

class _StubRecall:
    def __init__(self) -> None:
        self._queue = [[record_a, record_b], []]

    def get_latest(self) -> list:
        return self._queue.pop(0) if self._queue else []

    def clear(self, bump_generation: bool = True) -> None:
        pass

mocker.patch.object(Agent, "__init__", return_value=None)
state = _build_state()
recorder = _FakeRecorder(tmp_path)
genai_client = mocker.MagicMock()
linter = CitationLinter()
tracker = StrippedRateTracker()
playback = mocker.MagicMock()
registry = EvidenceRegistry()
registry.write("ev", "KICK_SWAP", 45.2)

stub_recall = _StubRecall()
agent = DJCoHostAgent(
    genai_client=genai_client,
    ...
    evidence_registry=registry,
    recall=stub_recall,
    recall_enabled=True,
)
```

**Phase 66 tests (clone shape):**
- `test_cooldown_suppresses_back_to_back_recalls` — two `TRACK_CHANGE` events fired within 120s; first emits a `[recall:<id>]` and arms the cooldown; second has non-empty survivors but cooldown is active → assert the prompt body for turn 2 contains NO recall fragment AND no `[recall:<id>]` chip surfaces. Mock `time.time()` to control the gap.
- `test_max_one_recall_per_turn` — drive a single turn with multiple survivors in `_StubRecall.get_latest()`; assert at most ONE `[recall:<id>]` token appears in the built prompt (the fragment template instructs "cite EXACTLY ONCE"; the structural property is the template + registry strict-subset).

---

### `tests/state/test_coach.py` — ADD 3 tests

**Analog:** existing golden-pin tests in `tests/state/test_coach.py` (the v5.0 byte-identity invariant tests around `evidence_line` recall block — referenced in research §Pitfall 1 as `test_evidence_line_audible_no_recall_byte_identical_v5_baseline`).

**Phase 66 tests:**
- `test_transition_recall_fragment_appears` — drive `build_prompt` with `ev=TRACK_CHANGE` / `MIX_MOVE` / `LAYER_ARRIVAL` and non-empty `recall_moments`; assert the result string contains `"FROM A PAST SESSION"` (from `evidence_line`) AND the transition-shape fragment marker (e.g., assert presence of `"past moment from a prior session"` OR a fragment-unique substring like `"in the live audio"`).
- `test_vocabulary_recall_fragment_appears` — drive with `ev=PHASE` and non-empty survivors; assert the vocabulary fragment marker (e.g., `"echo your own past words"`).
- `test_task_for_event_byte_identical_v5_baseline_no_recall` — drive `build_prompt(..., recall_moments=None)` vs `build_prompt(..., recall_moments=[])` vs the v5.0 baseline (cold path); assert all three are byte-identical. THIS IS THE LOAD-BEARING REGRESSION TEST (research §Pitfall 1).
- `test_only_strongest_survivor_record_id_in_fragment` — drive with 3 survivors sorted descending by cosine; assert the fragment's `{record_id}` interpolation is `recall_moments[0].record_id` only (not the other two). The other two STILL appear in the `evidence_line` PAST-tense block — assert that too.
- `test_transition_wins_track_change_overlap` (research §Pitfall 5 resolution): drive with `ev=TRACK_CHANGE` + non-empty survivors; assert the transition fragment is appended (NOT the vocabulary fragment) — verify by checking for a unique substring of each template.

---

### `tests/repo/test_no_recall_antifeatures.py` — CREATE

**Analog:** `tests/memory/test_no_extraction.py` (entire file — the tokenize-stripped grep gate). Phase 66 clones the file structure verbatim, swaps the target file list + forbidden phrase list, keeps the positive-control test.

**Analog excerpt — `_strip_comments_and_docstrings` template:**

```python
# ANALOG: tests/memory/test_no_extraction.py:50-76
def _strip_comments_and_docstrings(src_text: str) -> str:
    """Tokenize-based stripping: removes COMMENT and STRING tokens so prose
    that *documents* the ban (in a comment or docstring) is invisible to the
    scan, while a real NAME/OP token sequence survives. STRING tokens are
    replaced with an empty-string literal so token POSITIONS keep
    surrounding-code adjacency.
    """
    try:
        kept: list[tokenize.TokenInfo] = []
        for tok in tokenize.generate_tokens(io.StringIO(src_text).readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                if tok.type == tokenize.STRING:
                    kept.append(tok._replace(string='""'))
                continue
            kept.append(tok)
        return tokenize.untokenize(kept)
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return "\n".join(
            ln for ln in src_text.splitlines() if not ln.lstrip().startswith("#")
        )
```

**Analog excerpt — positive control:**

```python
# ANALOG: tests/memory/test_no_extraction.py:85-109
def test_no_extraction_detector_catches_a_generation_surface() -> None:
    """Positive control — the stripper+scan WOULD flag a generation call."""
    offending = (
        '"""Docstring mentioning generate_content to document the ban."""\n'
        "resp = client.models.generate_content(model=m, contents=c)\n"
    )
    stripped = _strip_comments_and_docstrings(offending)
    hits = [pat for pat in FORBIDDEN if pat in stripped]
    assert "generate_content" in hits, ...

    doc_only = '"""We never call generate_content here — embed_content only."""\n' "x = 1\n"
    doc_stripped = _strip_comments_and_docstrings(doc_only)
    assert "generate_content" not in doc_stripped, ...
```

**Phase 66 file (Pattern 4 from research §Code Examples — already supplies the full text):**

```python
FORBIDDEN_RECALL_PHRASES: tuple[str, ...] = (
    "you tend to",
    "you usually",
    "you always",
    "your tendency",
    "your tendencies",
    "based on your past",
    "next track",
    "you should play",
    "you should try",
    "i recommend",
    "my recommendation",
)
TARGET_FILES = (
    "src/vibemix/state/coach.py",
    "src/vibemix/prompts/matrix.py",
)
```

**Lowercasing** — the Phase 66 gate `.lower()`s the stripped source before substring-matching (the memory gate does not, because its forbidden tokens are case-sensitive python identifiers). This is the ONE legitimate divergence from the memory-gate template — document it in the new file's docstring.

**Positive control** (mandatory — research §Pitfall 6): assert that a synthetic source containing `"you tend to drop the bass"` IS flagged after stripping; the same phrase in a docstring is NOT.

---

### `.planning/phases/66-visible-copilot-move/66-HUMAN-UAT.md` — CREATE

**Analog:** `.planning/phases/54-hype-mode-live/54-HUMAN-UAT.md` (front-matter YAML + numbered ear-tests + Summary section). The Phase 66 file lands the per-callback ear-test items locked in CONTEXT.md Area 4 Q2.

**Analog excerpt:**

```markdown
---
status: partial
phase: 54-hype-mode-live
source: [54-VERIFICATION.md]
started: 2026-05-21
updated: 2026-05-21
---

## Current Test

[awaiting human testing — Kaan-action on the live/external clock]

## Tests

### 1. Live ≥2-genre hype drive on Kaan's Mac (SC2 + SC4)
expected: ...
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0
```

**Phase 66 ear-test scaffold** (CONTEXT.md Area 4 Q2 names this surface explicitly):
- Test 1: live transition-shape callback grounds on a real past move (not scripted, not nagging, not hallucinated)
- Test 2: live vocabulary callback echoes Kaan's prior phrasing (quote-shape, not Gemini-paraphrased — research §Pitfall 4)
- Test 3: cooldown verified by ear (no more than ~1 recall callback per ~2 minutes; never two in succession)
- Test 4 (optional): anti-feature presence by ear (no "you tend to" / "next track" phrases in the audio)

---

### `KAAN-ACTION-LEGAL.md` — APPEND §RECALL-EAR entry

**Analog:** existing Phase 60 / Phase 65 carry-forward entries in the same file (the precedent CONTEXT.md Area 4 explicitly names — "same pattern as Phase 60 harmonic veto, which Phase 65 already inherits"). The new §RECALL-EAR entry documents the `VIBEMIX_RECALL_ENABLED=1` flip-after-ear-pass discharge.

(The exact KAAN-ACTION-LEGAL.md path may be at the project root or under `.planning/` — the planner should locate the file via the existing Phase 65 entry and append in-file.)

---

## Shared Patterns

### Pattern A: Falsy-gate for cold-path byte-identity

**Source:** `src/vibemix/state/coach.py:220` (the existing Phase 65 `if recall_moments:` gate).
**Apply to:** the new `recall_fragment_for_event` helper (must return `""` on `None` / `[]` input) AND the new cooldown gate (must set `recall_moments = []` so downstream falsy-gates trip).

```python
# Source: state/coach.py:220
if recall_moments:
    parts = [
        f"[recall:{m.record_id}] {m.signature}" for m in recall_moments
    ]
    e.append("FROM A PAST SESSION (not happening now): " + " || ".join(parts))
```

Cold path = `recall_moments` is None or `[]` → block is skipped → output byte-identical to v5.0 baseline. THIS IS LOAD-BEARING — every existing `tests/state/test_coach.py` golden test depends on it.

### Pattern B: Best-effort try/except wrapper (recall path never breaks a turn)

**Source:** `src/vibemix/agent/dj_cohost.py:706-737` (Phase 65 `clear_source` + `get_latest` blocks).
**Apply to:** the new cooldown arm site at the emit path. The arm is a pure timestamp write — but the parse-citations scan over `emitted_text` should be wrapped in `try/except Exception as _e: print(f"[recall cooldown arm err] {_e}", file=sys.stderr)` to match the project idiom.

```python
# Source: dj_cohost.py:706-713
if self._registry is not None:
    try:
        self._registry.clear_source("recall")
    except Exception as _e:
        print(f"[recall registry clear err] {_e}", file=sys.stderr)
```

### Pattern C: Module-scope tuning constant (cooldown)

**Source:** `src/vibemix/agent/dj_cohost.py:83-110` (existing module-scope constants — `SILENCE_TOKEN`, `SCREEN_SKIP_EVENTS`, `DIET_AUDIO_SECONDS`, `ENV_SKILL_LEVEL`, `DEFAULT_*`).
**Apply to:** the new `RECALL_CALLBACK_COOLDOWN_S: float = 120.0` constant. One-line knob, named, module scope — Kaan can re-tune in a single edit on his real corpus.

### Pattern D: Static-gate target_files + forbidden tuple + offenders dict

**Source:** `tests/memory/test_no_extraction.py:42-47, 79-133`.
**Apply to:** `tests/repo/test_no_recall_antifeatures.py` (entire file). The shape is:
1. `FORBIDDEN: tuple[str, ...] = (...)` at module scope
2. A `_target_files()` helper (or hardcoded list)
3. Stripper function (cloned verbatim)
4. `test_no_<name>_detector_catches_a_<surface>()` positive control
5. `test_<name>_<invariant>()` main scan

```python
# Source: tests/memory/test_no_extraction.py:112-133
def test_memory_calls_only_embed_content() -> None:
    offenders: dict[str, list[str]] = {}
    for py in _memory_py_files():
        stripped = _strip_comments_and_docstrings(
            py.read_text(encoding="utf-8", errors="replace")
        )
        hits = [pat for pat in FORBIDDEN if pat in stripped]
        if hits:
            offenders[str(py.relative_to(REPO))] = hits
    assert not offenders, (
        "vibemix.memory references a generation surface ..."
    )
```

### Pattern E: Verb-format pin (locked grammar contract)

**Source:** `tests/agent/test_citation_strip_emit.py:211-231` (`test_verb_format_is_two_to_three_lowercase_words`).
**Apply to:** the chip allow-list edit must not break this gate. `"recall"` is a single lowercase word → trivially matches `^[a-z]+( [a-z]+){0,2}$`. The existing test acts as the regression guard; no new test needed, but the planner MUST verify it stays green after the allow-list edit.

### Pattern F: Per-agent timestamp state (cooldown bookkeeping)

**Source:** existing per-agent scalars in `DJCoHostAgent.__init__` (`_invoke_counter`, `_recall_task`, `_pending_event` — `dj_cohost.py:388-460`).
**Apply to:** the new `self._last_recall_callback_at: float = 0.0` field. Co-locate with `self._invoke_counter` / `self._ai_text_history` initializations. NO new class, NO inheritance, NO RecallCooldown helper class (research §Don't Hand-Roll).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | Every Phase 66 surface has an exact in-repo precedent. The chip allow-list cloning the `key` branch, the prompt fragment cloning Phase 60 KEY_CLASH/TRANSITION_OPPORTUNITY, the static gate cloning `tests/memory/test_no_extraction.py`, the HUMAN-UAT cloning Phase 54. This phase is intentionally a thin wiring layer — Phase 65 opened every load-bearing seam. |

## Metadata

**Analog search scope:**
- `src/vibemix/agent/dj_cohost.py` (the Phase 65 `recall_moments` integration + the `key` chip precedent)
- `src/vibemix/state/coach.py` (the `evidence_line` recall block + the Phase 60 prompt-fragment branches)
- `src/vibemix/state/evidence_registry.py` (the `recall` schema entry — read-only consumer site)
- `src/vibemix/memory/retrieval.py` (the read-only `MemoryRecall` consumer)
- `src/vibemix/ui_bus/messages.py` (the wire format — read-only)
- `tests/memory/test_no_extraction.py` (the static-gate template — verbatim)
- `tests/agent/test_citation_strip_emit.py` (the `key`-chip test precedent at :164-203)
- `tests/agent/test_dj_cohost_linter.py` (the recall-poisoning + cross-turn fabricated-recall tests at :250 and :333)
- `tests/coach/test_citation_linter.py` (existing linter test shape, read-only)
- `.planning/phases/54-hype-mode-live/54-HUMAN-UAT.md` (the HUMAN-UAT shape)

**Files scanned:** 11 source/test files + 1 HUMAN-UAT template + 2 phase planning artifacts (CONTEXT.md, RESEARCH.md).

**Pattern extraction date:** 2026-05-22

**Planner contract:** every Phase 66 PLAN.md action MUST cite the analog file + line range above. No new abstractions; precedent-first.
