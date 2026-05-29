# Handoff: Viber and Gemini Live Deck Context Work Done

**Date:** 2026-05-29
**Status:** implemented and test-covered for prompt, socket, browser, and guard
paths; live socket transport has been physically sampled; full live DJ proof
still requires audible deck audio, recent controls, resolved deck rows, and
`audio_delta`.
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

### 3a. Deck-audio separability contract

Added `deck_audio_separation_context[...]` across the runtime socket, Gemini
prompt, Viber prompt, Library UI normalizer, Rust bridge, and proof CLI. This
packet states the current capture capability explicitly:

- current capture is `P1_global_mix`
- Gemini audio is a mono downmix of the captured stream
- `deckA_audio=not_captured`
- `deckB_audio=not_captured`
- `per_deck_audio=not_attached`
- `isolated_decks=false`
- `upgrade_path=multi_channel_deck_pair_capture`

This is not a transition verdict. It prevents the LLM from silently upgrading
controller/deck labels into true isolated deck hearing. Local device probing on
2026-05-29 found `BlackHole 16ch`, `BlackHole 2ch`, `DDJ-FLX4`, and a
`rekordbox Aggregate Device`, but the current runtime still opens
`BlackHole 2ch` with two channels and downmixes before Gemini. So the honest
state is: deck identity/routing can be structured text; isolated deck audio is
not captured yet.

### 3b. Optional multichannel deck-pair capture seam

The runtime now has a real, default-off path for isolated deck-pair capture:

- `VIBEMIX_INPUT_DEVICE` selects the capture device as before.
- `VIBEMIX_INPUT_CHANNELS` can open more than two input channels.
- `VIBEMIX_DECK_AUDIO_CHANNELS` maps zero-based input channel pairs to deck
  lanes, for example `A=0,1;B=2,3`.
- `VIBEMIX_DECK_AUDIO_CHANNELS=auto` reads the local Rekordbox
  `rekordbox3.settings` deck output routing hint when present. On this machine
  it finds the external-mixer Aggregate Device route
  `Deck A=0,1 / Deck B=2,3`. This is a setup hint, not live audio proof, and
  default mode still stays disabled unless explicit env/auto routing is chosen.
- When `VIBEMIX_DECK_AUDIO_CHANNELS=auto` is explicitly requested and the user
  has not pinned `VIBEMIX_INPUT_DEVICE`, the live runtime now tries to upgrade
  the default BlackHole 2ch input to BlackHole 16ch if the Rekordbox route needs
  more channels. Explicit input-device selections are respected; too-narrow
  explicit devices still report setup blockers instead of pretending to capture
  both decks.
- The proof CLI setup hint now matches that runtime behavior. On this machine,
  the local audio probe sees `BlackHole 16ch` (16 in/out), `BlackHole 2ch`
  (2 in/out), and the Rekordbox settings route `Deck A=0,1 / Deck B=2,3`.
  With no live socket running, `library live-context --json` returns
  `diagnosis=live_socket_missing` plus `setup_hint.recommended_env` containing
  only `VIBEMIX_DECK_AUDIO_CHANNELS=auto`; the JSON also carries
  `auto_upgrade_input_device=BlackHole 16ch` and an explicit fallback env map.
- `VIBEMIX_MASTER_AUDIO_CHANNELS` can override which channels form the master
  P1 downmix. If omitted while deck pairs are configured, the master downmix is
  the configured deck-pair channels.

When both A and B are mapped and the stream opens enough channels,
`deck_audio_separation_context[...]` changes from global-only to
`mode=deck_pair_capture_configured`, `deckA_audio=captured`,
`deckB_audio=captured`, `per_deck_audio=captured_not_attached`, and
`deck_pairs=A:0,1+B:2,3`. The audio callback now updates the shared capture
context with per-deck RMS, so prompt/socket frames can also expose compact
activity such as `deck_audio_activity=A_active+B_silent`; live evidence mirrors
that as `deck_audio_capture=A_active+B_silent`.

The callback also emits a separate `deck_audio_features_context[...]` when deck
pair capture is configured. This packet carries small deterministic per-deck
descriptors from the latest captured lane frame: activity, RMS, peak, zero-cross
rate, flux, and crest. It is deliberately labeled
`rule=deck_audio_features_not_outcome_verdict`, so Viber can know "Deck A is
measuring active / Deck B is measuring quiet" without turning that into praise
or a transition grade.

The capture path now also emits `deck_audio_delta_context[...]` from the latest
deck-pair callback comparison. It reports bounded per-lane feature changes such
as `A_delta=rms_rose_100pct_strong` and
`B_delta=rms_fell_50pct_strong`, with
`rule=deck_audio_delta_not_causal_proof`. Live evidence mirrors this as
`deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong`, so Viber
can react to "what changed on deck A/B" without treating the delta as causality
or a skill grade. When the deck-pair capture is configured but no clear per-lane
change has happened, the context still renders explicit stable labels such as
`A_delta=no_clear_delta` and `B_delta=no_clear_delta`. Those labels help Viber
know "nothing changed on the deck lanes" without creating live-evidence proof
for a transition verdict.

The capture path now also keeps a short feature history and emits
`deck_audio_window_context[...]` for the user's "older part / current part"
shape. This packet compares `pre=-6.0..-1.0` to `current=-1.0..0.0` for each
captured deck lane and labels `A_pre`, `A_current`, `A_delta`, `B_pre`,
`B_current`, and `B_delta`. It is deterministic text, not duplicate audio, and
it carries `rule=deck_audio_window_not_causal_or_quality_verdict` so the model
can react to deck-lane movement without turning it into "great transition"
praise.

When a Rekordbox routing hint exists but deck capture is not enabled, the
separation packet can include
`routing_hint=rekordbox_settings_A:0+1+B:2+3` with
`routing_hint_rule=output_routing_not_live_audio_proof`. That gives the setup
path useful evidence while preventing the model from treating output-channel
configuration as heard deck audio.

`library live-context --json` now also includes this in `source_status` as
`rekordbox_deck_routing_hint`, even when the live socket is missing. That keeps
setup diagnostics useful without weakening the physical proof gate.

### 3c. Optional Gemini Deck A / Deck B audio Parts

Gemini can now receive short, explicitly labeled deck-pair audio Parts when the
multichannel capture seam is configured. This is separate from Viber chat:
Viber stays text-grounded through the live context packet, while Gemini can hear
the deck lanes on selected live-reaction turns.

Cost control:

- `VIBEMIX_GEMINI_DECK_AUDIO_PARTS=auto` is the default. It attaches Deck A/B
  Parts only on useful event types such as `MIX_MOVE`, `TRANSITION_OPPORTUNITY`,
  `KEY_CLASH`, or `MANUAL`, and only when deck RMS shows activity.
- `VIBEMIX_GEMINI_DECK_AUDIO_PARTS=off` disables deck audio Parts.
- `VIBEMIX_GEMINI_DECK_AUDIO_PARTS=always` attaches them whenever configured.
- `VIBEMIX_GEMINI_DECK_AUDIO_PART_SECONDS` is bounded to 1-6 seconds; default
  is 3 seconds, or about 96 audio tokens per deck at Gemini's documented
  32-token/sec audio rate.

Prompt labeling:

- P1 remains the audience-truth master/global mix.
- Optional Deck A/B Parts are appended after any mic/lookahead Parts and labeled
  in `audio_part_context[...]` as `deckA_configured_capture` /
  `deckB_configured_capture`.
- The Part labels also carry the capture activity state from the exact ring
  snapshot window being attached, for example `P2_activity=deckA_active` and
  `P3_activity=deckB_silent`; the spoken Part suffix names
  `captured Deck B audio (silent)` when that attached lane window is quiet.
  The WAV bytes are encoded from that same sampled PCM slice, so the activity
  label and attached audio cannot drift across two ring-buffer reads.
- `audio_part_context[...]` carries `audio_token_rate=32_per_second` and
  bounded estimates such as `P1_tokens_est=192` and `P2_tokens_est=96`, so the
  low-cost shape is explicit in the context packet without another model pass.
- When Deck A/B Parts are attached, both `audio_window_context[...]` and
  `audio_window_map` now reference the real deck Part labels:
  `deckA_audio=P2`, `deckB_audio=P3`, and
  `per_deck_audio=deck_pair_parts`. Without attached deck Parts they keep the
  older `deckA_audio=not_attached` / `deckB_audio=not_attached` fence.
- The prompt states that deck Parts are for mapping deck contribution only and
  are not transition-quality verdicts by themselves.

This closes the earlier half-step where the runtime captured per-deck rings but
Gemini could only read their structured text/RMS receipt.

Latest focused verification for this Part-label contract:

- `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_coach.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/memory/test_ingest.py tests/memory/test_retrieval.py`
  - 291 passed.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 72 passed.
- `npm --prefix tauri/ui run build`
  - passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args_preserve_time_aligned_audio_context`
  - 1 passed.
- `uv run pytest -q tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_cache_hit.py`
  - 10 passed.
- `uv run pytest -q tests/test_main_smoke.py`
  - 23 passed.
- `uv run ruff check src/vibemix/audio/deck_capture.py src/vibemix/state/deck_context.py src/vibemix/agent/dj_cohost.py src/vibemix/runtime/ws_bus.py src/vibemix/runtime/coach.py src/vibemix/__main__.py src/vibemix/library/codex_curate.py src/vibemix/memory/ingest.py src/vibemix/memory/retrieval.py tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_coach.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/memory/test_ingest.py tests/memory/test_retrieval.py`
  - passed.
- `git diff --check`
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
- `live_evidence.mix` keeps a 9-item evidence cap; `live_evidence.refs` keeps a
  13-item ref cap so four MIDI refs plus nine mix atoms can coexist.
- Priority keeps MIDI, deck lanes/reference/source, transition gates,
  second-deck identity, deck-audio capture/features/delta receipts,
  `move_scope`, and audio/move deltas ahead of lower-value raw route atoms.
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
- configured deck-pair capture in `deck_audio_separation_context`
- `deck_audio_capture=...` in live evidence
- at least one active deck-capture lane
- `deck_audio_features_context[...]` plus `deck_audio_features=...`
- `deck_audio_delta_context[...]` plus `deck_audio_delta=...`
- `deck_audio_window_context[...]` so the live packet contains a pre/current
  deck-lane window, not only latest-callback measurements

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
`deck_audio_separation_context[...]`, `deck_audio_features_context[...]`, and
`deck_audio_delta_context[...]`, and `deck_audio_window_context[...]` when the
runtime has those receipts, so past move memory can compare "what changed on
deck A/B" without storing raw audio or adding another model call.
`context_feed_contract[...]` preserves whether fields were volatile live labels,
cacheable/static prompt material, or past-session comparison memory. Viber and
Gemini can compare a current knob/fader move to past move-to-sound-change
memories, but the rendered memory is fenced as past-session comparison, not
current live proof.

Old or unsafe memory snippets are sanitized before prompt use:

- attached/isolated deck-stem claims are omitted
- stale "great transition" type spoken claims are omitted unless they are honest
  self-corrections
- copied bracket citations are stripped

## Main Files

- `src/vibemix/state/deck_context.py`
- `src/vibemix/state/coach.py`
- `src/vibemix/agent/dj_cohost.py`
- `src/vibemix/audio/deck_capture.py`
- `src/vibemix/audio/features.py`
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

## 2026-05-29 Deck-Audio-Rich Single-Deck Verifier

The deterministic Viber reply verifier now pins the exact scary case: a
readiness-ready live packet can contain configured deck-pair capture,
`deck_audio_capture=A_active+B_silent`,
`deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000`,
`deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong`, and even a
positive move-grade artifact, but if only deck A has independent identity then
the claim policy remains `blocked`. "Great transition" / "incoming deck landed"
is corrected, and the move grade is rejected as unsupported live proof.

Verification:

- `uv run pytest -q tests/library/test_live_context_cli.py::test_cmd_library_verify_live_reply_rejects_deck_audio_rich_single_deck_transition tests/library/test_live_context_cli.py::test_cmd_library_verify_live_reply_rejects_unsupported_transition_claim`
  - 2 passed.
- `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py`
  - 170 passed.

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
rack renders a `live read` row with calm states such as `fresh`, `waiting`,
`listening`, `live move checked`, `setup noted`, and `grounded`. It does
not show raw internal labels such as `live_reply_verify`, `guard`,
`live_context_required`, `unsupported_live_outcome_claim`, or the old
`verdict held`/`claim held` wording. If there are no playlist/export artifacts,
the artifact panel still shows a compact `live read` receipt, so a live answer
is not an opaque wall of text anymore. This exposes operational receipts, not
private chain-of-thought or debug self-confession.

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

## 2026-05-30 Public Reply Hygiene + Event-Capture Drift Fix

Kaan's latest product boundary is now pinned in code: public AI copy should not
confess model uncertainty, self-correct in the DJ's ear, or explain missing
proof. The deterministic guards still keep the evidence policy internally, but
replacement copy now says what was grounded:

- blocked/watch live outcome: `I caught the live move. The useful note is the sound change right there.`
- candidate-not-verdict live outcome: `That reads like a transition setup. The useful note is the shape, not a quality score.`
- unsupported move-effect verdict: `I caught the move and the sound change. The useful note is how the energy shifted right after it.`

Viber's chat rules now explicitly say weak live evidence should be answered
with grounded move/sound product language, not "live read is still locking" or
other proof/debug language. The result-boundary diagnostic scrubber also catches
phrases such as "I only have audible deck mix" and "live read is still
locking", keeping those details in `live_verification` / logs rather than the
spoken reply.

Two consistency drifts were fixed:

- `AICoach.task_for_event(MIX_MOVE)` now reads `ev.extra["audio_capture_context"]`
  when rendering `live_evidence[...]`, so the task tail can include the same
  `deck_audio_window=...` atom that the prompt and registry know about.
- `DJCoHostAgent.llm_node` now passes the per-event `prompt_audio_capture_context`
  to both `should_defer_live_claim_stream` and `apply_live_claim_guard`. This
  prevents a turn where Gemini sees event-scoped Deck A/B capture proof but the
  stream guard evaluates an older or empty agent-level capture context.
- The shared `live_claim_policy(...)` supported-verdict gate now requires a
  two-lane `deck_audio_window` pre/current packet in addition to trusted deck
  identity, two active deck lanes, feature descriptors, deltas, and attached
  Deck A/B audio Parts when those are requested. Latest-callback Deck A/B RMS
  and delta alone can only produce candidate/setup language; it cannot approve
  "great/clean transition" praise.

Verification:

- `uv run pytest -q tests/test_main_smoke.py::test_deck_audio_auto_upgrades_default_blackhole_input tests/test_main_smoke.py::test_deck_audio_auto_respects_explicit_input_device tests/audio/test_deck_capture.py`
  - 10 passed.
- `uv run pytest -q tests/library/test_live_context_cli.py::test_viber_setup_hint_turns_rekordbox_route_hint_into_env tests/library/test_live_context_cli.py::test_viber_setup_hint_respects_explicit_input_device tests/test_main_smoke.py::test_deck_audio_auto_upgrades_default_blackhole_input tests/test_main_smoke.py::test_deck_audio_auto_respects_explicit_input_device`
  - 4 passed.
- `uv run python -m vibemix library live-context --wait-ready 0.2 --interval 0.1 --json`
  - exited non-zero as expected with no live runtime, `diagnosis=live_socket_missing`;
    source status found the Rekordbox route hint and emitted the simplified
    `VIBEMIX_DECK_AUDIO_CHANNELS=auto` setup hint plus `auto_upgrade_input_device`.
- `VIBEMIX_DECK_AUDIO_CHANNELS=auto uv run python -m vibemix` boot probe
  - successfully upgraded `BlackHole 2ch -> BlackHole 16ch` and opened
    `BlackHole 16ch @ 48000Hz (4ch)`.
- Live socket proof while that runtime was up
  - `frames_seen=58`, `deck_pair_capture_configured=true`,
    `deck_audio_separation_context_seen=true`,
    `deck_audio_features_context_seen=true`,
    `deck_audio_window_context_seen=true`, and after the stable-delta patch
    `deck_audio_delta_context_seen=true` with
    `A_delta=no_clear_delta+B_delta=no_clear_delta`.
  - It correctly stayed `diagnosis=missing_physical_proof` because no deck audio
    was active, no controller move was observed, and no resolved deck rows were
    present.
- `uv run pytest -q tests/state/test_coach.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_linter.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  - 317 passed.
- `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/test_main_smoke.py`
  - 155 passed.
