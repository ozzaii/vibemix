# Live Deck Context for Viber and Gemini - Research Note

Date: 2026-05-29

## Decision

Use the app's existing live state as the primary deck reference:

- `MusicState.deck_state` for loaded per-deck identity, key, BPM, and confidence.
  The rendered prompt packet now carries a separate identity scope:
  `second_deck_identity=unknown_or_suppressed` for one resolved deck,
  `second_deck_identity=observed` for two resolved decks, and
  `identity_rule=do_not_invent_unresolved_decks` when a second identity is not
  independently present.
- `MusicState.audible_deck` / `deck_confidence` for what is currently audible.
- `deck_mixer` / `mixer_context` for bounded controller posture: per-deck
  volume/EQ/filter/play, crossfader, controller connection, and attribution
  confidence. This is evidence, not an outcome grade.
- `deck_lanes_context` for the clean "deck one here / deck two here" reference:
  each lane joins identity status, route tier, and controller posture in one
  bounded packet. Full/Viber/logged paths carry the detailed lane map; Gemini's
  diet prompt and audio-adjacent P1 map use the compact lane map so cheap
  turns still know "A known/B unknown" without leaving the 800-token cap.
- `deck_audio_context` for the clean audio arrangement Gemini/Viber should
  assume: the model hears the global booth/master mix, not isolated per-deck
  stems; deck routing is inferred from controller posture and must stay a
  reference frame, not a verdict.
- `deck_audio_separation_context` for the capture-capability contract:
  the current attached/captured audio is `P1_global_mix`, Gemini receives a
  mono downmix of that capture, `deckA_audio=not_captured`,
  `deckB_audio=not_captured`, `per_deck_audio=not_attached`, and
  `isolated_decks=false`. This is the explicit bridge between "deck1/deck2
  labels are structured text" and "the model is not hearing isolated deck
  channels." When a multichannel deck-pair route is configured, the same packet
  switches to `mode=deck_pair_capture_configured`, `deckA_audio=captured`,
  `deckB_audio=captured`, `per_deck_audio=captured_not_attached`, and a compact
  RMS activity receipt such as `deck_audio_activity=A_active+B_silent`. Gemini
  still uses one P1 master/global Part by default, but selected live-reaction
  turns can now attach short Deck A / Deck B audio Parts from the configured
  capture rings. The socket/Viber path also gets
  `deck_audio_features_context[...]` from the configured deck-pair capture:
  per-lane activity, RMS, peak, zero-cross rate, flux, and crest from the
  latest captured callback frame. Those descriptors are explicitly tagged as
  evidence, not a transition-quality verdict. It also gets
  `deck_audio_delta_context[...]` from the latest per-deck feature comparison,
  such as `A_delta=rms_rose_100pct_strong` /
  `B_delta=rms_fell_50pct_strong`, tagged
  `rule=deck_audio_delta_not_causal_proof`.
  The socket/Viber/Gemini prompt path now also gets
  `deck_audio_window_context[...]`, a cheap pre/current deck-pair feature
  packet. It compares an older lane window (`pre=-6.0..-1.0`) against the
  current action lane window (`current=-1.0..0.0`) and emits tokens such as
  `A_pre=...`, `A_current=...`, and `A_delta=...`. This is the user's
  "older part / current part" idea implemented as deterministic text labels,
  not as duplicate audio and not as a causal/quality verdict.
- `audio_part_context` for Gemini's attached audio Parts: P1 is the current
  live global mix, optional P2 can be Kaan's mic/user speech, optional P2/P3 can
  be source-file lookahead, and optional later Parts can be
  `deckA_configured_capture` / `deckB_configured_capture` when the deck-pair
  capture seam is active. This makes the "old/current/action/+3s" arrangement
  explicit without giving the model permission to treat future/lookahead as
  current audience evidence or deck-pair captures as quality verdicts.
- `deck_source_context` for the source/provenance ladder: live deck identity is
  read from `MusicState.deck_state`; the robust path is now-playing/controller
  attribution into the library cache; live `master.db` is not read; diagnostic
  event XML is not transition proof; and an unresolved second deck requires an
  independent source before it can support multi-deck outcome language.
- `deck_change_context` for moment-local history: recent move labels mapped to
  current deck routing and control tiers, e.g. "A low is now killed while deck A
  is dominant." This is the cheap bridge between "twisted a knob" and "what deck
  context did that affect"; it is not a quality grade.
- `move_effect_context` / `audio_delta` for bounded DSP evidence near a recent
  move: sub/low/mid/high/RMS/onset changes rendered from the existing
  `prev_perceive` snapshot and cached onto `MusicState.audio_delta` before
  `prev_perceive` advances. This gives the model a cheap "what changed in the
  sound" hint while explicitly saying it is not causal proof or a skill grade.
- EvidenceRegistry citable atoms for the same facts:
  - `midi:<move_key>@<t>` for recent controller moves.
  - `mix:deck_audio_support=<support>` and `mix:deck_route=<tiers>` for the
    controller-derived deck route.
  - `mix:second_deck_identity=unknown_or_suppressed|observed|blocked` so
    prompts and Viber have an explicit deck-identity capability signal, not
    just a transition gate.
  - `mix:deck_audio_capture=A_active+B_silent` when the optional deck-pair
    capture path is configured and RMS activity has been observed. This is
    capture activity, not a transition grade.
  - `mix:deck_audio_features=A_active_rms_0.020+B_silent_rms_0.000` when the
    optional deck-pair capture path has measured per-deck feature descriptors.
    This lets Viber cite per-deck audio activity without seeing or storing raw
    deck audio.
  - `mix:deck_audio_delta=A_rms_rose_100pct_strong+B_rms_fell_50pct_strong`
    when the optional deck-pair capture path has compared the latest callback
    against the prior one. This is per-deck change evidence, not proof that a
    move caused the change or that a transition was good.
  - `mix:move_scope=<scope>`, transition block/watch/candidate keys, and
    `mix:move_effect=<delta>` for move-local grounding. These are de-duped in
    the refresh loop and rendered as `grounding_refs[...]` only when the
    registry snapshot proves the atom exists.
- `recent_moves` / `ipc.session.snapshot.midi_events[].control` for bounded control evidence.
  Snapshot MIDI events are deltas: empty snapshots mean "no new controls in this
  frame," not "clear the prior move immediately."
- Rekordbox XML/cache for library grounding, never the live Rekordbox SQLCipher DB.
  On this machine `~/Library/Pioneer/rekordbox/master.db` exists and `file`
  reports opaque `data`, so the conservative implementation still avoids it.
  Official rekordbox support and manual pages document XML export/import and
  XML auto-export as the supported low-risk library-data path. They do not
  provide a stable public live deck-state DB contract for this use case.

The model can mention deck/control evidence, but multi-deck outcome claims
are gated by deterministic policy:

- one resolved deck -> block transition/blend/drop/handoff claims
- two decks loaded but single audible -> watch, do not claim
- two resolved decks plus audible mix/cross-deck route support -> candidate,
  not verdict
- candidate evidence may support "forming / possible transition" language, but
  praise or quality verdicts such as "great/clean/smooth transition" are still
  corrected unless stronger two-deck audio support exists.

This treats "great transition" as one example of an unsupported outcome class,
not as the only phrase to block.

Public language rule added 2026-05-30: proof/debug uncertainty stays internal.
If evidence is weak, Viber/Gemini must not say "I need to correct", "I'm not
sure", "I only have audible deck mix", or explain missing proof to the DJ.
The guard can still correct unsafe outcome claims, but the replacement sentence
must be grounded product copy about the move/sound shape, while the detailed
reason remains in `live_verification`, logs, and proof tooling.

Event-scope consistency rule added 2026-05-30: if a live event carries
`extra.audio_capture_context`, that same context must drive the task tail,
Gemini audio-adjacent prompt, stream deferral, and result guard. Agent-level
capture context is only the fallback. This prevents one turn from showing Deck
A/B capture/window proof to Gemini while the public guard evaluates an older or
empty context.

Supported-verdict proof rule added 2026-05-30: the shared live-claim gate now
requires the pre/current `deck_audio_window` packet before allowing
`supported_verdict`. Two trusted deck identities, two active deck lanes,
features, and deltas are necessary but not enough; without the old/current
deck-lane window, the public answer stays at transition setup/candidate
language. This keeps the user's "older part / current part / action moment"
context as a proof requirement rather than prompt decoration.

Deck-auto setup rule added 2026-05-30: `VIBEMIX_DECK_AUDIO_CHANNELS=auto` should
be practical, not a trap. If Rekordbox settings show Deck A/B on channels that
do not fit the default BlackHole 2ch input, and the user has not explicitly set
`VIBEMIX_INPUT_DEVICE`, the live runtime now attempts to upgrade to BlackHole
16ch before opening the stream. Explicit input-device choices remain pinned and
too-narrow explicit devices still produce setup blockers instead of false proof.
The proof CLI mirrors this: with the current local Rekordbox hint
`A=0,1;B=2,3`, the recommended setup env is now just
`VIBEMIX_DECK_AUDIO_CHANNELS=auto`; the proof artifact includes
`auto_upgrade_input_device=BlackHole 16ch` and an explicit fallback env map.

Local live proof update 2026-05-30: booting the runtime with
`VIBEMIX_DECK_AUDIO_CHANNELS=auto` now actually upgraded from BlackHole 2ch to
BlackHole 16ch and opened a 4-channel capture stream. A socket sample during
that run saw 58 frames and confirmed `deck_pair_capture_configured=true` plus
deck-audio separation, features, delta, and pre/current window contexts. The
capture was silent, so readiness correctly remained `missing_physical_proof`.
The delta context now emits `A_delta=no_clear_delta` / `B_delta=no_clear_delta`
for stable lanes; this is context only, not citable transition evidence.

## Official Gemini Facts Used

Sources:

- Audio understanding: https://ai.google.dev/gemini-api/docs/audio
- Token guide: https://ai.google.dev/gemini-api/docs/tokens
- Context caching: https://ai.google.dev/gemini-api/docs/caching
- Live API capabilities guide: https://ai.google.dev/gemini-api/docs/live-guide
- Live API session management: https://ai.google.dev/gemini-api/docs/live-session
- Gemini models: https://ai.google.dev/gemini-api/docs/models/gemini
- Pricing: https://ai.google.dev/pricing

Relevant facts verified 2026-05-29 and rechecked 2026-05-30 from the current
docs:

- Gemini accepts audio as inline data or uploaded files.
- Inline audio belongs only under the 20 MB total request limit; larger or
  repeated samples should use the Files API.
- Supported audio includes WAV, MP3, AIFF, AAC, OGG Vorbis, and FLAC.
- Audio is represented at 32 tokens per second.
- Gemini downsamples audio to 16 Kbps and combines multi-channel audio to mono.
- Gemini does not limit the number of audio files in a single prompt, but the
  combined audio duration is capped by the documented audio length limit. So
  multiple Parts are valid, but their labels must be strict.
- The Live API realtime audio path accepts raw little-endian 16-bit PCM.
  Input audio is natively 16 kHz, but the Live API can resample other input
  rates when the MIME type carries the rate; output audio is 24 kHz.
- Live API docs list audio-only sessions as limited to 15 minutes unless session
  management techniques are used; context window limits are 128k tokens for
  native audio output models and 32k tokens for other Live API models.
- Context caching is the supported cost-reduction lever for repeated prompt
  prefixes; cache hits are reported in `usage_metadata`.
- Current Gemini docs describe implicit caching for Gemini 2.5+ models and
  explicit caching for repeated large prefixes. This supports the existing
  architecture: static persona/rules in cache, volatile deck/audio routing in
  the per-turn prompt.
- Official AlphaTheta/rekordbox support documents the `[Output Channel]`
  mapping for deck output selection, for example Output Deck1 and Output Deck2
  routing. That supports using local Rekordbox output-channel settings as setup
  hints only. It is not live audio proof until Vibemix actually opens and
  measures the matching capture channels.
- Current pricing docs list Gemini 2.5 Flash Native Audio (Live API) paid audio
  input at `$3.00 / 1M tokens` and audio output at `$12.00 / 1M tokens`.
  Standard `generateContent` audio prices vary by model tier and are lower for
  Flash/Lite than native-audio Live output. Treat all pricing facts as volatile
  and re-check before any launch/billing decision.
- Official docs rechecked on 2026-05-29:
  Gemini audio understanding says each second of audio is 32 tokens and the
  token-counting guide repeats the same fixed audio rate; the pricing guide
  currently lists Gemini 2.5 Flash standard audio input at `$1.00 / 1M tokens`,
  Gemini 2.5 Flash-Lite standard audio input at `$0.30 / 1M tokens`, and
  Gemini 2.5 Flash Native Audio Live API audio/video input at
  `$3.00 / 1M tokens`.

Implication for Vibemix:

- The current 6s diet window costs about 192 audio tokens.
- The current 18s full window costs about 576 audio tokens.
- A default 3s Deck A + 3s Deck B pair costs about 192 extra audio tokens, so
  the cheap shape is still P1 plus conditional short Deck A/B Parts, not a
  continuous native-audio session.
- Deck/control context should stay small text, not another audio/model pass.
- Audio Part labels should stay small text too: a single `audio_part_context`
  line describes P1/P2/P3 roles, while the actual audio stays one live P1 plus
  optional mic/lookahead Parts.
- Moment-local deck history should also stay small text: bounded recent move
  labels plus current route/control tiers, not a second audio model pass.
- Move-effect evidence should stay in the same budget discipline: reuse the
  existing perceive delta, cap to a few strings, and ship it on the live frame as
  `audio_delta` instead of sending another audio window to Gemini.
- Move-local audio timing should be text, not duplicate audio. The cheap shape
  is a temporal map around the already-attached master window:
  `P1_heard=true`, `timeline=past_action_future`, `pre=-Ns..-1s`,
  `current=-1s..0s`, `action=-1s..0s`, `move_anchor=<move>@-age`, and optional
  `future=0..+3s` only when the file lookahead Part is truly attached. Future
  spans are always labeled `future_heard=false`.
- Per-deck move timing should also be text first. The current implementation
  keeps a short deterministic feature history in the deck-pair capture object
  and emits `deck_audio_window_context[...]` from that history. This gives the
  model "older Deck A/B vs current Deck A/B" labels without another audio Part,
  without another model call, and without delaying the reaction.
- Exact citable refs should be small text copied from the registry snapshot.
  They are essentially free compared with another audio pass and give the
  linter a structural way to reject invented move/route claims.
- Long persona/profile/static grounding belongs in the existing Gemini context
  cache; volatile deck/move state stays in the per-turn prompt.
- Historical move memory is comparison material only. It should carry the
  `history=past_comparison_not_live_proof` label and may help retrieval
  similarity, but unsafe or contradictory Deck A/B audio-window labels must be
  omitted before entering prompts or recall queries.
- Audio-Part labels must be consistent across every packet in the same live
  turn. A valid `audio_part_context[...]` and a valid `audio_window_context[...]`
  can still be contradictory if one says Deck A/B are `P4/P5` and the other says
  `P2/P3`; Viber should drop/recompute the weaker window/map instead of feeding
  both to the model.
- Readiness/proof has to enforce the same rule. Otherwise the app could refuse
  contradictory context in chat while still writing a proof artifact that says
  the live deck/audio context is ready.
