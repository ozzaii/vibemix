# Handoff: Viber and Gemini Live Deck Context Work Done

**Date:** 2026-05-29  
**Status:** implemented and test-covered for prompt, socket, browser, and guard
paths; not physically proven with live DJ audio/deck rows yet.  
**Scope:** make Viber and Gemini understand "deck one here / deck two here" as
grounded, labeled context; feed the LLM provenance/freshness/cache/history
boundaries before it reasons; keep Gemini audio context cheap; and preserve
historical move-to-audio-change memory without upgrading it into proof. The
"great transition from one deck" failure is one symptom, not the goal.

## Boundary

This work intentionally stayed out of the Viber MCP/tool orchestration lane.
The separate "Map Viber agent + MCP tool flow" session can evolve tool routing,
schemas, and agent flow without needing to rewrite these contracts.

This work did not run GSD and did not touch the Learn beginner-path suites.

## What Changed

### 1. Deck one / deck two reference context

Added a shared live deck context layer in `src/vibemix/state/deck_context.py`.
It renders:

- `deck_lanes_context[...]`: detailed lane map for A/B with identity,
  controller route, EQ/filter/volume/play posture, and aliases
  `deck1:A,deck2:B`.
- `deck_reference_context[...]`: plain deck-one/deck-two packet that says P1 is
  the global mix, per-deck audio is not attached, and isolated decks are false.
- `deck_source_context[...]`: provenance ladder for deck identity. Live deck
  identity comes from `MusicState.deck_state`; robust resolution is
  now-playing/controller attribution into the library cache. Live Rekordbox
  `master.db` is not read, and event XML is diagnostic only.
- `deck_audio_context[...]`: explains that the heard audio is the global
  master/booth mix, not isolated deck stems.
- `audio_window_context[...]`: time-aligned P1 map for old/current/action/future
  context, with `P1=master_global_mix`, `P1_heard=true`,
  `deckA_audio=not_attached`, `deckB_audio=not_attached`,
  `per_deck_audio=structured_text_only`, and
  `duplicate_audio=same_master_not_deck_split`.

### 2. Claim policy and unsupported outcome guard

The shared guard now treats "great transition" as one example of a broader
unsupported multi-deck outcome class. It also covers blend, switch, segue,
handoff, bridge, layer, incoming/other-deck claims, and move-quality verdicts
when the evidence only proves a one-deck move or an audio delta.

Policy shape:

- No resolved decks: block transition/outcome claims.
- One resolved deck: block multi-deck transition/outcome claims.
- Two decks but single audible route: watch-only, no verdict.
- Two resolved decks with cross-deck support: candidate language only, not
  "good/clean/successful" praise.

### 3. Gemini P1 audio arrangement

`src/vibemix/agent/dj_cohost.py` now places an `AUDIO CONTEXT MAP FOR ATTACHED
P1` immediately before the Gemini audio Part label.

That local map repeats the bounded live deck/audio facts and the feed contract
beside the audio Gemini is about to hear:

- `context_feed_contract[...]`: labels source/provenance, volatile vs cacheable
  fields, history-as-comparison, TTL, and the cheap per-turn cost shape
- `audio_part_context[...]`: labels the actual Gemini Parts. P1 is current live
  global mix; optional P2 can be Kaan/user mic; optional P2/P3 can be source
  lookahead; none of these Parts are isolated deck stems or transition verdicts.
- deck context and compact lane map
- deck source/provenance map
- mixer posture
- global-mix audio contract
- time-aligned audio window
- recent move, deck-change, and move-effect context
- live evidence refs
- current claim policy

The direct Gemini path now forces a safe `audio_window_context[...]` even when
deck state is cold, so a blank/cold P1 prompt still says the model is hearing a
global mix and must not infer isolated decks.

Latest focused verification for this Part-label contract:

- `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  - 94 passed.
- `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  - 191 passed.
- `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/agent/dj_cohost.py tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  - passed.

### 4. Viber prompt and browser bridge

`src/vibemix/library/codex_curate.py`, `src/vibemix/__main__.py`,
`tauri/ui/src/library/api.ts`, and `tauri/ui/src/library/index.ts` now preserve
and normalize the same live context packet for Viber chat.

Important behavior:

- Raw `audio_window_context[...]` is accepted only if it contains the required
  master-mix, no-stems, lane-alias, and time-alignment atoms.
- Bad or context-poor raw audio-window text is dropped; Python recomputes a safe
  prompt fence from current live state.
- Explicit empty `deck_state`, `deck="none"`, or disconnected mixer frames clear
  stale deck identity instead of carrying old proof forward.
- `live_evidence.mix` keeps an 8-item evidence cap; `live_evidence.refs` keeps a
  9-item ref cap so one MIDI move plus eight mix atoms can coexist.
- Priority keeps MIDI, deck lanes/reference/source, transition gates,
  second-deck identity, `move_scope`, and audio/move deltas ahead of lower-value
  raw route atoms.
- Viber receives `context_feed_contract[surface=viber_text ...]` ahead of the
  deck packets, so Codex reads live labels, provenance, freshness, history, and
  cache/static-vs-volatile boundaries before reasoning.

### 5. Runtime websocket producer

`src/vibemix/runtime/ws_bus.py` now emits the bounded deck context and
`live_evidence` from the producer side. Tests pin the cold controller case:
connected A/B posture with empty deck rows emits `transition_block=no_resolved_decks`,
`second_deck_identity=blocked`, deck1/deck2 reference atoms, and source atoms
with `src_none`.

### 6. Proof readiness and live-context CLI

`vibemix library live-context` samples the live socket and renders exactly what
Viber would receive.

`--require-proof` now checks for:

- frames and flat deck frames
- live-context schema v2 plus advertised structured capabilities
- resolved/citable deck rows with trusted source provenance
- rendered lane/reference/source/audio context
- structured `deck_source_status` JSON diagnostics
- connected A/B controller posture
- recent controller move
- observed master audio
- structured `audio_window_map` JSON for the P1 old/current/action/future map
- bounded `audio_delta`
- structured live evidence and transition block/watch/candidate gate
- citable deck lane/reference/source atoms with concrete route tiers

The proof gate distinguishes prompt safety from physical proof. A forced safe
`audio_window_context[...]` can protect the prompt, but it does not complete the
physical proof unless backed by trusted raw context or live signals. It now also
requires the structured lanes, so a string-only prompt fence cannot masquerade
as a fully LLM-aware proof packet.

The flat live socket now advertises `live_context_schema_version=2` plus
`live_context_capabilities`. The proof CLI checks those before trusting a run as
new enough for structured source/audio lanes. A live process started before
this change now fails with a clear stale-capability blocker instead of only
showing absent fields. The Library UI normalizer preserves the same schema and
capability receipt when forwarding live context into Viber chat. Viber's prompt
now renders it as `live_context_transport[...]`, explicitly labeled as transport
metadata and not musical evidence.

### 7. Historical move context

Runtime event rows and memory signatures now carry deck reference/source/audio
window context plus move/audio-delta signatures. They also carry
`context_feed_contract[...]`, so historical records preserve whether their
fields were volatile live labels, cacheable/static prompt material, or
past-session comparison memory. Viber and Gemini can compare a current
knob/fader move to past move-to-sound-change memories, but the rendered memory
is fenced as past-session comparison, not current live proof.

Old or unsafe memory snippets are sanitized before prompt use:

- attached/isolated deck-stem claims are omitted
- stale "great transition" type spoken claims are omitted unless they are honest
  self-corrections
- copied bracket citations are stripped

## Main Files

- `src/vibemix/state/deck_context.py`
- `src/vibemix/state/coach.py`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/runtime/ws_bus.py`
- `src/vibemix/runtime/coach.py`
- `src/vibemix/memory/ingest.py`
- `src/vibemix/memory/retrieval.py`
- `src/vibemix/library/codex_curate.py`
- `src/vibemix/__main__.py`
- `tauri/ui/src/library/api.ts`
- `tauri/ui/src/library/index.ts`
- `tauri/src-tauri/src/library_cmds.rs`
- `tauri/src-tauri/src/ws_client.rs`

## 2026-05-29 Viber Chat Mode Fix

Kaan surfaced a real Library UI failure: a request like
`find me dark rolling hypnotic techno` created grounded library artifacts, but
the visible Viber reply was a live-deck correction about unresolved decks and
transition evidence. The deep issue was prompt/result routing, not the
transition word itself: Viber attached live context to every chat turn and then
let the result-boundary live guard replace a library/crate answer with a live
proof correction.

