# Phase 66: Visible Copilot Move - Research

**Researched:** 2026-05-22
**Domain:** Coach-prompt fragment surface + citation-chip allow-list (wiring on top of the Phase 65 retrieval seam)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Area 1 — Coach Move Triggers (when each callback fires)**

- **Q1 (transition-shape callback event gate):** TRACK_CHANGE, MIX_MOVE, LAYER_ARRIVAL. The same `RECALL_EVENT_GATE` set Phase 65 uses (TRACK_CHANGE, PHASE, LAYER_ARRIVAL) PLUS MIX_MOVE for transition-specific callbacks. NEVER HEARTBEAT (Phase 65 invariant).
- **Q2 (vocabulary callback event gate):** PHASE, TRACK_CHANGE. Reuses the v5.0 PHASE event gate from `coach_persona` (consistent with the actionable-not-hype discipline).
- **Q3 (rare-and-earned cooldown):** ≥120s between any two recall callbacks, max 1 recall per turn. Mirrors Phase 65 RESEARCH.md cooldown intuition + v5.0 cooldown discipline.
- **Q4 (empty-survivor turn behavior):** No. If `recall_moments == []` after the deadline + floor, the coach prompt sees no `recall[…]` block (Phase 65 byte-identity invariant) — no past-tense ground means no past-tense callback. **Structural guarantee.**

**Area 2 — Anti-Slop / Anti-Feature Guards**

- **Q1:** Phase 65's existing linter gate carries forward. The poisoning test (`test_fabricated_recall_strips_turn` + `test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall`) already covers BL. Phase 66 adds tests that the *coach prompt-engineering* doesn't accidentally produce ungrounded callbacks.
- **Q2 (anti-features prevention):** Static repo-scrub test in `tests/repo/` mirroring Phase 65's `no-live-path`/`no-extraction` gates. Search prompt matrix + coach persona for forbidden patterns:
  - No "tendency" / "you always" / "you usually" (LLM-extracted personality claims)
  - No "next track" / "you should play" (recommendation surface)
  - No new settings-screen entry points
  - No continuous audio embedding (already guarded by Phase 65)
- **Q3 (warm + non-nagging tone):** Reuse v5.0 `coach_persona` discipline + actionable-not-hype tests (Phase 61). Cooldown + cap prevent nagging; persona prevents hype. No new tone-validator needed.
- **Q4 (disclosure surface):** No new surface. The recall chip on `citation_strip` is the disclosure — the user sees the chip when a callback fires.

**Area 3 — Citation Strip Recall Chip (Tier-1 visible surface)**

- **Q1:** Add `"recall"` to the source allow-list in `_build_citation_strip` at `src/vibemix/agent/dj_cohost.py:215`. Currently `("ev", "mix", "midi", "key")`; becomes `("ev", "mix", "midi", "key", "recall")`.
- **Q2:** Fixed verb `"recall"` — single token, letters-only. Mirrors the `key` precedent.
- **Q3:** The current session's reaction timestamp (when the callback fired), NOT the past moment's original timestamp.
- **Q4:** No. The chip is gated on the linter SEEING a `[recall:<id>]` in the reaction. If the coach decides not to use the past moment, no chip.

**Area 4 — Kaan-Ear Release Gate**

- **Q1:** Yes — Phase 66 ships with `VIBEMIX_RECALL_ENABLED=0` (Phase 65 default).
- **Q2:** `KAAN-ACTION-LEGAL.md` gets a v6.0 §RECALL-EAR entry + `66-HUMAN-UAT.md` gets per-callback ear-test items.
- **Q3:** Yes — autonomous-`fully` mode. Engineering passes verification + code-review when gates are green. Kaan-ear is carry-forward.

### Claude's Discretion

- Exact prompt wording for transition-shape + vocabulary callback templates.
- Number of recall examples surfaced in prompt (Phase 65 top-k 2–3 with floor ~0.7 → research recommendation below).
- Whether vocabulary callback needs its own retrieval query vs. reusing transition-shape survivors.
- Chip visual treatment (`frontend-enforcement` skill governs CDJ-Whisper material/typography; UI-SPEC if needed).

### Deferred Ideas (OUT OF SCOPE)

- **Recall-history settings screen** — explicit user-facing surface to inspect/delete past moments.
- **Cross-session "you tend to" summarizer** — explicit LLM-extracted tendency surface. Permanently out of scope per v6.0 anti-features lock.
- **Next-track recommendation** — out of scope per same anti-feature lock.
- **Mascot recall reaction** — could be v6.1+ touch; Phase 62 demoted mascot to opt-in/secondary; pill is primary.
- **Multi-modal recall** (image/audio callback) — out of scope for v6.0; reserved for v7+.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| COPILOT-01 | At least one end-user-noticeable copilot move proves retrieval is firing — **transition-shape callback** ("last time you ran this blend you killed the bass 2 bars earlier"), linter-grounded so the comparison must resolve to a real registered past moment. | §Pattern 1 (Transition-shape Callback Fragment) — prompt fragment lives in `state/coach.py::task_for_event` for TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL branches, gated on non-empty `recall_moments`. The Phase 65 PAST-tense fence + the `[recall:<id>]` linter wire are the floor; this phase only adds the prompt fragment that INVITES Gemini to USE the survivors. §Pitfall 6 (Prompt extraction-trigger phrases) documents the forbidden vocabulary. |
| COPILOT-02 | Second **vocabulary/register callback** calls back phrasing/moves the DJ has made before — cited, warm, non-nagging (reuses v5.0 actionable-not-hype coach persona discipline + cooldown/pacing). | §Pattern 2 (Vocabulary/Register Callback Fragment) — prompt fragment lives in the `state/coach.py::task_for_event` PHASE + TRACK_CHANGE branches; relies on the SAME `recall_moments` survivor list (one retrieval query, two prompt fragments — see §Decision on dual-query vs. shared survivors). The signature text in each `Record` already carries the DJ's past phrasing tokens (Phase 64 ingest preserves `said: <ai_text>` post-emit; signatures include the citation-strip-stripped reaction text). §Pattern 3 (Cooldown wiring) keeps callbacks rare. |
| COPILOT-03 | Copilot voice carries **no anti-features** — no next-track recommendation, no LLM-extracted tendencies/insights presented as fact, no settings-screen personalization, no continuous audio embedding (enforced by review + static gate). | §Pattern 4 (Static anti-feature gate `tests/repo/test_no_recall_antifeatures.py`) — tokenize-stripped grep over `state/coach.py` + `prompts/matrix.py` for the 4-class forbidden vocabulary, mirroring `tests/memory/test_no_extraction.py:_strip_comments_and_docstrings`. §Pitfall 6 (extraction-trigger phrases) documents the trap. |
</phase_requirements>

## Summary

Phase 66 is a **wiring + prompt-fragment phase** on top of the Phase 65 anti-slop release gate, **not new retrieval infrastructure.** Phase 65 already shipped:
- The `MemoryRecall` service that pre-dispatches off-loop on track-aware events (`src/vibemix/memory/retrieval.py`).
- The gated `recall[…]` PAST-tense block in `evidence_line` (`src/vibemix/state/coach.py:220-226`).
- The `recall` evidence source registered in `EVIDENCE_SOURCES` + `_SOURCE_ALT` regex (`src/vibemix/state/evidence_registry.py:111,136`).
- The `[recall:<record_id>]` form in `CITATION_GRAMMAR_BLOCK` (`src/vibemix/prompts/matrix.py:118`).
- The unconditional per-turn `clear_source("recall")` rescope at `dj_cohost.py:706-713` (anti-poisoning cross-turn fix, iter-3 BLOCKER closure).
- The `_build_citation_strip` allow-list at `dj_cohost.py:215`, currently `("ev", "mix", "midi", "key")` — DELIBERATELY missing `recall` per a Phase 65 deferral comment ("the recall chip is Phase 66").
- The `VIBEMIX_RECALL_ENABLED` env flag (default-OFF) wired in `__main__.py:856-877`.

