# Prompt Composition Contract -- Live Co-Host

_Single named contract for what enters the live co-host prompt per event type._

## Purpose

This doc enumerates every `EventType` the live co-host emits, the evidence fields it carries, which `EVIDENCE_SOURCES` citation tokens it may resolve against, the recall-fragment shape it triggers, whether the diet path applies, and the per-type cooldown that gates re-firing. It is the single named contract any new mood/lens contributor reads BEFORE editing the live prompt path. Reverse-engineering `coach.py` + `event_detector.py` + `evidence_registry.py` to discover the rules each time is the failure mode this doc closes (closes Factor 3 -- "own your context window" -- from the 2026-05-28 humanlayer/12-factor-agents audit).

Scope is the LIVE CO-HOST prompt composition ONLY. The Viber / library prompt surface (the `LibraryToolset` MCP tool grammar consumed by the local Codex agent) lives separately; v10.0 Phases 99 and 100 (HARDEN-RETRY + HARDEN-CLARIFY) own the Viber-side hardening. A future `docs/VIBER-PROMPT-COMPOSITION.md` may land if/when the Viber surface needs an equivalent contract -- that is HARDEN-FUTURE territory, not v10.0 scope.

## Reading Guide

- Quick reference: Composite Event Contract (Sec. 3) -- one row per shipped `EventType`, every column resolves to a single source-of-truth file:line.
- Citation source grammar depth: Citation Source Grammar (Sec. 4, filled by Plan 101-02).
- Recall-fragment depth: Recall-Fragment Shapes (Sec. 5, filled by Plan 101-02).
- Diet-mode depth: Diet-Mode (Sec. 6, filled by Plan 101-02).
- Cooldown table: Per-Event-Type Cooldowns (Sec. 7) -- reproduces `MIN_EVENT_GAP_PER_TYPE` one row per dict key with the inline-comment rationale.
- How to re-verify cites on rebase: Appendix (Sec. 8, filled by Plan 101-03).

## Composite Event Contract

The load-bearing artifact. Every shipped `EventType` emitted by `EventDetector._fire(...)` in `src/vibemix/state/event_detector.py` has exactly one row. The 9-event taxonomy is locked; this doc enumerates the shipped surface and never extends it. Event types are STRING LITERALS at the `_fire(...)` call sites (not an `Enum`).

| EventType                 | Fires at                                  | Cooldown (s)                              | Diet-mode eligible? | Citation sources (may carry)                              |
| ------------------------- | ----------------------------------------- | ----------------------------------------- | ------------------- | --------------------------------------------------------- |
| `KAAN_SPOKE`              | `src/vibemix/state/event_detector.py:239` | 3.0 (via `cooldown_key="MIC"`)            | yes                 | `ev`, `aud`, `mix`, `recall` (see Sec. 4)                 |
| `MANUAL`                  | `src/vibemix/state/event_detector.py:243` | 1.5                                       | no                  | `ev`, `aud`, `mix` (see Sec. 4)                           |
| `TRACK_CHANGE`            | `src/vibemix/state/event_detector.py:273` | 5.0                                       | no                  | `ev`, `aud`, `mix`, `track`, `recall` (see Sec. 4)        |
| `PHASE`                   | `src/vibemix/state/event_detector.py:289` | 10.0                                      | no                  | `ev`, `aud`, `mix`, `recall` (see Sec. 4)                 |
| `LAYER_ARRIVAL`           | `src/vibemix/state/event_detector.py:312` | 10.0                                      | yes                 | `ev`, `aud`, `mix`, `recall`, `exemplar` (see Sec. 4)     |
| `MIX_MOVE`                | `src/vibemix/state/event_detector.py:340` | 14.0                                      | yes                 | `ev`, `aud`, `midi`, `mix`, `recall` (see Sec. 4)         |
| `KEY_CLASH`               | `src/vibemix/state/event_detector.py:383` | 28.0                                      | no                  | `ev`, `key`, `mix` (see Sec. 4)                           |
| `TRANSITION_OPPORTUNITY`  | `src/vibemix/state/event_detector.py:443` | 20.0                                      | no                  | `ev`, `key`, `mix`, `cue` (see Sec. 4)                    |
| `HEARTBEAT`               | `src/vibemix/state/event_detector.py:469` | 45.0 (`HEARTBEAT_SEC`)                    | yes                 | `ev`, `aud`, `mix` (see Sec. 4)                           |

Notes:

- Genre-chain re-emit at `src/vibemix/state/event_detector.py:464` is NOT a new taxonomy entry -- it re-fires whatever `ev.type` the active genre detector returned (`ACID_LINE_ENTRY`, `KICK_SWAP`, `SUB_LAYER_ARRIVAL`, `KICK_DENSITY_SHIFT`, `DISTORTION_CLIMB`, `BREAKDOWN_KICK_KILL`, `REENTRY_KICK_LAND`, `PHRASE_BOUNDARY`). Cooldowns for those types live in the same `MIN_EVENT_GAP_PER_TYPE` dict (Sec. 7).
- "Diet-mode eligible" reproduces the `ACK_ELIGIBLE_EVENTS` frozenset at `src/vibemix/state/coach.py:54`. Only `HEARTBEAT`, `MIX_MOVE`, `LAYER_ARRIVAL`, `KAAN_SPOKE` take the compact-evidence diet path; every other event type uses the full-payload prompt. The `if diet:` dispatch lives at `src/vibemix/state/coach.py:828` and raises `ValueError` on a non-ack event passed with `diet=True` (loud failure on dispatch bugs).
- "Citation sources (may carry)" lists which of the 11 `EVIDENCE_SOURCES` tokens (locked frozenset at `src/vibemix/state/evidence_registry.py:129`) the event MAY cite. The exact body grammar per source and the per-event-type association rationale live in Sec. 4 (Plan 101-02). The 11 sources are: `ev`, `aud`, `midi`, `track`, `screen`, `mix`, `tend`, `key`, `recall`, `exemplar`, `cue`. `screen` and `tend` are populated by sibling subsystems (deck-poller screen-capture / Kaan-profile) and may flow into the prompt on any event when present; they are not gated per event type.
- Recall-fragment family (which event types trigger which template in `recall_fragment_for_event` at `src/vibemix/state/coach.py:158`). The dispatch resolves event-by-event:
  - `TRACK_CHANGE` -> transition-shape template (TRANSITION_SHAPE_RECALL_FRAGMENT_TPL).
  - `MIX_MOVE` -> transition-shape template.
  - `LAYER_ARRIVAL` -> transition-shape template.
  - `PHASE` -> vocabulary template (VOCABULARY_RECALL_FRAGMENT_TPL).
  - `KEY_CLASH`, `TRANSITION_OPPORTUNITY`, `HEARTBEAT`, `KAAN_SPOKE`, `MANUAL` -> empty string (no recall fragment).
  Worked examples per event family land in Sec. 5 (Plan 101-02).

Source-of-truth files for each column (rebuild the table from these if the doc drifts):

- EventType + Fires-at line -> `src/vibemix/state/event_detector.py` (`self._fire(...)` call sites).
- Cooldown seconds -> `src/vibemix/audio/constants.py:77` (`MIN_EVENT_GAP_PER_TYPE`).
- Diet-mode eligibility -> `src/vibemix/state/coach.py:54` (`ACK_ELIGIBLE_EVENTS`).
- Citation sources frozenset -> `src/vibemix/state/evidence_registry.py:129` (`EVIDENCE_SOURCES`).

How to read the table (worked walkthrough on TRACK_CHANGE):

- "Fires at `src/vibemix/state/event_detector.py:273`" -- open the file, line 273 reads `self._fire("TRACK_CHANGE", now, state)` immediately after the new-audible-track / confidence gate at lines 258-271. That is the single point where the TRACK_CHANGE event reaches the prompt path.
- "Cooldown 5.0" -- this is the `MIN_EVENT_GAP_PER_TYPE["TRACK_CHANGE"]` value at `src/vibemix/audio/constants.py:80`. It is the per-type re-fire floor. Note: the 22.0s `EVENT_GLOBAL_MIN_GAP` cross-event-type floor still applies on top, so a TRACK_CHANGE inside 22s of any other event is still suppressed.
- "Diet-mode no" -- TRACK_CHANGE is NOT in `ACK_ELIGIBLE_EVENTS` at `src/vibemix/state/coach.py:54`, so `build_prompt(diet=True)` on a TRACK_CHANGE event raises `ValueError` at `src/vibemix/state/coach.py:828`. The full-payload prompt is always used.
- "Citation sources `ev`, `aud`, `mix`, `track`, `recall`" -- these are the entries from `EVIDENCE_SOURCES` (at `src/vibemix/state/evidence_registry.py:129`) the event MAY cite. `ev` is written by `EventDetector._fire` itself (every fire registers `("ev", event_type, t_session)` at event_detector.py:509); `aud` and `mix` flow from the state-refresh loop; `track` comes from the nowplaying-cli identity at the moment of fire; `recall` may be appended when the strongest survivor from `MemoryRecall.get_latest()` is interpolated into the transition-shape fragment.