The Codex Viber path now classifies attached live context per turn:

- `active_live_context` for current/live/deck/move questions such as
  `was that a transition?`, `what happened?`, or `did that low cut fix it?`
- `silent_guard` for crate/search/vibe/playlist/set-building turns such as
  `find me dark rolling hypnotic techno`

In `silent_guard`, the live packet remains available as a safety rail, but the
prompt explicitly forbids visible `live_context`, `claim_policy`, resolved-deck,
evidence-gate, or live-read correction language. The result boundary also
suppresses an unprompted live correction on library requests and replaces it
with the grounded library outcome when tools/track ids/playlist artifacts exist.

Tool calls were already surfaced through the Codex MCP tool tape:
`tool_events.jsonl` -> Python `[viber-tool] ...` stderr lines -> Rust
`library://viber-tool` -> UI chat tool rows, plus final `tool_trace`. The UI
does not and should not expose private model chain-of-thought/reasoning; the
inspectable surface is the tool trace plus a concise rationale/artifact.

Verification:

- `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  - 84 passed.
- `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py`
  - passed.

## 2026-05-29 Viber Live Proof Receipt In Chat

The deterministic live-reply verifier is now wired into the actual Viber chat
result, not only available as a side CLI. When `library chat` receives live
context, `CodexChatResult.to_dict()` can include `live_verification` with:

- final reply pass/fail
- claim policy (`blocked`, `watch_not_claim`, `candidate_not_verdict`, etc.)
- transport freshness (`fresh_schema_v2` vs stale/pre-schema)
- move-grade allowance/seen count
- internal guard/correction diagnostics for tests and audit

The Library UI normalizes this receipt into product language. The visible side
rack renders a `live proof` row with calm states such as `fresh`, `not armed`,
`needs proof`, `verdict held`, and `checked`. It does not show raw internal
labels such as `live_reply_verify`, `guard`, `live_context_required`, or
`unsupported_live_outcome_claim`. If there are no playlist/export artifacts, the
artifact panel still shows a compact `live proof` receipt, so a live answer is
not an opaque wall of text anymore. This exposes proof receipts, not private
chain-of-thought or debug self-confession.

Verification:

- `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  - 96 passed.
- `uv run ruff check src/vibemix/library/codex_curate.py src/vibemix/__main__.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  - passed.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 50 passed.
- `npm --prefix tauri/ui run build`
  - passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args -- --nocapture`
  - 3 passed.

## 2026-05-29 Active Live Question Fail-Closed

The current physical proof run found the live socket missing:

- `uv run python -m vibemix library live-context --wait-ready 3 --interval 1 --json --out .planning/research/live-context-latest-proof.json`
  - exited non-zero with `readiness.diagnosis=live_socket_missing`
  - `frames_seen=0`, `flat_deck_frame_seen=false`, `listening=false`
  - library cache loaded from `folder_cache` with 1547 tracks
  - Now Playing was browser-owned (`com.apple.WebKit.GPU`) and correctly not a
    deck-source candidate

That exposed an important shipped-path hole: if the Library UI has no live
context at all and the DJ asks an active live question, Viber must not fall
through to a normal model turn. `chat_with_codex` now fails closed before
Codex is spawned for active live/deck/move questions with no live packet. The
spoken reply is intentionally short and non-psychotic:

`Live proof is not armed, so I won't judge that transition or deck move yet.`

The diagnostic detail stays in the structured JSON/CLI receipt:
`stop_reason=live_context_required`, `transport_status=missing_live_context`,
`claim_policy=requires_more_evidence`, and `move_grades_allowed=false`. The
Library UI maps that to `live proof · not armed` / `needs proof` and
`live proof needed`, without exposing raw guard or stop labels to the DJ.

Verification:

- `uv run python -m vibemix library chat 'was that transition good?' --json`
  - returned the deterministic fail-closed reply above with no Codex/tool run.
- `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  - 97 passed.
- `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py`
  - passed.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 53 passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args -- --nocapture`
  - 3 passed.

## 2026-05-29 Viber Live Proof Status Row

The Library/Viber side rack now shows live proof state before the DJ asks a live
question. This keeps the product behavior legible without making Viber speak a
long self-diagnostic.