Phase 66 adds, in order of structural load:
1. **One-char source allow-list edit** at `_build_citation_strip:215` to surface a `recall` chip (with a fixed `"recall"` verb mirroring the `key` precedent at `:230-236`). This is the user-visible Tier-1 surface.
2. **Two new prompt fragments** in `AICoach.task_for_event` (or a new helper) that tell Gemini "if a survivor matches what's happening NOW, you may emit ONE warm `[recall:<id>]` line" — gated on non-empty `recall_moments` AND the event type. One fragment for transition-shape (TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL); one for vocabulary (PHASE / TRACK_CHANGE).
3. **A coach-tier cooldown** (≥120s between any two recall callbacks, max 1 per turn) that sits ABOVE the Phase 65 event-detector cooldowns (which fire the event itself, separate concern). Implemented as a per-agent `_last_recall_callback_at: float` timestamp + a single-int counter that resets per turn.
4. **A static anti-feature gate** in `tests/repo/test_no_recall_antifeatures.py` mirroring `tests/memory/test_no_extraction.py:_strip_comments_and_docstrings` — tokenize-stripped grep over coach persona + prompt files for forbidden phrases ("you tend to", "you usually", "next track", "you should play").
5. **HUMAN-UAT + KAAN-ACTION carry-forward** following the Phase 60 harmonic-veto pattern.

**Primary recommendation:** Plan as **3 plans across 2 waves** (RED contract → wave parallel: prompt fragments + chip allow-list + cooldown ⇉ then anti-feature static gate + HUMAN-UAT). This is one wave SLIMMER than Phase 65's 4-plan structure because Phase 66 has zero new infrastructure surface — every load-bearing seam was opened by Phase 65, so the test contract collapses into a single RED-first wave and the implementation collapses into a single GREEN wave.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Recall chip on `citation_strip` (UI Tier-1 surface) | API/Backend (`agent/dj_cohost.py:_build_citation_strip`) | Browser (renderer reads existing payload, no changes) | Wire format is locked at `ui_bus/messages.py::CitationChipPayload`; Phase 66 widens the chip-build allow-list, never the renderer. |
| Transition-shape callback prompt fragment | API/Backend (`state/coach.py::task_for_event`) | — | The prompt fragment is a deterministic string assembly in the agent's coach persona seam; never crosses the wire. Gemini is the LLM tier, but the prompt is built backend-side. |
| Vocabulary callback prompt fragment | API/Backend (`state/coach.py::task_for_event`) | — | Same as transition-shape — pure backend prompt assembly. |
| Cooldown wiring (≥120s + max 1/turn) | API/Backend (`agent/dj_cohost.py::DJCoHostAgent`) | — | Per-agent in-memory state, like the existing `_invoke_counter` / `_ai_text_history`. Never touches MusicState (single-writer invariant), never opens a port (one-socket invariant). |
| Anti-feature static gate | CI/Build (`tests/repo/test_no_recall_antifeatures.py`) | — | Tokenize-stripped grep over prompt source files; identical pattern to `tests/memory/test_no_extraction.py`. |
| HUMAN-UAT + KAAN-ACTION discharge | Project docs (`.planning/phases/66-visible-copilot-move/66-HUMAN-UAT.md` + `KAAN-ACTION-LEGAL.md §RECALL-EAR`) | — | Documentation tier; ride the v4.0 / Phase 60 / Phase 65 KAAN-ACTION carry-forward pattern. |

## Standard Stack

### Core (all REUSED, not installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.12 | All Phase 66 surface | No net-new deps (WIRING milestone) |
| Phase 65 `MemoryRecall` service | shipped | Survivor source (read-only, `get_latest()`) | Phase 65 invariant — never touched here |
| Phase 65 `EvidenceRegistry::clear_source("recall")` | shipped | Per-turn rescope (cross-turn anti-poisoning) | Already unconditional at `dj_cohost.py:706-713` |
| Phase 59/65 `CitationLinter` | shipped | Whole-turn strip on fabricated `[recall:<id>]` | Existence-only check; zero new code |

**Installation:** None — this phase installs nothing.

**Version verification:** N/A — no package additions.

## Package Legitimacy Audit

> **Phase 66 installs no packages.** This is a pure code-edit + test-file phase: 1-char allow-list edit, 2 prompt-fragment strings, ~30 lines of cooldown state, 1 static-gate test file, 1 UAT markdown. Skipping the slopcheck protocol per the gate's "phase installs external packages" trigger condition.

## Architecture Patterns

### System Architecture Diagram

```
   TRACK-AWARE EVENT FIRES  ───►  Phase 65 dispatch (already shipped)
   (TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE
    — gated per RECALL_EVENT_GATE + Phase 66 fragment selector)
        │
        ▼
   MemoryRecall.on_event(...)   [off-loop, deadline-bounded — Phase 65]
        │
        ▼  survivors (cosine ≥ 0.7, top-k=3, current-session excluded)
   agent.llm_node                                                      [Phase 65 wiring]
        │
        ├─ if recall_moments not empty:
        │     registry.clear_source("recall")    [unconditional rescope, Phase 65]
        │     registry.write("recall", record_id, t)   [BEFORE snapshot]
        │     ...
        │
        ├─ COOLDOWN GATE (NEW — Phase 66) ─────────────────────────┐
        │     now - self._last_recall_callback_at < 120s ?         │
        │       YES → drop recall_moments → kwarg omitted          │
        │       NO  → proceed                                       │
        ├──────────────────────────────────────────────────────────┘
        │
        ▼
   build_prompt(ev, recall_moments=recall_moments) [Phase 65 kwarg]
        │
        ├─ evidence_line: PAST-tense fenced "FROM A PAST SESSION..." block [Phase 65]
        │
        └─ task_for_event:
              ┌─ TRACK_CHANGE/MIX_MOVE/LAYER_ARRIVAL + recall_moments?
              │     APPEND transition-shape fragment (NEW — Phase 66)
              │     "If a past moment matches what just happened NOW,
              │      you MAY add ONE warm line citing [recall:<id>] from
              │      the FROM A PAST SESSION block above. Past-tense only,
              │      grounded in BOTH the live audio AND the past signature."
              │
              ┌─ PHASE/TRACK_CHANGE + recall_moments?
              │     APPEND vocabulary fragment (NEW — Phase 66)
              │     "...you MAY echo your own past phrasing/move from
              │      the FROM A PAST SESSION block, citing [recall:<id>],
              │      using YOUR words (not paraphrased)."
              │
              (BOTH fragments share a single recall_moments survivor list;
               Gemini emits AT MOST ONE [recall:<id>] per turn due to
               anti-poisoning + cooldown + max-1-per-turn structural cap.)
        │
        ▼  Gemini emits reaction
   CitationLinter.check(...)                                      [Phase 65 wiring]
        │
        ├─ [recall:<id>] in snapshot["recall"]?  (existence-only)
        │    YES → emit
        │    NO  → strip WHOLE turn (poisoning gate)
        │
        ▼  emit chunks
   _build_citation_strip                                          [Phase 66 EDIT]
        │
        ├─ allow-list: ("ev", "mix", "midi", "key", "recall")    ← +recall
        │
        ├─ if source == "recall":
        │     verb = "recall"                                     [Phase 66 NEW]
        │     timestamp_s = registry.snapshot()["recall"][body][0]
        │       (current-turn t_session — when callback FIRED)
        │
        ▼
   {event_id: "recall:<record_id>", verb: "recall", timestamp_s: <now>}
        │
        ▼
   ipc.session.cohost-reaction → SessionCohostReaction.citation_strip
        │
        ▼
   Tier-1 UI (mocks/vibemix-app-ui.html) — recall chip surfaces
   alongside ev/mix/midi/key chips per existing renderer.

   COOLDOWN BOOKKEEPING (NEW — Phase 66):
   IF a chip with verb="recall" was emitted this turn:
     self._last_recall_callback_at = now    [arms 120s lockout]
   ELSE: cooldown counter unchanged.
```

### Recommended Project Structure

