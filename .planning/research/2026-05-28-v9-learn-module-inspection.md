# v9.0 Learn Module Inspection

Date: 2026-05-28

Scope: source-level inspection of the v9.0 "Lesson One" beginner DJ teaching
module, plus focused local tests/build checks. This is not a real-hardware ear
pass.

Update after first rebuild slice: the original inspection below remains the
honest critique of the inherited module. A first implementation slice now fixes
the Learn entrypoint, canonical lesson IDs, practice-booth first paint, virtual
deck fallback, screen-control acknowledgements, observer lesson integration, and
several deterministic verification bugs. A second slice adds a canonical
structured-flow compiler so all 36 beginner lessons expose practice steps,
observable controls, deterministic verification specs, and adaptive hints. The
third slice wires those structured flows back into `LessonRuntime`, fixes the
non-continue lesson prompt bug (the learner now sees the actual action prompt
before verification), adds an on-screen deck ack path under UI test, gives
exemplar-backed lessons a visible "example playing" state, and makes Learn
window mounts disposable so tests/HMR do not accumulate stale global listeners.
A fourth slice adds deterministic adaptive coaching for wrong actions instead
of silent guard failures. A fifth slice makes progress/unlocks real at the
frontstage and backstage boundary: the chooser now shows locked later courses,
the recommended button follows persisted progress snapshots, reset clears course
unlock flags, and `start_lesson`/`start_course` reject locked course jumps even
if the UI is stale or forged. A sixth slice pins the app-boot observer wiring
for exemplar/recital lessons, closes the biggest screen-deck control gaps
(`jog` aliasing, missing-control fallback, one-shot pulse ACKs), and makes the
Learn-only Ruff pass clean. A seventh slice adds a frontend beginner-path
contract from main-app LEARN selection through first lesson action ACK and the
next recommendation. An eighth slice turns two a11y stubs into live tests:
tutor speech now writes the shared SR region, hint speech raises it to assertive,
and the 45-second skip lockout has deterministic aria/tooltip/silent-unlock
coverage. A ninth slice wires HUD progress dots for keyboard replay/no-op/
prerequisite behavior. A tenth slice makes the "i got it" skip button explicitly
keyboard-activatable after the dwell floor and covered before/after lockout. The
eleventh slice converts the remaining SR reconnect and controller focus-order
stubs into live tests. A twelfth slice wires the Course 3 `session_active` lens
toggle through `state_refresh_loop`, keeping MusicState as the single writer and
leaving phrase prediction cold until a real cue/phrase source exists. A
thirteenth slice pins the first beginner lesson through the Python sidecar
dispatch path: `start_lesson`, authored continue ACKs, runtime completion,
terminal envelopes, and persisted progress. A fourteenth slice makes the
non-observable physical controls honest: `headphone_cue`, `master_vol`, and
`lesson_continue` compile as screen-only verification surfaces, the contract is
grounded against the bundled MIDI profiles, and the Learn UI now tests both
screen fallbacks. A fifteenth slice pins the EQ-as-tutor damaged-install
degraded path against the real `ExemplarFinder`: absent packaged assets now
prove no fake `exemplar_play`, no fabricated citation, no player call, and an
honest null tutor line. A sixteenth slice makes Course 3 retrospective-only
until a trusted cue/phrase source exists: `state_refresh_loop` now clears stale
`phrase_position_confidence` and `next_phrase_at` every tick, even while the
live Course 3 lens is active. The full 36-lesson perfection bar is still not
complete. A seventeenth slice converts the contrast placeholders into live
token-level WCAG tests, fixes cue highlights so `data-cue-color` actually maps
to visible CSS color, pins amber/warning highlight contrast, and removes fluid
viewport-scaled type from the tutor's main prompt line. An eighteenth slice adds
a Playwright Learn webview contrast pass that loads `learn.html` in Chromium and
checks computed browser styles for the tutor dock plus amber/warning cue
highlights. A nineteenth slice adds a real WebSocket bus beginner-path test:
`ipc.learn.start_lesson` and `ipc.learn.ack` travel over `ws_broadcast` on an
ephemeral port, complete `L1.01`, emit terminal Learn envelopes, and persist
progress. A twentieth slice joins the real browser Learn page to that Python
runtime harness: Playwright loads `learn.html`, the Tauri invoke shim forwards
`forward_ipc_to_sidecar` into the test `ws_broadcast` server, the UI clicks
through `L1.01`, receives real runtime envelopes, advances the recommendation
to `L1.02`, and verifies the persisted progress file. A twenty-first slice
removes a production bridge shortcut: the Learn client now consumes inbound
lesson events through the established Tauri/Rust event bridge when the event
plugin is present, keeps direct `ws:8765` only as a browser/dev fallback, and
pins the Rust `ipc.learn.*` event-name mapping plus outbound JSON serialization
with unit tests. It also adds `ipc.learn.midi_position` to the IPC client's
high-frequency log throttle so the bridge path does not spam the UI log at MIDI
mirror rates. A twenty-second slice adds a dependency-free Playwright browser
accessibility pass for Learn: visible button names, duplicate IDs, rendered SVG
control semantics, and focus targets under `aria-hidden`. A twenty-third slice
replaces the empty EQ exemplar scaffold with a packaged, self-authored WAV bank:
four deterministic band examples (`sub`, `low`, `mid`, `high`) now ship with a
pinned manifest, NOTICE attribution, real finder fallback, decode/hash tests,
and wheel-packaging proof. A twenty-fourth slice fixes a frontstage feel gap:
faders no longer freeze at static `data-value` markers. The renderer now infers
rail/thumb geometry from the SVG and translates the visible thumb while keeping
the parent control group stable for highlight and focus; browser Playwright now
asserts the motion on `learn.html`. A twenty-fifth slice fixes the live HUD dot
pipeline: `LearnProgress.dots_for_course` now emits the full current course
strip with completed/current/pending statuses, `LessonRuntime` passes the active
lesson id into that projection, and the HUD maps canonical Course 1-3 ids
instead of falling back to raw identifiers. A twenty-sixth slice deepens the
deterministic adaptive teaching loop: guard-rejected actions now distinguish
wrong control, wrong deck, tiny CC movement, wrong button direction, and
colon-vs-split deck IDs, then emit short grounded hints with `midi`/`screen`
citations instead of anonymous advice. A twenty-seventh slice fixes a real
WebSocket-bus shutdown race surfaced by the broader Learn suite: all shared
broadcast loops now iterate snapshots of the connected-client set, so a
disconnect during mascot/session/status/Learn traffic cannot mutate the set
mid-iteration and crash the beginner-path WebSocket harness. A twenty-eighth
slice wires timed hint strikes into persisted lesson progress: `strikes_used`
now reflects the runtime's actual strike count on completion, giving future
debrief/profile adaptation a real signal instead of a permanent zero. A
twenty-ninth slice grounds ordinary Learn practice actions in the shared
`EvidenceRegistry`: lesson highlights, matching learner actions, and adaptive
mismatch hints are recorded with session time, and MIDI hint citations now use
the linter-compatible `[midi:<control>@<t>]` grammar instead of UI-only citation
strings. A thirtieth slice pins the static Tauri Learn launch contract: the
Rust command remains registered, the Learn window loads `learn.html`, and the
Tauri capability scope includes the `learn` window label. This does not replace
a launched-process e2e, but it closes another quiet wiring-regression hole. A
thirty-first slice polishes the tutor citation chip for the new evidence
grammar: time-keyed MIDI citations display as learner-facing control labels
(`MIDI DECK A HIGH EQ`) rather than raw registry tokens. A thirty-second slice
strengthens the Rust bridge proof: the `forward_ipc_to_sidecar` send loop now
runs through a testable helper, and a Rust async test parks a real WebSocket
sink after a delay, forwards an `ipc.learn.ack`, and verifies a local WebSocket
server receives the exact JSON frame. A thirty-third slice hardens the
36-lesson curriculum contract: all beginner step IDs are unique, the first
three authored hint strikes carry real text/TTS markers, and the TypeScript
chooser metadata is pinned byte-for-byte against the Python curriculum IDs,
course IDs, and titles. A thirty-fourth slice makes started-but-unfinished
lessons visible without making the frontstage busier: the runtime marks an
incomplete progress row on lesson load, updates `strikes_used` when timed hints
fire, and the chooser now treats `completed: false` rows as in-progress and
recommends resuming them first. A later replay/resume hardening slice made those
start and hint rows durable via atomic `save_progress`, with pytest isolation so
ordinary test runs do not churn the user's real persisted progress file. A
thirty-fifth slice makes the backstage teaching loop explicit:
`teaching_loop.py` now
produces pure observe -> decide -> teach -> verify -> adapt turn records,
resolves the tutor route through `model_router` using `learn_tutor`, carries
structured-step verification metadata, and is used by runtime step, timed-hint,
and adaptive-hint emits. It still does not improvise lesson copy at runtime;
the loop records the intelligence contract while authored fixtures remain the
frontstage voice. A thirty-sixth slice threads the existing library cue/section
intelligence into the Course 3 live lens: `state_refresh_loop` can now resolve
the audible deck's Rekordbox track, inspect DJ-authored cue sections, register a
stable change-only `cue` evidence anchor, and open forward count-ins only when
BPM, deck, playhead, and cue confidence all clear the existing floors. Fallback
section maps remain cold so the tutor cannot turn library guesses into
proactive phrase calls. A thirty-seventh slice removes a product-overclaim from
L3.02: until the runtime actually loads a set-prep pool, the lesson no longer
claims that vibemix already loaded five tracks. It now asks the user to bring a
prepared pool from build-a-set or their own queue. A thirty-eighth slice wires
that honesty to a real backstage capability: Learn can read the latest neutral
playlist JSON artifact, ignore corrupt or undersized files, and in L3.02 emit a
short deterministic "latest saved pool" line naming the first two tracks. It
cites the first track only when the shared `EvidenceRegistry` already resolves
the `[track:]` atom. A thirty-ninth slice feeds that same saved pool into the
existing `SuggestionService`: when the audible track is in the pool, the next
row becomes a soft prepared target for the "what's next" engine. The pool reader
lives under `vibemix.library` because it is a saved playlist artifact, while
Learn keeps a compatibility wrapper. Deck-loaded targets remain strict; pool
targets win only with grounded transition evidence and use "next in saved pool"
copy instead of the target-deck label. A fortieth slice adds the first launched
desktop Learn smoke that works on macOS without `tauri-driver`: an opt-in Rust
e2e hook can skip the live-audio sidecar supervisor, open the real Learn
WebviewWindow, inject a tiny script that clicks the production practice-booth
buttons, route those clicks through Rust `forward_ipc_to_sidecar`, and verify
the Python Learn runtime persisted `L1.01` completion on the shared `:8765`
bus. A forty-first slice turns that launched smoke into a frontend quality
proof: the WebviewWindow now inspects its own DOM for duplicate IDs, unnamed
visible buttons, focusable controls under `aria-hidden`, keyboardable SVG
controls, opt-in lesson-map visibility, calm booth button count, tutor text
contrast, and screen-action text fit, then reports a JSON artifact through a
guarded Rust command. A forty-second slice adds axe-core instead of hand-waving
accessibility: the launched smoke injects the local `axe.min.js` into the real
Learn WebviewWindow, filters critical/serious WCAG violations, and the browser
Playwright Learn suite runs the same axe gate. That gate found a real
`nested-interactive` defect in the controller SVG semantics; the root SVGs are
now neutral stages while their child control groups own the interactive roles.
This is not a real-hardware ear pass, but it proves the launched Tauri
window/bridge path with a sidecar runtime, real frontstage quality assertions,
and an automated axe-core accessibility audit. A forty-third slice adds the
first Course 3 live-set rehearsal contract: one deterministic mini set now
joins cue-anchored count-in evidence, the coach's forward-count-in eligibility
marker, saved-pool "next prepared track" targeting, and graceful off-pool
deviation feedback. It still does not replace an actual controller/audio set
pass, but it proves those backstage seams work together rather than only in
isolated tests. A forty-fourth slice starts the real hardware pass honestly:
macOS exposes `DDJ-FLX4` as a MIDI input, CoreAudio sees the FLX4 plus
BlackHole devices at 48 kHz, and the opt-in live MIDI profile smoke now
enumerates ports in a subprocess so `python-rtmidi` cannot abort the pytest
runner. The FLX4 resolves to `pioneer_ddj_flx4`, but two raw sniff windows
captured zero control frames, so physical movement decode and the ear-pass are
still not proven. A forty-fifth slice fixes the opt-in full live startup smoke:
the test now checks the production app-data recordings root instead of a stale
repo-local `recordings/` path, stale `xfail` wrappers were removed from the
live MIDI and live startup tests, and `VIBEMIX_LIVE_SMOKE=1` now starts
`python -m vibemix`, keeps it alive for the smoke window, shuts it down cleanly,
and observes a new app-data recording session. A forty-sixth slice hardens
replay/resume behavior: lesson start and timed hint strikes now persist
atomically instead of staying process-local, Learn tests isolate progress writes
to temp files, completed lessons remain replayable even if their course gate is
otherwise locked, and the practice map emits `level: "replay"` for those
completed rows while keeping untouched later lessons locked. A forty-seventh
slice fixes a real Rekordbox-open live-start failure: MacBook speakers were at
44.1 kHz while vibemix expected 48 kHz for the silent passthrough output, so
`python -m vibemix` exited before the hardware smoke window. The macOS
passthrough output now opens at the selected output device's native rate and
resamples the monitor path when needed; BlackHole capture and mic capture keep
their strict sample-rate guards. A forty-eighth slice turns the last FLX4 jog
proof into a repeatable opt-in live test:
`tests/learn/test_live_flx4_learn_jog.py` opens the real FLX4 callback sniffer
in a subprocess, waits for a left-jog CC33 frame, then feeds that real byte
shape through `ControllerState`, `MidiMirror`, the Learn IPC handler, and the
L1.07 verifier. A forty-ninth slice tightens the optional lesson map as a real
practice-booth drawer instead of a visual-only overlay: opening it now moves
focus to the recommended playable lesson, Escape closes it, close returns focus
to the chooser button, and the map still stays hidden by default behind the
one-action booth.
A fiftieth slice sharpens the screen-only fallback from generic chrome into
actionable coaching copy: the Learn fallback button now names the exact action
(`press deck A headphone cue`, `move master volume`) instead of saying "do it
on screen", and the button wraps within a bounded width on small screens.
A fifty-first slice makes Course 3's calm frontstage honest in the structured
flow contract: every compiled step now carries `backstage_lenses`, and the live
Course 3 lessons expose their real backstage dependencies (`live_audio`,
`cue_section_lookahead`, `library_suggestions`, `session_state`,
`prepared_pool`, `session_recording`, `debrief`, `dj_profile`, and recovery
drill shapes). The teaching-loop observation carries those lenses too, so a
future tutor or UI pass cannot mistake L3.01-L3.06 for empty continue-button
slides. Focused proof: `uv run ruff check src/vibemix/learn/lesson_flow.py
src/vibemix/learn/teaching_loop.py src/vibemix/learn/__init__.py
tests/learn/test_lesson_flow_contract.py tests/learn/test_teaching_loop.py`
and `uv run pytest -q tests/learn/test_lesson_flow_contract.py
tests/learn/test_teaching_loop.py` both pass. Hardware context: `uv run python
scripts/sniff_controller.py --list` currently sees `DDJ-FLX4`, so the MIDI port
is visible, but this is still not the same as a physical jog/control decode or
audio ear pass.
A fifty-second slice fixes the Learn highlight paint budget instead of
tolerating timing drift: `applyHighlight` now clears the cached active control
and reuses resolved SVG control groups with stale-node guards after controller
remounts. This preserves the single-active highlight invariant while removing a
hot-path `querySelectorAll` scan on every tutor highlight. Focused proof:
`npm --prefix tauri/ui test -- --run tests/learn/highlight-paint.test.ts`
reports about 3.4 ms P95 in isolation, and the full Learn Vitest suite reports
about 1.0 ms P95 with all 143 Learn tests passing. `npm --prefix tauri/ui run
build` also passes.
A fifty-third slice hardens the browser/Tauri outbound fallback proof. The
shared Tauri runtime wrapper now rejects immediately in plain browser contexts
instead of waiting for `@tauri-apps/api` to discover missing internals, so Learn
can fall back to its direct `ws:8765` path without a dead-air click. The
Playwright sidecar harness now records outbound Learn frames and routes the
Tauri-style `forward_ipc_to_sidecar` shim through the same open Learn socket,
matching the one-socket invariant more closely than the earlier two-socket test
double. The browser beginner-path test now proves every continue click emits an
`ipc.learn.ack` before expecting the next tutor beat. Focused proof:
`npm --prefix tauri/ui run test:e2e:learn` passes 9/9 after the change, and
`npm --prefix tauri/ui run build` passes.
A fifty-fourth slice turns the remaining FLX4 L1.07 live discharge from an
opaque pytest incantation into a focused integration probe:
`scripts/live_learn_jog_probe.py` prompts for a left-jog nudge, captures the
real FLX4 CC33 frame, and feeds that exact byte through `ControllerState`,
`MidiMirror`, the Learn IPC ACK handler, and the L1.07 verifier before printing
a JSON proof summary. The opt-in pytest remains available, but the next live
session now has a direct "move this now" command. Focused proof:
`uv run ruff check scripts/live_learn_jog_probe.py
tests/learn/test_live_learn_jog_probe.py`, `uv run pytest -q
tests/learn/test_live_learn_jog_probe.py
tests/learn/test_physical_controller_pipeline.py
tests/midi/test_sniff_controller.py`, and `uv run python
scripts/live_learn_jog_probe.py --help` all pass.
A fifty-fifth slice moves the same physical L1.07 proof one layer closer to
production integration: `scripts/live_learn_socket_jog_probe.py` connects to
the established `ws://127.0.0.1:8765` sidecar socket, sends
`ipc.learn.start_lesson` for L1.07, waits for a real sidecar
`ipc.learn.midi_position` frame with `jog:A == 127`, sends the UI-shaped
`ipc.learn.ack`, and waits for `ipc.learn.advance`. Its contract test starts a
real `ws_broadcast` server with a real FLX4 `ControllerState`/`MidiMirror`,
injects the live-discovered CC33 jog byte, and proves the socket path advances
the lesson. Focused proof: `uv run ruff check
scripts/live_learn_socket_jog_probe.py
tests/learn/test_live_learn_socket_jog_probe.py`, `uv run pytest -q
tests/learn/test_live_learn_socket_jog_probe.py
tests/learn/test_live_learn_jog_probe.py
tests/learn/test_physical_controller_pipeline.py
tests/learn/test_ws_beginner_path.py`, and `uv run python
scripts/live_learn_socket_jog_probe.py --help` all pass. The broader
`uv run pytest -q tests/learn -rs` run now reports 375 passed and 1 skipped,
with the skip still being the deliberate opt-in live FLX4 jog proof.
A fifty-sixth slice turns the packaged EQ loop ear-pass from a vague manual
todo into a repeatable audition surface: `scripts/audition_learn_exemplars.py`
audits the four bundled band loops against the manifest, reports duration,
stereo channels, peak/RMS dBFS, clipping count, and hash-match status, and can
play the loops through the same dedicated `ExemplarPlayer` seam with
`--play --device-index <n>`. The default JSON audit proves all four files
decode, match their manifest hashes, and have zero clipped samples, while still
leaving `human_ear_pass: null` so the docs do not overclaim sonic approval.
Focused proof: `uv run ruff check scripts/audition_learn_exemplars.py
tests/learn/test_exemplar_audition.py`, `uv run pytest -q
tests/learn/test_exemplar_audition.py
tests/learn/test_exemplar_packaged_fallback.py
tests/learn/test_exemplar_player.py`, `uv run python
scripts/audition_learn_exemplars.py`, and `uv run python
scripts/audition_learn_exemplars.py --help` all pass. The broader
`uv run pytest -q tests/learn -rs` run now reports 378 passed and 1 skipped.
A fifty-seventh slice makes Course 3 live proof observable on the existing
socket instead of requiring process-memory inspection: the flat 30 Hz
`ws://127.0.0.1:8765` frame now carries `course3_lens` with honest cold
defaults (`session_active`, `phrase_position_confidence`, `next_phrase_at`,
`next_phrase_cue_id`). This is a read-only serialize edge from `MusicState`;
`state_refresh_loop` remains the single writer. `scripts/live_course3_lens_probe.py`
watches the same socket and can require active Course 3 plus citable next-phrase
cue evidence before passing. Focused proof: `uv run ruff check
src/vibemix/runtime/ws_bus.py scripts/live_course3_lens_probe.py
tests/runtime/test_ws_bus_course3_lens.py
tests/runtime/test_live_course3_lens_probe.py`, `uv run pytest -q
tests/runtime/test_ws_bus_course3_lens.py
tests/runtime/test_live_course3_lens_probe.py
tests/runtime/test_ws_bus_deck_state.py
tests/runtime/test_ws_bus_empty_frames.py tests/state/test_refresh.py
tests/state/test_coach_course3_confidence_gate.py`, and `uv run python
scripts/live_course3_lens_probe.py --help` all pass.
A fifty-eighth slice closes the broadest offline runtime-proof gap:
`tests/learn/test_all_lessons_runtime_path.py` now starts every one of the 36
beginner lessons through the shipped Learn IPC handler, sends each lesson's
canonical ACK action shape, drives the real observer controllers for L1.14
EQ exemplars and L1.16/L2.14 recitals, forces the normal finish edge when the
synchronous test path parks in `advancing`, and reloads the persisted progress
row for each lesson. Focused proof: `uv run ruff check
tests/learn/test_all_lessons_runtime_path.py`, `uv run pytest -q
tests/learn/test_all_lessons_runtime_path.py -x`, and `uv run pytest -q
tests/learn/test_all_lessons_runtime_path.py tests/learn/test_lesson_flow_contract.py
tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_ws_beginner_path.py`
all pass. The broader `uv run pytest -q tests/learn -rs` run now reports
418 passed and 1 skipped, with the skip still being the deliberate opt-in live
FLX4 jog proof.
A fifty-ninth slice proves the real on-screen Learn path against the actual
sidecar instead of only the test harness: `scripts/live_learn_screen_probe.py`
connects to `ws://127.0.0.1:8765`, starts `L1.01`, sends four screen-click
`lesson_continue` ACKs, waits through the real 45 s dwell, and requires both
`ipc.learn.complete_lesson` and a completed progress snapshot. To keep live
probes from mutating the user's normal progress, `LearnProgress.progress_path`
now honors `VIBEMIX_LEARN_PROGRESS_PATH`. Focused proof: `uv run ruff check
src/vibemix/learn/progress.py scripts/live_learn_screen_probe.py
tests/learn/test_live_learn_screen_probe.py tests/test_learn_progress_env_path.py`,
`uv run pytest -q tests/learn/test_live_learn_screen_probe.py
tests/test_learn_progress_env_path.py`, and `uv run pytest -q
tests/learn/test_live_learn_screen_probe.py
tests/learn/test_live_learn_socket_jog_probe.py
tests/learn/test_all_lessons_runtime_path.py tests/test_learn_progress_env_path.py`
all pass. Live proof on this machine: `VIBEMIX_LIVE_SMOKE=1 uv run pytest -q
-m macos_audio tests/test_main_live.py -v` passed, then a real
`python -m vibemix` process was started with
`VIBEMIX_LEARN_PROGRESS_PATH=/tmp/vibemix-live-learn-proof/learn-progress.json`;
`lsof` showed the app listening on `127.0.0.1:8765`; `uv run python
scripts/live_learn_screen_probe.py --seconds 60` passed with 4 ACKs,
4 advances, completion, and `progress_completed=true`; the isolated progress
JSON reloads with `L1.01.completed=true`. Current external blocker for the
physical-controller proof: Rekordbox is running, but
`uv run python scripts/sniff_controller.py --list` returns no MIDI inputs,
`system_profiler SPUSBDataType` shows no DDJ/FLX/Pioneer USB device, and
CoreAudio shows BlackHole plus the Rekordbox aggregate but no FLX4 device.
So the on-screen live path is now proven; the physical jog/control path is
still unproven because macOS cannot currently see the controller.
A sixtieth slice makes that remaining live-proof boundary repeatable:
`scripts/learn_live_readiness.py` preflights the sidecar socket, Rekordbox
process, MIDI input ports, macOS USB profiler, and audio device visibility,
then reports readiness for `screen`, `physical`, or `course3` proof paths as
JSON. Course 3 readiness now requires the sidecar, physical MIDI, USB-visible
controller, Rekordbox, loopback audio, and a DJ app/controller audio surface,
so it cannot go green from audio routing alone. Focused proof:
`uv run ruff check scripts/learn_live_readiness.py
tests/learn/test_learn_live_readiness.py`, `uv run pytest -q
tests/learn/test_learn_live_readiness.py`, and `uv run pytest -q
tests/learn/test_learn_live_readiness.py
tests/learn/test_live_learn_screen_probe.py
tests/learn/test_live_learn_socket_jog_probe.py
tests/learn/test_all_lessons_runtime_path.py tests/test_learn_progress_env_path.py`
all pass (10 readiness tests; 53 in the focused proof bundle). A current
`uv run python scripts/learn_live_readiness.py --require course3` run fails
honestly: the sidecar is not currently running, no MIDI controller ports are
visible, and no DDJ/FLX/Pioneer USB device is visible; it does confirm
Rekordbox is running plus BlackHole and the rekordbox Aggregate Device are
visible. The broader `uv run pytest -q tests/learn -rs` run now reports
431 passed and 1 skipped, with the skip still being the deliberate opt-in live
FLX4 jog proof.
A sixty-first slice adds a durable live-proof artifact runner:
`scripts/run_learn_live_proof.py` sequences readiness, optional app startup,
screen proof, optional physical jog proof, optional Course 3 lens proof,
shutdown, and progress-file evidence into one JSON report. It deliberately
marks stale progress snapshots as skipped unless the screen proof passed in the
same run. Focused proof: `uv run ruff check scripts/run_learn_live_proof.py
tests/learn/test_run_learn_live_proof.py scripts/learn_live_readiness.py
tests/learn/test_learn_live_readiness.py`, `uv run pytest -q
tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py
tests/learn/test_live_learn_screen_probe.py
tests/learn/test_live_learn_socket_jog_probe.py
tests/learn/test_all_lessons_runtime_path.py tests/test_learn_progress_env_path.py`,
and a real `uv run python scripts/run_learn_live_proof.py --start-app --out
/tmp/vibemix-live-learn-proof/proof-screen-runner.json` all pass. The live
artifact reports the app started, `screen_probe=passed` with 4 ACKs and
4 advances, `complete_seen=true`, `progress_completed=true`, app shutdown
passed, and isolated progress reloads with `L1.01.completed=true`. The broader
`uv run pytest -q tests/learn -rs` run now reports 436 passed and 1 skipped.
A follow-up combined run requested every currently relevant live proof:
`uv run python scripts/run_learn_live_proof.py --start-app --physical --course3
--require-count-in --out /tmp/vibemix-live-learn-proof/proof-combined-current.json`.
The report correctly fails overall while preserving proof boundaries:
`screen_probe=passed` with 4 ACKs, 4 advances, completion, and completed
progress; app shutdown passed; `physical_probe` and `course3_probe` are skipped
with blockers naming the missing MIDI controller input and missing
DDJ/FLX/Pioneer USB device. This is the strongest current artifact: on-screen
Learn is live-proven; the physical/Course 3 requirements are still unproven due
external hardware visibility.
A sixty-second slice adds a proof-artifact validator:
`scripts/validate_learn_live_proof.py` grades `run_learn_live_proof.py` JSON
reports requirement-by-requirement. It validates the current combined artifact
as screen proof plus explicit physical/Course 3 unavailability only when
`--allow-skipped physical --allow-skipped course3` is present, and fails that
same artifact if asked to prove physical movement. Focused proof: `uv run ruff
check scripts/validate_learn_live_proof.py
tests/learn/test_validate_learn_live_proof.py scripts/run_learn_live_proof.py
tests/learn/test_run_learn_live_proof.py scripts/learn_live_readiness.py
tests/learn/test_learn_live_readiness.py`, `uv run pytest -q
tests/learn/test_validate_learn_live_proof.py
tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py
tests/learn/test_live_learn_screen_probe.py
tests/learn/test_live_learn_socket_jog_probe.py
tests/learn/test_all_lessons_runtime_path.py tests/test_learn_progress_env_path.py`,
and both real validations against
`/tmp/vibemix-live-learn-proof/proof-combined-current.json` pass/fail in the
expected directions. The broader `uv run pytest -q tests/learn -rs` run now
reports 442 passed and 1 skipped.
A sixty-third slice makes the proof runner useful during actual hardware
replug attempts: `run_learn_live_proof.py` now supports
`--wait-physical-seconds` and `--wait-course3-seconds`, polling the exact
readiness bits before it skips the jog or Course 3 probes. A short current
environment run,
`uv run python scripts/run_learn_live_proof.py --no-screen --physical
--wait-physical-seconds 1 --wait-interval 0.2 --out
/tmp/vibemix-live-learn-proof/proof-wait-current.json`, fails as expected but
writes a useful artifact: the physical wait stage attempted twice, final
readiness still had `physical_learn=false`, and the physical probe was skipped
with blockers. Focused proof now reports 66 passed in the live-proof bundle,
and the broader `uv run pytest -q tests/learn -rs` run reports 444 passed and
1 skipped.
A sixty-fourth slice tightens proof-artifact validation semantics so the next
integration session cannot accidentally bless a weak live run. Physical proof
now has to prove the specific L1.07 jog path: lesson loaded, `control_id=jog:A`,
jog position observed, ACK sent, and lesson advance observed. Course 3 proof now
requires lens frames, active Course 3 state, count-in evidence, and a citable
`last_lens.next_phrase_cue_id`; a lens-only artifact no longer validates as
Course 3 proof. Focused proof now reports 69 passed in the live-proof bundle,
`tests/learn/test_validate_learn_live_proof.py` reports 9 passed, and the
broader `uv run pytest -q tests/learn -rs` run reports 447 passed and 1 skipped.
A sixty-fifth slice fixes a real Python/Tauri IPC schema drift: the shared
`ipc.learn.progress_state` schema still described v1 progress and rejected the
v2 `skills` live ledger emitted by `LearnProgress().to_dict()`. In the
in-process WebSocket proof this dropped valid progress snapshots with
`ValidationError`. The schema now accepts `schema_version` 1..2 and a closed
per-skill live ledger (`live_proof_count`, `mastered`, `first_mastered_at`);
`npm run codegen:ipc` regenerated the TypeScript type and AJV validator. The
proof runner's top-level `passed` flag is now backed by the strict artifact
validator too, so a JSON artifact cannot look green while failing the same
evidence contract. Current proof: focused live-proof bundle 70 passed,
`tests/ipc/test_learn_envelope_parity_p92.py tests/learn/test_live_learn_screen_probe.py`
18 passed, IPC schema parity 78/78 passed, TypeScript `check:ipc` passed,
Learn UI progress consumers 16 passed, full `tests/learn -rs` reports 461
passed and 1 skipped, and the real
`/tmp/vibemix-live-learn-proof/proof-screen-schema-v2-current.json` artifact
passes `--require screen` with v2 progress and six skills present.