- Positive transition scoring should use the same threshold. Strong-looking
  `live_evidence` tokens are not enough unless the validated Part/window/map
  packets are present and mutually consistent.
- Guard/debug/self-correction language belongs in artifacts such as
  `live_verification`, not in the user-facing Viber reply. If the model produces
  "my mistake on the live read" or similar self-confession text, the result
  boundary should replace it with calm product copy while preserving the raw
  violation internally.
- Per-deck "hearing" must be represented as structured routing context unless
  we add true isolated deck capture. Gemini's audio guide says multi-channel
  audio is combined into one channel, so sending a stereo/master feed cannot be
  relied on as deck A/deck B separation.

## Local Audio/rekordbox Probe on 2026-05-29

Local CoreAudio devices relevant to capture/routing:

- `DDJ-FLX4`: 2 inputs, 4 outputs, 48000 Hz
- `BlackHole 16ch`: 16 inputs, 16 outputs, 48000 Hz
- `BlackHole 2ch`: 2 inputs, 2 outputs, 48000 Hz
- `rekordbox Aggregate Device`: 2 inputs, 6 outputs, 48000 Hz
- `Aggregate Device`: 0 inputs, 2 outputs, 48000 Hz

The default runtime uses `INPUT_DEVICE=BlackHole 2ch`, opens it with
`channels=2`, then averages input channels to mono before Gemini/state buffers.
Therefore the default system can label deck identity/control/routing, but it
does not capture isolated Deck A / Deck B audio.

The next runtime seam now exists and was physically booted against
`BlackHole 16ch` on 2026-05-29:

- `VIBEMIX_INPUT_DEVICE='BlackHole 16ch'`
- `VIBEMIX_DECK_AUDIO_CHANNELS='A=0,1;B=2,3'`

With that configuration, Vibemix opened a 4-channel stream and the live socket
advertised:
`deck_audio_separation_context[requested_device=BlackHole_16ch capture_device=BlackHole_16ch input_channels=16 opened_channels=4 sample_rate=48000 device_capacity=multichannel_available mode=deck_pair_capture_configured master_channels=0,1,2,3 current_capture=P1_global_mix_plus_deck_pairs gemini_audio=mono_downmix_of_master_capture deckA_audio=captured deckB_audio=captured per_deck_audio=captured_not_attached isolated_decks=runtime_capture_available deck_pairs=A:0,1+B:2,3 upgrade_path=attach_deck_pair_audio_parts_when_needed deck_audio_activity=A_silent+B_silent rule=separation_capability_not_outcome]`

The same live frame carried `live_evidence.mix` with
`deck_audio_capture=A_silent+B_silent`, proving the runtime callback updates
the capture-activity receipt through the socket path.

The local `rekordbox6/rekordbox3.settings` file also contains external-mixer
deck output routing evidence. The best current hint is
`audioDeviceManager_PerformanceMode_1178899479` with
`audioOutputDeviceName=Aggregate Device`, `MixerMode_Is_Internal=0`,
`OutputChannel_Deck0_L/R=0/1`, and `OutputChannel_Deck1_L/R=2/3`. Vibemix now
parses this as a setup hint:
`rekordbox_deck_routing_hint[... deck_outputs=A:0,1+B:2,3 ...]`. This is
deliberately not treated as live audio proof; it only says how rekordbox was
configured to output decks. The runtime can use it when explicitly requested
with `VIBEMIX_DECK_AUDIO_CHANNELS=auto`, while the default remains disabled
unless a real deck-capture map is configured.

This proves the app can open and label a configured deck-pair capture. It does
not yet prove a live DJ transition because the sample was silent and had no
resolved deck rows or recent controls. The remaining upgrade is not a prompt
trick; it is a real routed-audio and proof workflow:

1. route rekordbox/driver deck outputs into the configured BlackHole 16ch
   input pairs;
2. map device channels to deck lanes from explicit env config or the
   Rekordbox-settings routing hint (`VIBEMIX_DECK_AUDIO_CHANNELS=auto`);
3. attach or summarize deck-pair audio only after that mapping is proven;
4. keep `deck_audio_separation_context` as the capability receipt so Viber and
   Gemini know whether per-deck audio is real or not.

Official AlphaTheta/rekordbox docs support this distinction: rekordbox audio
settings expose deck output-channel routing, and external mixer mode can route
track decks to separate output channels. That is output routing evidence and a
good upgrade path, but it is not the same thing as Vibemix currently capturing
isolated deck audio.

## Local Implementation Map

- Audio Part structuring for Gemini:
  - `contents[0]` is always the text packet: static/cached system behavior,
    current task, compact evidence line, and the audio-adjacent deck map.
  - `contents[1]` is P1: the current live master/booth audio window
    (`audio/wav`). It is the audience-true global mix, not isolated deck stems.
  - Optional later Parts are separately labeled by the prompt suffix: mic audio
    only when Kaan recently spoke, and lookahead only when explicitly enabled as
    `NOT YET HEARD BY AUDIENCE`. Deck A/B audio Parts are appended only when
    `VIBEMIX_GEMINI_DECK_AUDIO_PARTS` permits it and the configured deck-pair
    capture has activity. `auto` is the default, bounded to useful event types
    such as `MIX_MOVE`; `off` disables it; `always` forces it. The window is
    bounded by `VIBEMIX_GEMINI_DECK_AUDIO_PART_SECONDS` at 1-6 seconds, default
    3 seconds. Each deck Part is labeled with activity computed from the same
    ring-buffer PCM slice encoded as attached audio, e.g.
    `P2_activity=deckA_active` / `P3_activity=deckB_silent`, so Gemini can
    treat a captured quiet lane as quiet instead of inferring a hidden blend.
  - `audio_part_context[...]` now carries the doc-backed
    `audio_token_rate=32_per_second` plus bounded per-Part estimates such as
    `P1_tokens_est=192` and `P2_tokens_est=96`.
  - The `AUDIO CONTEXT MAP FOR ATTACHED P1` sits immediately before the audio
    Part description and repeats only bounded live facts:
    `deck_context`, compact `deck_lanes_context`, `deck_source_context`,
    `mixer_context`, `deck_audio_context`, `deck_audio_separation_context`,
    `deck_audio_features_context`, `deck_audio_delta_context`,
    `audio_window_context`, `move_context`, `deck_change_context`,
    `move_effect_context`, `live_evidence`, and `claim_policy`.
  - `audio_window_context[...]` is the "old part / current move / +3s forward"
    contract. It labels P1 as the heard master/global mix with `P1_heard=true`,
    marks the packet as `timeline=past_action_future`, splits P1 into `pre`,
    `current`, and `action` spans, anchors recent user moves by age when
    available, and labels any lookahead Part as `future_heard=false` /
    `forecast_only_not_audience_evidence`. If no Deck A/B Parts are attached it
    states `deckA_audio=not_attached` and `deckB_audio=not_attached`, so
    duplicated master audio can never masquerade as clean deck stems. If Deck
    A/B Parts are attached, both `audio_window_context[...]` and the structured
    `audio_window_map` now say `deckA_audio=P2` and `deckB_audio=P3` with
    `per_deck_audio=deck_pair_parts`; they no longer contradict the attached
    audio by saying deck audio is `not_attached`. The source/limit fields are
    intentionally emitted before long `move_anchor` strings so the UI/Viber cap
    cannot clip away the anti-hallucination contract.
  - The runtime prompt now also carries an explicit `AUDIO PART CONTRACT`:
    `P1=live_global_mix isolated_decks=false
    deck_separation=structured_text_only
    audio_window_context=time_aligned`. The generic Part suffix labels P1 as a
    global mix rather than isolated deck stems, mic Parts as not deck audio,
    lookahead Parts as not current live deck audio, and configured deck-pair
    Parts as deck-contribution references rather than transition grades.
  - This shape follows the Gemini docs: audio is tokenized at 32 tokens/sec,
    multi-channel audio is combined to mono, and context caching is the cost
    lever for repeated prefixes. Therefore deck separation must come from small
    structured text, not from assuming Gemini can separate a stereo/master feed
    into Deck A and Deck B.
- Gemini prompt context: `src/vibemix/state/deck_context.py`,
  `src/vibemix/state/coach.py`.
- Citable live deck/move/audio evidence: `src/vibemix/state/refresh.py` writes
  bounded `midi` and `mix` atoms into `EvidenceRegistry`; `coach.py` renders
  only registered atoms as `grounding_refs[...]`.
- Gemini result boundary: `src/vibemix/agent/dj_cohost.py` applies the shared
  live claim guard and defers streaming when the policy is blocked, watch-only,
  or candidate-not-verdict.
- Historical/session understanding: `src/vibemix/runtime/coach.py` logs
  `deck_reference_context`, `deck_source_context`, `deck_audio_context`,
  `deck_audio_separation_context`, `deck_audio_features_context`,
  `deck_audio_delta_context`, `audio_window_context`, `audio_delta`,
  `move_context`, `deck_change_context`, and `move_effect_context` on move event
  rows; `src/vibemix/memory/ingest.py` includes those fields in deterministic
  `coach_line` signatures (`SIG_TEMPLATE_VERSION=v9-coach_line-deck-audio-context`)
  without doing extraction or another model call. `src/vibemix/memory/retrieval.py`
  and `src/vibemix/agent/dj_cohost.py` mirror `audio_window=`,
  `deck_audio_features=`, and `deck_audio_delta=` into recall queries, so
  "this knob/fader move changed the sound this way on deck A/B" can be compared
  to past move/effect memories without upgrading the current live claim policy.
  The recall-query cap for `audio_window=` is larger than the generic field cap
  so the safety atoms and the `move_anchor=<move>@-age` both survive.
  The mirrored `deck_ref=` field gives recall the plain "deck1=A/deck2=B"
  lane map alongside the older compact policy/evidence tokens.
- Evidence-level deck reference: `live_evidence.mix` / `refs` now also carry a
  compact `deck_reference=deck1_A_<identity>_route_<tier>+deck2_B_<identity>_route_<tier>`
  atom. This is the citable sibling of `deck_reference_context[...]`: small
  enough for the WS/Viber evidence cap, explicit enough to survive prompt
  summarization, and still not a transition verdict.
- Viber prompt/result boundary: `src/vibemix/library/codex_curate.py`; raw
  socket live-context dicts are adapted into `MusicState`/`DeckState` plus
  controller posture, then evaluated by the same shared deck-claim guard Gemini
  uses.
- Viber agent/MCP boundary: this work does not reshape the MCP tool spine,
  tool schemas, or Codex/Viber agent loop. It only cleans the live-context and
  historical-memory text entering that loop, then validates unsupported live
  claims on the way out. The separate "map Viber agent + MCP tool flow" effort
  can evolve tool orchestration without clashing with these context contracts.
- Desktop live context bridge: `tauri/src-tauri/src/ws_client.rs`,
  `tauri/src-tauri/src/library_cmds.rs`, `tauri/ui/src/library/api.ts`,
  `tauri/ui/src/library/index.ts`.
- Structured Viber live evidence bridge: the flat WS frame now carries
  `live_evidence.{mix,midi,refs}` from the same bounded `deck_context` helpers;
  `library live-context`, Tauri normalization, and the Viber prompt pass it
  through as evidence categories, not outcome claims.
- Time-window live bridge: the flat WS frame now also carries fresh
  `recent_moves` plus `audio_window_context[...]` while a move is inside the
  bounded context window. Tauri normalizes and forwards it as a transient
  `LibraryLiveContext.audio_window_context`; `library live-context --require-proof`
  now checks for `audio_window_context_seen`. This keeps the "old part /
  current action / lookahead" context on the real Viber transport, not only in
  Gemini's local prompt suffix.
- Citable deck-lane evidence: `live_evidence.mix`/`refs` now include compact
  atoms such as `deck_lanes=A_known_route_dominant+B_unknown_route_muted`, so
  Gemini and Viber can cite per-deck route/identity posture without converting
  the lane map into a transition verdict.
- Citable deck-source evidence: `live_evidence.mix`/`refs` now also include
  compact atoms such as
  `deck_source=deck1_A_known_src_folder_cache+deck2_B_unknown_src_none`. This
  gives the source/provenance ladder a citable sibling to
  `deck_source_context[...]`, and the cap ordering preserves it alongside
  lane/reference atoms and move-effect evidence.
- Compact MIX_MOVE prompt diet: Gemini's diet path keeps the event-specific
  `live_evidence[...]` in the task tail and suppresses the duplicate background
  packet from the compact evidence line for MIX_MOVE. The compact evidence line
  now also carries compact `deck_lanes_context[...]`, so a cheap move reaction
  has the same per-lane identity/route guard even if the attached-audio context
  map is not the only prompt surface. This stays under the existing 800-token
  proxy cap.
- Viber live-context sampler merge: proof sampling now merges bounded
  `live_evidence` packets across websocket frames instead of replacing them, so
  a citable `deck_lanes=...` atom and a transition gate cannot be observed and
  then silently dropped by a later partial frame. `--require-proof` now requires
  both rendered `deck_lanes_context[...]` and structured `deck_lanes=...`
  evidence.
- Viber physical proof hardening: `library live-context --require-proof` now
  also requires concrete controller posture for both deck A and deck B plus a
  citable `deck_lanes=...` atom with non-unknown route tiers. A connected
  controller flag alone is no longer enough to prove "deck one here / deck two
  here" routing context.
- Library UI live-context merge: browser chat state now merges incoming live
  deck frames before calling `libraryChat`, preserving prior deck identity,
  mixer posture, transient `audio_delta`, and citable `live_evidence` safety
  atoms. It also preserves the peak bounded `music` master-level scalar as
  global audio-presence evidence; this is not a deck stem, quality verdict, or
  policy upgrade. The UI normalizer also prioritizes `deck_lanes=...` and
  transition gates under its 9-token mix cap and 13-token ref cap.
- Library UI stale-deck clearing: explicit empty `deck_state`, `deck="none"`,
  or disconnected `deck_mixer` payloads are now preserved through normalization
  and treated as authoritative clears in the browser merge. Older deck identity
  and mixer posture no longer survive after the live socket stops proving them.
- Viber backend stale-deck clearing: the Python chat prompt normalizer also
  preserves explicit empty `deck_state`, `deck="none"`, and empty
  `deck_mixer` payloads. A clear frame therefore renders
  `transition_block=no_resolved_decks` and can correct stale "great
  transition" claims instead of disappearing before the result guard.
- Viber/browser audio-window trust boundary: raw `audio_window_context[...]`
  text is not accepted just because it has the right prefix. The browser
  normalizer and Python Viber boundary now require the core safety atoms
  `P1=master_global_mix`, `deckA_audio=not_attached`, and
  `deckB_audio=not_attached`, plus the deck-split limit atoms
  `per_deck_audio=structured_text_only`,
  `duplicate_audio=same_master_not_deck_split`,
  `deck_separation=deck_lanes_context`, and
  `lane_aliases=deck1:A,deck2:B`. They also reject explicit
  stem/attached/isolated-deck claims. When Python drops an untrusted packet,
  Viber recomputes a safe `audio_window_context[...]` from live state plus
  recent moves instead of forwarding the bad text into the prompt. The CLI proof
  readiness uses the same shared validator, so a raw context-poor packet cannot
  satisfy `audio_window_context_seen`.
- Viber backend evidence sanitizer: the final Python chat backend now uses the
  same safety-token priority under its 9-token mix cap and derives missing `mix:...`
  refs from `live_evidence.mix`, so direct CLI/Tauri payloads cannot lose the
  citable deck-lane or transition-gate atoms at the last prompt boundary.