## Citation Source Grammar

Source-of-truth: the locked frozenset at `src/vibemix/state/evidence_registry.py:129` (`EVIDENCE_SOURCES`) defines the 11 citation tokens any reaction may emit. The compiled regex at `src/vibemix/state/evidence_registry.py:199` (`EVIDENCE_CITATION_RE`) enforces the EBNF on the wire; the inner-atom alternation at `src/vibemix/state/evidence_registry.py:174` (`_SOURCE_ALT`) is the mirror site that must move in lock-step with the frozenset.

Common EBNF (all 11 sources):

- `citation := '[' atom ( ',' atom )* ']'`
- `atom := <source> ':' <body>`
- `body` is one-or-more chars, no whitespace, no comma, no closing bracket
- Multi-atom citations are comma-joined inside ONE bracket pair (e.g. `[ev:TRACK_CHANGE@123.4,key:A:8A]`); empty `[]` is rejected
- The FIRST `:` separates source from body; inner colons survive as body (this is how `key:A:8A`, `recall:20260520-2200:7`, `exemplar:_packaged:low:track_03`, and `cue:phrase_boundary@45.2` all parse without a grammar change -- see the inline comment block at `src/vibemix/state/evidence_registry.py:139-167`)

Per-source body grammar and citation eligibility (each row cross-references Sec. 3 for the per-EventType view):

| Source     | Body grammar                                  | Introduced (phase)        | Example                                  | Event types that may cite                                                                                          |
| ---------- | --------------------------------------------- | ------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `ev`       | `<EVENT_TYPE>@<t_session>`                    | v4 baseline               | `[ev:TRACK_CHANGE@123.4]`                | Every event -- `EventDetector._fire` writes `("ev", event_type, t_session)` at `src/vibemix/state/event_detector.py:509` on every fire |
| `aud`      | `<audio-domain key>`                          | v4 baseline               | `[aud:rms@123.4]`                        | Any event surfacing audible-deck buffers (TRACK_CHANGE, PHASE, LAYER_ARRIVAL, MIX_MOVE, HEARTBEAT, KAAN_SPOKE, MANUAL, plus genre-chain re-emits per Sec. 3 notes) |
| `midi`     | `<controller-msg key>`                        | v4 baseline               | `[midi:fader_a@123.4]`                   | MIX_MOVE primarily; any event that consumed a MIDI move from the controller decoder thread                          |
| `track`    | `<track identity key>`                        | v4 baseline               | `[track:nowplaying@123.4]`               | TRACK_CHANGE primarily; any event with non-empty nowplaying identity at fire time                                   |
| `screen`   | `<screen-watcher key>`                        | v4 baseline               | `[screen:deck_a@123.4]`                  | Any event whose state.screen_state is populated by the deck-poller subsystem (not gated per event type)             |
| `mix`      | `<mix-state key>`                             | v4 baseline               | `[mix:last_move@123.4]`                  | Most events -- mix-state flows from the state-refresh loop and is populated for every non-cold turn                 |
| `tend`     | `<tendency / profile key>`                    | v4 baseline               | `[tend:peak_hour@123.4]`                 | Any event when long-term Kaan-profile data is loaded (not gated per event type)                                     |
| `key`      | `<deck> ':' <camelot>` (deck in `{A,B,C,D}`, camelot in `1A..12B`) | Phase 59 (DECK-03)        | `[key:A:8A]`                             | KEY_CLASH primarily; TRANSITION_OPPORTUNITY when both decks have detected keys; TRACK_CHANGE when the new audible deck has a detected key |
| `recall`   | `<record_id>` (inner colon survives, e.g. session-stamp `:` index) | Phase 65 (RECALL-01)      | `[recall:20260520-2200:7]`               | TRACK_CHANGE, MIX_MOVE, LAYER_ARRIVAL via `TRANSITION_SHAPE_RECALL_FRAGMENT_TPL` at `src/vibemix/state/coach.py:109`; PHASE via `VOCABULARY_RECALL_FRAGMENT_TPL` at `src/vibemix/state/coach.py:141`. See Sec. 5 |
| `exemplar` | `<track_id>` (library or packaged path, inner colons survive)      | Phase 93 (EXEMPLAR-05)    | `[exemplar:library:Marlon-Atlas]` or `[exemplar:_packaged:low:track_03]` | LAYER_ARRIVAL primarily; tutor-mode reactions emitting library-grounded exemplar callbacks                          |
| `cue`      | `<anchor_id>` (e.g. `<label>@<t>`)                                 | Phase 96 (CURR-3.07)      | `[cue:phrase_boundary@45.2]` or `[cue:drop@180.0]` | TRANSITION_OPPORTUNITY primarily; any count-in / phrase-prediction reaction grounded against a CueAnchor written by `state/refresh.py` before the LLM emits the cite |