## Verdict

v9.0 is not ready to call engineering-complete for a beginner DJ teaching
module. It is not fake: there is a real `src/vibemix/learn/` package, a lesson
FSM, typed IPC envelopes, a separate Learn webview, SVG controller schematics,
progress persistence, exemplar/recital classes, and a meaningful amount of unit
coverage. But the integrated learner path is broken or scaffolded in several
release-blocking ways.

The honest label is:

> Real implementation slices, integration-incomplete, overclaimed in milestone
> docs.

The strongest issue is that the "happy path" a beginner would use is not proven
and appears broken: open Learn from the app, click a lesson, receive the correct
lesson, advance through the dialog, move the highlighted physical control, hear
or see exemplar/recital behavior, and unlock the next course.

## The Deeper Product Failure

The code failures are symptoms. The deeper failure is that the module reads like
an executor converted a big emotional prompt into milestone inventory instead of
turning it into an authored teaching experience.

The original ask had a very specific energy: magical, mind-blowing, fully
autonomous, beginner-safe, comprehensive, and unmistakably vibemix. The shipped
artifact mostly answers a narrower question:

> Can we scaffold a lesson namespace, typed IPC, fixtures, SVGs, tests, and a
> milestone audit?

That is useful engineering, but it is not the product. The product should answer:

> What does it feel like when a person who has never DJed before suddenly
> understands what the deck is telling them?

The module does not yet have a strong answer to that.

### It over-engineered the surface

The user should not meet v9 as a syllabus. They should pick up their physical DJ
set, or use the on-screen DJ set, and start doing the thing. The lesson system
can be deep underneath, but the visible experience should be almost comically
simple:

1. Plug in or use the screen deck.
2. Touch the highlighted control.
3. Hear what changed.
4. Try the move in a tiny musical context.
5. Get one correction.
6. Continue.

Anything that looks like a course catalog, dashboard, progress database, or
administrative training portal is poison for this moment. A beginner opening a
36-row syllabus wall will feel the weight of everything they do not know before
they feel the joy of touching sound. They will shrivel before they begin.

The architecture can still contain courses, unlocks, evidence, progress,
recitals, and adaptive prompting. But those should be backstage machinery. The
frontstage should be one deck, one prompt, one action, one tiny win.

### Do not misread simplicity as shallowness

This is the trap for the next executor: "make it simple" must not become "make
it dumb." The user-facing surface should be simple because the system is doing
the hard work invisibly.

The right shape is not one giant prompt. One giant prompt will not generalize,
will be hard to test, and will slowly turn into a bag of vibes. The right shape
is a small teaching brain made of clear loops:

- **Observe:** what hardware exists, what changed, what audio is audible, what
  skill the learner is currently attempting.
- **Decide:** what is the single next useful action.
- **Teach:** say the shortest line that makes the action meaningful.
- **Verify:** did the user's hand/audio actually do the intended thing.
- **Adapt:** if they hesitate, simplify; if they overshoot, diagnose; if they
  succeed, name the win and move on.

That loop can sit behind an interface that looks almost empty. The depth is in
the teacher's judgment, not in visible pages.

The rebuild should therefore avoid both failure modes:

- **Over-engineered:** a syllabus wall, dashboards, rows, gates, and proof
  artifacts before the beginner has touched sound.
- **Over-simplified:** a toy prompt that says generic DJ tips and cannot adapt
  to the user's hands, controller, music, or mistakes.

The product target is intelligent simplicity: one visible action, backed by live
state, evidence, memory, curriculum, and taste.

### It lacks a teaching thesis

The curriculum has topics, but not a philosophy. A great beginner module needs a
spine, something like:

- "DJing is timing, energy, and confidence."
- "Every lesson follows hear it, touch it, name it, prove it."
- "You do not learn controls abstractly; you learn what each control does to the
  room."
- "The first win is not knowing terminology. The first win is making two songs
  feel intentional together."

The current curriculum mostly enumerates controls and techniques. That is
necessary, but not enough. It teaches "this is a crossfader" more readily than
"this is how you move attention from one song to another without panic."

### It lacks signature moments

There is no moment in the implementation that feels like only vibemix would have
made it. A magical beginner module should have at least a few unforgettable
beats:

- A first 60-second ritual: plug in, touch one control, see the deck wake up, and
  hear the tutor say exactly what changed.
- A "before and after" transition: the user makes an ugly transition, vibemix
  replays the same moment with one correction, then asks them to feel the
  difference.
- A "trainwreck lab": intentionally misalign two tracks, then rescue them with
  jog, filter, or cut. No shame, just controlled failure.
- A "your library teaches you" moment: pick one of the user's actual tracks and
  point to its intro, drop, breakdown, and outro.
- A "room hears / headphones hear" split: visually and sonically distinguish
  what the audience hears from what the DJ is preparing.
- A "ghost hand" overlay: not just highlight the control, but show the motion
  path and target range for the next move.
- A "you just did DJing" recap after the first real blend, naming the exact
  decisions the user made.

The existing implementation has ingredients for some of this, especially SVG
mirroring and exemplar tracks, but the actual shipped path does not stage those
moments.

### It treats comprehensiveness as coverage, not transformation

Thirty-six lesson rows can look comprehensive on paper. For a beginner, that can
also feel like a syllabus wall. A teaching module should be comprehensive in the
way a good coach is comprehensive: it knows what to ignore until the learner is
ready.

The current shape leans toward "all topics are represented." It needs to lean
toward "the learner is changed by the sequence." That means:

- A tiny first win before the full lesson list.
- Fewer visible choices at the start.
- Locked progression that feels motivating rather than bureaucratic.
- Recaps that convert hand motion into concepts.
- Practice loops that return to earlier skills under slightly harder conditions.
- A sense of "I am becoming a DJ," not "I completed row 7."

### The tutor is starting to teach live, but it is still bounded

The runtime still emits authored lesson text verbatim for the main prompts. That
is defensible for safety. The latest runtime now reacts to several wrong-action
classes deterministically: wrong deck, wrong control, wrong button direction,
and too-small CC deltas all produce specific hints with observed/expected
control citations. That is a real backstage teaching-loop improvement, not just
caption playback.

But this is not yet the full AI teacher promised by the milestone. The teacher
still does not listen to audio timbre, notice hesitation across time, read genre
context, adapt to library taste, or explain the sound coming out of the deck in
live language. The system has prompt scaffolding and a safer deterministic hint
layer, but not a fully present coaching intelligence.

The right move is not unlimited improvisation. The right move is a constrained,
opinionated teacher loop:

- Scripted lesson goal.
- Live observation from controller/audio state.
- Short adaptive diagnosis.
- One next action.
- Evidence citation when making claims about audio.
- A warm recap in the user's language.

That would let the module have flavor without hallucinating.

### The UI has surface taste, but not interaction taste

The visual direction is trying to fit CDJ Whisper: dark, restrained, hardware
schematics, amber highlight, low-noise chrome. That is directionally right for
vibemix. But the interaction design is not brave enough yet.

The current UI says, essentially: here is a controller diagram, here is a
lesson list, here is a tutor dock. It does not yet create a teaching stage.

The stage should feel like a practice booth:

- The deck is the center, not a diagram in a window.
- The next action is physically obvious.
- The user always knows whether the app is listening to hardware, audio, both,
  or neither.
- Mistakes are visible and recoverable.
- The module rewards correct motion with immediate sensory feedback, not just a
  row status update.

### The milestone process rewarded proof-shaped work

The docs are full of REQ-IDs, phases, gates, schema mirrors, and audit language.
Some of that is useful. But the volume of proof-shaped work appears to have
crowded out product taste.

The tell is that the milestone audit marks engineering complete while carrying
forward issues that are not small polish items: curriculum key normalization,
exemplar bank sourcing, Course 3 wiring, live controller verification, and
first-launch ear-pass. Those are core to the product promise.

This is how the module lost flavor: the work optimized for checkable artifacts.
It did not optimize for the one thing a beginner would feel in the chair.

## What "Flavor" Should Mean Here

Flavor is not random jokes, flashy UI, or the model inventing facts. Flavor is
authored taste under constraints.

For vibemix Learn, that means:

- The tutor sounds like a DJ friend, not a help article.
- Every lesson starts from sound and touch, then gives vocabulary.
- The user's own music appears as soon as possible.
- The module has rituals: wake the deck, find the one, rescue the trainwreck,
  earn the blend, graduate into live play.
- Failure is designed, not avoided.
- The AI is allowed to have a teaching point of view, but every factual/audio
  claim is grounded.
- The interface is sparse until the next action, then intensely clear.

If this becomes just "a complete DJ curriculum in a webview," it will never feel
magical. The magic is the app noticing the user's hands and the music, then
turning that moment into understanding.

## Better North Star

The next version should not start from "fix all 36 lessons." It should start
from one unforgettable vertical slice:

1. User opens Learn from the main app.
2. Learn detects the controller.
3. The stage asks for one touch: move the crossfader.
4. The UI mirrors the movement with a real thumb translation.
5. The tutor explains what the audience hears.
6. The user loads two tracks from their own library or a packaged fallback.
7. Vibemix walks them through a deliberately simple blend.
8. It lets them make one mistake.
9. It diagnoses the mistake using controller/audio evidence.
10. The user fixes it.
11. The module recaps: "you just moved attention from deck A to deck B."

That one path, done with taste, would be more valuable than 36 inert lesson rows.

## Findings

### P0 - Learn mode does not launch the Learn window

The Rust command exists and is registered, but the app UI does not call it. The
mode picker changes local session mode and emits `ipc.session.set_mode`; it does
not invoke `open_learn_window`.

Evidence:

- `tauri/src-tauri/src/learn_window.rs:64` defines `open_learn_window`.
- `tauri/src-tauri/src/main.rs:111` registers the command.
- `tauri/ui/src/session/render-loop.ts:100` only calls `setSessionState({ mode })`
  and emits `ipc.session.set_mode`.
- `rg "open_learn_window" tauri/ui/src tauri/src-tauri/src` found no UI caller.

Impact: the visible LEARN segment is persistence chrome, not a usable entrypoint.
A beginner cannot reliably start the module from the main app.

Latest rebuild status: fixed in the dirty worktree. The session mode handler now
invokes `open_learn_window` when the learner picks LEARN, and the same path still
persists `ipc.session.set_mode`.

### P0 - Frontend lesson IDs are rejected by the backend

The Learn progress list emits slugged lesson IDs such as
`L1.01-opening-dialog`, because the frontend schema expects
`^L[0-9]+\.[0-9]+-.+$`. The Python curriculum is keyed by short IDs such as
`L1.01`, `L2.14`, and `L3.06`. The backend handler rejects anything not exactly
in `CURRICULUM`.

Evidence:

- `tauri/ui/src/learn/lesson/curriculum-meta.ts:91` builds `${short_id}-${slug}`.
- `tauri/ui/src/learn/lesson/curriculum-meta.ts:124` returns that slugged ID.
- `tauri/ui/src/learn/learn-window.ts:241` emits `ipc.learn.start_lesson`.
- `src/vibemix/learn/ipc_handlers.py:104` rejects IDs not in `CURRICULUM`.
- `src/vibemix/learn/curriculum.py:146` and following use short IDs.
- `tauri/ui/src/ipc/messages.schema.json:3084` requires the slug pattern.

Impact: selecting Course 1-3 lessons from the UI silently no-ops at the Python
boundary. The v9 audit itself acknowledges this as a carry-forward item at
`.planning/milestones/v9.0-MILESTONE-AUDIT.md:285`, but still marks the milestone
engineering-complete.

Latest rebuild status: fixed. The Learn UI now emits canonical short IDs such as
`L1.01`; the backend still accepts old slugged IDs through a compatibility
normalizer so older persisted progress rows do not wedge the runtime.

### P0 - The runtime speaks only beat 0 of multi-beat scripts

Transcripts contain multi-beat dialogs, but the runtime emits only beat 0 when
entering `awaiting_action`. There is no sequencer that advances
`current_beat_index` through `tutor_speak[]`. The FSM then moves from
`awaiting_action` to `advancing` on a single matching action.

Evidence:

- `src/vibemix/learn/runtime.py:456` resets `current_beat_index = 0`.
- `src/vibemix/learn/runtime.py:563` calls `_emit_tutor_beat(0)`.
- `src/vibemix/learn/runtime.py:747` can emit arbitrary beats, but production
  search shows no later beat driver.
- `src/vibemix/learn/runtime.py:143` moves directly to `advancing` on a match.
- `src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json:5` contains a
  four-beat opening dialog.

Impact: much of the written curriculum is inert. Example: the opening dialog
asks to read four scripted lines, but the runtime path only speaks the first
line.

Latest rebuild status: fixed for the rebuilt authored step-flow path. The
structured-flow compiler turns every lesson into canonical steps; `lesson_continue`
advances beat-by-beat, and control lessons now emit their setup/action prompt
before verification instead of immediately waiting on a hidden action.

### P0 - Many expected lesson controls are not observable

The MIDI mirror publishes only a subset of controller state. Lesson transcripts
expect controls that are not emitted by the mirror and, in some cases, are not
real controls in the Learn UI.

Evidence:

- `src/vibemix/learn/midi_mirror.py:317` emits `vol`, EQs, `filter`, and `tempo`.
- `src/vibemix/learn/midi_mirror.py:322` emits only `play`, `cue`, and
  `jog_touched` among buttons.
- Transcripts expect `lesson_continue`, `headphone_cue`, `master_vol`, `jog`,
  `loop_in`, `hotcue`, and `fx_echo`; examples:
  - `src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json:35`
  - `src/vibemix/learn/transcripts/course_1_anatomy/08_headphone_cueing.json:19`
  - `src/vibemix/learn/transcripts/course_2_transitions/09_loop_transition.json:25`
  - `src/vibemix/learn/transcripts/course_2_transitions/10_hot_cues_memory_cues.json:19`
- `tauri/ui/src/learn/learn-window.ts:510` emits `ipc.learn.ack` only from
  `midi_position` deltas.
- `rg` finds no Learn SVG click/keyboard handler emitting `source: "click"`.

Impact: large parts of the curriculum cannot be completed by the physical
controller path as written. The "tap anywhere to read the next line" style
lessons are especially suspicious because there is no general `lesson_continue`
ack source.

Latest rebuild status: substantially improved, still not a full hardware
ear-pass. The on-screen deck aliases rendered `jog_touch` controls to the
curriculum's `jog` action, physical jog-touch ACKs normalize to `jog` CC events
at the IPC boundary, and the `learn-screen-action` button appears as a fallback
when the current lesson asks for a control that is not drawn on the active SVG,
such as `master_vol`. The MIDI mirror now projects new one-shot button events
for `sync`, `loop_in`, `loop_out`, `hotcue`, and `filter_fx`/`fx_echo`, and the
UI emits a first-seen pulse ACK for one-shot MIDI positions. Remaining honest
gap: real physical `master_vol` and `headphone_cue` support still depends on
known controller profile mappings rather than invented controls.

### P0 - Exemplar and recital controllers are defined but not wired into app boot

The architecture includes a per-lesson observer registry for special lessons,
and the exemplar/recital controllers have their own tests. The live app boot
does not register them.

Evidence:

- `src/vibemix/learn/runtime.py:229` defines `register_lesson_observer`.
- `src/vibemix/learn/runtime.py:575` only starts an active observer if one was
  registered.
- `rg "register_lesson_observer\(" src/vibemix tests` found only the definition
  in production code.
- `src/vibemix/__main__.py:1609` constructs `LessonRuntime`.
- `src/vibemix/__main__.py:1627` registers the five inbound Learn IPC handlers.
- No app boot code creates/registers `ExemplarLessonController` or
  `RecitalRuntime`.

Impact: Course 1.14 EQ-as-tutor, Course 1.16 recital, and Course 2 recital are
tested as isolated classes, not integrated lesson experiences.

Latest rebuild status: the dirty worktree now wires these observers in
`src/vibemix/__main__.py`: `L1.14` registers `ExemplarLessonController`, `L1.16`
and `L2.14` register `RecitalRuntime`, and observer-emitted
`ipc.learn.complete_lesson` envelopes are routed back into
`LessonRuntime.complete_observer_lesson`. Added
`tests/learn/test_observer_boot_wiring.py` to pin the boot wiring and the safe
no-op exemplar player fallback.

### P0 - The packaged exemplar bank was empty

Original inherited state: the source tree shipped only `.gitkeep` placeholders
and an empty manifest, so the default no-library beginner experience lacked the
promised packaged audio exemplars.

Latest rebuild status: fixed as a shippable scaffold, still pending ear-pass.
The bank now includes four self-authored WAV loops under
`src/vibemix/learn/assets/band_exemplars/{sub,low,mid,high}/`, a pinned
`MANIFEST.json`, NOTICE attribution, `.gitignore` package-data whitelisting, and
finder fallback for WAV files. Tests assert empty-library fallback, directory
layout, manifest-to-NOTICE attribution, exact file set, SHA-256 hashes, and
stereo decode. A wheel check proves the WAVs are present in the built package.

Remaining honest gap: these are deterministic internal teaching loops, not
ear-passed club records. They are enough to prevent fake/null exemplar UX, but a
human DJ should still approve the sonics or replace them with richer licensed
examples before calling the marquee experience final.

### P1 - Course 3 proactive tutor lens is scaffolded, not live-proven

Course 3 fields exist on `MusicState` and the coach renderer can read them, but
the production writer path appears absent.

Evidence:

- `src/vibemix/state/music_state.py:167` defines `session_active`,
  `phrase_position_confidence`, and `next_phrase_at` as scaffolding.
- `src/vibemix/state/coach.py:520` emits the proactive lens marker only if
  `state.session_active` is true.
- `rg` found no production assignments to `session_active`,
  `phrase_position_confidence`, or `next_phrase_at`.
- Tests set these fields directly in synthetic fixtures.
- Course 3 transcripts mostly gate on `lesson_continue`, for example
  `src/vibemix/learn/transcripts/course_3_play_mode/01_first_5_minute_mix.json:21`.

Impact: the "live proactive coaching" claim is not supported by integration
evidence. It is a prompt/state seam awaiting real runtime wiring.

Latest rebuild status: substantially fixed, still not real-session proven.
`state_refresh_loop` now accepts the live `LearnState` read-only and writes
`MusicState.session_active=True` only when the current course is
`course_3_play_mode`, the debounced audio state is audible, and the inferred
audible deck is not `"none"`. Leaving Course 3 or losing the audible deck clears
the lens and resets phrase fields to cold. Forward count-ins now open only when
the audible Rekordbox track, playhead, BPM/deck confidence, and a DJ-authored
cue section resolve; fallback section maps remain cold. A deterministic Course
3 live-set rehearsal now proves cue count-ins, saved-pool targeting, and
off-pool deviation feedback together. The remaining gap is no real
controller/ear pass proving those calls inside an actual set.

### P1 - Course locking and reset semantics do not match the progress model

The backend progress model has course unlock fields. The frontend progress list
does not consume them and renders all lessons as enabled. The reset handler
clears dictionaries but does not reset unlock booleans.

Evidence:

- `src/vibemix/learn/progress.py:92` defines `course_2_unlocked`.
- `src/vibemix/learn/progress.py:99` defines `course_3_unlocked`.
- `tauri/ui/src/learn/learn-window.ts:155` models only `schema_version`,
  `courses`, and `lessons`.
- `tauri/ui/src/learn/lesson/progress-list.ts:119` creates enabled buttons for
  every lesson.
- `src/vibemix/learn/ipc_handlers.py:323` clears `lessons` and `courses` on
  reset, but not unlock booleans.

Impact: beginners can jump into later courses despite the intended recital gate,
and a reset may preserve unlocked course state.

Latest rebuild status: fixed in the current slice. `curriculum-meta.ts` now
projects `course_2_unlocked` and `course_3_unlocked` into locked rows plus a
single recommended "next" lesson, `learn-window.ts` refreshes the chooser from
progress snapshots, and `ipc_handlers.py` enforces the same gates for
`start_lesson` and `start_course`. Covered by
`tauri/ui/tests/learn/test_curriculum_meta.spec.ts`,
`tauri/ui/tests/learn/test_progress_list.spec.ts`,
`tauri/ui/tests/learn/test_practice_booth_shell.spec.ts`, and
`tests/learn/test_ipc_handlers_dispatch.py`.

### P1 - Action validation is weaker than the lesson copy implies

CC actions compare control name and synthetic delta. They do not enforce deck
for CCs, and the IPC handler fabricates `prev_value` by about 40 because the
wire ack does not carry the true previous value.

Evidence:

- `src/vibemix/learn/runtime.py:338` handles CC matches without deck comparison.
- `src/vibemix/learn/runtime.py:341` compares current and previous values.
- `src/vibemix/learn/ipc_handlers.py:218` explains that the sidecar does not see
  prior frames.
- `src/vibemix/learn/ipc_handlers.py:256` synthesizes `prev_value`.

Impact: a tiny expected-control movement can satisfy a ">=30% of range" lesson
gate, and a deck A move can satisfy a deck B CC lesson if the control name
matches.

Latest rebuild status: fixed for the current ACK path. CC and button matching
now enforce the expected deck when the lesson declares one, and the UI sends real
`prev_value` deltas from the MIDI mirror instead of relying on the old synthetic
delta. Jog-touch and generic FX controls normalize before deterministic
verification.

### P1 - First-open Learn UI has layout and state issues

Independent UI inspection found the first-open layout clipped. The source
supports the concern: the root grid has three rows, but the DOM mounts more
top-level children into that grid. The frontend also does not request persisted
progress on load.

Evidence:

- `tauri/ui/src/learn/learn-window.ts:199` mounts titlebar, stage, progress list,
  status bar, SR region, and footer.
- `tauri/ui/src/learn/styles/learn.css:21` defines only three grid rows.
- `tauri/ui/src/learn/learn-window.ts:233` initializes progress from
  `buildProgressEntries(null)`.
- `rg` found no frontend emit of `ipc.learn.progress_state` with
  `action: "snapshot"`.
- `src/vibemix/learn/ipc_handlers.py:353` can answer a snapshot if requested.

Impact: the selector can render as a cramped slit, persisted progress may not
appear on initial open, and first-run hints can drift stale after controller
detection.

Latest rebuild status: fixed for first paint. The Learn window now opens as a
practice-booth surface with the screen deck ready, requests progress snapshots,
rerenders the chooser from live progress/controller state, and keeps the
recommended action focused instead of dumping a raw syllabus wall on first open.

### P1 - IPC schema parity fails and the smoke script masks it

The standalone schema parity check fails, while the smoke script explicitly
downgrades that failure to a warning.

Evidence:

- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/check_ipc_schema.py` failed:
  `78 oneOf entries vs 77 wrapper dataclasses`.
- `scripts/smoke/sidecar_bundle_smoke.sh:130` labels the IPC schema parity step.
- `scripts/smoke/sidecar_bundle_smoke.sh:132` comments that this check exits 1.
- `scripts/smoke/sidecar_bundle_smoke.sh:139` says to surface as WARN, not FAIL.

Impact: release evidence can look green while schema drift remains.

Latest rebuild status: fixed. `scripts/check_ipc_schema.py` now reports 78
dataclasses matching 78 schema `oneOf` entries, and the smoke script no longer
downgrades schema/dataclass drift to a warning.

### P1 - Accessibility and keyboard coverage was mostly TODO/skipped

Several Learn accessibility tests were explicit RED-state stubs or TODOs.
Controller SVG groups were focusable and styled as clickable, while important
keyboard, SR, dwell, and contrast contracts were not live.

Evidence:

- `tauri/ui/tests/learn/test_keyboard_nav_order.spec.ts`,
  `test_tutor_speak_sr_announcement.spec.ts`, `test_sr_announcement.spec.ts`,
  `test_hud_progress_dots_keyboard.spec.ts`, `test_min_dwell_aria.spec.ts`,
  `test_contrast_ratios.spec.ts`, and `test_contrast_p92.spec.ts` are now live
  Vitest contracts.
- `tauri/ui/src/learn/components/controller-stage.ts` now maps
  `data-cue-color="amber"` and `"warning"` through CSS-visible token colors.
- `tauri/ui/src/learn/learn-window.ts` emits screen-deck ACKs for rendered
  controls and fallback ACKs for screen-only controls.

Impact: the UI advertised hardware-free/keyboard interactivity that was not
actually implemented or covered. This is now substantially fixed across
jsdom/unit coverage, browser Playwright coverage, and launched-window process
checks.

Latest rebuild status: substantially fixed. `ipc.learn.tutor_speak` now updates
the shared `[data-sr-region="tutor"]` region, hint speech raises `aria-live` to
`assertive`, and the skip button's 45-second dwell lock has live aria/tooltip
tests. HUD progress dots support keyboard replay/current/pending behavior.
Contrast placeholders are now live token-level WCAG tests, and the tutor `.now`
line uses fixed 28px silk text rather than viewport-scaled type. A Chromium
Playwright pass now verifies computed browser contrast on the Learn webview.
The launched Tauri smoke and browser Playwright suite now also run axe-core
against Learn and fail on critical/serious WCAG violations.

### P2 - Frontend curriculum mirror has drift

The frontend maintains a static mirror of the Python curriculum with a future
drift gate. It already disagrees with Python titles/slugs.

Examples:

- Python `L1.08` is `headphone cueing`; TS says `loop section`.
- Python `L1.10` is `anatomy of a song`; TS says `filter knob`.
- Python `L1.11` is `counting bars`; TS says `fx pads`.
- Python Course 3 starts with `first 5-minute mix`; TS says
  `playing live versus the booth`.

Evidence:

- `tauri/ui/src/learn/lesson/curriculum-meta.ts:5` says Python is authoritative.
- `tauri/ui/src/learn/lesson/curriculum-meta.ts:9` defers the drift gate to P98.
- `src/vibemix/learn/curriculum.py:216`, `:236`, `:246`, and `:464` show the
  Python titles.

Impact: UI copy, slugged IDs, and lesson semantics are not locked to the
authoritative curriculum.

Latest rebuild status: fixed for the local mirror. The frontend navigation
projection now mirrors the Python course IDs, lesson titles, and canonical short
IDs for all 36 lessons.

### P2 - HUD/progress details were stale

The Learn HUD still maps old course IDs and progress dots are derived only from
completed progress entries.

Evidence:

- `tauri/ui/src/learn/lesson/hud.ts:31` maps `course_1`, `course_2`, and
  `course_3`.
- Python emits `course_1_anatomy`, `course_2_transitions`,
  `course_3_play_mode`.
- `src/vibemix/learn/progress.py:174` builds dots by iterating existing progress
  rows, not all lessons in the course.
- `tauri/ui/src/learn/lesson/hud.ts:150` formats `OF ${dots.length}`.

Impact: first lesson in a course can show an incorrect course chip and a bad
denominator such as `OF 0`.

Latest rebuild status: fixed. `LessonHud` now recognizes canonical course ids
(`course_1_anatomy`, `course_2_transitions`, `course_3_play_mode`) while keeping
legacy aliases. `LearnProgress.dots_for_course(...)` now walks the authoritative
curriculum order for the active course and marks every lesson as completed,
current, or pending; `LessonRuntime` passes the active lesson id so the HUD can
show a real current dot and denominator. Python tests pin a 16-dot Course 1
strip, and Vitest pins the canonical Course 1 chip plus `L1.02 OF 3` rendering.

### P2 - Faders and exemplar UI were visibly incomplete

Original inherited state: the controller renderer intentionally left faders
static, and exemplar play events were effectively log-only on the frontend.

Latest rebuild status: fixed for the current SVG geometry. Exemplar play/stop
events now show a visible listening chip with track shorthand, duration, gain,
active/stopped state, and screen-reader label. Faders still do not rotate the
parent group; instead, `applyPositionFrame` sets `data-value` and translates the
thumb rect along the inferred rail. The existing regression spec now asserts
both halves: no parent rotation, visible thumb translation.

Remaining honest gap: this proves screen-deck feedback in browser/unit tests,
not tactile correctness on a real controller with live audio.

## What Is Real And Worth Keeping

- The Learn package is cleanly separated under `src/vibemix/learn/`.
- The runtime uses a deterministic FSM rather than ad hoc timers.
- Learn IPC rides the existing `127.0.0.1:8765` bus rather than creating another
  socket.
- There is a thoughtful tone-safety decision: fixture scripts are emitted
  verbatim rather than improvised at runtime.
- Controller SVG/profile parity, highlight latency, and many lower-level
  message contracts are tested.
- The curriculum topics are directionally aligned with common beginner DJ
  material. A quick web spot-check found the expected core topics: beatmatching,
  tempo/phase alignment, headphones/cueing, EQ/volume/crossfader, phrasing/song
  structure, loops, and hot cues. See Digital DJ Tips, Hercules DJ Academy, and
  Point Blank:
  - https://www.digitaldjtips.com/how-to-mix-beatmix-beatmatch/
  - https://www.hercules.com/en-us/dj-academy/02-match-the-beat-the-basics-of-djing/
  - https://www.pointblankmusicschool.com/blog/a-beginners-guide-to-beat-matching-for-djs/

The issue is not that the curriculum idea is bad. The issue is that the app does
not yet execute the curriculum reliably.

## Verification Run

Latest rebuild slice:

- `uv run ruff check src/vibemix/library/prepared_pool.py src/vibemix/learn/prepared_pool.py src/vibemix/learn/runtime.py src/vibemix/library/next_suggestion.py src/vibemix/runtime/suggestion.py src/vibemix/__main__.py tests/learn/test_prepared_pool.py tests/runtime/test_suggestion.py tests/learn/test_observer_boot_wiring.py`
  - Passed.
- `uv run pytest -q tests/learn/test_prepared_pool.py`
  - 6 passed.
- `uv run pytest -q tests/learn/test_prepared_pool.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_lesson_flow_contract.py tests/learn/test_course_3_curriculum.py tests/learn/test_observer_boot_wiring.py tests/learn/test_runtime_invariants.py tests/learn/test_scripts_are_fixtures.py tests/learn/test_no_tutor_slop_blocklist.py`
  - 134 passed, 86 warnings.
- `uv run pytest -q tests/learn tests/state/test_refresh.py tests/state/test_coach_course3_confidence_gate.py tests/learn/test_no_speculative_phrase.py`
  - 418 passed, 111 warnings.
- `npm --prefix tauri/ui test -- --run tests/learn`
  - 138 passed.
- `uv run pytest -q tests/learn/test_observer_boot_wiring.py tests/runtime/test_suggestion.py tests/library/test_next_suggestion.py tests/intel/test_decision_runtime.py tests/learn/test_prepared_pool.py`
  - 96 passed.
- `uv run ruff check src/vibemix/learn tests/learn src/vibemix/state/refresh.py src/vibemix/state/music_state.py src/vibemix/state/coach.py tests/state/test_refresh.py tests/state/test_coach_course3_confidence_gate.py src/vibemix/__main__.py`
  - Passed.
- `uv run pytest -q tests/learn tests/ipc/test_learn_envelope_parity_p92.py tests/llm/test_model_router_learn_tutor.py tests/state/test_refresh.py tests/state/test_coach_course3_confidence_gate.py tests/state/test_evidence_registry.py`
  - 454 passed, 111 warnings.
- `npm --prefix tauri/ui test -- --run tests/learn`
  - 138 passed.
- `uv run ruff check src/vibemix/learn/runtime.py src/vibemix/learn/progress.py tests/learn/test_lesson_runtime_smoke.py tests/learn/test_progress_persistence.py`
  - Passed.
- `uv run pytest -q tests/learn/test_progress_persistence.py tests/learn/test_lesson_runtime_smoke.py tests/learn/test_ipc_handlers_dispatch.py`
  - 49 passed, 94 warnings.
- `npm --prefix tauri/ui test -- --run tests/learn/test_curriculum_meta.spec.ts`
  - 5 passed.
- `uv run ruff check src/vibemix/learn/teaching_loop.py src/vibemix/learn/runtime.py src/vibemix/learn/__init__.py tests/learn/test_teaching_loop.py`
  - Passed.
- `uv run pytest -q tests/learn/test_teaching_loop.py tests/llm/test_model_router_learn_tutor.py tests/learn/test_ipc_handlers_dispatch.py`
  - 33 passed, 87 warnings.
- `uv run pytest -q tests/learn tests/ipc/test_learn_envelope_parity_p92.py tests/llm/test_model_router_learn_tutor.py`
  - 366 passed, 111 warnings.
- `uv run ruff check src/vibemix/learn tests/learn src/vibemix/__main__.py src/vibemix/runtime/ws_bus.py`
  - Passed.
- `npm --prefix tauri/ui test -- --run tests/learn`
  - 138 passed.
- `git diff --check`
  - Passed.
- `npm --prefix tauri/ui test -- --run tests/learn/test_contrast_ratios.spec.ts tests/learn/test_contrast_p92.spec.ts`
  - 6 passed.
- `npm --prefix tauri/ui test -- --run tests/learn/highlight-paint.test.ts tests/learn/test_practice_booth_shell.spec.ts`
  - 13 passed.
- `npm --prefix tauri/ui test -- --run tests/learn`
  - 138 passed.
- `npm --prefix tauri/ui test -- --run tests/learn tests/session`
  - 306 passed.
- `npm --prefix tauri/ui test -- --run tests/learn/test_ws_client_tauri_bridge.spec.ts tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_uses_8765.spec.ts`
  - 7 passed.
- `npm --prefix tauri/ui run test:e2e:learn`
  - 7 passed.
- `uv run ruff check src/vibemix/learn/progress.py src/vibemix/learn/runtime.py tests/learn/test_progress_persistence.py tests/learn/test_lesson_runtime_smoke.py`
  - Passed.
- `uv run pytest -q tests/learn/test_progress_persistence.py tests/learn/test_lesson_runtime_smoke.py`
  - 20 passed, 8 warnings.
- `npm --prefix tauri/ui test -- --run tests/learn/test_hud_progress_dots_keyboard.spec.ts`
  - 4 passed.
- `npm --prefix tauri/ui run build`
  - Passed with existing Vite chunk warnings.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml ws_client -- --nocapture`
  - 3 passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml learn_window -- --nocapture`
  - 2 passed.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml`
  - Passed.
