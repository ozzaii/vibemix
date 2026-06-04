# BACKEND WIRING EXIT-MAP — 2026-06-04

For the vibemix backend Codex lanes (library / learn / sven / keystone+packaging). Synthesis of 12 verified
audit slices + the owned packets (`GOAL-{sven,learn,engine}.md`, `CODEX_READY-CHATTERBOX-VOICE-WIRED.md`,
`CODEX_READY-PILL-STREAK-ROBOT-VOICE.md`, `PILL-FAFO-AND-LEVELUP.md`, `SHIP-READINESS-2026-06-04.md`,
`CUE-LAND-ENGINE.md`, `docs/PROMPT-COMPOSITION.md`) and the companion `FRONTEND-WIRING-EXIT-MAP.md`. Pin a SHA
before acting — the tree is hot (HEAD `86a3527f` as this is written; the audits walked through `7057d154` /
`b6217dde` / `ec57bd5a`, line numbers drift as files grow, so confirm each anchor before each edit).

Tier language is load-bearing and never conflated: **SRC** (green tests on current source) != **PKG** (in the
signed DMG built at HEAD) != **LIVE** (a real user runs the app and HEARS a grounded result).
`test-passing-but-dark = 0`.

---

## VOICE — why the new voice never plays + the exact fix

The founder's live concern leads. Kaan ran a full ear-driven bench this session and LOCKED a new live co-host
voice (Chatterbox-Turbo MLX, the "pranker" clone, temp 0.4), plus a Daft-Punk-"Technologic" robot voice for the
pill streak/combo callout. Neither plays. Here is the exact root-cause chain and the precise wires.

### Root-cause chain (the new voice is structurally unreachable from a normal launch)

1. **The voice engine is selected by env ONLY.** `build_tts_chain` (`src/vibemix/agent/tts_chain.py:36`)
   defaults to MOSS and switches to Chatterbox-Turbo only when
   `os.environ.get("VIBEMIX_TTS_ENGINE","moss").strip().lower() == "chatterbox"` (`tts_chain.py:53`). The two
   live call sites are `__main__.py:1607` (direct) and `:1621` (proxy), both via `_build_tts_chain_or_mute`
   (`__main__.py:237`), and NEITHER passes an engine argument — the builder reads the env itself.

2. **A normal/packaged launch cannot set that env.** `open -a vibemix` / Dock / launchd strip `VIBEMIX_*` from
   the inherited env — that is exactly WHY `VIBEMIX_LOCAL_TTS` is force-seeded via `setdefault` in
   `_apply_packaged_defaults` rather than trusted from the launcher. So `VIBEMIX_TTS_ENGINE` is never set from a
   real app launch -> the `"moss"` default at `tts_chain.py:53` always wins -> the user always hears MOSS.

3. **There is no config field for the engine.** `ConfigStore` (`src/vibemix/runtime/config_store.py`) carries
   `voice`, `mode`, `genre`, `llm_mode` (`:194`), and persists the `_PHASE12_FIELDS` set (`:68`) — but it has
   **no `tts_engine` field**. The boot bridge `apply_persona_config_to_env` (`src/vibemix/runtime/settings.py:72`)
   seeds `VIBEMIX_SKILL_LEVEL` / `VIBEMIX_MODE` / `VIBEMIX_MOOD` from config; `_apply_deck_audio_config_to_env`
   (`__main__.py:1060`, called at `:1420`) seeds the deck-audio env. There is no equivalent TTS-engine seed. So
   even though the sidecar reads `config.json` at boot — the same file the Rust GUI writes — the engine choice
   has no field to live in and no env-seed bridge to carry it. The selector is unreachable end-to-end.

