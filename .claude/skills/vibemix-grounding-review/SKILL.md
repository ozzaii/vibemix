---
name: vibemix-grounding-review
description: Reviews any change to what the vibemix co-host SAYS or WHEN it speaks against the 5 cardinal anti-slop invariants. Trigger BEFORE shipping edits to src/vibemix/state/coach.py, src/vibemix/agent/dj_cohost.py, anything under src/vibemix/prompts/ (matrix.py, filter.py, negative_dict.py), src/vibemix/state/event_detector.py, state/refresh.py, state/evidence_registry.py, coach/citation_linter.py, or any reaction/persona/lens/learn-tutor wiring. Also trigger when a PR/plan touches the reaction loop, the citation grammar, EVIDENCE_SOURCES, the slop filter, or the ws bus, OR when Kaan asks "is this grounded / will this slop / does this break an invariant / can we ship this reaction change". Reactions that are scripted, late, hallucinated, or generic are the release blocker — this is the gate.
metadata:
  trigger: Editing co-host speech/timing — coach.py, dj_cohost.py, prompts/*, event_detector.py, evidence_registry.py, citation_linter.py, or any reaction/lens/tutor wiring
---

# vibemix — Grounding Review

The product promise is "real DJ friend in your ear, no AI slop." Kaan blocks
release if a reaction feels scripted, late, hallucinated, or generic. Five
cardinal invariants (CLAUDE.md §Architecture) are the test-enforced spine of
that promise. This skill checks a change against all five with exact commands.

**Run it BEFORE claiming a reaction/prompt/event change is done.** A green
unit test for your feature is not enough — these invariants are cross-cutting
and easy to break from a "harmless" edit to a prompt string or a new event
type.

## How to use this skill

1. Identify which surfaces the change touches (speech content, timing, citation
   grammar, sockets — see the trigger map below).
2. Run every invariant command that the change could touch. When unsure, run
   all five — they are fast (mostly static AST/grep gates).
3. For any failure, read the failure signature in
   [references/invariant-checks.md](references/invariant-checks.md), fix the
   source, re-run. Never relax a gate to make it pass.
4. Report which invariants you verified and the exact command output.

**Test commands** (authoritative, from CLAUDE.md §Commands + CONTRIBUTING):

```bash
# Python invariants (run from repo root):
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q <test path>
# or:  uv run pytest -q <test path>

# The one TypeScript invariant (#5) — run from tauri/ui/:
cd tauri/ui && npm test          # vitest run, ~886 tests
```

Do NOT launch the full app to verify these — it binds `127.0.0.1:8765` and
collides with a running session. All five gates are static or unit-level.

## Trigger map — which invariant your change can break

| You edited… | Re-check |
|---|---|
| `prompts/matrix.py`, `prompts/filter.py`, `prompts/negative_dict.py` | #2 (grammar lock-step), #3 (slop filter) |
| `agent/dj_cohost.py` (llm_node, strip path) | #2, #3 |
| `state/coach.py` (build_prompt) | #2 |
| `state/evidence_registry.py` (`EVIDENCE_SOURCES`, regex) | #2 — and keep all 4 lock-step copies in sync |
| `coach/citation_linter.py` | #2 |
| `state/event_detector.py` (new event type / cooldown) | #1, #3 |
| `state/refresh.py` (MusicState writes) | #1 |
| anything under `src/vibemix/learn/` | #1, #3, #4 |
| `runtime/ws_bus.py`, any `websockets.serve` | #4 |
| `tauri/ui/src/session/` (SessionLayout, cohost panel) | #5 |

---

## Invariant #2 — Citation grounding (THE anti-slop release gate)

**Statement.** Every citation a reaction emits must resolve in
`EvidenceRegistry`. An un-cited or unbacked reaction is stripped to silence —
`<silence/>` beats an invented citation. Cited audio is the only thing the
co-host is allowed to talk about.

The chokepoint is `DJCoHostAgent.llm_node` in `src/vibemix/agent/dj_cohost.py`:
it runs `CitationLinter.check(full_text, snapshot, mode="live")` after the
silence/slop gate. Decision is **response-level binary** — one bad atom strips
the whole turn (`citation_strip` event logged, no audio). The retired ack-bank
fallback is gone; the strip path now emits true silence (or a silence pad if a
speculative head was already in flight).

**Verify:**

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
  tests/state/test_coach_anti_slop.py \
  tests/agent/test_citation_strip_emit.py \
  tests/agent/test_dj_cohost_grounding.py \
  tests/state/test_evidence_registry.py
```

Key pins: `test_spine_unbacked_coach_citation_is_stripped` (fabricated cite →
no voice), `test_spine_grounded_coach_citation_passes` (real cite → emits),
`test_fabricated_key_citation_yields_no_chip_DECK03` /
`test_empty_registry_yields_empty_list` (the strip never fabricates a chip).

**Violation looks like.** A reaction cites `[ev:...]`/`[track:...]`/`[key:...]`
that was never written to the registry and still reaches TTS; a new citation
source added to `EVIDENCE_SOURCES` but missing from `_SOURCE_ALT`, the EBNF
docstring, `prompts/matrix.py::CITATION_GRAMMAR_BLOCK`, or
`dj_cohost.py::_build_citation_strip` (the silent-poisoning hole — see
[references/invariant-checks.md](references/invariant-checks.md)).

**Why it matters.** This is the single hard release gate. A hallucinated
"that breakdown was sick" with no breakdown in the audio is exactly the slop
Kaan blocks on. The linter is what turns "trust the audio" from a slogan into
a binary chokepoint.

## Invariant #3 — Trust the audio / no speculative phrasing

**Statement.** Live audio evidence is authoritative. The co-host reacts to real
detected events, never invents them. Two enforcement layers: a static AST gate
keeps the learn package from computing its own phrase structure, and the
post-hoc slop filter nukes any banned generic-AI phrasing.

**Verify:**

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
  tests/learn/test_no_speculative_phrase.py \
  tests/prompts/test_negative_dict.py \
  tests/state/test_hype_anti_slop.py \
  tests/state/test_coach_anti_slop.py
```

`tests/learn/test_no_speculative_phrase.py` is the Invariant-#3 AST gate: it
walks `src/vibemix/learn/**/*.py` and reddens on any `numpy.fft` / `scipy.signal`
/ `librosa.beat` / `librosa.onset` import — the learn tutor must consume phrase
structure from `state/refresh.py` + `CueAnchor`, never compute "breakdown in 16
beats" the deck never showed.

`prompts/filter.py::filter_for_slop` checks the accumulated LLM text against
`NEGATIVE_REGEX` (63 phrases in `prompts/negative_dict.py`); a match replaces
the whole turn with `<silence/>` and logs `slop_suppressed`.

**Violation looks like.** A learn module importing an FFT/beat-tracking
primitive; the negative dictionary dropping below 40 phrases
(`test_negative_dict_01_at_least_forty_phrases`); a prompt that asks the model
to predict structure ("the drop is coming") instead of citing observed events;
the detector firing on silence or out-of-range BPM
(`test_empty_evidence_silent_state_does_not_fire`).

**Why it matters.** Speculation is hallucination with better grammar. "Trust
the audio" means the co-host only narrates what the detectors actually saw.

## Invariant #1 — Single-writer

**Statement.** Only the state-refresh loop (`state/refresh.py::state_refresh_loop`)
writes `MusicState`. Everything else reads. Learn writes only `LearnState`
(sole writer `learn/runtime.py`); the MIDI listener is the sole writer of
controller state. A second writer races the single source of truth and makes
grounding non-deterministic.

**Verify:**

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
  tests/learn/test_runtime_invariants.py \
  tests/state/test_refresh.py \
  tests/state/test_music_state.py
```