- `rustfmt --edition 2021 --check tauri/src-tauri/src/ws_client.rs`
  - Passed.
- `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check`
  - Failed on pre-existing formatting drift in `debrief_window.rs`,
    `library_cmds.rs`, and `sidecar.rs`; `ws_client.rs` itself passes
    rustfmt.
- `uv run ruff check tests/learn/learn_ws_sidecar_harness.py tests/learn/test_ws_beginner_path.py`
  - Passed.
- `uv run pytest -q tests/learn/test_ws_beginner_path.py`
  - 1 passed, 9 warnings.
- `uv run ruff check src/vibemix/state/refresh.py tests/state/test_refresh.py`
  - Passed.
- `uv run pytest -q tests/state/test_refresh.py tests/state/test_coach_course3_confidence_gate.py tests/learn/test_course3_no_exemplar_during_live.py tests/learn/test_no_speculative_phrase.py`
  - 71 passed.
- `uv run ruff check tests/learn/test_exemplar_lesson.py`
  - Passed.
- `uv run ruff check src/vibemix/learn/exemplar.py tests/learn/test_exemplar_finder.py tests/learn/test_exemplar_packaged_fallback.py`
  - Passed.
- `uv run pytest -q tests/learn/test_exemplar_finder.py tests/learn/test_exemplar_packaged_fallback.py tests/learn/test_exemplar_lesson.py tests/learn/test_exemplar_grounding_e2e.py`
  - 18 passed.
- Packaged exemplar wheel check:
  - `uv build --wheel --out-dir /tmp/vibemix-wheel-check` plus a wheel manifest
    scan proved all four `band_exemplars/**/*.wav` files are included.
- `uv run ruff check src/vibemix/learn/lesson_flow.py src/vibemix/learn/__init__.py tests/learn/test_lesson_flow_contract.py`
  - Passed.
- `uv run pytest -q tests/learn/test_lesson_flow_contract.py`
  - 42 passed.
- `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts`
  - 10 passed.
- `npm --prefix tauri/ui test -- --run tests/learn/test_fader_does_not_rotate.spec.ts tests/learn/test_practice_booth_shell.spec.ts`
  - 16 passed.
- `npm --prefix tauri/ui run build`
  - Passed with existing Vite chunk warnings.
- `npm --prefix tauri/ui run test:e2e:learn`
  - 7 passed.
- `uv run ruff check tests/learn/test_ipc_handlers_dispatch.py`
  - Passed.
- `uv run pytest -q tests/learn/test_ipc_handlers_dispatch.py`
  - 24 passed, 86 warnings.
- `uv run ruff check src/vibemix/learn tests/learn`
  - Passed.
- `uv run pytest -q tests/learn/test_midi_mirror_unit.py tests/learn/test_ipc_handlers_dispatch.py`
  - 23 passed.
- `uv run pytest -q tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_progress_persistence.py tests/learn/test_lesson_flow_contract.py`
  - 69 passed.
- `uv run pytest -q tests/learn/test_observer_boot_wiring.py tests/learn/test_exemplar_lesson.py tests/learn/test_recital.py tests/learn/test_course_2_recital.py tests/learn/test_ipc_handlers_dispatch.py`
  - 44 passed.
- `uv run pytest -q tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_lesson_flow_contract.py`
  - 58 passed.
- `uv run ruff check src/vibemix/learn/runtime.py src/vibemix/learn/ipc_handlers.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_advancement_gates.py`
  - Passed.
- `uv run pytest -q tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_advancement_gates.py`
  - 30 passed, 92 warnings.
- `uv run pytest -q tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_advancement_gates.py tests/learn/test_ws_beginner_path.py`
  - 31 passed, 101 warnings.
- `uv run pytest -q tests/learn/test_ws_beginner_path.py`
  - 1 passed, 9 warnings.
- `uv run pytest -q tests/runtime/test_ws_bus.py tests/runtime/test_ws_bus_empty_frames.py tests/runtime/test_ws_bus_snapshot.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_ws_bus_genre_fields.py tests/runtime/test_ws_bus_phase22_fields.py tests/wizard/test_wizard_loop_ipc.py`
  - 44 passed.
- `uv run pytest -q tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py`
  - 1 passed, 99 warnings.
- `uv run pytest -q tests/learn/test_advancement_gates.py`
  - 6 passed, 6 warnings.
- `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_controller_detected_mounts_svg.test.ts tests/learn/highlight-paint.test.ts`
  - 13 passed.
- `uv run pytest -q tests/learn tests/ipc/test_learn_envelope_parity_p92.py`
  - 348 passed, 109 warnings.
- `uv run ruff check src/vibemix/learn tests/learn src/vibemix/__main__.py src/vibemix/runtime/ws_bus.py`
  - Passed.
- `uv run pytest -q tests/learn tests/ipc/test_learn_envelope_parity_p92.py`
  - 351 passed, 110 warnings.
- `uv run pytest -q tests/learn/test_observer_boot_wiring.py tests/learn/test_runtime_evidence_grounding.py`
  - 6 passed, 1 warning.
- `uv run pytest -q tests/coach/test_citation_linter.py tests/state/test_evidence_registry.py`
  - 46 passed.
- `uv run pytest -q tests/learn tests/ipc/test_learn_envelope_parity_p92.py tests/coach/test_citation_linter.py tests/state/test_evidence_registry.py`
  - 397 passed, 110 warnings.
- `npm --prefix tauri/ui test -- --run tests/learn/test_learn_window_label.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
  - 4 passed.
- `npm --prefix tauri/ui test -- --run tests/learn/test_tutor_speak_sr_announcement.spec.ts tests/learn/test_practice_booth_shell.spec.ts`
  - 13 passed.
- `npm --prefix tauri/ui run build`
  - Passed with existing Vite chunk warnings.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml learn_window -- --nocapture`
  - 2 passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml ws_client -- --nocapture`
  - 4 passed.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml`
  - Passed after the webview build finished. A parallel run during Vite's
    hashed-asset rewrite briefly failed because Tauri tried to embed an asset
    name that Vite had just replaced; rerunning after build stabilization
    passed.
- `npm --prefix tauri/ui test -- --run tests/learn/test_ws_client_tauri_bridge.spec.ts tests/learn/test_learn_window_label.spec.ts tests/learn/test_beginner_path_contract.spec.ts`
  - 5 passed.
- `uv run pytest -q tests/learn/test_ws_beginner_path.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_runtime_evidence_grounding.py`
  - 27 passed, 96 warnings.
- `uv run pytest -q tests/state tests/learn tests/ipc/test_learn_envelope_parity_p92.py`
  - 1210 passed, 4 skipped, 67 warnings.
- `uv run pytest -q tests/state/test_refresh.py tests/learn/test_course3_no_exemplar_during_live.py tests/learn/test_no_speculative_phrase.py`
  - 60 passed.
- `uv run pytest -q tests/test_main_smoke.py tests/coach/test_main_anti_slop_wiring.py`
  - 43 passed.
- `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts tests/settings/library-panel.spec.ts tests/settings/staleness-banner.spec.ts`
  - 24 passed.
- `npm --prefix tauri/ui test -- --run tests/learn/test_beginner_path_contract.spec.ts tests/session/render-loop-actions.spec.ts`
  - 5 passed.
- `npm --prefix tauri/ui test -- --run tests/learn tests/session`
  - 293 passed, 1 skipped, 3 todo; 2 test files skipped.
- `npm --prefix tauri/ui run build`
  - Passed with existing Vite warnings about `SettingsDrawer` chunking and large
    chunks.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/check_ipc_schema.py`
  - Passed: 78 dataclasses validate, 78 `oneOf` entries match.
- `bash -n scripts/smoke/sidecar_bundle_smoke.sh`
  - Passed.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml`
  - Passed.
- `git diff --check`
  - Passed.
- Playwright live render check at `http://127.0.0.1:5187/learn.html`
  - First row is recommended, Course 2 row is locked, and the map banner says
    "screen deck is ready".

Passed:

- `uv run pytest -q tests/learn tests/ipc/test_learn_envelope_parity.py tests/ipc/test_learn_envelope_parity_p92.py tests/llm/test_model_router_learn_tutor.py`
  - 283 passed, 3 skipped, 20 warnings.
- `npm --prefix tauri/ui test -- --run tests/learn`
  - 138 passed.
- `npm --prefix tauri/ui run build`
  - Passed with existing Vite chunk warnings.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml`
  - Passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml learn_e2e -- --nocapture`
  - 2 passed.
- `node --check scripts/e2e/learn_launched_tauri_smoke.mjs`
  - Passed.
- `npm --prefix tauri/ui run test:e2e:learn:tauri`
  - Passed: launched Tauri Learn completed `L1.01` and quality checks through
    `:8765`, including the in-webview axe-core critical/serious WCAG gate.
- `npm --prefix tauri/ui test -- --run tests/learn/test_beginner_path_contract.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts tests/learn/test_practice_booth_shell.spec.ts`
  - 13 passed.
- `uv run pytest -q tests/learn/test_ws_beginner_path.py tests/learn/test_observer_boot_wiring.py tests/learn/test_prepared_pool.py`
  - 13 passed, 9 warnings.
- `npm --prefix tauri/ui run test:e2e:learn`
  - 8 passed.
- `npm --prefix tauri/ui audit --omit=dev`
  - Passed: 0 production vulnerabilities.
- `uv run ruff check tests/learn/test_course3_live_set_rehearsal.py tests/state/test_refresh.py tests/state/test_coach_course3_confidence_gate.py tests/runtime/test_suggestion.py`
  - Passed.
- `uv run pytest -q tests/learn/test_course3_live_set_rehearsal.py tests/state/test_refresh.py tests/state/test_coach_course3_confidence_gate.py tests/runtime/test_suggestion.py`
  - 109 passed.
- `uv run python scripts/discover_midi_port.py`
  - Passed: attached MIDI input port `DDJ-FLX4`.
- CoreAudio device probe via `sounddevice.query_devices()`
  - Passed: `DDJ-FLX4`, `BlackHole 16ch`, and `BlackHole 2ch` visible at
    48 kHz.
- `uv run python scripts/sniff_controller.py --port FLX4 --seconds 10`
  - Completed, but captured 0 MIDI frames.
- `uv run python scripts/sniff_controller.py --port FLX4 --seconds 18`
  - Completed, but captured 0 MIDI frames.
- `uv run ruff check tests/test_midi_macos_live.py`
  - Passed.
- `uv run pytest -q -m macos_audio tests/test_midi_macos_live.py`
  - Passed: the visible FLX4 resolves to `pioneer_ddj_flx4` through the live
    profile registry. The test enumerates MIDI ports in a subprocess after the
    earlier in-process `python-rtmidi` path aborted the pytest runner.
- `uv run ruff check tests/test_main_live.py`
  - Passed.
- `VIBEMIX_LIVE_SMOKE=1 uv run pytest -q -m macos_audio tests/test_main_live.py`
  - Passed: full live `python -m vibemix` startup stayed alive for the smoke
    window, handled SIGINT cleanly, and created a new app-data recording
    session.
- Rekordbox-open hardware probe on 2026-05-28:
  - `DDJ-FLX4` visible as a MIDI input, Rekordbox 7 running, FLX4 plus
    BlackHole devices visible to CoreAudio.
  - `uv run python scripts/sniff_controller.py --port FLX4 --seconds 20 --mode callback`
    opened the FLX4 input while Rekordbox was running, captured 0 frames.
  - `uv run python scripts/sniff_controller.py --port FLX4 --seconds 60 --mode callback`
    also opened the FLX4 input while Rekordbox was running, captured 0 frames.
    This proves the port is attachable in the Rekordbox-open setup, but not a
    physical movement pass.
  - `VIBEMIX_LIVE_SMOKE=1 uv run pytest -q -m macos_audio tests/test_main_live.py`
    initially failed because `MacBook Pro Speakers` was currently 44.1 kHz and
    the silent passthrough stream required 48 kHz. After the passthrough
    native-rate/resample patch, the same live smoke passed.
- `uv run ruff check src/vibemix/platform/_audio_macos.py tests/test_audio_macos.py`
  - Passed.
- `uv run pytest -q tests/test_audio_macos.py`
  - Passed: 15 tests.
- `uv run pytest -q tests/test_audio_macos.py tests/test_audio_macos_live.py -m 'not slow'`
  - Passed: 15 passed, 3 live xpasses on this configured Mac.
- `uv run ruff check tests/learn/test_live_flx4_learn_jog.py`
  - Passed.
- `uv run pytest -q tests/learn/test_live_flx4_learn_jog.py`
  - Passed by default skip: the deliberate hardware discharge requires
    `VIBEMIX_LIVE_LEARN_JOG=1` plus a left-jog nudge during the sniff window.
- `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_keyboard_nav_order.spec.ts tests/learn/test_keyboard_skip_reachable.spec.ts tests/learn/test_progress_list.spec.ts`
  - Passed: 35 tests.
- `npm --prefix tauri/ui test -- --run tests/learn`
  - Passed: 142 tests.
- `npm --prefix tauri/ui run build`
  - Passed.
- Re-run after the screen-action copy/fitting polish:
  - `npm --prefix tauri/ui test -- --run tests/learn`
    - Passed: 142 tests.
  - `npm --prefix tauri/ui run build`
    - Passed.
- Browser-outbound fallback slice:
  - `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts`
    - Passed: 14 tests.
  - `npm --prefix tauri/ui test -- --run tests/learn/test_ws_client_tauri_bridge.spec.ts tests/learn/test_ws_client_uses_8765.spec.ts`
    - Passed: 3 tests.
  - `npm --prefix tauri/ui test -- --run tests/learn`
    - Passed: 143 tests.
  - `npm --prefix tauri/ui run build`
    - Passed.
  - `npm --prefix tauri/ui run test:e2e:learn`
    - Passed: 9 tests, including browser plus Python sidecar L1.01 completion
      through both the Tauri-style forwarder and the direct browser WebSocket
      fallback.
- Stale RED-state/stub-label cleanup:
  - `rg -n "RED-state|awaits Plan|awaiting Plan|This file is a STUB|Downstream plan that flips|skip flips|it\\.todo|stub-only|FAILS RED" tests/learn tauri/ui/tests/learn`
    - Passed: no matches.
  - `uv run pytest -q tests/learn -rs`
    - Passed: 364 passed, 1 skipped, 117 warnings. The skip is the deliberate
      opt-in live FLX4 jog proof.
  - `npm --prefix tauri/ui test -- --run tests/learn`
    - Passed: 143 tests.
  - Focused post-cleanup regression run:
    - `npm --prefix tauri/ui test -- --run tests/learn/highlight-latency.test.ts tests/learn/highlight-paint.test.ts tests/learn/test_all_11_svgs_present.spec.ts tests/learn/test_aria_labels_present.spec.ts tests/learn/test_dual_cue_slots_present.spec.ts tests/learn/test_generic_fallback.spec.ts tests/learn/test_learn_window_label.spec.ts tests/learn/test_min_dwell_aria.spec.ts tests/learn/test_keyboard_nav_order.spec.ts tests/learn/test_hud_progress_dots_keyboard.spec.ts tests/learn/test_tutor_speak_sr_announcement.spec.ts tests/learn/test_sr_announcement.spec.ts tests/learn/test_keyboard_skip_reachable.spec.ts`
      - Passed: 54 tests.
    - `uv run pytest -q tests/learn/test_load_audio_stereo.py tests/learn/test_exemplar_player.py tests/learn/test_advancement_gates.py tests/learn/test_lesson_runtime_smoke.py tests/learn/test_progress_persistence.py tests/learn/test_midi_mirror_unit.py tests/learn/test_band_share_store.py tests/learn/test_exemplar_finder.py tests/learn/test_exemplar_kick_guard.py tests/learn/test_compute_band_shares.py tests/learn/test_prompts.py tests/learn/test_recital.py tests/learn/test_exemplar_lesson.py tests/learn/test_tutor_system_instruction_lock.py tests/learn/test_no_new_ws_port.py`
      - Passed: 87 tests, 14 warnings.
- Runtime warning cleanup:
  - `uv run ruff check src/vibemix/learn/runtime.py`
    - Passed.
  - `uv run pytest -q tests/learn/test_advancement_gates.py tests/learn/test_lesson_runtime_smoke.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_progress_persistence.py tests/learn/test_physical_controller_pipeline.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_teaching_loop.py tests/learn/test_ws_beginner_path.py -W error::DeprecationWarning`
    - Passed: 68 tests.
  - `uv run pytest -q tests/learn -rs`
    - Passed: 364 passed, 1 skipped, no warnings. The skip is the deliberate
      opt-in live FLX4 jog proof.
- `uv run ruff check src/vibemix/learn/runtime.py tests/learn/conftest.py tests/learn/test_progress_persistence.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_lesson_runtime_smoke.py`
  - Passed.
- `uv run pytest -q tests/learn`
  - Passed: 364 tests.
- `npm --prefix tauri/ui test -- --run tests/learn`
  - Passed: 141 tests.
- `npm --prefix tauri/ui run build`
  - Passed.

Failed or incomplete:

- `uv run pytest -q`
  - Failed during collection because `jinja2` is missing for
    `tests/e2e/macbook/render_report.py`.
- No real controller ear-pass was run.
- Real hardware is partially proven: the OS sees the FLX4 MIDI/audio devices
  and profile resolution passes, callback sniffing has captured FLX4 jog CC33
  frames, and a deterministic pipeline test proves the raw CC33 byte shape
  reaches the L1.07 Learn verifier. With Rekordbox 7 open, the FLX4 MIDI port
  is still attachable by the callback sniffer, but the latest 20 s and 60 s
  sniff windows captured no frames because no physical movement was observed.
  The remaining proof is still a deliberate live app lesson pass with the user
  actually moving controls; an opt-in test now encodes that discharge as
  `VIBEMIX_LIVE_LEARN_JOG=1 uv run pytest -q -m macos_audio tests/learn/test_live_flx4_learn_jog.py`.
- A frontend beginner-path contract now covers main LEARN click -> Learn open
  command -> recommended lesson start -> screen ACK -> next recommendation.
- A Python sidecar dispatch contract now covers `L1.01` start -> continue beats
  -> runtime finish -> persisted progress.
- A real WebSocket bus contract now covers `L1.01` start and continue ACKs over
  `ws_broadcast` -> terminal Learn envelopes -> persisted progress on an
  ephemeral port.
- A Playwright browser-plus-Python contract now covers `learn.html` ->
  Tauri invoke shim -> real `ws_broadcast` Learn runtime -> four authored
  `L1.01` beats -> completed progress -> next recommendation (`L1.02`).
- `headphone_cue`, `master_vol`, and `lesson_continue` are explicitly
  screen-only in structured verification metadata, with profile-grounded tests
  proving no bundled physical mapping currently exists and UI fallback tests for
  both `headphone_cue` and `master_vol`.
- EQ-as-tutor no longer depends on a mocked degraded path: an empty user library
  now falls through the real finder to packaged self-authored WAV exemplars, and
  the installed bank is covered by layout, attribution, hash, decode, and wheel
  packaging tests. The old honest-null degraded path still exists if a packaged
  install is damaged.
- Course 3 no longer preserves stale count-in fields, and the live refresh loop
  now consumes the same cache-warm Rekordbox library used by deck polling. When
  the audible deck, playhead, and a DJ-authored cue section all resolve, refresh
  writes `phrase_position_confidence`, `next_phrase_at`, and a stable
  change-only `cue` anchor for the coach. When only fallback sections exist,
  live Course 3 remains retrospective-only by construction. A deterministic
  mini-set rehearsal now proves that cue-anchored count-in evidence, the coach
  eligibility marker, saved-pool next-track targeting, and graceful off-pool
  deviation feedback work together through the runtime seams.
- L3.02 now has real prepared-pool awareness instead of product copy pretending
  a pool was loaded. The runtime reads the latest saved playlist/set-prep JSON
  artifact, requires five valid track rows, ignores corrupt artifacts, names the
  first two tracks in the tutor dock, and emits a `[track:]` citation only when
  the shared registry resolves it.
- The saved pool also reaches the existing next-suggestion engine. If the
  current audible track appears in the latest pool, the following pool row is
  considered as a soft target; it is promoted only with transition evidence and
  does not trigger the strict prepared-target suppression path unless it is the
  selected grounded suggestion.
- Ordinary Learn practice evidence is now registry-backed: highlights, matched
  actions, and adaptive mismatch hints write `screen`/`midi` observations, and
  time-keyed MIDI hint citations are validated by the same `CitationLinter`
  grammar used by the co-host.
- The new citation grammar no longer leaks raw registry syntax into the tutor
  dock: citation chips strip `@time` and translate known controls to deck-facing
  labels.
- Learn contrast is no longer just a skipped/TODO placeholder: token-level
  WCAG checks now cover silk, silk-65, amber/status LEDs, citation chips, the
  tutor dock, and amber/warning cue highlights. A Playwright Chromium pass also
  verifies computed browser contrast on `learn.html`; a dependency-free
  Playwright accessibility pass checks names, duplicate IDs, SVG control
  semantics, and `aria-hidden` focus traps; and an axe-core Playwright pass now
  fails on critical/serious WCAG violations. The launched Tauri smoke injects
  the same local axe-core bundle into the real Learn WebviewWindow. That real
  gate caught the root-SVG `nested-interactive` issue, so the schematic SVGs are
  now neutral containers and their child controls own the button semantics. A
  browser motion pass still asserts fader thumbs translate on the real Learn
  page without rotating parent control groups.
- The browser and Python Learn runtime are now proven together outside Tauri,
  and a launched Tauri smoke now proves `open_learn_window`, the Learn
  WebviewWindow, the production Learn buttons, Rust `forward_ipc_to_sidecar`,
  and the Python Learn runtime together through `:8765`. The smoke deliberately
  uses an external test sidecar because the full live sidecar boots audio
  hardware and macOS has no official Tauri WKWebView WebDriver path.
- The browser-only practice booth no longer depends on a Tauri invoke shim for
  outbound Learn actions. Tauri IPC remains the production first path, but if
  `emitIpc` is unavailable the Learn window now queues the same `ipc.learn.*`
  envelope onto the existing `:8765` socket and flushes it when the direct
  browser WebSocket opens. This covers progress snapshots, recommended lesson
  starts, screen-deck ACKs, and skip ACKs without adding another socket or
  bypassing the Learn schema envelope.
- The Learn test surfaces no longer describe live assertions as RED-state
  stubs. A search for stale plan-awaiting phrases, `it.todo`, and `stub-only`
  under `tests/learn` and `tauri/ui/tests/learn` is now clean, so future agents
  should not mistake implemented contracts for dormant TDD placeholders. The
  one remaining Python skip in the full Learn suite is the deliberate opt-in
  live FLX4 jog proof.
- Learn's Python suite no longer emits the `python-statemachine`
  `current_state` deprecation flood. `LessonRuntime` now owns a small
  compatibility property that returns the same state object as
  `runtime.current_state.id` callers expected, backed by
  `current_state_value` internally. The full `tests/learn` run now reports no
  warnings; only the opt-in live FLX4 jog test skips.
- The static Tauri Learn launch contract is now pinned across Rust source,
  frontend tests, and capabilities: `open_learn_window` is registered,
  `learn.html` is the hardcoded webview URL, and the `learn` window label is in
  `capabilities/default.json`. This reduces launch drift risk, while the
  launched smoke is now the process proof for the Learn window/bridge path.
- The Rust outbound bridge now has a real-socket proof for the Learn ACK path:
  a delayed managed sink receives an `ipc.learn.ack` through the same forwarding
  helper used by `forward_ipc_to_sidecar`. This complements the launched smoke
  instead of standing in for it.
- The 36-lesson chooser mirror is now contract-tested against the Python
  curriculum, and started-but-unfinished lessons now persist as in-progress
  rows. Timed hint strikes persist too, so resume/debrief/profile adaptation no
  longer loses the learner's struggle if the app exits before completion. The
  recommended path now resumes an in-progress lesson before suggesting the next
  untouched row, and completed lessons can be replayed from the map even when
  their course gate is otherwise locked.
- The observe -> decide -> teach -> verify -> adapt backstage loop is now a
  pure, test-covered module rather than an implied behavior scattered across
  runtime callbacks. It proves every beginner step can become a teaching turn,
  that normal/hint/adaptive turns share the same deterministic verification
  ground, and that tutor routing goes through `model_router` instead of a model
  literal. Remaining honest gap: no live generative tutor call is made, by
  design, because the current safe voice path is authored fixture copy plus
  deterministic adaptive hints.
- The Course 3 live lens now reaches the real Learn app path, not only a probe
  script. The Rust websocket bridge routes flat `course3_lens` frames to a
  Learn-specific Tauri event, the browser fallback extracts the same field from
  `ws://127.0.0.1:8765`, and the practice-booth status rail reduces the signal
  to one quiet phrase: `listening for phrase` or `phrase cue locked`. This keeps
  the frontstage simple while making cue-backed Course 3 readiness visible.
- L3.06 no longer blind-claims that the debrief is open or that a profile
  exists. `vibemix.learn.graduation` now reads real Learn progress, profile
  consent/profile storage, and the latest persisted debrief, then emits one
  concise status line. When an `EvidenceRegistry` is wired, the line cites
  registry-backed `screen` facts for progress/debrief/profile presence.