Schema-mirror discipline (cite `src/vibemix/state/evidence_registry.py:126-128`): `EVIDENCE_SOURCES` is the source-of-truth. Three mirror sites must move in the SAME commit:

- `_SOURCE_ALT` at `src/vibemix/state/evidence_registry.py:174` (the regex alternation)
- `CITATION_GRAMMAR_BLOCK` in `src/vibemix/prompts/matrix.py` (the prompt-side grammar block)
- `_build_citation_strip` in `src/vibemix/agent/dj_cohost.py:181` (the wire-side stripper)

A new source added to the frozenset without joining `_SOURCE_ALT` is silently uncitable: the regex never matches, the linter never validates, and a fabricated `[<newsource>:<id>]` rides through un-stripped. The recall / exemplar / cue introductions all documented this discipline inline as a precedent (see `evidence_registry.py:144-167`).

Asymmetry (intentional, do NOT "fix"): `src/vibemix/memory/ingest.py` keeps an 8-source alternation -- `recall`, `exemplar`, `cue` are RETRIEVAL-time only, never ingest-time. A stored past reaction never cited `recall`, `exemplar`, or `cue` itself (`cue` is sampled from CueAnchor at narration time, not at ingest), so the ingest-time extractor must not whitelist them. Cited from the comment block at `src/vibemix/state/evidence_registry.py:169-173`.

## Recall-Fragment Shapes

Conditional-append seam: `recall_frag = recall_fragment_for_event(ev, recall_moments)` at `src/vibemix/state/coach.py:849`, immediately before the full-prompt return at `src/vibemix/state/coach.py:850`. The dispatch helper itself lives at `src/vibemix/state/coach.py:158` (`recall_fragment_for_event`). Cold-path falsy gate at `src/vibemix/state/coach.py:228` returns `""` when `recall_moments` is `None` or `[]` -- the v5.0 byte-identity floor every existing `tests/state/test_coach.py` golden depends on.

Branch order in `recall_fragment_for_event` (cited from `src/vibemix/state/coach.py:238-249`):

- `TRACK_CHANGE`, `MIX_MOVE`, `LAYER_ARRIVAL` -> transition-shape template (TRACK_CHANGE is in BOTH gates per the inline comment at `src/vibemix/state/coach.py:183-188`; transition wins by being listed FIRST -- transition is more concrete than a vocabulary echo on a track flip)
- `PHASE` -> vocabulary template
- All other event types (`KAAN_SPOKE`, `MANUAL`, `HEARTBEAT`, `KEY_CLASH`, `TRANSITION_OPPORTUNITY`) -> `""` returned, no fragment appended

Only the STRONGEST survivor's `record_id` is interpolated (cited from `src/vibemix/state/coach.py:234`: `strongest = recall_moments[0]`). Phase 65's `cosine_topk` returns survivors sorted DESC by score, so index 0 is the highest match; weaker survivors still appear in the `FROM A PAST SESSION` block of `evidence_line` for pattern-matching, but only the strongest is named for the `[recall:<record_id>]` citation. This is the structural max-1-per-turn cap.

### Transition-shape recall

Template constant: `TRANSITION_SHAPE_RECALL_FRAGMENT_TPL` at `src/vibemix/state/coach.py:109`.

Shape (prose summary -- the template body is a Python string literal at `src/vibemix/state/coach.py:109-126`, NOT reproduced here in full): a past-tense callback line referencing a transition-shaped past moment that lines up with the live audio, citing exactly `[recall:<record_id>]` once. The DJ hears "that blend sat longer than the last time" or "killed the bass earlier this time around" -- a delta between the past signature and the live moment, not a description of the past in isolation.