The row is deliberately compact:

- `live proof · not armed` when no live deck packet is attached
- `live proof · partial` when schema/source/audio/gate pieces are incomplete
- `live proof · armed` when schema-v2 transport, deck1/deck2 lanes,
  source/provenance, audio map, and a transition gate are present

When live context arrives, the row includes the deck reference summary, for
example `deck1 A=known:dominant / deck2 B=unknown:present`. It is status chrome,
not spoken copy, and it does not expose private reasoning, raw guard labels, or
internal stop reasons.

Verification:

- `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  - 53 passed.
- `npm --prefix tauri/ui run build`
  - passed.

Note: the build was initially blocked by a pre-existing
`GroundingPanel.ts` `NodeList` iterator compatibility error. That local shell
change was preserved and adjusted with `Array.from(...)` so the full build gate
is meaningful again.

## 2026-05-29 Now Playing Source Guard

Current live smoke showed a useful almost-bug: the controller posture was alive
(`deck B` dominant/play on), but macOS Now Playing was owned by a browser
process (`com.apple.WebKit.GPU`) playing Pink Floyd. Without a source guard, any
future exact library match from Safari/Chrome/Apple Music/Spotify could be
mis-attributed to the active controller deck and become a false deck identity.

`TrackInfo.snapshot()` now carries `client_bundle_id` from MediaRemote raw
metadata, and `DeckPoller` rejects known non-deck Now Playing owners before
resolving title/artist against the library cache. Unknown or DJ-looking owners
still preserve the existing path; known DJ hints include rekordbox, Pioneer DJ,
djay/Algoriddim, Serato, Traktor, VirtualDJ, Mixxx, Engine, and Denon DJ. The
`library live-context --json` source diagnostics now include a content-light
`nowplaying` block with title/artist, client bundle id, playback rate, and
`deck_source_candidate`.

Follow-up source-status wiring now carries the same provenance through
`DeckState.source_status` and into `deck_source_context[...]`. After a restart,
Gemini/Viber prompts can see bounded fields such as
`nowplaying=blocked_non_deck_owner`,
`nowplaying_owner=com.apple.webkit.gpu`, and
`resolution=blocked_non_deck_nowplaying`. These are diagnostic labels only, not
deck identity proof.

The source-status lane is now structured on the live socket too:
`deck_source_status` carries bounded JSON keys (`controller`, `nowplaying`,
`nowplaying_owner`, `nowplaying_title`, `audible_deck`, `resolution`,
`resolved_side`). The Library UI normalizes and forwards it to Viber, and
`chat_with_codex` rebuilds `MusicState.deck_state.source_status` from the map
before rendering `deck_source_context[...]`. This prevents a stale/missing text
context from hiding why deck identity is unresolved.

Verification:

- `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_refresh_deck.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py`
  - 107 passed.
- `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_codex_curate.py tests/state/test_deck_context.py tests/library/test_live_context_cli.py`
  - 138 passed after adding the structured `deck_source_status` socket/UI/Viber
    lane.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 48 passed after preserving `deck_source_status` through Library chat.
- `uv run pytest -q tests/test_track_macos.py tests/state/test_deck_poller.py tests/library/test_live_context_cli.py`
  - 58 passed.
- `uv run ruff check src/vibemix/state/deck_state.py src/vibemix/state/deck_poller.py src/vibemix/state/refresh.py src/vibemix/state/deck_context.py tests/state/test_deck_poller.py tests/state/test_refresh_deck.py tests/state/test_deck_context.py`
  - passed.
- `uv run python -m vibemix library live-context --json --timeout 0.2 --frames 1`
  - showed `nowplaying.client_bundle_id=com.apple.WebKit.GPU` and
    `deck_source_candidate=false`.

## Viber Tool Trace Visibility

The chat surface no longer has to trust Codex's final self-reported
`tool_trace` as the durable receipt. The MCP tool-event side channel now records
a bounded `arg` label next to each actual tool call, for example the search
query, `k`, curve, candidate count, playlist name, or exported set name. The
Codex wrapper reads that real tape before the temp directory disappears and
prefers it for `CodexChatResult.tool_trace`; the model's JSON trace is now only
a fallback when the tape is absent.

This addresses the "long wait then wild response" failure mode: the UI can keep
showing the actual agentic work instead of replacing live rows with whatever the
model chose to summarize at the end. It is still not hidden chain-of-thought,
but it is an auditable tool/proof receipt.

Verification:

- `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_clap_runtime_errors.py`
  - 70 passed.
- `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  - 48 passed.
- `uv run ruff check src/vibemix/library/codex_curate.py src/vibemix/library/toolset.py src/vibemix/library/mcp_server.py tests/library/test_codex_curate.py tests/library/test_clap_runtime_errors.py`
  - passed.