- Real FLX4 controller bring-up is materially better than the inherited state,
  but still needs a hands-on pass. The macOS live port probe resolves the
  attached `DDJ-FLX4` profile, and the full `python -m vibemix` live-start smoke
  now boots against the configured audio/MIDI environment and shuts down cleanly,
  including a Rekordbox-open setup where the selected MacBook speaker output is
  44.1 kHz.
  The old poll-only MIDI diagnostic saw zero frames, while callback mode captured
  real FLX4 jog-wheel CC33 frames on channels 0/1 (`63`/`65` ticks). The
  production MIDI listener is now callback-first with a poll fallback, and the
  FLX4 profile maps those CC33 ticks as a `relative` jog axis. Learn mirrors the
  relative movement as a one-frame `jog:<deck>` pulse over a neutral baseline,
  aliases it to the existing platter hit-region, and verifies it through the same
  deterministic `min_delta` gate as the on-screen jog. A deterministic
  controller-pipeline test now starts from the raw FLX4 byte shape
  (`control_change channel=0 control=33 value=65`) and proves it reaches
  `ControllerState`, `MidiMirror`, a UI-shaped `ipc.learn.ack`, and the L1.07
  lesson verifier. The webview also ACKs a first-seen jog pulse even if the
  user nudges the wheel before a baseline `0` frame arrives. Latest caveat: a
  follow-up 12-second callback sniff captured zero frames because no control
  movement occurred during that window, so the next proof should be an
  intentional live L1.07 jog-wheel lesson pass with someone nudging the
  controller.
- A sixty-sixth slice turns the live DDJ proof from "visible hardware" into a
  strict Learn lesson artifact. The readiness preflight now accepts the real
  state of this Mac: `DDJ-FLX4` can be visible via MIDI and CoreAudio even when
  `system_profiler SPUSBDataType` misses the USB brand row. The physical proof
  runner loaded L1.07 on the real `:8765` sidecar, observed a live `jog:A`
  position pulse, sent the UI-shaped ACK, saw the lesson advance, and validated
  `/tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json` with
  `--require physical`. Focused proof: readiness ruff passed; readiness tests
  passed 11; the live physical artifact validator passed.
- A sixty-seventh slice hardens Course 3 proof startup without mutating real
  learner progress. The Course 3 lens probe can now start L3.01 before watching
  lens frames, and the proof runner can seed an isolated v2 progress file with
  Course 2/3 unlocked via `--seed-course3-unlocked`. This fixed the earlier
  `L3.01 is locked` false negative; later failures now mean live evidence is
  missing, not that the proof could not start the lesson. Focused proof:
  `uv run ruff check scripts/live_course3_lens_probe.py tests/runtime/test_live_course3_lens_probe.py scripts/run_learn_live_proof.py tests/learn/test_run_learn_live_proof.py`
  passed, and
  `uv run pytest -q tests/runtime/test_live_course3_lens_probe.py tests/learn/test_run_learn_live_proof.py`
  passed 14.
- A sixty-eighth slice fixes the real rig's BlackHole routing problem and adds
  a reusable auto master-input finder. The factory default remains
  `BlackHole 2ch`, but `VIBEMIX_INPUT_DEVICE` can now override device names at
  boot, explicit variants such as `BlackHole 16ch` are honored, and
  `VIBEMIX_AUTO_MASTER_INPUT=1` briefly samples loopback/capture inputs,
  excludes microphones/controllers, chooses the live signal when present, and
  falls back to a 48 kHz BlackHole variant before the 44.1 kHz exact 2ch
  device. On this rig, direct probing selected `BlackHole 16ch @ 48000Hz`.
  The subsequent Course 3 proof no longer failed on silence or sample-rate
  crash: it started, heard audio, and loaded L3.01. It still failed correctly
  because the captured now-playing source was system/podcast audio and the deck
  attribution stayed `deck=none`, so no citable Rekordbox cue chain existed.
  Focused proof:
  `uv run ruff check src/vibemix/agent/config.py src/vibemix/platform/_audio_macos.py scripts/run_learn_live_proof.py tests/test_audio_macos.py tests/learn/test_run_learn_live_proof.py`
  passed, and
  `uv run pytest -q tests/test_audio_macos.py tests/learn/test_run_learn_live_proof.py`
  passed 27.
- A sixty-ninth slice fixes a mobile Learn shell overflow found by a live
  Playwright screenshot pass. At 390 px wide, the root bands fit the viewport
  and the booth panel no longer creates horizontal overflow. A new Chromium
  contract, `tauri/ui/tests/learn/browser-responsive.pw.ts`, asserts root,
  titlebar, stage, status bar, footer, booth, and primary actions remain inside
  the mobile viewport. Focused proof: `npm --prefix tauri/ui test -- --run
  tests/learn/test_practice_booth_shell.spec.ts` passed 15 and `cd tauri/ui &&
  npx playwright test -c tests/learn/playwright.config.ts
  tests/learn/browser-responsive.pw.ts` passed. The full Learn Playwright
  suite now passes 10 tests, and `npm --prefix tauri/ui run build` passes.
- A seventieth slice makes failed Course 3 proof artifacts explain the missing
  backstage evidence instead of merely saying the lens stayed cold. The flat
  socket's `deck_state` rows now include `track_id` so a probe can tell whether
  the app has a citable deck row, and `scripts/live_course3_lens_probe.py`
  records the surrounding flat-frame context: max music level, audible flag,
  non-`none` deck values, deck-state presence, citable deck-state presence, and
  blockers such as `audible deck stayed none` or `deck_state stayed empty`.
  `scripts/validate_learn_live_proof.py` surfaces those blockers as validation
  errors. This does not loosen Course 3: count-in proof still requires active
  Course 3 plus a cue-backed next phrase. It makes the next live run actionable.
  Focused proof: the touched ruff bundle passed, and the live-proof/socket
  focused pytest bundle passed 64 tests.
- A seventy-first slice makes the Course 3 lens itself carry honest readiness
  rather than forcing every consumer to reconstruct state from nearby socket
  fields. `course3_lens` keeps the original four keys and adds
  `audio_active`, `deck_attributed`, `deck_track_citable`, `cue_ready`, and
  stable blocker codes (`waiting_for_audio`, `waiting_for_deck`,
  `waiting_for_deck_track`, `waiting_for_cue`). The Learn status rail translates
  those into one quiet phrase: `waiting for deck`, `waiting for track`,
  `listening for phrase`, or `phrase cue locked`. The probe now records
  machine-readable lens blockers too. Focused proof: the touched Python ruff
  bundle passed; `uv run pytest -q tests/runtime/test_ws_bus_course3_lens.py
  tests/runtime/test_live_course3_lens_probe.py
  tests/learn/test_validate_learn_live_proof.py` passed 23; the broader
  live-proof/audio bundle passed 66; the focused Learn Vitest bridge/status
  bundle passed 22; `npm --prefix tauri/ui run test:e2e:learn` passed 10; and
  `npm --prefix tauri/ui run build` passed.
- A seventy-second slice fixes a frontstage verification bug found by that full
  Playwright sweep: the screen `lesson_continue` control was toggling, so the
  second click emitted an `up` action and L1.01 stalled on the second authored
  line. On-screen button actions now emit every click as a fresh down press.
  The browser plus Python sidecar path proves the four-line opening dialog
  through both the Tauri-style forwarder and direct browser WebSocket fallback.
- A seventy-third slice closes a Course 3 proof-runner false green. Static
  readiness could say Course 3 was ready because the sidecar, FLX4, Rekordbox,
  and BlackHole devices existed, even though the live lens later showed
  `deck=none`. `learn_live_readiness.py --require course3` and
  `run_learn_live_proof.py --course3` now sample live flat socket frames when
  the sidecar is up and require audible master audio, deck attribution to `A`,
  `B`, or `mix`, and a citable `deck_state.track_id` row before calling the
  Course 3 proof path ready. This still does not pass Course 3 count-in proof
  by itself; it prevents spending a 60-second proof window on generic system
  audio. Focused proof: the readiness/runner ruff bundle passed, the
  readiness/runner pytest bundle passed 24, the broader live-proof/audio bundle
  passed 70, and both readiness/proof runner help commands advertise the new
  live-context options.
- A seventy-fourth slice makes failed/skipped proof artifacts carry their real
  blockers through validation. `validate_learn_live_proof.py` now extracts
  blockers from direct readiness results, wait-loop `last` readiness results,
  and nested `checks.course3_live_context` objects, then emits errors like
  `course3 readiness: live deck_state has no citable track_id at confidence
  floor` instead of only `course3_probe skipped`. The validator still accepts
  explicitly allowed skipped requirements only when blockers are recorded.
  Focused proof: validator ruff passed, validator pytest passed 12, and the
  broader live-proof/audio bundle passed 72.
- A seventy-fifth slice fixes the live-context sampler inside the async proof
  runner. The readiness helper originally used `asyncio.run`, which works from
  the standalone CLI but fails inside `run_learn_live_proof.py`'s running event
  loop and reduced Course 3 readiness to a generic `could not read live sidecar
  context`. The helper now runs the socket sample directly in CLI contexts and
  uses a short helper thread with its own event loop when called from an active
  loop. The fresh artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-live-context-current.json` proves
  the gate now samples real frames: 43 flat frames, `music=0.0`, `audible=false`,
  `deck=none`, `deck_state={}`, and explicit lens blockers. Focused proof:
  readiness/runner/validator ruff passed, the focused pytest bundle passed 37,
  the broader live-proof/audio bundle passed 73, and direct artifact validation
  fails with actionable Course 3 readiness errors.
- A seventy-sixth slice removes two proof-rig false signals before handing off
  integration. First, sidecar readiness now opens the app with a real WebSocket
  handshake instead of a raw TCP connect, so socket readiness proves the
  protocol and no longer prints invalid-handshake tracebacks in app stderr.
  Second, proof validation now checks `app_start`/`app_stop` whenever those
  stages are present, even when the caller requested no screen/physical/Course
  3 probe. That closes the false-green path where `--start-app --no-screen`
  could pass despite an audio-start failure. Focused proof: readiness ruff
  passed, readiness pytest passed 17, readiness+validator ruff passed,
  readiness+validator pytest passed 31, and the broader live-proof/audio bundle
  passed 77. The smoke artifact
  `/tmp/vibemix-live-learn-proof/proof-socket-handshake-current.json` reports
  `app_start=passed`, `app_stop=passed`, socket `protocol=websocket`, and no
  invalid HTTP handshake noise in captured app stderr; `git diff --check`
  passed and no `8765`/`5188` listeners remained afterward.
- A seventy-seventh slice makes future course integration less brittle without
  adding frontstage complexity. Python now owns a `COURSE_REGISTRY` carrying
  course labels, HUD labels, unlock gates, lock reasons, and the beginner flag.
  The frontend lesson chooser projection is generated from Python by
  `src/vibemix/learn/curriculum_projection.py` and
  `scripts/export_learn_curriculum_meta.py`; the checked-in
  `tauri/ui/src/learn/lesson/curriculum-meta.ts` is now a generated projection,
  and the Learn HUD reads generated labels for beginner courses while keeping
  Course 0/legacy alias fallbacks. This turns "add a course" from a hand-sync
  trap into "add registry metadata + lessons, run `npm --prefix tauri/ui run
  codegen:learn`, and let tests catch drift." Focused proof: the registry/codegen
  ruff bundle passed, the Python curriculum/IPC/progress bundle passed 91,
  `npm --prefix tauri/ui run check:learn-curriculum` passed, the Learn Vitest
  curriculum/HUD bundle passed 9, the broader Learn skill-tree/runtime bundle
  passed 64, `npm --prefix tauri/ui run build` passed, and `git diff --check`
  passed.
- A seventy-eighth slice turns the optional lesson map from a hidden syllabus
  wall into a calm course accordion. The practice-booth frontstage remains one
  recommended action plus `choose lesson`; opening the map now expands only the
  current/recommended course, collapses other courses into summaries, and lets
  the user expand any course to jump or replay. Keyboard movement scopes to
  visible lesson rows, locked lessons stay non-startable, and course summaries
  refresh when completion status changes. This preserves graceful lesson choice
  without making the beginner read 36 rows at once. Focused proof: the
  progress-list/curriculum/HUD Vitest bundle passed 32, the practice-booth shell
  bundle passed 15, the responsive/accessibility Playwright subset passed 4,
  the full Learn Vitest suite passed 149, `npm --prefix tauri/ui run
  test:e2e:learn` passed 10, `npm --prefix tauri/ui run build` passed, and
  `git diff --check` passed.
- A seventy-ninth slice makes the backstage teaching loop visible on the socket
  without adding frontstage weight. `ipc.learn.tutor_speak` can now optionally
  carry `teaching_loop` metadata: stages, turn kind, model-router route path,
  observation context, and the deterministic verification contract for the
  lesson step. Runtime step beats, timed hints, and adaptive mismatch hints
  attach it when they resolve to a structured step; older and non-step tutor
  lines omit the field entirely. This gives integration tooling an auditable
  observe -> decide -> teach -> verify -> adapt trail while the beginner still
  sees one simple coaching line. Focused proof: the touched Python ruff bundle
  passed; `tests/learn/test_teaching_loop.py` plus
  `tests/ui_bus/test_messages_schema.py` passed 93; `npm --prefix tauri/ui run
  check:ipc` passed; the broader Learn runtime/schema bundle passed 170;
  `scripts/check_ipc_schema.py` passed with 78 wrappers and 78 schema oneOf
  entries; `npm --prefix tauri/ui run build` passed; and `git diff --check`
  passed.
- An eightieth slice makes the auto-master live proof artifact machine-readable
  instead of burying the selected input in app stderr. The proof runner now
  parses `[audio] auto master input: ...` startup lines and copies the runtime
  selection into both `app_start.result.audio_runtime` and
  `app_stop.result.audio_runtime`. The fresh live artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-auto-master-structured.json`
  shows app start/stop and WebSocket startup passing, with auto master selecting
  `BlackHole 16ch @ 48000Hz` as a `48k_fallback` and `live_signal=false`.
  Course 3 still failed correctly because master audio stayed silent,
  attribution stayed `deck=none`, and `deck_state` had no citable `track_id`.
  A direct `sounddevice.playrec` pulse through `BlackHole 16ch` at 48 kHz did
  record signal (RMS about `0.029`), so BlackHole itself is not the failed link;
  real Rekordbox master playback still needs to be routed into that device.
  Focused proof: run-proof ruff passed; the runner contract passed 13 tests;
  the broader live-proof/readiness/audio bundle passed 62 tests; the short live
  artifact run produced the structured audio runtime fields; and
  `git diff --check` passed.
- An eighty-first slice makes Course 3 readiness route-aware without weakening
  live-context proof. `learn_live_readiness.py` now records an `audio_route`
  diagnostic from `SwitchAudioSource`, including current macOS output/system
  devices and loopback matches. If Course 3 live context is silent and the
  default route is not loopback, that mismatch becomes an actionable blocker;
  if live context is already good, the route check remains diagnostic only.
  On this rig, output and system audio were set to `BlackHole 16ch`, and the
  fresh artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-route-aware-current.json`
  shows `audio_route.ok=true` plus app auto-master selection of
  `BlackHole 16ch @ 48000Hz`. Course 3 still fails correctly because no live
  master audio reaches the sidecar, deck attribution stays absent, and no
  citable `deck_state.track_id` appears. Focused proof: route-aware readiness
  ruff passed; the live readiness command reports output/system
  `BlackHole 16ch`; the short proof artifact includes both route and
  auto-master diagnostics; the live-proof/readiness/audio pytest bundle passed
  65; and `git diff --check` passed.
- An eighty-second slice adds direct loopback signal proof to the Course 3
  readiness path. `learn_live_readiness.py` now supports
  `--loopback-signal-seconds`, chooses the selected loopback input, samples it
  directly, and reports device index, sample rate, channels, RMS, peak, and the
  RMS floor. `run_learn_live_proof.py` forwards the same option so artifacts
  can distinguish "correctly routed but no signal" from "sidecar/deck
  attribution failed." The fresh artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-loopback-signal-current.json`
  shows output/system route `BlackHole 16ch`, app auto-master selection
  `BlackHole 16ch @ 48000Hz`, but direct capture silence (`rms=0.0`,
  `peak=0.0`). Course 3 remains honestly failed: no live master audio, no deck
  attribution, no citable deck track, and now a clear `direct loopback capture
  is silent` blocker. Focused proof: readiness/proof ruff passed; the
  live-readiness plus runner tests passed 38; the broader
  live-proof/readiness/audio bundle passed 70; the short live artifact recorded
  the signal check; and `git diff --check` passed.
- An eighty-third slice turns that direct loopback check into a real proof
  wait gate. `run_learn_live_proof.py` now supports
  `--wait-loopback-signal-seconds`; when Course 3 is requested, the runner adds
  a `loopback_signal_wait` stage that polls direct capture RMS/peak before the
  live lens proof. This lets an operator start Rekordbox playback during the
  window and gives the artifact a precise answer about whether the run failed
  before routed signal ever existed. The fresh artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-loopback-wait-current.json`
  shows app startup/WebSocket/auto-master selection passing, but the wait stage
  sampled `BlackHole 16ch` twice and still recorded `rms=0.0`, `peak=0.0`.
  Course 3 remains honestly failed with blockers for silent loopback, no live
  audio, no deck attribution, and no citable deck track. Focused proof: runner
  ruff passed; runner contracts passed 16; the broader live-proof/readiness
  audio bundle passed 72; the short live artifact recorded the wait stage; and
  `git diff --check` passed.
- An eighty-fourth slice adds a full capture matrix so Course 3 artifacts can
  distinguish "wrong selected input" from "no playback on any relevant input."
  `learn_live_readiness.py` now supports `--capture-matrix-seconds`, sampling
  and ranking DJ/controller/loopback inputs by RMS/peak, and the proof runner
  forwards that option into readiness and wait stages. The fresh artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-capture-matrix-current.json`
  sampled `DDJ-FLX4`, `rekordbox Aggregate Device`, `BlackHole 16ch`, and
  `BlackHole 2ch`; every row stayed below the `0.003` RMS floor. FLX4 and
  rekordbox Aggregate only show tiny noise around `0.000175`, and both
  BlackHole inputs remain `0.0`. This proves the current blocker is not merely
  auto-master choosing the wrong input; no sampled capture path has real
  playback yet. Focused proof: readiness/runner ruff passed; readiness plus
  runner tests passed 44; the broader live-proof/readiness/audio bundle passed
  76; the short live artifact recorded the capture matrix; and
  `git diff --check` passed.
- An eighty-fifth slice adds a loopback route self-test so the Course 3 proof
  can separate "BlackHole is broken" from "external playback is absent."
  `learn_live_readiness.py` now supports `--loopback-self-test-seconds`, which
  emits a quiet known tone through the selected duplex loopback device and
  captures it back. `run_learn_live_proof.py` forwards the same option. The
  fresh artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-loopback-self-test-current.json`
  proves `BlackHole 16ch` itself is healthy (`rms≈0.0249`, `peak≈0.0505` from
  the injected tone) while passive loopback capture remains silent and the
  capture matrix still has no signal row. Course 3 remains honestly failed, but
  the blocker is now sharply located: real Rekordbox/deck playback is not
  reaching any sampled capture path. Focused proof: readiness/runner ruff
  passed; readiness plus runner tests passed 49; the broader
  live-proof/readiness/audio bundle passed 81; the short live artifact recorded
  the self-test; and `git diff --check` passed.
- An eighty-sixth slice makes those Course 3 audio diagnostics stable and
  machine-readable. `learn_live_readiness.py` now emits
  `course3_audio_diagnosis` with a code, severity, message, and next action,
  derived from the route, loopback self-test, passive loopback, capture matrix,
  and live socket context without loosening proof semantics. The current rig
  reports `loopback_route_healthy_external_playback_absent`: the selected
  `BlackHole 16ch` route captures an injected tone, but no sampled DJ/loopback
  input has real playback. The fresh artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-diagnosis-current.json` carries
  that code in both pre-probe readiness and the skipped Course 3 probe. Focused
  proof: readiness/runner ruff passed; readiness plus runner tests passed 50;
  the broader live-proof/readiness/audio bundle passed 82; the short live
  artifact recorded the diagnosis code; and `git diff --check` passed.
- An eighty-seventh slice adds a capture-signal wait gate to the Course 3 proof
  runner. `run_learn_live_proof.py` now supports
  `--wait-capture-signal-seconds`, which polls the full capture matrix before
  the live lens proof and passes as soon as any sampled DJ/loopback input
  crosses the signal floor. This is the complementary wait to
  `--wait-loopback-signal-seconds`: it can catch "audio exists, but on the
  wrong capture input" during the proof window. The fresh artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-capture-wait-current.json`
  shows the current rig still has no external playback on any sampled input,
  while the BlackHole self-test remains healthy and the diagnosis remains
  `loopback_route_healthy_external_playback_absent`. Focused proof: runner
  ruff passed; runner contracts passed 20; the broader
  live-proof/readiness/audio bundle passed 84; the short live artifact recorded
  both wait stages; and `git diff --check` passed.
- An eighty-eighth slice makes the packaged EQ exemplar audit a durable
  release artifact instead of a loose stdout check. `scripts/audition_learn_exemplars.py`
  now supports `--out`, emits schema version 2, carries per-track
  `integrity_passed`, `clip_free`, `non_silent`, `sample_rate_matches`, and
  `stereo` booleans, and reports bank-level `technical_failures`. The key
  distinction is explicit: `technical_passed=true` can coexist with
  `release_ready=false` while the human ear-pass is pending. The fresh artifact
  `/tmp/vibemix-live-learn-proof/learn-exemplar-audit-current.json` reports
  diagnosis `technical_audit_passed_ear_pass_pending` and all four packaged
  band loops passing objective integrity checks. Focused proof: exemplar audit
  ruff passed; exemplar audit/player/fallback tests passed 16; the `--out`
  artifact was written and inspected; and `git diff --check` passed.
- An eighty-ninth slice adds a course-pack integration audit so future Learn
  courses do not become another hand-synced Python/TypeScript chase.
  `src/vibemix/learn/curriculum_audit.py` and
  `scripts/audit_learn_curriculum.py` now emit a JSON report checking
  registry/frame parity, LessonMeta-to-transcript drift, required transcript
  fields, beginner flow compilation through `build_lesson_flow`, and generated
  frontend projection freshness. The fresh artifact
  `/tmp/vibemix-live-learn-proof/learn-curriculum-audit-current.json` reports
  `passed=true`, 36 beginner lessons, all beginner lesson flows compiling, no
  errors, and `frontend_projection.up_to_date=true`. Focused proof: curriculum
  audit ruff passed; audit/projection/lesson-flow tests passed 53; the audit
  artifact was written and inspected; and `git diff --check` passed.
- A ninetieth slice tightens the practice-booth frontstage and the authored
  Learn voice. `learn-window.ts` now optimistically updates local progress on
  `ipc.learn.complete_lesson`, re-renders the chooser, and moves the default
  booth action to the next lesson before the disk-backed snapshot arrives. This
  removes a save-gap where "start recommended" could still point at the lesson
  that just completed. The same pass removes em-dash punctuation from the
  first-controller announcement, progress-list aria labels, curriculum
  addenda, and transcript JSON, then adds a tutor-copy regression that rejects
  em/en dash sentence glue in live lesson fixtures. Focused proof: the
  practice-booth/first-launch/progress-list/beginner-path Vitest bundle passed
  45; the tone/curriculum prompt bundle passed 129; all-lesson flow traversal
  plus curriculum audit passed 86; design-slop/min-dwell/skip/tutor/bridge
  Vitest passed 14; `npm --prefix tauri/ui run test:e2e:learn` passed 10
  browser tests including axe, contrast, responsive, controller motion, and
  Python sidecar beginner-path coverage; `npm --prefix tauri/ui run build`
  passed; and `git diff --check` passed.
- A ninety-first slice turns the launched Tauri Learn smoke into a durable app
  wiring proof. `scripts/e2e/learn_launched_tauri_smoke.mjs` now accepts
  `--out` and writes a JSON artifact, while the Rust `learn_e2e` autorun checks
  the post-completion frontstage: after L1.01 completes, the real Learn
  WebviewWindow must show `start meet your controller` and keep the practice map
  hidden/opt-in. The fresh artifact
  `/tmp/vibemix-live-learn-proof/learn-tauri-smoke-current.json` reports
  `passed=true`, `l101_completed=true`, `quality_check_count=17`, no failures,
  and both next-lesson/opt-in-map checks passing through the launched Tauri app,
  Rust bridge, and Python sidecar on `127.0.0.1:8765`. Focused proof:
  `node --check` passed, Rust `learn_e2e` tests passed 2, the Tauri Learn smoke
  with `--out` passed, `cargo fmt --check` passed, no proof-run listeners
  remained on `8765`/`1420`, and `git diff --check` passed.
- A ninety-second slice makes the Course 3 audio blocker less dumb in the exact
  Rekordbox setup now on the desk. `learn_live_readiness.py` still keeps the
  stable diagnosis code `loopback_route_healthy_external_playback_absent`, but
  when BlackHole self-test passes, passive BlackHole capture is silent, and the
  capture matrix includes DJ/Rekordbox rows, it now attaches
  `rekordbox_route_hint`. The hint explicitly names the missing mental model:
  Rekordbox can bypass macOS output and use its own audio device, so setting
  macOS output to BlackHole is not enough proof. The fresh artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-route-hint-current.json` shows
  BlackHole 16ch self-test healthy, direct BlackHole capture silent, DDJ-FLX4
  and `rekordbox Aggregate Device` below signal floor, and the next action
  points to Rekordbox Audio preferences plus a real deck with channel/master
  faders up. The app-runner artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-route-hint-runner-current.json`
  proves the hint survives real app startup: sidecar socket ready, physical
  Learn readiness true, auto-master on BlackHole 16ch, and Course 3 skipped
  honestly with the same diagnosis. Focused proof: readiness ruff passed, the
  readiness contract test file passed 33 tests, the broader
  readiness/proof/validator bundle passed 67, the current rig artifacts were
  written, and the runner artifact validated with `--allow-skipped course3`.
- A ninety-third slice fixes a subtle Course 3 frontstage honesty bug. When a
  Course 3 live lens is active but routed master audio is still missing, the
  Learn status rail now says `waiting for audio` instead of falling through to
  `listening for phrase`. The route-heavy diagnosis stays backstage in the
  proof artifacts, while the user sees exactly one calm phrase plus an
  accessible label that says routed master audio is not audible yet. Focused
  proof: the practice-booth shell test passed 16, the Learn websocket bridge
  tests passed 7, the full Learn Vitest suite passed 150, the frontend build
  passed, and the browser Learn e2e gate passed 10 tests including axe,
  contrast, responsive, controller motion, and both Python sidecar modes. The
  launched Tauri smoke also passed after the change and wrote
  `/tmp/vibemix-live-learn-proof/learn-tauri-smoke-after-audio-wait.json`
  with 17 quality checks and no failures.
- A ninety-fourth slice adds the consolidated Learn package verifier:
  `scripts/verify_learn_package.py`. It gives future integration sessions one
  JSON verdict that separates deterministic package integrity from release
  readiness. The verifier joins the curriculum/course-pack audit, packaged EQ
  exemplar technical audit, launched Tauri smoke artifact, and live-proof
  artifact validation for screen, physical, and Course 3. The current artifact
  `/tmp/vibemix-live-learn-proof/learn-package-verification-current.json`
  reports `passed=true`, `technical_passed=true`, `release_ready=false`, 36
  beginner lessons, frontend projection up to date, Tauri smoke passing with 17
  quality checks, screen proof passed, physical proof passed, and Course 3
  unavailable on the route-hint runner. Its only completion blockers are the
  packaged EQ exemplar human ear-pass and Course 3 routed-audio count-in proof.
  Focused proof: verifier/audit ruff passed, the verifier/curriculum/exemplar/
  live-proof pytest bundle passed 28, the package artifact was written, and
  `--require-release-ready` exited 4 as intended.
- A ninety-fifth slice turns the packaged EQ exemplar ear-pass from a vague
  checklist item into a hash-bound artifact contract. `audition_learn_exemplars.py`
  can now write `learn-exemplar-ear-pass-current.json` with
  `--approve-ear-pass --approved-by <name>`, recording the exact current WAV
  hashes after a human listens. Future audits validate that approval against the
  current bank and reject stale or mismatched hashes, so regenerated examples
  cannot inherit an old approval. `verify_learn_package.py` auto-discovers that
  artifact under `/tmp/vibemix-live-learn-proof/` or accepts
  `--exemplar-approval`. The current package report still has
  `sections.exemplars.approval_path=null` and `release_ready=false` because no
  real human approval has been recorded. Focused proof: exemplar/verifier ruff
  passed, the exemplar/verifier tests passed 13, the broader
  verifier/curriculum/exemplar/live-proof bundle passed 32, the updated package
  artifact was written, and `--require-release-ready` still exits 4 with the
  honest remaining blockers.
- A ninety-sixth slice promotes the Course 3 audio diagnosis into the
  consolidated package verdict instead of leaving it buried in a runner
  attempt. `verify_learn_package.py` now extracts
  `course3_audio_diagnosis` from the Course 3 proof/readiness stages and
  exposes it at `sections.live_proofs.course3.diagnosis`; package-level
  `next_actions` now use that diagnosis's precise next action. The current
  package artifact therefore says exactly what the rig still needs:
  set Rekordbox Audio preferences to BlackHole 16ch or an aggregate that
  includes BlackHole, then play a deck with channel and master faders up.
  Focused proof: verifier ruff passed, verifier/exemplar tests passed 14, the
  broader verifier/curriculum/exemplar/live-proof bundle passed 33, the package
  artifact was refreshed, and `--require-release-ready` still exits 4 with the
  honest remaining blockers.
- A ninety-seventh slice makes the Course 3 route diagnosis specific to the
  Rekordbox state on disk without editing Rekordbox. `learn_live_readiness.py`
  now read-only parses
  `~/Library/Application Support/Pioneer/rekordbox6/rekordbox3.settings`,
  extracts the current `audioDeviceManager` output/input/rate/buffer/channel
  row plus recent performance rows, and passes that check through
  `course3_audio_diagnosis` and the raw readiness checks. When the loopback
  route self-test passes but external playback is absent, the next action now
  says the persisted Rekordbox output currently names `BlackHole 2ch` at
  `44100.0`, while the vibemix/macOS proof route is `BlackHole 16ch`; it asks
  the operator to align Rekordbox Audio preferences with `BlackHole 16ch` or an
  aggregate containing it before playing a real deck. `verify_learn_package.py`
  now prefers
  `/tmp/vibemix-live-learn-proof/proof-course3-route-settings-runner-current.json`,
  and the refreshed package artifact keeps `passed=true`,
  `release_ready=false`, with the same two blockers: packaged EQ exemplar
  human ear-pass and Course 3 routed-audio count-in proof. Focused proof:
  readiness/verifier ruff passed, the readiness/verifier tests passed 41, the
  broader readiness/proof/validator/verifier/exemplar bundle passed 83, the
  live readiness artifact and route-settings runner artifact were written, no
  sidecar listeners remained on `8765` or `8766`, and the package verdict was
  refreshed with the settings-aware next action.