- `uv run pytest -q tests/agent/test_dj_cohost.py::test_agent_02_super_init_kwargs tests/agent/test_dj_cohost.py::test_agent_03_initial_state`
  - 2 passed. A broader mixed run including all of `tests/test_main_smoke.py`
    plus `tests/agent/test_dj_cohost.py` exposed two existing persona-prefix
    order failures, but the isolated agent tests pass and the deck-auto patch is
    covered by the targeted main-smoke tests above.
- `uv run ruff check src/vibemix/state/coach.py src/vibemix/agent/dj_cohost.py src/vibemix/state/deck_context.py src/vibemix/library/codex_curate.py tests/state/test_coach.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_linter.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  - passed.
- `uv run ruff check src/vibemix/__main__.py tests/test_main_smoke.py`
  - passed.
- `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  - 72 passed.
- `git diff --check`
  - passed.

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

`Start live monitoring first, then I'll read the live move from the decks.`

The diagnostic detail stays in the structured JSON/CLI receipt:
`stop_reason=live_context_required`, `transport_status=missing_live_context`,
`claim_policy=requires_more_evidence`, and `move_grades_allowed=false`. The
Library UI maps that to `live read · waiting` / `listening` and `live read
waiting`, without exposing raw guard or stop labels to the DJ.

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

The Library/Viber side rack now shows live-read state before the DJ asks a live
question. This keeps the product behavior legible without making Viber speak a
long self-diagnostic.

The row is deliberately compact:

- `live read · waiting` when no live deck packet is attached
- `live read · partial` when schema/source/audio/gate pieces are incomplete
- `live read · armed` only when schema-v2 transport, deck1/deck2 lanes,
  source/provenance, audio map, a transition gate, configured deck-pair capture,
  `deck_audio_capture=...`, `deck_audio_features=...`,
  `deck_audio_delta=...`, and at least one active deck audio lane
  are present

When live context arrives, the row includes the deck reference summary, for
example `deck1 A=known:dominant / deck2 B=unknown:present`. It is status chrome,
not spoken copy, and it does not expose private reasoning, raw guard labels, or
internal stop reasons.

The UI now mirrors the proof CLI's stricter deck-audio gate: a safe global-mix
or stereo-only context can show `partial`, but cannot show `armed`. A packet
with feature/delta context but missing the matching `live_evidence` receipts
also stays `partial`.

Verification:

- `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  - 59 passed.
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
`deck_source_status` carries bounded JSON keys (`controller`,
`controller_connection`, `library`, `library_tracks`, `library_source`,
`library_match`, `nowplaying`, `nowplaying_owner`, `nowplaying_title`,
`audible_deck`, `resolution`, `resolved_side`, `second_deck_source`,
`screen_vision`). The Library UI normalizes and forwards it to Viber, and
`chat_with_codex` rebuilds `MusicState.deck_state.source_status` from the map
before rendering `deck_source_context[...]`. This prevents a stale/missing text
context from hiding why deck identity is unresolved.

Latest follow-up: `DeckPoller` no longer collapses every failed title
resolution into generic `library_miss`. It now distinguishes missing/empty/error
library cache, unique match vs ambiguous/missing title match, blocked non-DJ Now
Playing owner, controller connection state, disabled screen-vision independent
source, and the explicit second-deck suppression rule. The Viber proof CLI turns
those private diagnostics into content-light blockers such as "Now Playing did
not match a unique library row" or "second deck identity source requires
independent deck evidence." This is still not proof; it is the internal reason
why proof is missing.

Verification:

- `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_refresh_deck.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py`
  - 107 passed.
- `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_codex_curate.py tests/state/test_deck_context.py tests/library/test_live_context_cli.py`
  - 138 passed after adding the structured `deck_source_status` socket/UI/Viber
    lane.
- `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py`
  - 153 passed after adding richer deck-source blockers.
- `npm --prefix tauri/ui test -- src/library/api.test.ts`
  - 44 passed after preserving the expanded `deck_source_status` keys in the UI
    normalizer.
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
"great transition" line, or a self-correction such as "I can't call it a
transition," from priming the next prompt when the current transport receipt is
stale. Those diagnostics stay in proof artifacts; public Viber copy uses calm
held states instead.

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

- `VIBEMIX_INPUT_DEVICE='BlackHole 16ch' VIBEMIX_DECK_AUDIO_CHANNELS=auto uv run python -m vibemix`
  booted a live runtime from this tree, selected the local Rekordbox route hint
  (`A=0,1;B=2,3`), opened `BlackHole 16ch` as a 4-channel stream, and exposed
  the mascot bus on `127.0.0.1:8765`.
- `uv run python -m vibemix library live-context --wait-ready 3 --interval 1 --json --out .planning/research/live-context-latest-proof.json`
  - `ok=true`
  - `frames_seen=62`
  - `flat_deck_frame_seen=true`
  - `session_snapshot_seen=true`
  - `readiness.diagnosis=missing_physical_proof`
  - `stale_live_runtime=false`
  - `live_context_schema_version=2`
  - `missing_capabilities=[]`
  - `deck_pair_capture_configured=true`
  - `deck_audio_separation_context_seen=true`
  - `deck_audio_features_context_seen=true`
  - `audio_part_context_seen=true`
  - raw `audio_window_context[...]` and `audio_window_map` are present
  - `audio_window_context_seen=true`
  - `audio_window_map_seen=true`
  - `deck_audio_capture=A_silent+B_silent`
  - `deck_audio_features=A_silent_rms_0.000+B_silent_rms_0.000`
  - `deck_source_status.controller=present`
  - `deck_source_status.controller_connection=disconnected`
  - raw `deck_lanes_context[...]` is present
  - raw `deck_reference_context[...]` is present
  - raw `deck_source_context[...]` is present
  - `deck_lane_context_seen=true`
  - `deck_reference_context_seen=true`
  - `deck_source_context_seen=true`
  - `transition_gate_seen=true`
  - `deck_lane_evidence_seen=true`
  - `deck_reference_evidence_seen=true`
  - `deck_source_evidence_seen=true`
  - `deck_lanes=A_unknown_route_unknown+B_unknown_route_unknown`
  - `deck_reference=deck1_A_unknown_route_unknown+deck2_B_unknown_route_unknown`
  - `deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none`
  - `deck_lane_route_evidence_seen=false`
  - `deck_reference_route_evidence_seen=false`
  - remaining blockers are physical: no resolved/citable deck row, no recent
    controller move, no active deck audio lane, no per-deck delta
    context/evidence, no observed master audio, no bounded `audio_delta`, and
    no concrete route tiers because the sample had no connected controller
    posture or resolved deck rows.
- `uv run python -m vibemix library verify-live-reply --live-context-file .planning/research/live-context-latest-proof.json --reply 'Great transition, clean handoff.' --json`
  - rejected the reply with `unsupported_live_outcome_claim` and
    `proof_not_ready`
  - returned `transport_status=fresh_schema_v2`
  - corrected public copy to the calm held-state reply.
  A second verifier run against confession-style prose (`I need to correct the
  live read...`) also corrected to the same calm public state:
  `I caught the live move. The useful note is the sound change right there.`
  The live runtime was stopped after sampling.
- Runtime socket follow-up: configured Deck A/B capture now forces
  `audio_window_context[...]` and `audio_window_map` on silent frames too, so
  the old/current/action/future context rides the raw live packet whenever real
  deck-pair capture is configured. Verification:
  `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py::test_configured_deck_pair_capture_forces_audio_window_on_silent_frame tests/runtime/test_ws_bus_deck_state.py::test_payload_marks_configured_deck_pair_capture tests/library/test_live_context_cli.py::test_viber_live_context_readiness_ignores_untrusted_audio_window_context`
  passed with 3 tests;
  `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/state/test_deck_context.py`
  passed with 183 tests; Ruff passed on the touched runtime/guard/test files;
  and `git diff --check` passed.
- Source-status follow-up: DeckPoller now emits
  `controller_connection=connected|disconnected|unavailable` separately from
  `controller=present|missing`. This keeps "controller-state reader is wired"
  from sounding like "controller hardware is live" in Viber/Gemini prompt
  context. Source-status-only frames now also render diagnostic
  `deck_lanes_context[...]`, `deck_reference_context[...]`,
  `deck_source_context[...]`, and negative
  `deck_lanes=...unknown_route_unknown`,
  `deck_reference=...unknown_route_unknown`, and
  `deck_source=...unknown_src_none` evidence atoms, which let Viber cite Deck
  A/B context absence without upgrading it into proof. Verification:
  `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 206 tests; Ruff passed on the touched source-status files.
  The later lane/reference follow-up passed
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  with 186 tests, and Ruff passed on the touched deck-context/runtime files.

Verification:

- `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py`
  - 78 passed.
