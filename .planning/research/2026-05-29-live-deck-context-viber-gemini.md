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
- `audio_part_context` for Gemini's attached audio Parts: P1 is the current
  live global mix, optional P2 can be Kaan's mic/user speech, optional P2/P3 can
  be source-file lookahead, and none of those Parts are deck stems. This makes
  the "old/current/action/+3s" arrangement explicit without duplicating audio or
  giving the model permission to treat future/lookahead as current audience
  evidence.
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

## Official Gemini Facts Used

Sources:

- Audio understanding: https://ai.google.dev/gemini-api/docs/audio
- Token guide: https://ai.google.dev/gemini-api/docs/tokens
- Context caching: https://ai.google.dev/gemini-api/docs/caching
- Live API capabilities guide: https://ai.google.dev/gemini-api/docs/live-guide
- Live API session management: https://ai.google.dev/gemini-api/docs/live-session
- Gemini models: https://ai.google.dev/gemini-api/docs/models/gemini
- Pricing: https://ai.google.dev/pricing

Relevant facts verified 2026-05-29 from the current docs:

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
- Current pricing docs list Gemini 2.5 Flash Native Audio (Live API) paid audio
  input at `$3.00 / 1M tokens` and audio output at `$12.00 / 1M tokens`.
  Standard `generateContent` audio prices vary by model tier and are lower for
  Flash/Lite than native-audio Live output. Treat all pricing facts as volatile
  and re-check before any launch/billing decision.

Implication for Vibemix:

- The current 6s diet window costs about 192 audio tokens.
- The current 18s full window costs about 576 audio tokens.
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
- Exact citable refs should be small text copied from the registry snapshot.
  They are essentially free compared with another audio pass and give the
  linter a structural way to reject invented move/route claims.
- Long persona/profile/static grounding belongs in the existing Gemini context
  cache; volatile deck/move state stays in the per-turn prompt.
- Per-deck "hearing" must be represented as structured routing context unless
  we add true isolated deck capture. Gemini's audio guide says multi-channel
  audio is combined into one channel, so sending a stereo/master feed cannot be
  relied on as deck A/deck B separation.

## Local Implementation Map

- Audio Part structuring for Gemini:
  - `contents[0]` is always the text packet: static/cached system behavior,
    current task, compact evidence line, and the audio-adjacent deck map.
  - `contents[1]` is P1: the current live master/booth audio window
    (`audio/wav`). It is the audience-true global mix, not isolated deck stems.
  - Optional later Parts are separately labeled by the prompt suffix: mic audio
    only when Kaan recently spoke, and lookahead only when explicitly enabled as
    `NOT YET HEARD BY AUDIENCE`. Those Parts must never be treated as current
    deck audio.
  - The `AUDIO CONTEXT MAP FOR ATTACHED P1` sits immediately before the audio
    Part description and repeats only bounded live facts:
    `deck_context`, compact `deck_lanes_context`, `deck_source_context`,
    `mixer_context`, `deck_audio_context`, `audio_window_context`,
    `move_context`, `deck_change_context`, `move_effect_context`,
    `live_evidence`, and `claim_policy`.
  - `audio_window_context[...]` is the "old part / current move / +3s forward"
    contract. It labels P1 as the heard master/global mix with `P1_heard=true`,
    marks the packet as `timeline=past_action_future`, splits P1 into `pre`,
    `current`, and `action` spans, anchors recent user moves by age when
    available, and labels any lookahead Part as `future_heard=false` /
    `forecast_only_not_audience_evidence`. It also states
    `deckA_audio=not_attached` and `deckB_audio=not_attached`, so duplicated
    master audio can never masquerade as clean deck stems. The source/limit
    fields are intentionally emitted before long `move_anchor` strings so the
    UI/Viber cap cannot clip away the anti-hallucination contract.
  - The runtime prompt now also carries an explicit `AUDIO PART CONTRACT`:
    `P1=live_global_mix isolated_decks=false
    deck_separation=structured_text_only
    audio_window_context=time_aligned`. The generic Part suffix labels P1 as a
    global mix rather than isolated deck stems, mic Parts as not deck audio, and
    lookahead Parts as not current live deck audio.
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
  `audio_window_context`, `audio_delta`, `move_context`,
  `deck_change_context`, and `move_effect_context` on move event rows;
  `src/vibemix/memory/ingest.py` includes those fields in deterministic
  `coach_line` signatures (`SIG_TEMPLATE_VERSION=v8-coach_line-context-feed`)
  without doing extraction or another model call. `src/vibemix/memory/retrieval.py`
  and `src/vibemix/agent/dj_cohost.py` mirror `audio_window=` into recall
  queries, so "this knob/fader move changed the sound this way" can be compared
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
  transition gates under its 8-token cap.
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
  same safety-token priority under its 8-token cap and derives missing `mix:...`
  refs from `live_evidence.mix`, so direct CLI/Tauri payloads cannot lose the
  citable deck-lane or transition-gate atoms at the last prompt boundary.
- Viber chat-history sanitizer: prior chat turns are bounded before entering
  the Codex prompt, and stale Viber live outcome claims are omitted whenever the
  current live context is blocked, watch-only, or candidate-not-verdict. User
  wording remains dialogue, but older assistant phrases such as "great
  transition" no longer prime a fresh turn beside a single-deck evidence packet.