- A ninety-eighth slice makes the auto-master finder route-aware without
  making it reckless. `AudioMacOS.select_active_master_input` now accepts an
  optional `VIBEMIX_AUTO_MASTER_FALLBACK_DEVICE` hint: live signal still wins,
  but if startup is silent the backend can choose a known preferred capture
  route before falling back to the generic 48 kHz BlackHole variant.
  `run_learn_live_proof.py` resolves that hint from the read-only Rekordbox
  settings and the capture matrix. It only passes the hint when the persisted
  Rekordbox output has a safe `48000Hz` capture row; on the current desk it
  records `BlackHole 2ch is 44100Hz; vibemix capture expects 48000Hz` and lets
  the app keep the safe `BlackHole 16ch @ 48000Hz` fallback. The fresh artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-auto-master-plan-current.json`
  is now preferred by `verify_learn_package.py` and still reports Course 3
  unavailable because no sampled loopback/DJ input carries external playback.
  Focused proof: auto-master runner/backend ruff passed, the runner/verifier/
  readiness/audio-macos test bundle passed 83, the live auto-master-plan
  artifact was written, no sidecar listeners remained on `8765` or `8766`, and
  the package verifier was refreshed with the same honest two release blockers.
- A ninety-ninth slice promotes the auto-master route plan into the package
  verifier instead of requiring humans to dig through the raw runner artifact.
  `verify_learn_package.py` now extracts Course 3 `app_start.result.audio_env`
  and `audio_runtime.auto_master_input` into
  `sections.live_proofs.course3.route_plan` and every Course 3 attempt row.
  The current package report therefore shows the attempted Rekordbox-derived
  fallback candidate `BlackHole 2ch @ 44100Hz`, the rejection reason
  `BlackHole 2ch is 44100Hz; vibemix capture expects 48000Hz`, and the selected
  app input `BlackHole 16ch @ 48000Hz` with reason `48k_fallback`. Top-level
  `next_actions` now include the rate mismatch before the Rekordbox route
  instruction. Focused proof: verifier ruff passed, verifier tests passed 7,
  the broader verifier/runner/readiness/audio-macos bundle passed 84, and the
  package artifact was regenerated with `passed=true`, `release_ready=false`,
  and the same two honest blockers.
- A one-hundredth slice sharpens the Course 3 diagnosis itself from a broad
  "external playback absent" state to a concrete sample-rate mismatch when the
  evidence supports it. `learn_live_readiness.py` now checks whether Rekordbox's
  persisted audio output is a loopback device and whether that exact capture
  row is below vibemix's expected `48000Hz` rate. On the current desk it emits
  `rekordbox_loopback_sample_rate_mismatch` with `severity=fix_rate`, naming
  `BlackHole 2ch @ 44100Hz` and the expected `48000Hz`. The refreshed readiness
  artifact, auto-master runner artifact, and package verifier now tell the
  operator to set `BlackHole 2ch` to `48000Hz` in Audio MIDI Setup or move
  Rekordbox to `BlackHole 16ch` or a 48 kHz aggregate, then play a real deck.
  Focused proof: readiness ruff passed, the readiness/runner/verifier tests
  passed 66, the broader readiness/runner/verifier/audio-macos bundle passed
  85, the live readiness and auto-master runner artifacts were refreshed, no
  sidecar listeners remained on `8765` or `8766`, and the package verifier was
  regenerated with `passed=true`, `release_ready=false`, and the same two
  release blockers.
- A one-hundred-first slice removes that live rate blocker instead of merely
  documenting it. `AudioMacOS.set_device_nominal_sample_rate` now falls back to
  an in-memory Swift/CoreAudio bridge when PyObjC cannot marshal the
  `AudioObjectSetPropertyData` void-buffer path; this matches what worked on
  the desk. The fallback waits for the nominal rate to settle after CoreAudio
  accepts the write. On the current machine, `BlackHole 2ch` now reports
  `48000Hz`; the refreshed Course 3 runner accepts it as the
  Rekordbox-derived `VIBEMIX_AUTO_MASTER_FALLBACK_DEVICE`, and the app starts
  on `BlackHole 2ch @ 48000Hz` with `reason=preferred_fallback`. Course 3 still
  remains unavailable because no real deck audio crossed the signal floor, but
  the top-level package next action is now correctly reduced to starting real
  Rekordbox deck playback with channel and master faders up. Focused proof:
  sample-rate guard/audio-macos/readiness ruff passed, the audio guard,
  audio-macos, readiness, runner, and verifier bundle passed 91, the live
  readiness/runner/package artifacts were refreshed, and no sidecar listeners
  remained on `8765` or `8766`.
- A one-hundred-second slice makes the latest Course 3 evidence cleaner and
  easier to hand off. `learn_live_readiness.py` now samples the persisted
  Rekordbox loopback route for Course 3 direct-signal and self-test checks, so
  a saved `BlackHole 2ch` route is not accidentally diagnosed through macOS's
  default `BlackHole 16ch` output. `run_learn_live_proof.py` now uses the
  broadest requested readiness lens for its generic before/after snapshots, so
  a Course 3 proof samples `BlackHole 2ch` consistently from the first stage.
  `verify_learn_package.py` now prefers
  `/tmp/vibemix-live-learn-proof/proof-course3-rekordbox-nudge-current.json`
  over the older auto-master artifact and surfaces
  `sections.live_proofs.course3.playback_nudge`, proving the opt-in Rekordbox
  spacebar nudge succeeded. The regenerated nudge proof starts vibemix on
  `BlackHole 2ch @ 48000Hz` with `reason=preferred_fallback`; the loopback
  self-test passes, but the direct loopback capture and capture matrix remain
  silent for real external playback. The package verifier remains
  `passed=true`, `release_ready=false`, with the same two blockers: packaged EQ
  exemplar human ear-pass and Course 3 routed-audio count-in proof. Focused
  proof: touched Learn readiness/runner/verifier ruff passed, their focused
  pytest bundle passed 75, the nudge runner artifact and package artifact were
  regenerated, and no sidecar listeners remained on `8765` or `8766`.
- A one-hundred-third slice makes future course integration a checked contract
  instead of a prose-only note. `curriculum_audit.py` now emits
  `course_pack_contract` with the source-of-truth files, required
  `COURSE_REGISTRY` / `COURSE_FRAMES` / `CURRICULUM` fields, required
  transcript fields, the `build_lesson_flow` beginner gate, frontend codegen
  ownership, and verification commands. `verify_learn_package.py` now carries
  that object through `sections.curriculum.course_pack_contract`, so the package
  artifact itself tells the next course author how to add a course without
  hand-editing the frontend mirror. Focused proof: curriculum/verifier ruff
  passed, the curriculum-audit and verifier tests passed 15, the broader
  curriculum/projection/lesson-flow/verifier bundle passed 63, the frontend
  projection check passed, the UI curriculum meta Vitest passed 5, and the
  package artifact plus `/tmp/vibemix-live-learn-proof/learn-curriculum-audit-current.json`
  were regenerated.
- A one-hundred-fourth slice tightens the replay/jump frontstage contract.
  `learn-window.ts` now labels the primary booth action with `replay` when the
  recommended row is already completed, instead of always saying `start`. The
  emitted command was already `level="replay"`; the visible copy now matches
  the actual action, preserving the one-prompt booth without adding a syllabus
  wall. `test_practice_booth_shell.spec.ts` now pins the all-available-lessons-
  completed case: the button says `replay opening dialog` and emits
  `ipc.learn.start_lesson` with `level="replay"`. Focused proof: the practice
  booth Vitest passed 17, the surrounding curriculum/progress-list/HUD replay
  tests passed 32, `npm --prefix tauri/ui run build` passed, and the package
  artifact was refreshed with `passed=true`, `release_ready=false`.
- A one-hundred-fifth slice tightens the Course 3 auto-master proof lens.
  `run_learn_live_proof.py` now polls loopback and capture waits with
  `requirement="course3"`, so those pre-proof waits sample the same
  Rekordbox-selected route as the Course 3 readiness check. The focused run
  exposed that an injected duplex self-test on the exact route Rekordbox owns
  can return silence even though the real blocker is absent external deck
  playback. `learn_live_readiness.py` now treats that case as inconclusive,
  removes the misleading self-test blocker, and emits
  `rekordbox_route_self_test_inconclusive_external_playback_absent`. Refreshed
  artifact `/tmp/vibemix-live-learn-proof/proof-course3-rekordbox-nudge-current.json`
  shows app auto-master selecting `BlackHole 2ch @ 48000Hz`, the Rekordbox
  spacebar nudge passing, no sidecar left on `8765`/`8766`, and no real signal
  on any sampled DJ/loopback capture path. Focused proof: runner/readiness/
  verifier pytest passed 78, touched Python Ruff passed, and the package
  verifier regenerated with `passed=true`, `release_ready=false`, same two
  completion blockers.
- A one-hundred-sixth slice tightens the Course 3 frontstage wait copy back to
  the booth contract. When the Course 3 lens is missing an input, the status
  rail now gives one action: `press play on deck`, `open one channel`,
  `load a track`, or `keep playing`, with `phrase cue locked` preserved as the
  positive state. The aria labels still name the evidence conditions
  (`routed master audio is not audible yet`, no attributed deck, no citable
  track, waiting for phrase evidence) while the visible UI stays beginner-
  actionable. Focused proof: the practice-booth shell Vitest passed 17 after
  pinning the new phrases, `npm --prefix tauri/ui run build` passed, and the
  package verifier regenerated with `passed=true`, `release_ready=false`.
- A one-hundred-seventh slice turns the route diagnostics into an auto-master
  recommendation seam instead of leaving callers to reverse-engineer the
  capture matrix. `learn_live_readiness.py` now emits
  `auto_master_recommendation` with one bounded answer: use the live 48 kHz
  capture input, use Rekordbox's saved 48 kHz loopback route, use the current
  macOS 48 kHz loopback route, fall back to a silent 48 kHz loopback while
  waiting for playback, or fix the named device's sample rate. The live proof
  runner consumes that recommendation when `--auto-master-input` starts the app,
  so future artifacts can show whether the selected input came from live signal,
  Rekordbox settings, macOS output, or fallback. Current
  `proof-course3-auto-master-plan-current.json` records
  `saved_loopback_route` from Rekordbox settings, app selection of
  `BlackHole 2ch @ 48000Hz` as preferred fallback, and Course 3 still skipped
  honestly because count-in/deck grounding is not proven. Focused proof:
  readiness/runner pytest passed 73, touched Python Ruff passed,
  verifier pytest passed 9, and the package verifier regenerated with
  `passed=true`, `release_ready=false`.
- A one-hundred-eighth slice wires that auto-master path into the desktop
  sidecar launch instead of keeping it proof-runner-only. `sidecar.rs` now
  forwards explicit audio environment overrides (`VIBEMIX_INPUT_DEVICE`,
  `VIBEMIX_OUTPUT_DEVICE`, `VIBEMIX_MIC_DEVICE`,
  `VIBEMIX_AUTO_MASTER_INPUT`, and `VIBEMIX_AUTO_MASTER_FALLBACK_DEVICE`) and
  defaults `VIBEMIX_AUTO_MASTER_INPUT=1` when the desktop app has no explicit
  input or auto-master choice. This makes the ordinary Learn app launch use the
  backstage master finder, while preserving power-user overrides such as a
  named input device or `VIBEMIX_AUTO_MASTER_INPUT=0`. Focused Rust proof:
  `cargo check --manifest-path tauri/src-tauri/Cargo.toml` passed,
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml sidecar_audio_env_defaults`
  passed 2, and
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml forwarded_env_keys_relay_runtime_auth_and_codex_setup`
  passed 1.
- A one-hundred-ninth slice fixes the package verifier's Course 3 evidence
  choice so it does not accidentally summarize an older unavailable artifact
  when a richer auto-master attempt exists. `verify_learn_package.py` now
  extracts `auto_master_recommendation` from readiness stages and scores
  Course 3 attempts by strict proof first, then by actionable route evidence:
  machine-readable recommendation, fallback candidate source/reason, selected
  input reason, diagnosis, playback nudge, and tighter blocker count. The
  refreshed `learn-package-verification-current.json` still reports
  `passed=true`, `release_ready=false`, but its Course 3 section now points at
  `proof-course3-auto-master-plan-current.json` with
  `reason=saved_loopback_route`, `source=rekordbox_audio_settings`, and
  `BlackHole 2ch @ 48000Hz` as the preferred fallback. A refreshed short live
  attempt also passed the Rekordbox spacebar nudge but still failed Course 3
  honestly: the loopback route self-test is healthy, direct routed playback is
  still silent, and the live deck state is not attributed to a citable track.
  Focused proof: verifier Ruff passed,
  `tests/learn/test_verify_learn_package.py` passed 10, the live
  auto-master/nudge proof exited 4 with no sidecar listeners left on `8765` or
  `8766`, and the package verifier regenerated with the same two honest blockers:
  packaged EQ exemplar human ear-pass and strict Course 3 routed-audio count-in
  proof.
- A one-hundred-tenth slice closes a Course 3 false-positive audio-active seam.
  The proof readiness summarizer no longer trusts `course3_lens.audio_active`
  when the flat frame also carries `music=0` and `phase=silent`; the socket lens
  itself now requires `MusicState.audible` plus RMS above `SILENT_RMS` before it
  reports `audio_active=true`. The refreshed
  `proof-course3-auto-master-plan-current.json` now shows both the summary and
  `last_lens` agreeing on `audio_active=false`, with blockers for missing live
  master audio, missing deck attribution, missing citable deck track, silent
  direct loopback capture, and silent capture matrix. Focused proof: the touched
  Python/Ruff slice passed, `tests/runtime/test_ws_bus_course3_lens.py` plus
  `tests/learn/test_learn_live_readiness.py` passed 52, the runner/verifier
  bundle passed 39, the live-proof validator passed 14, the live auto-master
  proof exited 4 honestly, no listeners remained on `8765`/`8766`, and the
  package verifier regenerated with `passed=true`, `release_ready=false`.
- A one-hundred-eleventh slice reconnects that stricter Course 3 lens to the
  calm frontstage. Because `session_active` is intentionally false until a real
  audible deck exists, the status rail now tracks whether the loaded lesson is
  in `course_3_play_mode` (or has an `L3.*` id) separately from the live-audio
  lens. When Course 3 is loaded and the lens reports `waiting_for_audio`, the
  beginner sees the one useful action, `press play on deck`, instead of the cold
  window-switch hint. Completing the lesson clears the Course 3 active flag and
  restores the default hint. Focused proof: the practice-booth shell Vitest
  passed 18, Course 3 lens/ws-client Vitest passed 7, and
  `npm --prefix tauri/ui run build` passed. The package verifier was refreshed
  after the UI patch and still reports `passed=true`, `release_ready=false`,
  with the same two honest blockers: packaged EQ exemplar human ear-pass and
  strict Course 3 routed-audio count-in proof.
- A one-hundred-twelfth slice expands the quality pass beyond the focused Learn
  rail. The full UI Vitest suite initially exposed stale jsdom IPC assumptions:
  several settings/session specs mocked `@tauri-apps/api/core` but did not mark
  the webview as Tauri-present, so the shared `invokeTauri` guard correctly
  rejected before the mock could observe `forward_ipc_to_sidecar`. The specs now
  install a fake `window.__TAURI_INTERNALS__` for Tauri-webview assertions while
  keeping the production guard intact. The full Learn pytest suite also exposed
  one stale em-dash expectation after the no-dash tutor-copy cleanup; that
  expectation now matches the shipped colon copy. Broad proof after the fix:
  `tests/learn` passed 582 with 1 opt-in live-jog skip, full UI Vitest passed
  134 files / 1222 tests with 1 todo, `npm --prefix tauri/ui run build` passed,
  and Learn Playwright passed all 10 browser tests across accessibility, axe,
  contrast, controller motion, responsive layout, and Python-sidecar beginner
  path through both Tauri-style forwarding and direct browser WebSocket
  fallback. The refreshed package verifier still reports `passed=true`,
  `release_ready=false`, with the same two live/human blockers.
- A one-hundred-thirteenth slice tightens Course 3 live-proof honesty after a
  fresh app-start run. The runner started `python -m vibemix`, auto-mastered to
  Rekordbox's saved `BlackHole 2ch @ 48000Hz` route, nudged Rekordbox with
  Space successfully, sampled direct loopback and the capture matrix, then
  stopped cleanly with no `8765`/`8766` listeners left behind. The proof still
  failed correctly because no sampled input crossed the signal floor and the
  live socket never saw audible/citable deck context. During that run, an
  artifact-shape seam surfaced: explicit silent loopback/capture diagnostics
  could appear under a summary that still said `course3_audio=true` when live
  context was not sampled. `learn_live_readiness` now treats explicitly enabled
  silent loopback/capture/self-test diagnostics as Course 3 readiness blockers,
  so regenerated wait-stage artifacts report `last.passed=false`,
  `course3_audio=false`, and direct blockers in the same object. The package
  verifier now discovers `proof-course3-auto-master-current.json` and prefers it
  over older plan artifacts, so the top-level Course 3 section points at the
  freshest app-start proof. Focused proof: Ruff passed for the changed scripts
  and tests; `tests/learn/test_learn_live_readiness.py`,
  `tests/learn/test_run_learn_live_proof.py`,
  `tests/learn/test_validate_learn_live_proof.py`, and
  `tests/learn/test_verify_learn_package.py` passed 100; the package verifier
  refreshed with `passed=true`, `release_ready=false`, and the same two honest
  blockers.
- A one-hundred-fourteenth slice makes future courses easier to integrate
  without making the Learn surface feel like a syllabus wall. `CourseMeta` now
  carries `frontstage_mode` plus a machine-readable `capabilities` tuple, and
  the generated frontend curriculum mirror receives the same quiet contract.
  The audit now checks that every compiled lesson flow's backstage lenses and
  input surfaces are covered by the owning course's declared capabilities, so a
  future course cannot depend on live audio, prepared pools, exemplar playback,
  recital observers, debrief/profile state, or controller state without naming
  that seam in the Python source of truth. Observer lessons now expose
  `library_exemplars` and `recital_observer` as real backstage lenses, instead
  of hiding them behind generic practice flow metadata. Current artifacts:
  `/tmp/vibemix-live-learn-proof/learn-curriculum-audit-current.json` and
  `/tmp/vibemix-live-learn-proof/learn-package-verification-current.json`
  both include the upgraded `course_pack_contract.capability_contract`.
  Verification: touched Ruff passed, the focused curriculum/flow/audit/
  teaching-loop/runtime traversal bundle passed 99, the Course 3 proof/verifier
  bundle passed 100, all deterministic Learn pytest passed 584 with the one
  opt-in live-jog skip, Learn UI Vitest passed 29 files / 153 tests,
  `npm --prefix tauri/ui run build` passed, and the package verifier still
  reports `passed=true`, `release_ready=false` with only the packaged EQ
  exemplar ear-pass and strict Course 3 routed-audio count-in proof outstanding.
- A one-hundred-fifteenth slice tightens the packaged EQ exemplar ear-pass
  handoff without pretending human listening has happened. The audition helper
  now has `--list-devices`, returning JSON-safe sounddevice output rows with
  index, name, host API, output channel count, default sample rate, and default
  output marker. Its audit summary now carries `operator_commands` for the
  exact release sequence: list devices, play through a chosen output index,
  write hash-bound approval with `--approve-ear-pass --approved-by <name>`, and
  refresh the package verifier. `verify_learn_package.py` now surfaces those
  commands under `sections.exemplars.operator_commands` and its top-level
  `next_actions` names the same sequence instead of the vague "play and record
  approval." The refreshed
  `/tmp/vibemix-live-learn-proof/learn-exemplar-audit-current.json` includes
  the current output-device list; the default output is currently
  `BlackHole 16ch`, with `DDJ-FLX4`, `BlackHole 2ch`, speakers, and aggregate
  devices also visible. Verification: touched Ruff passed, exemplar/verifier
  pytest passed 20, full deterministic Learn pytest passed 586 with the one
  opt-in live-jog skip, and the package verifier still reports `passed=true`,
  `release_ready=false` until a human actually approves the loops and Course 3
  routed count-in proof passes.
- A one-hundred-sixteenth slice gives Course 3 the same explicit operator
  runway as the exemplar ear-pass path. The package verifier now persists
  `sections.live_proofs.course3.operator_commands` with the current selected
  input, fallback candidate, manual action, readiness command, proof command,
  and verify command. The current artifact names `BlackHole 2ch @ 48000Hz` as
  both the selected input and saved Rekordbox fallback, and the proof command
  runs the app with `--auto-master-input`, `--seed-course3-unlocked`,
  `--nudge-rekordbox-playback`, and `--require-count-in`. The focused verifier
  tests now lock this contract so future sessions cannot silently drop the
  runnable Course 3 recipe. Verification: Ruff passed for the verifier/test
  pair, `uv run pytest -q tests/learn/test_verify_learn_package.py` passed 10,
  and `/tmp/vibemix-live-learn-proof/learn-package-verification-current.json`
  was refreshed with `passed=true`, `release_ready=false`, and only the
  packaged EQ exemplar ear-pass plus strict Course 3 routed-audio count-in proof
  outstanding.
- A one-hundred-seventeenth slice ran the new Course 3 operator recipe against
  the live desk. The proof started and stopped the vibemix app cleanly, brought
  the sidecar up on `127.0.0.1:8765`, selected `BlackHole 2ch @ 48000Hz` via
  auto-master fallback from Rekordbox settings, and recorded a successful
  Rekordbox spacebar nudge. It still failed the strict Course 3 proof because
  direct loopback capture stayed silent, all sampled DJ/loopback capture inputs
  stayed below the signal floor, and the live socket never saw audible,
  deck-attributed, citable-track audio. The refreshed package verifier now
  reports the Course 3 diagnosis as `selected_loopback_silent` with the manual
  action `Start playback into the selected loopback route.` This is good
  integration evidence, but not a release proof.
- A one-hundred-eighteenth slice turns the package verifier into a proper
  requirement-level completion surface. `scripts/verify_learn_package.py` now
  discovers a full frontend-quality artifact, verifies that Learn Vitest,
  production build, and browser Learn e2e all ran, and includes
  `sections.frontend_quality` plus an eight-row `completion_matrix`. The matrix
  tracks curriculum, capability reuse, frontend quality, launched Tauri
  practice-booth integration, on-screen deck proof, physical controller proof,
  Course 3 live-audio play mode, and packaged EQ exemplar ear-pass separately.
  A new `scripts/run_learn_frontend_quality.py` writes
  `/tmp/vibemix-live-learn-proof/learn-frontend-quality-current.json`.
  Current frontend quality artifact is green: `learn_vitest`, `learn_build`,
  and `learn_e2e` all passed. The refreshed package verifier now reports
  `passed=true`, `release_ready=false`, matrix `6/8` proven, and the only
  not-proven rows are `course3_live_audio_play_mode` plus
  `packaged_eq_exemplar_ear_pass`. Verification: touched Ruff passed,
  `uv run pytest -q tests/learn/test_verify_learn_package.py` passed 11, the
  frontend quality runner passed, and the package verifier was refreshed.
- A one-hundred-nineteenth slice hardens the Course 3 proof runner against a
  real operator hazard: pressing Space in Rekordbox is a toggle, so a blind
  nudge can stop already-active playback. `run_learn_live_proof.py` now performs
  a Course 3 signal precheck before the nudge. If loopback, capture-matrix, or
  live Course 3 context signal is already present, it records
  `rekordbox_spacebar_skipped_signal_present` and does not press Space. If the
  route is silent, it records the precheck and then performs the macOS
  automation. The package verifier now preserves that precheck under
  `sections.live_proofs.course3.playback_nudge.precheck` and in the completion
  matrix evidence. The refreshed live artifact still fails Course 3, but with
  sharper proof: selected input is `BlackHole 2ch @ 48000Hz`, precheck had
  `loopback_ok=false`, `capture_ok=false`, `live_context_ok=false`, Space nudge
  succeeded, and the post-wait blocker remains `selected_loopback_silent`.
  Verification: touched Ruff passed, the focused live-proof/verifier pytest
  bundle passed 44, the Course 3 proof artifact was refreshed, and the package
  verifier still reports `passed=true`, `release_ready=false`, matrix `6/8`
  proven.
- A one-hundred-twentieth slice makes the "perfection package" an executable
  artifact flow instead of a remembered checklist. A new
  `scripts/run_learn_python_quality.py` writes
  `/tmp/vibemix-live-learn-proof/learn-python-quality-current.json` after
  running Learn-scoped Ruff, curriculum projection codegen check, and the full
  deterministic Learn pytest suite. A new
  `scripts/run_learn_perfection_package.py` runs Python quality, frontend
  quality, then `verify_learn_package.py` in order and writes
  `/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`.
  `verify_learn_package.py` now requires/discovers `sections.python_quality`
  and adds `python_quality_suite` to the completion matrix, bringing the current
  matrix to 9 rows. The first real package run correctly failed on Learn Ruff
  import hygiene in `skill_recognizer.py`, `test_skill_tree.py`, and
  `test_skill_tree_migration.py`; those mechanical import fixes were applied.
  The rerun passed all deterministic package commands: Python quality,
  frontend quality, and package verifier, and the saved package artifact marks
  `verification_refreshed=true` so stale verifier summaries cannot masquerade
  as fresh. Current package state: `passed=true`, `release_ready=false`, matrix
  `7/9` proven, with only
  `course3_live_audio_play_mode` and `packaged_eq_exemplar_ear_pass`
  not-proven.
- A one-hundred-twenty-first slice makes desktop-shell quality a first-class
  package gate. A new `scripts/run_learn_desktop_quality.py` writes
  `/tmp/vibemix-live-learn-proof/learn-desktop-quality-current.json` after
  running Rust formatting and the Tauri `cargo check` command.
  `verify_learn_package.py` now
  requires/discovers `sections.desktop_quality` and adds
  `desktop_shell_quality` to the completion matrix. The perfection package
  runner now refreshes Python quality, frontend quality, desktop quality, and
  the verifier in order, passing `--desktop-quality` into the verifier so stale
  shell evidence cannot be assumed. Verification: touched Ruff passed, focused
  package/verifier tests passed 25, the desktop quality artifact passed, and
  the full package run passed all four commands. Current package state:
  `passed=true`, `release_ready=false`, `verification_refreshed=true`, matrix
  `8/10` proven, with only `course3_live_audio_play_mode` and
  `packaged_eq_exemplar_ear_pass` not-proven.
- A one-hundred-twenty-second slice makes the Course 3 auto-master/readiness
  probe durable. `scripts/learn_live_readiness.py` now accepts `--out` and
  writes the exact JSON it prints, and the verifier's Course 3 operator recipe
  now saves `/tmp/vibemix-live-learn-proof/learn-course3-readiness-current.json`.
  Focused readiness/verifier tests passed 61, and the full package runner still
  passed all four deterministic commands after adding the package runner itself
  to the Python-quality Ruff envelope. A fresh readiness artifact confirms the
  current desk state: Rekordbox is running, DDJ-FLX4 MIDI/audio is visible,
  the auto-master recommendation is `BlackHole 2ch` from
  `rekordbox_audio_settings`, the loopback self-test captures the injected tone,
  but real playback remains silent on both direct loopback and capture matrix.
- A one-hundred-twenty-third slice tightens the desktop-shell proof from
  "Rust compiles" to "Rust compiles and the app-spawned sidecar defaults
  auto-master correctly." `scripts/run_learn_desktop_quality.py` now includes
  `cargo test --manifest-path tauri/src-tauri/Cargo.toml
  sidecar_audio_env_defaults`, and `verify_learn_package.py` requires that
  command row under `sections.desktop_quality`. Focused desktop/verifier tests
  passed 16, the refreshed desktop quality artifact passed all three rows
  (`learn_cargo_fmt`, `learn_cargo_check`,
  `learn_cargo_sidecar_audio_test`), and the full package runner passed all
  four commands. Current package state remains `passed=true`,
  `release_ready=false`, matrix `8/10` proven; the two unresolved rows are
  still the honest live/human blockers.
- A one-hundred-twenty-fourth slice hardens the future-course integration seam.
  `audit_curriculum()` now emits `flow_contract_summary` proving that all 36
  beginner flows are structurally real (`total_steps=76`, `min_hint_count=3`,
  both hardware and screen input surfaces, 18 observable controls, and all
  declared backstage lenses), and `transcript_inventory` proving every
  transcript fixture is claimed by exactly one `LessonMeta` row (`37/37`,
  no duplicates, missing paths, or orphans). `verify_learn_package.py` carries
  both summaries into the `curriculum_36_lesson_contract` evidence. Focused
  curriculum/verifier/flow tests passed 64, and the full package runner passed
  all four commands with the same two remaining live/human blockers.
- A one-hundred-twenty-fifth slice promotes replay/jump and graceful lesson
  choice from "buried in broad frontend tests" to explicit package evidence.
  `scripts/run_learn_frontend_quality.py` now runs a named
  `learn_choice_replay_vitest` command before the broad Learn suite, targeting
  `test_practice_booth_shell.spec.ts`, `test_progress_list.spec.ts`,
  `test_curriculum_meta.spec.ts`, and `test_hud_progress_dots_keyboard.spec.ts`.
  `verify_learn_package.py` requires that row and adds
  `lesson_choice_replay_contract` to the completion matrix, proving the calm
  recommended-start path, opt-in lesson map, locked-course handling, and
  completed-lesson replay semantics. Focused frontend-runner/verifier/package
  tests passed 23; the refreshed frontend artifact passed all four rows; the
  full package runner passed all four commands. Current package state:
  `passed=true`, `release_ready=false`, matrix `9/11` proven, with only the
  Course 3 live routed-audio proof and EQ exemplar ear-pass unresolved.
- A one-hundred-twenty-sixth slice promotes the backstage teaching loop from
  broad Python coverage to explicit package evidence. `scripts/run_learn_python_quality.py`
  now runs a named `learn_teaching_loop_pytest` command before the broad Learn
  pytest suite, targeting `tests/learn/test_teaching_loop.py`. The package
  verifier requires that command and adds `teaching_loop_contract` to the
  completion matrix, proving observe, decide, teach, verify, and adapt turns
  through `vibemix.llm.model_router` plus deterministic verification metadata.
  Focused runner/verifier/package/teaching-loop tests passed 31; the refreshed
  Python artifact passed all four rows (`learn_ruff`, `learn_codegen_check`,
  `learn_teaching_loop_pytest`, `learn_pytest`); the full perfection package
  runner passed Python quality, frontend quality, desktop quality, and package
  verification. Current package state: `passed=true`, `release_ready=false`,
  matrix `10/12` proven, with only the Course 3 live routed-audio proof and EQ
  exemplar ear-pass unresolved.
- A one-hundred-twenty-seventh slice promotes real app entry into Learn from
  implicit frontend coverage to package evidence. `scripts/run_learn_frontend_quality.py`
  now runs `learn_app_entry_vitest` before the choice/replay and broad frontend
  gates, targeting `tests/learn/test_beginner_path_contract.spec.ts`,
  `tests/session/render-loop-actions.spec.ts`, and `tests/shell/shell.spec.ts`.
  The verifier requires that row and adds `app_entry_contract` to the matrix,
  proving the main session mode picker invokes `open_learn_window`, the shell
  command palette can jump to Learn, and the recommended first booth action can
  start from that normal app path. Focused runner/verifier/package tests passed
  23; the targeted app-entry Vitest slice passed 17; the refreshed frontend
  artifact passed all five rows; the full perfection package runner passed all
  four commands. Current package state: `passed=true`, `release_ready=false`,
  matrix `11/13` proven, with only the Course 3 live routed-audio proof and EQ
  exemplar ear-pass unresolved.
- A one-hundred-twenty-eighth slice makes Course 3's current route failure
  specific enough for a human to fix. `scripts/learn_live_readiness.py` now
  compares Rekordbox's persisted `audio_device_rate` against the selected
  loopback capture row when `rekordbox_audio_settings` and the capture matrix
  are available. On this desk the saved Rekordbox route is `BlackHole 2ch` at
  `44100.0`, while vibemix captures `BlackHole 2ch` at `48000Hz`, so readiness
  emits `course3_audio_diagnosis.code="rekordbox_saved_sample_rate_mismatch"`,
  `severity="fix_rate"`, and a structured `saved_rate_mismatch` payload. The
  loopback self-test passes, so the action is not "install BlackHole"; it is
  "set Rekordbox's BlackHole 2ch route from 44100Hz to 48000Hz, then play a
  deck with channel and master faders up." The Course 3 operator recipe now
  includes `--loopback-self-test-seconds 1` in both readiness and proof paths so
  the package artifact preserves that distinction. Live proof against the
  plugged-in DDJ/Rekordbox desk started and stopped the app cleanly, selected
  `BlackHole 2ch @ 48000Hz`, passed the Rekordbox Space nudge and loopback
  self-test, then failed strictly because external loopback/capture remained
  silent and the live socket had no audible deck-attributed citable track.
  Verification: touched readiness/verifier Ruff passed; focused
  `test_learn_live_readiness.py` plus `test_verify_learn_package.py` passed 62;
  the bounded live readiness/proof artifacts exited 4 as expected with the new
  diagnosis; `verify_learn_package.py` passed; and the full
  `run_learn_perfection_package.py` refreshed Python, frontend, desktop, and
  package verification with `passed=true`, `release_ready=false`, matrix
  `11/13`.
- A one-hundred-twenty-ninth slice applies that route fix on the live desk and
  proves the blocker moved forward. Rekordbox did not quit cleanly through
  AppleScript, so the main process was terminated normally, the settings file was
  backed up as `rekordbox3.settings.codex-backup-20260529-075121`, and only the
  BlackHole 2ch `audioDeviceRate` / `SampleRate` fields were changed from
  `44100.0` to `48000.0`. After reopening Rekordbox, readiness reported
  `audio_device_rate="48000.0"` for both the global and performance-mode
  BlackHole 2ch settings, selected `BlackHole 2ch @ 48000Hz`, and passed the
  loopback self-test. The refreshed Course 3 app proof still exited 4, but the
  diagnosis is now `loopback_route_healthy_external_playback_absent`, not a rate
  mismatch: external loopback/capture remained silent, the live socket saw
  `deck=none`, and no citable deck track/count-in evidence appeared. The
  package verifier was refreshed and still reports `passed=true`,
  `release_ready=false`, matrix `11/13`; the only remaining Course 3 action is
  to play a real Rekordbox library track through the routed master with channel
  and master faders up.
- A one-hundred-thirtieth slice makes that last Course 3 action harder to
  misread. `learn_live_readiness.py` now samples macOS Now Playing for Course 3
  readiness and appends an explicit blocker when the active metadata source is
  unavailable or not Rekordbox. On the current desk, the route is aligned
  (`BlackHole 2ch @ 48000Hz`) and the loopback self-test passes, but Now Playing
  is a paused WebKit podcast from `com.apple.WebKit.GPU`, not a Rekordbox deck
  title. The diagnosis stays
  `loopback_route_healthy_external_playback_absent`; its action now says to
  start real Rekordbox deck playback and stop unrelated media or make Rekordbox
  the active playing source. `verify_learn_package.py` now gives Course 3
  attempts with `nowplaying_hint`/raw `nowplaying` evidence a higher score, so
  the package verifier prefers the fresh
  `/tmp/vibemix-live-learn-proof/proof-course3-auto-master-current.json` over
  older plan artifacts. Verification: Ruff passed for readiness/verifier tests,
  focused readiness/verifier pytest passed 63, `verify_learn_package.py`
  refreshed the current verifier artifact with the Now Playing hint, and the
  full perfection package passed all four commands with `passed=true`,
  `release_ready=false`, matrix `11/13`.
- A one-hundred-thirty-first slice turns that diagnosis into a structured
  operator action without weakening the proof. Course 3 external-playback
  failures now include `course3_audio_diagnosis.operator_action`: route
  `BlackHole 2ch @ 48000Hz`, a one-line prompt to play a real Rekordbox library
  track through that route with channel/master up, the current Now Playing
  blocker, and four steps ending in rerunning the count-in proof. The package
  verifier copies that object to
  `sections.live_proofs.course3.operator_commands.operator_action`, so the next
  integration session can render a calm "do this next" card instead of parsing
  raw blockers. A refreshed strict live proof still failed honestly with silent
  loopback/capture and paused WebKit Now Playing, but stopped the app cleanly
  and wrote the new action object. Verification: Ruff passed for
  readiness/verifier files and focused readiness/verifier pytest passed 63; the
  full perfection package passed all four commands with `passed=true`,
  `release_ready=false`, matrix `11/13`.
- A one-hundred-thirty-second slice sharpens the other release blocker without
  pretending to approve it. `audition_learn_exemplars.py` now ranks output
  devices for human ear-pass and filters out loopback/capture sinks such as
  BlackHole, aggregate routes, and rekordbox capture devices. Its
  `operator_action` now carries a one-line prompt, recommended audible outputs,
  and a concrete play command when `--list-devices` is used. On this desk the
  default output is still `BlackHole 16ch`, so the refreshed exemplar audit
  recommends `MacBook Pro Speakers` at device index `4` and writes the exact
  step `uv run python scripts/audition_learn_exemplars.py --play --device-index
  4`. This keeps the human-listening gate intact while removing the trap of
  auditioning silence through the routing bus. Verification: Ruff passed for
  the exemplar/verifier files, focused exemplar/verifier pytest passed 24, the
  refreshed `/tmp/vibemix-live-learn-proof/learn-exemplar-audit-current.json`
  contains the recommendation, and the full perfection package passed all four
  commands with `passed=true`, `release_ready=false`, matrix `11/13`.
- A one-hundred-thirty-third slice wires those structured next actions into the
  Learn frontstage without making another page. `operator-action.ts` normalizes
  backstage `operator_action` objects and compresses them to one booth-sized
  phrase, while preserving the fuller route and steps in aria/title text. The
  Course 3 lens path now accepts `operator_action` from the flat frame and the
  status rail shows `play Rekordbox through BlackHole` when that proof object is
  present. A generic `learn.operator_action` event gives the same calm one-line
  surface to exemplar ear-pass or future courses, e.g. `audition EQ examples on
  MacBook Pro Speakers`, without exposing a syllabus wall or JSON panel.
  Verification: focused Learn Vitest passed 29 tests across operator projection,
  practice-booth shell, and WebSocket lens parsing, and `npm --prefix tauri/ui
  run build` passed.
- A one-hundred-thirty-fourth slice removes the last vague route wording from
  Course 3 failure evidence. `learn_live_readiness.py` now lets
  `course3_audio_diagnosis.operator_action` use current Rekordbox audio settings
  even when `rekordbox_route_hint` cannot form, and falls back to the
  auto-master recommendation when no Rekordbox route is named. The fresh desk
  run shows the exact current state: auto-master can select `BlackHole 16ch @
  48000Hz`, Rekordbox currently names `Aggregate Device @ 48000Hz`, no DDJ/FLX
  controller is visible to MIDI/USB/audio, passive loopback capture is silent,
  Now Playing is still a paused WebKit podcast, and the app-start Course 3 proof
  remains unavailable. This is still not release-ready, but the operator action
  now says the concrete route instead of `the selected loopback capture route`.
  Verification: Ruff passed for readiness/tests, focused readiness pytest
  passed, the refreshed Course 3 proof wrote the exact route, package verifier
  picked it up, and no `8765`/`8766` listener was left behind.
- A one-hundred-thirty-fifth slice hardens future course integration around
  unlock gates. `curriculum_audit.py` now emits `unlock_gate_contract`, derived
  from `LearnProgress().to_dict()`, and fails if any `CourseMeta.unlock_gate`
  lacks a persisted progress boolean or has no lock reason. This prevents a
  future Course 4 from rendering as a locked chooser row with no backend field
  capable of unlocking it. `curriculum_projection.py` now generates the
  frontend `LearnProgressProjection` unlock fields from declared gates, so the
  TS mirror follows the Python source instead of carrying hardcoded Course 2/3
  assumptions. The package verifier includes this contract under the
  curriculum evidence. Verification: Ruff passed for curriculum audit,
  projection, package verifier, and tests; focused pytest passed 24 tests across
  curriculum audit/projection/verifier; codegen check passed; Learn curriculum
  Vitest passed; the refreshed curriculum audit reports supported/used gates
  `course_2_unlocked` and `course_3_unlocked`, with no unsupported gates.
- A one-hundred-thirty-sixth slice removes an overclaim from the L3.04
  capstone and turns it into a reusable integration rule. The lesson no longer
  says the debrief "opens at end"; it now says session evidence is saved for a
  post-set debrief and points the learner to the debrief surface after the set.
  `curriculum_audit.py` now emits `copy_truthfulness_contract` and fails future
  transcript copy that promises automatic debrief opening without a proven
  runtime command and frontend invoke path. The package verifier carries this
  contract in the 36-lesson curriculum evidence. Verification: focused Ruff
  passed, focused pytest passed 62 tests, `audit_learn_curriculum.py` reports
  `copy_truthfulness_contract.ok=true`, and the full Learn perfection package
  passed with `release_ready=false` for the existing ear-pass and Course 3 live
  audio blockers.
- A one-hundred-thirty-seventh slice wires Learn into the existing recording
  session spine without adding a new surface. `LessonRuntime` now accepts an
  optional `session_event_logger` and fail-soft logs `learn_lesson_loaded`,
  `learn_tutor_speak`, `learn_action_observed`, and `learn_lesson_completed`
  events. The live sidecar passes a `VoiceRecorder.log_event` adapter, so Learn
  lessons leave a timeline in the same `events.jsonl` that debrief/profile
  tooling already reads. The frontstage remains one prompt/one action; this is
  backstage integration only. Verification: focused Ruff passed, focused
  runtime/lesson-path pytest passed 52 tests, and the full Learn perfection
  package passed again with the same two honest release blockers.
- A one-hundred-thirty-eighth slice consumes that Learn timeline through the
  existing debrief/profile seams. `_build_cited_critique` now turns
  `learn_action_observed` into cited learner-action critique lines using the
  same `midi`/`screen` evidence keys the runtime writes, preserves only cited
  `learn_tutor_speak` lines, and leaves uncited fixture copy out of debrief
  evidence. `learn_action_observed` now carries `evidence_time`, so the later
  debrief citation points at the exact registry timestamp instead of a generic
  event time. The package verifier adds `session_debrief_profile_contract`,
  proving Learn logs lesson milestones to `events.jsonl` and that debrief
  critique plus profile write-back can consume the structured events. This
  keeps the frontstage simple while making post-lesson intelligence real.
  Verification: focused Ruff passed, focused pytest passed 25 tests across
  runtime evidence, debrief/profile integration, verifier, and package-runner
  contracts, and the full Learn perfection package passed with
  `passed=true`, `release_ready=false`, matrix `12/14`. The only remaining
  blockers are still packaged EQ exemplar human ear-pass and Course 3 routed
  audio count-in proof.
- A one-hundred-thirty-ninth slice reduces false-negative hardware readiness
  during the live proof. On this desk, `sniff_controller.py --list` reports
  `DDJ-FLX4` and CoreAudio exposes `DDJ-FLX4` with manufacturer
  `AlphaTheta Corporation`, but `system_profiler SPUSBDataType` can be quiet.
  `learn_live_readiness.py` now falls back from `SPUSBDataType` to
  `SPAudioDataType` for the `usb_controller` check and records the profiler
  `source`, so the artifact no longer implies the controller is unplugged when
  macOS exposes its audio endpoint. The same slice also removes a Course 3
  runbook ambiguity: when Rekordbox's current saved route is unaligned/silent
  but auto-master selected a viable capture device, the operator action now
  targets the auto-master route and records the current Rekordbox route
  separately. In the current artifact that means `route="BlackHole 16ch @
  48000Hz"` with `current_rekordbox_route="Aggregate Device @ 48000Hz"`.
  Verification: Ruff passed for the readiness script/tests,
  `tests/learn/test_learn_live_readiness.py` passed 54 tests, the refreshed
  live readiness artifact reports MIDI `DDJ-FLX4`,
  `controller_audio_present=true`, and `usb_controller.ok=true` via
  `SPAudioDataType`. The full Learn perfection package passed again with
  `passed=true`, `release_ready=false`, matrix `12/14`; Course 3 remains
  blocked by silent loopback/external Rekordbox playback, not by controller
  detection.