- `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  - 186 passed.
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
   `audio_window_map`, recent move, master audio, `audio_delta`, configured
   deck-pair capture, a `deck_audio_capture=...` activity receipt, and at
   least one active deck audio lane.
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

- The current local Vibemix proof sample was refreshed while a live session was
  started from this worktree with `BlackHole 16ch`, four opened channels, and
  `VIBEMIX_DECK_AUDIO_CHANNELS=A=0,1;B=2,3`:
  `uv run python -m vibemix library live-context --wait-ready 2 --interval 1 --json --out .planning/research/live-context-latest-proof.json`.
  The artifact now proves the runtime socket path is fresh: `ok=true`,
  `frames_seen=20`, schema v2, `missing_capabilities=[]`,
  `deck_pair_capture_configured=true`, `deck_audio_features_context_seen=true`,
  `deck_audio_capture=A_silent+B_silent`, and
  `deck_audio_features=A_silent_rms_0.000+B_silent_rms_0.000`.
  It still correctly reports `readiness.diagnosis=missing_physical_proof`
  because the sample was silent: no resolved/citable deck row, no recent
  controller move, no active deck audio lane, no per-deck delta context/evidence,
  no audible master audio, and no bounded `audio_delta`. Source diagnostics
  loaded the folder-cache library with 1547 tracks, found rekordbox 7 and
  `master.db`, and kept live DB reads disabled by policy. The live process was
  stopped after sampling.
- The result-boundary correction copy no longer exposes a self-correction
  essay to the DJ. Public replies are now short product states such as
  `I caught the live move. The useful note is the sound change right there.`
  Detailed deck lanes/source/provenance remain in structured
  guard summaries, logs, and `live_verification`. Verification:
  `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_linter.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/test_main_smoke.py`
  passed with 256 tests, `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 98 tests, `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 56 tests, `uv run ruff check ...` passed, and
  `git diff --check` passed.
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

## Follow-up: Deck Part Audio Window Bridge

The Library/Viber bridge now preserves the Deck A/B Part-aware audio window
shape instead of accepting only the older `deckA_audio=not_attached` form.

Changed:

- `src/vibemix/library/codex_curate.py` accepts structured
  `audio_window_map` packets where `deckA_audio=P2`,
  `deckB_audio=P3`, `per_deck_audio=deck_pair_parts`, and
  `duplicate_audio=separate_deck_pair_parts`, with
  `deck_audio_separation=deck_audio_separation_context`.
- The rendered Viber prompt line now keeps those Deck Part labels instead of
  hardcoding `deckA_audio=not_attached` / `deckB_audio=not_attached`.
- `tauri/ui/src/library/api.ts` accepts the same Deck Part window shape and
  preserves `deck_part_span_s` plus `deck_part_activity` through the webview
  live-context normalizer.
- `tauri/ui/src/library/chat.test.ts` now proves a deck-pair live context sends
  the P2/P3 `audio_window_context` and `audio_window_map` into `libraryChat`.
- `tauri/ui/src/library/index.ts` now treats `audio_part_context` and
  `deck_audio_separation_context` as volatile live fields. If a later live
  frame omits the Deck A/B Part contract, the Library chat context clears the
  stale P2/P3 role labels instead of letting Viber reason from old deck-audio
  attachment state.
- `library live-context --json` now also emits a bounded `setup_hint` when a
  Rekordbox deck-output route is found but the live proof is not ready. On this
  machine it reports `deck_channels=A=0,1;B=2,3`, recommends
  `VIBEMIX_INPUT_DEVICE='BlackHole 16ch'` plus
  `VIBEMIX_DECK_AUDIO_CHANNELS=auto`, and labels the packet
  `rule=setup_hint_not_live_audio_proof`.
- If `VIBEMIX_DECK_AUDIO_CHANNELS=auto` finds Deck A/B output pairs but the
  selected capture device/opened stream is too narrow, the deck map now fails
  closed instead of exposing a partial A-only capture. The separation packet
  carries `required_opened_channels=4`,
  `capture_reason=capture_device_too_few_channels` or
  `capture_reason=opened_channels_too_few`, plus a matching `setup_block=...`.
  Proof readiness then names this as a setup block, not live deck audio.

Verification:

- `uv run pytest -q tests/library/test_codex_curate.py::test_chat_prompt_preserves_deck_pair_audio_window_map tests/library/test_codex_curate.py::test_chat_prompt_includes_bounded_live_deck_context_guard`
  - 2 passed.
- `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  - 100 passed.
- `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py`
  - passed.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 62 passed after adding the stale Deck A/B Part-context clearing regression.
- `npm --prefix tauri/ui run build`
  - passed.
- `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  - 230 passed after adding the setup-hint regression.
- `git diff --check`
  - passed.
- `uv run pytest -q tests/library/test_live_context_cli.py tests/audio/test_deck_capture.py`
  - 39 passed after adding the setup-hint regression.
- `uv run pytest -q tests/audio/test_deck_capture.py::test_deck_audio_routing_auto_reports_too_narrow_capture_device tests/state/test_deck_context.py::test_deck_audio_separation_context_marks_too_narrow_auto_capture tests/library/test_live_context_cli.py::test_viber_live_context_readiness_names_too_narrow_deck_capture_device`
  - 3 passed.
- `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/library/test_live_context_cli.py`
  - 102 passed after adding the too-narrow capture setup-block regression.
- `uv run ruff check src/vibemix/audio/deck_capture.py src/vibemix/state/deck_context.py src/vibemix/__main__.py tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/library/test_live_context_cli.py`
  - passed.
- Historical recall now treats per-deck capture deltas as valid
  move-plus-sound-change evidence for `MIX_MOVE` recall. A controller move with
  `audio_capture_context.deck_audio_deltas` can trigger the same bounded
  memory comparison as a global `audio_delta`, while heartbeat/no-move turns
  still stay out of the embed path. This keeps "knob move -> Deck A/B changed"
  history useful without embedding every controller twitch or treating memory as
  current proof.
- `uv run pytest -q tests/memory/test_retrieval.py tests/memory/test_ingest.py`
  - 17 passed after adding the per-deck-delta recall gate.
- `uv run pytest -q tests/memory/test_no_live_path_import.py tests/memory/test_no_extraction.py`
  - 5 passed, proving the memory path still has no live-path import or
    generation surface.
- `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_coach.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/memory/test_retrieval.py tests/memory/test_ingest.py`
  - 265 passed.
- Proof readiness and the Library UI live-read badge now require both captured
  deck lanes to be active before calling the deck-pair proof armed. A packet
  with configured deck-pair capture but only `deck_audio_capture=A_active+B_silent`
  stays partial and reports `deck_audio_capture did not show active audio on
  both deck lanes`. This prevents a one-deck audible capture from looking like
  the full "deck one here / deck two here" state.
- The Library UI live-read badge now mirrors the backend's deck-pair proof gate:
  active Deck A/B audio is not enough by itself. It also requires both Deck A
  and Deck B identities, citable track IDs, and trusted source provenance before
  showing `armed`. If Deck B is still unknown, the badge stays calmly partial
  instead of exposing a self-correction/confession-style Viber reply to the user.
  Verification:
  `npm --prefix tauri/ui test -- src/library/chat.test.ts` passed with 27 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 64 tests; `npm --prefix tauri/ui run build` passed; and
  the focused Python public-reply scrub regressions in
  `tests/library/test_codex_curate.py` passed with 3 tests; `git diff --check`
  passed.
- Public Viber replies are now scrubbed for debug/proof labels even when the bad
  text is not phrased as an explicit transition verdict. Replies containing
  `resolved decks=...`, `live evidence gate:...`, `transition_block=...`,
  `claim_policy=...`, `guard_violations`, or similar internal proof labels are
  rewritten to calm public copy while the details stay in `live_verification`.
  Non-live library/crate turns that accidentally receive a live-outcome claim
  now fall back to the grounded library result instead of showing the live
  hallucination. Verification:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py`
  passed with 189 tests;
  `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed; and `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 66 tests.