- Viber chat-history sanitizer: prior chat turns are bounded before entering
  the Codex prompt, and stale Viber live outcome claims are omitted whenever the
  current live context is blocked, watch-only, or candidate-not-verdict. User
  wording remains dialogue, but older assistant phrases such as "great
  transition" no longer prime a fresh turn beside a single-deck evidence packet.
- Result-boundary correction hardening: shared Gemini guard code and the Viber
  chat wrapper now keep self-correction/proof language internal. Public Viber
  copy uses calm product states such as "I'll score it once both decks are
  locked" instead of exposing "I can't call that a transition"; a disclaimer
  also cannot smuggle in a fresh unsupported outcome claim such as "but that
  blend was clean."
- Viber move-grade artifact hardening: the same live claim policy now gates
  `move_grades` receipts at the backend result boundary. If the current live
  context is blocked, watch-only, candidate-not-verdict, or lacks enough
  evidence, positive transition/skill grade artifacts are dropped before
  `seen_track_ids` or the Library UI can surface them. Non-live grounded
  transition-prep grades still pass through.
- MIX_MOVE prompt cleanup: the Gemini task text now says a controller move was
  observed instead of "a move landed," and asks for bounded before/after sound
  changes rather than asking whether the move "landed." The shared result guard
  also corrects bare move-quality verdicts such as "That landed" when the only
  support is move-scoped DSP delta evidence.
- Unsupported outcome detection is category-based, not just the phrase "great
  transition." The shared/Viber guard treats switch, segue, handoff, bridge,
  layer, incoming/other-deck claims, and "incoming track came in clean" as the
  same multi-deck outcome class when the live policy is blocked or watch-only.
  The phrase grammar now lives in the shared `deck_context` helper so Gemini's
  streaming guard and Viber's Codex result wrapper cannot drift.
- Gemini prompt/memory symmetry: the same shared helpers now render
  `live_evidence[...]` inside full and compact `AICoach.evidence_line` prompts,
  session trace/event rows, and deterministic `coach_line` memory signatures.
- Per-deck reference memory: runtime event rows now include both
  `deck_lane_context` and `deck_reference_context`, and deterministic
  `coach_line` signatures use
  `SIG_TEMPLATE_VERSION=v6-coach_line-deck-reference`. This means future
  historical move recall can compare "deck1=A known/dominant, deck2=B
  unknown/muted, P1 is the global mix" rather than remembering only the raw
  controller label.
- Viber historical move lookup now uses the current compact lane map and
  citable `deck_lanes=...` evidence as cheap deterministic query tokens, so a
  past move in the same deck-one/deck-two route posture ranks above an otherwise
  similar move with the opposite route posture. This stays a raw memory scan:
  no extra model call and no upgrade from memory comparison to live proof.
- Viber historical move lookup also uses the current compact
  `deck_source_context[...]` source ladder as a high-priority deterministic
  query token. A past move with the same source/provenance posture now ranks
  above an otherwise similar move from a different source ladder, so historical
  "same knob/fader -> sound change" comparisons stay aligned with the same
  deck-identity limits used by live corrections.
- CLI proof path: `vibemix library live-context`. For physical verification,
  capture a durable audit packet with
  `uv run python -m vibemix library live-context --require-proof --out <path>.json`;
  the JSON contains the bounded live context, rendered preview, readiness
  checks/blockers, and local source diagnostics.

## Anti-Hallucination Rules

- Empty deck state emits no context.
- Low-confidence deck rows do not resolve.
- A single resolved deck must say the second deck identity is
  `unknown_or_suppressed`; this is an identity capability limit, separate from
  the transition block. The model may say "deck A is known" but must not invent
  "deck B" title/key/BPM or imply a second deck was involved.
- `deck_lanes_context[...]` is a lane map, not an outcome. It can support
  "deck A was known/dominant, deck B was unknown/muted" but never "good
  transition" by itself.
- `deck_reference_context[...]` is the plain deck-one/deck-two map:
  `deck1=A`, `deck2=B`, each lane's identity/route/controls, plus
  `audio=P1_global_mix`, `per_deck_audio=not_attached`, and
  `isolated_decks=false`. It is designed for Viber/Gemini to understand "deck
  one here, deck two here" without hallucinating isolated deck audio or turning
  that map into a transition verdict.
- `deck_source_context[...]` is a provenance map, not a transition cue. It must
  preserve `second_deck=independent_source_required` and
  `rule=unresolved_deck_is_not_transition_evidence` across prompt, socket,
  browser, CLI, and memory paths.
- Result-boundary corrections should keep compact lane evidence in structured
  diagnostics, not spoken copy. If the model says "great transition" from
  one-deck evidence, the guard summary carries details such as
  `deck lanes=A=known:dominant / B=unknown:muted` plus
  `deck source=... second_deck=independent_source_required
  rule=unresolved_deck_is_not_transition_evidence`, while the public reply stays
  short and calm.
- A self-correction is diagnostic, not user copy. "I can't call that a
  transition" is normalized to a calm held-state reply, and "I can't call it a
  transition, but that blend was clean" is also corrected because the second
  clause invents a multi-deck quality verdict.
- The blocked phrase class must generalize beyond `transition`: clean switch,
  clean segue, handoff, bridge, layer, other-deck/incoming-deck, and
  incoming-track-came-in claims are all multi-deck outcome claims unless the
  policy admits them.
- Empty session snapshots do not clear recent moves immediately. The UI keeps a
  short bounded window (8 seconds) and expires stale controls there; the CLI
  proof sampler keeps prior moves across empty deltas inside one sample.
- Mixer posture may support deck/control references, but it must not be promoted
  into a musical outcome claim without the deck-claim policy allowing it.
- Deck-audio context must always say `source=global_mix` and
  `isolated_decks=false` until there is a real isolated per-deck capture path.
- Deck-change context is history evidence only. It can support "you cut deck A
  lows while A was dominant/present/muted," but not "that was a good
  transition" by itself.
- Move-effect context is DSP evidence only. It can support "low/sub energy fell
  after the move window," but it must not be upgraded into causality or a quality
  verdict without the deck-claim policy allowing that claim category.
- `audio_delta` must be written by state refresh before `prev_perceive` is
  advanced, then read from the cached `MusicState.audio_delta` by prompt, WS,
  Viber, and event logging surfaces.
- `grounding_refs[...]` must be rendered only from atoms present in the current
  EvidenceRegistry snapshot. If the registry has no atom, the prompt should not
  hand the model a citation token to copy.
- `live_evidence[...]` may identify categories such as
  `transition_block=single_resolved_deck`, `deck_audio_support=single_deck_A`,
  `second_deck_identity=unknown_or_suppressed`,
  `move_scope=single_deck_move_A`, and recent MIDI refs. It is not a quality
  verdict and must not be treated as causality or skill proof.
- `live_evidence[...]` is allowed in Gemini and Viber prompts even when no
  citation token is registered; it is a compact category map. Bracketed
  citable refs remain gated by `grounding_refs[...]` / `EvidenceRegistry`.
- Viber's result-boundary guard treats `live_evidence` transition gates as
  authoritative with priority `transition_block` > `transition_watch` >
  `transition_candidate`, so a structured block can override a state-derived
  candidate before speech is returned.
- Result-boundary guard also enforces this category: if a response says a knob
  move "fixed/cleaned/caused/improved" the mix from `audio_delta` alone, the
  response is corrected to correlation-only language.
- Viber and Gemini should correct unsupported multi-deck outcome claims at the
  result boundary through the shared deck-claim policy, so synonyms such as
  transition/blend/handoff/bridge stay one evidence category.
- The direct Gemini path should repeat the bounded deck/audio gate immediately
  next to the attached P1 audio Part. `AICoach.build_prompt(...)` carries the
  full packet, but the final text part now adds `AUDIO CONTEXT MAP FOR ATTACHED
  P1` before the `Attached: P1 = ... live BlackHole audio` clause. This keeps
  `deck_audio_context`, `move_effect_context`, `live_evidence`, and
  `claim_policy` local to the audio Gemini is about to hear, without attaching
  raw MIDI/screen metadata as extra Parts.
- Historical move learning now uses the existing memory spine rather than a new
  generation call. `MIX_MOVE` recall is eligible only when both controller move
  labels and `audio_delta` are present, so the app can retrieve prior
  knob/fader -> sound-change signatures without embedding every controller
  twitch. When a diet `MIX_MOVE` turn has hot recall survivors, the prompt stays
  compact and adds a bounded `FROM A PAST SESSION` block plus a short recall
  instruction. This lets Gemini compare the current move in the live audio to a
  prior grounded move signature while keeping live evidence primary.
- Viber chat now gets the same concept through a zero-generation local memory
  scan. When live_context contains recent moves plus `audio_delta`, the Codex
  prompt adds `HISTORICAL MOVE CONTEXT` from local `memory.db` /
  `memory_moments.db` coach-line rows matching `event=MIX_MOVE`. The block is
  explicitly past-session comparison memory, not live proof, and cannot upgrade
  the current `claim_policy`. This keeps Viber cheap: no extra audio Part, no
  generation call, and no semantic embed on every chat turn.
- Historical memory prompt sanitizer: old `coach_line` signatures can predate
  the current audio-window contract or contain an old Viber phrase such as
  "great transition." A shared `deck_context` sanitizer now rewrites safe legacy
  `audio_window=audio_window_context[...]` snippets into the current
  master-mix/structured-text-only shape, omits snippets that claim attached
  stems or isolated decks, strips copied bracket citations, and removes stale
  past spoken multi-deck outcome claims unless they are honest self-corrections.
  Gemini's full recall block, Gemini's compact MIX_MOVE recall block, and
  Viber's `HISTORICAL MOVE CONTEXT` all use this same sanitizer. Scoring still
  uses the raw signature for retrieval, but rendered comparison memory cannot
  prime the current turn with fake stem or transition language.
- Deck-source provenance must survive the whole live-context path. Runtime
  frames now carry `deck_state.<side>.source`; the Tauri normalizer and Viber
  adapter only preserve allowed source tokens such as `rekordbox_xml`,
  `folder_cache`, `screen_vision`, `numpy_key`, and `nowplaying`. Viber renders
  this back as `src=...`, so a citable track row is not just "some title
  appeared" but a known source class.
- Local machine check on 2026-05-29: Rekordbox 7 is installed and local
  Rekordbox DB/Event files exist under the user Library, but vibemix's current
  title-resolution cache opens from `~/.cache/vibemix/library.pkl` with 1547
  tracks and `xml_path` pointing at a folder source. The deck poller now reports
  that case as `source=folder_cache`, not `source=rekordbox_xml`, so the prompt
  does not claim a Rekordbox XML provenance when the active cache is folder
  ingest.
- The `library live-context --json` result now includes a content-free
  `source_status` diagnostic. It reports the cache source/count, whether
  Rekordbox 7 and `master.db` are present, whether the local `rekordboxEvent.xml`
  files contain event/controller payload counts, and the explicit policy that
  vibemix does not live-read SQLCipher `master.db`.
- Local `rekordboxEvent.xml` check on 2026-05-29: the files exist, but both
  event/controller counts are `0`, so they do not currently provide independent
  deck A/B loaded-track identity. That means the honest live deck identity path
  remains app state + controller + nowplaying + cache enrichment, with the
  future `screen_vision` leg as the independent second-deck source once it clears
  the screenshot eval gate.
- The source of truth is the live app state plus XML/cache; no direct live
  Rekordbox DB read is required for this goal.
- `vibemix library live-context --require-proof` is the physical proof gate:
  cold socket plumbing can still render `ok=true`, but proof readiness requires
  `live_context_schema_version=2`, advertised structured live-context
  capabilities,
  a citable deck `track_id`, connected mixer posture, recent controller moves,
  trusted source provenance for that citable track, observed master audio,
  a rendered per-deck lane map, a rendered `deck_reference_context[...]`
  deck1/deck2 map, a rendered `deck_source_context[...]` source/provenance map,
  structured `deck_source_status` diagnostics,
  a citable `deck_reference=...` live-evidence atom with concrete route tiers,
  structured `audio_window_map` timing, `audio_delta`, `live_evidence`, and a
  transition block/watch/candidate gate.
  In proof mode the sampler keeps
  watching until readiness passes or the timeout expires; in preview mode it
  still exits after the first flat deck frame plus snapshot/move evidence.
  A local live run on 2026-05-29 found an already-running `python -m vibemix`
  socket that was alive but stale for this proof path: it emitted deck/mixer
  context and live evidence, but not schema v2, `deck_source_status`, or
  `audio_window_map`. The new blocker wording calls this out directly.

## Live Proof Status

Automated tests cover the prompt/render/guard/bridge paths.

Structured evidence propagation proof on 2026-05-29:

- Live proof verdict CLI:
  `uv run pytest -q tests/library/test_live_context_cli.py` passed. The CLI now
  emits `readiness.{ready,checks,blockers}` and `--require-proof` exits non-zero
  with blockers until real deck/controller/audio evidence is present. The proof
  sampler preserves peak `music` plus non-empty transient `audio_delta` and
  `live_evidence` observed during the sampling window.
- Gemini-side symmetry proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/memory/test_ingest.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost_linter.py`
  passed, and Ruff passed on the touched Python files.
- Gemini attached-audio adjacency proof:
  `uv run pytest -q tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_linter.py tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/memory/test_ingest.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 244 tests. The new regression locks that the final Gemini text
  part places `AUDIO CONTEXT MAP FOR ATTACHED P1` before the P1 audio clause
  and includes `source=global_mix`, `live_evidence`, `move_effect_context`, and
  a blocking `claim_policy` for single-deck evidence.
- Historical move-memory proof:
  `uv run pytest -q tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_linter.py tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/memory/test_no_live_path_import.py tests/memory/test_no_extraction.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 261 tests. This covers the MIX_MOVE recall cost gate, compact
  diet prompt recall, no-live-path/no-extraction memory boundaries, and the
  Gemini agent passing recall survivors into diet MIX_MOVE prompts.
- Viber historical move-context proof:
  `uv run pytest -q tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_linter.py tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/memory/test_no_live_path_import.py tests/memory/test_no_extraction.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 263 tests. The new Viber regression writes a synthetic
  `memory.db` moments table and proves `chat_with_codex` includes
  `HISTORICAL MOVE CONTEXT` only when live_context has both recent moves and
  `audio_delta`, with the "not live proof" fence present.
- Second-deck identity capability proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 94 tests. This locks `second_deck_identity=unknown_or_suppressed`
  into the shared `deck_context[...]`, `live_evidence[...]`, WS payload refs,
  Viber prompt preview, and the guard correction summary for single-resolved
  deck states.
- Per-deck lane context proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/state/test_coach_prompt_grounding.py tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/agent/test_dj_cohost.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 258 tests. This covers full/detail `deck_lanes_context[...]`,
  compact Gemini P1-adjacent lane context, Viber prompt preview, runtime event
  logging, memory signature/retrieval query wiring, and the MIX_MOVE diet cap.