- A one-hundred-fortieth slice attempted the real physical DDJ proof after the
  controller became visible. The proof started the app, opened the socket, saw
  `DDJ-FLX4` as MIDI input, loaded L1.07 with
  `lesson_loaded_controller_id="pioneer_ddj_flx4"`, and proved physical
  readiness before the probe. It did not receive an `ipc.learn.midi_position`
  frame for `jog:A`, so it did not send the Learn ACK or see advance. The
  artifact `/tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json` is
  therefore correctly failed rather than grandfathering an older success. The
  refreshed full Learn perfection package still passes its quality/verifier
  commands, but now reports `release_ready=false`, matrix `11/14`, with three
  blockers: packaged EQ exemplar human ear-pass, physical controller lesson
  proof, and Course 3 routed-audio count-in proof.
- A one-hundred-forty-first slice tightens auto-master fallback selection for
  proof runs. Physical-only proof readiness does not sample the capture matrix,
  so the runner could record Rekordbox's saved `Aggregate Device` as an
  auto-master fallback candidate and pass it to the app even though it had not
  been verified as a capture route. `run_learn_live_proof.py` now rejects any
  Rekordbox-settings fallback that is not present in the sampled capture matrix,
  recording a clear `auto_master_fallback_rejected_reason` instead. This keeps
  physical proof audio envs honest and leaves Course 3 runs to use their
  sampled auto-master recommendation. Verification: Ruff passed for the runner
  and tests, `tests/learn/test_run_learn_live_proof.py` passed 34 tests, and
  the full Learn perfection package passed with `release_ready=false`, matrix
  `11/14`, preserving the same three live/human blockers.
- A one-hundred-forty-second slice fixes two live-proof overconstraints exposed
  by the BlackHole desk run. First, `live_learn_socket_jog_probe.py` now retries
  `ipc.learn.start_lesson` once per second until `lesson_loaded` or deadline and
  reports a stable diagnosis code (`learn_lesson_not_loaded`,
  `left_jog_not_observed`, `jog_seen_ack_not_sent`, `jog_ack_no_advance`, or
  `physical_l1_07_proven`) plus operator action. Second, Course 3 readiness no
  longer requires DDJ USB/MIDI hardware just to enter play mode; that was
  incompatible with the product promise that a learner can use a physical
  controller or the on-screen/Rekordbox deck. Course 3 now requires the sidecar,
  Rekordbox, loopback/DJ audio visibility, audio diagnostics, and live/citable
  deck context. The refreshed artifact fails for the real remaining reasons:
  `BlackHole 2ch @ 48000Hz` is selected from Rekordbox settings, but capture is
  silent, live master audio is not audible, no Deck A/B/mix attribution exists,
  no citable `track_id` exists, and macOS Now Playing is a paused WebKit title
  rather than Rekordbox. The user then unplugged the DDJ, so no further physical
  proof was attempted. Verification: Ruff passed for the touched live proof
  scripts/tests, focused pytest passed 107 tests across live readiness,
  proof-runner, validator, and socket jog probe contracts, and the refreshed
  package verifier reports `technical_passed=true`, `release_ready=false`,
  matrix `11/14`, with no `8765`/`8766` listener left behind.
- A one-hundred-forty-third slice makes the package verifier's physical lane as
  actionable as the Course 3 lane. `verify_learn_package.py` now extracts
  `physical_probe.result.diagnosis` when present, publishes physical
  `operator_commands` (`sniff_controller.py --list`, physical readiness, full
  L1.07 proof, and package verify), includes those in the completion matrix,
  and uses the probe's `operator_action.prompt` in `next_actions` when
  available. The current unplugged-desk physical artifact was refreshed with a
  short wait: it now skips because the DDJ is absent from MIDI and
  USB/controller audio, rather than preserving an older no-jog attempt. The
  refreshed package verifier still reports `technical_passed=true`,
  `release_ready=false`, matrix `11/14`, with the same honest blockers:
  packaged EQ exemplar ear-pass, physical controller proof, and Course 3
  routed-audio count-in proof. Verification: Ruff passed for the touched
  verifier/live proof scripts and tests, focused pytest passed 121 tests, and no
  `8765`/`8766` listener was left behind.
- A one-hundred-forty-fourth slice hardens the `model_router` part of the
  backstage teaching-loop claim. `run_learn_python_quality.py` now runs
  `bash scripts/release/check_no_hardcoded_model.sh` as
  `learn_model_router_guard`, and `verify_learn_package.py` requires that row
  in the Python quality artifact. The `teaching_loop_contract` evidence now
  records `model_router_guard=true` beside the observe/decide/teach/verify/adapt
  metadata tests, so stale artifacts without the hardcoded-model guard no longer
  prove the Learn Python quality gate. Verification: the model literal gate
  passed directly, Ruff passed for the runner/verifier/tests, focused pytest
  passed 17 tests for the Python quality runner and package verifier, the full
  Learn Python quality artifact passed all five commands (`learn_ruff`,
  `learn_codegen_check`, `learn_model_router_guard`,
  `learn_teaching_loop_pytest`, `learn_pytest`), and the refreshed package
  verifier remains `technical_passed=true`, `release_ready=false`, matrix
  `11/14`.
- A one-hundred-forty-fifth slice tightens the remaining human EQ exemplar
  release gate. `audition_learn_exemplars.py` now computes a
  `bank_fingerprint` for the exact packaged bank using the manifest hash plus
  canonical track metadata and WAV hashes. `write_ear_pass_approval()` embeds
  that fingerprint, and `validate_ear_pass_approval()` rejects approval
  artifacts with missing/mismatched bank fingerprints in addition to stale track
  hashes. `verify_learn_package.py` now surfaces the fingerprint in
  `sections.exemplars` and the `packaged_eq_exemplar_ear_pass` completion row,
  so the consolidated proof surface can show exactly which bank is awaiting
  human approval. Current fingerprint:
  `34e7aafe568b2e8badecb75fd28e0a8bd710f4fd1b1f2d84e7ff4a78584096e9`;
  manifest hash:
  `8d8ae0dd1e418babb900dc70c3335829eae27629e9f8b5e6591721c435decd58`.
  Verification: Ruff passed for the exemplar/verifier scripts and tests,
  focused pytest passed 28 exemplar/verifier tests, the exemplar audit artifact
  passed technical integrity with `release_ready=false`, and the refreshed
  package verifier remains `technical_passed=true`, `release_ready=false`,
  matrix `11/14`.
- A one-hundred-forty-sixth slice propagates the stricter backstage quality
  contract into the top-level perfection package artifact.
  `run_learn_perfection_package.py` now reads the refreshed package verifier and
  writes `quality_contract` metadata for Python, frontend, and desktop quality.
  The Python summary carries the exact verified command names and
  `model_router_guard=true`, so reviewers can see from
  `/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json` that the
  package pass included `learn_model_router_guard` without opening a nested
  artifact. Verification: Ruff passed for the package runner/tests and related
  quality/verifier scripts, focused pytest passed 24 tests, desktop quality
  passed after refreshing the frontend build outputs, and the full Learn
  perfection package passed all four commands with `verification_refreshed=true`,
  `release_ready=false`, matrix `11/14`. The three release blockers remain the
  EQ human ear-pass, the unplugged physical-controller proof, and Course 3
  routed-audio proof.
- A one-hundred-forty-seventh slice makes the desktop-shell gate self-contained
  with respect to Tauri's embedded frontend assets. `run_learn_desktop_quality.py`
  now runs `learn_tauri_frontend_dist_build` (`npm --prefix tauri/ui run build`)
  before `cargo fmt`, `cargo check`, and the sidecar auto-master Rust test.
  `verify_learn_package.py` requires that new desktop row, and the top-level
  perfection-package `quality_contract` now lists frontend and desktop command
  names as well as Python commands. This prevents a stale or missing
  `tauri/ui/dist/assets/*.js` file from surfacing as an opaque
  `tauri::generate_context!()` Cargo failure. Verification: Ruff passed for the
  desktop/package/verifier runners and tests, focused pytest passed 25 tests,
  the refreshed desktop artifact passed all four desktop commands, and the full
  Learn perfection package passed all four package commands with
  `verification_refreshed=true`, `release_ready=false`, matrix `11/14`.
- A one-hundred-forty-eighth slice promotes future-course readiness from a
  nested curriculum-audit detail into a scored package requirement.
  `verify_learn_package.py` now emits a `future_course_extension_contract`
  completion row that checks the course source map, required Python registry
  entries, transcript fields, generated-only frontend projection, lesson-flow
  compiler, capability/unlock rules, and the verification command set for
  adding a new course. The row is currently proven and appears beside the other
  release-gate requirements, moving the refreshed package matrix to `12/15`
  proven while preserving the same three honest blockers: EQ human ear-pass,
  unplugged physical-controller proof, and Course 3 routed-audio proof.
  Verification: Ruff passed for the package verifier/tests, focused verifier
  pytest passed 16 tests, and the full Learn perfection package passed all four
  package commands with `verification_refreshed=true`, `release_ready=false`,
  matrix `12/15`.
- A one-hundred-forty-ninth slice makes the "not a syllabus wall" frontstage
  promise a scored package requirement instead of an implied behavior inside
  the broader choice/replay tests. `run_learn_frontend_quality.py` now has a
  focused `learn_frontstage_simplicity_vitest` command for
  `test_practice_booth_shell.spec.ts`, while `learn_choice_replay_vitest`
  covers the optional map/progress/HUD contracts. `verify_learn_package.py`
  now emits `frontstage_simplicity_contract`, proving the default Learn surface
  offers one primary recommended action plus an opt-in chooser, keeps the
  36-lesson map hidden by default, and keeps progress snapshots from
  auto-opening the map. Verification: Ruff passed for the frontend runner,
  package verifier, and tests; focused Python pytest passed 26 tests; focused
  Vitest passed 21 practice-booth tests; and the full Learn perfection package
  passed all four package commands with `verification_refreshed=true`,
  `release_ready=false`, matrix `13/16`. The same three release blockers remain.
- A one-hundred-fiftieth slice hardens the exact no-charge/no-controller case
  the desk ended in. `test_practice_booth_shell.spec.ts` now covers a real UI
  sequence where `ipc.learn.controller_detected` connects a DDJ-FLX4, then
  disconnects it: the booth stays visible, the 36-lesson map stays hidden, the
  status rail returns to `on-screen deck`, the no-controller banner says
  `screen deck is ready` only inside the opt-in chooser, and the primary button
  still starts `L1.01` through the normal `ipc.learn.start_lesson` path.
  `verify_learn_package.py` records that behavior in
  `frontstage_simplicity_contract.evidence.hardware_unavailable`, so a handoff
  can distinguish "physical proof unavailable" from "Learn unusable without
  hardware." Verification: Ruff passed for the package verifier/tests, focused
  verifier pytest passed 16 tests, focused Vitest passed 22 practice-booth
  tests, and the full Learn perfection package passed all four package commands
  with `verification_refreshed=true`, `release_ready=false`, matrix `13/16`.
  The same three release blockers remain.
- A one-hundred-fifty-first slice makes the all-lesson deterministic verifier
  shape explicit in the curriculum audit instead of leaving it as a hidden
  implementation detail. `src/vibemix/learn/curriculum_audit.py` now records
  per-lesson and package-level `verification_kind_counts` plus
  `input_surface_step_counts`, while also rejecting unknown verifier kinds,
  invalid button directions, and non-positive CC deltas. The current proven
  flow summary is 36 beginner lessons, 76 compiled steps, 51 `button_press`
  verifiers, 25 `cc_delta` verifiers, 44 screen-only steps, 32
  hardware-or-screen steps, 18 observable control IDs, and 13 backstage lenses.
  The package verifier exposes those numbers under
  `curriculum_36_lesson_contract.evidence.flow_contract_summary`, making the
  "all 36 lessons have deterministic verification" claim directly inspectable.
  Verification: Ruff passed for the curriculum audit/verifier tests, focused
  curriculum/verifier pytest passed 23 tests, focused lesson-flow pytest passed
  45 tests, `scripts/audit_learn_curriculum.py` wrote a passing artifact, and
  the full Learn perfection package passed all four package commands with
  `verification_refreshed=true`, `release_ready=false`, matrix `13/16`. The
  same three release blockers remain.
- A one-hundred-fifty-second slice promotes the existing all-lesson runtime
  traversal from broad pytest coverage into first-class package evidence.
  `scripts/run_learn_python_quality.py` now runs
  `learn_all_lessons_runtime_pytest` (`uv run pytest -q
  tests/learn/test_all_lessons_runtime_path.py`) between the model-router guard
  and the teaching-loop pytest. `verify_learn_package.py` requires that command
  and emits `all_lessons_runtime_contract`, proving every beginner lesson uses
  the real `ipc.learn.start_lesson` -> `ipc.learn.ack` ->
  `ipc.learn.complete_lesson` runtime path, reaches `LessonRuntime.completed`,
  persists `LearnProgress`, and covers observer lessons `L1.14`, `L1.16`, and
  `L2.14`. `run_learn_perfection_package.py` now mirrors this as
  `quality_contract.python_quality.all_lessons_runtime=true`. Verification:
  Ruff passed for the Python/package/verifier runners and tests, focused runner
  and verifier pytest passed 25 tests, focused all-lessons runtime pytest passed
  36 tests, and the full Learn perfection package passed all four package
  commands with `verification_refreshed=true`, `release_ready=false`, matrix
  `14/17`. The same three release blockers remain.
- A one-hundred-fifty-third slice promotes grounded adaptive coaching from
  buried runtime coverage into first-class package evidence. Added
  `tests/learn/test_adaptive_coaching_runtime_contract.py`, a focused release
  contract proving that a timed hint strike emits
  `teaching_loop.turn_kind=hint` and persists `LearnProgress.strikes_used`, a
  wrong on-screen action travels through the normal `ipc.learn.start_lesson` /
  `ipc.learn.ack` path and emits `teaching_loop.turn_kind=adapt` without
  advancing, and a too-small MIDI EQ move writes registry-backed
  `[midi:...]` plus `[screen:...]` citations that pass the live
  `CitationLinter`. `scripts/run_learn_python_quality.py` now runs that file
  as `learn_adaptive_coaching_pytest`; `verify_learn_package.py` requires it
  and emits `adaptive_coaching_runtime_contract`; and
  `run_learn_perfection_package.py` mirrors it as
  `quality_contract.python_quality.adaptive_coaching=true`. Verification:
  Ruff passed for the new test and quality/package/verifier scripts, the new
  focused pytest passed 3 tests, the runner/package/verifier pytest bundle
  passed 25 tests, and the full Learn perfection package passed all four
  package commands with `verification_refreshed=true`,
  `release_ready=false`, matrix `15/18`. The same three release blockers
  remain: packaged EQ exemplar human ear-pass, physical controller proof, and
  Course 3 routed-audio count-in proof.
- A one-hundred-fifty-fourth slice promotes the Learn desktop-window wiring
  into first-class package evidence. `scripts/run_learn_frontend_quality.py`
  now runs `learn_tauri_window_vitest` against
  `tauri/ui/tests/learn/test_learn_window_label.spec.ts`, and
  `scripts/run_learn_desktop_quality.py` now runs
  `learn_cargo_learn_window_test` (`cargo test --manifest-path
  tauri/src-tauri/Cargo.toml learn_window`). `verify_learn_package.py` emits
  `tauri_learn_window_contract`, proving `open_learn_window` is registered,
  the `learn` window is in Tauri capabilities, the window label remains the
  lowercase `learn`, and the Webview loads bundled `learn.html` without
  launching a second Python process. `run_learn_perfection_package.py` mirrors
  this in `quality_contract.frontend_quality.tauri_window_contract=true` and
  `quality_contract.desktop_quality.learn_window_test=true`. Verification:
  Ruff passed for the quality/package/verifier scripts and tests, the focused
  Python runner/verifier bundle passed 30 tests, the Learn-window Vitest passed
  2 tests, the Rust Learn-window cargo test passed 2 tests, and the full Learn
  perfection package passed all four package commands with
  `verification_refreshed=true`, `release_ready=false`, matrix `16/19`. The
  same three release blockers remain.