## Structured Audio Window Map

`audio_window_context[...]` remains the compact prompt grammar, but it now has a
structured twin: `audio_window_map`. The map labels the same P1 master-mix
window as old/current/action/future spans (`pre_s`, `current_s`, `action_s`,
`future`) plus bounded move anchors. It explicitly repeats
`deckA_audio=not_attached`, `deckB_audio=not_attached`,
`duplicate_audio=same_master_not_deck_split`, and
`rule=time_alignment_not_outcome_verdict`.

This is deliberately cheap: no new audio Part, no second model pass, and no
claim that deck stems are available. Gemini sees the map adjacent to the P1
audio Part; the live socket and Library chat can carry the structured map to
Viber for the same old/action/future grounding. The live-context proof command
now fails with an explicit blocker when this structured map is missing.

`audio_part_context[...]` now sits beside this window map on the direct Gemini
path and rides the live socket/Viber packet as a required schema-v2 capability.
On Gemini turns it says P1 was model-heard; on Viber/socket turns it says P1 is
runtime-observed but `P1_model_heard=false`, so Viber gets the same part-role
contract without pretending it literally received an audio Part. This closes a
separate confusion class: when P2/P3 exists, Gemini can see whether that Part is
user mic or future source lookahead, and the prompt states that P2/P3 are not
current deck audio or isolated deck stems.

Verification:

- `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  - 204 passed after making `audio_part_context` a socket/Viber capability.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 53 passed after preserving the schema/capability/part-role receipt through
    the Library UI chat bridge.
- `npm --prefix tauri/ui run build`
  - passed.
- `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/runtime/ws_bus.py src/vibemix/library/codex_curate.py src/vibemix/__main__.py src/vibemix/agent/dj_cohost.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  - passed.

## Stale Transport Result Boundary

Prompt warnings alone are not enough. If a live socket is pre-schema-v2 or
missing required structured capabilities, Viber now treats that packet as
`stale_or_pre_schema_v2` at the result boundary too. If Codex still writes
"great transition", "clean blend", or another multi-deck/move-outcome verdict
from that packet, `chat_with_codex` replaces it with a fresh-resample correction
that asks for schema-v2 deck/source/audio lanes before judging the move.

The chat history sanitizer also treats `requires_more_evidence` as a blocking
policy for prior Viber live outcome claims. This keeps an older hallucinated
"great transition" line from priming the next prompt when the current transport
receipt is stale. Honest self-corrections such as "I can't call it a transition"
are still kept.

Verification:

- `uv run pytest -q tests/library/test_codex_curate.py`
  - 65 passed, including the stale-transport result-boundary test.
- `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  - 190 passed.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 48 passed.
- `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py`
  - passed.

## Fresh Runtime Smoke And Cold Audio Window Map

The stale live runtime was restarted on the current worktree. The new socket now
advertises `live_context_schema_version=2` and the required capability receipt,
so the prior `stale_live_runtime` blocker is gone.

The restart exposed a real cold-frame mismatch: the socket advertised
`audio_window_map` but omitted the structured map when there were no recent MIDI
moves. `src/vibemix/runtime/ws_bus.py` now emits
`audio_window_context[...]` and `audio_window_map` whenever the live state has a
reference frame such as a connected controller, audio, deck rows, or lookahead.
Recent moves become anchors inside the map; a cold/silent frame carries
`move_anchor=none` and `move_anchors=[]`.

The trust normalizer cap for `audio_window_context[...]` was also raised so the
safe no-move contract no longer clips mid-token before `future=not_attached]`.

Current live smoke:

- `uv run python -m vibemix library live-context --json --require-proof --timeout 0.3 --frames 10`
  - `ok=true`
  - `readiness.diagnosis=missing_physical_proof`
  - `stale_live_runtime=false`
  - `live_context_schema_version=2`
  - `missing_capabilities=[]`
  - `audio_window_context_seen=true`
  - `audio_window_map_seen=true`
  - remaining blockers are physical: no resolved/citable deck row, no recent
    controller move, no observed master audio, and no bounded `audio_delta`.

Verification:

- `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py`
  - 78 passed.
- `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  - 144 passed.
- `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/runtime/ws_bus.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py`
  - passed.