- Citable deck-lane evidence proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py`
  passed with 36 tests. This locks
  `deck_lanes=A_known_route_dominant+B_unknown_route_muted` into
  `live_evidence.mix` and `live_evidence.refs` for the shared prompt/socket
  packet.
- Compact MIX_MOVE prompt-diet proof:
  `uv run pytest -q tests/state/test_coach_prompt_diet.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py`
  passed with 54 tests. The regression asserts one `live_evidence[...]` packet
  in dieted MIX_MOVE prompts and preserves `PROMPT_TOKEN_CAP_ACK == 800`.
- Focused non-GSD/non-beginner sweep proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/state/test_coach_prompt_grounding.py tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_linter.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 276 tests after the citable lane-evidence, compact-prompt dedupe,
  Viber sampler merge, Library UI merge, and backend sanitizer changes.
- Viber sampler/normalizer deck-lane proof:
  `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py tests/state/test_coach_prompt_diet.py`
  passed with 117 tests, and
  `npm --prefix tauri/ui test -- src/library/api.test.ts` passed with 27 tests.
  This locks cross-frame `live_evidence` merging, `deck_lane_evidence_seen` proof
  gating, safety-evidence priority under the 9-atom cap, and browser-side
  preservation of `deck_lanes=...`/`mix:deck_lanes=...`.
- Library UI live-context merge proof:
  `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 40 tests, and `npm --prefix tauri/ui run build` passed. This
  proves the real chat run path merges live deck frames before Viber receives
  them and that TypeScript accepts the merged payload contract.
- Viber backend sanitizer proof:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py`
  passed with 100 tests. The regression sends over-cap noise plus partial refs
  and proves the final prompt still contains `deck_lanes=...`,
  `mix:deck_lanes=...`, and `transition_block=...`.
- Viber lane/reference-map proof gate:
  `uv run pytest -q tests/library/test_live_context_cli.py` passed with 20
  tests. `--require-proof` readiness now includes `deck_lane_context_seen` and
  `deck_reference_context_seen`; it blocks with "rendered live context had no
  per-deck lane map" or "rendered live context had no deck1/deck2 reference
  map" when the sampled context cannot render the policy lane map and the plain
  deck-one/deck-two map.
- Lane/source-aware correction proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost_linter.py`
  passed with 90 tests before the source ladder was added. The current focused
  guard slice,
  `uv run pytest -q tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost_linter.py tests/library/test_live_context_cli.py`,
  passed with 130 tests. Shared Gemini/live corrections and Viber corrections
  now include compact lane evidence plus the source-ladder rule when correcting
  unsupported transition, blend, handoff, or bridge claims. The wired Gemini
  streaming/linter regression now asserts the emitted correction and the
  `live_claim_guard` trace both carry
  `second_deck=independent_source_required` and
  `rule=unresolved_deck_is_not_transition_evidence`.
- Viber live move-grade artifact proof:
  `uv run pytest -q tests/library/test_codex_curate.py::test_chat_with_codex_surfaces_grounded_move_grade_receipts tests/library/test_codex_curate.py::test_chat_with_codex_live_evidence_candidate_blocks_quality_grade tests/library/test_codex_curate.py::test_chat_with_codex_drops_move_grade_when_live_policy_blocks_current_claim tests/library/test_codex_curate.py::test_chat_with_codex_corrects_unsupported_multi_deck_outcome_claim`
  passed with 4 tests, and
  `uv run pytest -q tests/library/test_codex_curate.py tests/state/test_deck_context.py tests/library/test_live_context_cli.py`
  passed with 118 tests. This proves Viber can still surface grounded
  non-live move-grade receipts, but a one-deck or candidate-only live context
  strips `move_grades` and does not let the grade track id leak into
  `seen_track_ids`.
- Time-aligned audio-window proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost.py::test_llm_node_03b_places_deck_audio_map_next_to_audio_part tests/agent/test_dj_cohost_3part.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 113 tests. This locks `audio_window_context[...]` into the
  Gemini P1-adjacent prompt, the lookahead-only and mic+lookahead Part labels,
  and the Viber/Codex live-context preview without adding duplicate deck audio
  Parts.
- Historical audio-window memory proof:
  `uv run pytest -q tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/runtime/test_coach.py tests/state/test_coach.py tests/agent/test_dj_cohost.py::test_recall_query_context_includes_time_aligned_audio_window tests/library/test_codex_curate.py::test_chat_with_codex_adds_historical_move_context_from_memory tests/library/test_codex_curate.py::test_chat_prompt_prefers_historical_move_with_same_deck_lane_context`
  passed with 98 tests. This proves live move event logs carry
  `audio_window_context`, deterministic memory signatures store
  `audio_window=...`, recall queries mirror it, and Viber's historical move
  matcher can prefer memories with the same deck-lane/time-window posture while
  keeping them fenced as comparison memory, not live proof.
- Historical deck-source memory proof:
  `uv run pytest -q tests/library/test_codex_curate.py tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/state/test_deck_context.py`
  passed with 114 tests. The new Viber regression proves the raw historical
  move scan prefers a memory with matching `sources=folder_cache` /
  `second_deck=independent_source_required` over a newer otherwise similar
  memory from a different source ladder.
- Historical memory sanitizer proof:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py tests/memory/test_ingest.py tests/memory/test_retrieval.py`
  passed with 128 tests. The new regression writes a synthetic memory row that
  claims attached deck stems and says "great transition"; Viber still retrieves
  the row for move/audio-delta comparison but renders
  `audio_window=omitted_untrusted_audio_window` and
  `said: omitted_past_live_outcome_claim`, with the "not live proof" fence
  intact.
- Shared Gemini/Viber historical-memory sanitizer proof:
  `uv run pytest -q tests/agent/test_dj_cohost.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/memory/test_ingest.py tests/memory/test_retrieval.py`
  passed with 256 tests, and Ruff check/format check passed on the touched
  Python files. This proves full Gemini recall prompts, compact diet MIX_MOVE
  recall prompts, and Viber historical move context all omit old attached-stem
  audio-window claims and stale spoken transition verdicts while keeping useful
  move/audio-delta comparison memory. It also locks that recall queries keep the
  full time-aligned `audio_window` move anchor and that the compact MIX_MOVE
  prompt stays under the existing 800-token proxy cap.
- Deck-one/deck-two reference proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/agent/test_dj_cohost.py tests/runtime/test_coach.py tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/library/test_codex_curate.py`
  passed with 250 tests, and Ruff check/format check passed. This locks
  `deck_reference_context[...]` into Viber live prompts, full Gemini prompts,
  Gemini's P1-adjacent audio context map, runtime event rows, deterministic
  memory signatures, and recall queries. The standalone compact diet evidence
  line intentionally stays lean; the richer deck-one/deck-two map is attached
  beside the P1 audio map in the real Gemini call and in Viber's live context.
- Evidence-level deck-reference proof:
  `uv run pytest -q tests/agent/test_dj_cohost.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/memory/test_ingest.py tests/memory/test_retrieval.py`
  passed with 263 tests, and Ruff check/format check passed. This locks
  `deck_reference=deck1_A_...+deck2_B_...` into shared live evidence, WS
  frames, Viber evidence priority/normalization, and the physical proof gate.
  The ordering keeps the deck-audio capture/features/delta receipts inside the
  9-item evidence cap by
  treating raw `deck_route=...` as lower priority than the plain deck1/deck2
  reference and move-effect signals.
- Evidence-level deck-source proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 126 tests, and
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 45 tests. `npm --prefix tauri/ui run build` passed. This locks
  `deck_source=deck1_A_...+deck2_B_...` into shared live evidence, WS payloads,
  Viber sampler merge priority, browser normalizer/merge priority, and the
  physical proof gate's `deck_source_evidence_seen` check. `move_effect=...`
  remains inside the bounded refs by ordering it ahead of `move_scope=...`.
  Additional refresh-loop proof:
  `uv run pytest -q tests/state/test_refresh.py::test_tick_registers_citable_deck_source_evidence_from_deck_snapshot tests/state/test_deck_context.py::test_grounding_refs_render_only_registered_deck_move_atoms`
  passed with 2 tests, and
  `uv run pytest -q tests/state/test_refresh.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 180 tests. The new regression drives a real `_tick_once` with a
  `deck_source.snapshot()` and asserts the resulting `EvidenceRegistry` contains
  `mix:deck_source=deck1_A_known_src_rekordbox_xml+deck2_B_unknown_src_none`, so
  the source atom is registered by the live writer, not just rendered by helper
  functions.
- Live socket audio-window transport proof:
  `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/runtime/test_coach.py tests/state/test_coach.py tests/agent/test_dj_cohost.py::test_recall_query_context_includes_time_aligned_audio_window`
  passed with 178 tests, and
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 44 tests. These lock the flat WS `audio_window_context`, CLI
  proof/readiness merge, Viber prompt rendering, and Tauri chat forwarding
  without letting the field persist after a fresh deck frame omits it.
- Audio-window truncation safety proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/state/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/agent/test_dj_cohost.py::test_llm_node_03b_places_deck_audio_map_next_to_audio_part tests/agent/test_dj_cohost_3part.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 185 tests. This locks the source/limit fields near the front of
  `audio_window_context[...]` so even capped Viber payloads still say P1 is the
  shared master mix, deck A/B audio are not attached, duplicated audio is not a
  deck split, and deck-one/deck-two references map to lane aliases
  `deck1:A,deck2:B`.
- Audio-window timeline hardening proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/memory/test_ingest.py tests/memory/test_retrieval.py`
  passed with 181 tests, and
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 45 tests. This tightens the shared Python and browser validators
  so a trusted packet must carry `P1_heard=true`,
  `timeline=past_action_future`, `action=-1.0..0.0`, and
  `rule=time_alignment_not_outcome_verdict`. Lookahead is no longer represented
  with an ambiguous second bare `heard=false`; it is labeled
  `future_heard=false`, so Gemini/Viber cannot smear the future Part onto the
  current P1 evidence.
- Audio-window trust-boundary proof:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py`
  passed with 110 tests, and
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 44 tests. `npm --prefix tauri/ui run build` passed, and
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds::tests`
  passed with 30 tests when run after the UI build. The new regressions prove
  malformed or context-poor `audio_window_context[...]` strings that claim
  attached deck stems, omit the duplicate-master warning, or omit lane aliases
  are rejected before Viber treats them as proof; Python then recomputes the
  safe master-mix/structured-text-only packet from state when enough state is
  present.
- Tauri command bridge proof:
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml library_cmds::tests`
  passed with 30 tests after adding
  `chat_library_args_preserve_time_aligned_audio_context`. This pins that
  browser `liveContext` is serialized as one raw JSON `--live-context` payload
  and that `audio_window_context[...]` plus `recent_moves` survive the Rust
  bridge into the Python CLI.
- `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed.
- Source-provenance proof:
  `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 66 tests, and
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 38 tests. These lock `source=rekordbox_xml` from runtime frame to
  UI normalizer to Viber prompt, require trusted source provenance in
  `--require-proof`, and sanitize invalid source/path strings.
- Local source diagnostic proof:
  `uv run pytest -q tests/library/test_live_context_cli.py tests/state/test_deck_poller.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_codex_curate.py`
  passed with 83 tests. `uv run python -m vibemix library live-context --json
  --timeout 0.2 --frames 1` returned `source_status.library_cache.track_count =
  1547`, `source_type = folder_cache`, Rekordbox app/master DB present, and
  `rekordboxEvent.xml` payload counts at 0.
- Local Rekordbox source probe, re-checked 2026-05-29:
  `~/Library/Pioneer/rekordbox/master.db` is present but `file` reports opaque
  `data` at 6,021,120 bytes; `masterPlaylists6.xml` is XML; the event XML files
  under `~/Library/Application Support/Pioneer/rekordbox*/` are tiny diagnostic
  XML files (676 bytes and 91 bytes), and no useful live deck transport payload
  was found. This keeps the live DB/event XML out of the default deck-state
  resolver. The safer path remains now-playing/controller attribution into the
  cache-warm library/folder index.
- Now-playing resolver proof:
  `uv run pytest -q tests/state/test_deck_poller.py` passed with 18 tests after
  adding artist-title, ambiguity-abstention, folder-stem, and folder-source
  coverage. `TrackInfo` can publish `Artist - Title` while Rekordbox/cache rows
  store artist/title separately; the poller now builds an ambiguity-aware
  now-playing label index from bare title, `Artist - Title`, `Artist – Title`,
  and file stem labels. Duplicate labels resolve to `None`, so the deck poller
  abstains instead of inventing a track identity.
- Broader deck/source resolver proof:
  `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_refresh_deck.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py`
  passed with 97 tests, and Ruff passed on
  `src/vibemix/state/deck_poller.py tests/state/test_deck_poller.py`.
- Broader targeted slice passed:
  `uv run pytest -q tests/state/test_deck_context.py tests/state/test_refresh_deck.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost_linter.py`.
- Browser-path deck-reference proof:
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 44 tests, and `npm --prefix tauri/ui run build` passed. The UI
  normalizer and live-frame merge helper now keep `deck_reference=...` at the
  same high priority as the Python/Viber/CLI path, so the 9-token cap preserves
  the deck1/deck2 reference atom alongside `deck_lanes=...` and transition
  blockers.
- Explicit live-frame context-map proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 124 tests. `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 45 tests, and `npm --prefix tauri/ui run build` passed. The flat
  30 Hz live frame now carries bounded `deck_lanes_context[...]`,
  `deck_reference_context[...]`, `deck_source_context[...]`, and
  `deck_audio_context[...]` strings directly beside
  `deck_state`/`deck_mixer`/`live_evidence`; the browser validates them,
  forwards them into Viber chat payloads, and clears stale context maps when a
  fresh deck frame omits them or an empty deck frame arrives.
- Source-ladder honesty proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/agent/test_dj_cohost.py tests/library/test_codex_curate.py tests/runtime/test_coach.py tests/memory/test_ingest.py tests/memory/test_retrieval.py`
  passed with 252 tests. `deck_source_context[...]` now states that live deck
  identity comes from `MusicState.deck_state`, the robust primary path is
  now-playing/controller attribution into the library cache, live
  `master.db` is not read, `rekordboxEvent.xml` is diagnostic only, and deck2
  needs an independent source before it becomes transition evidence. The same
  source-ladder text reaches Gemini's P1-adjacent audio map, Viber's live
  preview, runtime event rows, and v7 historical memory/recall signatures.
- Live-frame deck-source transport proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 125 tests. `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 45 tests, and `npm --prefix tauri/ui run build` passed. This
  locks the `deck_source_context[...]` packet from shared validator to flat WS
  frame, CLI sampler merge, Python Viber normalizer/preview, TypeScript
  normalizer, and browser chat merge/clear behavior without changing the Viber
  MCP tool-flow spine.
- Deck-source proof-gate hardening:
  `uv run pytest -q tests/library/test_live_context_cli.py` passed with 20
  tests after adding `readiness.checks.deck_source_context_seen`. The physical
  `--require-proof` gate now blocks with "rendered live context had no deck
  source/provenance map" when the preview cannot show the source ladder, so a
  proof packet cannot pass on deck title/track IDs alone.
- Desktop deck-source bridge proof:
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args_preserve_time_aligned_audio_context`
  and
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml has_live_deck_context_routes_flat_deck_snapshot_to_library`
  passed. The first test now parses the exact `--live-context` JSON argument
  sent from the desktop chat bridge and proves `deck_source_context[...]`
  survives with `second_deck=independent_source_required` and
  `rule=unresolved_deck_is_not_transition_evidence`. The second pins that a
  flat live deck frame carrying the source ladder is still routed to the
  Library/Viber window.