- The Gemini attached-audio contract now matches the actual Part layout. P1-only
  turns say `deck_audio_parts=not_attached`; turns with configured Deck A/B
  Parts say `deck_audio_parts=attached_configured_deck_pair_refs deckA_audio=P2
  deckB_audio=P3 ... deck_parts_rule=reference_not_quality_verdict`. The stale
  phrase `optional_later_parts_not_current_deck_audio` is now forbidden in the
  co-host tests, so Gemini is not given contradictory instructions when it is
  actually receiving clean deck-reference audio.
  Follow-up: the contract now also covers mic/lookahead turns where Deck A/B are
  not P2/P3. `audio_part_context[...]` carries `part_order=...`, so with mic and
  source-file lookahead the prompt can say `part_order=P1,P2,P3,P4,P5` with Deck
  A/B on P4/P5. The final `AUDIO PART CONTRACT` now says
  `deck_separation=deck_pair_parts` whenever Deck A/B audio Parts are attached,
  and both Python and webview validators keep the full P1+mic+lookahead+Deck A/B
  label line under a 1400-char cap. The same validators now reject partial or
  conflicting deck-pair maps: `deckA_part` and `deckB_part` must both exist, be
  distinct, appear in `part_order`, and each Part label must map only to its
  configured deck capture role. This prevents a reused mic/lookahead label or a
  one-deck-only map from being treated as clean Deck A/B audio context.
  `audio_window_context[...]` and structured `audio_window_map` now apply the
  same distinct-label rule for `deckA_audio=P...` / `deckB_audio=P...`, so the
  old/current/action map cannot point both decks at one attached audio Part.
  Renderer-side follow-up: if upstream labels are partial, colliding, or reuse a
  mic/lookahead Part, the audio-part renderer, audio-window text/map renderers,
  and final co-host `AUDIO PART CONTRACT` now fall back to `not_attached` /
  `structured_text_only` rather than emitting a contradictory deck-pair packet.
  Verification:
  `uv run pytest -q tests/agent/test_dj_cohost.py::test_llm_node_03a_fences_cold_p1_audio_with_claim_policy tests/agent/test_dj_cohost.py::test_llm_node_audio_map_reflects_configured_deck_pair_capture tests/agent/test_dj_cohost.py::test_llm_node_attaches_configured_deck_audio_parts_on_mix_move tests/agent/test_dj_cohost.py::test_llm_node_03b_places_deck_audio_map_next_to_audio_part`
  passed with 4 tests; `uv run pytest -q tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_cache_hit.py`
  passed with 54 tests; and
  `uv run ruff check src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost.py`
  passed.
  Latest focused verification:
  `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/runtime/test_ws_bus_deck_state.py`
  passed with 247 tests;
  `uv run ruff check src/vibemix/agent/dj_cohost.py src/vibemix/state/deck_context.py src/vibemix/library/codex_curate.py tests/agent/test_dj_cohost.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed; `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 69 tests; and `npm --prefix tauri/ui run build` passed.
- Memory/history hygiene now applies the same "past comparison, not live proof"
  intent to unsafe deck-pair audio-window labels. If a stored or recall-query
  `audio_window_context[...]` tries to point `deckA_audio` and `deckB_audio` at
  the same Part label, or claims a partial/colliding deck-pair map, ingest and
  retrieval replace that packet with `audio_window=omitted_untrusted_audio_window`.
  This keeps old move/audio memories useful for similarity while preventing
  cached text from sounding like current Deck A/B proof.
- Viber live-context normalization now also checks cross-packet Part-label
  consistency. Individually valid packets are not enough: if
  `audio_part_context[...]` says Deck A/B are `P4/P5`, then
  `audio_window_context[...]` and `audio_window_map` must also say `P4/P5`.
  Mismatched or deck-pair windows without a matching audio-Part contract are
  dropped, and the prompt renderer recomputes a matching audio window from the
  validated Part labels. This prevents the LLM from seeing two different deck
  maps in one turn.
- The `library live-context --require-proof` readiness gate now reports that
  same condition explicitly as
  `audio_part_window_labels_consistent=false`. A proof packet with otherwise
  valid deck rows, controller posture, deck-pair capture, features, deltas, and
  live evidence is still not ready if its audio Part labels disagree with the
  audio window/map labels; the blocker names the contradiction instead of
  hiding it behind a generic missing-map failure.
- Viber's positive `supported_verdict` path now requires the same coherent
  packet, not only strong-looking `live_evidence` tokens. A quality grade needs
  valid `deck_audio_separation_context`, `deck_audio_features_context`,
  `deck_audio_delta_context`, `audio_part_context`, `audio_window_context`, and
  `audio_window_map`, with Deck A/B Part labels agreeing across all of them.
  If the evidence tokens look strong but the Part/window/map contract is absent
  or contradictory, Viber falls back to candidate-only language and drops move
  grades.