```
src/vibemix/
├── agent/dj_cohost.py          # EDIT: _build_citation_strip allow-list (+1 elt)
│                               #       + cooldown state (~30 lines: __init__ ts,
│                               #         llm_node gate, post-emit arm)
├── state/coach.py              # EDIT: task_for_event fragment appends per event
│                               #       (gated on non-empty recall_moments) — adds
│                               #       ~40 lines of fragment strings; the falsy
│                               #       gate is the EXACT precedent the recall[…]
│                               #       block uses at :220.
├── prompts/matrix.py           # NO EDIT (decision: do NOT add a recall section
│                               #          to CITATION_GRAMMAR_BLOCK — Gemini already
│                               #          knows the [recall:<record_id>] grammar
│                               #          from Phase 65; the fragments INVITE use,
│                               #          they don't add new grammar)
└── ui_bus/messages.py          # NO EDIT (wire format is the existing
                                #          CitationChipPayload — recall chip is
                                #          payload-shape-identical to key)

tests/
├── agent/test_citation_strip_emit.py   # ADD: test_recall_citation_yields_chip_COPILOT01
│                                       #      test_fabricated_recall_yields_no_chip_COPILOT01
│                                       #      (mirror existing test_key_citation_* shape)
├── agent/test_dj_cohost_linter.py      # ADD: test_cooldown_suppresses_back_to_back_recalls
│                                       #      test_max_one_recall_per_turn
├── state/test_coach.py                 # ADD: test_task_for_event_appends_transition_fragment_when_recall_present
│                                       #      test_task_for_event_no_fragment_when_recall_empty
│                                       #      test_task_for_event_byte_identical_v5_baseline
└── repo/test_no_recall_antifeatures.py # NEW: tokenize-stripped grep over coach/persona files
                                        #      for ("you tend to", "you usually", "you always",
                                        #      "next track", "you should play", "your tendency",
                                        #      "based on your past")
                                        #      Positive-control: synthetic source carrying
                                        #      one forbidden phrase MUST be flagged after
                                        #      stripping; the same phrase inside a
                                        #      docstring must NOT be flagged.

.planning/phases/66-visible-copilot-move/
├── 66-HUMAN-UAT.md             # NEW: ear-test items for Kaan
└── (KAAN-ACTION-LEGAL.md gets +§RECALL-EAR entry — root-level file)
```

### Pattern 1: Transition-shape Callback Prompt Fragment

**What:** A conditional append to the `task_for_event` string for the three transition-eligible event classes (TRACK_CHANGE, MIX_MOVE, LAYER_ARRIVAL), gated on non-empty `recall_moments` AND the cooldown gate.

**When to use:** In `AICoach.task_for_event` (or — recommended — a new sibling helper `AICoach.recall_fragment_for_event(ev, recall_moments)` so the testable surface is a single pure function). The fragment lands AFTER the existing task tail so the model reads "react to MIX_MOVE" first, then "if a survivor matches..." as a CONDITIONAL invitation.

**Example:**
```python
# Source: NEW — Phase 66 prompt fragment, lives in src/vibemix/state/coach.py
# Architecture mirrors Phase 60 HARMONIC-04 TRANSITION_OPPORTUNITY at coach.py:363-381:
#   - cited, grounded, narrate-only
#   - past-tense framed (the past moment AND the current latency)
#   - the system gives you the cite; you do NOT invent it
TRANSITION_SHAPE_RECALL_FRAGMENT_TPL: str = (
    " A PAST MOMENT from a prior session is attached in the "
    "'FROM A PAST SESSION' block above — a transition with similar shape "
    "you've run before. If — AND ONLY IF — that past moment matches what "
    "just happened in the live audio, you MAY add ONE short past-tense "
    "callback line referencing it, citing exactly [recall:{record_id}]. "
    "Compare what you heard NOW vs. what's in the past signature — the "
    "delta is the whole point. Examples of shape: \"that blend sat longer "
    "than the same one you ran last set\", \"killed the bass earlier this "
    "time around\", \"cleaner cut than the version you ran before\". "
    "Hard rules: cite [recall:{record_id}] EXACTLY ONCE (the registry "
    "validates it; a fabricated id strips the whole turn); do NOT invent a "
    "past moment, paraphrase the past signature, or describe it as live; "
    "do NOT recommend a NEXT track or move (no 'try X next time'); do NOT "
    "claim a tendency ('you usually do', 'you always') — narrate THIS one "
    "compared to THAT one. If the past moment doesn't match, OMIT the "
    "callback entirely — your normal reaction is the floor."
)
```

The fragment template carries the record_id of the STRONGEST survivor (highest cosine — Phase 65 returns survivors already sorted by score descending via `cosine_topk`); if multiple survivors are present, the LLM still sees all of them in the PAST-tense fenced `recall[…]` block, but the fragment instruction names ONE for the citation. This keeps the "max 1 recall per turn" cap a structural property of the prompt instruction, not just the cooldown gate.

### Pattern 2: Vocabulary/Register Callback Prompt Fragment

**What:** A second conditional fragment for PHASE + TRACK_CHANGE events (narrative moves, not transition moves), gated on non-empty `recall_moments`.

**When to use:** In the same `recall_fragment_for_event` helper. PHASE + TRACK_CHANGE events overlap with the transition fragment on TRACK_CHANGE only — research-question §Decision below resolves which fragment wins on the TRACK_CHANGE overlap.

**Example:**
```python
VOCABULARY_RECALL_FRAGMENT_TPL: str = (
    " A PAST MOMENT from a prior session is attached in the "
    "'FROM A PAST SESSION' block above — a phrasing or call you made "
    "before. If — AND ONLY IF — what you'd naturally say RIGHT NOW lines "
    "up with that past signature, you MAY echo your own past words, "
    "citing exactly [recall:{record_id}]. The past signature is YOUR "
    "voice from before; speak in the same register, not Gemini-paraphrased. "
    "Examples: \"same call you made on the last drop like this\", "
    "\"your line from the last set still holds\". Hard rules: cite "
    "[recall:{record_id}] EXACTLY ONCE; do NOT invent a past phrasing; "
    "do NOT claim it's a habit ('you always', 'you tend to'); do NOT "
    "recommend a next move. If your live reaction wouldn't naturally "
    "echo the past, OMIT the callback — a forced echo is the failure "
    "mode this phase guards."
)
```

### Pattern 3: Coach-Tier Cooldown Wiring

**What:** A per-agent timestamp + a per-turn boolean that gates whether `recall_moments` is threaded into the prompt at all.

**When to use:** Inside `DJCoHostAgent` — initialize `_last_recall_callback_at: float = 0.0` in `__init__`; check `time.time() - self._last_recall_callback_at < RECALL_CALLBACK_COOLDOWN_S` (120s) inside `llm_node` AFTER the Phase 65 `get_latest()` pull but BEFORE the registry write loop. If the cooldown is active, set `recall_moments = []` (which makes everything downstream byte-identical to the cold path — the registry write loop is skipped, the prompt fragment is skipped via the falsy `if recall_moments:` gate in the new helper, and the chip never surfaces because no `[recall:<id>]` token can land in the reaction).

The "max 1 recall per turn" cap is a STRUCTURAL property of the existing wiring: only the strongest survivor's `record_id` is interpolated into the prompt fragment, and the prompt fragment explicitly instructs Gemini "cite [recall:<id>] EXACTLY ONCE". The cap doesn't need a runtime counter — it's enforced by the prompt instruction + the registry strict-subset invariant + the fact that a SINGLE turn produces a single emission stream.

**Example:**
```python
# Source: NEW — Phase 66, src/vibemix/agent/dj_cohost.py module constant
# Mirrors src/vibemix/audio/constants.py::MIN_EVENT_GAP_PER_TYPE shape — a
# named, one-line-editable tuning knob. 120s is the conservative Phase 66
# default; KAAN-ACTION can re-tune on the real corpus.
RECALL_CALLBACK_COOLDOWN_S: float = 120.0  # ≥120s between two recall callbacks

# In DJCoHostAgent.__init__ — colocated with _ai_text_history, _invoke_counter:
self._last_recall_callback_at: float = 0.0

# In DJCoHostAgent.llm_node — INSIDE the existing try block at :676, AFTER
# the get_latest() pull at :715 and BEFORE the registry write loop at :754:
if recall_moments:
    if (time.time() - self._last_recall_callback_at) < RECALL_CALLBACK_COOLDOWN_S:
        # Coach-tier cooldown active — drop survivors so the prompt is
        # byte-identical to the cold path for this turn. The recall block
        # never lands; no [recall:<id>] token can be emitted; no chip can
        # surface. The registry clear_source above already ran, so no
        # stale registrations remain.
        recall_moments = []

# In the EMIT path (after CitationLinter.check passes and ai_text is yielded) —
# scan the emitted reaction for at least one valid [recall:...] atom; if
# present, arm the cooldown:
if any(source == "recall" for source, _ in parse_citations(emitted_text)):
    self._last_recall_callback_at = time.time()
```

### Pattern 4: Anti-Feature Static Gate