- `npm --prefix tauri/ui run build` and
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml has_live_deck_context_routes_flat_deck_snapshot_to_library`
  passed. The Rust test must not run concurrently with the UI build because the
  Tauri macro embeds the hashed `dist` tree while Vite is replacing files.

Controlled boot proof on 2026-05-29:

- `VIBEMIX_TRACE=0 uv run python -m vibemix` started the live session.
- The app opened the mascot bus on `ws://127.0.0.1:8765`.
- `uv run python -m vibemix library live-context --json --timeout 2.0 --frames 12`
  returned `ok=true`, `flat_deck_frame_seen=true`, and
  `session_snapshot_seen=true`.
- The sampled context was honestly cold/silent: `deck=none`, `audible=false`,
  empty `deck_state`, disconnected `deck_mixer`, and empty `audio_delta`.
- The rendered preview correctly emitted `transition_block=no_resolved_decks`
  and `multi_deck_outcome=blocked`.

Remaining proof gap is now live musical activity, not socket plumbing:

1. Start the live session.
2. Run
   `uv run python -m vibemix library live-context --json --require-proof`.
3. Route DJ audio into BlackHole / the configured input.
4. Connect or move the controller so `deck_mixer.connected=true` and
   `recent_moves` appear.
5. Load real decks / Rekordbox-derived deck rows so `deck_state` resolves.
6. Make a single-deck move and ask Viber/Gemini about it.
7. Verify they name deck/control evidence without calling it a transition.

Current local blocker on 2026-05-29:

- `uv run python -m vibemix library live-context --timeout 0.2 --frames 4 --json`
  now reaches a real Vibemix process at
  `/Users/ozai/projects/dj-set-ai/.venv/bin/python3 -m vibemix`
  (`looks_like_vibemix=true`), saw 3 frames, and returns `ok=true` for socket
  plumbing. The sampled process currently has controller posture
  (`deck_mixer.connected=true`, both A/B controls present) and the local preview
  now renders `deck_lanes_context[...]`, `deck_reference_context[...]`,
  `deck_source_context[...]`, `deck_audio_context[...]`, and
  `audio_window_context[...]`.
- Stale-evidence repair proof:
  `uv run pytest -q tests/state/test_deck_context.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/runtime/test_ws_bus_deck_state.py`
  passed with 129 tests. The shared evidence builder now emits
  `transition_block=no_resolved_decks`, `second_deck_identity=blocked`,
  `deck_reference=deck1_A_unknown_route_...+deck2_B_unknown_route_...`, and
  `deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none` when
  controller posture exists but no deck row resolves. Viber normalization merges
  those derived atoms with raw socket evidence, so an older/stale running socket
  cannot make the proof packet lose deck1/deck2 reference/source atoms.
- Live CLI re-check after that repair:
  `uv run python -m vibemix library live-context --json --timeout 0.2 --frames 1`
  returned `ok=true`, `flat_deck_frame_seen=true`, `controller_connected=true`,
  `deck_reference_evidence_seen=true`, `deck_reference_route_evidence_seen=true`,
  `deck_source_evidence_seen=true`, and `transition_gate_seen=true`. Readiness
  remains honestly false because the musical proof is incomplete:
  `audible=false`, `music=0.0`, empty `deck_state`, no recent moves, and no
  `audio_delta`. `source_status` confirms local `library.pkl` loaded from
  folder cache with 1547 tracks, Rekordbox app and `master.db` exist, and both
  `rekordboxEvent.xml` files have zero live deck payload counts. The remaining
  proof requires real DJ audio, controller moves, and resolved deck rows.
- Browser/Tauri bridge parity proof:
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 47 tests, and `npm --prefix tauri/ui run build` passed. The
  browser normalizer now mirrors the Python repair: raw `live_evidence` refs
  are merged with derived refs, controller/deck frames derive citable
  `transition_block`, `second_deck_identity`, `deck_reference`, and
  `deck_source` atoms, partial mixer frames do not invent missing deck identity
  when `deck_state` was omitted, and explicit empty `deck_state` frames clear
  stale identity/evidence before a Viber chat turn. This keeps the Tauri/UI
  payload from lagging behind the Python Viber prompt contract.
- Python sampler stale-evidence reset proof:
  `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py`
  passed with 130 tests after aligning the CLI sampler with the browser bridge:
  every explicit deck-state frame resets old `live_evidence` before merging
  current evidence, so an empty or newly-resolved deck snapshot cannot carry a
  previous `deck_reference`, `deck_source`, or transition gate. Peak `music`
  and bounded `audio_delta` are still preserved as transient observations, but
  identity/evidence atoms must be current or re-derived from the normalized
  frame. A live CLI re-check with
  `uv run python -m vibemix library live-context --json --timeout 0.2 --frames 1`
  still returned `ok=true` with current derived `deck_reference`, `deck_source`,
  and `transition_block=no_resolved_decks` evidence, while keeping readiness
  false for the honest missing physical proof: no resolved deck row, no recent
  move, no audible master audio, and no `audio_delta`.
- Runtime producer non-clash proof:
  this work stayed in the live deck/audio evidence lane, not the Viber MCP/tool
  orchestration lane. The real 30 Hz websocket producer already emits
  `live_evidence`; `tests/runtime/test_ws_bus_deck_state.py` now pins the cold
  controller case directly at the producer: empty `deck_state` plus connected
  A/B routing publishes `transition_block=no_resolved_decks`,
  `second_deck_identity=blocked`, deck1/deck2 reference route atoms, and
  `deck_source=...src_none` atoms. Verified with
  `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py tests/library/test_live_context_cli.py`
  (72 passed) and
  `uv run ruff check src/vibemix/runtime/ws_bus.py tests/runtime/test_ws_bus_deck_state.py`.
- Gemini cold-P1 audio contract proof:
  the attached-audio prompt path now forces an `audio_window_context[...]` next
  to P1 even when the deck state is completely cold. That means Gemini always
  sees `P1=master_global_mix`, `deckA_audio=not_attached`,
  `deckB_audio=not_attached`, `lane_aliases=deck1:A,deck2:B`, and a
  `claim_policy[policy=requires_more_evidence ...]` immediately before the
  `Attached: P1 = ... global mix, not isolated deck stems` clause. This closes
  the empty-context suffix gap without adding another audio Part or changing
  the cheap 6s/18s audio windows.
- LLM-aware context-feed contract:
  the shared deck-context helper now renders a compact
  `context_feed_contract[...]` packet. It is not musical evidence; it labels
  the feed itself for the LLM: `deck1:A,deck2:B`, source/provenance classes
  (`MusicState.deck_state`, `deck_mixer`, `EvidenceRegistry`, perceive cache),
  volatile per-turn fields, history as past-session comparison rather than live
  proof, static persona/rules as the cacheable layer, the per-turn cost shape,
  recent-move/audio-window TTL, and `speed=no_extra_model_pass`. Gemini receives
  it beside P1 with `surface=gemini_p1` / `per_turn=small_text+single_P1_audio`;
  Viber receives it in the live-context block with `surface=viber_text` /
  `per_turn=small_text_live_context`. This reframes the work as intelligent
  context feeding and label management, with claim blocking only one downstream
  policy.
- Historical context-feed memory proof:
  session event rows, deterministic `coach_line` memory signatures, Viber's raw
  historical move query tokens, and Gemini recall-query context now also carry
  `context_feed_contract[...]`. The field has a larger bounded cap than generic
  context fields so `history=past_comparison_not_live_proof`,
  `cache=static_persona_rules_only`, and `speed=no_extra_model_pass` survive
  memory/retrieval. Viber appends these generic feed tokens after deck
  lane/reference/source/audio evidence when scoring historical rows, so
  lane-specific matches still outrank generic context-feed overlap.
- Viber cold-frame prompt safety proof:
  the Python Viber prompt path now recomputes the same safe
  `audio_window_context[...]` for explicit empty/cold live contexts after
  rejecting untrusted raw packets. The prompt therefore still gives Codex/Viber
  the deck1/deck2 lane aliases, `P1=master_global_mix`, `deckA_audio` /
  `deckB_audio=not_attached`, and `claim_policy=requires_more_evidence` even
  when no deck row resolves. This is prompt fencing only, not physical proof.
- Proof-readiness distinction:
  `library live-context --require-proof` no longer treats a prompt-forced
  safety map as observed time-aligned audio evidence by itself. Readiness
  counts `audio_window_context_seen` only when a trusted raw audio-window packet
  arrives or when the prompt-rendered map is backed by live signals such as a
  recent move, controller connection, deck state, audible flag, or master music
  floor. A context-poor raw packet plus empty deck state still blocks with
  `no time-aligned audio_window_context was observed`.
- Move-scope citation priority proof:
  `live_evidence.refs` now keeps nine refs so one MIDI move plus the eight
  bounded mix keys can carry both `mix:move_scope=single_deck_move_A` and
  `mix:move_effect=...`; `grounding_refs[...]` uses the same nine-ref cap when
  the EvidenceRegistry proves those atoms. Python and TypeScript still keep the
  live evidence `mix` cap at eight, with `refs` at nine, and prioritize MIDI,
  deck lanes/reference/source, transition gates, second-deck identity,
  `move_scope`, and move/audio deltas ahead of lower-value raw route atoms.
  The MIX_MOVE diet instruction was tightened to stay under
  `PROMPT_TOKEN_CAP_ACK == 800` while preserving the hard
  `do NOT call this a transition or blend` gate.
  Verification:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py tests/state/test_coach.py::test_evidence_line_renders_live_evidence_categories_for_gemini`
  passed with 122 tests, and Ruff passed on the touched Python live-context
  files.
  `uv run pytest -q tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 277 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 47 tests; and
  `uv run python -m vibemix library live-context --json --timeout 0.2 --frames 1`
  returned a real socket frame with current deck1/deck2 reference/source atoms,
  `transition_block=no_resolved_decks`, and honest readiness blockers for the
  still-missing physical proof: no resolved deck row, no recent move, no audible
  master audio, and no `audio_delta`.
- Live smoke re-check after the proof-readiness split:
  `uv run python -m vibemix library live-context --json --timeout 0.2 --frames 1`
  returned `ok=true` from the real local Vibemix socket. The prompt preview
  rendered the safe master-mix `audio_window_context[...]` plus deck1/deck2
  reference/source atoms; readiness remained false because deck rows, recent
  moves, audible master audio, and `audio_delta` were still absent.
- Live smoke re-check after `context_feed_contract[...]`:
  the same command returned `ok=true` and the Viber preview now includes
  `context_feed_contract[surface=viber_text ... cache=static_persona_rules_only
  ... history=past_comparison_not_live_proof ... speed=no_extra_model_pass]`
  ahead of the deck lane/reference/source packets. The readiness blockers are
  unchanged and honest: no resolved deck row, no recent move, no audible master
  audio, and no `audio_delta`. The Viber instruction now starts by telling the
  model to bind deck1/deck2 labels, source/provenance, freshness/TTL,
  cache/static-vs-volatile boundaries, and history-as-comparison before
  reasoning. Verification:
  `uv run pytest -q tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/state/test_deck_context.py tests/state/test_coach.py tests/state/test_coach_prompt_diet.py tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 279 tests, and Ruff passed on the touched Python files.
- Session/memory context-feed verification:
  `uv run pytest -q tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/runtime/test_coach.py tests/agent/test_dj_cohost.py tests/library/test_codex_curate.py`
  passed with 133 tests. This pins `context_feed_contract[...]` in session event
  logs, `coach_line` signatures, recall queries, and Viber historical move
  matching without adding another model call.
- Viber library/live intent split:
  the Library chat path now treats attached live context as
  `active_live_context` only when the user's turn asks about the current live
  deck/move/audio moment (`was that a transition?`, `what happened?`,
  `did that low cut fix it?`). Crate/search/vibe/playlist/set-building turns
  (`find me dark rolling hypnotic techno`) keep the live packet as
  `silent_guard`: useful as a hidden safety rail, but forbidden as visible
  `resolved decks` / `claim_policy` / live-read correction prose. The result
  boundary also replaces an unprompted live correction with the grounded
  library outcome when tool traces, validated track IDs, or playlist artifacts
  exist. Verification:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 84 tests, and Ruff passed on
  `src/vibemix/library/codex_curate.py` plus
  `tests/library/test_codex_curate.py`.
- Now Playing deck-source guard:
  a live smoke showed the controller reporting deck B posture while macOS Now
  Playing was owned by `com.apple.WebKit.GPU`, not DJ software. `TrackInfo`
  now carries the MediaRemote client bundle id, and `DeckPoller` rejects known
  browser/consumer-player bundle ids before resolving a title against the
  library cache. This keeps global Now Playing from accidentally becoming a
  citable deck identity just because the controller has an active deck. The
  proof command reports the source as
  `source_status.nowplaying.deck_source_candidate=false` so the missing
  deck-state leg is explainable. The poller also publishes bounded
  `DeckState.source_status` fields into `deck_source_context[...]` after
  refresh, so the LLM sees the provenance reason (`nowplaying=...`,
  `nowplaying_owner=...`, `resolution=...`) rather than a blank `source=none`.
  These fields are diagnostic context, not deck identity proof. Verification:
  `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_refresh_deck.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py`
  passed with 107 tests;
  `uv run pytest -q tests/test_track_macos.py tests/state/test_deck_poller.py tests/library/test_live_context_cli.py`
  passed with 58 tests; Ruff passed on the touched files; and live smoke
  showed `client_bundle_id=com.apple.WebKit.GPU` with
  `deck_source_candidate=false`.
- Structured source-status transport:
  `deck_source_status` now rides the flat live socket as bounded JSON
  diagnostics instead of only being embedded in `deck_source_context[...]`.
  The UI normalizer preserves it and drops unknown/noisy keys, chat forwarding
  keeps it fresh, and Viber reconstructs `DeckState.source_status` from the map
  before rendering the shared source context. This makes source/provenance
  reasoning less dependent on string parsing and more LLM-aware: the model can
  see `nowplaying=blocked_non_deck_owner`,
  `nowplaying_owner=com.apple.webkit.gpu`, and
  `resolution=blocked_non_deck_nowplaying` as diagnostic context without
  treating them as identity proof.
  Follow-up source-resolution expansion adds `library`, `library_tracks`,
  `library_source`, `library_match`, `second_deck_source`, and `screen_vision`
  to the same bounded lane. The live proof CLI now surfaces private, content-light
  blockers for missing/empty library cache, ambiguous title match, blocked
  browser/media-player Now Playing, controller disconnection, disabled
  screen-vision, and the independent-source requirement for Deck B. These
  explain why the system cannot know Deck 1/Deck 2 yet without upgrading the
  diagnostic into proof.
  Verification:
  `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_codex_curate.py tests/state/test_deck_context.py tests/library/test_live_context_cli.py`
  passed with 138 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 48 tests; and Ruff passed on the touched Python files.
  Latest expanded-source verification:
  `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py`
  passed with 153 tests; `npm --prefix tauri/ui test -- src/library/api.test.ts`
  passed with 44 tests; and
  `uv run ruff check src/vibemix/state/deck_poller.py src/vibemix/state/deck_context.py src/vibemix/runtime/ws_bus.py src/vibemix/library/codex_curate.py src/vibemix/__main__.py tests/state/test_deck_poller.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py`
  passed.
- Structured audio-window transport:
  `audio_window_map` now rides beside the existing `audio_window_context[...]`.
  The text packet stays the compact LLM grammar, while the map carries
  structured `pre_s`, `current_s`, `action_s`, `future`, and bounded
  `move_anchors` for the single P1 master-global-mix audio window. It repeats
  the safety constraints (`deckA_audio=not_attached`,
  `deckB_audio=not_attached`, `duplicate_audio=same_master_not_deck_split`,
  `rule=time_alignment_not_outcome_verdict`) so the "older part / action /
  three seconds forward" arrangement is explicit without adding audio uploads,
  model passes, or fake deck stems. Gemini sees `audio_window_map[...]` adjacent
  to the attached P1 audio Part; WS/UI/Viber preserve the JSON map. Verification:
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 204 tests after `audio_part_context` also became a socket/Viber
  capability;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 53 tests; `npm --prefix tauri/ui run build` passed; and Ruff
  passed on the touched files.
- Structured audio-part transport:
  `audio_part_context` is now a required live-context capability, not just a
  Gemini-only prompt suffix. The socket emits it with `surface=live_context` and
  `P1_model_heard=false`, so Viber gets the same P1/P2/P3 role contract without
  pretending it received audio bytes. Gemini direct turns still render
  `surface=gemini_parts` with `P1_model_heard=true`. Both variants repeat
  `P1_deck_audio=global_mix_not_stems`, `per_deck_audio=not_attached`, and
  `rule=part_labels_not_outcome_verdict`. Rust desktop bridge verification:
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args -- --nocapture`
  passed with 3 tests and now pins that this field survives the `--live-context`
  JSON handoff.