- A one-hundred-fifty-fifth slice promotes browser-rendered practice-booth
  quality into first-class package evidence. `scripts/run_learn_frontend_quality.py`
  now runs `learn_browser_booth_playwright` through the existing
  `test:e2e:learn` Playwright script, targeting `browser-axe.pw.ts`,
  `browser-responsive.pw.ts`, `browser-contrast.pw.ts`, and
  `browser-python-beginner-path.pw.ts` before the broad Learn e2e gate.
  `verify_learn_package.py` emits `browser_practice_booth_quality_contract`,
  proving the booth has no critical/serious axe findings, no narrow first-paint
  shell overflow, browser-computed contrast for tutor/cue highlights, and
  recommended L1.01 completion through both the Tauri-style forwarder and
  direct browser WebSocket fallback. `run_learn_perfection_package.py` mirrors
  this as `quality_contract.frontend_quality.browser_booth_quality=true`.
  Verification: Ruff passed for the quality/package/verifier scripts and
  tests, the focused Python runner/verifier bundle passed 26 tests, the focused
  browser Playwright command passed 6 tests, and the full Learn perfection
  package passed all four package commands with `verification_refreshed=true`,
  `release_ready=false`, matrix `17/20`. The same three release blockers
  remain.
- A one-hundred-fifty-sixth slice promotes the Course 3 auto-master finder into
  first-class package evidence. `scripts/learn_live_readiness.py` now attaches
  ranked `candidates` to `recommend_auto_master_input`, covering live signal,
  saved Rekordbox route, macOS output route, 48 kHz loopback fallbacks, sampled
  versus unsampled evidence, source/reason tags, sample rates, and signal
  metrics. `tests/learn/test_auto_master_finder_contract.py` pins the ranked
  evidence, unsampled saved-route honesty, and pre-start rejection of
  rate-mismatched fallbacks. `scripts/run_learn_python_quality.py` runs that
  file as `learn_auto_master_finder_pytest`; `verify_learn_package.py` emits
  `course3_auto_master_finder_contract`; and
  `run_learn_perfection_package.py` mirrors it as
  `quality_contract.python_quality.auto_master_finder=true`. Verification:
  Ruff passed for the touched scripts/tests, the focused package/verifier bundle
  passed 28 tests, the live-readiness/live-proof/lens bundle passed 95 tests,
  the focused auto-master contract passed 3 tests, and the full Learn
  perfection package passed all four package commands with
  `verification_refreshed=true`, `release_ready=false`, matrix `18/21`. The
  same three release blockers remain.
- A one-hundred-fifty-seventh slice makes Course 3 count-ins work in the actual
  two-deck `mix` posture without guessing. `src/vibemix/state/refresh.py` now
  resolves a Course 3 phrase anchor from `audible_deck="mix"` only when the
  Now Playing title exactly and unambiguously matches one citable deck row;
  duplicate title matches still abstain and keep `next_phrase_cue_id=null`.
  `tests/state/test_refresh.py` pins the old single-deck cue path, the new
  unambiguous mix-title cue path, and the ambiguous duplicate-title abstention.
  `scripts/run_learn_python_quality.py` runs those tests as
  `learn_course3_mix_anchor_pytest`; `verify_learn_package.py` emits
  `course3_mix_count_in_anchor_contract`; and
  `run_learn_perfection_package.py` mirrors it as
  `quality_contract.python_quality.course3_mix_anchor=true`. Verification:
  Ruff passed for the touched state/package/verifier files, the focused
  package/verifier bundle passed 28 tests, the broader refresh/ws/lens bundle
  passed 67 tests, the named mix-anchor command passed 3 tests, and the full
  Learn perfection package passed all four package commands with
  `verification_refreshed=true`, `release_ready=false`, matrix `19/22`. The
  same three release blockers remain.
- A one-hundred-fifty-eighth slice hardens the practice booth for the real
  unplugged-controller state. `tauri/ui/src/learn/learn-window.ts` now caches
  the active lesson highlight and replays it after the default on-screen deck
  finishes its async SVG import, covering both first-paint races and mid-lesson
  controller disconnects. When the DDJ drops, the UI remounts the screen deck,
  restores the highlighted control, keeps the lesson map hidden, and still emits
  the same `ipc.learn.ack` from the on-screen control. The package verifier's
  `frontstage_simplicity_contract.evidence.hardware_unavailable` now names this
  behavior explicitly. Verification: the focused booth Vitest spec passed 23
  tests, `tests/learn/test_verify_learn_package.py` passed 16 tests, Ruff passed
  for the verifier/test pair, the standalone Learn frontend quality runner
  passed all eight commands, and the full Learn perfection package passed all
  four package commands with `verification_refreshed=true`,
  `release_ready=false`, matrix `19/22`. The same three release blockers remain.
- A one-hundred-fifty-ninth slice proves browser-to-Python adaptive coaching on
  the real on-screen deck. `browser-python-beginner-path.pw.ts` now starts
  `L1.03` against the Python Learn harness, clicks the wrong on-screen mid-EQ
  control, verifies the grounded hint with `[screen:eq_mid:A]` and
  `[screen:eq_hi:A]` citations plus `teaching_loop.turn_kind=adapt`, then
  clicks the correct high-EQ control and proves `L1.03` completes in persisted
  progress. That e2e
  exposed an actual SVG hit-region weakness: accessible SVG control groups can
  have unpainted centers, so browser clicks could miss the group even though the
  control looked interactive. `learn-window.ts` now resolves a control from the
  pointer coordinates when the event target is the SVG/stage, and `learn.css`
  opts SVG controls into bounding-box hit testing. Verification: the focused
  browser Python path passed all 3 Playwright tests, booth Vitest passed 23
  tests, production frontend build passed, verifier tests passed 16, Ruff
  passed for the verifier/test pair, the frontend quality runner passed all 8
  commands, and the full Learn perfection package passed all four package
  commands with `verification_refreshed=true`, `release_ready=false`, matrix
  `19/22`. The same three release blockers remain.
- A one-hundred-sixtieth slice turns future-course readiness from a checklist
  into an executable preflight. `vibemix.learn.lesson_flow` now exposes
  `build_lesson_flow_from_meta(...)` so draft lessons can compile through the
  same structured-flow engine before they are merged into global curriculum
  tables. New `vibemix.learn.course_pack.validate_course_pack_draft(...)`
  validates a future course's `CourseMeta`, frame text, `LessonMeta` rows,
  transcript metadata, expected action, three-hint floor, observed backstage
  capabilities, transcript/id collisions, and required progress fields. The
  package verifier now records this as
  `future_course_extension_contract.evidence.draft_validator`, and the Python
  quality artifact has a dedicated `learn_course_pack_pytest` command. This
  keeps the frontstage simple while giving future intermediate/pro courses a
  real backstage gate. Verification: focused Ruff passed for the touched Learn,
  script, and test files; the focused course-pack/curriculum/verifier bundle
  passed 75 tests; curriculum codegen stayed up to date; and the full Learn
  perfection package passed all four package commands with
  `verification_refreshed=true`, `release_ready=false`, matrix `19/22`. The
  same three release blockers remain.
- A one-hundred-sixty-first slice makes the course-pack preflight usable from
  disk. `src/vibemix/learn/course_pack.py` now loads a JSON course-pack
  manifest with `schema_version=1`, course metadata, frame text, lesson rows,
  and transcript fixtures, then validates it without mutating
  `COURSE_REGISTRY` or `CURRICULUM`. New
  `scripts/validate_learn_course_pack.py` is the operator/agent CLI:
  `uv run python scripts/validate_learn_course_pack.py <course-pack.json>`.
  It writes a JSON report and exits `0` only when the draft compiles and its
  capabilities/progress-field needs are explicit. The package contract now
  records both the function and CLI under `draft_validator`, and the verifier
  treats missing CLI support as an incomplete future-course extension contract.
  Verification: focused Ruff passed for the touched files, the focused
  course-pack/curriculum/verifier tests passed 33 tests, curriculum codegen
  stayed current, `git diff --check` passed for the touched files, and the full
  Learn perfection package passed all four commands with
  `verification_refreshed=true`, `release_ready=false`, matrix `19/22`. The
  same three release blockers remain.
- A one-hundred-sixty-second slice makes the remaining release blockers
  handoff-executable instead of scattered across proof artifacts.
  `scripts/verify_learn_package.py` now emits top-level
  `release_blocker_recipe` rows for `packaged_eq_exemplar_ear_pass`,
  `physical_controller_path`, and `course3_live_audio_play_mode`. Each row
  carries the current status, the human/manual action, the exact follow-up
  commands, and the relevant evidence payload: the EQ bank fingerprint for
  ear-pass, DDJ list/readiness/proof commands for physical proof, and the
  current BlackHole/Rekordbox route diagnosis plus operator steps for Course 3.
  The verifier tests assert that those rows exist while release is blocked and
  that the recipe becomes empty when the package is release-ready. Verification:
  focused Ruff passed for the verifier/test pair, the focused verifier tests
  passed 16 tests, the package verifier artifact refreshed with
  `technical_passed=true`, and the full Learn perfection package passed all
  four commands (`python_quality`, `frontend_quality`, `desktop_quality`,
  `package_verifier`) with `verification_refreshed=true`,
  `release_ready=false`, matrix `19/22`. The same three release blockers
  remain, but the next operator path is now explicit.
- A one-hundred-sixty-third slice mirrors that operator path into the
  all-in-one perfection-package artifact. `scripts/run_learn_perfection_package.py`
  now copies the verifier's `release_blocker_recipe` into
  `/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`, prints
  `release_blocker_recipe_ids` in its command summary, and exposes
  `quality_contract.python_quality.course_pack_preflight=true` when the package
  pass included `learn_course_pack_pytest`. This makes the single package file a
  usable handoff artifact for both remaining proof work and future-course
  extension work. Verification: focused Ruff passed for the package runner/test
  pair, `tests/learn/test_run_learn_perfection_package.py` passed 6 tests, and
  the full Learn perfection package passed all four commands with
  `verification_refreshed=true`, `release_ready=false`, matrix `19/22`, recipe
  ids `packaged_eq_exemplar_ear_pass`, `physical_controller_path`, and
  `course3_live_audio_play_mode`. The same three external release blockers
  remain.
- A one-hundred-sixty-fourth slice fixes a stale-progress edge in the calm
  booth. `src/vibemix/learn/ipc_handlers.py` now emits the emptied
  `LearnProgress.snapshot()` inside `ipc.learn.progress_state` `reset_ack`, and
  `tauri/ui/src/learn/learn-window.ts` treats `reset_ack` with `progress` as a
  chooser refresh just like a `snapshot`. This means a settings reset clears
  stale recommended lessons, course locks, and replay state immediately instead
  of waiting for a later snapshot. `tests/learn/test_ipc_handlers_dispatch.py`
  pins the emptied reset-ack payload, and
  `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts` now proves reset
  returns the booth to `start opening dialog` while keeping the map opt-in. The
  same slice also hardens `scripts/run_learn_desktop_quality.py` against the
  observed Vite generated-dist cleanup flake (`ENOTEMPTY` while removing
  `tauri/ui/dist/assets`) by retrying that exact build after clearing the
  generated `dist` directory; `tests/learn/test_run_learn_desktop_quality.py`
  pins the retry. Verification: focused Ruff passed for the touched Python
  files, focused Python reset/desktop tests passed 7 tests, the focused booth
  Vitest passed 24 tests, standalone desktop quality passed, and the full Learn
  perfection package passed all four commands with `verification_refreshed=true`,
  `release_ready=false`, matrix `19/22`. The same three external release
  blockers remain.
- A one-hundred-sixty-fifth slice captures the live FLX4 hardware learning from
  the desk. The user plugged in a DDJ-FLX4, and `uv run python
  scripts/sniff_controller.py --list` resolved `DDJ-FLX4`. A raw callback sniff
  with the user rotating the left jog wheel captured 5,276 frames in 18 s,
  including left-jog CC `33` / `0x21` with non-neutral values `62`, `63`, `65`,
  and `66` plus jog-touch note `54`; `unique_cc=[0,32,33,34]` and
  `unique_notes=[54]`. This proves the physical controller, user motion, CoreMIDI
  path, and `pioneer_ddj_flx4.json` jog mapping are good enough for the Learn
  lesson. The strict app-bus proof still failed earlier: L1.07 loaded on
  `ws://127.0.0.1:8765` with `controller_id=pioneer_ddj_flx4` and emitted a
  baseline `ipc.learn.midi_position`, but sampled `jog:A` stayed `0`, so no
  app-bus ACK or advance was proven. Conclusion: do not spend more time proving
  raw MIDI mapping. The remaining work is to catch or harden the live sidecar
  listener plus `MidiMirror.events_since(...)` path so relative jog pulses
  survive to the socket as `jog:A=127` during L1.07.
- A one-hundred-sixty-sixth slice adds a small but important operator cue to
  the hardware proof harness. `scripts/live_learn_socket_jog_probe.py` now has
  optional `say_prompts=True` / `--say-prompts`, and
  `scripts/run_learn_live_proof.py` exposes it as `--say-physical-prompts`.
  On macOS the proof speaks the moment it needs the operator to move the left
  jog wheel via `say(1)`; it is fail-soft and disabled by default so CI and
  unattended runs stay quiet. Verification: focused Ruff passed for the probe,
  live proof wrapper, and socket-probe tests; `tests/learn/test_live_learn_socket_jog_probe.py`
  passed 7 tests, including the new macOS `say` invocation and quiet-disabled
  guards.
- A one-hundred-sixty-seventh slice clears the physical DDJ-FLX4 Learn proof
  and records the UX lesson. The strict live app run at
  `/tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json` passed:
  L1.07 loaded with `controller_id=pioneer_ddj_flx4`, the live socket saw the
  left jog as `jog:A=127`, the probe sent the ACK, and the lesson advanced. The
  useful human-learning is not just technical. Any proof or lesson that asks for
  a timed hardware move should speak the moment on macOS with `say(1)` when the
  operator opts in, because the student is looking at the controller, not the
  terminal. Keep that audible cue fail-soft and artifact-backed via
  `operator_prompt_spoken`, not as a mandatory runtime dependency. The current
  package verifier now treats physical and screen live proofs as passed; the
  remaining release blockers are packaged EQ exemplar ear-pass, launched Tauri
  smoke artifact alignment, and Course 3 routed-audio count-in proof.
- A one-hundred-sixty-eighth slice fixes the launched Tauri smoke artifact
  alignment and refreshes the full deterministic package. The smoke script now
  writes `/tmp/vibemix-live-learn-proof/learn-tauri-smoke-current.json` by
  default, still supports `--out`, and handles `--help` before creating its temp
  run directory. A focused contract test pins the default artifact path, and
  `node --check`, Ruff for the verifier test, and the `tauri_smoke` verifier
  tests passed. The real launched Tauri smoke then passed through the Learn
  WebviewWindow and wrote an artifact with `passed=true`,
  `completed_lesson_id=L1.01`, `l101_completed=true`, `quality_ok=true`,
  `quality_check_count=17`, and no failures. The full
  `run_learn_perfection_package.py` pass then refreshed Python, frontend,
  desktop, and package verification with all four commands passing:
  `python_quality` 21.459 s, `frontend_quality` 33.859 s, `desktop_quality`
  16.177 s, and `package_verifier` 0.436 s. Current package state is
  `passed=true`, `technical_passed=true`, `release_ready=false`, matrix
  `20/22`, and the release blocker recipe is down to exactly two rows:
  `packaged_eq_exemplar_ear_pass` and `course3_live_audio_play_mode`.
- A one-hundred-sixty-ninth slice records the latest Course 3 desk truth rather
  than guessing. `learn_live_readiness.py --require course3` exited 4 and wrote
  `/tmp/vibemix-live-learn-proof/learn-course3-readiness-current.json`.
  BlackHole 16ch and 2ch are visible at 48 kHz, and the BlackHole 16ch
  self-test passed (`rms=0.048799`), so the loopback device itself is usable.
  But direct loopback capture stayed silent (`rms=0.0`), every sampled
  DJ/loopback capture input stayed below the signal floor, macOS output is
  `MacBook Pro Speakers`, Rekordbox settings currently point at `DDJ-FLX4 @
  44100Hz`, the sidecar was not running during readiness, and Now Playing is a
  paused WebKit source rather than Rekordbox. Conclusion: Course 3 remains an
  external routing/playback proof problem, not a Learn curriculum or Tauri smoke
  problem. The next real proof needs Rekordbox master routed into a 48 kHz
  BlackHole/loopback path, deck playback active, channel/master faders up, and a
  citable Rekordbox/library title.
- A one-hundred-seventieth slice carries the "speak the human-timed moment"
  lesson from hardware into Course 3. `scripts/run_learn_live_proof.py` now has
  `--say-course3-prompts`, a fail-soft macOS `say(1)` cue that fires only when
  Course 3 signal is absent and the proof needs external route/playback action:
  route Rekordbox master to BlackHole, press play on a deck, and raise
  channel/master faders. The prompt is recorded as a
  `course3_operator_prompt` stage with `spoken`, `skipped`, and precheck signal
  fields, so it is inspectable instead of magical. `verify_learn_package.py`
  now includes `--say-course3-prompts` in the generated
  `course3_live_audio_play_mode` release-blocker proof command. Verification:
  Ruff passed for the live-proof runner, verifier, and focused tests; the
  combined live-proof/verifier pytest files passed 54; the full Learn
  perfection package refreshed with all four commands passing and remains
  `passed=true`, `technical_passed=true`, `release_ready=false`, matrix `20/22`.
- A one-hundred-seventy-first slice makes the remaining EQ ear-pass recipe more
  actionable without weakening the human approval gate. `verify_learn_package.py`
  now fail-soft enriches the exemplar section with current sounddevice output
  rows and `ear_pass_operator_action(...)`, then copies that full
  `operator_action` and `operator_steps` into `release_blocker_recipe`. On this
  Mac the current refreshed package recommends `MacBook Pro Speakers` at device
  index `3`, with `HEADPHONEMG` at index `5` as the next audible fallback, and
  still rejects loopback/capture sinks for human listening. The approval command
  remains hash/fingerprint-bound, so this is only better operator guidance, not
  a fake ear-pass. Verification: Ruff passed for the verifier files,
  `tests/learn/test_verify_learn_package.py` passed 18, and the full Learn
  perfection package refreshed with all four commands passing:
  `passed=true`, `technical_passed=true`, `release_ready=false`, matrix `20/22`.
- A one-hundred-seventy-second slice removes the last null operator-action hole
  from the blocker recipe. When Course 3 has a diagnosis but no authored
  `operator_action`, `verify_learn_package.py` now synthesizes one from the
  current selected/fallback route: stop unrelated system audio, route Rekordbox
  master/output to the selected loopback (currently `BlackHole 2ch @ 48000Hz`),
  load and play a real Rekordbox library track, raise channel/master faders
  until loopback capture has signal, then rerun the proof command. The generated
  proof still includes `--say-course3-prompts`. Verification: Ruff passed for
  the verifier files, focused verifier tests passed, the full verifier test
  file passed 18, and the full Learn perfection package refreshed with all four
  commands passing: `passed=true`, `technical_passed=true`,
  `release_ready=false`, matrix `20/22`.
- A one-hundred-seventy-third slice adds spoken labels to the EQ exemplar
  audition path. `scripts/audition_learn_exemplars.py --play` now accepts
  `--say-prompts`; on macOS it fail-soft speaks a short band label such as
  "sub EQ exemplar" before each loop, records playback metadata including
  `spoken_prompt_count`, and stays quiet unless explicitly requested. The
  release-blocker recipe now suggests
  `uv run python scripts/audition_learn_exemplars.py --play --device-index 3 --say-prompts
  --out /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json`
  for this Mac's current `MacBook Pro Speakers` output, so the audition leaves a
  durable playback summary before approval. Verification: Ruff passed for the
  audition/verifier files, focused tests passed 7, the full exemplar+verifier
  test pair passed 34, and the full Learn perfection package refreshed with all
  four commands passing: `passed=true`, `technical_passed=true`,
  `release_ready=false`, matrix `20/22`.
- A one-hundred-seventy-fourth slice makes the audible audition memory
  enforceable instead of merely suggested. `--approve-ear-pass` now requires a
  matching `/tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json`
  playback artifact from `--play --say-prompts`, validates the current
  `bank_fingerprint`, track count, output `device_index`, and playback metadata,
  and refuses to write the approval artifact until that proof exists. This keeps
  the Mac `say(1)` cue useful for human attention without turning it into fake
  release evidence. Verification: Ruff passed for the audition/verifier files,
  the focused exemplar+verifier test pair passed 37, and the full Learn
  perfection package refreshed with all four commands passing: `passed=true`,
  `technical_passed=true`, `release_ready=false`, matrix `20/22`.
- A one-hundred-seventy-fifth slice closes the quiet physical-proof recipe gap.
  The handoff already said hardware prompts should speak on macOS, but the
  verifier-generated physical proof command still lacked
  `--say-physical-prompts`. `verify_learn_package.py` now emits that flag for
  the physical DDJ proof, keeps Course 3 on `--say-course3-prompts`, and keeps
  EQ audition on `--say-prompts` plus a required `--audition` artifact. The
  verifier tests pin all three operator-audio paths. Verification: Ruff passed
  for the verifier files, `tests/learn/test_verify_learn_package.py` passed 18,
  and the full Learn perfection package refreshed with all four commands
  passing: `passed=true`, `technical_passed=true`, `release_ready=false`,
  matrix `20/22`.
- A one-hundred-seventy-sixth slice hardens the future-course path against
  sloppy IDs. `validate_course_pack_draft(...)` now rejects draft
  `course_id` values that do not look like `course_<number>_<slug>`, lesson IDs
  that do not look like `L<number>.<two digits>`, lesson numbers that do not
  match the course number, and non-contiguous lesson ordinals. The curriculum
  audit now exposes `canonical_id_contract`, and the package verifier requires
  it in `future_course_extension_contract`. Verification: Ruff passed for the
  course-pack/audit/verifier files, the focused course-pack/audit/verifier
  tests passed 34, and the full Learn perfection package refreshed with all
  four commands passing: `passed=true`, `technical_passed=true`,
  `release_ready=false`, matrix `20/22`.
- A one-hundred-seventy-seventh slice makes future-course creation start from a
  valid template instead of an empty manifest. `course_pack.py` now exposes
  `course_pack_template(...)` and `write_course_pack_template(...)`, while
  `scripts/validate_learn_course_pack.py --init-template <dir> --course-number
  4 --slug <slug>` writes `course-pack.json` plus transcript fixtures, refuses
  overwrites unless `--force` is supplied, and immediately validates the result.
  The curriculum audit and package verifier now surface the template CLI in the
  `future_course_extension_contract`. Verification: Ruff passed for the
  course-pack/audit/CLI/verifier files, the focused course-pack/audit/verifier
  tests passed 37, the template smoke wrote a 2-lesson starter pack with zero
  validation errors, and the full Learn perfection package refreshed with all
  four commands passing: `passed=true`, `technical_passed=true`,
  `release_ready=false`, matrix `20/22`.
- A one-hundred-seventy-eighth slice makes future-course validation more
  inspectable. `CoursePackValidation.to_dict()` now includes `flow_preview`,
  a compact per-lesson preview of compiled step IDs, prompts, verifier kind,
  observable controls, input surfaces, backstage lenses, and hint counts. The
  course-pack contract and package verifier require that field, so future
  courses prove their calm one-action practice flow before merging into
  `CURRICULUM`. Verification: Ruff passed for the course-pack/audit/verifier
  files, the focused course-pack/audit/verifier tests passed 37, the template
  smoke showed `L4.01`/`L4.02` preview rows with `cue:A`,
  `hardware`/`screen`, `button_press`, and three hints, and the full Learn
  perfection package refreshed with all four commands passing: `passed=true`,
  `technical_passed=true`, `release_ready=false`, matrix `20/22`.
- A one-hundred-seventy-ninth slice shares the copy-truthfulness guard with
  future course packs. The unwired debrief auto-open phrase list now lives in
  `vibemix.learn.copy_truth`, and `validate_course_pack_draft(...)` rejects
  draft transcript copy that promises behavior like "the debrief opens
  automatically" before a runtime/frontend open-debrief command exists.
  `CoursePackValidation.to_dict()` now includes `copy_truthfulness`, and the
  package verifier requires that result field plus the course-pack
  copy-truthfulness contract. Verification: Ruff passed for the shared guard,
  course-pack/audit/verifier files, focused tests passed 38, a bad-copy draft
  smoke returned `ok=false` with
  `draft_transcript_debrief_auto_open_unwired`, and the full Learn perfection
  package refreshed with all four commands passing: `passed=true`,
  `technical_passed=true`, `release_ready=false`, matrix `20/22`.
- A one-hundred-eightieth slice tightens the "alive, not syllabus" frontstage.
  Quality read: Learn had strong proof plumbing, but a correct action vanished
  too quietly into the next instruction. The fix is deliberately small and
  deterministic: `TutorSpeakDock.advance(...)` now accepts an action-matched
  receipt and shows a quiet `clean touch · 01` style tick in the existing
  receipt row, while the practice booth keeps a one-line pulse such as
  `clean pass · 1 move` after completion and immediately offers the next
  recommended lesson. No new page, no badge wall, no generative praise loop.
  The Course 3 route-doctor packet was also pinned on the readiness summary, so
  release blockers can carry spoken-prompt proof commands and exact operator
  steps. Verification: `npx impeccable detect --json` returned no findings for
  the touched Learn TS files, focused Learn UI tests passed 29, the live
  readiness test module passed 55, Ruff passed for the readiness files, and
  `npm --prefix tauri/ui run build` passed.
- A one-hundred-eighty-first slice makes Course 3 readiness less misleading
  when another local service owns the shared app socket. `check_socket(...)`
  now records the process listening on `127.0.0.1:8765` after a failed
  WebSocket handshake, and `build_summary(...)` turns that into a concrete
  blocker such as `port 8765 is occupied by python3.1 pid 85484, not the
  Vibemix Learn sidecar websocket`. This matters because the live desk had a
  `mithril` uvicorn process on `:8765`, producing `HTTP 403`; the old wording
  looked like the sidecar was merely absent. Verification: Ruff passed for the
  readiness files, `tests/learn/test_learn_live_readiness.py` passed 57, a
  fresh Course 3 readiness artifact now names the foreign listener, and the
  full Learn perfection package refreshed current with all four commands
  passing: `passed=true`, `technical_passed=true`, `release_ready=false`,
  matrix `20/22`.
- A one-hundred-eighty-second slice turns the quality analysis into a useful
  live handoff instead of a stale proof summary. `build_course3_route_doctor(...)`
  now converts current readiness blockers into ordered operator steps and
  dedupes equivalent route/switch-output wording. `verify_learn_package.py`
  now discovers `learn-course3-readiness-current.json`, merges its diagnosis,
  route doctor, blockers, and auto-master recommendation into the Course 3
  release recipe, and still refuses to mark Course 3 proven until the routed
  count-in proof passes. The current desk probe shows the sidecar socket is
  healthy, but macOS output is on `MacBook Pro Speakers`, Rekordbox is saved to
  `DDJ-FLX4` at `44100.0`, the BlackHole captures are silent, and Now Playing
  is WebKit media rather than Rekordbox. Verification: Ruff passed for the
  readiness/verifier files, focused readiness+verifier tests passed 77, and the
  full Learn perfection package passed all four commands with
  `technical_passed=true`, `release_ready=false`, matrix `20/22`, with only EQ
  ear-pass and Course 3 routed-audio proof remaining.
- A one-hundred-eighty-third slice wires those Course 3 blockers into the calm
  practice-booth frontstage without adding a diagnostic panel. When the Course 3
  live lens says the user is waiting for audio, deck attribution, a citable
  track, or cue lock, `StatusBar` now keeps the same one-line booth copy
  (`press play on deck`, `open one channel`, `load a track`, `keep playing`) but
  marks it as an active operator action and carries the deterministic next
  steps in aria/title text. `operatorActionAriaLabel(...)` now includes up to
  three bounded steps so the hidden review surface preserves the actual action
  sequence. The same pass caught and fixed a global webview type fixture drift
  in the pill next-suggestion test by adding required `camelot`/`bpm` fields.
  Verification: `npx impeccable detect --json` returned no findings for the
  touched Learn UI files, focused Learn/pill UI tests passed 103, production
  `npm --prefix tauri/ui run build` passed, and the full Learn perfection
  package passed all four commands with `technical_passed=true`,
  `release_ready=false`, matrix `20/22`.
- A one-hundred-eighty-fourth slice moves that Course 3 next-action decision
  into the live socket lens itself. `_serialize_course3_lens(...)` now emits a
  bounded `operator_action` from observed `MusicState` blockers whenever Course
  3 is active or audio is already audible: press play for missing audio, open
  one channel for unattributed audio, load a citable Rekordbox track when the
  audible deck lacks a grounded track, and keep playing while cue-section
  lookahead waits for phrase lock. It deliberately does not claim a concrete
  BlackHole route; route-specific guidance stays in `learn_live_readiness.py`,
  where the route evidence exists. Verification: Ruff passed for the runtime
  bus and Course 3 lens tests, focused Python live-lens tests passed 15,
  focused Learn socket/frontstage UI tests passed 34, and the full Learn
  perfection package passed all four commands with `technical_passed=true`,
  `release_ready=false`, matrix `20/22`.
- A one-hundred-eighty-fifth slice carries that runtime action through the live
  proof tooling. `live_course3_lens_probe.py` now promotes the last observed
  lens `operator_action` into the probe summary and repeats it under
  `diagnostics.operator_action`; `validate_learn_live_proof.py` surfaces that
  prompt as a `course3 operator action: ...` validation error when the Course 3
  proof still fails. This does not make a failed proof pass; it makes the
  artifact explain the observed next move alongside the strict count-in
  failure. Verification: Ruff passed for the probe/validator files and focused
  tests, focused live-lens/proof-validator tests passed 30, and the full Learn
  perfection package passed all four commands with `technical_passed=true`,
  `release_ready=false`, matrix `20/22`.
- A one-hundred-eighty-sixth slice makes that same failed-proof action a package
  verifier contract. `verify_learn_package.py` now extracts Course 3
  `operator_action` from the probe result, diagnostics, last lens, or readiness
  wait stage, scores richer failed/unavailable Course 3 attempts higher, carries
  `probe_operator_action` into the live-proof section and completion matrix, and
  uses it as the release-recipe/manual next action when no stronger route
  doctor exists. The current real desk artifact still shows no live probe
  operator action because the Course 3 socket lens stayed cold; the route doctor
  correctly remains the stronger handoff: route macOS/Rekordbox output to
  BlackHole/loopback, play a real Rekordbox track, and stop unrelated WebKit
  media. Verification: Ruff passed for the verifier files, focused verifier
  tests passed 20, and the full Learn perfection package passed all four
  commands with `technical_passed=true`, `release_ready=false`, matrix `20/22`.