Hard rules (quoted verbatim from `src/vibemix/state/coach.py:119-126` -- the template body):

> Hard rules: cite [recall:{record_id}] EXACTLY ONCE (the registry validates it; a fabricated id strips the whole turn); do NOT invent a past moment, paraphrase the past signature, or describe it as live; do NOT recommend a NEXT track or move (no 'try X next time'); do NOT claim a tendency ('you usually do', 'you always') -- narrate THIS one compared to THAT one. If the past moment doesn't match, OMIT the callback entirely -- your normal reaction is the floor.

Worked examples:

- TRACK_CHANGE with `recall_moments=[Record(record_id="20260520-2200:7", ...)]` -> fragment appended; tail of the prompt reads "... your normal reaction is the floor." with `[recall:20260520-2200:7]` cited once. Wire-side validation at `src/vibemix/agent/dj_cohost.py:181` (`_build_citation_strip`) confirms the id resolves in the registry; a fabricated id strips the whole turn (the anti-poisoning posture documented at `src/vibemix/state/coach.py:74-77`).
- MIX_MOVE with same fragment shape -- transition-shape branch matches MIX_MOVE just as it does TRACK_CHANGE (`src/vibemix/state/coach.py:238`).
- LAYER_ARRIVAL with same fragment shape -- third event type in the transition-shape tuple at `src/vibemix/state/coach.py:238`.
- TRACK_CHANGE with `recall_moments=None` or `[]` -> falsy gate at `src/vibemix/state/coach.py:228` returns `""`; nothing appended; output is byte-identical to the v5.0 baseline.

### Vocabulary/register recall

Template constant: `VOCABULARY_RECALL_FRAGMENT_TPL` at `src/vibemix/state/coach.py:141`.

Shape (prose summary): echo the DJ's own past phrasing in the DJ's own register, citing exactly `[recall:<record_id>]` once. The anti-paraphrase discipline is baked into the template body: "speak in the same register, not Gemini-paraphrased" -- explicit framing against the failure mode where Gemini describes the DJ's voice instead of echoing it. The inline comment at `src/vibemix/state/coach.py:135-140` names this as Pitfall 4 from 66-RESEARCH.md.

Hard rules (quoted verbatim from `src/vibemix/state/coach.py:149-155` -- the template body):

> Hard rules: cite [recall:{record_id}] EXACTLY ONCE; do NOT invent a past phrasing; do NOT claim it's a habit ('you always', 'you tend to'); do NOT recommend a next move. If your live reaction wouldn't naturally echo the past, OMIT the callback -- a forced echo is the failure mode this phase guards.

Worked example: PHASE event with `recall_moments=[Record(record_id="20260520-2200:7", ...)]` and a live moment whose natural reaction lines up with the past signature -> fragment appended; output cites `[recall:20260520-2200:7]` once and stays in the DJ's voice. Same falsy-gate behavior for cold `recall_moments`.

### Structural pins

- The diet path SKIPS the recall fragment entirely. Cited from the build_prompt docstring at `src/vibemix/state/coach.py:811-813`: "the diet branch intentionally skips the recall block -- diet events are ACK_ELIGIBLE (incl. HEARTBEAT) and are never retrieval events." Mechanically, the diet branch at `src/vibemix/state/coach.py:826-833` returns before reaching the `recall_fragment_for_event` call at `src/vibemix/state/coach.py:849`.
- Registry strict-subset enforcement: `_build_citation_strip` at `src/vibemix/agent/dj_cohost.py:181` validates every `[recall:<id>]` against `EvidenceRegistry`. A fabricated id strips the whole turn -- the Phase 65 anti-poisoning linter posture cited at `src/vibemix/state/coach.py:75-77` and the comment block at `src/vibemix/state/evidence_registry.py:146-148`.
- Byte-identity contract: the leading space at the start of each template is LOAD-BEARING (`src/vibemix/state/coach.py:98-101`) -- `build_prompt` concatenates the fragment directly onto the task tail with no separator, so the leading space is the only delimiter. Preserve it exactly if editing a template.

## Diet-Mode

Eligibility gate: `ACK_ELIGIBLE_EVENTS` frozenset at `src/vibemix/state/coach.py:54`, containing exactly four event types: `HEARTBEAT`, `MIX_MOVE`, `LAYER_ARRIVAL`, `KAAN_SPOKE`. Dispatch branch: `if diet:` at `src/vibemix/state/coach.py:828`.