- Result-boundary correction hardening: shared Gemini guard code and the Viber
  chat wrapper now preserve honest self-corrections such as "I can't call that a
  transition," but do not let a disclaimer smuggle in a fresh unsupported
  outcome claim such as "but that blend was clean."
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
- Result-boundary corrections should name the compact lane evidence when
  available. If the model says "great transition" from one-deck evidence, the
  corrected reply now carries a summary such as
  `deck lanes=A=known:dominant / B=unknown:muted` plus
  `deck source=... second_deck=independent_source_required
  rule=unresolved_deck_is_not_transition_evidence`, so the final answer teaches
  the same per-deck and source-provenance frame the prompt used.
- A self-correction is safe only when it actually withdraws the claim. "I can't
  call that a transition" may pass; "I can't call it a transition, but that
  blend was clean" must still be corrected because the second clause invents a
  multi-deck quality verdict.
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
  gating, safety-evidence priority under the 8-atom cap, and browser-side
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
  passed with 254 tests, and Ruff check/format check passed on the touched
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
  The ordering keeps `move_effect=...` inside the 8-item evidence cap by
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
  same high priority as the Python/Viber/CLI path, so the 8-token cap preserves
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
  treating them as identity proof. Verification:
  `uv run pytest -q tests/runtime/test_ws_bus_deck_state.py tests/library/test_codex_curate.py tests/state/test_deck_context.py tests/library/test_live_context_cli.py`
  passed with 138 tests;
  `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 48 tests; and Ruff passed on the touched Python files.
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
  `audio_part_context`, `deck_source_status`, and `audio_window_map` before
  declaring the sampled live packet ready. Missing schema/capabilities or structured lanes produce
  explicit blockers instead of letting a string-rendered prompt fence look like
  full proof. The Library UI now preserves the same schema/capability receipt
  through `normalizeLiveContextPayload` and into `libraryChat`, so a Viber chat
  turn can see whether the live context came from a schema-v2 socket. The
  prompt renderer also emits `live_context_transport[schema=2 capabilities=...
  rule=transport_receipt_not_musical_evidence]`, so this receipt is visible to
  Viber as metadata, not as music/deck outcome evidence. When schema/capability
  proof is missing, the latest local sampler writes
  `.planning/research/live-context-latest-proof.json` with
  `readiness.diagnosis=live_socket_missing`, `frames_seen=0`, and missing
  capabilities including `audio_part_context`.
  data is absent or incomplete, the same prompt line renders
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
- Viber live-proof receipt in the shipped chat path:
  the verifier is now attached to real `library chat` results whenever live
  context is present. `CodexChatResult.to_dict()` carries a bounded
  `live_verification` packet with final reply pass/fail, claim policy,
  transport freshness, move-grade allowance, and internal guard/correction
  diagnostics. The Library UI normalizes that packet into a `live proof` row in
  the chat side rack, with calm states such as `not armed`, `needs proof`,
  `verdict held`, and `checked`. Raw internal labels such as
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
  answer stays short (`Live proof is not armed...`), while structured detail
  stays in the JSON/CLI receipt (`transport_status=missing_live_context`,
  `claim_policy=requires_more_evidence`, `move_grades_allowed=false`). The
  Library UI maps the stop/tool detail to `live proof` and `live proof needed`
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
- Viber idle proof visibility:
  the chat side rack now renders a calm live-proof status row before the user
  asks. It shows `not armed`, `partial`, or `armed` based on the same schema-v2,
  deck lane/reference, source/provenance, audio-window, and transition-gate
  fields sent to Viber. When context is present, the row includes the deck
  reference summary (`deck1 A=known:dominant / deck2 B=unknown:present`) so the
  operator can see whether Viber has deck1/deck2 footing without reading a long
  explanation. This is UI chrome, not spoken Viber copy, and it deliberately
  avoids raw guard/violation/stop labels. Verification:
  `npm --prefix tauri/ui test -- src/library/chat.test.ts src/library/api.test.ts`
  passed with 53 tests, and `npm --prefix tauri/ui run build` passed. The build
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
  a live `uv run python -m vibemix` session was started and sampled with
  `uv run python -m vibemix library live-context --wait-ready 3 --interval 1 --json --out .planning/research/live-context-latest-proof.json`.
  The sampler reached the real socket (`frames_seen=63`,
  `flat_deck_frame_seen=true`, `session_snapshot_seen=true`), saw schema v2
  with `missing_capabilities=[]`, and confirmed `audio_part_context_seen=true`.
  Readiness stayed false for physical reasons only: no resolved/citable deck
  row, no recent control move, no audible master audio, and no bounded
  `audio_delta`. The runtime was then stopped cleanly. In the same pass, the
  visible live-claim correction text was changed from diagnostic self-correction
  prose to short product copy such as `Live proof is incomplete, so the
  transition verdict is held for now.` Detailed lane/source/provenance reasons
  remain in structured guard summaries and `live_verification`, not in the
  spoken/chat reply. Verification:
  `uv run pytest -q tests/state/test_deck_context.py tests/runtime/test_ws_bus_deck_state.py tests/library/test_codex_curate.py tests/library/test_live_context_cli.py tests/agent/test_dj_cohost.py tests/agent/test_dj_cohost_3part.py tests/agent/test_dj_cohost_linter.py`
  passed with 219 tests, `npm --prefix tauri/ui test -- src/library/api.test.ts src/library/chat.test.ts`
  passed with 53 tests, and Ruff passed on the edited guard/copy files.