- A one-hundred-eighty-seventh slice adds restrained liveliness to the practice
  booth without adding another progress system. `learn-window.ts` now derives
  the tiny post-action receipt from the current expected control when that
  context exists: high/mid/low EQ becomes `eq turn`, jog becomes `jog nudge`,
  channel volume becomes `fader lift`, cue becomes `cue hit`, and so on. The
  old deterministic label cycle remains as the fallback when no highlight has
  established an expected action. This makes the booth feel like it noticed the
  exact move, while still staying inside the existing receipt row and not
  becoming a badge wall. Verification: `npx impeccable detect --json` returned
  no findings for the touched files, focused tutor receipt tests passed 5,
  focused Learn UI tests passed 34, `npm --prefix tauri/ui run build` passed,
  and the full Learn perfection package passed all four commands with
  `technical_passed=true`, `release_ready=false`, matrix `20/22`.
- A one-hundred-eighty-eighth slice hardens the DDJ-FLX4 connection preflight
  against the Bluetooth-MIDI trap. `learn_live_readiness.py` now detects
  controller-looking MIDI ports whose transport name includes Bluetooth/BLE/BT;
  when that is the only FLX4 evidence and USB/controller-audio is absent,
  physical readiness says `DDJ-FLX4 is visible only as Bluetooth MIDI; connect
  it by USB for Learn hardware/audio proof` instead of the generic USB/audio
  blocker. Course 3 gets the matching audio warning and route-doctor step:
  Bluetooth MIDI is not enough for routed-audio proof. A live check after the
  user plugged the DDJ showed no MIDI ports, no USB FLX4, and no controller
  audio device yet; only Rekordbox's saved settings still mention `DDJ-FLX4 @
  44100Hz`, so the Mac has not enumerated the controller. Verification: Ruff
  passed for the readiness files, `tests/learn/test_learn_live_readiness.py`
  passed 60, and the full Learn perfection package passed all four commands
  with `technical_passed=true`, `release_ready=false`, matrix `20/22`.
- A one-hundred-eighty-ninth slice makes the physical-controller failure mode a
  first-class doctor, not just blockers. `learn_live_readiness.py` now emits
  `physical_connection_doctor` for `--require physical`, with `next_step`,
  bounded operator steps, readiness/proof commands, and a
  `uses_spoken_prompt=true` flag. The doctor distinguishes Bluetooth-MIDI-only,
  missing MIDI, and missing USB/controller-audio states, then tells the
  operator whether to use USB instead of Bluetooth, use a data-capable cable or
  powered adapter, or wait for DDJ-FLX4 in macOS MIDI/audio devices.
  `verify_learn_package.py` now preserves that doctor from embedded live-proof
  readiness stages into `sections.live_proofs.physical`, the completion matrix,
  release blocker recipe, and `next_actions` without changing pass/fail
  semantics. Verification: Ruff passed for readiness/verifier files and focused
  readiness+verifier tests passed 81, and the full Learn perfection package
  passed all four commands with `technical_passed=true`, `release_ready=false`,
  matrix `20/22`.
- A one-hundred-ninetieth slice makes standalone physical readiness artifacts
  part of the verifier contract. `verify_learn_package.py` now discovers
  `/tmp/vibemix-live-learn-proof/learn-physical-readiness-current.json` (or
  accepts `--physical-readiness`), attaches it as
  `sections.live_proofs.physical.readiness_status`, and merges its
  `physical_connection_doctor`/`hardware_connection` into the physical report
  only when the strict physical proof is not already passed. This prevents a
  fresh USB/DDJ readiness check from downgrading the already-cleared L1.07
  app-bus proof while still giving the next operator an exact doctor if the
  proof is missing. After the user reloaded the DDJ, `sniff_controller.py
  --list` returned `DDJ-FLX4`; `learn_live_readiness.py --require physical`
  passed with MIDI, USB/audio, and controller hardware ready, and the doctor
  now says the next move is to nudge the left jog wheel during the L1.07 proof
  window. Verification: Ruff passed for the verifier files, focused verifier
  tests passed 23, standalone frontend quality passed all eight Learn UI/build
  commands, and the full Learn perfection package passed all four commands with
  `verification_refreshed=true`, `technical_passed=true`, `release_ready=false`,
  matrix `20/22`. The only release blockers remain the packaged EQ exemplar
  ear-pass and Course 3 routed-audio/count-in proof.
- A one-hundred-ninety-first slice makes the Course 3 route doctor match the
  live desk's actual Aggregate Device shape. `learn_live_readiness.py` now
  treats a CoreAudio capture row named `rekordbox Aggregate Device` as the
  sampled alias of Rekordbox's saved `Aggregate Device` output, carries that
  alias into auto-master candidate evidence, and diagnoses the current failure
  as `rekordbox_saved_route_capture_rate_mismatch` instead of the older generic
  `macos_output_not_loopback`. The release recipe now leads with the specific
  operator action: set Rekordbox's `Aggregate Device` route, sampled as
  `rekordbox Aggregate Device`, from 44100Hz to 48000Hz in Audio MIDI Setup or
  choose a 48k BlackHole/aggregate route, then play a deck with channel and
  master faders up. It still preserves the other necessary steps: route
  Rekordbox/master output to the intended capture, play a real Rekordbox
  library track, and stop WebKit/system media so Now Playing can become
  citable. Verification: Ruff passed for the readiness files, focused
  live-readiness tests passed 62, the refreshed live Course 3 readiness artifact
  shows the new `fix_rate` doctor on the real DDJ/Rekordbox desk, standalone
  desktop quality passed, and the full Learn perfection package passed all four
  commands with `verification_refreshed=true`, `technical_passed=true`,
  `release_ready=false`, matrix `20/22`.
- A one-hundred-ninety-second slice prevents the spoken Course 3 proof runner
  from drifting behind the route doctor. `run_learn_live_proof.py` now derives
  its Course 3 operator prompt from `course3_route_doctor.next_step`, falls back
  to `course3_audio_diagnosis.next_action`, and only then uses the old generic
  BlackHole prompt. The `course3_operator_prompt` stage records
  `prompt_source`, `diagnosis_code`, `route`, and `operator_steps`, so a failed
  live proof can be audited against the exact advice the Mac spoke. On the
  current desk that means the spoken first move is the Aggregate Device
  44100Hz-to-48000Hz fix, not a vague "route to BlackHole" reminder.
  Verification: Ruff passed for the proof-runner files, focused
  `test_run_learn_live_proof.py` passed 40 tests, and the refreshed full Learn
  perfection package passed all four commands with `verification_refreshed=true`,
  `technical_passed=true`, `release_ready=false`, matrix `20/22`.
- A one-hundred-ninety-third slice keeps the calm frontstage from oversimplifying
  the new rate doctor into the wrong instruction. `learn_live_readiness.py` now
  attaches a structured `operator_action` to Course 3 sample-rate diagnoses,
  including `route`, `current_rekordbox_route`, `current_capture_route`,
  `target_capture_route`, and exact ordered steps. For the current desk, that
  separates Rekordbox's saved `Aggregate Device @ 48000Hz` from the sampled
  `rekordbox Aggregate Device @ 44100Hz`, with target
  `rekordbox Aggregate Device @ 48000Hz`. `operator-action.ts` now compresses
  those rate-fix actions into the booth-sized label `set aggregate route to 48k`
  instead of the misleading `play Rekordbox from deck`, while preserving the
  full route and steps in aria/title text. Verification: Ruff passed for the
  readiness files, focused live-readiness tests passed 62, focused verifier and
  proof-runner tests passed 63, focused Learn UI tests passed 30, the refreshed
  real Course 3 readiness artifact has the structured route fields above, and
  the full Learn perfection package passed all four commands with
  `verification_refreshed=true`, `technical_passed=true`, `release_ready=false`,
  matrix `20/22`.
- A one-hundred-ninety-fourth slice makes the refreshed perfection package
  artifact self-contained for handoff tooling. `run_learn_perfection_package.py`
  already printed `release_blocker_recipe_ids` to stdout, but the saved
  `/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json` only
  contained the full recipe rows. The package report now persists
  `release_blocker_recipe_ids` beside `release_blocker_recipe`, filtering blank
  or malformed rows, so downstream integration can read the durable artifact
  directly and see `packaged_eq_exemplar_ear_pass` and
  `course3_live_audio_play_mode` without recomputing. Verification: Ruff passed
  for the package-runner files, focused package-runner tests passed 6, the full
  Learn perfection package passed all four commands with
  `verification_refreshed=true`, `technical_passed=true`, `release_ready=false`,
  matrix `20/22`, and the saved package artifact now contains the two blocker
  IDs.
- A one-hundred-ninety-fifth slice tightens the Course 3 route doctor after the
  operator fixed the aggregate sample rate live. Once the real desk moved
  `rekordbox Aggregate Device` to 48000Hz, readiness correctly left the
  `fix_rate` state and exposed the next blocker: no sampled DJ/loopback input
  had signal, and Now Playing still held a stale WebKit title. The route doctor
  now preserves structured `operator_action.steps` before generic blocker
  steps, so its `next_step` becomes `Stop unrelated media or make Rekordbox the
  active playing source` instead of falling back to generic routing. The saved
  Rekordbox route can also be `DDJ-FLX4`; `_rekordbox_saved_rate_mismatch(...)`
  now detects non-loopback saved routes when the sampled capture row is 48k but
  Rekordbox's saved rate is stale. Focused readiness tests passed 63. A fresh
  live readiness run then showed the actual port state is clean
  (`python3 -m vibemix` owns `127.0.0.1:8765` and the websocket handshake is
  valid), the current Rekordbox route is `DDJ-FLX4 @ 48000Hz`, and the remaining
  external blocker is still real master audio plus citable Rekordbox metadata,
  not the app socket.
- A one-hundred-ninety-sixth slice refreshed the full package after the
  transient TypeScript build artifact. The current
  `/tmp/vibemix-live-learn-proof/learn-desktop-quality-current.json` passes
  `learn_tauri_frontend_dist_build`, `learn_cargo_fmt`, `learn_cargo_check`,
  `learn_cargo_learn_window_test`, and `learn_cargo_sidecar_audio_test`.
  The current `/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`
  passes all four package commands (`python_quality`, `frontend_quality`,
  `desktop_quality`, `package_verifier`) with `verification_refreshed=true`.
  Its `verification_summary` reports `technical_passed=true`,
  `release_ready=false`, matrix `20/22`, and exactly two blockers:
  packaged EQ exemplar human ear-pass and Course 3 routed-audio count-in proof.
  The durable `release_blocker_recipe_ids` are
  `packaged_eq_exemplar_ear_pass` and `course3_live_audio_play_mode`.
- A one-hundred-ninety-seventh slice pivots away from external proof looping
  and hardens the productive future-course path. Course-pack validation now
  emits a machine-readable `integration_plan` with `merge_ready`, exact target
  files, `COURSE_REGISTRY`/`COURSE_FRAMES`/`CURRICULUM` edit rows, transcript
  paths, progress-field edits for new locked courses, and the commands to run
  after merge. The curriculum audit and package verifier now require
  `integration_plan` in the draft-validator result fields, so future course
  integration is not just documented; it is release-matrix evidence. Verification:
  Ruff passed for course-pack/audit/verifier files, focused course-pack,
  curriculum-audit, and verifier tests passed 43, the template CLI smoke wrote
  a two-lesson `course_4_integration_plan_lab` pack and returned
  `integration_plan.merge_ready=true`, and the full Learn perfection package
  passed all four commands with `verification_refreshed=true`, still
  `release_ready=false` only for the two external gates.
- A one-hundred-ninety-eighth slice hardens graceful lesson choice without
  turning the booth into a syllabus wall. The optional progress map already
  marks completed lessons as replayable and keeps locked unfinished lessons
  visible but blocked. `renderProgressList(...)` now adds an `onLockedLesson`
  hook, and the real Learn window uses it to surface the existing
  `lock_reason` as a single booth pulse instead of a dead click or hidden
  console failure. Locked choices still emit no `ipc.learn.start_lesson`, and
  completed locked-course lessons still replay with `level="replay"`.
  Verification: focused Learn UI tests passed 56, frontend quality passed all
  eight rows including build, browser booth Playwright, and Learn E2E, and the
  full Learn perfection package passed all four commands with
  `verification_refreshed=true`, still `release_ready=false` only for the EQ
  ear-pass and Course 3 routed-audio count-in proof.
- A one-hundred-ninety-ninth slice makes "one clear prompt" a deterministic
  Learn contract instead of taste. `lesson_flow.py` now exposes shared
  frontstage prompt metrics with caps of 150 chars, 24 words, 2 sentences, one
  line, and no inline list shape. The curriculum audit enforces that contract
  for all governed beginner steps, records `prompt_contract` in every flow
  summary plus the global flow summary, and carries the single explicit
  exemption `L1.01.beat.3` because the opening dialog is byte-locked by the
  tone tests and is not a practice instruction. The future course-pack
  validator uses the same metrics, includes step-level `prompt_metrics`, emits
  a package-level `prompt_contract`, and rejects syllabus-wall draft prompts
  before they can merge. Three existing Course 2 and Course 3 prompts were
  tightened so all governed shipped prompts now top out at 115 chars, 23 words,
  and 2 sentences. Verification: Ruff passed for the touched Learn contract
  files, focused prompt/course-pack/verifier tests passed 95, the full Learn
  Python quality gate passed, the course-pack template smoke returned
  `validation.prompt_contract.ok=true`, and the full Learn perfection package
  passed all four commands with `verification_refreshed=true`,
  `technical_passed=true`, `release_ready=false`, matrix `20/22`.
- A two-hundredth slice adds a machine-readable objective audit on top of the
  existing completion matrix. `verify_learn_package.py` now emits
  `objective_audit`, grouping the user's broad Learn goal into nine objective
  promises: 36 structured lessons, calm practice-booth UX, physical/on-screen
  practice paths, grounded adaptive loop, existing coded-power reuse, Course 3
  live play mode, future-course extensibility, app wiring/quality, and audible
  example quality. The package runner includes the objective summary in
  `verification_summary`. Current artifact status: `7/9` objective groups are
  proven; the only blocking objective IDs are `course3_live_play_mode` and
  `audible_example_quality`, which correspond exactly to the two existing
  release blockers. Verification: Ruff passed for verifier/package-runner
  files, focused verifier/package-runner tests passed 29, and the full Learn
  perfection package passed all four commands with `verification_refreshed=true`,
  `technical_passed=true`, `release_ready=false`, matrix `20/22`,
  objective audit `7/9`.
- A two-hundred-first slice hardens authored adaptive hints from "present" to
  "grounded." `teaching_loop.py` now exposes
  `teaching_turn_is_grounded(...)`, checking that a tutor turn retains the
  Learn tutor route, active lesson and step, observed control, declared input
  surfaces, EvidenceRegistry lens, authored text/TTS marker, and deterministic
  verification spec. `curriculum_audit.py` now plans the first three hints for
  every compiled beginner step as real teaching-loop turns and records
  `hint_grounding_contract`; current artifacts prove `228/228` beginner hint
  turns grounded with no failing lessons. `verify_learn_package.py` now
  requires that contract before `teaching_loop_contract` can be marked proven.
  Verification: Ruff passed for the touched files, focused teaching-loop,
  curriculum-audit, and package-verifier tests passed 41, Python quality passed
  all rows, and the full Learn perfection package passed all four commands
  with `verification_refreshed=true`, `technical_passed=true`,
  `release_ready=false`, matrix `20/22`, objective audit `7/9`.
- A two-hundred-second slice makes that grounding visible and citation-backed.
  `teaching_loop.py` now falls empty authored teaching and hint citations back
  to `step_grounding_citations(...)`, a deterministic `[screen:<control>]` atom
  for the highlighted control. `runtime.py` uses those citations for normal
  tutor beats and timed hint strikes, and the runtime evidence test proves a
  timed hint's `[screen:eq_hi:A]` citation is backed by the EvidenceRegistry
  write from the current highlight. `tutor-dock.ts` now updates the existing
  citation chip for hint lines too, so the learner sees the grounded target
  without a second panel or a syllabus wall. The curriculum/package evidence
  now reports `hint_turn_count=228`, `grounded_hint_turn_count=228`, and
  `cited_hint_turn_count=228`. Verification: Ruff passed for touched files,
  focused Python tests passed 49, the tutor-dock Vitest passed 6, and the full
  Learn perfection package passed all four commands with
  `verification_refreshed=true`, `technical_passed=true`,
  `release_ready=false`, matrix `20/22`, objective audit `7/9`.
- A two-hundred-third slice pins the same grounding at browser level.
  `browser-python-beginner-path.pw.ts` now asserts the wrong on-screen EQ move
  renders `SCREEN DECK A MID EQ` in the tutor dock citation chip before the
  correct high-EQ move completes L1.03. `verify_learn_package.py` now promotes
  that as browser practice-booth evidence, so the package verifier no longer
  proves only invisible citation payloads for this path. Verification: Ruff
  passed for the verifier/test files, the focused browser/Python sidecar suite
  passed 3, package verifier tests passed 23, and the full Learn perfection
  package passed all four commands with `verification_refreshed=true`,
  `technical_passed=true`, `release_ready=false`, matrix `20/22`, objective
  audit `7/9`.
- A two-hundred-fourth slice extends deterministic grounding from hints to
  normal teaching turns. `curriculum_audit.py` now plans every compiled
  beginner step as a `plan_teaching_turn(...)`, requires
  `teaching_turn_is_grounded(...)`, and requires a citation, producing
  `teaching_grounding_contract`. `verify_learn_package.py` requires that
  contract before `teaching_loop_contract` can be marked proven. Current
  artifacts prove `teaching_turn_count=76`,
  `grounded_teaching_turn_count=76`, and `cited_teaching_turn_count=76` with
  no failing lessons, alongside the existing `228/228` hint grounding.
  Verification: focused teaching-loop/curriculum/verifier tests passed 42,
  the curriculum audit refreshed, and the full Learn perfection package passed
  all four commands with `verification_refreshed=true`,
  `technical_passed=true`, `release_ready=false`, matrix `20/22`, objective
  audit `7/9`.
- A two-hundred-fifth slice closes the remaining internal/completion ambiguity
  after the user explicitly deferred the ear pass and audio routing pass.
  `course_pack.py` now gives future course drafts the same grounded standard as
  the shipped 36 lessons: `CoursePackValidation` emits
  `teaching_grounding_contract` and `hint_grounding_contract`, rejects uncited
  normal teaching turns, and rejects uncited first-three hint turns before a
  draft can be merged. The course-pack contract surfaced by
  `curriculum_audit.py` now names those validator fields plus a
  `teaching_loop_contract`, and `verify_learn_package.py` requires them before
  `future_course_extension_contract` can be marked proven. The package verifier
  and perfection runner now also report `non_external_ready`: it is true only
  when deterministic package quality is green and every remaining blocker is
  one of the explicitly deferred external gates. Current artifacts report
  `passed=true`, `technical_passed=true`, `non_external_ready=true`,
  `internal_blocker_ids=[]`,
  `deferred_external_blocker_ids=["packaged_eq_exemplar_ear_pass",
  "course3_live_audio_play_mode"]`, `release_ready=false`, matrix `20/22`,
  and objective audit `7/9`. Verification: Ruff passed for touched files,
  focused course-pack/curriculum/verifier/runner tests passed 53, the
  curriculum audit refreshed, and the full Learn perfection package passed all
  four commands.
- A two-hundred-sixth slice adds a small but important character/QoL signal to
  the practice booth: matched action receipts now remember where the action
  came from. The existing receipt line still stays one compact row, but a
  hardware control move can read `eq turn · hardware · 01`, while an on-screen
  deck click can read `cue hit · screen · 02`. The MIDI delta ACK path now goes
  through the same `emitLearnAction(...)` helper as one-shot MIDI and screen
  actions, so source memory is consistent instead of only working for buttons.
  Verification: focused Learn UI tests passed 34, `npm --prefix tauri/ui run
  build` passed, and the full Learn perfection package refreshed with
  `passed=true`, `technical_passed=true`, `non_external_ready=true`, and
  `internal_blocker_ids=[]`.
- A two-hundred-seventh slice makes that character pass accessible and
  verifier-backed. `TutorSpeakDock.advance(...)` now writes the matched receipt
  into the tutor live region and adds an `aria-label` such as
  `matched eq turn · hardware · 01`, while the `frontstage_simplicity_contract`
  evidence explicitly names the action-receipt behavior and includes the tutor
  dock announcement test in the focused frontend gate. Verification: focused
  Learn UI tests passed 34, frontend-runner/verifier contract tests passed 28,
  touched Python verifier/runner files passed Ruff, `npm --prefix tauri/ui run
  build` passed, and the full Learn perfection package refreshed with
  `passed=true`, `technical_passed=true`, `non_external_ready=true`,
  `internal_blocker_ids=[]`, `release_ready=false`, matrix `20/22`, and
  objective audit `7/9`.
- A two-hundred-eighth slice tightens the completion moment without adding a
  new panel. `complete_lesson` now refreshes the recommendation first, then the
  booth pulse keeps the visible reward compact (`clean pass · 1 move`) while
  adding an accessible title/aria label that names the next action, for example
  `next practice: start meet your controller`. The verifier records this as
  `frontstage_simplicity_contract.evidence.completion_reward`. Verification:
  focused practice-booth Vitest passed 27, frontend build passed,
  verifier/Ruff checks passed, and the full Learn perfection package refreshed
  with `passed=true`, `technical_passed=true`, `non_external_ready=true`,
  `internal_blocker_ids=[]`, `release_ready=false`, matrix `20/22`, and
  objective audit `7/9`.
- A two-hundred-ninth slice makes recommended-path copy more truthful for
  learners who left a lesson started but unfinished. The frontstage now renders
  an in-progress recommendation as `retry <lesson title>` instead of
  `start <lesson title>`, while still emitting `level="fresh"` because the
  deterministic runtime restarts the lesson path. The verifier records this as
  `frontstage_simplicity_contract.evidence.in_progress_recommendation`.
  Verification: focused practice-booth Vitest passed 27, frontend build passed,
  verifier/Ruff checks passed, and the full Learn perfection package refreshed
  with `passed=true`, `technical_passed=true`, `non_external_ready=true`,
  `internal_blocker_ids=[]`, `release_ready=false`, matrix `20/22`, and
  objective audit `7/9`.
- A two-hundred-tenth slice hardens future course creation. The course-pack
  starter manifest generated by `validate_learn_course_pack.py --init-template`
  now includes an `authoring_contract` with the one-prompt/one-action booth
  rule, hardware/screen defaults, starter expected action, hint floor, prompt
  caps, copy-truthfulness rule, and post-merge verification commands. Manifest
  validation now requires that contract and reports it as
  `CoursePackValidation.authoring_contract`; the curriculum audit exposes the
  starter rule as `starter_template_contract`, and the package verifier requires
  both `future_course_extension_contract.evidence.starter_template_contract`
  and `draft_validator.result_fields[] == "authoring_contract"`, including
  explicit starter-template evidence for the expected cue action and post-merge
  commands.
  Verification: course-pack/curriculum/verifier tests passed 48, touched
  Python files passed Ruff, and the full Learn perfection package refreshed
  with `passed=true`, `technical_passed=true`, `non_external_ready=true`,
  `internal_blocker_ids=[]`, `release_ready=false`, matrix `20/22`, and
  objective audit `7/9`.
- A two-hundred-eleventh slice adds backstage learner data without frontstage
  complexity. `LearnProgress` lesson rows can now remember
  `practice_sources: {hardware, screen}` and `last_practice_source`; row
  rewrites for start, hint, and completion preserve that memory. The runtime
  writes it from real `ipc.learn.ack` sources for matched actions, multi-beat
  screen continues, observer-owned ACKs, and wrong-action adaptive hints. The
  generated frontend progress projection knows the optional fields, and the
  package verifier records the behavior as frontstage-simplicity evidence
  because the learner sees no new panel. Verification: Ruff passed for touched
  Python files; focused pytest passed 73; curriculum codegen check passed; and
  the focused curriculum-meta Vitest passed 6. The first full package refresh
  correctly failed because the shared `ipc.learn.progress_state` schema had not
  accepted the new lesson-row fields; after updating
  `messages.schema.json`, generated TS IPC types, and the generated validator,
  `uv run python scripts/check_ipc_schema.py`, `npm --prefix tauri/ui run
  check:ipc`, and the full Learn perfection package all passed.
- A two-hundred-twelfth slice gives that data a restrained user-facing payoff.
  Course 3's L3.06 graduation handoff now totals hardware/screen practice
  actions from `LearnProgress` and adds one compact phrase to the existing
  grounded status line only when data exists: `practice: mostly hardware deck`,
  `practice: mostly screen deck`, or `practice: hardware + screen`. It does not
  expose counts or add a new panel. Verification: `uv run pytest -q
  tests/learn/test_graduation.py tests/learn/test_verify_learn_package.py`
  passed 30 and Ruff passed for the touched files.
- A two-hundred-thirteenth slice turns persisted hint strikes into a quiet
  retry primer. The generated curriculum projection now carries
  `strikes_used` into `ProgressListEntry`, and the practice booth uses that
  data only when it changes the next action: an unfinished recommended lesson
  with prior hints shows `hint ready for retry`, while exact hint counts move
  into aria/title text and the primary button remains `retry <lesson>`. This
  adds observant personality without a score panel, dashboard, or syllabus
  wall. Verification: focused curriculum/projection and practice-booth tests
  passed, verifier tests passed, Ruff passed for touched Python files, and the
  Learn frontend build passed.
- A two-hundred-fourteenth slice hardens graceful lesson choice without making
  the chooser feel like the product. The `choose lesson` control now exposes
  `aria-controls="learn-progress-list-host"` and live `aria-expanded` state,
  the map closes on Escape or lesson pick, and focus returns to the opener when
  dismissed. The package verifier records this under the
  `frontstage_simplicity_contract` evidence, so the opt-in chooser quality is
  part of release proof rather than an incidental UI detail. Verification:
  focused practice-booth Vitest passed 27, verifier tests passed 24, and Ruff
  passed for the touched Python verifier files.
- A two-hundred-fifteenth slice hardens the on-screen deck fallback path. When
  a lesson expects a control that the active SVG does not represent, the single
  fallback `#learn-screen-action` button now receives aria/title copy such as
  `screen fallback: press deck A headphone cue`, while its visible label and
  deterministic `ipc.learn.ack` payload remain unchanged. The package verifier
  records this under the frontstage simplicity contract so SVG gaps cannot
  quietly become vague screen-deck actions. Verification: focused
  practice-booth Vitest passed 27, verifier tests passed 24, and Ruff passed
  for the touched Python verifier files.
- A two-hundred-sixteenth slice hardens HUD replay affordances without adding
  visual weight. Completed progress dots now announce `press to replay` and
  carry a matching title, current dots announce the current step, and pending
  dots announce the prerequisite lock. The verifier records this under the
  lesson choice/replay contract because jump/replay support should be
  understandable to keyboard and assistive-tech users, not only technically
  wired. Verification: focused HUD Vitest passed 4, verifier tests passed 24,
  and Ruff passed for the touched Python verifier files.
- A two-hundred-seventeenth slice carries source awareness into the completion
  payoff. The practice booth already knew whether a matched move came from
  MIDI hardware or the on-screen deck for the receipt row; now the tiny
  clean-pass reward can say `clean pass · hardware · 1 move`,
  `clean pass · screen · 1 move`, or
  `clean pass · hardware + screen · 2 moves` without adding another surface.
  It also distinguishes hinted completions as `recovered pass`, for example
  `recovered pass · screen · 1 move`, so the booth is encouraging without
  falsely calling a coached recovery clean. The
  verifier records this under the frontstage simplicity contract so "it noticed
  how I practiced" stays a product behavior, not a one-off flourish.
  Verification: focused practice-booth Vitest passed 31, verifier tests passed
  24, Ruff passed for the touched Python verifier files, `git diff --check`
  passed, and the full Learn perfection package refreshed with `passed=true`,
  `non_external_ready=true`, and only the two deferred external blockers.
- A two-hundred-eighteenth slice makes the opt-in lesson map as explicit as the
  HUD replay dots. Completed rows already replayed through
  `ipc.learn.start_lesson {level: "replay"}`; they now announce
  `press to replay` and carry a matching title. In-progress rows announce retry,
  and locked rows preserve the exact unlock reason in aria/title text. This
  improves graceful lesson choice without changing the visible practice booth.

## Release Call

Do not call the current dirty worktree a finished release yet, because the
external ear-pass and Course 3 routed-audio proof are still open. With those two
deferred, the current package is internally ready: the verifier reports no
internal blockers and `non_external_ready=true`.

Suggested status:

> v9.0 Learn rebuild: strong structured implementation slice, not yet a proven
> complete beginner-teaching product. The real DDJ-FLX4 controller path and
> launched Tauri path are now proven. Ship-blocked on packaged EQ ear-pass,
> Course 3 live-audio set pass, and live audio/content ear validation.
> Browser Learn rendering and Python WebSocket Learn runtime are joined in a
> Playwright harness, and the launched Tauri smoke now proves the real Learn
> WebviewWindow, production practice-booth clicks, Rust bridge, Python Learn
> runtime, and frontstage quality assertions plus an axe-core critical/serious
> WCAG gate together through `:8765`.
> EQ-as-tutor now has a
> packaged self-authored WAV bank, but those loops still need human ear-pass or a
> richer licensed replacement before the marquee lesson can be called polished.
> Course 3 forward count-ins and L3.02 prepared-pool awareness are now grounded
> in cue/playlist evidence and covered by a deterministic mini-set rehearsal,
> but still need a real controller/audio set pass before being called polished.

Minimum bar before calling it complete from here:

1. Ear-pass and accept the packaged internal EQ loops, or replace them with
   richer licensed examples for the marquee version.
2. Run a real Course 3 controller/audio set pass. The deterministic rehearsal
   now covers cue-anchored forward count-ins, prepared-pool awareness, and
   graceful deviation from the pool; the remaining proof is live hardware.
3. Run a live audio/content pass: the full sidecar startup/shutdown smoke is
   now green with configured hardware, but it still does not prove the coach
   heard and cited a real routed set.
4. Keep the real-hardware proof artifact with the handoff. The FLX4 is visible
   and profile-resolved, callback MIDI is proven, and live-discovered jog
   movement has now been mapped/proven through the deterministic Learn verifier;
   the remaining live proof is Course 3 routed audio, not basic controller I/O.