Diet mode is OPT-IN by caller. The default at `src/vibemix/state/coach.py:799` is `diet: bool = False`, the v4-byte-identical full-prompt path. Passing `diet=True` on a non-ack event raises `ValueError` at `src/vibemix/state/coach.py:828-830` -- dispatch bugs fail loud at the call site rather than silently producing a compressed prompt for an event that needs the full payload to ground a substantive reaction. The comment block at `src/vibemix/state/coach.py:50-53` names the contract: PHASE, TRACK_CHANGE, MANUAL, KEY_CLASH, TRANSITION_OPPORTUNITY, and the genre-chain re-emit types "truly need the 18s audio window + corpus footer + history fields" to ground; only the four ack events take the diet path.

### What diet strips

Cited from the build_prompt docstring at `src/vibemix/state/coach.py:815-821` and the branch implementation at `src/vibemix/state/coach.py:826-833`:

- Uses `_evidence_line_compact(ev.state)` (the 5-field compact assembler) at `src/vibemix/state/coach.py:833` instead of the full `AICoach.evidence_line(...)` call -- the compact path is defined at `src/vibemix/state/coach.py:533` and excludes the registry corpus footer and the recall block by construction
- Omits the `| event=<TYPE>` tag (the full path includes it via the f-string at `src/vibemix/state/coach.py:850`: `f"[{evidence} | event={ev.type}] {task}{recall_frag}"`; the diet return at `src/vibemix/state/coach.py:833` is `f"[{evidence}] {task}"` -- no `event=` tag)
- Omits the evidence-corpus footer (the `evidence_corpus[ev=N,aud=M,mix=K]` footer assembled inside `AICoach.evidence_line` from `registry_snapshot`); the compact path at `src/vibemix/state/coach.py:533` never reads a `registry_snapshot` and never assembles a footer
- Skips the recall-fragment conditional append at `src/vibemix/state/coach.py:849`; the diet branch returns at `src/vibemix/state/coach.py:833` before reaching that call. The recall fragment is the load-bearing component the diet path strips -- cited as intentional at `src/vibemix/state/coach.py:811-813` ("diet events are ACK_ELIGIBLE incl. HEARTBEAT, never retrieval events")

### Why diet exists

TTFT (time-to-first-token) budget on ack-eligible event classes. Cited from `src/vibemix/state/coach.py:818-819`: "Saves >=500ms TTFT on the four ack-eligible event classes (HEARTBEAT, MIX_MOVE, LAYER_ARRIVAL, KAAN_SPOKE)."

The ack events are short, frequent, and structurally compressible -- a HEARTBEAT does not benefit from a registry corpus footer the way a TRACK_CHANGE does. The compressed prompt lands a fast vocal acknowledgment via the ack-bank fallback in `src/vibemix/agent/dj_cohost.py` without the full reasoning-grounded reaction the heavy events get. The full-prompt path is preserved for every other event type so substantive reactions stay grounded.

The `ValueError` at `src/vibemix/state/coach.py:828-830` is the dispatch-bug guard: a caller that accidentally passes `diet=True` on TRACK_CHANGE (an event that needs the full payload) does NOT silently degrade to a compressed prompt -- it raises immediately, surfacing the bug at the call site instead of producing a quietly-worse reaction.

## Per-Event-Type Cooldowns

Reproduces `MIN_EVENT_GAP_PER_TYPE` from `src/vibemix/audio/constants.py:77` one row per dict key. The third column quotes the inline-comment rationale preserved alongside the value in source.

