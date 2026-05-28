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
- "Diet-mode eligible" reproduces the `ACK_ELIGIBLE_EVENTS` frozenset at `src/vibemix/state/coach.py:54`. Only `HEARTBEAT`, `MIX_MOVE`, `LAYER_ARRIVAL`, `KAAN_SPOKE` take the compact-evidence diet path; every other event type uses the full-payload prompt. The `if diet:` dispatch lives at `src/vibemix/state/coach.py:824` and raises `ValueError` on a non-ack event passed with `diet=True` (loud failure on dispatch bugs).
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
- "Diet-mode no" -- TRACK_CHANGE is NOT in `ACK_ELIGIBLE_EVENTS` at `src/vibemix/state/coach.py:54`, so `build_prompt(diet=True)` on a TRACK_CHANGE event raises `ValueError` at `src/vibemix/state/coach.py:826`. The full-payload prompt is always used.
- "Citation sources `ev`, `aud`, `mix`, `track`, `recall`" -- these are the entries from `EVIDENCE_SOURCES` (at `src/vibemix/state/evidence_registry.py:129`) the event MAY cite. `ev` is written by `EventDetector._fire` itself (every fire registers `("ev", event_type, t_session)` at event_detector.py:509); `aud` and `mix` flow from the state-refresh loop; `track` comes from the nowplaying-cli identity at the moment of fire; `recall` may be appended when the strongest survivor from `MemoryRecall.get_latest()` is interpolated into the transition-shape fragment.

## Citation Source Grammar

_TODO 101-02_ -- body grammar per `EVIDENCE_SOURCES` entry (11 sources: `ev`, `aud`, `midi`, `track`, `screen`, `mix`, `tend`, `key`, `recall`, `exemplar`, `cue`) with concrete examples and which event types may cite which sources.

## Recall-Fragment Shapes

_TODO 101-02_ -- enumerate the per-event-family recall templates. Transition-shape template (triggered by TRACK_CHANGE, MIX_MOVE, LAYER_ARRIVAL) at `src/vibemix/state/coach.py:109` (`TRANSITION_SHAPE_RECALL_FRAGMENT_TPL`); vocabulary template (triggered by PHASE) at `src/vibemix/state/coach.py:141` (`VOCABULARY_RECALL_FRAGMENT_TPL`); empty-string return for HEARTBEAT, KAAN_SPOKE, MANUAL, KEY_CLASH, TRANSITION_OPPORTUNITY (no recall fragment). All dispatched by `recall_fragment_for_event` at `src/vibemix/state/coach.py:158`. Plan 101-02 lands the per-template body grammar + a worked example per event family (TRACK_CHANGE worked example, MIX_MOVE worked example, LAYER_ARRIVAL worked example, PHASE worked example).

## Diet-Mode

_TODO 101-02_ -- what triggers the diet path, what gets stripped vs full-prompt, why (TTFT budget on ack-eligible events). Cross-referenced to `src/vibemix/state/coach.py:54` (`ACK_ELIGIBLE_EVENTS`) and `src/vibemix/state/coach.py:824` (`if diet:` dispatch).

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

_TODO 101-03_ -- shell loop showing `grep -n` invocations to re-verify every file:line citation in this doc resolves on current source. Run on rebase / after `src/vibemix/state/` changes.