- Gemini's live cohost now applies the same "attached Deck A/B Parts this turn"
  boundary before it tells the model or the post-model guard that a transition
  verdict is supported. Strong deck-pair capture/features/deltas still appear as
  context, but if the actual Gemini `contents` array only carries P1 master
  audio, the prompt policy is downgraded to
  `candidate_not_verdict reason=deck_audio_parts_not_attached` and any attempted
  public "Great transition" reply is replaced by the calm candidate-held line.
  The raw reason is logged in the guard event; the DJ does not hear AI
  self-confession or proof diagnostics.
  Verification:
  `uv run pytest -q tests/agent/test_dj_cohost.py::test_llm_node_downgrades_verdict_when_deck_audio_parts_not_attached tests/agent/test_dj_cohost.py::test_llm_node_attaches_configured_deck_audio_parts_on_mix_move tests/state/test_deck_context.py::test_live_claim_guard_requires_attached_deck_audio_parts_when_requested tests/state/test_deck_context.py::test_live_claim_guard_allows_verdict_with_citable_deck_pair_audio_delta`
  passed with 4 tests; `uv run pytest -q tests/agent/test_dj_cohost.py tests/state/test_deck_context.py`
  passed with 119 tests; `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 113 tests; and `uv run ruff check src/vibemix/agent/dj_cohost.py src/vibemix/state/deck_context.py tests/agent/test_dj_cohost.py tests/state/test_deck_context.py`
  passed.
- Viber public reply hygiene now treats model self-correction/self-blame as an
  internal guard event, not chat copy. Public replies that say things like
  "my mistake on the live read" or "I'm not sure from this live read" are
  normalized to the same calm held live-moment response; the raw guard reason
  stays in `live_verification.guard_violations` for the tool/proof surface.
  Follow-up hardening also catches more natural self-diagnosis/confession
  variants such as "my bad on the live read", "I was wrong", "I messed up",
  "I shouldn't have called that", "that was dumb", and "I overclaimed". These
  remain audit/proof events, never DJ-facing chat copy.
  Verification:
  `uv run pytest -q tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/memory/test_no_live_path_import.py tests/memory/test_no_extraction.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 288 tests;
  `uv run ruff check src/vibemix/memory/ingest.py src/vibemix/memory/retrieval.py src/vibemix/library/codex_curate.py tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/library/test_codex_curate.py`
  passed; and `git diff --check` passed. Latest cross-packet follow-up:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/runtime/test_ws_bus_deck_state.py`
  passed with 245 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 71 tests; `npm --prefix tauri/ui run build` passed; and
  `uv run ruff check src/vibemix/__main__.py src/vibemix/library/codex_curate.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed.
  Latest self-diagnosis variant verification:
  `uv run pytest -q tests/library/test_codex_curate.py::test_chat_with_codex_normalizes_public_live_self_confession tests/library/test_codex_curate.py::test_chat_with_codex_normalizes_public_live_self_diagnosis_variants tests/library/test_codex_curate.py::test_chat_with_codex_normalizes_public_live_diagnostics_without_transition_claim tests/library/test_live_context_cli.py::test_cmd_library_verify_live_reply_rejects_public_debug_labels`
  passed with 7 tests; `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 118 tests; `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 72 tests; and `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py`
  passed.
- Viber/Gemini now have a positive `supported_verdict` state instead of only a
  block/candidate ladder. A transition quality reply or move grade is allowed
  only when the turn has recent move context, citable Deck A/B identity, trusted
  source provenance, both-active deck-pair audio, per-deck features, and
  audio-delta evidence. Missing any of those keeps the old candidate/held
  behavior. This addresses the user's "not just banning great transition"
  boundary: strong proof can score; weak proof cannot bluff.
  Verification:
  `uv run pytest -q tests/state/test_deck_context.py::test_live_claim_guard_allows_verdict_with_citable_deck_pair_audio_delta tests/state/test_deck_context.py::test_live_claim_guard_keeps_candidate_when_deck_pair_audio_delta_missing tests/state/test_deck_context.py::test_deck_audio_context_marks_two_deck_route_as_candidate_support`
  passed with 3 tests;
  `uv run pytest -q tests/library/test_codex_curate.py::test_chat_with_codex_live_evidence_candidate_blocks_quality_grade tests/library/test_codex_curate.py::test_chat_with_codex_allows_quality_grade_with_strong_deck_pair_proof tests/library/test_codex_curate.py::test_chat_with_codex_corrects_candidate_quality_verdict`
  passed with 3 tests;
  `uv run pytest -q tests/agent/test_dj_cohost.py::test_llm_node_attaches_configured_deck_audio_parts_on_mix_move`
  passed with 1 test;
  `uv run pytest -q tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_cache_hit.py`
  passed with 186 tests; and
  `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/library/codex_curate.py src/vibemix/agent/dj_cohost.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py`
  passed.
- The Library UI now carries the positive proof state as user-facing grounded
  copy: `supported_verdict` renders as `scoring grounded`, and an allowed move
  grade adds `move scoring grounded by live read`. Raw `claim_policy` labels
  remain hidden from the chat chrome.
  Verification:
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 66 tests, and `npm --prefix tauri/ui run build` passed.
- The state-level `supported_verdict` gate now requires deck identity sources
  from the trusted allow-list (`rekordbox_xml`, `folder_cache`, `screen_vision`,
  `numpy_key`, `nowplaying`). Arbitrary source strings no longer unlock scoring;
  they stay candidate-only even with Deck A/B audio, features, and deltas. The
  Python Viber/backend and live-proof CLI now share
  `DECK_CONTEXT_TRUSTED_SOURCES` with the state guard, so trusted-source
  semantics cannot quietly diverge between the prompt guard and proof surfaces.
  Verification:
  `uv run pytest -q tests/state/test_deck_context.py::test_live_claim_guard_allows_verdict_with_citable_deck_pair_audio_delta tests/state/test_deck_context.py::test_live_claim_guard_requires_trusted_sources_for_supported_verdict tests/state/test_deck_context.py::test_live_claim_guard_keeps_candidate_when_deck_pair_audio_delta_missing`
  passed with 3 tests;
  `uv run pytest -q tests/library/test_codex_curate.py::test_chat_with_codex_allows_quality_grade_with_strong_deck_pair_proof tests/library/test_codex_curate.py::test_chat_with_codex_requires_trusted_sources_for_quality_grade tests/state/test_deck_context.py::test_live_claim_guard_requires_trusted_sources_for_supported_verdict`
  passed with 3 tests;
  `uv run pytest -q tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_cache_hit.py`
  passed with 188 tests; and
  `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/library/codex_curate.py src/vibemix/agent/dj_cohost.py src/vibemix/__main__.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py`
  passed; `git diff --check` passed.
- The Rust/Tauri library command bridge test now preserves
  `deck_audio_features_context`, `deck_audio_delta_context`, and
  `audio_window_map` alongside `audio_part_context`, so the desktop
  `library_chat` command path is pinned to the same full live-context packet as
  Python and the webview.