| Key                       | Seconds       | Source-of-truth comment                                                                                                  |
| ------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `TRACK_CHANGE`            | 5.0           | Plan 40-04 -- was 6.0; v4 2026-05-11 baseline                                                                            |
| `PHASE`                   | 10.0          | Plan 40-04 -- was 18.0; v4 2026-05-11 baseline                                                                           |
| `LAYER_ARRIVAL`           | 10.0          | Plan 40-04 -- was 16.0; v4 2026-05-11 baseline                                                                           |
| `MIX_MOVE`                | 14.0          | Plan 40-04 -- was 20.0; v4 2026-05-11 baseline                                                                           |
| `HEARTBEAT`               | 45.0          | Plan 40-04 -- flows from `HEARTBEAT_SEC` (45.0)                                                                          |
| `MIC`                     | 3.0           | (v4 baseline -- KAAN_SPOKE cooldown bucket; KAAN_SPOKE fires via `cooldown_key="MIC"` at event_detector.py:239)          |
| `MANUAL`                  | 1.5           | (v4 baseline -- bypasses music-presence gate for manual trigger)                                                         |
| `KICK_SWAP`               | 14.0          | Phase 17 SENSE-12 -- KICK_SWAP slightly faster than LAYER_ARRIVAL; main "moment" worth catching                          |
| `SUB_LAYER_ARRIVAL`       | 16.0          | Phase 17 SENSE-12 -- mirrors LAYER_ARRIVAL (its bass-side analog)                                                        |
| `KICK_DENSITY_SHIFT`      | 18.0          | Phase 17 SENSE-12 -- mirrors PHASE (structural shift, not a layer arrival)                                               |
| `BREAKDOWN_KICK_KILL`     | 20.0          | Plan 17-03 -- same 20s as MIX_MOVE (structural moment, not a fast tap)                                                   |
| `REENTRY_KICK_LAND`       | 12.0          | Plan 17-03 -- shorter (paired with kill within `KICK_REENTRY_MAX_AGE_S = 30s`)                                           |
| `PHRASE_BOUNDARY`         | 24.0          | Plan 17-04 SENSE-14 -- prevents same-phrase double-fire; bar-count is the meaningful unit (wall-clock floor)             |
| `DISTORTION_CLIMB`        | 6.0           | Phase 30 SENSE-17 -- Hard Tek climbs evolve fast; tight to avoid swallowing a real moment                                |
| `ACID_LINE_ENTRY`         | 8.0           | Phase 30 SENSE-18 -- Hard Tek genre-specific; tight relative to PHASE/MIX_MOVE                                           |
| `KEY_CLASH`               | 28.0          | Phase 59 DECK-04 -- long gap; harmonic clash persists; re-arm only after it clears+recurs (~25-30s)                      |
| `TRANSITION_OPPORTUNITY`  | 20.0          | Phase 59 DECK-04 -- medium; fires at the moment a blend COULD start, not continuously                                    |

Notes:

- Every cooldown is gated by `EventDetector._cooldown_ok` in `src/vibemix/state/event_detector.py` (the `(now - last) > gap AND (now - last_event_at) > EVENT_GLOBAL_MIN_GAP` check). The `EVENT_GLOBAL_MIN_GAP = 22.0` floor at `src/vibemix/audio/constants.py:58` is the cross-event-type lower bound -- any event type with a `MIN_EVENT_GAP_PER_TYPE` value BELOW 22.0 (e.g. `TRACK_CHANGE` at 5.0) is still subject to the 22s global floor between any two reactions. The global floor exists so the co-host does not talk back-to-back -- Kaan's 2026-05-21 live-drive tuning.
- `KAAN_SPOKE` is the externally visible event name, but its cooldown bookkeeping uses the `MIC` bucket (`cooldown_key="MIC"` at event_detector.py:239). This is intentional: v4 cooldown bucket name preserved; event-type name exposed for prompt grammar + Phase 20 linter.
- An event type not present in `MIN_EVENT_GAP_PER_TYPE` falls back to `EVENT_GLOBAL_MIN_GAP` (22.0) via the `.get(ev_type, EVENT_GLOBAL_MIN_GAP)` default in `_cooldown_ok`.

## Appendix: How to Grep-Verify This Doc

Line numbers drift. Every section above cites source by `path.py:line`; the value of this doc as a contract depends on every cite resolving to the line the prose says it does. The protocol below is the write-time gate (REQ-CONTRACT-05) and the re-verification recipe for future contributors on rebase. CI smoke check is explicitly OPTIONAL per REQ-05 and not blocking -- this appendix is the canonical executable check.

Run on rebase, after any `src/vibemix/state/` refactor that touches `coach.py`, `event_detector.py`, or `evidence_registry.py`, and after any cooldown tuning in `src/vibemix/audio/constants.py`. If any cite drifts, fix the line number in this doc BEFORE landing the source change so the contract stays self-consistent.

### Loop 1: every `path.py:line` cite resolves to a non-empty line

The doc-wide sweep. Extracts every `path.py:N` (and `path.py:N-M` range) token, resolves the path against the repo root, and flags any cite whose target line is blank, out-of-bounds, or missing. Run from the repo root. Python is used rather than `awk` because it gives deterministic newline handling and range support without shell-quoting traps.