## Wait-Ready Physical Proof Capture

`vibemix library live-context` is no longer only a one-shot sampler. It now has
a bounded proof loop:

`uv run python -m vibemix library live-context --wait-ready 60 --interval 1 --timeout 0.5 --frames 30 --out .planning/proofs/live-context-<date>.json`

`--wait-ready` implies `--require-proof`. The command keeps resampling the live
socket until the readiness packet is physically ready or the wait deadline
expires. The JSON result includes `proof_attempts`, `wait_ready_s`, and
`wait_interval_s`, and `--out` writes the exact packet that Viber would receive.

This is the intended booth proof workflow now:

1. Start `uv run python -m vibemix`.
2. In another terminal, run the `live-context --wait-ready ... --out ...`
   command above.
3. Load/play the DJ source, move a controller, and let the command capture the
   first packet with schema-v2 transport, deck/source/audio context,
   `audio_window_map`, recent move, master audio, and `audio_delta`.
4. Use that artifact to ask Viber/Gemini about the same move and verify the
   answer names deck/control evidence without inventing a transition verdict.

The Viber CLI can now consume that proof artifact directly:

`uv run python -m vibemix library chat "was that good?" --live-context-file .planning/proofs/live-context-<date>.json --json`

`--live-context-file` accepts either a raw live-context dict or the full
`library live-context --out` artifact and extracts its `live_context` field. A
bad file path or non-context JSON fails loudly instead of silently asking Viber
without the proof packet.

The deterministic reply verifier closes the loop:

`uv run python -m vibemix library verify-live-reply --live-context-file .planning/proofs/live-context-<date>.json --chat-result-file .planning/proofs/viber-chat-<date>.json --json`

It reuses the same live claim guard as the Codex result boundary and fails if
the Viber reply would have needed correction, if move grades appear without
live proof, or if the proof artifact says `readiness.ready=false`. This gives a
machine-checkable answer to "did Viber hallucinate a transition from this
packet?" without another model call.

Verification:

- `uv run pytest -q tests/library/test_live_context_cli.py`
  - 30 passed after adding proof-artifact input and deterministic reply
    verification.
- `uv run pytest -q tests/library/test_live_context_cli.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py tests/library/test_codex_curate.py`
  - 151 passed.
- `uv run ruff check src/vibemix/__main__.py src/vibemix/library/codex_curate.py tests/library/test_live_context_cli.py`
  - passed.

## Verification

Latest focused verification after the final prompt/proof split:

- `uv run python -m vibemix` was started with the local DDJ-FLX4/BlackHole
  stack, then sampled with
  `uv run python -m vibemix library live-context --wait-ready 3 --interval 1 --json --out .planning/research/live-context-latest-proof.json`.
  The sampler saw the real socket at `ws://127.0.0.1:8765`:
  `ok=true`, `frames_seen=63`, `flat_deck_frame_seen=true`,
  `session_snapshot_seen=true`, schema v2, `missing_capabilities=[]`, and
  `audio_part_context_seen=true`. Readiness correctly stayed false with
  `diagnosis=missing_physical_proof` because the feed was silent: no resolved
  deck row, no citable deck track, no recent controller move, no audible master
  audio, and no bounded `audio_delta`. The runtime was stopped cleanly.
- The result-boundary correction copy no longer exposes a self-correction
  essay to the DJ. Public replies are now short states such as
  `Live proof is incomplete, so the transition verdict is held for now.`;
  detailed deck lanes/source/provenance remain in structured guard summaries,
  logs, and `live_verification`. Verification:
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_linter.py`
  passed with 219 tests, `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 53 tests, and Ruff passed on the edited Python guard/copy files.
- `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  - 204 passed after adding `audio_part_context` to the socket/Viber proof
    capability set.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 53 passed.
- `npm --prefix tauri/ui run build`
  - passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args -- --nocapture`
  - 3 passed. The Rust bridge now pins that `audio_part_context` survives in
    `--live-context` alongside schema/capability JSON.