4. **The Technologic robot streak voice has zero code, AND its trigger signal is mis-grounded.** Grep for
   `technologic` / `streak_voice` / `combo_voice` returns nothing — the robot voice is a proven recipe (Kaan
   ear-validated, `CODEX_READY-PILL-STREAK-ROBOT-VOICE.md`) but unwired. Worse, the streak it would ride is
   self-applause: `_next_grade_progress` (`src/vibemix/runtime/suggestion.py:1375`) increments off
   `_selected_move_grade(suggestion)` -> `grade.get("deserved")` — it ticks when the engine rates its OWN
   un-played SUGGESTION clean, not when the DJ executed a transition a live judge graded from real audio
   (confirmed by the FAFO probe, `PILL-FAFO-AND-LEVELUP.md` §Streak). Today that streak only feeds prompt TEXT
   (a `grade_progress` atom in `intel/context_compiler.py:637`); it gates no audio, so nothing slop ships yet.
   But landing a robot voice on the current streak ships the worst case: a callout that SOUNDS earned but is the
   engine clapping for itself (Invariant #3 violation).

### The precise wires

**Wire V1 — make the chosen engine reachable from a normal/packaged launch (mirror the deck-audio env precedent).**
- `src/vibemix/runtime/config_store.py` — add `tts_engine: str = "moss"` to the dataclass (after `:194`) AND add
  `"tts_engine"` to `_PHASE12_FIELDS` (`:68`) so it persists; coerce the value to `{"moss","chatterbox"}` in
  `from_dict` (alongside the existing coercions near `:228`).
- `src/vibemix/__main__.py:1420` (right after `_apply_deck_audio_config_to_env(_boot_settings_config)`) — add a
  TTS-engine seed mirroring that helper: `os.environ.setdefault("VIBEMIX_TTS_ENGINE", _boot_settings_config.tts_engine)`.
  `setdefault` keeps an explicit shell/.env override winning (consistent with `_apply_packaged_defaults`). No
  change to `tts_chain.py` — its `:53` env read becomes reachable because the config now writes the env.
- Frontend lane owns the settings rocker that writes `tts_engine` via the existing `ipc.settings.set` path; this
  backend wire is what makes that field do anything at boot. Cross-lane handshake (see FRONTEND map #3).

**Wire V2 — land the robot streak voice on a GROUNDED streak (gated behind V3; mirror `mastered_vocal.py`).**
- New `src/vibemix/runtime/streak_vocal.py` mirroring `src/vibemix/learn/mastered_vocal.py`: a hand-authored
  copy bank (never LLM-generated, the `mastered_vocal.py:11-13` anti-slop contract) with a
  `streak_milestone_line(streak, *, before, after) -> str | None` that fires EXACTLY ONCE per milestone crossing
  (x3 / x5 / x10) by construction, like `mastered_unlock_line`. Callouts <=8-10 words (the robot voice is gappy;
  `CODEX_READY-PILL-STREAK-ROBOT-VOICE.md` §two-hard-requirements).
- Render through the existing fire-once fixed-text path: `runtime/coach.py::_make_mastered_speak` (the proven
  grounded one-shot say path), with the robot timbre from a second `ChatterboxLocalTTS(ref=robot_voice_ref)`
  (`src/vibemix/agent/chatterbox_tts.py`) and a de-gap silence-trim on the rendered PCM (mandatory; the recipe
  packet). Surface = debrief / a deliberately-opened progress view, NEVER the live eyes-off pill (Kaan's
  "live'dan ayrı" call).

**Wire V3 — re-bind the streak to a cited, executed transition (load-bearing grounding fix; PREREQ for V2).**
- The streak must increment on an EXECUTED, judged transition, not a computed suggestion. The grounded signal
  exists: `runtime/coach.py::_credit_judged_transition` (`:313`) + the live Judge (`_run_live_judge`, `:364`).
  Move the increment trigger off the suggestion-compute sites (`suggestion.py:386/520/1015/1295`) and onto the
  credit-on-executed-transition site in `coach.py`, keyed by an EvidenceRegistry-resolvable `[ev:BEATMATCH_GRADED@…]`
  / `[judge:…]` citation. That live judge event does NOT exist on the bus on a master-only rig today (practice /
  recorder only) — so this is real plumbing, not a quick wire, and it is the prerequisite before V2 speaks.

### Default-engine decision needed from Kaan

The proven floor is `tts_engine` default `"moss"` (never-mute; Chatterbox already falls back to MOSS when
unavailable, `tts_chain.py:56-67`). Flipping the PACKAGED default to `"chatterbox"` is defensible (Kaan ear-LOCKED
it as the live voice) but gated on TWO owner calls that are also in `SHIP-READINESS`: (a) add `mlx-audio` to the
shipped dep surface (it reintroduces `transformers` 5.x and is Apple-only; today `chatterbox_available()=False`
in-app, so the flip would be inert), and (b) bundle the ~675MB model + the music-stripped ref clip
(`~/.cache/vibemix/cohost_voice_ref.wav`, a licensing call). See NEEDS-CLARIFICATION.

---

## The exit, in one paragraph

"Fully wired backend" means every engine value the product computes either reaches the human surface it was built
for — a spoken line, a pill receipt, a credited skill, a persisted choice — the instant it is grounded, OR stays
honestly dark by an OWNED decision (default-off opt-in, honest-null abstain, env-gated dormant feature). The good
news from the 12 slices: the brain is real (~80% SRC) and the citation-grounded read path is healthy (recall,
taste, profile, debrief, the Judge, the keystone EQ-move model all reach the prompt). The dark is concentrated and
specific: (1) the chosen voice engine is env-only and unreachable from a normal launch; (2) the new streak/robot
voice is unwired AND rides a self-applauding signal that must be re-grounded first; (3) the in-GUI brain (Gemini
key persist + proxy) has its IPC contract built but NO handler — a stranger has no in-app path to a brain; (4)
several measured engine outputs reach the prompt machinery but never speak because the payload-attach gate omits
their event types (HEARTBEAT receipts, LAYER_ARRIVAL band-jumps, transition-scorer reasons, Judge risk-flags); (5)
two cue-landing spines coexist (the live Viber auto-cue path vs the orphaned reusable `cue_landing.land()`
engine); (6) the route-doctor recommendation flips device run-to-run on RMS noise, so the operator can copy a
coin-flip device into the keystone capture. The backend lanes close every break under `src/vibemix/**` + the
PyInstaller specs + the proxy/billing config, hand the IPC schema halves to the frontend lane via named types, and
prove each one BY EAR (or by-bus) in the running app before exit. Exit is not test-green; exit is the human
hearing or seeing it work.

---

## Wiring exit-map

Ordered by ship-leverage (top = closest to the VOICE / keystone / democratization / anti-slop gates). Lane =
who owns the island. Proof = by-ear (a human hears the co-host) or by-bus (a value confirmed on the ws bus /
events.jsonl / a re-parsed export).

| # | Engine / value | Computed source (file:line) | Where it dies | THE EXACT WIRE (file:line -> file:line) | Lane | Proof |
|---|---|---|---|---|---|---|
| 1 | **Chosen TTS engine reachable from a normal launch** (Kaan's live voice) | `build_tts_chain` reads `os.environ.get("VIBEMIX_TTS_ENGINE","moss")` (`agent/tts_chain.py:53`); live builders `__main__.py:1607/1621` via `_build_tts_chain_or_mute:237` pass no engine arg | launchd/Dock strip `VIBEMIX_*`; no `ConfigStore.tts_engine` field; no env-seed bridge -> default MOSS always wins, Chatterbox unreachable | add `tts_engine="moss"` to `config_store.py` dataclass (~`:194`) + `_PHASE12_FIELDS` (`:68`) + `from_dict` coerce (~`:228`); add `os.environ.setdefault("VIBEMIX_TTS_ENGINE", cfg.tts_engine)` at `__main__.py:1420` (mirror `_apply_deck_audio_config_to_env:1060`). No `tts_chain.py` edit. | keystone+packaging | by-ear: set engine in config.json -> restart -> co-host speaks in the cloned voice (Chatterbox available on Mac); by-bus: `ps eww <sidecar>` shows `VIBEMIX_TTS_ENGINE` set |
| 2 | **In-GUI Gemini-key persist + DIRECT/PROXY** (democratization #1, ship-blocking) | IPC contract fully built: schema `messages.schema.json:1488` `SettingsSetBrain` + `:1530` `SettingsBrainAck`; Python `ui_bus/messages.py:1022` `SettingsSetBrain` + `:1044` `SettingsBrainAck.make`; boot reads `app_data_dir()/.env` (`__main__.py` candidate-2) | NO handler: `session_loop.py:register_handlers` (~`:263-290`) never registers `ipc.settings.set_brain`; `SettingsApplier.apply` (`runtime/settings.py:293`) has no brain field; no `.env` writer exists | add `register_handler("ipc.settings.set_brain", self._on_settings_set_brain)` at `session_loop.py:~270`; NEW `_on_settings_set_brain` -> persist `ConfigStore.llm_mode` via `save_config`, write `GEMINI_API_KEY` to `app_data_dir()/.env` (chmod 600, never log) via NEW `_write_env_key` helper, emit `SettingsBrainAck.make(ok,mode,key_set,restart_required=True)` (`messages.py:1044`) | keystone+packaging | by-bus: send `ipc.settings.set_brain` -> `.env` written + `brain_ack{key_set:true}` (key absent from ack + logs); by-ear: restart -> co-host boots DIRECT and speaks |
| 3 | **HEARTBEAT grounded receipt** (the #1 voice slop driver) | `task_for_event` HEARTBEAT branch wraps `_with_grounded_receipts` (`state/prompt_builder.py:893-903`), interpolating `next_suggestion_voice_line` etc. from `ev.extra` (`:785-802`) | `runtime/coach.py:765` attaches receipts only for `("PHASE","TRACK_CHANGE","TRANSITION_OPPORTUNITY")`; the voice builders self-gate (`_VOICE_EVENT_TYPES`) excluding HEARTBEAT -> HEARTBEAT's `_with_grounded_receipts` is a guaranteed no-op -> bare describe-bank task | add `"HEARTBEAT"` to the tuple at `runtime/coach.py:765` + to `_VOICE_EVENT_TYPES` in `runtime/suggestion_voice.py:20` and `runtime/set_plan_voice.py:21` (NOT `transition_verdict_voice.py` — a verdict on a heartbeat is ungrounded). Receipts already mutate `ev.extra` before `build_prompt` (same loop) | sven | by-ear: a HEARTBEAT delivers a grounded forward read, not describe-bank slop; `grounding-review` first |
| 4 | **TRACK_CHANGE-with-next "Option A/B" malformed line** (live bug, friend 0) | `dj_cohost.py` live reaction on TRACK_CHANGE-with-next | the Respan burn caught a malformed multi-option meta-line (friend 0) instead of one clean coaching line (`GOAL-sven.md` thread 5) | the `dj_cohost.py` malformed-output guard + the prompt task that emits the forward read; emit ONE clean coaching line, not an Option-A/Option-B scaffold | sven | by-ear + Respan: `TRACK_CHANGE`-with-next friend score moves off 0; one clean line |
| 5 | **Route-doctor names a stable BlackHole 2ch** (keystone capture safety) | `recommend_auto_master_input` (`scripts/learn_live_readiness.py:1880`); 6 real runs today named 3 different devices | `check_capture_matrix` `top_signal` sort (`:922`) + `silent_48k_loopback_fallback` ranker (`:2018-2022`) sort by `(rms,peak)` only — no `exact_2ch` discriminator -> flips on which time-window each sequential probe sampled | add `1 if name=="blackhole 2ch" else 0` as FIRST sort key at `learn_live_readiness.py:922` AND `:2018-2022` (mirror the already-shipped `_auto_master_candidate_evidence` / `_master_probe_score` 2ch preference). Do NOT touch the morning `a6625caa` fixes | keystone+packaging (engine helper) | by-bus: 3 repeated readiness runs all name `BlackHole 2ch`; parity assert `select_master_input == recommend_auto_master_input.device_name` |
| 6 | **Coach-identity persona as live default + 5 RED agent tests** (ship-blocking, Inv #2) | `matrix.py:432` `HYPE_INTERMEDIATE = SVEN_COACH_IDENTITY` (bench-proven win, +0.79 friend) | the coach-identity swap (`bb708077`) rewrote the anti-slop persona/grounding contract and left 5 guard tests RED (`test_persona_02/03`, `test_intermediate_hype_cell_is_v4_grounded`, two `test_dj_cohost.py` `P1_span`) — CI blocks, Inv #2 uncertifiable while RED | re-pin the 5 tests to the new Sven coach IP (or revert the swap); make the coach identity the live persona with no describe-license (`GOAL-sven.md` thread 2) | sven | Respan: friend/earned/voice climb off 1.2 (target friend>=2, voice>=2) while grounded>=2.4, gate 9/9; tests green |
| 7 | **LAYER_ARRIVAL measured band-jump narrated** (measured-but-discarded) | `event_detector.py:352-355` fires LAYER_ARRIVAL with `extra={"mid_jump","high_jump"}` | `task_for_event` LAYER_ARRIVAL branch (`prompt_builder.py:839-843`) reads NEITHER -> emits a generic "a new layer arrived" task with zero measured fact, inviting the model to guess | read `ev.extra.get("mid_jump")`/`("high_jump")` at `prompt_builder.py:839` and state the band that moved (mirror the genre-chain "the system measured … react to how that FEELS" shape, e.g. `KICK_SWAP` at `:986`). Narrate-only, no forced citation | sven | by-ear: a LAYER_ARRIVAL names the actual band that moved, not a guess |
| 8 | **Vibe Judge dark on master-only rigs** (the one intel engine reaching the brain, ~never fires) | Judge wired in `_run_live_judge` (`runtime/coach.py:364`, fires on TRACK_CHANGE `:937`) | `_supports_grounded_transition_verdict` (`state/deck_context.py:2880`) requires two trusted audio-active decks with per-deck deltas; master-only rig (default, `deck_signal.py:43` `routing_enabled=False`) -> always abstains | FINISH (not pure wire): add a master-only branch to `_supports_grounded_transition_verdict` that infers the executed mix from the single master stream via the landed `eq_move_model` spectral receipt; `signal_frame_from_capture` (`deck_signal.py:22`) populates a single-lane observation instead of `None`. Depends on the keystone EQ model (landed) | sven | by-ear on a captured set: the Judge voices a transition verdict whose `[judge:]` citation resolves; risk_flags surfaced (W11 below) |
| 9 | **Transition-scorer reasons + grade reach the spoken line** (rich verdict only on the pill) | `score_transition_slate` (`intel/transition_scorer.py:154`) full components; `grade_transition` (`intel/move_grade.py:135`) verdict — 20 callers, all pill/library/tests | the live spoken prompt's ONLY transition intelligence is the bare Camelot relation join at `state/prompt_builder.py:493`; the scorer's phrase-alignment/energy-shape and the `lit_aff`/`care`/`mid` grade never speak | in `runtime/coach.py::coach_loop` on a two-deck TRACK_CHANGE/MIX_MOVE (same gate `prompt_builder.py:455` uses), build `TransitionScoringInput` from `state.deck_state.decks[A/B]`, call `score_transition_slate` -> feed top candidate through `grade_transition` -> attach grounded `reasons`/grade as an evidence line in `event_payload` (mirror `move_effect_context` attach at `runtime/coach.py:914-925`), citing the existing `blend[...]`/`[deck:]` atoms so `apply_live_claim_guard` passes | sven | by-ear: a spoken transition verdict ("that 9A->4A blend clicked") whose citation resolves |
| 10 | **events.jsonl symmetry for silent describe-bank events** (debrief under-count) | every `_fire` writes `[ev:TYPE@t]` to the registry; speaking events log to `events.jsonl` at `runtime/coach.py:926` | LAYER_ARRIVAL / SUB_LAYER_ARRIVAL / PHRASE_BOUNDARY are in `_DESCRIBE_BANK_EVENT_TYPES` (`speak_gate.py:30-39`) and never get a payload (W3/W7), so they strip to `describe_bank_only` and never reach `:926` -> debrief timeline under-counts | decide intent per event: if they should speak, fold into W3/W7 payload-attach; if evidence-only, accept as honest dark (debrief still gets the `[ev:…]` registry observation + speak_gate rows at `:826`) | sven | by-bus: debrief timeline reflects detected-but-silent events (or confirmed-intentional dark) |
| 11 | **Judge `risk_flags` (harmonic clash / bass collision) surfaced** | `judge_transition` computes `risk_flags` (`intel/transition_judge.py:71`) + persists to events.jsonl (`:119`) | neither the live voice line (`intel/judge_voice.py::verdict_evidence_line`) nor the debrief critique (`debrief/main.py:217`, components-only) surfaces the named hazard -> "you clashed the keys" coaching moment goes unspoken | in `intel/judge_voice.py::verdict_evidence_line`, when `verdict.risk_flags` non-empty append a fixed clause per flag (`harmonic_clash->"keys clashed"`, `bass_collision->"low-end collided"`) gated on the existing `[judge:]` citation | sven | by-ear: a clash transition speaks the named hazard; `grounding-review` first |
| 12 | **Live beatmatch credit on a real set** (orphaned-beatmatch, the highest-value DJ line) | `learn/runtime.py:_emit_live_beatmatch_grade:2483` writes `[ev:BEATMATCH_GRADED@t]`; `skill_recognizer.py:169-187` credits `beatmatching` from that event | all callers of `_emit_live_beatmatch_grade` are inside `learn/runtime.py`; `grep BEATMATCH_GRADED runtime/coach.py` = 0 -> on a real DJ set the recognizer can never fire; beatmatching uncreditable live | WIRE+BUILD: in `runtime/coach.py::coach_loop` at the TRACK_CHANGE site (`:937`), when two active lanes carry signal, grade the live frame and emit `BEATMATCH_GRADED` into `_credit_live_skill_demo`. Needs a live tempo/phase signal the Judge does not compute (the build); lights only on a deck-routed rig | sven (+ engine for the grid feed) | by-ear on a deck-routed set: an executed beatmatch credits `beatmatching` with a resolving `[ev:BEATMATCH_GRADED@t]` |
| 13 | **Cue-landing reusable engine consolidated** (two parallel spines) | `cue_landing.land()`/`CueSet`/`LandedCue`/`ExportTarget` (`library/cue_landing.py:210`) — callers: tests only; the live Viber auto-cue path goes through `toolset.export_set` inline (`:1002 _auto_cue_marks_for_export`) | the auto-cue capability is LIVE end-to-end (default-on, provenance enforced), but the packet's flagship reusable `land()` verb is orphaned dead code; two spines share `propose_smart_cues`/provenance so they agree today but can silently diverge | route `toolset.export_set` auto-cue through `cue_landing.land()`: replace the hand-rolled `propose->marks` in `_auto_cue_marks_for_export` (`toolset.py:2124`) with `cue_landing.cue_set_from_proposal(...)`, and at the carrier seam `toolset.py:1044` call `cue_landing.land(cueset, ExportTarget.rekordbox_xml(path), granted=True)`. Owner-gate: consolidate vs leave tested-but-unused | library | by-bus: `library build-set --cue --export rekordbox` -> re-parsed XML shows `VM `-named marks in empty slots + DJ cues byte-preserved + zero DB writes |
| 14 | **Learn mastered->cue routes through `land()`** (deferred 1-line re-point) | `learn/mastered_marker_writer.write_mastered_marker:207` is LIVE-wired (`__main__.py:3194` callback), writes Serato tags via `write_serato_cues` directly | bypasses `cue_landing.land()` so it does not inherit the consent/receipt contract (packet "later 1-line re-point") | re-point `write_mastered_marker` at `cue_landing.land()` (after W13 consolidation) so the mastered marker inherits the provenance/consent receipt | library | by-bus: a mastered marker lands via the same `land()` path with a provenance stamp |
| 15 | **macOS screen-watch covers Rekordbox/Serato/Traktor** (honesty: README claims app-agnostic) | `_screen_macos.py:470` `_find_djay_window_bounds("djay")`; banner `:465` "djay-only crop" | mac `ScreenMacOS` has no `find_dj_window` method (Windows does); on Mac the vision layer is DARK for every non-djay DJ app while README claims "app-agnostic" / names Rekordbox | add `_DJ_HINTS` tuple + `find_dj_window` method to `_screen_macos.py` (mirror `_screen_windows.py:64/191`); wire `_screen_macos.py:470` `_find_djay_window_bounds("djay")` -> `self.find_dj_window()`; fix banner `:465`. `_find_djay_window_bounds` is already generic | engine | by-ear/by-bus on a non-djay DJ window open: a `screen`-cited reaction fires |
| 16 | **Honest controller count + S2-MK3 HID** (catalog = 11, not 10; NI coverage dark) | 11 JSON profiles in `midi/profiles/` (docs say 10, undercount); S2-MK3 HID bridge (`platform/_hid_macos.py:319`) tested, zero callers | docs/README undercount as 10 and imply "supported" = verified; the HID bridge emits decoded `MidiEvent`s but `ControllerState` only ingests raw mido via `handle_msg` (`midi/state.py:309`) — no public seam to push a `MidiEvent` | (a) doc/copy: fix 10->11 + verified/mapped split in `docs/midi-controllers.md`, `README.md:177`, `docs/midi-mapping.md:3`; (b) POST-SHIP: add `ControllerState.apply_event(ev: MidiEvent)` public ingest seam (`midi/state.py`), then guard-wire `start_s2_mk3_listener(on_event=...apply_event)` at `__main__.py:2091` behind `list_s2_mk3_devices()`, add `hid` to specs | engine | (a) docs match reality; (b) by-ear on an S2-MK3: a `midi`-cited reaction on a transport press |
| 17 | **Voice/audio model literals gated against drift** (governance) | `chatterbox_tts.py:40`, `local_tts.py:62`, `library/model_assets.py:27`, `library/cue_detr.py` carry hardcoded model IDs | the CI grep gate (`scripts/release/check_no_hardcoded_model.sh`) only matches `gemini-*`, so voice/audio model literals pass green forever; the Gemini-only router is correctly NOT the home for them (3 tests pin Gemini-only) | extend the gate + `tests/repo/test_model_literal_gate.py` with a voice/audio pattern (`chatterbox|MOSS-TTS-Nano|larger_clap_music_and_speech|cuedetr`) + a 4-file allowlist. Do NOT force these into the Gemini router (breaks `test_no_non_gemini_models`) | keystone+packaging | by-bus: the gate fails if a voice-model literal drifts to a 5th file |

### Confirmed CLEAR / by-design dark — NOT findings, do not "fix"

- **Learn fused-beatmatch loop** (grade emit, audibility, A1 guard, MOSS tutor voice, live HUD/waveform/playhead
  IPC) is WIRED end-to-end at HEAD; the 06-03 LEARN-UX-REALITY diagnosis is STALE (a 14-commit landing fixed it,
  LIVE-proven `CODEX_VERDICT-LEARN-FUSED-BEATMATCH-LIVE-PROOF.md`). The real residual is content-shallow lessons
  (36/37 act on silence) + passive-skip crediting at full weight — content/registration, not a missing wire.
- **S9 memory/recall, debrief->profile, taste->persona** are all WIRED end-to-end and citation/consent-grounded;
  the only "dark" is 3 default-OFF opt-in flags (`VIBEMIX_RECALL_ENABLED`, profile-consent, taste) — owner
  ear-pass decisions, NOT engineering wires. `MemoryStore` direct construction is dead-but-harmless (same gating).
- **Gemini brain routing** is fully clean via `model_router`; debrief/learn-tutor/embedding routes all resolve.
- **DROP / KEY_CLASH / TRANSITION_OPPORTUNITY** dark-by-design: DROP has an env opt-in (`VIBEMIX_DROP_CALL`);
  KEY_CLASH/TRANSITION_OPPORTUNITY need the Plan 60-03 Kaan-ear veto. KEY_CLASH's missing env reader
  (`EventDetector(harmonic_clash_enabled=...)` never set at `__main__.py:1462`) is the one note — even Kaan can't
  flip it without a code change, unlike DROP. Low priority.
- **Proxy register->JWT->Gemini chain** resolves end-to-end and is LIVE-wired; keyless brain is DEAD only because
  the Bravoh key is at 429 (out of credits) — external/Kaan-Bravoh-ops, NOT a code wire.

---

## Paste-ready /goal blocks per lane

> **SHARED LAW (every lane obeys, verbatim):** ONE working tree, 2+ concurrent sessions — `git add` your EXACT
> paths, NEVER `git add -A` (verify `git diff --cached --name-only` matches your intended set before every
> commit). The IPC schema (`tauri/ui/src/ipc/messages.schema.json`) is FRONTEND-lane-owned — backend lanes
> implement the named Python handler half, never edit the schema. ONE socket: `127.0.0.1:8765`, one listener;
> `pkill -f "python -m vibemix"` before relaunch. Commits `-s`, identity `Kaan Ozkan <rahipdotaci@gmail.com>`,
> end the message with the Co-Authored-By trailer. Do NOT rush to exit at test-green — `test-passing-but-dark =
> 0`: prove BY EAR in the real app (`drive-vibemix` / `VIBEMIX_DEV_SIDECAR=1`), run `vibemix-grounding-review` on
> EVERY new co-host line before it ships, and commit each piece the instant it is green + proven, not in a batch.

### Lane: sven (the live Gemini reaction brain)

```
/goal SVEN VOICE EXIT — take the co-host from grounded-narrating to grounded-coaching, from
.planning/packets/2026-06-04/BACKEND-WIRING-EXIT-MAP.md + GOAL-sven.md. Pin a SHA first (~86a3527f).
ISLAND: src/vibemix/prompts/ (matrix.py persona), src/vibemix/state/{prompt_builder.py,event_detector.py},
src/vibemix/runtime/{coach.py,speak_gate.py,suggestion_voice.py,set_plan_voice.py}, src/vibemix/agent/dj_cohost.py,
src/vibemix/intel/{judge_voice.py,transition_scorer.py,move_grade.py}, scripts/eval/. The validator is the Respan
eval number, NOT green tests. In order:
(3) HEARTBEAT grounded receipt — add "HEARTBEAT" to the payload-attach tuple at runtime/coach.py:765 + to
    _VOICE_EVENT_TYPES in suggestion_voice.py:20 + set_plan_voice.py:21 (NOT transition_verdict_voice). By-ear: a
    HEARTBEAT delivers a grounded forward read, not describe-bank.
(4) Fix the TRACK_CHANGE-with-next "Option A/B" malformed line in dj_cohost.py — one clean coaching line; Respan
    friend off 0.
(6) Make HYPE_INTERMEDIATE=SVEN_COACH_IDENTITY the live persona; re-pin the 5 RED agent tests to the new coach IP.
    Respan friend/earned/voice off 1.2 (target >=2) while grounded>=2.4, gate 9/9.
(7) LAYER_ARRIVAL — read ev.extra mid_jump/high_jump at prompt_builder.py:839, name the band that moved.
(8) FINISH the Vibe Judge master-only branch in deck_context.py:_supports_grounded_transition_verdict +
    deck_signal.py single-lane observation, inferring the mix from the eq_move_model spectral receipt.
(9) Feed score_transition_slate reasons + grade_transition verdict into the spoken line via the coach_loop
    move_effect_context attach pattern (runtime/coach.py:914-925), cited on existing blend[...]/[deck:] atoms.
(11) Surface Judge risk_flags in judge_voice.verdict_evidence_line gated on [judge:].
(12) WIRE+BUILD the live beatmatch credit: emit BEATMATCH_GRADED from coach_loop at the TRACK_CHANGE site into
    _credit_live_skill_demo (needs the live tempo/phase signal — coordinate the grid feed with the engine lane).
PROOF: run scripts/eval/respan_sven_sim.py + respan_sven_heartbeat_judge.py and show the dim numbers moved;
vibemix-grounding-review on every change to what/when the co-host speaks; drive-vibemix by-ear on a real set.
SHARED LAW applies (see header).
```

### Lane: learn

```
/goal LEARN EXIT — the fused-beatmatch loop is WIRED at HEAD (06-03 diagnosis is STALE), so do NOT re-wire it.
From BACKEND-WIRING-EXIT-MAP.md + GOAL-learn.md + LEARN-PLAYABILITY-TEARDOWN.md. Pin a SHA first.
ISLAND: src/vibemix/learn/{runtime.py, miniplayer.py, beatmatch_practice_driver.py, ipc_handlers.py},
src/vibemix/audio/waveform_peaks.py (new). The real residual is content + reach, not dead wires:
- Widen the audible-practice lesson gate (beatmatch_practice_driver.py _PRACTICE_LESSONS) to the Course-1/2
  control lessons that touch a deck, keeping TwoDeckPlayer.can_play() + the A1 guard (practice audio NEVER over a
  live set). Today only ~4 of 38 lessons make sound.
- Author the missing exemplar_cycle fixtures so the 36 silent control lessons demonstrate over real audio
  (Stages 3/4 of the 5-stage loop), templating the L2.01 pattern.
- Fix passive-skip crediting: on_enter_completed credits at full WEIGHT_FIRST_TRY even on a 45s skip
  (runtime.py:1224 + skill_tree.py:254) — persist a demonstrated flag, record skip at floor weight.
PROOF: PYTHONPATH=src python3 -m pytest -q (learn+intel); drive-vibemix BY EAR — a beginner on a control lesson
HEARS the demonstrated move, and a skip does not credit mastery. Kill criterion: a control lesson still acts on
silence. test-passing-but-dark=0. SHARED LAW applies (see header).
```

### Lane: library (Viber / cue / embeddings)

```
/goal LIBRARY EXIT — consolidate the cue-landing spines + close the deferred re-points, from
BACKEND-WIRING-EXIT-MAP.md + CUE-LAND-ENGINE.md. Pin a SHA first. The Viber auto-cue path is LIVE end-to-end
(default-on, provenance enforced) — do NOT re-build it; the gap is a duplicate spine + an orphaned reusable engine.
ISLAND: src/vibemix/library/{cue_landing.py, toolset.py, cue_provenance.py}, src/vibemix/learn/mastered_marker_writer.py.
(13) Route toolset.export_set auto-cue through cue_landing.land(): replace the hand-rolled propose->marks in
    _auto_cue_marks_for_export (toolset.py:2124) with cue_landing.cue_set_from_proposal(...), and at the carrier
    seam toolset.py:1044 call cue_landing.land(cueset, ExportTarget.rekordbox_xml(path), granted=True). ONE
    permissioned landing verb. Owner-gate: confirm consolidate vs leave land() tested-but-unused.
(14) Re-point learn/mastered_marker_writer.write_mastered_marker (write_serato_cues) at cue_landing.land() so the
    mastered marker inherits the consent/receipt.
PROOF: library build-set "..." --cue --export rekordbox -> re-parse the XML: VM-named marks fill empty slots, DJ
cues byte-preserved, zero DB writes (by-bus). PYTHONPATH=src python3 -m pytest tests/library/test_cue_landing.py
tests/repo/test_no_seen_relaxation.py -q. NOTE the Cue Tray UI is FRONTEND-lane (a Tauri invoke library_land_cues
+ a NEW Python CLI verb that emits the CueSet JSON) — coordinate that handshake, do not build the UI here.
SHARED LAW applies (see header).
```

### Lane: keystone + packaging (the engine-reachability, brain-persist, ship gates)

```
/goal KEYSTONE+PACKAGING EXIT — make the chosen voice + the brain reachable from a normal launch, and stabilize
the keystone-capture device, from BACKEND-WIRING-EXIT-MAP.md + SHIP-READINESS-2026-06-04.md +
CODEX_READY-CHATTERBOX-VOICE-WIRED.md. Pin a SHA first.
ISLAND: src/vibemix/runtime/{config_store.py, session_loop.py, settings.py}, src/vibemix/__main__.py,
scripts/learn_live_readiness.py, scripts/release/check_no_hardcoded_model.sh, tests/repo/test_model_literal_gate.py,
the PyInstaller specs.
(1) tts_engine reachable: add tts_engine="moss" to config_store.py (dataclass ~:194 + _PHASE12_FIELDS:68 +
    from_dict coerce ~:228); add os.environ.setdefault("VIBEMIX_TTS_ENGINE", cfg.tts_engine) at __main__.py:1420
    (mirror _apply_deck_audio_config_to_env:1060). No tts_chain.py edit. By-ear: config.json engine -> restart ->
    cloned voice (Chatterbox on Mac, MOSS floor otherwise).
(2) Brain persist handler: register ipc.settings.set_brain in session_loop.py:~270 -> NEW _on_settings_set_brain:
    persist ConfigStore.llm_mode via save_config, write GEMINI_API_KEY to app_data_dir()/.env (chmod 600, NEVER
    log), emit SettingsBrainAck.make(...) (ui_bus/messages.py:1044). The IPC schema + the settings-drawer UI are
    FRONTEND-lane — implement the Python handler half only.
(5) Route-doctor stability: add `1 if name=="blackhole 2ch" else 0` as the FIRST sort key at
    learn_live_readiness.py:922 AND :2018-2022. Do NOT touch the morning a6625caa fixes. By-bus: 3 repeated runs
    all name BlackHole 2ch + parity with select_master_input.
(17) Extend check_no_hardcoded_model.sh + test_model_literal_gate.py with a voice/audio model pattern +
    4-file allowlist; do NOT force voice IDs into the Gemini router (breaks test_no_non_gemini_models).
PROOF: by-ear on the real app for (1)+(2); by-bus for (5)+(17). After landing, the keystone+packaging follow-on
(commit dirty src, rebuild sidecar + DMG at HEAD, re-sign) is gated on the RED-test resolution in the sven lane.
SHARED LAW applies (see header).
```

---

## NEEDS-CLARIFICATION

1. **Voice default-engine call (Kaan).** Keep `tts_engine` default `"moss"` (proven never-mute floor) for the
   shipped artifact, or flip the packaged default to `"chatterbox"`? The flip is inert until two owner calls land
   (both in SHIP-READINESS owner-gates): (a) add `mlx-audio` as a `pyproject.toml` extra — it is Apple-only and
   reintroduces `transformers` 5.x into a tree CLAUDE.md calls "torch-free, Transformers-free, librosa-free"; and
   (b) bundle the ~675MB `chatterbox-turbo-8bit` model + the music-stripped YouTube-vocal ref clip (a licensing
   decision). Default `"moss"` with config-driven opt-in is the safe wire either way; the default-flip is the
   open call.

2. **Cue-landing consolidation (Kaan/owner).** Route the live Viber auto-cue export through the reusable
   `cue_landing.land()` engine (W13) — worth the consolidation to retire the duplicate spine — or leave
   `cue_landing.py` as a tested-but-unused library and accept two spines that agree today via shared
   `propose_smart_cues`/provenance? The user-facing auto-cue is LIVE either way; this is an architecture/anti-drift
   call, not a dark-feature call.

3. **Streak grounding scope (Kaan, gates the robot voice).** V3 re-binds the streak to a cited executed
   transition, which requires a live `[ev:BEATMATCH_GRADED@…]`/`[judge:]` event that does not exist on a
   master-only rig today (practice/recorder only) — this is L-effort plumbing (debrief-first, separate surface per
   Kaan's "live'dan ayrı" call). Confirm: is the robot streak voice (V2) in scope NOW behind this plumbing, or
   deferred until a deck-routed judge event exists? Wiring V2 to the current self-applauding streak is out of
   scope by the FAFO verdict — do not ship the robot voice on the present signal.