```bash
python3 - <<'PYEOF'
import re, pathlib
doc = pathlib.Path("docs/PROMPT-COMPOSITION.md").read_text()
pat = re.compile(r"([a-zA-Z0-9_/.-]+\.py):(\d+)(?:-(\d+))?")
def resolve(p):
    if p.startswith(("src/", "docs/", "tauri/", "tests/")):
        return p
    # Bare filenames (e.g. event_detector.py:239) resolve under src/vibemix/state/
    # because that is where the doc's load-bearing cites live.
    return f"src/vibemix/state/{p}"
stale = []
for m in pat.finditer(doc):
    path, start = m.group(1), int(m.group(2))
    end = int(m.group(3)) if m.group(3) else start
    fp = pathlib.Path(resolve(path))
    if not fp.exists():
        stale.append(f"FILE_MISSING: {path}:{start}-{end}"); continue
    lines = fp.read_text().splitlines()
    for L in range(start, end + 1):
        if L < 1 or L > len(lines):
            stale.append(f"OOB: {path}:{L} (file has {len(lines)} lines)"); break
        if not lines[L - 1].strip():
            stale.append(f"BLANK: {path}:{L}"); break
print(f"stale={len(stale)}")
for s in stale: print(" ", s)
PYEOF
```

Expected output: `stale=0`. Any line beginning with `STALE:`, `OOB:`, `BLANK:`, or `FILE_MISSING:` is a cite that needs fixing.

### Loop 2: anchor-symbol grep -- catches semantic drift, not just renumbering

A line cite is only useful if it still points to the symbol the prose names. Loop 1 confirms the line is non-empty; Loop 2 confirms it carries the expected symbol. Run these one at a time and confirm each returns the expected line range -- if the line number drifted but the symbol is intact, update the cite in the doc. If the symbol moved or renamed, that is a structural source change and may require a doc rewrite, not just a line-number bump.

```bash
grep -n 'EVIDENCE_SOURCES: frozenset\[str\]'        src/vibemix/state/evidence_registry.py    # expect line ~129
grep -n 'EVIDENCE_CITATION_RE'                      src/vibemix/state/evidence_registry.py    # expect ~199 (compiled regex)
grep -n '_SOURCE_ALT'                               src/vibemix/state/evidence_registry.py    # expect ~174 (inner-atom alternation)
grep -n 'ACK_ELIGIBLE_EVENTS: frozenset\[str\]'     src/vibemix/state/coach.py                # expect ~54
grep -n 'def recall_fragment_for_event'             src/vibemix/state/coach.py                # expect ~158
grep -n 'TRANSITION_SHAPE_RECALL_FRAGMENT_TPL: str' src/vibemix/state/coach.py                # expect ~109
grep -n 'VOCABULARY_RECALL_FRAGMENT_TPL: str'       src/vibemix/state/coach.py                # expect ~141
grep -n 'def build_prompt'                          src/vibemix/state/coach.py                # expect ~796
grep -n 'def _evidence_line_compact'                src/vibemix/state/coach.py                # expect ~533
grep -nF 'if diet:'                                 src/vibemix/state/coach.py                # expect ~826 (diet dispatch branch)
grep -n 'MIN_EVENT_GAP_PER_TYPE: dict'              src/vibemix/audio/constants.py            # expect ~77
grep -n 'EVENT_GLOBAL_MIN_GAP'                      src/vibemix/audio/constants.py            # expect ~58 (cross-event-type floor)
grep -nF 'self._fire('                              src/vibemix/state/event_detector.py       # expect 10 hits (9 unique event types + 1 genre-chain re-emit)
grep -n '_build_citation_strip'                     src/vibemix/agent/dj_cohost.py            # expect ~181 (wire-side stripper)
```

### If a cite has drifted

1. If only the line number changed (the symbol is intact at a nearby line per Loop 2): bump the cite in this doc to the new line number. Do not relax it to a symbol-only reference -- the precise jump-target is the doc's value.
2. If the symbol moved between files or was renamed: re-grep the symbol across `src/vibemix/` to find its new home, then update both the path and the line in the cite. Confirm with Loop 1 that the new cite resolves.
3. If the symbol was deleted: that is a structural source change and the surrounding doc prose likely needs more than a cite fix. Re-read Sections 1-7 around the deleted reference and audit whether the contract this doc enumerates still holds.

Do not commit a doc update that fails Loop 1. The acceptance floor is `stale=0` against current source at write-time.