- `uv run python -m vibemix library live-context --wait-ready 3 --interval 1 --json --out .planning/research/live-context-latest-proof.json`
  - exited non-zero with `readiness.diagnosis=live_socket_missing`,
    `frames_seen=0`, and `listening=false` on `127.0.0.1:8765`.
  - The missing capability list now includes
    `audio_delta,audio_part_context,audio_window_map,deck_source_status,live_evidence`.
  - Library cache loaded from `folder_cache` with 1547 tracks; current
    Now Playing was browser-owned (`com.apple.WebKit.GPU`) and correctly not a
    deck-source candidate. Physical proof still requires restarting/running the
    live Vibemix session.
- `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py`
  - 139 passed after `--require-proof` began requiring structured
    `deck_source_status` and `audio_window_map`.
- `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  - 189 passed after adding the socket schema/capability receipt and rendering
    fresh/stale `live_context_transport[...]` into Viber's prompt.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 48 passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args_preserve_time_aligned_audio_context`
  - passed, pinning that the Tauri command preserves schema/capability JSON.
- `uv run ruff check src/vibemix/runtime/ws_bus.py src/vibemix/__main__.py src/vibemix/library/codex_curate.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py`
  - passed.
- `uv run python -m vibemix library live-context --json --require-proof --timeout 0.25 --frames 8`
  - returned `ok=true` from the current running socket, but readiness remained
    false because that already-running process advertised no schema/capabilities
    and did not emit the required `audio_part_context`, `deck_source_status`,
    or `audio_window_map`. Restart the live session before using this as
    physical proof.
- `uv run python -m vibemix library live-context --json --require-proof --timeout 0.2 --frames 6`
  - now reports `readiness.diagnosis=stale_live_runtime`,
    `stale_live_runtime=true`, and a `next_action` telling the operator to
    restart the live session before chasing physical audio/deck blockers. The
    prompt preview also renders `status=stale_or_pre_schema_v2`, so Viber should
    avoid live verdicts from stale transport.
- `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py tests/state/test_coach.py::test_evidence_line_renders_live_evidence_categories_for_gemini`
  - 122 passed.
- `uv run pytest -q tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  - 279 passed after adding the LLM-aware `context_feed_contract[...]`.
- `uv run pytest -q tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/runtime/test_coach.py tests/agent/test_dj_cohost.py tests/library/test_codex_curate.py`
  - 133 passed after carrying `context_feed_contract[...]` into session events,
    `coach_line` signatures, Gemini recall queries, and Viber historical move
    matching.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 47 passed.
- `uv run ruff check src/vibemix/__main__.py src/vibemix/library/codex_curate.py src/vibemix/state/deck_context.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  - passed.
- `uv run python -m vibemix library live-context --json --timeout 0.2 --frames 1`
  - returned `ok=true` from the local Vibemix socket.
  - rendered `context_feed_contract[...]` plus safe deck1/deck2
    reference/source/audio context.
  - readiness remained false because physical proof was missing.

Earlier broader slices are logged in
`.planning/research/2026-05-29-live-deck-context-viber-gemini.md`.

## Current Honest State

The code now has the context and guard spine needed for Viber/Gemini to avoid
calling a one-deck move a great transition. The local socket preview proves the
prompt and bridge path render the right safety packet.

The full product goal is not physically complete yet. Remaining proof requires a
real live DJ run with:

1. DJ audio routed into the configured input.
2. A connected controller publishing recent moves.
3. Deck rows resolved with citable track IDs and source provenance.
4. `audio_delta` observed around a move.
5. Viber/Gemini asked about that move.
6. The response naming deck/control evidence without inventing a transition.

## Safe Continuation

1. Start the live session with real DJ audio and controller attached.
2. Run:
   `uv run python -m vibemix library live-context --json --require-proof --out .planning/proofs/live-context-<date>.json`
3. If readiness fails, fix only the missing proof leg shown in
   `readiness.blockers`.
4. Once proof passes, ask Viber and Gemini about a single-deck move and capture
   both the prompt evidence packet and the corrected response.
5. Keep MCP/tool-flow changes in the separate Viber agent mapping session.