- Structured proof readiness:
  `library live-context --require-proof` now preserves and validates
  `live_context_schema_version=2`, `live_context_capabilities`,
  `audio_part_context`, `deck_audio_separation_context`,
  `deck_source_status`, `audio_window_map`, configured deck-pair capture,
  deck-audio capture/features/delta context and evidence, and at least one
  active deck audio lane before declaring the sampled live packet ready.
  Missing schema/capabilities, structured lanes, or capture activity produce
  explicit blockers instead of
  letting a string-rendered prompt fence look like full proof. The Library UI
  now preserves the same schema/capability receipt
  through `normalizeLiveContextPayload` and into `libraryChat`, so a Viber chat
  turn can see whether the live context came from a schema-v2 socket. The
  prompt renderer also emits `live_context_transport[schema=2 capabilities=...
  rule=transport_receipt_not_musical_evidence]`, so this receipt is visible to
  Viber as metadata, not as music/deck outcome evidence. When schema/capability
  proof is missing, the latest local sampler writes
  `.planning/research/live-context-latest-proof.json` with
  `readiness.diagnosis=live_socket_missing`, `frames_seen=0`, and missing
  capabilities including `audio_part_context`. When transport data is absent or
  incomplete, the same prompt line renders
  `status=stale_or_pre_schema_v2` plus missing capabilities, and active live
  questions instruct Viber not to give transition or move-outcome verdicts until
  the live session is restarted/resampled.
  The readiness payload now separates stale runtime from missing physical proof:
  `diagnosis=stale_live_runtime`, `stale_live_runtime=true`, and `next_action`
  point to restarting the live session when the socket is alive but too old.
  Verification:
  `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  passed with 189 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 48 tests;
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args_preserve_time_aligned_audio_context`
  passed;
  `npm --prefix tauri/ui run build` passed; and
  `uv run ruff check src/vibemix/runtime/ws_bus.py src/vibemix/__main__.py src/vibemix/library/codex_curate.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py`
  passed.
  A local stale-socket smoke on 2026-05-29 returned `ok=true` with
  `readiness.diagnosis=stale_live_runtime` and an explicit restart
  `next_action`; the preview also rendered
  `live_context_transport[schema=missing ... status=stale_or_pre_schema_v2]`.
- Viber stale-transport result boundary:
  stale schema/capability receipts are now enforced after the model speaks, not
  only in the prompt. For active live questions, if the live context is missing
  schema-v2 transport/capabilities and Codex writes a multi-deck or move-outcome
  verdict, the Python result guard replaces it with a fresh-resample correction
  and refuses to call the packet a transition, blend, or move outcome. The chat
  history sanitizer also treats `requires_more_evidence` as a blocking policy
  for prior Viber live outcome claims, so an older "great transition" response
  is omitted from the next prompt under stale transport while honest
  self-corrections remain. Verification:
  `uv run pytest -q tests/library/test_codex_curate.py` passed with 65 tests;
  `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  passed with 190 tests; UI API/chat tests passed with 48 tests; Ruff passed on
  `src/vibemix/library/codex_curate.py` and
  `tests/library/test_codex_curate.py`.
- Fresh runtime cold-frame audio-window proof:
  after restarting the live runtime on the current worktree, the socket now
  advertises `live_context_schema_version=2` and all required capabilities, so
  stale transport is no longer the active blocker. The smoke exposed a better
  bug: `audio_window_map` was advertised but omitted on cold/silent frames with
  no recent moves. The websocket producer now emits both
  `audio_window_context[...]` and structured `audio_window_map` whenever live
  state has a usable reference frame (controller, audio, deck rows, or
  lookahead). No-move frames carry `move_anchor=none` and `move_anchors=[]`,
  which keeps the old/current/action/future P1 contract present without
  inventing a user action. The text trust cap was raised so the safe
  `audio_window_context[...]` line remains intact through
  `future=not_attached]`. Fresh smoke now reports
  `stale_live_runtime=false`, `missing_capabilities=[]`,
  `audio_window_context_seen=true`, and `audio_window_map_seen=true`; remaining
  blockers are physical proof only: no resolved/citable deck row, no recent
  controller move, no observed master audio, and no bounded `audio_delta`.
  Verification:
  `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py`
  passed with 78 tests;
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 144 tests; Ruff passed on the touched runtime/deck-context files.
- Wait-ready physical proof capture:
  `vibemix library live-context` now has `--wait-ready <seconds>` and
  `--interval <seconds>`. The wait mode implies `--require-proof` and keeps
  resampling until the readiness packet passes or the deadline expires. This
  matches the physical DJ workflow better than a one-shot sampler: start the
  live runtime, start the wait-ready proof command with `--out`, then load/play
  a deck and move a control so the first complete schema-v2 deck/source/audio
  packet is captured. The result includes `proof_attempts`, `wait_ready_s`, and
  `wait_interval_s`. Verification:
  `uv run pytest -q tests/library/test_live_context_cli.py` passed with 24
  tests; `uv run pytest -q tests/library/test_live_context_cli.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py tests/library/test_codex_curate.py`
  passed with 145 tests; Ruff passed on `src/vibemix/__main__.py` and
  `tests/library/test_live_context_cli.py`.
- Proof artifact to Viber chat:
  `vibemix library chat` now accepts `--live-context-file`. The file can be
  either a raw live-context dictionary or the full `library live-context --out`
  artifact; the CLI extracts the nested `live_context` field and passes that to
  `chat_with_codex`. Bad files fail with `stop_reason=live_context_file_error`
  rather than silently dropping live proof. This closes the practical loop from
  physical proof capture to an auditable Viber answer check:
  `live-context --wait-ready ... --out proof.json`, then
  `library chat "was that good?" --live-context-file proof.json --json`.
  Verification:
  `uv run pytest -q tests/library/test_live_context_cli.py` passed with 27
  tests; `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py`
  passed with 148 tests; Ruff passed.
- Deterministic Viber reply verifier:
  `vibemix library verify-live-reply` checks a captured proof packet plus either
  a `library chat --json` result file or direct `--reply` text. It calls the
  same live-claim guard used at the Codex result boundary, so an invented
  "great transition" from a one-deck proof packet fails with
  `unsupported_live_outcome_claim` and exposes the corrected reply. It also
  fails if the proof artifact is not ready or if move grades are attached while
  the live policy does not allow grading. This gives the physical test a
  machine-checkable answer without another model pass:
  capture proof -> run Viber -> verify reply. Verification:
  `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 95 tests;
  `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_deck_context.py`
  passed with 151 tests; Ruff passed on `src/vibemix/__main__.py`,
  `src/vibemix/library/codex_curate.py`, and `tests/library/test_live_context_cli.py`.
- Viber live-read receipt in the shipped chat path:
  the verifier is now attached to real `library chat` results whenever live
  context is present. `CodexChatResult.to_dict()` carries a bounded
  `live_verification` packet with final reply pass/fail, claim policy,
  transport freshness, move-grade allowance, and internal guard/correction
  diagnostics. The Library UI normalizes that packet into a `live read` row in
  the chat side rack, with calm states such as `waiting`, `listening`,
  `live move checked`, `setup noted`, `grounded`, and `checked`.
  Raw internal labels such as
  `live_reply_verify`, `guard`, `live_context_required`, and
  `unsupported_live_outcome_claim` are not rendered in the user-facing chrome.
  This gives the DJ a visible proof receipt without exposing private model
  chain-of-thought or debug self-confession. Verification:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 96 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 53 tests;
  `npm --prefix tauri/ui run build` passed;
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args -- --nocapture`
  passed with 3 tests; and Ruff passed on the touched Python files.
- Active live question fail-closed when no packet exists:
  a local physical proof attempt on 2026-05-29 returned
  `readiness.diagnosis=live_socket_missing` with no frames from
  `127.0.0.1:8765`. Library cache and Rekordbox were present, and the current
  browser-owned Now Playing source was correctly rejected as deck identity. The
  resulting product requirement is clear: if no live packet is attached, an
  active live/deck/move question must not fall through to a normal model turn.
  `chat_with_codex` now returns before spawning Codex for that case. The spoken
  answer stays short (`Start live monitoring first, then I'll read that
  transition from the decks.`), while structured detail
  stays in the JSON/CLI receipt (`transport_status=missing_live_context`,
  `claim_policy=requires_more_evidence`, `move_grades_allowed=false`). The
  Library UI maps the stop/tool detail to `live read` and `live read waiting`
  rather than showing raw `live_context_required` text to the DJ.
  Verification:
  `uv run python -m vibemix library chat 'was that transition good?' --json`
  returned the deterministic fail-closed DTO;
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 97 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 50 tests;
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args -- --nocapture`
  passed with 3 tests; and Ruff passed on
  `src/vibemix/library/codex_curate.py` plus
  `tests/library/test_codex_curate.py`.
- Viber idle live-read visibility:
  the chat side rack now renders a calm live-read status row before the user
  asks. It shows `waiting`, `partial`, or `armed` based on the same schema-v2,
  deck lane/reference, source/provenance, audio-window, transition-gate,
  configured deck-pair capture, `deck_audio_capture=...`,
  `deck_audio_features=...`, and `deck_audio_delta=...` receipts sent to Viber.
  A global-mix/stereo-only packet can show `partial`, but cannot show `armed`;
  a packet with feature/delta context but missing those evidence receipts also
  stays `partial`. When context is present, the row includes the deck
  reference summary (`deck1 A=known:dominant / deck2 B=unknown:present`) so the
  operator can see whether Viber has deck1/deck2 footing without reading a long
  explanation. This is UI chrome, not spoken Viber copy, and it deliberately
  avoids raw guard/violation/stop labels. Verification:
  `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 59 tests, and `npm --prefix tauri/ui run build` passed. The build
  also required preserving and adjusting an existing shell `GroundingPanel.ts`
  iterator change with `Array.from(...)`.
- Viber tool-trace visibility / black-box wait fix:
  the final chat `tool_trace` now prefers the authoritative MCP tool-event tape
  over the model's self-reported JSON. `LibraryToolset` records bounded argument
  labels (`query`, `k`, curve, track count, playlist/export name, etc.) beside
  each actual tool call, `_ToolTapProxy` forwards those labels for direct MCP
  handler calls, and `chat_with_codex` reads the tape before tempdir cleanup.
  The UI live-tape test pins that a pending chat turn shows tool rows before
  the final reply lands. This exposes auditable tool/proof receipts, not hidden
  chain-of-thought. Verification:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_clap_runtime_errors.py`
  passed with 70 tests;
  `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 48 tests; and Ruff passed on the touched Python trace files.
- Socket-running proof and public-copy cleanup:
  a live `uv run python -m vibemix` session was first started with
  `VIBEMIX_INPUT_DEVICE='BlackHole 16ch'` and
  `VIBEMIX_DECK_AUDIO_CHANNELS='A=0,1;B=2,3'`. That controlled boot proved the
  runtime can open and label a configured deck-pair capture: the socket emitted
  `mode=deck_pair_capture_configured`, `deckA_audio=captured`,
  `deckB_audio=captured`, `deck_pairs=A:0,1+B:2,3`, and
  `deck_audio_capture=A_silent+B_silent`. It did not prove a live DJ transition
  because the capture was silent and had no resolved deck rows, recent controls,
  master audio, `audio_delta`, or per-deck feature/delta activity to evaluate.

  The current `.planning/research/live-context-latest-proof.json` was then
  refreshed from the already-running socket on `127.0.0.1:8765` with
  `uv run python -m vibemix library live-context --wait-ready 3 --interval 1 --json --out .planning/research/live-context-latest-proof.json`.
  That sample reached schema v2 with `missing_capabilities=[]`,
  `audio_part_context_seen=true`, and
  `deck_audio_separation_context_seen=true`, but the sampled separation packet
  says `requested_device=BlackHole_2ch`, `capture_device=BlackHole_16ch`,
  `input_channels=16`, `opened_channels=2`, and
  `mode=multichannel_device_available_but_runtime_opened_stereo`. The stricter
  readiness gate therefore keeps `diagnosis=missing_physical_proof` with the
  new blockers `deck_pair_capture_configured=false`, no deck audio
  capture/features/delta evidence, and no active deck audio lane, alongside the
  older physical
  blockers: no resolved/citable deck row, no recent control move, no audible
  master audio, and no bounded `audio_delta`.

  In the same pass, the visible live-claim correction text was changed from
  diagnostic correction prose to short product copy such as
  `I caught the live move. The useful note is the sound change right there.`
  Detailed lane/source/provenance reasons remain in structured guard summaries,
  logs, and `live_verification`, not in the spoken/chat reply. New visible copy
  should not apologize, confess internal stupidity, or expose guard/debug
  labels; the public state is calm (`waiting`, `listening`, `live move checked`,
  `setup noted`, `grounded`) while diagnostics stay in artifacts.
  Follow-up hardening extends that rule to pure diagnostic/proof labels even
  when there is no explicit "great transition" phrase: public replies containing
  `resolved decks=...`, `live evidence gate:...`, `transition_block=...`,
  `claim_policy=...`, `guard_violations`, or similar proof/debug tokens are
  normalized at the Viber result boundary. If the DJ asked for a library/crate
  task and the model accidentally talks about a live transition anyway, Viber now
  replaces that stray live claim with the grounded library result instead of
  showing the hallucinated live verdict. Latest follow-up also catches softer
  self-confession/self-diagnosis forms: "my bad on the live read", "I was
  wrong", "I messed up", "I shouldn't have called that", "that was dumb", and
  "I overclaimed" all normalize to calm public copy while details stay in
  `live_verification`.
  Verification:
  `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_linter.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/test_main_smoke.py`
  passed with 256 tests, `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 98 tests, `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 56 tests, Ruff passed on the edited Python files, and
  `git diff --check` passed.
  Latest focused verification for the public-diagnostic hardening:
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py`
  passed with 189 tests; `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed; and `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 66 tests.
  Latest self-diagnosis variant verification:
  `uv run pytest -q tests/library/test_codex_curate.py::test_chat_with_codex_normalizes_public_live_self_confession tests/library/test_codex_curate.py::test_chat_with_codex_normalizes_public_live_self_diagnosis_variants tests/library/test_codex_curate.py::test_chat_with_codex_normalizes_public_live_diagnostics_without_transition_claim tests/library/test_live_context_cli.py::test_cmd_library_verify_live_reply_rejects_public_debug_labels`
  passed with 7 tests; `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 118 tests; `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 72 tests; and `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py`
  passed.