`tests/learn/test_runtime_invariants.py` is the static-grep gate: it reddens on
any `MusicState.<field> =` or `ControllerState.<field> =` assignment under
`src/vibemix/learn/`, and confines `LearnState` writes to `runtime.py`/`state.py`.

**Violation looks like.** A consumer (coach, agent, learn, a new detector)
assigns a `MusicState` field directly instead of reading it; phrase/genre
fields written outside the single-writer block in `state_refresh_loop._tick_once`.

**Why it matters.** If two threads write `MusicState`, the evidence the linter
grounds against can flip mid-turn — and the "real friend" reacts to a state
that never coherently existed.

## Invariant #4 — One socket

**Statement.** The mascot/wizard bus binds `127.0.0.1:8765` only (never two
listeners at once). Debrief uses `8766`. No new `websockets.serve` anywhere
that races the one bus. Constants live in `src/vibemix/audio/constants.py`
(`WS_HOST = "127.0.0.1"`, `WS_PORT = 8765`).

**Verify:**

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q \
  tests/learn/test_no_new_ws_port.py \
  tests/runtime/test_ws_bus.py
```

`tests/learn/test_no_new_ws_port.py` reddens on any non-comment
`websockets.serve` under `src/vibemix/learn/`. The live bus lives in
`runtime/ws_bus.py` (single `IpcRouterBus`/mascot `serve` on `8765`).

**Violation looks like.** A new surface opening its own `websockets.serve` on a
fresh port instead of piggy-backing the `ws_broadcast` producer on `8765`;
hardcoding `8765`/`8766` somewhere instead of importing `WS_PORT`.

**Why it matters.** Two listeners on `8765` is the "VIBEMIX-CORE STOPPED" /
empty-screen class of bug. Reactions broadcast over the bus (`transcript_delta`)
silently vanish if the wrong listener wins the bind.

## Invariant #5 — Idle ≠ fault

**Statement.** `SessionLayout`'s grounding-failure timer runs ONLY while the
co-host is ACTIVE. At idle, `grounded=false` is expected (no music to ground
to) and must read as calm "silent", never flip the deck to a fake "AI SERVICE
OFFLINE" fault with a blank hero.

**Verify** (this is the one TypeScript invariant — vitest, not pytest):

```bash
cd tauri/ui && npm test
# narrow:  cd tauri/ui && npx vitest run tests/session/grounding-failure.spec.ts
```

`tauri/ui/tests/session/grounding-failure.spec.ts` pins it:
`an IDLE co-host never faults on grounded=false` (the empty-screen regression
guard), `after >= 5s of grounded=false on an ACTIVE co-host the deck flips to
fault`, and `screen=denied` is badge-only (audio-only is a valid mode).
`GROUNDING_FAILURE_MS` is 5000.

**Violation looks like.** The fault timer arming at idle (`groundedFalseSinceMs`
non-null on an IDLE mount); the deck showing `data-mode="fault"` with no active
co-host; screen-denied faulting the whole deck.

**Why it matters.** A blank "AI service unreachable" hero on first launch is the
recurring "the app is always broken" bug — it kills the first-run delight that
the GitHub-star goal depends on, while nothing is actually wrong.

---

## Reporting template

State, per invariant you touched: command run, pass/fail, and (on fail) the
offending file:line + the fix. Do not claim "grounded" without the green output.
Full command list, failure signatures, and the lock-step file map:
[references/invariant-checks.md](references/invariant-checks.md).