**What:** A tokenize-stripped grep test in `tests/repo/` mirroring `tests/memory/test_no_extraction.py:_strip_comments_and_docstrings` (the exact same stripper, cloned to avoid coupling to `memory/`).

**When to use:** As a CI gate that fires on every commit; a positive-control test ensures the stripper itself works (so a stripper bug can't silently make the gate vacuous).

**Example:**
```python
# Source: NEW — tests/repo/test_no_recall_antifeatures.py
# Mirrors tests/memory/test_no_extraction.py shape verbatim.
FORBIDDEN_RECALL_PHRASES: tuple[str, ...] = (
    "you tend to",
    "you usually",
    "you always",
    "your tendency",
    "your tendencies",
    "based on your past",
    "next track",
    "you should play",
    "you should try",       # near-miss to "next track" recommendation
    "I recommend",
    "my recommendation",
)

# Files to scan — the prompt + coach persona surface that Gemini sees:
TARGET_FILES = (
    "src/vibemix/state/coach.py",
    "src/vibemix/prompts/matrix.py",
)

def test_no_recall_antifeatures_in_coach_surface() -> None:
    """COPILOT-03 — no LLM-extracted tendency / next-track / settings-
    personalization phrases reach Gemini through the coach/prompt surface.

    Anti-features are STRUCTURALLY EXCLUDED — Phase 65 already keeps
    memory out of the live path; Phase 66 keeps the visible callbacks
    inside the 'compare THIS to THAT' shape, never 'you tend to'.
    """
    offenders = {}
    for rel in TARGET_FILES:
        src = (REPO / rel).read_text(encoding="utf-8", errors="replace")
        stripped = _strip_comments_and_docstrings(src)
        hits = [phrase for phrase in FORBIDDEN_RECALL_PHRASES if phrase in stripped.lower()]
        if hits:
            offenders[rel] = hits
    assert not offenders, (
        f"Phase 66 anti-feature gate VIOLATED — forbidden phrases "
        f"reached the coach/prompt surface: {offenders}. v6.0 anti-features "
        "lock: no LLM-extracted tendencies, no next-track recommendation."
    )
```

### Anti-Patterns to Avoid

- **Threading `recall_moments` directly into the prompt without the cooldown gate.** Phase 65 wired the kwarg path; Phase 66's cooldown gate sits ON TOP of that path. Adding the prompt fragment before adding the cooldown gate would mean a freshly-fired `LAYER_ARRIVAL → TRACK_CHANGE → MIX_MOVE` cascade could produce three recall callbacks back-to-back — the exact nagging failure mode the cooldown exists to prevent.
- **Putting the cooldown in `EventDetector._cooldown_ok`.** That cooldown gates the EVENT (whether the event fires at all). The recall-callback cooldown is a SEPARATE concern — the event still fires (so the live reaction still happens), only the recall-callback fragment is suppressed. Keep them separate: event cooldown in `audio/constants.py::MIN_EVENT_GAP_PER_TYPE`, recall-callback cooldown in `agent/dj_cohost.py::RECALL_CALLBACK_COOLDOWN_S`.
- **Deriving the recall chip verb from the record_id.** Body shape is `<session_id>:<seq>` (e.g. `"20260520-2200:7"`); deriving a "verb" from a date is meaningless and leaks an embedding-internal value to the UI. Mirror the `key` precedent at `_build_citation_strip:230-236` — use a fixed letters-only `"recall"` verb.
- **Appending the recall fragment to the diet/compact path.** The diet path serves ACK_ELIGIBLE_EVENTS (HEARTBEAT, MIX_MOVE, LAYER_ARRIVAL, KAAN_SPOKE). HEARTBEAT is never a retrieval event (Phase 65 invariant); MIX_MOVE and LAYER_ARRIVAL ARE retrieval events but Phase 65 already documents that the diet path intentionally has no recall block (`coach.py:213-216`). Phase 66's prompt fragments live in the FULL `task_for_event` path; the existing `_bp_kwargs` logic at `dj_cohost.py:827` already ensures `recall_moments` is never passed in the diet branch.
- **A second retrieval query for the vocabulary callback.** The Phase 65 `MemoryRecall.on_event` returns top-k survivors of the GENERIC `coach_line` signature query. Vocabulary callbacks read the SAME signatures (the `said:` post-emit text was already serialized into the Phase 64 signature template). One query, two prompt fragments — see §Decision on dual-query vs. shared survivors.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Recall chip allow-list logic | Custom verb-derivation regex for `recall` body | Fixed letters-only verb `"recall"` (mirror `key:230-236`) | The `key` precedent already solved the "opaque body, no @t, no verb-like component" problem. Re-derive from scratch and you'll break the `^[a-z]+( [a-z]+){0,2}$` verb-format pin at `tests/agent/test_citation_strip_emit.py:226`. |
| Prompt-fragment dispatch by event type | A new fragment-dispatcher class with strategy pattern | Inline conditional appends in `task_for_event` (mirrors the existing 9 event-type branches at `coach.py:273-381`) | The existing `task_for_event` is already a 9-branch dispatcher. Adding two conditional appends inside the existing TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL / PHASE branches is structurally identical to how Phase 60 added the KEY_CLASH and TRANSITION_OPPORTUNITY branches. A new dispatcher class is over-engineering for ~40 lines of fragment templates. |
| Anti-feature detection | A custom AST walker over the coach surface | Tokenize-stripped substring grep (mirror `tests/memory/test_no_extraction.py:50-76`) | The existing static gate pattern is the proven shape: strip comments/docstrings (so prose documenting the ban can't self-trip), then substring-match the forbidden vocabulary. AST walking would catch more sophisticated evasions but the threat model here is a copy-paste of a banned phrase into a prompt, not an obfuscated AST construction. |
| Cooldown timer | A separate `RecallCooldown` class with `arm()` / `is_armed()` | One `float` field + one `time.time()` comparison inline in `llm_node` | The agent already tracks several `float`/`int` timestamps (`_invoke_counter`, `_ttft_meter.event_fired_at`, `_last_kaan_spoke_at` via state). One more timestamp + one comparison is the project's idiom. |
| HUMAN-UAT structure | A new template | Copy `54-HUMAN-UAT.md` shape (front-matter + numbered tests + Summary section) | The HUMAN-UAT shape is already proven across Phases 54-58. Phase 66 just needs 3-4 ear-test items in that shape. |

**Key insight:** Phase 66 is INTENTIONALLY a thin wiring + prompt-fragment phase. Every architectural decision Phase 65 made is the floor; this phase only ADDS the visible end-user surface (chip + two prompt fragments + a cooldown). Building custom infrastructure here would create maintenance debt against a project mode (`gsd-autonomous fully`) that explicitly favors precedent-following over invention.

## Runtime State Inventory

> Phase 66 is a thin wiring phase, not a rename/refactor/migration. The Phase 65 retrieval seam state (memory.db rows, registry entries, latch survivors) is INHERITED unchanged. Brief inventory to satisfy the protocol:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 66 writes no new rows. The Phase 64 `memory.db` rows the survivor list is drawn from are read-only here. Phase 65 `EvidenceRegistry` per-turn `recall` registrations are owned by Phase 65 wiring (unconditional clear at `dj_cohost.py:706-713` + per-turn write at `:771`). | None |
| Live service config | None — no new env vars (Phase 65 `VIBEMIX_RECALL_ENABLED` is the ONLY toggle and it stays default-OFF for Phase 66 too). No new ports (one-socket invariant). No new service deps. | None |
| OS-registered state | None — no Task Scheduler / pm2 / launchd / systemd surface touched. | None |
| Secrets/env vars | None — `VIBEMIX_RECALL_ENABLED` stays default-OFF (existing semantics: 0/off/false/empty → disabled). No new secrets. | None |
| Build artifacts | None — no `pyproject.toml` changes, no installable-package metadata changes. The `tauri/` sidecar bundle is unaffected (no new Python deps). | None |

**Conclusion:** Phase 66 is a *zero-state-migration* phase. Every byte of runtime state is owned upstream by Phase 65 or Phase 64.

## Environment Availability

> Phase 66 is a pure code+test phase with no external tool/runtime dependencies beyond what Phase 65 already shipped. Skipping the full audit per the protocol's skip condition ("phase has no external dependencies").

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest>=8` (existing — see `pyproject.toml`) + `pytest-mock` for the `mocker` fixture |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Quick run command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest tests/agent/test_citation_strip_emit.py tests/state/test_coach.py tests/repo/test_no_recall_antifeatures.py -q` |
| Full suite command | `source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| COPILOT-01 | Grounded `[recall:<id>]` citation in a reaction yields a chip with verb="recall", source-routed via the allow-list at `dj_cohost.py:215` | unit | `pytest tests/agent/test_citation_strip_emit.py::test_recall_citation_yields_chip_with_registry_timestamp_COPILOT01 -x` | ❌ Wave 0 (test file exists; new tests are RED-first) |
| COPILOT-01 | Fabricated `[recall:<id>]` yields NO chip (mirrors Phase 65 turn-strip — the chip CANNOT surface because the WHOLE turn strips upstream) | unit | `pytest tests/agent/test_citation_strip_emit.py::test_fabricated_recall_yields_no_chip_COPILOT01 -x` | ❌ Wave 0 |
| COPILOT-01 | TRACK_CHANGE / MIX_MOVE / LAYER_ARRIVAL with non-empty `recall_moments` AND cooldown not active → transition-shape fragment is appended to `task_for_event` output | unit | `pytest tests/state/test_coach.py::test_transition_recall_fragment_appears -x` | ❌ Wave 0 |
| COPILOT-01 | Empty `recall_moments` → fragment NOT appended → `task_for_event` byte-identical to v5.0 baseline | unit | `pytest tests/state/test_coach.py::test_task_for_event_byte_identical_v5_baseline_no_recall -x` | ❌ Wave 0 |
| COPILOT-02 | PHASE / TRACK_CHANGE with non-empty `recall_moments` AND cooldown not active → vocabulary fragment is appended | unit | `pytest tests/state/test_coach.py::test_vocabulary_recall_fragment_appears -x` | ❌ Wave 0 |
| COPILOT-02 | Two back-to-back recall-eligible turns within 120s → only first emits the prompt fragment (cooldown) | integration | `pytest tests/agent/test_dj_cohost_linter.py::test_cooldown_suppresses_back_to_back_recalls -x` | ❌ Wave 0 |
| COPILOT-02 | A single turn with multiple survivors → AT MOST ONE `[recall:<id>]` token can land (structural property of the fragment template + the registry strict-subset invariant; assert by inspecting the prompt body the agent built) | unit | `pytest tests/state/test_coach.py::test_only_strongest_survivor_record_id_in_fragment -x` | ❌ Wave 0 |
| COPILOT-03 | No "you tend to" / "you usually" / "you always" / "next track" / "you should play" phrases reach the coach/prompt surface | static-gate | `pytest tests/repo/test_no_recall_antifeatures.py -x` | ❌ Wave 0 (NEW file) |
| COPILOT-03 | Anti-feature gate has positive control (a synthetic forbidden phrase in a non-prompt file IS flagged; the same phrase in a docstring is NOT) | unit | `pytest tests/repo/test_no_recall_antifeatures.py::test_no_recall_antifeatures_detector_catches_a_forbidden_phrase -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/agent/test_citation_strip_emit.py tests/state/test_coach.py tests/repo/test_no_recall_antifeatures.py -q` (~5s)
- **Per wave merge:** `pytest tests/agent/ tests/state/ tests/coach/ tests/memory/ tests/repo/ tests/prompts/ -q` (covers Phase 65 regression surface; ~30s)
- **Phase gate:** Full suite green before `/gsd:verify-work` — `pytest -q`. Acceptance is **zero NEW failures vs the known `live-tuning-or-brain` baseline** (8 pre-existing WIP failures documented in 65-VERIFICATION.md).

### Wave 0 Gaps

- [ ] `tests/repo/test_no_recall_antifeatures.py` — NEW file; implements the static gate + positive-control test (mirrors `tests/memory/test_no_extraction.py` shape).
- [ ] Test additions to `tests/agent/test_citation_strip_emit.py` — new `recall`-chip allow-list tests (mirror the `key` precedent at `test_key_citation_yields_chip_with_registry_timestamp_DECK03` + `test_fabricated_key_citation_yields_no_chip_DECK03`).
- [ ] Test additions to `tests/state/test_coach.py` — new fragment-appending tests + cold-path byte-identity test (mirror the existing `test_evidence_line_silent_state_full_format` golden-pin).
- [ ] Test additions to `tests/agent/test_dj_cohost_linter.py` — new cooldown tests (mirror the existing `test_fabricated_recall_strips_turn_n_plus_1_with_empty_recall` integration shape; same stub-recall-service pattern).
- [ ] No framework installs needed — `pytest` + `pytest-mock` already in `pyproject.toml`.

## Security Domain

> Phase 66 is a UI/prompt-surface phase. The Phase 65 anti-poisoning gate (the milestone's hard security boundary) is unchanged; Phase 66 only widens the chip allow-list (a one-character source-string edit) and adds two prompt fragments + a cooldown. There is no new authentication, no new session boundary, no new data path. The applicable ASVS surface is narrow:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface touched. |
| V3 Session Management | no | No session boundary touched. The current-session-exclusion invariant is Phase 65's, not Phase 66's. |
| V4 Access Control | no | No access boundary touched. |
| V5 Input Validation | yes (inherited) | The Phase 65 `CitationLinter` existence-only check + `EvidenceRegistry` strict-subset invariant is the validation gate. Phase 66's chip allow-list edit and prompt fragments do not introduce a new input surface — they consume already-validated registry/snapshot data. |
| V6 Cryptography | no | No crypto surface. |

### Known Threat Patterns for {prompt-injection / poisoning surface}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt-injection via the recall fragment template | Tampering | Fragment templates are FIXED STRINGS with one interpolation point (`{record_id}`); the record_id is a validated registry key, NOT user input. Mirrors `MOOD_PERSONAS` anti-injection pattern (matrix.py:41, `CITATION_GRAMMAR_BLOCK` has zero interpolation). |
| Cross-turn recall poisoning (turn N survivors leak into turn N+1) | Tampering | Phase 65's iter-3 BLOCKER fix at `dj_cohost.py:706-713` (unconditional `clear_source("recall")` at top of recall path) is unchanged and load-bearing. Phase 66 inherits it; its cooldown gate ALSO drops `recall_moments = []` on cooldown-active turns, which means the registry write loop is skipped (defense in depth). |
| Anti-feature creep via a copy-pasted "you tend to..." prompt phrase | Spoofing | The new `tests/repo/test_no_recall_antifeatures.py` static gate is the mitigation; mirrors `tests/memory/test_no_extraction.py` shape. |
| Chip-allow-list expansion smuggling a non-existence-only source | Tampering | The `recall` source is already in `EVIDENCE_SOURCES` AND `_SOURCE_ALT` AND ABSENT from `_TIME_KEYED_SOURCES` (Phase 65 invariant verified in `65-VERIFICATION.md` observable #14). Phase 66's allow-list edit at `_build_citation_strip:215` is a CONSUMER of that schema; it cannot reclassify `recall` as time-keyed. |

## Sources

### Primary (HIGH confidence — verified directly in the codebase this session)

- `src/vibemix/agent/dj_cohost.py:148-260` — `_build_citation_strip` (the allow-list edit site at `:215` + the `key` verb precedent at `:230-236`). VERIFIED via direct read.
- `src/vibemix/agent/dj_cohost.py:546-656,706-713,754-778` — `_maybe_dispatch_recall`, the unconditional `clear_source("recall")`, the registry write loop. Phase 66 cooldown integrates here. VERIFIED via direct read.
- `src/vibemix/state/coach.py:62-228,272-382` — `AICoach.evidence_line` (recall block at :220-226), `task_for_event` (9 event-type branches). VERIFIED via direct read.
- `src/vibemix/memory/retrieval.py` — full `MemoryRecall` service: `RECALL_EVENT_GATE`, `RECALL_SIMILARITY_FLOOR=0.7`, `RECALL_TOP_K=3`, `RECALL_DEADLINE_S=0.5`. VERIFIED via direct read.
- `src/vibemix/state/evidence_registry.py:100-149` — `EVIDENCE_SOURCES` (9 elements incl `recall`), `_SOURCE_ALT` regex, EBNF documentation, ASYMMETRY note re: `memory/ingest.py`. VERIFIED via direct read.
- `src/vibemix/prompts/matrix.py:101-139,698-789` — `CITATION_GRAMMAR_BLOCK` (9 source forms incl `[recall:<record_id>]`), `build_system_instruction`, COACH_* cells. VERIFIED via direct read.
- `src/vibemix/__main__.py:846-922` — `VIBEMIX_RECALL_ENABLED` env-var wiring + `recall=recall_svc` agent kwarg. VERIFIED via direct read.
- `src/vibemix/audio/constants.py:58-95` — `EVENT_GLOBAL_MIN_GAP=22.0`, `MIN_EVENT_GAP_PER_TYPE` shape (the cooldown-constant idiom Phase 66 follows). VERIFIED via direct read.
- `tests/agent/test_citation_strip_emit.py:159-232` — `key` chip + verb-format precedent tests Phase 66 mirrors. VERIFIED via direct read.
- `tests/agent/test_dj_cohost_linter.py:245-400` — `test_fabricated_recall_strips_turn` + cross-turn regression (the anti-poisoning gates Phase 66 inherits and must not regress). VERIFIED via direct read.
- `tests/memory/test_no_extraction.py` — the tokenize-stripped static-gate template Phase 66 clones. VERIFIED via direct read.
- `.planning/phases/66-visible-copilot-move/66-CONTEXT.md` — the discuss-phase decisions (all 4 areas). VERIFIED via direct read.
- `.planning/phases/65-memory-retrieval-seam/65-CONTEXT.md, 65-VERIFICATION.md, 65-REVIEW-FIX.md, 65-RESEARCH.md` — the floor Phase 66 stands on. VERIFIED via direct read.
- `.planning/REQUIREMENTS.md` — COPILOT-01/02/03 + the v6.0 anti-feature lock + traceability table. VERIFIED via direct read.
- `.planning/STATE.md` — milestone status (Phase 65 closed 4/4, Phase 66 ready to plan). VERIFIED via direct read.

### Secondary (HIGH confidence — verified by precedent reasoning across multiple files)

- The Phase 60 HARMONIC-04 / Phase 65 RECALL KAAN-ACTION carry-forward pattern (default-OFF, ship engineering, surface to `KAAN-ACTION-LEGAL.md`). Verified by `__main__.py:856`, `event_detector.py:143-153`, `65-VERIFICATION.md` §Required Artifacts + §Human Verification Required, `.planning/phases/54-hype-mode-live/54-HUMAN-UAT.md` shape.
- The "compose, don't subclass" idiom for adding prompt fragments to `task_for_event` (mirrors the Phase 60 KEY_CLASH + TRANSITION_OPPORTUNITY additions at `coach.py:332-381`).

### Tertiary (LOW confidence — would benefit from validation but is not load-bearing)

- None. Every load-bearing claim in this research was verified against the live codebase or its planning artifacts.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v5.0 single-turn reactive coach with no past-session memory | v6.0 retrieval-grounded coach (Phase 65 seam + Phase 66 visible callbacks) | Phase 63-66 (2026-05-22) | Visible "it remembers me" surface without an LLM-extraction layer or a managed memory framework. |
| (project-internal) Phase 65's deferred chip allow-list (comment in `_build_citation_strip:215`: "do NOT add `recall`… the recall chip is Phase 66") | Phase 66 makes the one-char edit + adds the verb branch | This phase | The deferred edit becomes a single PR; no architectural change. |

**Deprecated/outdated:**
- The retired POC era cohost variants (`cohost*.py` at repo root) — already pruned 2026-05-20. Their event-cooldown intuition was lifted into `src/vibemix/audio/constants.py::MIN_EVENT_GAP_PER_TYPE`; their citation-strip intuition was lifted into `_build_citation_strip`. Phase 66 reads neither — only the live `src/vibemix/` tree.

## Assumptions Log

> All claims in this research were verified directly against the live codebase or Phase 65's verified artifacts. No claim is tagged `[ASSUMED]` — the table is empty by design.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | (none) | — | — |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed on factual matters. The open questions below are CHOICES, not factual gaps.

## Common Pitfalls

### Pitfall 1: The cold-path byte-identity regression

**What goes wrong:** A naive addition of the recall prompt fragment to `task_for_event` runs the fragment unconditionally, which means a cold-memory turn (no survivors) produces a DIFFERENT `task_for_event` output than v5.0 — every existing `tests/state/test_coach.py` golden test fails.
**Why it happens:** The fragment APPEARS to be a string append, but the v5.0 byte-identity invariant (`test_evidence_line_audible_no_recall_byte_identical_v5_baseline`) is load-bearing across Phase 65 + Phase 66.
**How to avoid:** Mirror the Phase 65 `evidence_line` `recall[…]` block falsy gate at `coach.py:220` (`if recall_moments:`). Phase 66's fragment helper MUST be `def recall_fragment_for_event(ev, recall_moments): if not recall_moments: return ""` — empty string append is the cold-path byte-identity guarantee.
**Warning signs:** Any new test that asserts `task_for_event(..., recall_moments=None) != task_for_event(..., recall_moments=[])` is the bug; both MUST be `""`.

### Pitfall 2: Cooldown double-fire from rapid `set_next_event` calls

**What goes wrong:** `set_next_event` can be called twice in quick succession (the existing comment at `dj_cohost.py:519-521` documents that overwriting a pending event is intentional — a previous event was preempted). If the cooldown timestamp is armed inside `set_next_event` (or in any pre-`llm_node` hook), a preempt-then-replace sequence could double-count or under-count the cooldown.
**Why it happens:** The Phase 65 `_maybe_dispatch_recall` runs from `set_next_event` and DOES manage a `_recall_task` cancel-and-replace at `:653-656`. Adding cooldown bookkeeping in the SAME spot would couple two concerns.
**How to avoid:** Arm the cooldown timestamp AFTER the citation linter passes + chunks are emitted (the EMIT path, not the dispatch path). Specifically, after `parse_citations(emitted_text)` returns at least one `("recall", ...)` atom. This guarantees the cooldown is armed iff a real recall callback REACHED the audience, not iff a recall callback was MERELY ATTEMPTED.
**Warning signs:** A test where two `TRACK_CHANGE` events fire within 120s + the first one's reaction is STRIPPED (fabricated recall, anti-poisoning win) + the second one's recall-eligible-but-survivor-empty turn is SKIPPED. If the cooldown was armed by the first event's dispatch, the second event would be wrongly suppressed. The fix is the EMIT-path arming above.

### Pitfall 3: The recall chip surfaces but its timestamp is wrong

**What goes wrong:** The `_build_citation_strip` chip's `timestamp_s` field comes from `snapshot.get(source, {}).get(body)[0]` at `dj_cohost.py:222-228`. For the `recall` source, the registry was written at `dj_cohost.py:771` with `t = ev.state.set_seconds` (current turn's set-time). If a developer "fixes" this to use the past moment's original timestamp, the chip will lie about when the callback fired.
**Why it happens:** Intuitively, "the past moment happened at T_past" — but the CONTEXT decision Q3 in Area 3 is explicit: the chip is "the coach made a recall move just now", so timestamp must be CURRENT turn's time.
**How to avoid:** Leave the existing `dj_cohost.py:771` registry write logic UNCHANGED (`t_session = ev.state.set_seconds`). The chip's `timestamp_s = float(timestamps[0])` at `dj_cohost.py:228` reads this. Phase 66 needs ZERO timestamp-logic changes.
**Warning signs:** A test that asserts `strip[0]["timestamp_s"] == past_record.ts` would be wrong; the correct assertion is `strip[0]["timestamp_s"] == current_turn_set_seconds` (the value the agent wrote at `:771`).

### Pitfall 4: The vocabulary fragment paraphrases instead of echoing

**What goes wrong:** Gemini, given "echo the DJ's past phrasing", produces a paraphrase that sounds AI-generated ("based on your past sessions, your verbal style suggests..."). This is the exact failure mode COPILOT-03 prohibits.
**Why it happens:** Prompt instruction wording. "Echo" can be read as "describe in your voice"; "in YOUR words (not paraphrased)" needs explicit framing.
**How to avoid:** The vocabulary fragment must instruct Gemini "speak in the same register, not Gemini-paraphrased" — see §Pattern 2 fragment template. The HUMAN-UAT ear-test items must explicitly check for this failure mode.
**Warning signs:** Any callback that includes "your style" / "your voice" / "your past" + a description rather than a quote-shape echo. The fragment template's "Examples" section pins the quote-shape.

### Pitfall 5: TRACK_CHANGE overlaps between transition + vocabulary fragments

**What goes wrong:** TRACK_CHANGE is in BOTH event gates (transition-shape: Q1 Area 1; vocabulary: Q2 Area 1). On a TRACK_CHANGE event with non-empty survivors, both fragments could append — Gemini sees TWO conditional invitations and may emit TWO `[recall:<id>]` tokens (with the same record_id, since there's one survivor). The max-1-per-turn structural cap is then a property of survivor-list size, not prompt-instruction count.
**Why it happens:** The two fragments are SEPARATE conditional appends. On TRACK_CHANGE they overlap.
**How to avoid:** **Recommended (Discretion §Open Question 1):** On TRACK_CHANGE, transition-shape WINS — the vocabulary fragment is skipped. Rationale: TRACK_CHANGE is a transition moment by definition (the user is mixing INTO a new track); the transition-shape comparison is the more concrete callback. PHASE-only is where the vocabulary fragment dominates.
**Warning signs:** A TRACK_CHANGE turn that emits two `[recall:<id>]` tokens (even if they're for the same record_id, the chip would surface twice). The fragment-helper test asserts at most ONE fragment string is appended per call.

### Pitfall 6: Prompt extraction-trigger phrases sneak in

**What goes wrong:** Well-intentioned prompt wording like "based on your past sessions" or "you tend to do X here" is the EXACT failure mode COPILOT-03 prohibits. These phrases trigger Gemini's tendency-extraction circuits even when the survivor block is concrete.
**Why it happens:** "Based on" / "you tend to" / "you usually" are common English phrasings that read natural to humans but are LLM-extraction-flavored.
**How to avoid:** The `tests/repo/test_no_recall_antifeatures.py` static gate (Pattern 4) catches these. The fragment templates themselves use "compare what you heard NOW vs. what's in the past signature" (concrete, this-vs-that) rather than "based on your tendencies".
**Warning signs:** Any commit touching `coach.py` or `prompts/matrix.py` that the static gate flags. The gate's positive-control test ensures the stripper itself works (so the gate can't go vacuous silently).

## Code Examples

Verified patterns from the live codebase + adaptation for Phase 66:

### Existing `key`-source chip pattern (the verbatim precedent for `recall`)

```python
# Source: src/vibemix/agent/dj_cohost.py:215-243 (current)
if source not in ("ev", "mix", "midi", "key"):
    continue
# ... snapshot lookup ...
if source == "key":
    # Phase 59 (DECK-03): body is ``<deck>:<camelot>`` (e.g. A:8A),
    # not the ``KEY@t`` shape. The camelot detail (deck + code) lives
    # in event_id for the deep-link; the chip verb is a fixed,
    # letters-only "key" label (keeps the locked verb format
    # `^[a-z]+( [a-z]+){0,2}$` — camelot codes carry digits).
    verb = "key"
else:
    # Body shape is ``KEY@t`` for ev/aud/midi/mix; partition on "@"
    key, _, _ = body.partition("@")
    verb_tokens = key.lower().split("_")
    verb = " ".join(verb_tokens[:CITATION_VERB_MAX_WORDS])
```

### Phase 66 edit — add `recall` to allow-list + verb branch

```python
# Source: src/vibemix/agent/dj_cohost.py:215-243 (PROPOSED Phase 66 edit)
if source not in ("ev", "mix", "midi", "key", "recall"):  # +recall
    continue
# ... snapshot lookup unchanged ...
if source == "key":
    verb = "key"
elif source == "recall":
    # Phase 66 (COPILOT-01): body is `<session_id>:<seq>` (e.g.
    # "20260520-2200:7") — opaque to the user. The fixed letters-only
    # "recall" verb mirrors the `key` precedent: a structured/opaque
    # body has no verb-like component, so the verb is a fixed label.
    # The record_id detail rides in event_id for the deep-link.
    verb = "recall"
else:
    key, _, _ = body.partition("@")
    verb_tokens = key.lower().split("_")
    verb = " ".join(verb_tokens[:CITATION_VERB_MAX_WORDS])
```

### Existing `evidence_line` falsy-gate pattern (Phase 65 — the exact shape Phase 66's fragment helper clones)

```python
# Source: src/vibemix/state/coach.py:220-226 (current — Phase 65)
if recall_moments:
    parts = [
        f"[recall:{m.record_id}] {m.signature}" for m in recall_moments
    ]
    e.append(
        "FROM A PAST SESSION (not happening now): " + " || ".join(parts)
    )
```

### Phase 66 — `recall_fragment_for_event` helper (clones the falsy-gate shape)

```python
# Source: NEW — src/vibemix/state/coach.py (added near task_for_event)
# Phase 66 (COPILOT-01/02). Cold/empty path returns "" so a string append
# to task_for_event output is byte-identical to v5.0 baseline when
# recall_moments is None or [].
def recall_fragment_for_event(
    ev: Event,
    recall_moments: "list[Record] | None",
) -> str:
    """Return the recall callback prompt fragment for ``ev``.

    Empty string when ``recall_moments`` is None/[] OR the event type is
    not recall-eligible — preserves byte-identity for the cold/feature-off
    path AND for non-recall event classes.

    Selection logic (CONTEXT.md Area 1 Q1+Q2 + research §Pitfall 5):
        * TRACK_CHANGE → transition-shape fragment (transition WINS over
          vocabulary on the overlap — TRACK_CHANGE is a transition moment
          by definition)
        * MIX_MOVE, LAYER_ARRIVAL → transition-shape fragment
        * PHASE → vocabulary fragment
        * other event types → "" (no recall callback)

    Only the STRONGEST survivor's record_id (recall_moments[0], sorted
    by cosine score descending per Phase 65 cosine_topk contract) is
    interpolated into the template. The full survivor list is already
    visible to Gemini via the PAST-tense fenced recall[…] block in
    evidence_line; the fragment template instructs cite EXACTLY ONCE.
    """
    if not recall_moments:
        return ""
    strongest = recall_moments[0]  # cosine_topk sort order: highest first
    if ev.type in ("TRACK_CHANGE", "MIX_MOVE", "LAYER_ARRIVAL"):
        return TRANSITION_SHAPE_RECALL_FRAGMENT_TPL.format(
            record_id=strongest.record_id
        )
    if ev.type == "PHASE":
        return VOCABULARY_RECALL_FRAGMENT_TPL.format(
            record_id=strongest.record_id
        )
    return ""
```

### Phase 66 — `task_for_event` integration

```python
# Source: PROPOSED — src/vibemix/state/coach.py::AICoach.build_prompt
# (modifies the existing call at :423-429)
evidence = AICoach.evidence_line(
    ev.state,
    registry_snapshot=registry_snapshot,
    recall_moments=recall_moments,
)
task = AICoach.task_for_event(ev)
recall_frag = recall_fragment_for_event(ev, recall_moments)  # NEW Phase 66
return f"[{evidence} | event={ev.type}] {task}{recall_frag}"
```

### Phase 66 — cooldown wiring in `llm_node`

```python
# Source: PROPOSED — src/vibemix/agent/dj_cohost.py module constant + llm_node integration
RECALL_CALLBACK_COOLDOWN_S: float = 120.0  # Phase 66 — ≥120s between callbacks

# In DJCoHostAgent.__init__:
self._last_recall_callback_at: float = 0.0

# In llm_node, INSIDE the existing try block at :676, AFTER get_latest at :715:
if recall_moments:
    if (time.time() - self._last_recall_callback_at) < RECALL_CALLBACK_COOLDOWN_S:
        # Cooldown active — drop survivors. Downstream is byte-identical
        # to the empty-survivor path (no registry writes, no fragment, no chip).
        recall_moments = []

# After the citation linter passes + chunks are emitted (in the existing
# emit path that calls _build_citation_strip):
emitted_recall_chips = [c for c in chips if c.get("source") == "recall"
                       or c.get("event_id", "").startswith("recall:")]
if emitted_recall_chips:
    self._last_recall_callback_at = time.time()
```

## Open Questions (research-resolved recommendations)

These are CHOICES the planner should lock; each carries a research-recommended default that the planner can adopt without further investigation.

1. **TRACK_CHANGE overlap policy (transition-shape vs. vocabulary)**
   - What we know: TRACK_CHANGE is in both event gates (CONTEXT.md Q1+Q2 Area 1).
   - What's unclear: Which fragment wins on the overlap.
   - **Recommendation:** Transition-shape wins. TRACK_CHANGE is a transition moment by definition; the comparison shape ("you ran this blend before, and...") is more concrete + actionable than a vocabulary echo. PHASE-only is where vocabulary fragment dominates. (Implemented in `recall_fragment_for_event` above.)

2. **Dual retrieval queries vs. shared survivors**
   - What we know: Phase 65's `MemoryRecall.on_event(query_text)` is generic; `query_text` is `build_recall_query(ev)` = a `coach_line | track=… | phase=… | deck=… | event=…` shape.
   - What's unclear: Whether the vocabulary callback needs a different query.
   - **Recommendation:** Shared survivors. The Phase 64 `coach_line` signature template already encodes `said: <ai_text>` post-emit text — vocabulary survivors share the SAME embedding space as transition survivors. One retrieval query, two prompt fragments. Adding a second query doubles the FLEX embed cost + opens a coordination problem for the off-loop deadline.

3. **Number of survivors visible to the LLM in the prompt**
   - What we know: Phase 65 caps at top-k=3 with floor 0.7; `recall_moments` list is sorted desc by cosine.
   - What's unclear: Should the LLM see all 3 survivors or just the strongest?
   - **Recommendation:** All survivors visible in the PAST-tense fenced block (Phase 65 already does this); fragment template names the STRONGEST for the citation. Rationale: Gemini can pattern-match across multiple survivors when picking whether to use the callback at all, but the SINGLE-citation discipline is preserved by the fragment instruction. Mirrors how the `evidence_corpus[…]` footer shows aggregate counts while individual `[ev:KEY@t]` citations pin specific events.

4. **Chip visual treatment**
   - What we know: `frontend-enforcement` skill mandates CDJ-Whisper material discipline; the existing `key` chip + `ev/mix/midi` chips set the precedent.
   - What's unclear: Whether the `recall` chip needs a distinct visual treatment (different glow color, different shape) to distinguish a past-moment-callback from a current-event chip.
   - **Recommendation:** v6.0 ships the recall chip with the SAME treatment as other chips (no visual differentiation). A distinct treatment is a v6.1+ touch IF Kaan's ear-pass surfaces a need ("I want to see at a glance that the coach is recalling, not reacting"). Pre-building a distinct chip class without ear-pass evidence is over-engineering. UI-SPEC may be skipped for v6.0; if the frontend-enforcement skill auto-loads on a UI phase chain (`gsd-ui-phase`), defer to its judgment.

5. **Cooldown arm site (dispatch vs. emit)**
   - What we know: §Pitfall 2 documents the race; the recommendation is to arm after emit.
   - **Recommendation:** Arm at emit (after `_build_citation_strip` returns at least one `recall`-source chip). This is the strictest semantic: cooldown reflects "a recall callback REACHED the audience".

## Project Constraints (from CLAUDE.md)

Phase 66 must honor these directives extracted from `./CLAUDE.md`:

| Directive | Source | Phase 66 Compliance |
|-----------|--------|---------------------|
| Gemini-only (no Anthropic / OpenAI / managed memory frameworks) | CLAUDE.md (vibemix project) | Phase 66 makes no model calls; reuses Phase 65 `MemoryRecall` (which uses `LibraryEmbedder` + reused Gemini embedding) → COMPLIANT. |
| No CLAP / MERT / OpenL3 / continuous audio embedding | CLAUDE.md project memory `feedback_no_clap_use_gemini_embedding` + `project_gemini_embedding_2` | Phase 66 does no audio embedding. The static anti-feature gate explicitly checks for this class. → COMPLIANT. |
| No scope creep — clean utility only | CLAUDE.md project memory `feedback_no_scope_creep_clean_utility` | Phase 66 ships a one-char allow-list edit + two prompt fragments + a cooldown + one static gate + one UAT doc. No new infrastructure. → COMPLIANT. |
| One-click install — every dep choice rated green/yellow/red | CLAUDE.md project memory `project_one_click_install_hard_req` | Phase 66 installs zero packages. → COMPLIANT (trivially). |
| Privacy hard rule (no reading Hermes/OZ logs) | CLAUDE.md privacy rule | Phase 66 does not read any off-limits paths. → COMPLIANT. |
| `gsd-autonomous fully` mode (defer to KAAN-ACTION, never block) | CLAUDE.md project memory `feedback_autonomous_no_grey_area_pause` | Phase 66 ships engineering-green; Kaan-ear veto is carry-forward (CONTEXT.md Area 4 Q3). → COMPLIANT. |
| `frontend-enforcement` skill for any UI work | `.claude/skills/frontend-enforcement/SKILL.md` | Phase 66 widens the chip allow-list (one source); the renderer is unchanged. If a UI-SPEC chain runs for the chip visual treatment, the skill auto-loads. → COMPLIANT. |
| Use GSD command entry points for code edits | CLAUDE.md "GSD Workflow Enforcement" | Phase 66 runs through `/gsd:plan-phase` → `/gsd:execute-phase`. → COMPLIANT. |
| `vibemix` aesthetic = retro-futurist hardware (Pioneer/Roland CDJ-Whisper) | `frontend-enforcement` SKILL.md hard rule 7 | If chip styling lands in a UI-SPEC phase, the skill enforces it. v6.0 ships without distinct chip treatment (Open Q4). → COMPLIANT. |

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every load-bearing import is direct from the codebase (verified via `Read` + `grep`).
- Architecture: HIGH — the chip allow-list edit, the prompt-fragment shape, and the cooldown wiring all follow named precedents (key chip, decks[…] gate, MIN_EVENT_GAP_PER_TYPE), all verified directly.
- Pitfalls: HIGH — each pitfall is grounded in a specific line of code or a specific Phase 65 invariant that was verified.
- Anti-feature gate: HIGH — the template (`tests/memory/test_no_extraction.py:_strip_comments_and_docstrings`) is read verbatim.
- KAAN-ACTION pattern: HIGH — Phase 60 + Phase 65 + v4.0 SHIP all use the same shape, verified at `__main__.py:856`, `event_detector.py:143-153`, `54-HUMAN-UAT.md`.

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (30 days — stable project state, no upstream deps in flight). If a v6.0 sub-phase reshuffles `state/coach.py::task_for_event` or `agent/dj_cohost.py::_build_citation_strip` before Phase 66 lands, re-verify the line numbers in §Pattern 1/§Code Examples.

**Recommended plan structure (planner consumes this):**

| Plan | Wave | Scope |
|------|------|-------|
| **66-01** | Wave 0 (RED-first contract) | Write all 9 new tests in §Phase Requirements → Test Map BEFORE source edits. Acceptance = tests collect cleanly + fail for the right reasons (fragment missing, chip allow-list missing `recall`, cooldown missing, static gate missing). Includes the NEW `tests/repo/test_no_recall_antifeatures.py` file with its positive-control test. Mirrors Phase 65's 65-01 Wave 0 RED-first contract shape. |
| **66-02** | Wave 1 (GREEN — implementation, parallel-safe) | Three task lanes that can land in any order (no inter-lane file conflicts): (a) `dj_cohost.py::_build_citation_strip` allow-list + `recall` verb branch + cooldown state/gate/arm; (b) `state/coach.py` `recall_fragment_for_event` helper + `task_for_event` integration; (c) HUMAN-UAT.md file + KAAN-ACTION-LEGAL.md §RECALL-EAR entry. All 9 RED tests flip GREEN; zero NEW failures vs the documented `live-tuning-or-brain` baseline; v5.0 byte-identity goldens stay green. |

**Why 2 plans, not 3:** The CONTEXT.md guidance ("3 plans seems right") was a STARTING heuristic. The dependency analysis shows that the implementation tasks (chip allow-list, prompt fragments, cooldown, static gate, UAT) have no inter-task dependencies — they all touch different files. The Phase 65 4-plan structure was needed because Phase 65 had genuine wave dependencies (recall schema → recall service → live-path wiring → review fixes). Phase 66 has none — the schema is closed, the service is closed, the live-path wiring is closed. Splitting into 3 plans would create artificial waves for what is a single coherent wave of independent edits. **Recommendation: 2 plans (RED → GREEN), matching Phase 65 P63-01 + P63-02 + P63-03 paradigm where each plan is one wave.** The planner has final say; if the granularity config drives toward more plans, splitting Plan 66-02 into 02a (chip+cooldown), 02b (prompt fragments + static gate), 02c (UAT+KAAN-ACTION) is the natural cleavage.