- `deck_audio_window_context[...]` now has a matching citable
  `deck_audio_window=...` receipt in `live_evidence.mix` and `live_evidence.refs`.
  The receipt is intentionally compact: per deck it records the pre/current RMS
  window, not a quality judgment. Viber readiness, the Library live-proof badge,
  and the `supported_verdict` gate now require it; MIX_MOVE memory recall also
  accepts `deck_audio_windows` as the "move plus sound changed" proof leg. This
  keeps uncertainty and proof bookkeeping internal while the public answer stays
  calm instead of confessing that the AI is unsure or correcting itself.
  Verification:
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_coach.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/memory/test_retrieval.py`
  passed with 228 tests;
  `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 72 tests;
  `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/__main__.py src/vibemix/library/codex_curate.py src/vibemix/memory/retrieval.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_coach.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/memory/test_retrieval.py`
  passed;
  `npm --prefix tauri/ui run build` passed; and `git diff --check` passed.
- Follow-up: the receipt is now citable in the live prompt spine, not only visible
  in socket/UI packets. `state_refresh_loop` threads the shared
  `audio_capture_context` into `live_mix_evidence_keys(...)`, so the
  `EvidenceRegistry` records the same `deck_audio_window=...` atom as Viber/UI.
  `AICoach.build_prompt(...)` also receives the deck capture context, allowing
  `grounding_refs[...]` to include `[mix:deck_audio_window=...]`. This matters
  because Gemini's useful context must be both visible and citable; otherwise a
  clean per-deck audio map could still fail the anti-hallucination spine.
  Verification:
  `uv run pytest -q tests/agent/test_dj_cohost.py tests/state/test_coach.py tests/state/test_deck_context.py tests/state/test_refresh.py`
  passed with 242 tests;
  `uv run pytest -q tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/memory/test_retrieval.py tests/test_main_smoke.py`
  passed with 177 tests;
  `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 72 tests; and focused Ruff checks passed.
- Follow-up: the runtime event handoff now attaches `audio_capture_context` to
  `ev.extra` before `agent.set_next_event(ev)`. This preserves the intended
  cheap history path: recall pre-dispatch sees the same Deck A/B audio windows
  and deltas that the Gemini prompt and Viber UI see, so a MIX_MOVE can be
  learned as "move plus sound changed" instead of embedding naked controller
  twitch text. The state tracer's live-evidence context also renders with the
  deck capture context.
  Verification:
  `uv run pytest -q tests/runtime/test_coach.py tests/agent/test_dj_cohost.py tests/state/test_coach.py tests/state/test_deck_context.py tests/state/test_refresh.py tests/memory/test_retrieval.py`
  passed with 268 tests; focused Ruff checks passed; and `git diff --check`
  passed.
- Follow-up: `DeckPoller` now carries a previous independently resolved deck as
  `source=last_known` for lane context only. It is capped at confidence `0.29`,
  expires after 30 minutes, requires the controller to still be connected, and
  writes `last_known_rule=context_only_not_current_identity_proof`. Viber keeps
  that source through normalization so prompts can say "Deck A last-known
  Strobe", but `last_known` is deliberately outside
  `DECK_CONTEXT_TRUSTED_SOURCES`, below `DECK_CONTEXT_MIN_CONF`, and excluded
  from second-deck identity proof. Public Viber and shared Gemini/live-coach
  copy were also tightened again: self-diagnosis such as "my bad", "I was
  wrong", "I overclaimed", or "I'm doing something stupid about the live read"
  is normalized to calm product language; the details stay in diagnostics such
  as `live_verification`, `tool_trace`, and guard summaries.
  Verification:
  `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 240 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 72 tests;
  focused Ruff checks passed; and `git diff --check` passed.
- Follow-up: the Gemini audio Part contract now exposes the estimated model
  audio-token budget for the actual attached Parts. `audio_part_context[...]`
  includes per-Part estimates for P1, mic, lookahead, and Deck A/B Parts, plus
  `model_audio_tokens_est=...`; the live `llm_invoke` event logs the same
  estimate as `audio_tokens_est`. This follows Gemini's documented 32 audio
  tokens/sec rate and keeps the low-cost arrangement visible: static
  persona/rules stay cacheable, while volatile P1/deck/mic/lookahead audio is
  short, event-gated per-turn context. The move-effect context is also richer:
  when deck-pair capture has per-lane deltas/windows, the prompt/event payload
  now carries `deck_deltas=...` and `deck_windows=...` beside the user's recent
  move. That directly encodes "user moved A_low; Deck A changed like this; Deck
  B changed like this" without promoting it to causality or a quality verdict.
  Verification:
  `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/runtime/test_coach.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 267 tests;
  `uv run pytest -q tests/audio/test_deck_capture.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_cache_hit.py tests/state/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_refresh.py tests/memory/test_ingest.py tests/memory/test_retrieval.py`
  passed with 173 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 72 tests;
  focused Ruff checks passed; and `git diff --check` passed.
- `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_coach.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/memory/test_retrieval.py tests/memory/test_ingest.py`
  - 266 passed after tightening both-lane active proof.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  - 63 passed after adding the "both decks active" live-read partial regression.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml`
  - 116 passed.
- `npm --prefix tauri/ui run build`
  - passed.
- `uv run python -m vibemix library live-context --wait-ready 3 --interval 1 --json --out .planning/research/live-context-latest-proof.json`
  - with no live runtime: exits non-zero with `live_socket_missing` and still
    includes `source_status.rekordbox_deck_routing_hint` / `setup_hint`
  - with the routed live runtime above: connects to the schema-v2 socket and
    proves configured Deck A/B capture plus raw audio-window context/map, then
    exits non-zero only because the remaining proof legs require real audio,
    deck rows, and a recent control.

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
5. Configured deck-pair capture with `deck_audio_capture=...`,
   `deck_audio_features=...`, `deck_audio_delta=...`,
   `deck_audio_window=...`, and active Deck A and Deck B audio lanes.
6. Viber/Gemini asked about that move.
7. The response naming deck/control evidence without inventing a transition.

## Safe Continuation

1. Start the live session with real DJ audio and controller attached.
2. Run:
   `uv run python -m vibemix library live-context --json --require-proof --out .planning/proofs/live-context-<date>.json`
3. If readiness fails, fix only the missing proof leg shown in
   `readiness.blockers`.
4. Once proof passes, ask Viber and Gemini about a single-deck move and capture
   both the prompt evidence packet and the corrected response.
5. Keep MCP/tool-flow changes in the separate Viber agent mapping session.