- Per-deck feature-delta context:
  `DeckAudioCapture` now tracks latest per-deck feature descriptors and
  bounded deltas, the socket/Viber/Gemini/UI paths carry
  `deck_audio_features_context[...]` and `deck_audio_delta_context[...]`, and
  `live_evidence.mix` is bounded at nine atoms so
  `deck_audio_capture`, `deck_audio_features`, and `deck_audio_delta` survive
  together. Refs are bounded at thirteen atoms so four MIDI refs plus nine mix
  refs can coexist. Verification:
  `uv run ruff check src/vibemix/audio/deck_capture.py src/vibemix/state/deck_context.py src/vibemix/runtime/ws_bus.py src/vibemix/__main__.py src/vibemix/library/codex_curate.py src/vibemix/agent/dj_cohost.py tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py`
  passed;
  `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  passed with 222 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 59 tests;
  `npm --prefix tauri/ui run build` passed; and `git diff --check` passed.
- Historical deck-audio memory context:
  session event rows, deterministic memory signatures, raw memory retrieval,
  and Gemini recall query context now preserve deck-audio separation/features
  and per-deck deltas as text fields. The memory signature version is
  `v9-coach_line-deck-audio-context`, and the memory package still passes the
  no-live-path / no-generation gates. Verification:
  `uv run ruff check src/vibemix/runtime/coach.py src/vibemix/__main__.py src/vibemix/memory/ingest.py src/vibemix/memory/retrieval.py src/vibemix/agent/dj_cohost.py tests/runtime/test_coach.py tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/agent/test_dj_cohost.py`
  passed; and
  `uv run pytest -q tests/memory/test_ingest.py tests/memory/test_retrieval.py tests/memory/test_no_live_path_import.py tests/memory/test_no_extraction.py tests/runtime/test_coach.py tests/agent/test_dj_cohost.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 179 tests.
- Gemini Deck A/B Part window alignment:
  when optional Deck A/B audio Parts are attached, the audio Part label,
  `audio_window_context[...]`, and structured `audio_window_map` now agree on
  the same P2/P3 deck references and 3s span. The context also carries
  `audio_token_rate=32_per_second` plus bounded token estimates, matching the
  official Gemini audio-token docs. Verification:
  `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  passed with 228 tests; Ruff passed on the touched Python/test files; and
  `git diff --check` passed.
- Rekordbox deck-output routing hint:
  `deck_capture` now parses local `rekordbox3.settings` `DEVICESETUP`
  entries and can use the best external-mixer Deck A/B output pair when
  `VIBEMIX_DECK_AUDIO_CHANNELS=auto` is explicitly set. On this machine the
  current hint is `Deck A=0,1 / Deck B=2,3` from the Aggregate Device entry.
  The same hint can appear in `deck_audio_separation_context[...]` as
  `routing_hint=rekordbox_settings_A:0+1+B:2+3`, fenced by
  `routing_hint_rule=output_routing_not_live_audio_proof`. The proof command's
  `source_status` also reports the same `rekordbox_deck_routing_hint`, so a
  missing-live-socket artifact still tells the operator that Vibemix found a
  likely Deck A/B output route while keeping the live proof blockers intact.
  Verification is included in the 228-test slice above, plus a local
  `library live-context --json --timeout 0.2 --frames 1` sample showed the
  hint in `source_status` with `readiness.diagnosis=live_socket_missing`.
- Deck-audio-rich one-deck verifier guard:
  `verify-live-reply` now has a regression for a readiness-ready live packet
  containing configured deck-pair capture, active/silent deck capture evidence,
  per-deck features, per-deck deltas, and a positive move grade, but only one
  resolved deck identity. The deterministic verifier still reports
  `claim_policy=blocked`, rejects "great transition / incoming deck landed"
  language, and rejects move grades as unsupported. Verification:
  `uv run pytest -q tests/library/test_live_context_cli.py::test_cmd_library_verify_live_reply_rejects_deck_audio_rich_single_deck_transition tests/library/test_live_context_cli.py::test_cmd_library_verify_live_reply_rejects_unsupported_transition_claim`
  passed with 2 tests; and
  `uv run pytest -q tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py`
  passed with 170 tests.
- Current live proof artifact:
  `VIBEMIX_INPUT_DEVICE='BlackHole 16ch' VIBEMIX_DECK_AUDIO_CHANNELS=auto uv run python -m vibemix`
  was booted from this tree, then
  `uv run python -m vibemix library live-context --wait-ready 3 --interval 1 --json --out .planning/research/live-context-latest-proof.json`
  was run while the live runtime was started from this tree with
  `VIBEMIX_INPUT_DEVICE='BlackHole 16ch'` and
  `VIBEMIX_DECK_AUDIO_CHANNELS=auto`. Auto used the local Rekordbox settings
  hint (`A=0,1;B=2,3`) and opened a 4-channel stream. The artifact proves the
  fresh socket transport: `ok=true`, `frames_seen=62`,
  `flat_deck_frame_seen=true`, `session_snapshot_seen=true`, schema v2,
  `missing_capabilities=[]`, configured deck-pair capture,
  `deck_audio_separation_context[...]`, `deck_audio_features_context[...]`,
  `audio_part_context[...]`, raw `audio_window_context[...]`, raw
  `audio_window_map`, `audio_window_context_seen=true`,
  `audio_window_map_seen=true`, `deck_audio_capture=A_silent+B_silent`, and
  `deck_audio_features=A_silent_rms_0.000+B_silent_rms_0.000`. The same packet
  now carries `deck_source_status.controller=present` plus
  `controller_connection=disconnected`, raw `deck_lanes_context[...]`, raw
  `deck_reference_context[...]`, raw `deck_source_context[...]`,
  `deck_lane_context_seen=true`, `deck_reference_context_seen=true`,
  `deck_source_context_seen=true`, `transition_gate_seen=true`,
  `deck_lane_evidence_seen=true`, `deck_reference_evidence_seen=true`, and
  `deck_source_evidence_seen=true` through
  `deck_lanes=A_unknown_route_unknown+B_unknown_route_unknown`,
  `deck_reference=deck1_A_unknown_route_unknown+deck2_B_unknown_route_unknown`,
  and `deck_source=deck1_A_unknown_src_none+deck2_B_unknown_src_none`. That gives
  Viber/Gemini a citable internal "Deck A/B lanes exist but identity/route are
  unknown" receipt, while keeping `deck_lane_route_evidence_seen=false` and
  `deck_reference_route_evidence_seen=false` so unknown routes cannot become a
  transition verdict. It still exits non-zero because readiness is
  `missing_physical_proof`: no resolved/citable deck row, no connected
  controller posture, no recent controller move, no active deck audio lane, no
  per-deck delta context/evidence, no audible master audio, no bounded
  `audio_delta`, and no concrete route tiers. Local source diagnostics still
  found the folder-cache library with 1547 tracks, rekordbox 7 installed, and
  the live DB read policy disabled.
  A verifier run against that packet rejected
  `Great transition, clean handoff.` with `unsupported_live_outcome_claim` and
  `proof_not_ready`, while keeping `transport_status=fresh_schema_v2`. A second
  verifier run against a confession-style reply (`I need to correct the live
  read...`) also returned the calm public replacement
  `I caught the live move. The useful note is the sound change right there.`
  The live runtime was stopped after sampling.
  The runtime socket patch that made this proof possible:
  configured Deck A/B capture now forces the P1 old/current/future time map
  even on silent frames, so the advertised `audio_window_context` /
  `audio_window_map` capability is backed by raw structured packet fields and
  not only by a rendered preview fallback. Verification:
  `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py::test_configured_deck_pair_capture_forces_audio_window_on_silent_frame tests/runtime/test_ws_bus_deck_state.py::test_payload_marks_configured_deck_pair_capture tests/library/test_live_context_cli.py::test_viber_live_context_readiness_ignores_untrusted_audio_window_context`
  passed with 3 tests;
  `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/state/test_deck_context.py`
  passed with 183 tests; Ruff passed on the touched runtime/guard/test files;
  and `git diff --check` passed.
  Source-status and lane/reference follow-up verification:
  `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 206 tests; Ruff passed on the touched source-status files.
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  later passed with 186 tests after source-status-only frames gained safe
  `deck_lanes_context[...]` / `deck_reference_context[...]` and matching
  unknown-route evidence atoms; Ruff passed on the touched deck-context/runtime
  files.

- Deck Part audio-window bridge follow-up:
  the Python Viber normalizer and the Library webview normalizer now accept and
  preserve Deck A/B audio Part labels in `audio_window_context[...]` and
  structured `audio_window_map`. The important shape is
  `deckA_audio=P2`, `deckB_audio=P3`, `per_deck_audio=deck_pair_parts`,
  `duplicate_audio=separate_deck_pair_parts`, and
  `deck_audio_separation=deck_audio_separation_context`; the webview also
  preserves `deck_part_span_s` and `deck_part_activity`. This closes a product
  bridge gap where Python/Gemini could construct P2/P3 deck Part context, but
  Viber chat through the Library UI would silently drop the Part-aware
  `audio_window_map` and fall back to the old not-attached shape.
  A second webview fix treats `audio_part_context` and
  `deck_audio_separation_context` as volatile live fields, so a later frame
  that no longer carries Deck A/B Parts clears stale P2/P3 role labels before a
  Viber chat turn.
  Verification:
  `uv run pytest -q tests/library/test_codex_curate.py::test_chat_prompt_preserves_deck_pair_audio_window_map tests/library/test_codex_curate.py::test_chat_prompt_includes_bounded_live_deck_context_guard`
  passed with 2 tests;
  `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 100 tests;
  `uv run ruff check src/vibemix/library/codex_curate.py tests/library/test_codex_curate.py`
  passed;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 62 tests; `npm --prefix tauri/ui run build` passed;
  `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py`
  passed with 230 tests after the setup-hint regression; and
  `git diff --check` passed.

- Rekordbox route setup hint:
  `library live-context --json` now converts a local Rekordbox deck-output
  routing hint into a concrete `setup_hint` while preserving the proof fence.
  With the current local settings and no live socket, a sample
  `uv run python -m vibemix library live-context --json --timeout 0.2 --frames 1`
  exited non-zero as expected (`readiness.diagnosis=live_socket_missing`) but
  returned `setup_hint.status=rekordbox_route_hint_found`,
  `deck_channels=A=0,1;B=2,3`,
  `recommended_env.VIBEMIX_INPUT_DEVICE=BlackHole 16ch`,
  `recommended_env.VIBEMIX_DECK_AUDIO_CHANNELS=auto`, and
  `rule=setup_hint_not_live_audio_proof`. This moves the remaining physical
  proof from "infer the env from diagnostics" to a direct setup recipe without
  letting route metadata satisfy live audio proof.
  Verification:
  `uv run pytest -q tests/library/test_live_context_cli.py::test_viber_setup_hint_turns_rekordbox_route_hint_into_env tests/library/test_live_context_cli.py::test_cmd_library_live_context_text_failure tests/library/test_live_context_cli.py::test_viber_source_status_reports_ws_port_listener`
  passed with 3 tests;
  `uv run pytest -q tests/library/test_live_context_cli.py tests/audio/test_deck_capture.py`
  passed with 39 tests; and
  `uv run ruff check src/vibemix/__main__.py tests/library/test_live_context_cli.py`
  passed.

- Too-narrow capture guard:
  if `VIBEMIX_DECK_AUDIO_CHANNELS=auto` resolves a Deck A/B route that requires
  more channels than the selected capture device or opened stream provides, the
  runtime now fails closed as a setup block. It does not publish a partial
  A-only deck map. The capture context records
  `deck_audio_required_opened_channels=4` and either
  `deck_audio_capture_reason=capture_device_too_few_channels` or
  `deck_audio_capture_reason=opened_channels_too_few`; the rendered separation
  packet includes `setup_block=...`, and readiness reports that the deck-pair
  route hint requires a multichannel capture device/opened channels.
  Verification:
  `uv run pytest -q tests/audio/test_deck_capture.py::test_deck_audio_routing_auto_reports_too_narrow_capture_device tests/state/test_deck_context.py::test_deck_audio_separation_context_marks_too_narrow_auto_capture tests/library/test_live_context_cli.py::test_viber_live_context_readiness_names_too_narrow_deck_capture_device`
  passed with 3 tests;
  `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/library/test_live_context_cli.py`
  passed with 102 tests; and
  `uv run ruff check src/vibemix/audio/deck_capture.py src/vibemix/state/deck_context.py src/vibemix/__main__.py tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/library/test_live_context_cli.py`
  passed.

- Per-deck historical recall gate:
  `MIX_MOVE` memory recall now accepts either the existing global `audio_delta`
  or the new per-deck capture delta evidence in
  `audio_capture_context.deck_audio_deltas`. This preserves the cost gate
  (`move` plus `sound changed`) while letting the system learn and compare
  deck-local moves such as "Deck A RMS rose while Deck B fell" even when the
  global master-delta detector is too coarse to fire. Heartbeats, moves without
  sound evidence, and no-move events still avoid the embed path.
  Verification:
  `uv run pytest -q tests/memory/test_retrieval.py tests/memory/test_ingest.py`
  passed with 17 tests;
  `uv run pytest -q tests/memory/test_no_live_path_import.py tests/memory/test_no_extraction.py`
  passed with 5 tests; and
  `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_coach.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/memory/test_retrieval.py tests/memory/test_ingest.py`
  passed with 265 tests.

- Both-lane active proof gate:
  readiness now distinguishes "some captured deck audio is active" from "both
  Deck A and Deck B are active." A configured capture with
  `deck_audio_capture=A_active+B_silent` remains useful context, but it no
  longer satisfies the proof-ready state for the full deck-pair hearing goal.
  The Python proof gate adds `deck_audio_capture_both_active`, and the Library
  UI live-read badge stays partial with the detail `both decks active` until a
  `deck_audio_capture=A_active+B_active` receipt appears. This better matches
  the product claim: "Viber/Gemini can hear each deck," not merely "one
  captured deck lane is currently making sound."
  Verification:
  `uv run pytest -q tests/library/test_live_context_cli.py::test_viber_live_context_readiness_passes_for_deck_controller_audio_evidence tests/library/test_live_context_cli.py::test_viber_live_context_readiness_requires_both_deck_audio_lanes_active`
  passed with 2 tests;
  `npm --prefix tauri/ui test -- src/library/chat.test.ts` passed with 26
  tests; `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 63 tests; and
  `uv run pytest -q tests/audio/test_deck_capture.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_coach.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/memory/test_retrieval.py tests/memory/test_ingest.py`
  passed with 266 tests.

- Library live-read UI parity:
  the webview badge now mirrors the backend proof gate for deck identity and
  provenance too. It will not show `armed` from deck-pair audio receipts alone;
  both Deck A and Deck B must have resolved identities, citable `track_id`
  values, trusted source provenance, and active captured audio. Missing proof is
  presented as calm live-read status, keeping self-correction/confession
  language out of the user-facing Viber response.
  Verification:
  `npm --prefix tauri/ui test -- src/library/chat.test.ts` passed with 27
  tests; `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 64 tests; `npm --prefix tauri/ui run build` passed; the focused
  Python public-reply scrub regressions in `tests/library/test_codex_curate.py`
  passed with 3 tests; and `git diff --check` passed.

- Gemini attached-audio contract cleanup:
  the live Gemini prompt no longer says
  `optional_later_parts_not_current_deck_audio` when Deck A/B audio Parts are
  actually attached. The audio contract is now conditional:
  `deck_audio_parts=not_attached` on P1-only turns, and
  `deck_audio_parts=attached_configured_deck_pair_refs deckA_audio=P2
  deckB_audio=P3 ... deck_parts_rule=reference_not_quality_verdict` when
  configured deck-pair Parts ride beside the master mix. This keeps the nearby
  context aligned with the real `contents` array: P1 is still the audience-truth
  master/global mix, while P2/P3 are clean deck-reference audio for contribution
  mapping, not transition scoring by themselves.
  Follow-up hardening makes this true when other audio Parts are present too:
  `audio_part_context[...]` now includes `part_order=...`, so a mic Part and/or
  source-file lookahead can occupy P2/P3 while Deck A/B correctly shift to later
  labels such as P4/P5. The final `AUDIO PART CONTRACT` now says
  `deck_separation=deck_pair_parts` when deck Parts are actually attached,
  instead of the contradictory old `deck_separation=structured_text_only`. The
  Python and webview audio-part validators now keep the full P1+mic+lookahead+
  Deck A/B contract under a 1400-char cap, preserving the `rule=...` tail instead
  of truncating the strongest safety label. The validators now also require a
  complete, non-conflicting Deck A/B map whenever
  `per_deck_audio=deck_pair_parts`: both `deckA_part=P...` and `deckB_part=P...`
  must be present, distinct, listed in `part_order=...`, and each label must map
  only to its configured deck capture role. A label reused for mic/lookahead or a
  partial one-deck deck-pair map is dropped before Viber/Gemini sees it. The same
  distinct-label rule now applies to the time-window sibling too:
  `audio_window_context[...]` and structured `audio_window_map` reject
  `deckA_audio=P...` / `deckB_audio=P...` when both sides point at the same Part,
  so the "old/current/action" map cannot silently collapse both decks onto one
  audio reference. Renderer-side hardening now mirrors the validator: if an
  upstream caller passes partial, colliding, or mic/lookahead-conflicting Deck
  Part labels, `render_audio_part_context(...)`, `render_audio_window_context(...)`,
  `render_audio_window_map(...)`, and the co-host's final `AUDIO PART CONTRACT`
  fall back to `deck_audio_parts=not_attached` / `per_deck_audio=structured_text_only`
  instead of emitting a contradictory deck-pair packet.
  Verification:
  `uv run pytest -q tests/agent/test_dj_cohost.py::test_llm_node_03a_fences_cold_p1_audio_with_claim_policy tests/agent/test_dj_cohost.py::test_llm_node_audio_map_reflects_configured_deck_pair_capture tests/agent/test_dj_cohost.py::test_llm_node_attaches_configured_deck_audio_parts_on_mix_move tests/agent/test_dj_cohost.py::test_llm_node_03b_places_deck_audio_map_next_to_audio_part`
  passed with 4 tests; `uv run pytest -q tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_cache_hit.py`
  passed with 54 tests; and
  `uv run ruff check src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost.py`
  passed.
  Latest focused verification for the part-order follow-up:
  `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/runtime/test_ws_bus_deck_state.py`
  later passed with 247 tests; `uv run ruff check src/vibemix/agent/dj_cohost.py src/vibemix/state/deck_context.py src/vibemix/library/codex_curate.py tests/agent/test_dj_cohost.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed; `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 69 tests; and `npm --prefix tauri/ui run build` passed.

- Supported-verdict proof state:
  the live claim policy is no longer only a brake. It now has a
  `supported_verdict` branch that allows transition/blend/handoff scoring only
  when the current turn has recent move context, citable Deck A and Deck B rows,
  trusted source provenance, both-active deck-pair audio capture,
  per-deck feature receipts, deck/global audio-delta evidence, and a two-lane
  pre/current `deck_audio_window` packet. Weaker two-deck cases still return
  `candidate_not_verdict`, and one-deck/single-move cases still return `blocked`
  or `watch_not_claim`. Gemini receives
  `claim_policy[policy=supported_verdict rule=grounded_verdict_allowed]` in the
  audio context map when the proof is strong; Viber keeps `move_grades` and a
  quality reply only under the same strong live-evidence packet.
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

- Gemini per-turn audio-Part verdict boundary:
  state-level deck-pair capture can be strong while the current Gemini request
  still lacks actual Deck A/B audio Parts. The live cohost now treats that as
  candidate-only for this turn: `_build_attached_audio_context_clause(...)`,
  `should_defer_live_claim_stream(...)`, and `apply_live_claim_guard(...)` all
  receive `deck_audio_parts_attached=False` unless the validated Deck A/B labels
  are present and non-conflicting in the attached `contents` array. This keeps
  `deck_audio_features_context` and `deck_audio_delta_context` useful as
  context, while preventing Gemini from seeing or leaking
  `claim_policy=supported_verdict` on P1-only turns. Public output becomes the
  calm candidate-held line; the internal reason is
  `deck_audio_parts_not_attached`.
  Verification:
  `uv run pytest -q tests/agent/test_dj_cohost.py::test_llm_node_downgrades_verdict_when_deck_audio_parts_not_attached tests/agent/test_dj_cohost.py::test_llm_node_attaches_configured_deck_audio_parts_on_mix_move tests/state/test_deck_context.py::test_live_claim_guard_requires_attached_deck_audio_parts_when_requested tests/state/test_deck_context.py::test_live_claim_guard_allows_verdict_with_citable_deck_pair_audio_delta`
  passed with 4 tests; `uv run pytest -q tests/agent/test_dj_cohost.py tests/state/test_deck_context.py`
  passed with 119 tests; and `uv run pytest -q tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 113 tests.

- Supported-verdict UI wire:
  the Library webview now gives the positive proof state a public label instead
  of falling through to generic `ready`. A `supported_verdict` receipt renders
  as `scoring grounded`, and when move grades are present and allowed the
  artifact adds `move scoring grounded by live read`. The raw policy string
  stays hidden from the user-facing chrome.
  Verification:
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 66 tests, and `npm --prefix tauri/ui run build` passed.

- Trusted-source hardening for supported verdicts:
  the state-level `supported_verdict` gate now uses the same trusted deck-source
  allow-list semantics as the app surface (`rekordbox_xml`, `folder_cache`,
  `screen_vision`, `numpy_key`, `nowplaying`). Arbitrary non-empty sources no
  longer unlock scoring merely because they are not `unknown`; they stay
  `candidate_not_verdict`. The Python Viber/backend and live-proof CLI now read
  the same shared `DECK_CONTEXT_TRUSTED_SOURCES` constant instead of carrying
  separate source lists, and the Viber chat regression covers an untrusted Deck
  B source with otherwise strong Deck A/B audio evidence.
  Verification:
  `uv run pytest -q tests/state/test_deck_context.py::test_live_claim_guard_allows_verdict_with_citable_deck_pair_audio_delta tests/state/test_deck_context.py::test_live_claim_guard_requires_trusted_sources_for_supported_verdict tests/state/test_deck_context.py::test_live_claim_guard_keeps_candidate_when_deck_pair_audio_delta_missing`
  passed with 3 tests;
  `uv run pytest -q tests/library/test_codex_curate.py::test_chat_with_codex_allows_quality_grade_with_strong_deck_pair_proof tests/library/test_codex_curate.py::test_chat_with_codex_requires_trusted_sources_for_quality_grade tests/state/test_deck_context.py::test_live_claim_guard_requires_trusted_sources_for_supported_verdict`
  passed with 3 tests;
  `uv run pytest -q tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_cache_hit.py`
  passed with 188 tests; and
  `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/library/codex_curate.py src/vibemix/agent/dj_cohost.py src/vibemix/__main__.py tests/state/test_deck_context.py tests/library/test_codex_curate.py tests/agent/test_dj_cohost.py`
  passed; `git diff --check` passed.

- Rust/Tauri command bridge parity:
  the `library_chat` argument-shape test now includes
  `deck_audio_features_context`, `deck_audio_delta_context`, and structured
  `audio_window_map` in the serialized `--live-context` payload. This proves
  the desktop command bridge preserves the full live-context packet and does not
  accidentally pin an older pre-deck-audio contract.
  Verification:
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml chat_library_args_preserve_time_aligned_audio_context`
  passed, and the full `cargo test --manifest-path tauri/src-tauri/Cargo.toml`
  run passed with 116 tests.

- First-class pre/current deck-audio window receipts:
  `deck_audio_window_context[...]` is now paired with a compact citable
  `deck_audio_window=...` live-evidence atom. The atom records each deck lane's
  pre/current RMS window (`A_active_pre_..._current_...`) without turning that
  descriptor into a causal or quality verdict. Viber live-readiness, the Library
  proof badge, and `supported_verdict` all require the receipt alongside
  deck-pair capture, per-deck features, and per-deck deltas. MIX_MOVE recall can
  also pass on `deck_audio_windows`, so historical memory learns from the
  "move plus before/current audio changed" pattern without needing the public AI
  to confess uncertainty or print raw proof diagnostics.
  Verification:
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_coach.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/memory/test_retrieval.py`
  passed with 228 tests;
  `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 72 tests;
  `uv run ruff check src/vibemix/state/deck_context.py src/vibemix/__main__.py src/vibemix/library/codex_curate.py src/vibemix/memory/retrieval.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_coach.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/memory/test_retrieval.py`
  passed;
  `npm --prefix tauri/ui run build` passed; and `git diff --check` passed.

- EvidenceRegistry and prompt-citation parity for deck windows:
  the 10 Hz `state_refresh_loop` now receives the shared deck capture context and
  writes `deck_audio_capture=...`, `deck_audio_features=...`,
  `deck_audio_delta=...`, and `deck_audio_window=...` into the
  `EvidenceRegistry` through the same `live_mix_evidence_keys(...)` path used by
  sockets and Viber. `AICoach.build_prompt(...)` also receives the deck capture
  context, so `grounding_refs[...]` can render `[mix:deck_audio_window=...]` and
  the live evidence line does not silently drop the per-deck receipt. This closes
  the gap where the model could see structured deck context but lack a citable
  registry reference for the exact before/current deck-lane audio.
  Verification:
  `uv run pytest -q tests/state/test_refresh.py::test_tick_registers_citable_deck_audio_window_evidence tests/state/test_refresh.py::test_18_02_state_refresh_loop_threads_registry_kwarg tests/state/test_deck_context.py::test_grounding_refs_render_registered_deck_audio_window_receipt tests/state/test_coach.py::test_evidence_line_renders_registered_deck_audio_window_ref tests/agent/test_dj_cohost.py::test_llm_node_audio_map_reflects_configured_deck_pair_capture tests/agent/test_dj_cohost.py::test_llm_node_03b_places_deck_audio_map_next_to_audio_part`
  passed with 6 tests;
  `uv run pytest -q tests/agent/test_dj_cohost.py tests/state/test_coach.py tests/state/test_deck_context.py tests/state/test_refresh.py`
  passed with 242 tests;
  `uv run pytest -q tests/runtime/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py tests/memory/test_retrieval.py tests/test_main_smoke.py`
  passed with 177 tests;
  `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 72 tests; and focused Ruff checks passed.

- Event-handoff timing for historical move memory:
  `coach_loop` now attaches the shared `audio_capture_context` to `ev.extra`
  immediately after detection, before `agent.set_next_event(ev)`. That ordering
  is important because recall pre-dispatch runs inside `set_next_event`; a
  MIX_MOVE should decide whether to embed based on the same per-deck windows and
  deltas that Gemini will later see. The state tracer's live-evidence context
  also renders with the deck capture context, so diagnostics do not drift from
  the prompt/socket packet.
  Verification:
  `uv run pytest -q tests/runtime/test_coach.py::test_coach_event_log_carries_deck_move_audio_context`
  passed; `uv run pytest -q tests/runtime/test_coach.py tests/agent/test_dj_cohost.py tests/state/test_coach.py tests/state/test_deck_context.py tests/state/test_refresh.py tests/memory/test_retrieval.py`
  passed with 268 tests; focused Ruff checks passed; and `git diff --check`
  passed.

- Last-known deck identity as non-citable context:
  a deck that was independently resolved earlier in the session can now ride
  along as `source=last_known` when the controller is still connected and the
  row is younger than 30 minutes. This is not an identity source and not a
  transition-proof leg. Its confidence is capped at `0.29`, below the shared
  resolved-deck floor, and the source-status packet declares
  `last_known_rule=context_only_not_current_identity_proof`. Viber keeps the
  label through live-context normalization so the prompt can preserve useful
  human context, while the supported-verdict gate still requires current,
  trusted Deck A/B sources plus audio proof. Public chat hygiene was also
  tightened on both the Viber wrapper and shared Gemini/live-coach guard: if the
  model emits self-confession, internal guard labels, or "doing something
  stupid" style live-read language, the result boundary replaces it with calm
  DJ-facing copy and keeps the reason in diagnostics.
  Verification:
  `uv run pytest -q tests/state/test_deck_poller.py tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_live_context_cli.py tests/library/test_codex_curate.py`
  passed with 240 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 72 tests;
  focused Ruff checks passed; and `git diff --check` passed.

- Audio Part cost visibility plus move-to-deck-window binding:
  Gemini's audio context now names the expected token footprint in the same
  bounded Part contract that labels P1, mic, lookahead, and Deck A/B audio.
  The estimate uses the documented 32 audio tokens/sec rate; P1, mic,
  lookahead, and deck-pair Parts each carry `*_tokens_est=...`, and the turn
  carries `model_audio_tokens_est=...` in the prompt plus `audio_tokens_est` in
  the `llm_invoke` event. This makes the cost shape inspectable instead of
  implicit. The cache boundary remains: static persona/rules/profile live in
  the Gemini context cache, while current audio Parts are short per-turn
  volatile payload. The move-effect packet now binds deck-pair capture back to
  the human action: when deck capture supplies deltas/windows, it renders
  `deck_deltas=A:...+B:...` and
  `deck_windows=A:active:pre_...:current_...+B:...` next to the recent move.
  This gives Viber/Gemini the "twist knob -> deck lane audio changed" training
  shape without claiming the move caused the change or that the transition was
  good.
  Verification:
  `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost.py tests/runtime/test_coach.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py`
  passed with 267 tests;
  `uv run pytest -q tests/audio/test_deck_capture.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_cache_hit.py tests/state/test_coach.py tests/runtime/test_ws_bus_deck_state.py tests/state/test_refresh.py tests/memory/test_ingest.py tests/memory/test_retrieval.py`
  passed with 173 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 72 tests;
  focused Ruff checks passed; and `git diff --check` passed.
