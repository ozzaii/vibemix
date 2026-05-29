# Handoff: Learn Integration And Live-Proof Pass

**Date:** 2026-05-29
**Status:** integration-handoff ready, not complete
**Scope:** vibemix Learn beginner module after the latest structured-flow,
practice-booth, bridge, and frontend quality slices.

**Start here for the compact work-done summary:**
`.planning/handoffs/2026-05-29-learn-work-done-summary.md`

## Bottom line

Do not call the full Learn goal complete yet.

The dirty worktree now contains a much stronger Learn implementation than the
inherited v9 state: 36 canonical beginner lesson flows, deterministic action
verification, adaptive hints, progress and replay semantics, observer wiring,
packaged EQ exemplar fallback, Course 3 backstage lenses, browser/Tauri bridge
proof, and a restrained practice-booth frontstage.

The remaining proof is integration evidence, not another syllabus pass:

1. Course 3 routed-audio count-in proof with grounded Rekordbox/deck evidence.
2. Human ear-pass for the packaged EQ loops, or replacement with richer
   licensed examples.

## Product Direction

Keep Learn characterful by making it feel observant, not busy. The booth should
notice the exact hand move, name it in one compact receipt, correct it with one
grounded hint when needed, and then move on. Do not add XP systems, confetti,
extra dashboards, or syllabus-first navigation to create personality. The
personality is precision: `eq turn · hardware · 01`, `clean pass · 1 move`, a
specific citation chip, and a next action that makes the learner feel capable.

## Latest completed slice

The latest Learn slice added or hardened these areas:

- Lesson-map replay/retry affordance:
  The opt-in lesson map already emitted `level: "replay"` for completed rows
  and `level: "fresh"` for retryable rows. It now says that clearly in
  aria/title text: completed rows announce `press to replay`, in-progress rows
  announce retry, and locked rows carry the exact lock reason. This keeps
  graceful lesson choice understandable without changing the visual booth.
  Focused proof:
  `npm --prefix tauri/ui test -- tests/learn/test_progress_list.spec.ts`,
  `uv run pytest -q tests/learn/test_verify_learn_package.py`, and Ruff for
  the verifier/test files.

- Source-aware clean-pass payoff:
  The one-line completion reward now carries the matched input source when the
  booth knows it, for example `clean pass · hardware · 1 move` or
  `clean pass · screen · 1 move`. Mixed hardware/screen lessons resolve to
  `hardware + screen`. If the learner needed an adaptive hint first, the same
  one-line reward says `recovered pass`, for example
  `recovered pass · screen · 1 move`. This makes the practice booth feel
  observant at the exact payoff moment without adding a dashboard, score, or
  extra panel. Focused proof:
  `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
  passed 31, `uv run pytest -q tests/learn/test_verify_learn_package.py`
  passed 24, and Ruff passed for the verifier/test files. Full package refresh
  passed Python quality, frontend quality, desktop quality, and the package
  verifier with `non_external_ready=true`, `internal_blocker_ids=[]`, and only
  the deferred ear-pass / Course 3 routed-audio blockers.

- HUD replay affordance labels:
  Completed lesson HUD dots already replay lessons through the same
  `ipc.learn.start_lesson {level: "replay"}` path; they now announce
  `press to replay` and carry a matching title. Current dots announce the
  current step, and pending dots announce the prerequisite lock. This improves
  replay/jump support without adding visible UI. Focused proof:
  `npm --prefix tauri/ui test -- tests/learn/test_hud_progress_dots_keyboard.spec.ts`
  passed 4, `uv run pytest -q tests/learn/test_verify_learn_package.py`
  passed 24, and Ruff passed for the verifier/test files.

- Screen fallback action label:
  Some beginner lessons use controls that are not represented in every
  controller SVG. The one fallback screen-action button now names the exact
  fallback in aria/title text, for example `screen fallback: press deck A
  headphone cue`, while preserving the same deterministic `ipc.learn.ack`
  shape. This keeps the on-screen deck usable without adding another panel.
  Focused proof:
  `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
  passed 27, `uv run pytest -q tests/learn/test_verify_learn_package.py`
  passed 24, and Ruff passed for the verifier/test files.

- Chooser disclosure quality:
  The optional lesson chooser now behaves like a proper product disclosure,
  not a hidden side page. `choose lesson` carries `aria-controls` and
  `aria-expanded`, the map closes on Escape or lesson pick, and focus returns
  to the opener when the user dismisses it. This strengthens graceful lesson
  choice while preserving the recommended-path booth. Focused proof:
  `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
  passed 27, `uv run pytest -q tests/learn/test_verify_learn_package.py`
  passed 24, and Ruff passed for the verifier/test files.

- Adaptive retry primer:
  The practice booth now uses persisted hint-strike memory without adding a
  stat panel. When the recommended lesson is unfinished and the prior attempt
  used hints, the primary action still says `retry <lesson>`, while the booth
  pulse says `hint ready for retry` and moves the exact hint count into
  aria/title text. This makes the coach feel observant and useful without
  turning Learn into a dashboard. Focused proof:
  `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts
  tests/learn/test_practice_booth_shell.spec.ts` passed 34,
  `uv run pytest -q tests/learn/test_curriculum_projection.py
  tests/learn/test_verify_learn_package.py` passed 28, Ruff passed for the
  touched Python files, and `npm --prefix tauri/ui run build` passed.

- Graduation practice payoff:
  The stored hardware/screen practice-source data now appears where it has real
  learner value: the L3.06 graduation status line. `build_graduation_summary`
  totals hardware and screen actions from `LearnProgress`, and
  `build_graduation_tutor_line` adds one compact phrase only when data exists,
  for example `practice: mostly hardware deck` or `practice: hardware + screen`.
  This is the intended character register: the system remembers the learner's
  path, but does not expose counts or add another dashboard. Focused proof:
  `uv run pytest -q tests/learn/test_graduation.py
  tests/learn/test_verify_learn_package.py` passed 30 and Ruff passed for the
  touched files. Full package refresh then passed Python quality, frontend
  quality, desktop quality, and the package verifier with
  `non_external_ready=true`, `internal_blocker_ids=[]`, and only the deferred
  ear-pass / Course 3 routed-audio blockers.

- Backstage practice-source memory:
  Learn now persists whether user actions came from MIDI/controller hardware
  or the on-screen deck. `LearnProgress` rows can carry
  `practice_sources: {hardware, screen}` plus `last_practice_source`, and the
  runtime writes those fields from matching ACKs, multi-beat screen continues,
  observer-owned lesson ACKs, and wrong-action adaptive hints. This creates
  future debrief/profile/course intelligence without adding a page, panel, or
  metric to the learner's booth. Focused proof:
  `uv run pytest -q tests/learn/test_progress_persistence.py
  tests/learn/test_ipc_handlers_dispatch.py
  tests/learn/test_curriculum_projection.py tests/learn/test_verify_learn_package.py`
  passed 73, Ruff passed for touched Python files, codegen check passed, and
  `npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts`
  passed 6. The first full package refresh exposed the important missing seam:
  `ipc.learn.progress_state` rejected the new row fields until
  `messages.schema.json`, generated TS types, and the generated validator were
  updated. After that fix, `uv run python scripts/check_ipc_schema.py`,
  `npm --prefix tauri/ui run check:ipc`, and the full Learn perfection package
  all passed.

- Source-aware action receipts:
  the tutor dock's one-line receipt now keeps the booth feeling observed
  without adding UI. Matched moves still use the existing control-specific
  labels (`eq turn`, `cue hit`, `jog nudge`, etc.), but now append the surface
  when Learn knows it: `hardware` for MIDI/controller movement and `screen` for
  on-screen deck clicks. This also unified the MIDI delta ACK path through the
  same frontstage helper as one-shot MIDI and screen clicks. The same receipt
  now gets an accessible `aria-label`, is spoken through the tutor live region,
  and is recorded in `frontstage_simplicity_contract.evidence.action_receipts`
  so it is a verified product behavior rather than decorative copy. Focused
  proof:
  `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts
  tests/learn/test_tutor_speak_sr_announcement.spec.ts` passed 34,
  `uv run pytest -q tests/learn/test_run_learn_frontend_quality.py
  tests/learn/test_verify_learn_package.py` passed 28,
  `npm --prefix tauri/ui run build` passed, and the full Learn perfection
  package refreshed with `passed=true`, `non_external_ready=true`,
  `internal_blocker_ids=[]`.
- Completion payoff and next-practice label:
  after a lesson completes, Learn still shows one compact visible reward such
  as `clean pass · 1 move`, but the booth pulse now carries an accessible
  next-practice label/title derived from the refreshed recommendation, for
  example `next practice: start meet your controller`. This gives the learner a
  little payoff and an immediate next move without exposing the syllabus map.
  The behavior is covered by `tests/learn/test_practice_booth_shell.spec.ts`
  and named in
  `frontstage_simplicity_contract.evidence.completion_reward`. Full package
  refreshed with `passed=true`, `non_external_ready=true`,
  `internal_blocker_ids=[]`, and only the two deferred external blockers.
- In-progress recommendation copy:
  when progress says the recommended lesson has been started but not finished,
  the primary booth action says `retry <lesson title>` instead of
  `start <lesson title>`. Activation still emits `level="fresh"` because the
  Learn runtime restarts the deterministic lesson path rather than resuming a
  hidden midpoint. This is now named in
  `frontstage_simplicity_contract.evidence.in_progress_recommendation`.
- Non-external completion boundary:
  `scripts/verify_learn_package.py` and
  `scripts/run_learn_perfection_package.py` now report
  `non_external_ready`. This is the exact current user boundary: the package is
  internally complete when deterministic quality passes and the only blockers
  are the deferred human EQ ear-pass and Course 3 routed-audio proof. Current
  package artifact reports `passed=true`, `technical_passed=true`,
  `non_external_ready=true`, `internal_blocker_ids=[]`,
  `deferred_external_blocker_ids=["packaged_eq_exemplar_ear_pass",
  "course3_live_audio_play_mode"]`, and `release_ready=false`. If any other
  blocker appears, the same field flips false instead of hiding it.
- Future course-pack grounding parity:
  `src/vibemix/learn/course_pack.py` now validates future course drafts against
  the same grounded teaching-loop standard as the shipped 36 lessons.
  `CoursePackValidation` emits `teaching_grounding_contract` and
  `hint_grounding_contract`; the validator rejects uncited or ungrounded normal
  teaching turns and uncited or ungrounded first-three hint turns before merge.
  `curriculum_audit.course_pack_contract()` exposes those fields and the
  `teaching_loop_contract`, and the package verifier now requires them for the
  `future_course_extension_contract` row. The starter CLI now also writes an
  `authoring_contract` into generated manifests, covering the one-action booth
  rule, hardware/screen defaults, starter expected cue action, hint floor,
  prompt caps, copy-truthfulness rule, and post-merge verification commands.
  Manifest validation now requires that contract on submitted course packs and
  reports it as `CoursePackValidation.authoring_contract`; the package verifier
  records this as
  `future_course_extension_contract.evidence.starter_template_contract` and
  requires `draft_validator.result_fields` to include `authoring_contract`,
  plus starter-template evidence for the expected action and post-merge checks.
  Focused proof:
  `uv run pytest -q tests/learn/test_course_pack.py
  tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py`
  passed 48, Ruff passed for touched Python files, and the full Learn
  perfection package passed all four commands with only the two deferred
  external blockers.
- Grounded hint-turn contract:
  `src/vibemix/learn/teaching_loop.py` now exposes
  `teaching_turn_is_grounded(...)`, a pure check that a tutor turn carries the
  active lesson and step, Learn tutor route, observed control, declared input
  surfaces, EvidenceRegistry lens, authored text/TTS marker, and the same
  deterministic verifier the runtime will use. `curriculum_audit.py` now
  exercises every first-three beginner hint as a first-class teaching-loop
  turn and records `hint_grounding_contract`: current artifacts prove
  `hint_turn_count=228`, `grounded_hint_turn_count=228`, `ok=true`, and no
  failing lessons. `verify_learn_package.py` now requires that contract inside
  `teaching_loop_contract`, so the grounded adaptive loop cannot be marked
  proven if future lesson edits create ungrounded hints. Focused tests passed
  41, Python quality passed all rows, and the full package refresh passed all
  four commands with the same two external release blockers.
- Visible citation grounding for hints:
  empty authored teaching and hint citations now fall back to
  `step_grounding_citations(...)`, a deterministic `[screen:<control>]` atom
  for the highlighted control. The runtime uses those citations for normal
  tutor beats and timed hint strikes, and `test_runtime_evidence_grounding.py`
  proves a timed hint's `[screen:eq_hi:A]` citation is backed by the
  EvidenceRegistry write from the current highlight. The tutor dock reuses its
  existing citation chip for hint lines, so learners see the grounded target
  without a new panel. Current package verification reports
  `hint_turn_count=228`, `grounded_hint_turn_count=228`, and
  `cited_hint_turn_count=228` under
  `flow_contract_summary.hint_grounding_contract`. Verification: focused
  Python tests passed 49, the tutor-dock Vitest passed 6, and the full Learn
  perfection package passed all four commands with `release_ready=false` only
  for EQ ear-pass and Course 3 routed-audio proof.
- Teaching-turn grounding contract:
  the same deterministic grounding is now counted for normal authored teaching
  prompts, not only hint turns. `curriculum_audit.py` plans every compiled
  beginner step as a `plan_teaching_turn(...)`, requires
  `teaching_turn_is_grounded(...)`, and requires a deterministic citation.
  `verify_learn_package.py` refuses to mark `teaching_loop_contract` proven
  unless `teaching_grounding_contract` is green. Current package verification
  reports `teaching_turn_count=76`, `grounded_teaching_turn_count=76`,
  `cited_teaching_turn_count=76`, and zero failing lessons. Verification:
  focused teaching-loop/curriculum/verifier tests passed 42, the curriculum
  audit refreshed, and the full Learn perfection package passed all four
  commands with the same two external release blockers.
- Browser-visible grounded coaching proof:
  `browser-python-beginner-path.pw.ts` now proves the same wrong on-screen EQ
  move renders `SCREEN DECK A MID EQ` in the tutor dock citation chip, not only
  in the captured websocket payload. `verify_learn_package.py` promotes that
  as a `browser_practice_booth_quality_contract` claim:
  "wrong on-screen EQ move reaches the Python sidecar, renders a grounded
  citation chip, and recovers to lesson completion." Verification: Ruff passed
  for the verifier/test files, the focused browser/Python sidecar suite passed
  3, package verifier tests passed 23, and the full Learn perfection package
  passed all four commands with the same two external release blockers.
- EQ exemplar ear-pass approval artifact:
  `scripts/audition_learn_exemplars.py` now has a durable human approval path
  for the packaged EQ examples. `--play --say-prompts --out
  /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json` speaks
  the band labels on macOS, plays the exact current bank, and leaves durable
  playback metadata. `--approve-ear-pass --approved-by <name>` now refuses to
  write `learn-exemplar-ear-pass-current.json` unless that matching audition
  artifact exists, then records the exact current track hashes and bank
  fingerprint. Future audits only mark the exemplar bank `release_ready=true`
  when the approval artifact still matches the current WAV bank. Missing
  audition proof, stale hashes, or mismatched fingerprints keep
  `release_ready=false`, so an old approval cannot silently bless regenerated
  examples. `scripts/verify_learn_package.py` now auto-discovers
  `/tmp/vibemix-live-learn-proof/learn-exemplar-ear-pass-current.json` or
  accepts `--exemplar-approval`. Current package verification still reports
  `approval_path=null`, `release_ready=false`, and the ear-pass blocker because
  no real human approval artifact has been recorded.
- Consolidated Learn package verifier:
  `scripts/verify_learn_package.py` now gives the integration session one
  machine-readable truth surface for the whole Learn package. It runs the
  curriculum/course-pack audit, packaged EQ exemplar technical audit, launched
  Tauri smoke artifact check, and live-proof artifact validation for screen,
  physical, and Course 3 evidence. The key contract is explicit:
  `passed=true` means deterministic package integrity is green, while
  `release_ready=false` can still carry honest completion blockers. Current
  artifact
  `/tmp/vibemix-live-learn-proof/learn-package-verification-current.json`
  reports `passed=true`, `technical_passed=true`, `release_ready=false`, 36
  beginner lessons, frontend projection up to date, browser booth quality
  proven, launched Tauri smoke passed with 17 quality checks, screen proof
  passed, physical proof passed, Course 3 unavailable on the route-hint runner,
  and exactly two completion blockers: packaged EQ exemplar human ear-pass
  pending and Course 3 routed-audio count-in proof not strictly proven.
  Running the same verifier
  with `--require-release-ready` exits 4 until those blockers are cleared. The
  Course 3 verdict now surfaces its nested `course3_audio_diagnosis` directly,
  so the package artifact's `next_actions` can say the exact current fix. The
  current desk state is not yet routed for Course 3: macOS output is
  `MacBook Pro Speakers`, Rekordbox settings currently point at `DDJ-FLX4 @
  44100Hz`, BlackHole 16ch/2ch are visible at 48 kHz but silent, and the
  remaining operator action is to route real Rekordbox master audio into a
  48 kHz BlackHole/loopback path with channel and master faders up.
- Course 3 frontstage audio wait state:
  `tauri/ui/src/learn/components/status-bar.ts` now maps an active Course 3
  lens with `waiting_for_audio` to one action prompt: `press play on deck`.
  Previously that state could fall through to `listening for phrase`, which made
  a silent or misrouted set look more ready than it was; an intermediate slice
  then said only `waiting for audio`, which was honest but not a one-action
  booth prompt. The UI still stays calm: no diagnostic panel, no route dump,
  only the next move plus an aria label that says routed master audio is not
  audible yet. `tauri/ui/tests/learn/test_practice_booth_shell.spec.ts` pins
  the state and the cold reset behavior.
- Learn operator-action frontstage seam:
  `tauri/ui/src/learn/lesson/operator-action.ts` now normalizes structured
  backstage actions into a booth-sized prompt while preserving the fuller route
  and steps in aria/title text. The Course 3 flat-frame lens can carry
  `operator_action`, and the Learn status rail collapses the current route proof
  into `play Rekordbox through BlackHole` instead of showing raw blockers. A
  generic `learn.operator_action` local event gives the package verifier,
  exemplar ear-pass, or future courses the same one-action surface without
  adding a page or syllabus wall. Focused Learn Vitest coverage pins the
  projection helper, Course 3 status behavior, generic EQ ear-pass prompt, and
  direct WebSocket preservation.
- Course 3 failed-proof action preservation:
  `scripts/live_course3_lens_probe.py` now stores the last observed Course 3
  lens `operator_action`, `scripts/validate_learn_live_proof.py` surfaces it in
  strict proof failures, and `scripts/verify_learn_package.py` now promotes the
  same action into `sections.live_proofs.course3.probe_operator_action`,
  Course 3 completion-matrix evidence, and the release blocker recipe when no
  stronger route doctor is available. This is the quality-analysis seam for the
  integration pass: a failed live proof can still say one next thing such as
  `Open one channel.` instead of collapsing to a generic red gate. The current
  desk artifact has no live probe operator action because the Course 3 lens
  stayed cold; the route doctor is therefore still the correct handoff:
  route macOS/Rekordbox output to BlackHole/loopback, play a real Rekordbox
  library track, and stop unrelated WebKit media.
- Grounded action receipts:
  `tauri/ui/src/learn/learn-window.ts` now uses the active expected action to
  make the small tutor-dock receipt specific to the move the learner just made:
  `eq turn · 01`, `jog nudge · 01`, `fader lift · 01`, `cue hit · 01`, etc.
  This is the liveliness pass requested for the booth: it feels noticed and
  responsive, but it stays in the existing one-line receipt instead of adding
  scores, badges, or another page. If no expected-action context exists, the
  older deterministic fallback labels still apply.
- FLX4 USB versus Bluetooth readiness:
  `scripts/learn_live_readiness.py` now names the Bluetooth-MIDI-only state
  explicitly. If a controller-like MIDI port says Bluetooth/BLE/BT and there is
  no USB or controller-audio evidence, physical readiness tells the operator to
  connect the DDJ-FLX4 by USB for Learn hardware/audio proof, and Course 3 adds
  the matching routed-audio route-doctor step. This is not a release shortcut:
  Bluetooth MIDI can be useful as a control path, but the Learn hardware/audio
  proof still needs USB/controller-audio or a real Rekordbox/loopback route.
  Latest live probe after the DDJ was plugged in: sidecar and Rekordbox are
  visible, BlackHole and `rekordbox Aggregate Device` are visible, but MIDI
  ports are empty, USB has no FLX4/AlphaTheta row, controller audio is absent,
  macOS output is still `MacBook Pro Speakers`, and WebKit media is the current
  Now Playing source. Treat that as a cable/power/enumeration problem before
  attempting the physical proof again.
- Physical connection doctor:
  `scripts/learn_live_readiness.py --require physical` now emits a
  `physical_connection_doctor` packet with `next_step`, bounded
  `operator_steps`, readiness/proof commands, and `uses_spoken_prompt=true`.
  The package verifier preserves that packet from embedded proof readiness
  stages into `sections.live_proofs.physical`, the completion matrix, release
  blocker recipe, and `next_actions`. This gives the next run one calm action
  when hardware is absent: use USB instead of Bluetooth, use a data-capable
  cable or powered adapter, or wait for DDJ-FLX4 in macOS MIDI/audio devices.
  It does not make physical proof pass unless the actual mapped controller move
  is observed.
- Audible operator prompts are now a verifier contract, not only a handoff
  memory. Generated operator commands include `--say-physical-prompts` for the
  physical DDJ proof, `--say-course3-prompts` for Course 3 routed-audio proof,
  and `--say-prompts` plus a required `--audition` artifact for packaged EQ
  exemplar ear-pass. Focused verifier tests pin those flags so future release
  recipes cannot silently become terminal-only while the user is looking at the
  deck.
- Browser practice-booth quality row:
  `scripts/run_learn_frontend_quality.py` now runs
  `learn_browser_booth_playwright` against the focused browser specs
  `browser-axe.pw.ts`, `browser-responsive.pw.ts`,
  `browser-contrast.pw.ts`, and `browser-python-beginner-path.pw.ts` before
  the broad Learn Playwright gate. `scripts/verify_learn_package.py` emits
  `browser_practice_booth_quality_contract`, proving no critical/serious axe
  violations, no narrow-viewport shell overflow, computed contrast thresholds
  for tutor/cue highlights, and recommended L1.01 completion through both the
  Tauri-style forwarder and direct browser WebSocket fallback. The same browser
  contract now also proves a wrong on-screen EQ move reaches the Python sidecar,
  returns grounded adaptive coaching, and recovers through the correct on-screen
  sweep to lesson completion instead of silently doing nothing.
- Course 3 auto-master finder contract:
  `scripts/learn_live_readiness.py` now returns ranked auto-master candidate
  evidence: live-signal rows, saved Rekordbox route, macOS route, 48 kHz
  loopback fallbacks, source/reason tags, sample rates, and whether a route was
  actually sampled. `scripts/run_learn_python_quality.py` now runs
  `learn_auto_master_finder_pytest`, and `scripts/verify_learn_package.py`
  emits `course3_auto_master_finder_contract`, proving the finder can explain a
  chosen route and reject rate-mismatched fallbacks before app startup.
- Course 3 mix count-in anchor contract:
  `src/vibemix/state/refresh.py` now allows Course 3 phrase anchors during a
  two-deck `mix` only when the Now Playing title exactly and unambiguously
  matches one citable deck row. Duplicate/ambiguous deck titles still abstain,
  leaving `next_phrase_cue_id=null`. `scripts/run_learn_python_quality.py` runs
  this as `learn_course3_mix_anchor_pytest`, and the package verifier emits
  `course3_mix_count_in_anchor_contract`.
- Mid-lesson controller-unplug recovery:
  `tauri/ui/src/learn/learn-window.ts` now remembers the active lesson
  highlight and replays it after the practice deck is remounted. This covers
  both initial async SVG load races and the real unplug path: if the DDJ drops
  during a lesson, the booth falls back to the on-screen deck, restores the
  current highlighted control, and still emits the same `ipc.learn.ack` when
  the learner performs the action on screen. `test_practice_booth_shell.spec.ts`
  pins that the lesson map stays hidden and the active action survives the
  unplug instead of becoming a dead end.
- Browser-to-Python adaptive coaching proof:
  `browser-python-beginner-path.pw.ts` now starts `L1.03` against the real
  Python Learn harness, clicks the wrong on-screen EQ, and waits for the
  grounded adaptive hint with `[screen:eq_mid:A]` and `[screen:eq_hi:A]`
  citations plus `teaching_loop.turn_kind=adapt`, then clicks the correct
  high-EQ control and proves `L1.03` completes in persisted progress. The same
  slice fixed the
  SVG hit-region weakness that the proof exposed: `learn-window.ts` now
  resolves controls from pointer coordinates when a click lands inside a
  control's SVG bounding box but not on a painted child, and `learn.css` opts
  controls into SVG bounding-box hit testing. This makes the on-screen deck
  usable as a real practice surface, not just a schematic.
- Course 3 route-action precision:
  `scripts/learn_live_readiness.py` now builds the structured Course 3
  `operator_action` from the current Rekordbox audio settings even when the
  richer route-hint lens cannot form, and falls back to the auto-master
  recommendation when Rekordbox does not name a route. The current desk rerun
  proves the sharper behavior: auto-master selects `BlackHole 16ch @ 48000Hz`,
  Rekordbox's current saved output is `Aggregate Device @ 48000Hz`, no
  DDJ/FLX controller is visible to MIDI/USB/audio, passive loopback is silent,
  and the app-start Course 3 proof still fails honestly while telling the
  operator to play a real Rekordbox track through `Aggregate Device @ 48000Hz`.
  The sidecar cleaned up with no listeners left on `8765`/`8766`.
- Course 3 Rekordbox route hint:
  `scripts/learn_live_readiness.py` now attaches a structured
  `rekordbox_route_hint` when the selected loopback route is healthy, passive
  BlackHole capture is silent, and the capture matrix sees DJ/Rekordbox device
  rows. This keeps the stable diagnosis code
  `loopback_route_healthy_external_playback_absent`, but the next action now
  names the common Rekordbox trap: macOS output on BlackHole does not prove
  Rekordbox master audio is routed to BlackHole because Rekordbox can use its
  own audio device. Current artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-route-hint-current.json`
  reports BlackHole 16ch self-test passing, direct BlackHole capture silent,
  DDJ-FLX4 and `rekordbox Aggregate Device` sampled below the signal floor, and
  the route hint telling the operator to set Rekordbox Audio preferences to
  BlackHole 16ch or an aggregate that includes BlackHole, then play a deck with
  channel and master faders up. The app-runner artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-route-hint-runner-current.json`
  proves the same hint survives real app startup: sidecar socket ready,
  physical Learn readiness true, auto-master selected `BlackHole 16ch @ 48000Hz`,
  Course 3 skipped honestly because live master audio, deck attribution, citable
  deck track, and capture signal were absent.
- Course 3 auto-master proof lens tightening:
  the Course 3 loopback/capture wait stages now call readiness with the Course 3
  route lens, so they sample Rekordbox's saved loopback route instead of the
  macOS default output route. `learn_live_readiness.py` also treats an injected
  self-test failure on the exact route Rekordbox currently owns as inconclusive,
  not proof that BlackHole is broken. Current artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-rekordbox-nudge-current.json`
  records the app selecting `BlackHole 2ch @ 48000Hz` via preferred fallback,
  a passed Rekordbox spacebar nudge, a passing BlackHole self-test, and no real
  external playback on any sampled DJ/loopback input. The package verifier now
  reports the diagnosis `loopback_route_healthy_external_playback_absent`: the
  route is aligned, but no deck audio crossed the capture floor.
- Course 3 auto-master recommendation seam:
  `scripts/learn_live_readiness.py` now emits `auto_master_recommendation`, a
  bounded machine-readable answer for the app/proof layer: live 48 kHz capture,
  Rekordbox saved loopback, macOS output loopback, silent 48 kHz loopback
  fallback, sample-rate fix, or no usable capture input. `run_learn_live_proof.py`
  consumes that recommendation when `--auto-master-input` starts the app and
  records the recommendation source/reason in the audio plan. This keeps the
  future Learn booth integration simple: it can show one frontstage action while
  the backstage knows exactly why the master route was chosen or rejected.
  Current artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-auto-master-plan-current.json`
  records `saved_loopback_route` from `rekordbox_audio_settings`, app startup
  selecting `BlackHole 2ch @ 48000Hz` as preferred fallback, and Course 3 still
  skipped because deck attribution/citable track/count-in were not proven.
- Desktop sidecar auto-master launch wiring:
  `tauri/src-tauri/src/sidecar.rs` now forwards the app audio env overrides and
  defaults `VIBEMIX_AUTO_MASTER_INPUT=1` whenever no explicit
  `VIBEMIX_INPUT_DEVICE` or `VIBEMIX_AUTO_MASTER_INPUT` is already present.
  That means the normal desktop Learn app starts with the master finder on
  BlackHole-capable rigs, while explicit input choices and
  `VIBEMIX_AUTO_MASTER_INPUT=0` remain respected for debugging or manual
  routing.
- Package verifier Course 3 evidence selection:
  `scripts/verify_learn_package.py` now extracts
  `auto_master_recommendation` and scores Course 3 attempts so a strict pass
  still wins, but among unavailable attempts the report prefers the most
  actionable route evidence. The current regenerated package verification now
  points Course 3 at
  `/tmp/vibemix-live-learn-proof/proof-course3-auto-master-plan-current.json`
  and carries `saved_loopback_route` / `rekordbox_audio_settings` directly,
  instead of summarizing the older nudge artifact first. The refreshed artifact
  also records a successful Rekordbox spacebar nudge, but Course 3 remains
  blocked on actual routed deck attribution/citable-track evidence.
- Course 3 audio-active honesty:
  `scripts/learn_live_readiness.py` now rejects a stale/loose
  `course3_lens.audio_active=true` when the same flat socket frame reports
  `music=0` and `phase=silent`. `src/vibemix/runtime/ws_bus.py` also requires
  `MusicState.audible` plus RMS above `SILENT_RMS` before serializing
  `course3_lens.audio_active=true`. The current proof now has summary and lens
  agreeing on `audio_active=false`; the UI/proof layer should keep showing
  "waiting for audio" until real routed deck signal arrives.
- Course 3 silent-audio frontstage copy:
  `tauri/ui/src/learn/learn-window.ts` now tells the status rail when a
  Course 3 lesson is loaded, separate from `course3_lens.session_active`.
  `tauri/ui/src/learn/components/status-bar.ts` uses that lesson context so a
  silent Course 3 proof still shows `press play on deck` when the lens reports
  `waiting_for_audio`. Lesson completion clears the Course 3-active flag and
  returns the rail to the default window-switch hint. The refreshed package
  verifier at
  `/tmp/vibemix-live-learn-proof/learn-package-verification-current.json`
  still reports `passed=true`, `release_ready=false`, with only the packaged EQ
  exemplar ear-pass and strict Course 3 routed-audio count-in proof outstanding.
- Broad frontend/runtime quality pass:
  the wider gates are now green after two test-harness cleanups. The full
  `tests/learn` pytest run exposed one stale em-dash copy expectation in
  `tests/learn/test_ipc_handlers_dispatch.py`; it now matches the shipped colon
  copy enforced by the tutor-copy cleanup. The full UI Vitest run exposed stale
  jsdom IPC assumptions in settings/session tests; those specs now set
  `window.__TAURI_INTERNALS__` when they assert Tauri-webview forwarding, so the
  shared `invokeTauri` runtime guard remains strict in production. Current proof:
  `uv run pytest -q tests/learn` passed 582 with 1 opt-in live-jog skip,
  `npm --prefix tauri/ui test` passed 134 files / 1222 tests with 1 todo,
  `npm --prefix tauri/ui run build` passed, and
  `npm --prefix tauri/ui run test:e2e:learn` passed all 10 browser checks.
- Current Course 3 app-start proof:
  `/tmp/vibemix-live-learn-proof/proof-course3-auto-master-current.json` is now
  the preferred Course 3 package-verifier source. It proves app startup,
  auto-master selection of `BlackHole 2ch @ 48000Hz` from Rekordbox's saved
  route, a passed Rekordbox Space nudge, direct loopback/capture-matrix
  sampling, a passing loopback self-test, clean app shutdown, and no leftover
  listeners on `8765`/`8766`. It still fails the strict Course 3 proof honestly:
  direct external loopback capture is silent, every sampled DJ/loopback capture
  row is below floor, live master audio is not audible, no deck is attributed,
  and no citable deck track is present.
- Course 3 readiness artifact honesty:
  `scripts/learn_live_readiness.py` now refuses `course3_audio=true` when
  explicit Course 3 loopback/capture/self-test diagnostics are enabled and fail.
  This fixes a confusing proof-shape seam where wait-stage status could fail
  but the nested readiness summary still looked green. The regenerated current
  artifact now keeps `last.passed=false`, `course3_audio=false`, and the direct
  signal blockers together. `scripts/verify_learn_package.py` now discovers
  `proof-course3-auto-master-current.json`, so the combined verifier reports the
  freshest app-start evidence instead of the older plan artifact.
- Launched Tauri Learn proof artifact:
  `scripts/e2e/learn_launched_tauri_smoke.mjs` now writes
  `/tmp/vibemix-live-learn-proof/learn-tauri-smoke-current.json` by default,
  still accepts `--out` for custom proof paths, and writes a durable JSON proof
  for the real app path. The Rust e2e autorun now checks that after L1.01
  completes, the booth recommends `start meet your controller` and the practice
  map remains opt-in. Current artifact
  `/tmp/vibemix-live-learn-proof/learn-tauri-smoke-current.json` reports
  `passed=true`, `l101_completed=true`, `quality_check_count=17`, no failures,
  and both post-completion booth checks passing through the launched Learn
  WebviewWindow, Rust bridge, and Python sidecar on `127.0.0.1:8765`.
- Practice-booth continuation and copy polish:
  the Learn frontstage now updates its recommended next lesson immediately on
  `ipc.learn.complete_lesson`, before the follow-up progress snapshot arrives,
  so the booth does not offer the just-finished lesson during the save gap.
  The first-controller screen-reader greeting and progress-list aria labels now
  use plain sentence/comma punctuation instead of em-dash copy, and the Learn
  transcript/tutor-copy gate now rejects em/en dash sentence glue in live
  transcript JSON. The browser Learn e2e suite still passes across axe,
  contrast, responsive, controller motion, and the Python sidecar beginner path.
- Course-pack integration audit:
  `src/vibemix/learn/curriculum_audit.py` and
  `scripts/audit_learn_curriculum.py` now provide a reusable JSON audit for
  adding future Learn courses. It checks course registry/frame parity,
  LessonMeta-to-transcript drift, required transcript fields, beginner lesson
  flow compilation, and generated frontend projection freshness. Current
  artifact `/tmp/vibemix-live-learn-proof/learn-curriculum-audit-current.json`
  reports `passed=true`, 36 beginner lessons, all beginner flows compiling, and
  the checked-in frontend projection up to date.
- Future course IDs are now canonical at preflight time. Course-pack drafts must
  use `course_<number>_<slug>` plus lesson IDs like `L4.01`, with the lesson
  number matching the course number and ordinals contiguous from `.01`. This
  is enforced by `vibemix.learn.course_pack.validate_course_pack_draft(...)`,
  exposed in `sections.curriculum.course_pack_contract.canonical_id_contract`,
  and proven by the `future_course_extension_contract` row.
- Future course authors also get a validating starter pack instead of a blank
  manifest. `uv run python scripts/validate_learn_course_pack.py
  --init-template <dir> --course-number 4 --slug <slug>` writes
  `course-pack.json` plus transcript fixtures, refuses overwrites unless
  `--force` is supplied, and immediately validates the generated pack through
  the same course-pack preflight. Validation reports now include
  `flow_preview`: for each compiled draft lesson, the concrete step IDs,
  one-action prompt, observable controls, input surfaces, verifier kind, and
  adaptive hint count. That lets an author inspect the backstage practice flow
  before merging anything into the real curriculum. Draft validation also now
  shares the shipped curriculum's copy-truthfulness guard, so future course
  transcripts cannot claim unwired behavior such as the debrief opening
  automatically.
- Course capability contract for future courses:
  `src/vibemix/learn/curriculum.py` now makes each course declare a
  `frontstage_mode` and the coded seams it is allowed to use. The generated
  `tauri/ui/src/learn/lesson/curriculum-meta.ts` mirrors those fields without
  rendering them as visible curriculum weight. `curriculum_audit.py` now checks
  compiled lesson-flow lenses and input surfaces against each course's declared
  capabilities, so new courses cannot silently depend on live audio, prepared
  pools, exemplar audio, recital observers, debrief/profile state, or
  controller/on-screen input support. Observer lessons now expose
  `library_exemplars` and `recital_observer` as backstage lenses. The package
  verifier surfaces this at
  `sections.curriculum.course_pack_contract.capability_contract`.
- Course unlock-gate contract for future courses:
  `src/vibemix/learn/curriculum_audit.py` now also proves that every
  `CourseMeta.unlock_gate` is backed by a persisted boolean in
  `LearnProgress.to_dict()`. This closes a future-course trap where a new
  locked course could declare `course_4_unlocked` in Python, render in the
  chooser, and then remain permanently locked because no progress schema field
  could ever flip it. `src/vibemix/learn/curriculum_projection.py` now generates
  `LearnProgressProjection` unlock fields from declared gates instead of
  hardcoding Course 2/3. Current audit evidence shows supported and used gates
  are exactly `course_2_unlocked` and `course_3_unlocked`, with no unsupported
  gates or missing lock reasons.
- Packaged EQ exemplar proof artifact:
  `scripts/audition_learn_exemplars.py` now writes a durable JSON artifact with
  `--out`, schema versioning, per-track `integrity_passed`/`clip_free`/
  `non_silent` checks, bank-level `technical_failures`, and a separate
  `release_ready` flag. Current artifact
  `/tmp/vibemix-live-learn-proof/learn-exemplar-audit-current.json` reports
  `technical_passed=true` and diagnosis
  `technical_audit_passed_ear_pass_pending`, while keeping
  `release_ready=false` until a human actually ear-passes the loops.
- Packaged EQ ear-pass operator path:
  `scripts/audition_learn_exemplars.py --list-devices` now appends the
  available sounddevice output devices to the JSON summary so the listener can
  choose a real output index before `--play`. The same summary and the combined
  package verifier expose `operator_commands`: list devices, play with
  `--device-index <output-device-index> --say-prompts --out
  /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json`, approve
  with `--approve-ear-pass --approved-by <name>`, then refresh the verifier.
  The list-devices summary now also emits `operator_action`, which avoids
  BlackHole/capture sinks for human listening and recommends audible outputs.
  During `--play --say-prompts`, macOS speaks a short band label before each
  loop so the listener can keep attention on the sound rather than the
  terminal. This reduces release friction without lowering the human-listening
  gate.
  The current package verifier enriches that action with this Mac's available
  outputs and puts the same guidance into `release_blocker_recipe`. The latest
  artifact recommends `MacBook Pro Speakers` at device index `3` for the
  immediate ear-pass, with `HEADPHONEMG` at index `5` as the next audible
  fallback; BlackHole/capture sinks are avoided for human listening.
- Capture-signal wait gate:
  `scripts/run_learn_live_proof.py` now supports
  `--wait-capture-signal-seconds`, a pre-Course-3 wait stage that polls the
  whole capture matrix until any sampled DJ/loopback input crosses the signal
  floor. This catches the "playback is present, but not on selected BlackHole"
  case during the proof window. Current artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-capture-wait-current.json`
  shows both `capture_signal_wait` and `loopback_signal_wait` failing: the
  matrix sampled `rekordbox Aggregate Device`, `DDJ-FLX4`, `BlackHole 16ch`,
  and `BlackHole 2ch`, and no row crossed the signal floor. Diagnosis remains
  `loopback_route_healthy_external_playback_absent`.
- Stable Course 3 audio diagnosis:
  `scripts/learn_live_readiness.py` now emits a `course3_audio_diagnosis`
  object with stable codes, severity, message, and next action. It is derived
  from the route, self-test, passive loopback, capture-matrix, and live-context
  checks without changing pass/fail semantics. Current artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-diagnosis-current.json` reports
  `loopback_route_healthy_external_playback_absent`: `BlackHole 16ch` captures
  an injected self-test tone, but no sampled DJ/loopback input is receiving
  external playback. Next action is to start real Rekordbox deck playback and
  route its master output to `BlackHole 16ch` or the intended capture input.
- Loopback route self-test:
  `scripts/learn_live_readiness.py` now supports
  `--loopback-self-test-seconds`, which emits a quiet known tone through the
  selected duplex loopback device and captures it back. This proves the
  loopback route itself independently of Rekordbox/deck playback. Current
  artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-loopback-self-test-current.json`
  shows `BlackHole 16ch` self-test passing (`rms≈0.0249`, `peak≈0.0505`) while
  passive loopback capture is still silent and the capture matrix has no
  signal row. The remaining live blocker is therefore external playback not
  reaching any sampled capture path, not a broken BlackHole duplex route.
- Capture-matrix Course 3 diagnostics:
  `scripts/learn_live_readiness.py` now supports `--capture-matrix-seconds`,
  sampling and ranking relevant DJ/controller/loopback inputs (`DDJ-FLX4`,
  `rekordbox Aggregate Device`, `BlackHole 16ch`, `BlackHole 2ch`) by RMS/peak.
  `scripts/run_learn_live_proof.py` forwards the option into readiness and wait
  stages. Current artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-capture-matrix-current.json`
  shows all sampled DJ/loopback inputs are below the `0.003` RMS signal floor:
  FLX4 and rekordbox Aggregate only show tiny floor noise around `0.000175`,
  while both BlackHole devices are `0.0`. That rules out "wrong selected input"
  for the current run; no sampled capture path currently has real playback.
- Loopback-signal wait gate:
  `scripts/run_learn_live_proof.py` now supports
  `--wait-loopback-signal-seconds`, a dedicated pre-Course-3 stage that polls
  direct loopback RMS/peak before attempting the live lens proof. This lets an
  operator start playback during the proof window and lets the artifact show
  whether the run failed before or after real routed signal appeared. Current
  artifact `/tmp/vibemix-live-learn-proof/proof-course3-loopback-wait-current.json`
  waited on `BlackHole 16ch`, sampled twice, and failed cleanly with `rms=0.0`
  / `peak=0.0`; app startup, WebSocket readiness, and auto-master selection
  still passed.
- Direct loopback signal readiness:
  `scripts/learn_live_readiness.py` now accepts `--loopback-signal-seconds`
  and can sample the selected loopback input directly, recording device index,
  sample rate, channels, RMS, peak, and the RMS floor. `scripts/run_learn_live_proof.py`
  forwards the same option so durable artifacts can prove whether BlackHole is
  actually receiving signal, independent of the sidecar's deck attribution.
  Current artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-loopback-signal-current.json`
  shows the route and app selection are both `BlackHole 16ch`, but direct
  loopback capture is silent (`rms=0.0`, `peak=0.0`), so Course 3 still cannot
  honestly claim live master audio.
- Route-aware Course 3 readiness:
  `scripts/learn_live_readiness.py` now includes an `audio_route` diagnostic
  from `SwitchAudioSource`, reporting the current macOS output/system devices
  and whether they point at a loopback capture path. If live Course 3 context is
  silent and the default output is not routed to loopback, that route mismatch
  is surfaced as an actionable Course 3 blocker. On this rig I switched both
  output and system audio to `BlackHole 16ch`; the new artifact
  `/tmp/vibemix-live-learn-proof/proof-course3-route-aware-current.json`
  records `audio_route.ok=true` with output/system `BlackHole 16ch`, and the
  app still selected `BlackHole 16ch @ 48000Hz`. Course 3 still failed
  honestly because no live master audio reached the sidecar, deck attribution
  stayed absent, and no citable `deck_state.track_id` appeared.
- Structured auto-master proof diagnostics:
  `scripts/run_learn_live_proof.py` now parses the app's audio startup line and
  stores the selected auto-master input in both `app_start.result.audio_runtime`
  and `app_stop.result.audio_runtime`. A short real run wrote
  `/tmp/vibemix-live-learn-proof/proof-course3-auto-master-structured.json`:
  app start/stop passed, the sidecar WebSocket came up, auto master selected
  `BlackHole 16ch @ 48000Hz`, and the reason was `48k_fallback` with
  `live_signal=false`. Course 3 still failed correctly because live master
  audio was silent, deck attribution stayed `none`, and `deck_state` had no
  citable `track_id`. A direct `sounddevice.playrec` pulse through device index
  1 (`BlackHole 16ch`) passed with RMS about `0.029`, so the loopback device
  itself captures; the missing piece is routing real Rekordbox master playback
  into that path.
- Socket-visible teaching-loop metadata:
  `ipc.learn.tutor_speak` can now optionally carry `teaching_loop` metadata
  with the five backstage stages, turn kind, model-router path, observation
  fields, and deterministic verification contract. Runtime step beats, timed
  hints, and adaptive mismatch hints attach this metadata when they resolve to a
  structured lesson step. The Learn UI does not need to render it, so the
  frontstage remains calm, but proof/dev tooling can now inspect
  observe -> decide -> teach -> verify -> adapt without reverse-engineering
  tutor copy. Backward compatibility is preserved: older or non-step
  `tutor_speak` payloads omit `teaching_loop` instead of sending null.
- Physical DDJ-FLX4 proof:
  macOS currently sees `DDJ-FLX4` over MIDI and CoreAudio even when
  `SPUSBDataType` does not show a Pioneer/AlphaTheta row. The readiness gate now
  accepts MIDI + controller-audio visibility as physical-controller evidence.
  `/tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json` strictly
  validates as physical proof: L1.07 loaded on the real sidecar, the live
  `jog:A` pulse was observed, an ACK was sent, and the lesson advanced.
- Course 3 start/unlock proof helpers:
  `scripts/live_course3_lens_probe.py` can now send `ipc.learn.start_lesson`
  before watching the live lens. `scripts/run_learn_live_proof.py` has
  `--course3-lesson-id` and `--seed-course3-unlocked` so proof runs can start
  L3.01 from an isolated progress file without mutating the user's real Learn
  progress.
- Auto master-input finder:
  `AudioMacOS.find_device` now honors explicit BlackHole variants and supports
  `VIBEMIX_AUTO_MASTER_INPUT=1` / `--auto-master-input`. In auto mode it samples
  loopback/capture candidates briefly, excludes mics/controllers, picks the live
  master input when one is carrying signal, and otherwise prefers a usable
  48 kHz BlackHole variant over a silent or misconfigured exact `BlackHole 2ch`.
  `src/vibemix/agent/config.py` also accepts import-time
  `VIBEMIX_INPUT_DEVICE`, `VIBEMIX_OUTPUT_DEVICE`, and `VIBEMIX_MIC_DEVICE`
  overrides for proof/session boot.
- Learn mobile plating pass:
  the practice-booth shell no longer overflows at 390 px wide. The root and
  title/stage/status/footer bands are width-bounded, and
  `tauri/ui/tests/learn/browser-responsive.pw.ts` locks the mobile viewport
  regression in Chromium.
- Course 3 structured backstage lenses:
  `src/vibemix/learn/lesson_flow.py`,
  `src/vibemix/learn/teaching_loop.py`,
  `src/vibemix/learn/__init__.py`,
  `tests/learn/test_lesson_flow_contract.py`,
  `tests/learn/test_teaching_loop.py`.
- Highlight paint performance:
  `tauri/ui/src/learn/components/controller-stage.ts` now clears only the
  active highlighted SVG group and caches control-group lookups with stale-node
  guards.
- Browser/Tauri outbound fallback:
  `tauri/ui/src/tauri-runtime.ts` now fails fast when Tauri internals are not
  present, and
  `tauri/ui/tests/learn/browser-python-beginner-path.pw.ts` proves outbound
  Learn ACK frames before expecting the next tutor beat.
- Live L1.07 jog proof probe:
  `scripts/live_learn_jog_probe.py` now gives the integration session a focused
  "move the left jog wheel now" command. It captures the real FLX4 CC33 byte,
  then feeds that exact frame through `ControllerState`, `MidiMirror`, the Learn
  IPC ACK handler, and the L1.07 verifier. The pure contracts live in
  `tests/learn/test_live_learn_jog_probe.py`.
- Live L1.07 socket proof probe:
  `scripts/live_learn_socket_jog_probe.py` assumes the sidecar is already
  running, sends `ipc.learn.start_lesson` for L1.07 over `ws://127.0.0.1:8765`,
  waits for the live sidecar `ipc.learn.midi_position` jog pulse, sends the
  UI-shaped ACK, and waits for `ipc.learn.advance`. The contract test runs the
  same flow against a real `ws_broadcast` server.
- Packaged EQ exemplar audition:
  `scripts/audition_learn_exemplars.py` audits the four packaged band loops
  against the manifest and prints duration, channel, peak, RMS, clipping, and
  hash evidence. With `--play --device-index <n>`, it routes the loops through
  the same dedicated `ExemplarPlayer` seam used by Learn so a human can approve
  or replace the marquee EQ examples.
- Course 3 live-lens socket proof:
  `ws_broadcast` now adds an honest `course3_lens` object to the existing flat
  `ws://127.0.0.1:8765` frame. `scripts/live_course3_lens_probe.py` watches
  that same socket and can require active Course 3 plus citable next-phrase cue
  evidence before passing. The flat `deck_state` rows now also carry
  `track_id`, and failed Course 3 probes keep `last_context`, `max_music`,
  `audible_seen`, `deck_values`, `deck_state_seen`,
  `citable_deck_state_seen`, and human-readable diagnostic blockers so a cold
  lens can be traced to audio, deck attribution, library metadata, or cue
  evidence instead of collapsing into a generic failure.
- Course 3 live-lens frontstage bridge:
  `tauri/src-tauri/src/ws_client.rs` routes flat `course3_lens` frames to a
  Learn-specific Tauri event, `tauri/ui/src/learn/ws-client.ts` extracts the
  same field in direct browser fallback, and the Learn status rail shows one
  restrained action phrase: `press play on deck`, `open one channel`,
  `load a track`, `keep playing`, or `phrase cue locked`.
- Course 3 readiness/blocker contract:
  `course3_lens` now carries additive readiness booleans
  (`audio_active`, `deck_attributed`, `deck_track_citable`, `cue_ready`) plus
  stable blocker codes (`waiting_for_audio`, `waiting_for_deck`,
  `waiting_for_deck_track`, `waiting_for_cue`). The old four lens keys remain
  intact. This lets the proof tooling and UI say why Course 3 is waiting
  without scraping unrelated flat-frame fields or inventing a cue.
- Course 3 live-context readiness:
  `scripts/learn_live_readiness.py --require course3` and
  `scripts/run_learn_live_proof.py --course3` now optionally sample the live
  socket once the sidecar is up. Static device presence is no longer enough for
  a "Course 3 ready" runner decision: the context sample must see audible
  master audio, deck attribution to `A`, `B`, or `mix`, and a citable
  `deck_state.track_id` row. Count-in/cue proof is still stricter and remains
  owned by `live_course3_lens_probe.py`.
- WebSocket-safe sidecar readiness:
  `scripts/learn_live_readiness.py` now checks the sidecar with a real
  WebSocket handshake instead of a raw TCP connect. Successful socket checks
  report `protocol=websocket`, and app stderr no longer gets polluted by
  invalid-handshake noise during proof startup.
- Proof lifecycle validation:
  `scripts/validate_learn_live_proof.py` now grades `app_start` and `app_stop`
  whenever those stages appear, independent of requested proof requirements.
  This closes the false-green case where `--start-app --no-screen` could pass
  despite a failed app start or a missing stop record.
- Course registry and generated frontend projection:
  `src/vibemix/learn/curriculum.py` now has a `COURSE_REGISTRY` with labels,
  HUD labels, unlock gates, lock reasons, and the beginner-course flag.
  `src/vibemix/learn/curriculum_projection.py` plus
  `scripts/export_learn_curriculum_meta.py` generate
  `tauri/ui/src/learn/lesson/curriculum-meta.ts` from Python instead of
  hand-maintaining a second lesson table. The Learn HUD now reads generated
  course labels for beginner courses, while preserving Course 0/legacy alias
  fallbacks. New course integration should add one registry row plus lessons,
  then run `npm --prefix tauri/ui run codegen:learn`.
- Calm lesson-map accordion:
  `tauri/ui/src/learn/lesson/progress-list.ts` no longer opens the optional
  chooser as a 36-row syllabus wall. The current/recommended course expands by
  default, other courses collapse to course summaries, and the user can expand
  any course to jump or replay. Arrow-key movement is scoped to visible rows,
  locked lessons remain visible only after expansion, course summaries update
  when completion status changes, and the practice-booth first screen still
  offers exactly one recommended action plus `choose lesson`.
- Screen-action repeat press fix:
  the on-screen `lesson_continue` action now emits every click as a fresh
  button-down press instead of toggling to an up event on the second click. The
  browser plus Python sidecar path now completes the verbatim four-line L1.01
  dialog through both the Tauri-style forwarder and direct WebSocket fallback.
- L3.06 graduation grounding:
  `src/vibemix/learn/graduation.py` now reads the real Learn progress,
  profile consent/profile storage, and persisted debrief index. The L3.06
  transcript no longer claims the debrief window is open without evidence; the
  runtime emits one truthful status line and registry-backed `screen` citations
  when evidence is available.
- All-36 IPC/runtime traversal:
  `tests/learn/test_all_lessons_runtime_path.py` starts every beginner lesson
  through the real Learn IPC handler, sends canonical ACK actions, drives
  observer-owned EQ exemplar and recital cycles through their shipped
  controllers, reaches `LessonRuntime.completed`, and reloads the persisted
  progress row for each lesson.
- Live on-screen Learn proof:
  `scripts/live_learn_screen_probe.py` connects to the real
  `ws://127.0.0.1:8765` sidecar, starts `L1.01`, sends the same
  `lesson_continue` screen ACKs as the Learn UI, waits through the real 45 s
  dwell, and requires `complete_lesson` plus a completed progress snapshot.
  `VIBEMIX_LEARN_PROGRESS_PATH` now lets live probes isolate Learn progress
  without touching the user's normal `~/.cache/vibemix/learn-progress.json`.
- Live readiness preflight:
  `scripts/learn_live_readiness.py` checks the real sidecar socket, Rekordbox
  process, MIDI input ports, macOS USB profiler, and audio devices. It supports
  `--require screen`, `--require physical`, and `--require course3` so the
  integration operator can fail fast on the exact missing live condition before
  running the proof probes. The Course 3 requirement is intentionally strict:
  it needs sidecar socket, physical MIDI, USB-visible controller, Rekordbox,
  loopback audio, and a DJ app/controller audio surface.
- Live proof artifact runner:
  `scripts/run_learn_live_proof.py` runs the readiness checks and requested
  probes into one JSON artifact. With `--start-app`, it starts `python -m
  vibemix`, isolates Learn progress with `VIBEMIX_LEARN_PROGRESS_PATH`, waits
  for the real `8765` socket, runs the screen proof, shuts the app down, and
  records exact skipped/failed blockers for physical and Course 3 paths.
  `--wait-physical-seconds` and `--wait-course3-seconds` poll readiness so an
  operator can plug/replug the controller during the proof window. The runner's
  top-level `passed` flag is now backed by the strict artifact validator and
  the artifact carries the embedded validation verdict.
- Live proof artifact validator:
  `scripts/validate_learn_live_proof.py` grades proof artifacts requirement by
  requirement. It accepts the current combined artifact as "screen proven,
  physical/Course3 explicitly unavailable" only when `--allow-skipped physical`
  and `--allow-skipped course3` are supplied, and it fails if someone tries to
  use that same artifact as physical proof. The validation is intentionally
  strict: physical proof must show the L1.07 jog lesson loaded, `control_id` is
  `jog:A`, jog position was seen, an ACK was sent, and the lesson advanced;
  Course 3 proof must show live lens frames, active Course 3 state, count-in
  evidence, and a citable `last_lens.next_phrase_cue_id`. Skipped
  physical/Course 3 validation failures now include recorded readiness blockers,
  including nested live-context blockers from wait-loop artifacts, so a failed
  proof tells the next operator what to fix.
- Learn progress IPC schema:
  `ipc.learn.progress_state` now accepts current v2 `LearnProgress` snapshots,
  including the six-skill live ledger. This fixes the shared Python/Tauri
  schema drift that could reject legitimate progress snapshots on the socket.
  `npm run codegen:ipc` regenerated `messages.ts` and
  `validator.generated.mjs`.
- Inspection notes:
  `.planning/research/2026-05-28-v9-learn-module-inspection.md` records the
  Course 3 lens, highlight paint, and fallback hardening slices.

## Known-good verification from the latest slice

- `uv run ruff check scripts/audition_learn_exemplars.py scripts/verify_learn_package.py tests/learn/test_exemplar_audition.py tests/learn/test_verify_learn_package.py`
  - Passed after adding hash-bound ear-pass approval artifacts.
- `uv run pytest -q tests/learn/test_exemplar_audition.py tests/learn/test_verify_learn_package.py`
  - Passed: 14 tests after surfacing Course 3 diagnosis in the package verifier.
- `uv run pytest -q tests/learn/test_verify_learn_package.py tests/learn/test_curriculum_audit.py tests/learn/test_exemplar_audition.py tests/learn/test_validate_learn_live_proof.py`
  - Passed: 33 tests.
- `uv run python scripts/audition_learn_exemplars.py --help`
  - Passed and documents `--approval`, `--approve-ear-pass`, `--approved-by`,
    `--approval-out`, `--audition`, and `--say-prompts`.
- `uv run python scripts/verify_learn_package.py --out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json`
  - Passed again after the approval-path change. Current artifact still reports
    `release_ready=false`, `sections.exemplars.approval_path=null`, and the
    packaged EQ exemplar human ear-pass blocker. It now also promotes
    `sections.live_proofs.course3.diagnosis.code=loopback_route_healthy_external_playback_absent`
    and carries the Rekordbox Audio preferences fix in package-level
    `next_actions`.
- `uv run python scripts/verify_learn_package.py --require-release-ready`
  - Exited 4 as intended, with the ear-pass and Course 3 blockers still present.
- `uv run ruff check scripts/verify_learn_package.py scripts/audit_learn_curriculum.py scripts/audition_learn_exemplars.py scripts/validate_learn_live_proof.py tests/learn/test_verify_learn_package.py tests/learn/test_curriculum_audit.py tests/learn/test_exemplar_audition.py tests/learn/test_validate_learn_live_proof.py`
  - Passed.
- `uv run pytest -q tests/learn/test_verify_learn_package.py tests/learn/test_curriculum_audit.py tests/learn/test_exemplar_audition.py tests/learn/test_validate_learn_live_proof.py`
  - Passed: 28 tests.
- `uv run python scripts/verify_learn_package.py --out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json`
  - Passed with `passed=true`, `technical_passed=true`, `release_ready=false`.
    Screen and physical proofs are strict-passed; Course 3 remains unavailable
    with live audio/deck/capture blockers from
    `/tmp/vibemix-live-learn-proof/proof-course3-route-hint-runner-current.json`.
- `uv run python scripts/verify_learn_package.py --require-release-ready`
  - Exited 4 as intended, because exemplar ear-pass and Course 3 routed-audio
    count-in proof remain incomplete.
- `uv run ruff check scripts/audition_learn_exemplars.py tests/learn/test_exemplar_audition.py tests/learn/test_verify_learn_package.py`
  - Passed after making approval require a matching audition artifact.
- `uv run pytest -q tests/learn/test_exemplar_audition.py tests/learn/test_verify_learn_package.py`
  - Passed: 37 tests after pinning the audition-before-approval gate.
- `uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`
  - Passed with all four commands green: Python quality, frontend quality,
    desktop quality, and package verifier. Current matrix remains
    `20/22`, `passed=true`, `technical_passed=true`, `release_ready=false`;
    the two honest blockers are still packaged EQ human ear-pass and Course 3
    routed-audio count-in proof.
- `uv run ruff check scripts/verify_learn_package.py tests/learn/test_verify_learn_package.py`
  - Passed after pinning audible operator prompts in the generated verifier
    recipe.
- `uv run pytest -q tests/learn/test_verify_learn_package.py`
  - Passed: 18 tests.
- `uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`
  - Passed again with all four quality/package commands green. The refreshed
    verification artifact now shows the physical proof command with
    `--say-physical-prompts`, the Course 3 proof command with
    `--say-course3-prompts`, and the EQ recipe with `--say-prompts` plus the
    required `--audition` artifact. Matrix remains `20/22`,
    `release_ready=false`.
- `uv run ruff check src/vibemix/learn/course_pack.py src/vibemix/learn/curriculum_audit.py scripts/verify_learn_package.py tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py`
  - Passed after adding the canonical future-course ID contract.
- `uv run pytest -q tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py`
  - Passed: 34 tests.
- `uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`
  - Passed again. The refreshed verification artifact proves
    `future_course_extension_contract.evidence.canonical_id_contract` with no
    blockers. Matrix remains `20/22`, `release_ready=false`.
- `uv run ruff check src/vibemix/learn/course_pack.py src/vibemix/learn/curriculum_audit.py scripts/validate_learn_course_pack.py scripts/verify_learn_package.py tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py`
  - Passed after adding the canonical starter-template CLI.
- `uv run pytest -q tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py`
  - Passed: 37 tests.
- `uv run python scripts/validate_learn_course_pack.py --init-template /tmp/vibemix-live-learn-proof/course-pack-template-smoke --course-number 4 --slug scratch_lab --lesson-count 2 --force`
  - Passed and wrote a 2-lesson starter pack that validated with
    `lesson_count=2`, `step_count=2`, and no errors.
- `uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`
  - Passed again. The refreshed verifier proves
    `draft_validator.template_cli` and the canonical starter-template contract.
    Matrix remains `20/22`, `release_ready=false`.
- `uv run ruff check src/vibemix/learn/course_pack.py src/vibemix/learn/curriculum_audit.py scripts/verify_learn_package.py tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py`
  - Passed after adding course-pack `flow_preview` reports.
- `uv run pytest -q tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py`
  - Passed: 37 tests.
- `uv run python scripts/validate_learn_course_pack.py --init-template /tmp/vibemix-live-learn-proof/course-pack-template-preview-smoke --course-number 4 --slug flow_preview_lab --lesson-count 2 --force`
  - Passed and showed `flow_preview` rows for `L4.01` and `L4.02`, each with
    `cue:A`, `hardware`/`screen`, `button_press`, and three hints.
- `uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`
  - Passed again. The refreshed verifier proves `flow_preview` in
    `future_course_extension_contract.evidence.draft_validator.result_fields`.
    Matrix remains `20/22`, `release_ready=false`.
- `uv run ruff check src/vibemix/learn/copy_truth.py src/vibemix/learn/course_pack.py src/vibemix/learn/curriculum_audit.py scripts/verify_learn_package.py tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py`
  - Passed after sharing the copy-truthfulness guard with course-pack
    validation.
- `uv run pytest -q tests/learn/test_course_pack.py tests/learn/test_curriculum_audit.py tests/learn/test_verify_learn_package.py`
  - Passed: 38 tests.
- Draft bad-copy smoke:
  `uv run python scripts/validate_learn_course_pack.py <mutated-course-pack.json>`
  returned `ok=false` for `When you finish, the debrief opens automatically.`
  and reported `draft_transcript_debrief_auto_open_unwired` on `learner_copy`.
- `uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`
  - Passed again. The refreshed verifier proves `copy_truthfulness` in
    `future_course_extension_contract.evidence.draft_validator.result_fields`
    and includes the unsupported auto-open phrase list. Matrix remains
    `20/22`, `release_ready=false`.
- `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts`
  - Passed: 16 tests after adding the active Course 3 `waiting for audio`
    status.
- `npm --prefix tauri/ui test -- --run tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
  - Passed: 7 tests.
- `npm --prefix tauri/ui test -- --run tests/learn`
  - Passed: 150 Learn Vitest tests.
- `npm --prefix tauri/ui run build`
  - Passed.
- `npm --prefix tauri/ui run test:e2e:learn`
  - Passed: 10 browser Playwright tests, including axe, contrast, responsive,
    controller motion, and both Python sidecar beginner-path modes.
- `npm --prefix tauri/ui run test:e2e:learn:tauri -- --out /tmp/vibemix-live-learn-proof/learn-tauri-smoke-after-audio-wait.json`
  - Passed after the Course 3 audio-wait status change. The artifact reports
    `passed=true`, `l101_completed=true`, `quality_ok=true`,
    `quality_check_count=17`, and no failures.
- `uv run ruff check scripts/learn_live_readiness.py tests/learn/test_learn_live_readiness.py`
  - Passed after adding the Rekordbox route hint.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py`
  - Passed: 33 tests.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed: 67 tests.
- `uv run ruff check scripts/learn_live_readiness.py scripts/run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py`
  - Passed after adding `auto_master_recommendation`.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py`
  - Passed: 73 tests.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --nudge-rekordbox-playback --require-count-in --wait-capture-signal-seconds 3 --wait-loopback-signal-seconds 3 --wait-course3-seconds 6 --wait-interval 1 --course3-context-seconds 1 --loopback-self-test-seconds 0.5 --loopback-signal-seconds 0.5 --capture-matrix-seconds 0.5 --out /tmp/vibemix-live-learn-proof/proof-course3-auto-master-plan-current.json`
  - Exited 4 honestly, wrote an app-runner artifact with
    `auto_master_recommendation.reason=saved_loopback_route`, app audio env
    carrying source/reason/live-signal fields, runtime selection
    `BlackHole 2ch @ 48000Hz` as preferred fallback, Rekordbox spacebar nudge
    passed, Course 3 skipped, `course3_live_context.audio_active=false`,
    `last_lens.audio_active=false`, and no sidecar left listening on
    `8765`/`8766`.
- `uv run python scripts/verify_learn_package.py --out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json`
  - Passed with `release_ready=false`; the two blockers remain packaged EQ
    exemplar human ear-pass and strict Course 3 routed-audio count-in proof.
  - Latest regenerated report now prefers the Course 3 auto-master-plan
    artifact and exposes `auto_master_recommendation.reason=saved_loopback_route`
    plus `source=rekordbox_audio_settings` and `playback_nudge.ok=true` in the
    Course 3 summary.
- `uv run ruff check src/vibemix/runtime/ws_bus.py tests/runtime/test_ws_bus_course3_lens.py scripts/learn_live_readiness.py tests/learn/test_learn_live_readiness.py`
  - Passed after hardening Course 3 audio-active honesty.
- `uv run pytest -q tests/runtime/test_ws_bus_course3_lens.py tests/learn/test_learn_live_readiness.py`
  - Passed: 52 tests.
- `uv run pytest -q tests/learn/test_run_learn_live_proof.py tests/learn/test_verify_learn_package.py`
  - Passed: 39 tests.
- `uv run pytest -q tests/learn/test_validate_learn_live_proof.py`
  - Passed: 14 tests.
- `npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts`
  - Passed: 18 tests after keeping Course 3 waiting-audio copy active while
    the loaded lesson is silent.
- `npm --prefix tauri/ui test -- tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
  - Passed: 7 tests.
- `npm --prefix tauri/ui run build`
  - Passed after the Course 3 status-rail integration.
- `uv run ruff check scripts/verify_learn_package.py tests/learn/test_verify_learn_package.py`
  - Passed after adding Course 3 attempt scoring.
- `uv run pytest -q tests/learn/test_verify_learn_package.py`
  - Passed: 10 tests.
- `cargo check --manifest-path tauri/src-tauri/Cargo.toml`
  - Passed after wiring desktop sidecar auto-master defaults.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml sidecar_audio_env_defaults`
  - Passed: 2 tests.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml forwarded_env_keys_relay_runtime_auth_and_codex_setup`
  - Passed: 1 test.
- `uv run python scripts/learn_live_readiness.py --require course3 --live-context-seconds 0.5 --loopback-self-test-seconds 0.5 --loopback-signal-seconds 0.5 --capture-matrix-seconds 0.5 > /tmp/vibemix-live-learn-proof/proof-course3-route-hint-current.json`
  - Exited 4 honestly because no sidecar was listening, but wrote the current
    rig artifact with
    `course3_audio_diagnosis.rekordbox_route_hint.code=rekordbox_may_bypass_macos_output`,
    BlackHole self-test passing, and passive BlackHole capture silent.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-capture-signal-seconds 1 --wait-loopback-signal-seconds 1 --wait-course3-seconds 1 --course3-context-seconds 0.5 --loopback-self-test-seconds 0.5 --loopback-signal-seconds 0.5 --capture-matrix-seconds 0.5 --out /tmp/vibemix-live-learn-proof/proof-course3-route-hint-runner-current.json`
  - Exited 4 honestly, wrote an app-runner artifact with sidecar socket ready,
    physical Learn readiness true, auto-master on BlackHole 16ch, Course 3
    skipped, and the same Rekordbox route hint in
    `stages.course3_probe.result.course3_audio_diagnosis`.
- `uv run python scripts/validate_learn_live_proof.py /tmp/vibemix-live-learn-proof/proof-course3-route-hint-runner-current.json --require course3 --allow-skipped course3`
  - Passed validation with no errors or warnings.
- `node --check scripts/e2e/learn_launched_tauri_smoke.mjs`
  - Passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml learn_e2e -- --nocapture`
  - Passed: 2 tests.
- `npm --prefix tauri/ui run test:e2e:learn:tauri -- --help`
  - Passed and documents `--out`.
- `npm --prefix tauri/ui run test:e2e:learn:tauri -- --out /tmp/vibemix-live-learn-proof/learn-tauri-smoke-current.json`
  - Passed: launched Tauri Learn completed L1.01 through `:8765` and wrote a
    durable artifact with 17 quality checks, including next-lesson booth
    recommendation and opt-in map checks.
- `cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --check`
  - Passed.
- `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_first_launch_announce.spec.ts tests/learn/test_progress_list.spec.ts tests/learn/test_beginner_path_contract.spec.ts`
  - Passed: 45 tests.
- `uv run pytest -q tests/learn/test_no_tutor_slop_blocklist.py tests/learn/test_course_2_curriculum.py tests/learn/test_course_3_curriculum.py tests/learn/test_tutor_prompts_byte_equality.py tests/learn/test_prompts.py`
  - Passed: 129 tests.
- `uv run ruff check src/vibemix/learn/curriculum.py tests/learn/test_no_tutor_slop_blocklist.py`
  - Passed.
- `uv run pytest -q tests/learn/test_curriculum_audit.py tests/learn/test_lesson_flow_contract.py tests/learn/test_all_lessons_runtime_path.py`
  - Passed: 86 tests.
- `npm --prefix tauri/ui test -- --run tests/design-slop-gate.spec.ts tests/learn/test_min_dwell_aria.spec.ts tests/learn/test_keyboard_skip_reachable.spec.ts tests/learn/test_tutor_speak_sr_announcement.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
  - Passed: 14 tests.
- `npm --prefix tauri/ui run test:e2e:learn`
  - Passed: 10 Playwright tests, including browser axe, contrast, responsive,
    controller motion, and Python sidecar beginner-path coverage.
- `npm --prefix tauri/ui run build`
  - Passed.
- `uv run ruff check src/vibemix/learn/curriculum_audit.py src/vibemix/learn/__init__.py scripts/audit_learn_curriculum.py tests/learn/test_curriculum_audit.py tests/learn/test_curriculum_projection.py`
  - Passed.
- `uv run pytest -q tests/learn/test_curriculum_audit.py tests/learn/test_curriculum_projection.py tests/learn/test_lesson_flow_contract.py`
  - Passed: 53 tests.
- `uv run python scripts/audit_learn_curriculum.py --out /tmp/vibemix-live-learn-proof/learn-curriculum-audit-current.json`
  - Passed: report shows 36 beginner lessons, all beginner flows compiling, no
    errors, and `frontend_projection.up_to_date=true`.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-capture-signal-seconds 1 --wait-loopback-signal-seconds 1 --wait-course3-seconds 1 --course3-context-seconds 0.5 --loopback-self-test-seconds 0.5 --loopback-signal-seconds 0.5 --capture-matrix-seconds 0.5 --out /tmp/vibemix-live-learn-proof/proof-course3-capture-wait-current.json`
  - Failed honestly: `capture_signal_wait` found no signal on any sampled
    DJ/loopback input, `loopback_signal_wait` found no selected-loopback
    signal, BlackHole self-test stayed healthy, and diagnosis remained
    `loopback_route_healthy_external_playback_absent`.
- `uv run ruff check scripts/learn_live_readiness.py scripts/run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py tests/test_audio_macos.py`
  - Passed: 84 tests.
- `git diff --check`
  - Passed.
- `uv run python scripts/learn_live_readiness.py --require course3 --live-context-seconds 0.5 --loopback-self-test-seconds 0.5 --loopback-signal-seconds 0.5 --capture-matrix-seconds 0.5`
  - Failed because the sidecar socket was down, but the JSON records
    `course3_audio_diagnosis.code=loopback_route_healthy_external_playback_absent`
    and `severity=start_playback`.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-loopback-signal-seconds 1 --wait-course3-seconds 1 --course3-context-seconds 0.5 --loopback-self-test-seconds 0.5 --loopback-signal-seconds 0.5 --capture-matrix-seconds 0.5 --out /tmp/vibemix-live-learn-proof/proof-course3-diagnosis-current.json`
  - Failed honestly: artifact records the same diagnosis code in
    `readiness_before` and `course3_probe`, plus passing BlackHole self-test,
    passive capture silence, all sampled capture inputs below floor, and no
    live deck/citable-track evidence.
- `uv run ruff check scripts/learn_live_readiness.py scripts/run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py tests/test_audio_macos.py`
  - Passed: 82 tests.
- `git diff --check`
  - Passed.
- `uv run python scripts/learn_live_readiness.py --require course3 --live-context-seconds 0.5 --loopback-self-test-seconds 0.5 --loopback-signal-seconds 0.5 --capture-matrix-seconds 0.5`
  - Failed because the sidecar socket was down, but the JSON records
    `loopback_self_test.ok=true` for `BlackHole 16ch` with `rms≈0.0249` and
    `peak≈0.0505`, while passive `loopback_signal.ok=false` and the capture
    matrix stayed below the signal floor.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-loopback-signal-seconds 1 --wait-course3-seconds 1 --course3-context-seconds 0.5 --loopback-self-test-seconds 0.5 --loopback-signal-seconds 0.5 --capture-matrix-seconds 0.5 --out /tmp/vibemix-live-learn-proof/proof-course3-loopback-self-test-current.json`
  - Failed honestly: artifact records app/WebSocket start, auto-master
    `BlackHole 16ch @ 48000Hz`, a passing injected BlackHole self-test, passive
    loopback silence, all sampled DJ/loopback inputs below signal floor, and no
    Course 3 deck/citable-track evidence.
- `uv run ruff check scripts/learn_live_readiness.py scripts/run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py tests/test_audio_macos.py`
  - Passed: 81 tests.
- `git diff --check`
  - Passed.
- `uv run python scripts/learn_live_readiness.py --require course3 --live-context-seconds 0.5 --loopback-signal-seconds 0.5 --capture-matrix-seconds 0.5`
  - Failed because the sidecar socket was down, but the JSON records
    `checks.capture_matrix.rows`: `DDJ-FLX4` RMS about `0.000176`,
    `rekordbox Aggregate Device` RMS about `0.000176`, and both BlackHole
    inputs at `0.0`; no row crossed the `0.003` signal floor.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-loopback-signal-seconds 1 --wait-course3-seconds 1 --course3-context-seconds 0.5 --loopback-signal-seconds 0.5 --capture-matrix-seconds 0.5 --out /tmp/vibemix-live-learn-proof/proof-course3-capture-matrix-current.json`
  - Failed honestly: artifact records app/WebSocket start, auto-master
    `BlackHole 16ch @ 48000Hz`, direct loopback silence, and capture matrix
    rows all below signal floor. Validator now surfaces `all sampled
    DJ/loopback capture inputs are below signal floor` with the other Course 3
    readiness blockers.
- `uv run ruff check scripts/learn_live_readiness.py scripts/run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py tests/test_audio_macos.py`
  - Passed: 76 tests.
- `git diff --check`
  - Passed.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-loopback-signal-seconds 3 --wait-course3-seconds 2 --course3-context-seconds 0.5 --loopback-signal-seconds 0.5 --out /tmp/vibemix-live-learn-proof/proof-course3-loopback-wait-current.json`
  - Failed honestly: `loopback_signal_wait` attempted 2 samples and recorded
    direct `BlackHole 16ch` silence (`rms=0.0`, `peak=0.0`), then Course 3
    readiness surfaced `direct loopback capture is silent` alongside missing
    live audio, deck attribution, and citable track evidence.
- `uv run ruff check scripts/learn_live_readiness.py scripts/run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py tests/test_audio_macos.py`
  - Passed: 72 tests.
- `git diff --check`
  - Passed.
- `uv run python scripts/learn_live_readiness.py --require course3 --live-context-seconds 0.5 --loopback-signal-seconds 1.0`
  - Failed because the sidecar socket was down, but the JSON records
    `checks.audio_route.ok=true` for output/system `BlackHole 16ch` and
    `checks.loopback_signal.ok=false` with `rms=0.0`, `peak=0.0`, device
    `BlackHole 16ch`.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-course3-seconds 2 --course3-context-seconds 0.5 --loopback-signal-seconds 1.0 --out /tmp/vibemix-live-learn-proof/proof-course3-loopback-signal-current.json`
  - Failed honestly: artifact records route `BlackHole 16ch`, selected
    auto-master `BlackHole 16ch @ 48000Hz`, direct loopback silence
    (`rms=0.0`, `peak=0.0`), and Course 3 blockers including `direct loopback
    capture is silent`.
- `uv run ruff check scripts/learn_live_readiness.py scripts/run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py tests/test_audio_macos.py`
  - Passed: 70 tests.
- `git diff --check`
  - Passed.
- `SwitchAudioSource -s 'BlackHole 16ch' -t output` and
  `SwitchAudioSource -s 'BlackHole 16ch' -t system`
  - Passed; current output/system route is `BlackHole 16ch`.
- `uv run python scripts/learn_live_readiness.py --require course3 --live-context-seconds 0.5`
  - Failed only on the sidecar not listening; the JSON now records
    `checks.audio_route.ok=true` with output/system `BlackHole 16ch`.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-course3-seconds 2 --course3-context-seconds 0.5 --out /tmp/vibemix-live-learn-proof/proof-course3-route-aware-current.json`
  - Failed honestly: the artifact records `audio_route.ok=true`, selected
    auto-master `BlackHole 16ch @ 48000Hz`, and Course 3 blockers `live master
    audio is not audible yet`, `live audio is not attributed to deck A, B, or
    mix`, and `live deck_state has no citable track_id at confidence floor`.
- `uv run ruff check scripts/learn_live_readiness.py scripts/run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py tests/test_audio_macos.py`
  - Passed: 65 tests.
- `git diff --check`
  - Passed.
- `uv run ruff check scripts/run_learn_live_proof.py tests/learn/test_run_learn_live_proof.py`
  - Passed.
- `uv run pytest -q tests/learn/test_run_learn_live_proof.py`
  - Passed: 13 tests.
- `uv run pytest -q tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_validate_learn_live_proof.py tests/test_audio_macos.py`
  - Passed: 62 tests.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-course3-seconds 2 --course3-context-seconds 0.5 --out /tmp/vibemix-live-learn-proof/proof-course3-auto-master-structured.json`
  - Failed honestly: artifact records `BlackHole 16ch @ 48000Hz` auto-master fallback and Course 3 blockers `live master audio is not audible yet`, `live audio is not attributed to deck A, B, or mix`, and `live deck_state has no citable track_id at confidence floor`.
- Direct `sounddevice.playrec` pulse through `BlackHole 16ch` at 48 kHz
  - Passed: recorded channel-1/2 RMS about `0.029`, peak about `0.050`.
- `git diff --check`
  - Passed.
- `uv run ruff check src/vibemix/ui_bus/learn_messages.py src/vibemix/ui_bus/__init__.py src/vibemix/learn/runtime.py tests/learn/test_teaching_loop.py tests/ui_bus/test_messages_schema.py`
  - Passed.
- `uv run pytest -q tests/learn/test_teaching_loop.py tests/ui_bus/test_messages_schema.py`
  - Passed: 93 tests.
- `npm --prefix tauri/ui run check:ipc`
  - Passed.
- `uv run pytest -q tests/learn/test_lesson_runtime_smoke.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_all_lessons_runtime_path.py tests/ipc/test_learn_envelope_parity_p92.py tests/ui_bus/test_messages_schema.py`
  - Passed: 170 tests.
- `uv run python scripts/check_ipc_schema.py`
  - Passed: 78 dataclasses validate, 78 wrapper dataclasses match 78 oneOf entries.
- `npm --prefix tauri/ui run build`
  - Passed.
- `git diff --check`
  - Passed.
- `uv run ruff check src/vibemix/learn/lesson_flow.py src/vibemix/learn/teaching_loop.py src/vibemix/learn/__init__.py tests/learn/test_lesson_flow_contract.py tests/learn/test_teaching_loop.py`
  - Passed.
- `uv run pytest -q tests/learn/test_lesson_flow_contract.py tests/learn/test_teaching_loop.py`
  - Passed: 52 tests.
- `uv run pytest -q tests/learn -rs`
  - Passed: 461 passed, 1 skipped.
- `uv run ruff check tests/learn/test_all_lessons_runtime_path.py`
  - Passed.
- `uv run pytest -q tests/learn/test_all_lessons_runtime_path.py -x`
  - Passed: 36 tests.
- `uv run pytest -q tests/learn/test_all_lessons_runtime_path.py tests/learn/test_lesson_flow_contract.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_ws_beginner_path.py`
  - Passed: 107 tests.
- `uv run ruff check src/vibemix/learn/progress.py scripts/live_learn_screen_probe.py tests/learn/test_live_learn_screen_probe.py tests/test_learn_progress_env_path.py`
  - Passed.
- `uv run pytest -q tests/learn/test_live_learn_screen_probe.py tests/test_learn_progress_env_path.py`
  - Passed: 4 tests.
- `uv run pytest -q tests/learn/test_live_learn_screen_probe.py tests/learn/test_live_learn_socket_jog_probe.py tests/learn/test_all_lessons_runtime_path.py tests/test_learn_progress_env_path.py`
  - Passed: 43 tests.
- `uv run ruff check scripts/learn_live_readiness.py tests/learn/test_learn_live_readiness.py`
  - Passed.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py`
  - Passed: 10 tests.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_live_learn_screen_probe.py tests/learn/test_live_learn_socket_jog_probe.py tests/learn/test_all_lessons_runtime_path.py tests/test_learn_progress_env_path.py`
  - Passed: 53 tests.
- `uv run ruff check scripts/run_learn_live_proof.py tests/learn/test_run_learn_live_proof.py scripts/learn_live_readiness.py tests/learn/test_learn_live_readiness.py`
  - Passed.
- `uv run pytest -q tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_live_learn_screen_probe.py tests/learn/test_live_learn_socket_jog_probe.py tests/learn/test_all_lessons_runtime_path.py tests/test_learn_progress_env_path.py`
  - Passed: 58 tests.
- `uv run ruff check scripts/validate_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py scripts/run_learn_live_proof.py tests/learn/test_run_learn_live_proof.py scripts/learn_live_readiness.py tests/learn/test_learn_live_readiness.py`
  - Passed.
- `uv run pytest -q tests/learn/test_validate_learn_live_proof.py`
  - Passed: 9 tests.
- `uv run pytest -q tests/learn/test_validate_learn_live_proof.py tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/learn/test_live_learn_screen_probe.py tests/learn/test_live_learn_socket_jog_probe.py tests/learn/test_all_lessons_runtime_path.py tests/test_learn_progress_env_path.py`
  - Passed: 70 tests.
- `uv run pytest -q tests/ipc/test_learn_envelope_parity_p92.py tests/learn/test_live_learn_screen_probe.py`
  - Passed: 18 tests.
- `uv run python scripts/check_ipc_schema.py`
  - Passed: 78 dataclasses validate against 78 schema entries.
- `npm --prefix tauri/ui run check:ipc`
  - Passed.
- `uv run pytest -q tests/ipc/test_learn_envelope_parity_p92.py tests/ui_bus/test_messages_schema.py`
  - Passed: 97 tests.
- `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_beginner_path_contract.spec.ts`
  - Passed: 16 tests.
- `uv run python scripts/run_learn_live_proof.py --start-app --out /tmp/vibemix-live-learn-proof/proof-screen-schema-v2-current.json`
  - Passed. The artifact reports `passed=true`, embedded validation
    `valid=true`, `screen_probe=passed`, `progress_file=passed`,
    `app_stop=passed`, `schema_version=2`, six progress skills, 4 ACKs,
    4 advances, `complete_seen=true`, and `progress_completed=true`.
- `uv run python scripts/validate_learn_live_proof.py /tmp/vibemix-live-learn-proof/proof-screen-schema-v2-current.json --require screen`
  - Passed.
- `uv run python scripts/run_learn_live_proof.py --no-screen --physical --wait-physical-seconds 1 --wait-interval 0.2 --out /tmp/vibemix-live-learn-proof/proof-wait-current.json`
  - Failed as expected in the current environment, but wrote a useful wait
    artifact: `physical_readiness_wait=failed`, `attempts=2`, final readiness
    still has `physical_learn=false`, and `physical_probe=skipped`.
- `uv run python scripts/run_learn_live_proof.py --start-app --out /tmp/vibemix-live-learn-proof/proof-screen-runner.json`
  - Passed. The artifact reports `screen_probe=passed` with 4 ACKs, 4
    advances, `complete_seen=true`, `progress_completed=true`, `app_stop=passed`,
    and `progress_file=L1.01.completed=true`.
- `uv run python scripts/run_learn_live_proof.py --start-app --physical --course3 --require-count-in --out /tmp/vibemix-live-learn-proof/proof-combined-current.json`
  - Overall failed, as expected, because requested physical/Course 3 proof
    remains unavailable. The artifact reports `screen_probe=passed` with 4
    ACKs, 4 advances, `complete_seen=true`, `progress_completed=true`,
    `app_stop=passed`, and `progress_file=L1.01.completed=true`.
    `physical_probe` and `course3_probe` are `skipped` with blockers:
    no MIDI controller input and no DDJ/FLX/Pioneer USB device.
- `uv run python scripts/validate_learn_live_proof.py /tmp/vibemix-live-learn-proof/proof-combined-current.json --require screen --require physical --require course3 --allow-skipped physical --allow-skipped course3`
  - Passed: current artifact is valid as screen proof plus explicit
    unavailable physical/Course3 proof. Without `--allow-skipped`, Course 3 now
    requires active lens frames, count-in evidence, and a citable cue id.
- `uv run python scripts/validate_learn_live_proof.py /tmp/vibemix-live-learn-proof/proof-combined-current.json --require physical`
  - Failed as expected: the artifact cannot be used as physical proof.
- `uv run python scripts/learn_live_readiness.py --require course3`
  - Failed as expected for the current machine state: no sidecar on `8765`,
    no MIDI controller ports, and no DDJ/FLX/Pioneer USB device. It did confirm
    Rekordbox is running, BlackHole is visible, and the rekordbox Aggregate
    Device is visible.
- `VIBEMIX_LIVE_SMOKE=1 uv run pytest -q -m macos_audio tests/test_main_live.py -v`
  - Passed: 1 live startup/shutdown test.
- Real sidecar on-screen Learn proof:
  - Started `python -m vibemix` with
    `VIBEMIX_LEARN_PROGRESS_PATH=/tmp/vibemix-live-learn-proof/learn-progress.json`.
  - `lsof -nP -iTCP:8765 -sTCP:LISTEN` showed the real app listening on
    `127.0.0.1:8765`.
  - `uv run python scripts/live_learn_screen_probe.py --seconds 60` passed:
    4 screen ACKs, 4 advances, `complete_lesson`, and `progress_completed=true`
    for `L1.01`.
  - The isolated progress JSON reloaded with `L1.01.completed=true`.
- `uv run ruff check src/vibemix/learn/graduation.py src/vibemix/learn/runtime.py src/vibemix/learn/__init__.py tests/learn/test_graduation.py`
  - Passed.
- `uv run pytest -q tests/learn/test_graduation.py tests/learn/test_lesson_flow_contract.py tests/learn/test_teaching_loop.py tests/learn/test_course_3_curriculum.py tests/learn/test_runtime_evidence_grounding.py`
  - Passed: 99 tests.
- `npm --prefix tauri/ui test -- --run tests/learn`
  - Passed: 145 tests.
- `npm --prefix tauri/ui test -- --run tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts tests/learn/test_practice_booth_shell.spec.ts`
  - Passed: 22 tests.
- `npm --prefix tauri/ui run test:e2e:learn`
  - Passed: 9 tests.
- `npm --prefix tauri/ui run build`
  - Passed.
- `cargo test --manifest-path tauri/src-tauri/Cargo.toml ws_client`
  - Passed: 5 tests.
- `uv run pytest -q tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_live_course3_lens_probe.py`
  - Passed: 8 tests.
- `git diff --check`
  - Passed.
- `uv run python scripts/sniff_controller.py --list`
  - Saw `DDJ-FLX4`.
- `uv run python scripts/sniff_controller.py --port FLX4 --seconds 5 --mode callback`
  - Completed, but captured 0 frames because no physical movement was observed.
- `uv run ruff check scripts/live_learn_jog_probe.py tests/learn/test_live_learn_jog_probe.py`
  - Passed.
- `uv run pytest -q tests/learn/test_live_learn_jog_probe.py tests/learn/test_physical_controller_pipeline.py tests/midi/test_sniff_controller.py`
  - Passed: 25 tests.
- `uv run python scripts/live_learn_jog_probe.py --help`
  - Passed.
- `uv run ruff check scripts/live_learn_socket_jog_probe.py tests/learn/test_live_learn_socket_jog_probe.py`
  - Passed.
- `uv run pytest -q tests/learn/test_live_learn_socket_jog_probe.py tests/learn/test_live_learn_jog_probe.py tests/learn/test_physical_controller_pipeline.py tests/learn/test_ws_beginner_path.py`
  - Passed: 11 tests.
- `uv run python scripts/live_learn_socket_jog_probe.py --help`
  - Passed.
- Current hardware state after the live on-screen proof:
  - Rekordbox is running.
  - `uv run python scripts/sniff_controller.py --list` returns no MIDI input
    ports.
  - `system_profiler SPUSBDataType` currently shows no DDJ/FLX/Pioneer device.
  - `system_profiler SPAudioDataType` shows BlackHole and the Rekordbox
    aggregate, but no FLX4 audio device.
- `uv run ruff check scripts/audition_learn_exemplars.py tests/learn/test_exemplar_audition.py`
  - Passed.
- `uv run pytest -q tests/learn/test_exemplar_audition.py tests/learn/test_exemplar_packaged_fallback.py tests/learn/test_exemplar_player.py`
  - Passed: 16 tests after adding durable artifact contracts.
- `uv run python scripts/audition_learn_exemplars.py --out /tmp/vibemix-live-learn-proof/learn-exemplar-audit-current.json`
  - Passed: JSON reports all 4 loops decode as stereo, hash-match manifest,
    have 0 clipped samples, and are non-silent. The artifact reports
    `technical_passed=true`, `release_ready=false`, and diagnosis
    `technical_audit_passed_ear_pass_pending`.
- `uv run python scripts/audition_learn_exemplars.py --help`
  - Passed.
- `uv run ruff check src/vibemix/runtime/ws_bus.py scripts/live_course3_lens_probe.py tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_live_course3_lens_probe.py`
  - Passed.
- `uv run pytest -q tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_live_course3_lens_probe.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_ws_bus_empty_frames.py tests/state/test_refresh.py tests/state/test_coach_course3_confidence_gate.py`
  - Passed: 77 tests.
- `uv run python scripts/live_course3_lens_probe.py --help`
  - Passed.
- `uv run ruff check scripts/validate_learn_live_proof.py scripts/run_learn_live_proof.py scripts/learn_live_readiness.py scripts/live_course3_lens_probe.py tests/learn/test_validate_learn_live_proof.py tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/runtime/test_live_course3_lens_probe.py tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_ws_bus_deck_state.py tests/test_audio_macos.py src/vibemix/runtime/ws_bus.py src/vibemix/platform/_audio_macos.py src/vibemix/agent/config.py`
  - Passed after adding Course 3 probe diagnostics and `deck_state.track_id`.
- `uv run pytest -q tests/learn/test_validate_learn_live_proof.py tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/runtime/test_live_course3_lens_probe.py tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_ws_bus_deck_state.py tests/test_audio_macos.py`
  - Passed: 64 tests.
- `uv run ruff check src/vibemix/runtime/ws_bus.py tests/runtime/test_ws_bus_course3_lens.py scripts/live_course3_lens_probe.py tests/runtime/test_live_course3_lens_probe.py`
  - Passed after adding lens readiness/blocker fields.
- `uv run pytest -q tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_live_course3_lens_probe.py tests/learn/test_validate_learn_live_proof.py`
  - Passed: 23 tests.
- `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts tests/learn/test_ws_client_filters_mascot.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts`
  - Passed: 22 tests.
- `uv run pytest -q tests/learn/test_validate_learn_live_proof.py tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/runtime/test_live_course3_lens_probe.py tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_ws_bus_deck_state.py tests/test_audio_macos.py`
  - Passed: 66 tests after the readiness/blocker lens additions.
- `uv run ruff check scripts/learn_live_readiness.py tests/learn/test_learn_live_readiness.py scripts/run_learn_live_proof.py tests/learn/test_run_learn_live_proof.py`
  - Passed after adding live Course 3 context readiness.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py`
  - Passed: 24 tests.
- `uv run pytest -q tests/learn/test_validate_learn_live_proof.py tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/runtime/test_live_course3_lens_probe.py tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_ws_bus_deck_state.py tests/test_audio_macos.py`
  - Passed: 70 tests after live Course 3 context readiness.
- `uv run ruff check scripts/validate_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed after surfacing readiness/context blockers in validation errors.
- `uv run pytest -q tests/learn/test_validate_learn_live_proof.py`
  - Passed: 12 tests.
- `uv run pytest -q tests/learn/test_validate_learn_live_proof.py tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/runtime/test_live_course3_lens_probe.py tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_ws_bus_deck_state.py tests/test_audio_macos.py`
  - Passed: 72 tests after validator blocker surfacing.
- `uv run ruff check scripts/learn_live_readiness.py tests/learn/test_learn_live_readiness.py scripts/run_learn_live_proof.py tests/learn/test_run_learn_live_proof.py scripts/validate_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed after fixing the async proof-runner/live-context sampler seam.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed: 37 tests.
- `uv run pytest -q tests/learn/test_validate_learn_live_proof.py tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/runtime/test_live_course3_lens_probe.py tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_ws_bus_deck_state.py tests/test_audio_macos.py`
  - Passed: 73 tests after the async seam fix.
- `uv run python scripts/validate_learn_live_proof.py /tmp/vibemix-live-learn-proof/proof-course3-ddj-auto-master-48k-current.json --require course3`
  - Failed as expected because the old artifact predates live-context
    readiness and Course 3 did not prove active lens/count-in/citable cue.
- `uv run python scripts/run_learn_live_proof.py --start-app --start-timeout 30 --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-course3-seconds 12 --wait-interval 2 --course3-context-seconds 1.5 --course3-seconds 20 --out /tmp/vibemix-live-learn-proof/proof-course3-live-context-current.json`
  - Failed honestly. The app started and stopped cleanly; the live-context
    sampler read 43 flat frames and recorded `music=0.0`, `audible=false`,
    `deck=none`, `deck_state={}`, and Course 3 lens blockers
    `waiting_for_audio`, `waiting_for_deck`, `waiting_for_deck_track`, and
    `waiting_for_cue`.
- `uv run python scripts/validate_learn_live_proof.py /tmp/vibemix-live-learn-proof/proof-course3-live-context-current.json --require course3`
  - Failed as expected with actionable readiness errors: live master audio not
    audible, no deck attribution, and no citable `deck_state.track_id`.
- `uv run python scripts/learn_live_readiness.py --help`
  - Passed and documents `--live-context-seconds`.
- `uv run python scripts/run_learn_live_proof.py --help`
  - Passed and documents `--course3-context-seconds`.
- `cd tauri/ui && npx playwright test -c tests/learn/playwright.config.ts tests/learn/browser-python-beginner-path.pw.ts tests/learn/browser-responsive.pw.ts`
  - Passed: 3 tests after fixing repeat screen-button presses.
- `npm --prefix tauri/ui run test:e2e:learn`
  - Passed: 10 tests.
- `npm --prefix tauri/ui run build`
  - Passed.
- `uv run ruff check scripts/learn_live_readiness.py tests/learn/test_learn_live_readiness.py`
  - Passed after accepting MIDI + controller-audio visibility when USB profiler
    misses the DDJ.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py`
  - Passed: 11 tests.
- `uv run ruff check scripts/live_course3_lens_probe.py tests/runtime/test_live_course3_lens_probe.py scripts/run_learn_live_proof.py tests/learn/test_run_learn_live_proof.py`
  - Passed after adding Course 3 lesson-start and isolated unlock seeding.
- `uv run pytest -q tests/runtime/test_live_course3_lens_probe.py tests/learn/test_run_learn_live_proof.py`
  - Passed: 14 tests after Course 3 lesson-start and isolated unlock seeding.
    The runner remains covered in the combined audio-backend run below.
- `uv run ruff check src/vibemix/agent/config.py src/vibemix/platform/_audio_macos.py scripts/run_learn_live_proof.py tests/test_audio_macos.py tests/learn/test_run_learn_live_proof.py`
  - Passed.
- `uv run pytest -q tests/test_audio_macos.py tests/learn/test_run_learn_live_proof.py`
  - Passed: 27 tests.
- `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts`
  - Passed: 15 tests.
- `cd tauri/ui && npx playwright test -c tests/learn/playwright.config.ts tests/learn/browser-responsive.pw.ts`
  - Passed: 1 test.
- `npm --prefix tauri/ui run test:e2e:learn`
  - Passed: 10 tests, including the new narrow-viewport responsive shell
    contract.
- `npm --prefix tauri/ui run build`
  - Passed.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --physical --physical-seconds 35 --out /tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json`
  - Passed, with the user nudging the left jog wheel.
- `uv run python scripts/validate_learn_live_proof.py /tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json --require physical`
  - Passed.
- `uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --course3-seconds 60 --out /tmp/vibemix-live-learn-proof/proof-course3-ddj-auto-master-48k-current.json`
  - Failed honestly. This is no longer a BlackHole-silence failure:
    `app_start=passed`, readiness before probes was green, L3.01 loaded, and
    stdout showed live audio (`music≈0.03..0.08`, `audible=1`). The Course 3
    lens stayed cold because `deck=none`; the captured now-playing title was a
    podcast/system-output source rather than a Rekordbox/library deck source.
    Validator errors were: no active Course 3 lens, no count-in evidence, and no
    citable next phrase cue id.
- Direct auto-master probe:
  `VIBEMIX_AUTO_MASTER_INPUT=1 uv run python - <<'PY' ... select_active_master_input ...`
  selected `BlackHole 16ch @ 48000Hz` on this rig. The system output was set to
  `BlackHole 16ch` during the live proof pass.
- `uv run ruff check scripts/learn_live_readiness.py tests/learn/test_learn_live_readiness.py`
  - Passed after replacing raw TCP socket probing with a real WebSocket
    handshake.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py`
  - Passed: 17 tests.
- `uv run ruff check scripts/learn_live_readiness.py tests/learn/test_learn_live_readiness.py scripts/validate_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py`
  - Passed after adding proof lifecycle validation.
- `uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_validate_learn_live_proof.py`
  - Passed: 31 tests.
- `uv run pytest -q tests/learn/test_validate_learn_live_proof.py tests/learn/test_run_learn_live_proof.py tests/learn/test_learn_live_readiness.py tests/runtime/test_live_course3_lens_probe.py tests/runtime/test_ws_bus_course3_lens.py tests/runtime/test_ws_bus_deck_state.py tests/test_audio_macos.py`
  - Passed: 77 tests after the WebSocket-safe readiness and lifecycle
    validation hardening.
- `uv run python scripts/run_learn_live_proof.py --start-app --start-timeout 20 --auto-master-input --no-screen --out /tmp/vibemix-live-learn-proof/proof-socket-handshake-current.json`
  - Passed. The artifact reports `app_start=passed`, `app_stop=passed`, and
    socket `protocol=websocket`; captured app stderr has no invalid HTTP
    handshake noise.
- `git diff --check`
  - Passed.
- `lsof -nP -iTCP:8765 -sTCP:LISTEN` and
  `lsof -nP -iTCP:5188 -sTCP:LISTEN`
  - Both returned no listeners after the smoke proof.
- `uv run ruff check src/vibemix/learn/curriculum.py src/vibemix/learn/curriculum_projection.py src/vibemix/learn/lesson_flow.py src/vibemix/learn/ipc_handlers.py src/vibemix/learn/__init__.py scripts/export_learn_curriculum_meta.py tests/learn/test_curriculum_projection.py tests/learn/test_lesson_flow_contract.py`
  - Passed after adding the course registry/generated curriculum projection.
- `uv run pytest -q tests/learn/test_curriculum_projection.py tests/learn/test_lesson_flow_contract.py tests/learn/test_ipc_handlers_dispatch.py tests/learn/test_progress_persistence.py`
  - Passed: 91 tests.
- `npm --prefix tauri/ui run check:learn-curriculum`
  - Passed; the generated frontend curriculum projection matches Python.
- `npm --prefix tauri/ui test -- --run tests/learn/test_curriculum_meta.spec.ts tests/learn/test_hud_progress_dots_keyboard.spec.ts`
  - Passed: 9 tests.
- `uv run pytest -q tests/learn/test_skill_tree.py tests/learn/test_all_lessons_runtime_path.py tests/learn/test_lesson_runtime_smoke.py`
  - Passed: 64 tests.
- `npm --prefix tauri/ui run build`
  - Passed.
- `git diff --check`
  - Passed after the course registry/generated projection slice.
- `npm --prefix tauri/ui test -- --run tests/learn/test_progress_list.spec.ts tests/learn/test_curriculum_meta.spec.ts tests/learn/test_hud_progress_dots_keyboard.spec.ts`
  - Passed: 32 tests after the calm lesson-map accordion slice.
- `npm --prefix tauri/ui test -- --run tests/learn/test_practice_booth_shell.spec.ts`
  - Passed: 15 tests.
- `cd tauri/ui && npx playwright test -c tests/learn/playwright.config.ts tests/learn/browser-responsive.pw.ts tests/learn/browser-accessibility.pw.ts`
  - Passed: 4 tests.
- `npm --prefix tauri/ui test -- --run tests/learn`
  - Passed: 149 Learn Vitest tests.
- `npm --prefix tauri/ui run test:e2e:learn`
  - Passed: 10 Playwright tests.
- `npm --prefix tauri/ui run build`
  - Passed after the calm lesson-map accordion slice.
- `git diff --check`
  - Passed after the calm lesson-map accordion slice.

## Live proof commands

Use the screen probe whenever the app is running, even with no controller
visible. Use the jog probes only with the controller plugged in and the user
ready to move controls.

```bash
uv run python scripts/run_learn_live_proof.py --start-app --out /tmp/vibemix-live-learn-proof/proof-screen-runner.json
```

This is the one-command screen-proof artifact path. It starts the real app,
uses isolated Learn progress, runs the L1.01 screen proof, stops the app, and
writes one JSON report. Add `--physical` and/or `--course3 --require-count-in`
only after the corresponding readiness command is green.

```bash
uv run python scripts/validate_learn_live_proof.py /tmp/vibemix-live-learn-proof/proof-screen-runner.json --require screen
```

Use this before summarizing a proof artifact. For the current combined artifact,
the honest validation command is:

```bash
uv run python scripts/validate_learn_live_proof.py /tmp/vibemix-live-learn-proof/proof-combined-current.json --require screen --require physical --require course3 --allow-skipped physical --allow-skipped course3
```

Do not use `--allow-skipped` after real physical/Course 3 proof is expected.

```bash
uv run python scripts/run_learn_live_proof.py --start-app --physical --wait-physical-seconds 120 --out /tmp/vibemix-live-learn-proof/proof-physical-wait.json
```

Use this when the controller may be plugged/replugged during the run. It keeps
polling readiness before deciding whether to run the jog proof.

```bash
uv run python scripts/learn_live_readiness.py --require screen
```

Run this before the screen proof. It should pass only when the real app or
sidecar is already listening on `127.0.0.1:8765`.

```bash
VIBEMIX_LEARN_PROGRESS_PATH=/tmp/vibemix-live-learn-proof/learn-progress.json uv run python -m vibemix
```

In another shell:

```bash
uv run python scripts/live_learn_screen_probe.py --seconds 60
```

Passing this proves the real sidecar socket can start `L1.01`, accept the
on-screen `lesson_continue` ACKs, wait through the real Learn dwell, emit
completion, and persist progress. The env var keeps this proof out of the
user's normal Learn progress file.

```bash
uv run python scripts/learn_live_readiness.py --require physical
```

Run this before the jog probes. If it fails, the JSON names whether the missing
piece is the sidecar socket, MIDI port, USB device, or audio routing.

```bash
uv run python scripts/live_learn_socket_jog_probe.py --seconds 20
```

Run this while `python -m vibemix` or the Tauri sidecar is already running.
During the run, nudge the left jog wheel. Passing this proves the live
one-socket sidecar path sees the jog pulse, accepts the Learn ACK, and advances
L1.07.

```bash
uv run python scripts/live_learn_jog_probe.py --port FLX4 --seconds 20
```

During that run, nudge the left jog wheel. Passing this captures the live byte
and prints a JSON summary proving it reached `ControllerState`, `MidiMirror`,
the Learn ACK handler, and the L1.07 verifier.

```bash
uv run python scripts/live_course3_lens_probe.py --require-count-in --seconds 30
```

Run this while Course 3, Rekordbox, and routed audio are active. Passing means
the existing live socket exposed `session_active=true`, phrase confidence,
`next_phrase_at`, and a citable cue id for the next count-in.

For rigs where `BlackHole 2ch` is not the live 48 kHz route, use the auto
master finder:

```bash
uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --require-count-in --wait-course3-seconds 120 --out /tmp/vibemix-live-learn-proof/proof-course3-auto-master.json
```

If you know the exact device, an explicit override is also supported:

```bash
uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --input-device "BlackHole 16ch" --require-count-in --wait-course3-seconds 120 --out /tmp/vibemix-live-learn-proof/proof-course3-blackhole16.json
```

Do not treat "audio is audible" as Course 3 proof. The last auto-master artifact
captured system audio but still had `deck=none`; Course 3 needs a Rekordbox
track/playhead/library/cue chain, not just any Mac output routed to BlackHole.
After the diagnostic patch, a failed artifact should name this explicitly in
`stages.course3_probe.result.diagnostics.blockers` (for example
`audible deck stayed none`, `deck_state stayed empty`, or
`deck_state had no citable track_id at confidence floor`). The flat lens itself
also carries machine-readable `blockers`, so the UI can stay quiet while proof
artifacts remain exact.
With the live-context readiness gate, the runner should now wait or skip before
the expensive Course 3 count-in probe when the sidecar is merely hearing generic
system audio or a deck row is not citable.
Fresh artifact:
`/tmp/vibemix-live-learn-proof/proof-course3-live-context-current.json` proves
the new gate no longer throws an async-loop error inside the proof runner. It
also shows the current rig was silent to vibemix during the sample window, so
the next live attempt must start real Rekordbox playback into the routed master
before Course 3 can advance to cue proof.

The latest route-settings proof adds a read-only Rekordbox settings clue:
`/tmp/vibemix-live-learn-proof/proof-course3-route-settings-runner-current.json`
still skips Course 3 honestly, but now reports the persisted Rekordbox
`audioDeviceManager` output as `BlackHole 2ch` at `44100.0`, while macOS output
and system audio are on `BlackHole 16ch`. The BlackHole self-test passes, both
BlackHole captures remain silent for external playback, and the package
verifier now surfaces this exact next action instead of a generic route hint:
align Rekordbox Audio preferences with the vibemix capture input
(`BlackHole 16ch` or an aggregate that includes it), then play a deck with
channel and master faders up.

The newer auto-master-plan proof is now the verifier-preferred Course 3
artifact:
`/tmp/vibemix-live-learn-proof/proof-course3-auto-master-plan-current.json`.
It keeps `VIBEMIX_AUTO_MASTER_INPUT=1`, notices the same persisted
`BlackHole 2ch` Rekordbox route, but rejects it as a silent-start fallback
because the capture row is `44100Hz` and vibemix capture expects `48000Hz`.
The app therefore starts on `BlackHole 16ch @ 48000Hz` as a 48 kHz fallback.
This is deliberate: do not force the app onto a 44.1 kHz route just because
Rekordbox has it saved. If Rekordbox is changed to a 48 kHz loopback or
aggregate, the auto-master preferred fallback hook can follow it on the next
proof run.
The consolidated package verifier now surfaces that route plan directly at
`sections.live_proofs.course3.route_plan`, including the rejected fallback
reason and the selected `BlackHole 16ch @ 48000Hz` input. Its top-level
`next_actions` now list the rate mismatch before the generic Rekordbox route
instruction, so the next operator sees why `BlackHole 2ch` was not used.
The latest readiness and runner artifacts have cleared the previous Course 3
sample-rate blocker. A timestamped backup was written beside
`~/Library/Application Support/Pioneer/rekordbox6/rekordbox3.settings`, then the
two persisted BlackHole 2ch Rekordbox rate fields were moved from `44100.0` to
`48000.0` and Rekordbox was reopened. Readiness now reports Rekordbox saved to
`BlackHole 2ch @ 48000Hz`, the selected vibemix capture route also at
`48000Hz`, and a passing loopback self-test.
The current verifier-preferred Course 3 artifact is now
`/tmp/vibemix-live-learn-proof/proof-course3-auto-master-current.json`. It
records the app selecting `BlackHole 2ch @ 48000Hz`, the opt-in Rekordbox
spacebar nudge passing, the direct loopback self-test passing, and the external
playback checks staying silent. Its current diagnosis is
`loopback_route_healthy_external_playback_absent`: Course 3 remains honestly
unavailable until routed Rekordbox deck audio crosses the capture floor with
deck attribution and a citable track.
The same readiness/proof path now also checks macOS Now Playing metadata for
Course 3. The current desk is publishing a paused WebKit podcast title
(`The Diary Of A CEO - Chase Hughes...`) from `com.apple.WebKit.GPU`, not a
Rekordbox deck title, so the verifier's operator command explicitly says to
stop unrelated media or make Rekordbox the active playing source before rerun.
The diagnosis now includes a structured `operator_action` object as well: route
`BlackHole 2ch @ 48000Hz`, prompt "play a real Rekordbox library track through
that route with channel and master faders up", and the four explicit steps:
clear unrelated media / make Rekordbox active, load and play a library track,
raise channel/master until loopback capture has signal, then rerun the Course 3
count-in proof.
The curriculum audit and package verifier now expose a machine-readable
`course_pack_contract` at `sections.curriculum.course_pack_contract`. It names
the Python source of truth, transcript root, generated frontend projection,
required course/lesson/transcript fields, the lesson-flow compiler gate, and
the exact commands for adding a future course without hand-editing the
frontend mirror. The package verifier now promotes that into the
`future_course_extension_contract` completion row, so future-course readiness is
scored in the same matrix as curriculum, quality, UI, and live proof. The
current contract artifact is
`/tmp/vibemix-live-learn-proof/learn-curriculum-audit-current.json`.
The practice-booth primary action now labels replay honestly. When every
available unlocked lesson is already complete, the booth says
`replay opening dialog` and sends `ipc.learn.start_lesson` with
`level="replay"` instead of showing a misleading `start ...` label.

```bash
uv run python scripts/audition_learn_exemplars.py --list-devices
```

This lists output devices as JSON so the listener can choose the correct
`--device-index` for the ear-pass. The current generated
`operator_action.steps[1]` recommends:

```bash
uv run python scripts/audition_learn_exemplars.py --play --device-index 3 --say-prompts --out /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json
```

That plays through `MacBook Pro Speakers` on this desk instead of a loopback or
capture sink, speaks each band label before playback, and persists the audition
summary before the human writes the approval artifact.

```bash
uv run python scripts/audition_learn_exemplars.py
```

This is the non-interactive packaged-loop audit. It does not approve the sound;
it gives the ear-pass operator objective stats before listening.

```bash
uv run python scripts/audition_learn_exemplars.py --play --device-index <output-device-index> --say-prompts --out /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json
```

This plays the four packaged loops through the Learn exemplar player seam for
human approval or replacement, with spoken band labels on macOS and a durable
audition artifact.

```bash
uv run python scripts/audition_learn_exemplars.py --approve-ear-pass --approved-by <name> --audition /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json --approval-out /tmp/vibemix-live-learn-proof/learn-exemplar-ear-pass-current.json
```

Run this only after the listener has heard and approved the exact current loop
bank. The approval is hash-bound and now requires the matching audition
artifact first; changing any packaged loop invalidates it.

```bash
VIBEMIX_LIVE_LEARN_JOG=1 uv run pytest -q -m macos_audio tests/learn/test_live_flx4_learn_jog.py
```

This is the pytest form of the same discharge. Use it after the probe or when
you want a test-run artifact.

```bash
VIBEMIX_LIVE_SMOKE=1 uv run pytest -m macos_audio tests/test_main_live.py
```

This proves `python -m vibemix` starts, remains alive briefly, shuts down
cleanly, and creates a recording session with the configured live devices. It
does not by itself prove the coach heard and cited a real routed set.

```bash
uv run pytest -m macos_audio tests/test_midi_macos_live.py -v
```

This proves the OS-visible FLX4 resolves to the expected profile. The docstring
in that file contains the manual unplug/replug/live movement recipe.

```bash
npm --prefix tauri/ui test -- tests/learn/test_practice_booth_shell.spec.ts
npm --prefix tauri/ui test
npm --prefix tauri/ui run build
npm --prefix tauri/ui run test:e2e:learn
```

These cover the calm booth shell, optional map, screen-deck fallbacks, replay
labeling, full jsdom frontend coverage, production renderer build, and browser
Learn accessibility/contrast/responsive/sidecar-path checks after UI changes.

```bash
uv run pytest -q tests/learn
```

This is the broad deterministic Learn runtime/curriculum/proof-script suite.
The live FLX4 jog proof remains intentionally opt-in and skipped unless
`VIBEMIX_LIVE_LEARN_JOG=1` is set and the operator moves the left jog wheel.

```bash
uv run pytest -q tests/learn/test_learn_live_readiness.py tests/learn/test_run_learn_live_proof.py tests/learn/test_validate_learn_live_proof.py tests/learn/test_verify_learn_package.py
```

This covers the Course 3 readiness/proof/verifier artifact contract, including
the corrected explicit-silent-loopback behavior, Now Playing source mismatch,
and current app-start artifact discovery.

```bash
uv run python scripts/verify_learn_package.py --out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json
```

This refreshes the combined Learn package artifact. As of the current handoff it
passes deterministic package integrity, but remains non-release-ready until the
ear-pass and Course 3 routed-audio proof are discharged.

The verifier now also requires and reports a full frontend-quality artifact:

```bash
uv run python scripts/run_learn_frontend_quality.py --out /tmp/vibemix-live-learn-proof/learn-frontend-quality-current.json
```

The latest artifact passed all five rows: the targeted app-entry Vitest
contract, targeted choice/replay Vitest contract, broad Learn Vitest,
production build, and browser Learn e2e.
`learn-package-verification-current.json` now includes
`sections.frontend_quality`; the single package command below is the preferred
way to refresh the full matrix. The targeted row covers recommended start,
opt-in lesson choice, locked-course handling, and completed-lesson replay via:
`test_practice_booth_shell.spec.ts`, `test_progress_list.spec.ts`,
`test_curriculum_meta.spec.ts`, and `test_hud_progress_dots_keyboard.spec.ts`.

The verifier also requires a desktop-shell quality artifact:

```bash
uv run python scripts/run_learn_desktop_quality.py --out /tmp/vibemix-live-learn-proof/learn-desktop-quality-current.json
```

The current artifact first runs `learn_tauri_frontend_dist_build`
(`npm --prefix tauri/ui run build`), then passes Rust formatting,
`cargo check --manifest-path tauri/src-tauri/Cargo.toml`, and the targeted
`sidecar_audio_env_defaults` Rust tests. This makes Tauri's embedded
`../ui/dist` assets an explicit desktop-shell prerequisite instead of letting a
missing hashed frontend asset appear as a confusing Cargo failure. It also
proves the app-spawned sidecar defaults `VIBEMIX_AUTO_MASTER_INPUT=1` when the
user has not chosen a capture device, while preserving explicit user/device
choices. The Tauri shell is now a first-class package gate instead of an
implicit terminal check.

There is now a single deterministic package command that refreshes Python
quality, frontend quality, desktop-shell quality, and the package verifier in
order:

```bash
uv run python scripts/run_learn_perfection_package.py --out /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json
```

That command writes `/tmp/vibemix-live-learn-proof/learn-python-quality-current.json`,
refreshes `/tmp/vibemix-live-learn-proof/learn-frontend-quality-current.json`,
refreshes `/tmp/vibemix-live-learn-proof/learn-desktop-quality-current.json`,
then refreshes `/tmp/vibemix-live-learn-proof/learn-package-verification-current.json`.
Current package command result: `passed=true`, `release_ready=false`,
`verification_refreshed=true`; the matrix is now 20/22 proven because
`python_quality_suite`, `all_lessons_runtime_contract`,
`teaching_loop_contract`, `adaptive_coaching_runtime_contract`,
`course3_auto_master_finder_contract`,
`course3_mix_count_in_anchor_contract`,
`frontend_quality_suite`,
`frontstage_simplicity_contract`, `lesson_choice_replay_contract`,
`browser_practice_booth_quality_contract`, `app_entry_contract`,
`tauri_learn_window_contract`, and
`desktop_shell_quality` are first-class rows. The
`session_debrief_profile_contract` proves Learn session events are useful after
the lesson. The `future_course_extension_contract` row is also proven and
checks the source map, registry/transcript contract, generated frontend
projection, unlock-gate rule, and verification command set for adding more
courses. The `all_lessons_runtime_contract` is backed by
`learn_all_lessons_runtime_pytest`, proving every one of the 36 beginner
lessons starts through `ipc.learn.start_lesson`, receives canonical ACK action
shapes, reaches `LessonRuntime.completed`, persists completed
`LearnProgress`, and covers the observer lessons `L1.14`, `L1.16`, and
`L2.14`. The `frontstage_simplicity_contract` is backed by
`learn_frontstage_simplicity_vitest`, proving the default booth offers one
primary recommended action, keeps the 36-lesson map hidden by default, does
not auto-open the map on progress snapshots, and survives a DDJ disconnect by
falling back to the on-screen deck, keeping the map opt-in, and repainting the
active lesson highlight after a mid-lesson remount. The
verifier evidence now names that as
`frontstage_simplicity_contract.evidence.hardware_unavailable`, which matters
because the current desk has no charged controller. The `teaching_loop_contract`
is backed by the targeted `learn_teaching_loop_pytest` command inside
`/tmp/vibemix-live-learn-proof/learn-python-quality-current.json`, proving
observe, decide, teach, verify, and adapt turns through `model_router` plus
deterministic verification metadata. The `adaptive_coaching_runtime_contract`
is backed by `learn_adaptive_coaching_pytest`, proving that timed hint strikes
emit `teaching_loop.turn_kind=hint`, wrong screen actions emit
`teaching_loop.turn_kind=adapt` without advancing, small MIDI movements write
registry-backed `midi`/`screen` citations, and unfinished lesson strike counts
persist to `LearnProgress`. The new `course3_auto_master_finder_contract` is
backed by `learn_auto_master_finder_pytest`, proving the Course 3 route finder
emits ranked candidate evidence for live signal, saved Rekordbox route, macOS
route, and 48 kHz loopback fallbacks, and rejects rate-mismatched fallbacks
before app startup. The new `course3_mix_count_in_anchor_contract` is backed by
`learn_course3_mix_anchor_pytest`, proving that Course 3 can form cue-backed
count-ins during a two-deck mix only when Now Playing title identity exactly
and unambiguously matches one citable deck row; ambiguous duplicate titles keep
the cue null. The new `app_entry_contract` is backed by
`learn_app_entry_vitest` inside
`/tmp/vibemix-live-learn-proof/learn-frontend-quality-current.json`, proving the
main session mode picker opens the Learn window, the shell palette can jump to
Learn, and the first recommended booth action can start from that entry. The
`tauri_learn_window_contract` is backed by `learn_tauri_window_vitest` and
`learn_cargo_learn_window_test`, proving the desktop app registers
`open_learn_window`, scopes the `learn` window in Tauri capabilities, preserves
the lowercase `learn` label, and loads bundled `learn.html` without launching a
second Python process. The `browser_practice_booth_quality_contract` is backed
by `learn_browser_booth_playwright`, proving the browser-rendered booth clears
the focused axe, responsive, computed-contrast, Tauri-forwarder, and direct
WebSocket fallback checks for recommended L1.01, and now also proves a wrong
on-screen EQ move returns grounded adaptive coaching from the Python harness
before recovering to lesson completion.
The
`session_debrief_profile_contract` is backed by runtime evidence tests and
debrief/profile integration tests: `learn_action_observed` now carries
`evidence_time`, cited learner actions are condensed into debrief critique with
`midi`/`screen` registry citations, cited Learn tutor lines can be preserved,
and profile write-back receives the structured Learn events. The current
not-proven rows are packaged EQ exemplar human ear-pass and Course 3 routed
live audio.

The curriculum evidence is sharper than a simple lesson count. The current
`curriculum_36_lesson_contract.evidence.flow_contract_summary` proves all 36
beginner lessons compile to 76 structured steps with deterministic verifier
shapes: 51 `button_press` steps, 25 `cc_delta` steps, 44 screen-only steps, 32
hardware-or-screen steps, 18 observable control IDs, and 13 backstage lenses
(`controller_state`, `live_audio`, `cue_section_lookahead`, `prepared_pool`,
`session_state`, `session_recording`, `debrief`, `dj_profile`, and the rest).
`src/vibemix/learn/curriculum_audit.py` now rejects unknown verifier kinds,
invalid button directions, and non-positive CC deltas, so those numbers are not
just inventory; they are part of the release-gate audit.

The current perfection-package artifact is also self-describing for handoff
review. Its `quality_contract.python_quality.commands` lists all nine Python
sub-gates (`learn_ruff`, `learn_codegen_check`, `learn_model_router_guard`,
`learn_all_lessons_runtime_pytest`, `learn_teaching_loop_pytest`,
`learn_adaptive_coaching_pytest`, `learn_auto_master_finder_pytest`,
`learn_course3_mix_anchor_pytest`, `learn_pytest`) and records
`quality_contract.python_quality.model_router_guard=true` and
`quality_contract.python_quality.all_lessons_runtime=true`, and
`quality_contract.python_quality.adaptive_coaching=true`, and
`quality_contract.python_quality.auto_master_finder=true`, and
`quality_contract.python_quality.course3_mix_anchor=true`, so a future
integration session does not need to open the nested Python artifact just to
confirm that those gates were part of the package pass. It now also lists
`quality_contract.frontend_quality.commands` and
`quality_contract.desktop_quality.commands`; the frontend list now includes
`learn_frontstage_simplicity_vitest`, `learn_tauri_window_vitest`, and
`learn_browser_booth_playwright`; the desktop list starts with
`learn_tauri_frontend_dist_build`, then `learn_cargo_fmt`,
`learn_cargo_check`, `learn_cargo_learn_window_test`, and
`learn_cargo_sidecar_audio_test`. It also records
`quality_contract.frontend_quality.tauri_window_contract=true` and
`quality_contract.frontend_quality.browser_booth_quality=true` plus
`quality_contract.desktop_quality.learn_window_test=true`.

The same verifier now exposes a machine-readable Course 3 operator recipe at
`sections.live_proofs.course3.operator_commands`. It carries the current
diagnosis action as `manual_action`, exposes the structured `operator_action`
mini-runbook, and provides these runnable commands:

```bash
uv run python scripts/learn_live_readiness.py --require course3 --live-context-seconds 5 --loopback-signal-seconds 2 --loopback-self-test-seconds 1 --capture-matrix-seconds 2 --out /tmp/vibemix-live-learn-proof/learn-course3-readiness-current.json
uv run python scripts/run_learn_live_proof.py --start-app --no-screen --course3 --seed-course3-unlocked --auto-master-input --nudge-rekordbox-playback --require-count-in --say-course3-prompts --wait-loopback-signal-seconds 30 --wait-capture-signal-seconds 30 --wait-course3-seconds 120 --course3-context-seconds 5 --loopback-signal-seconds 2 --loopback-self-test-seconds 1 --capture-matrix-seconds 2 --out /tmp/vibemix-live-learn-proof/proof-course3-auto-master-current.json
uv run python scripts/verify_learn_package.py --out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json
```

The latest live proof run of that recipe started and stopped the app cleanly,
brought up the sidecar, selected a BlackHole route, and successfully nudged
Rekordbox with Space. It still did not prove Course 3: the selected loopback was
silent, the capture matrix found no DJ/loopback signal, and the live socket saw
no audible deck-attributed track context. It also detected macOS Now Playing as
a paused WebKit source, not Rekordbox. The current verifier diagnosis remains a
route/playback problem, not a lesson-structure problem.

`learn_live_readiness.py` now supports `--out`; the saved readiness artifact at
`/tmp/vibemix-live-learn-proof/learn-course3-readiness-current.json` is useful
for route debugging, but it should not be treated as Course 3 proof. The current
package verifier already treats physical proof as proven; Course 3 remains the
unproven live-audio row. The auto-master finder now selects or explains a
target capture route from ranked candidates; in the latest readiness artifact
it targets `BlackHole 16ch @ 48000Hz` as a silent 48 kHz loopback fallback,
while Rekordbox's current persisted route is `DDJ-FLX4 @ 44100Hz` and macOS
output is `MacBook Pro Speakers`. The actual external playback signal remained
silent (`loopback_signal.rms=0.0`, `capture_matrix.top_signal=null`), BlackHole
self-test passed, and macOS Now Playing was a paused WebKit track, not
Rekordbox. The current diagnosis remains
`loopback_route_healthy_external_playback_absent`. The current
`operator_action` now points at the target capture route instead of echoing the
silent saved route: `route="BlackHole 16ch @ 48000Hz"`,
`target_capture_route="BlackHole 16ch @ 48000Hz"`, and
`current_rekordbox_route="Aggregate Device @ 48000Hz"`. In plain terms: set
Rekordbox's master/recording route to BlackHole 16ch, or to an aggregate that
actually includes that BlackHole route, then play a deck with channel/master
up.

The latest physical DDJ proof attempt at
`/tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json` is now a strict
controller proof. L1.07 loaded with `controller_id=pioneer_ddj_flx4`, the live
socket saw a nonzero `jog:A` movement, the probe sent the ACK, and the lesson
advanced. The package verifier no longer carries the physical controller row as
a release blocker.

The physical proof runner was also hardened after that attempt. If readiness did
not sample a capture matrix, `run_learn_live_proof.py` no longer passes
Rekordbox's saved `Aggregate Device` as an auto-master fallback just because the
setting exists; it records an `auto_master_fallback_rejected_reason` and lets
the app use its normal safe auto selection. Course 3 runs still use the sampled
auto-master recommendation from readiness.

The Space nudge is now signal-aware. Before pressing Space, the proof runner
checks loopback, capture-matrix, and live Course 3 context signal. If signal is
already present it records `rekordbox_spacebar_skipped_signal_present` and does
not toggle playback. In the latest artifact the precheck was silent
(`loopback_ok=false`, `capture_ok=false`, `live_context_ok=false`), so the nudge
pressed Space and still did not produce routed master audio.

L3.04 capstone copy was made truthful. It no longer promises that the debrief
automatically opens when the set ends; it says session evidence is saved for a
post-set debrief and asks the learner to use the existing debrief surface after
the set. The curriculum audit now exposes `copy_truthfulness_contract` and will
fail future transcript copy containing phrases such as `debrief opens` or
`opens automatically` until a real Learn runtime command and frontend invoke
path exist. The refreshed package verifier includes that contract under
`curriculum_36_lesson_contract.evidence.copy_truthfulness_contract` with no
unsupported claims.

Learn now also writes its own quiet timeline into the existing recording spine.
`LessonRuntime` accepts a fail-soft `session_event_logger`, and the live sidecar
adapts it to `VoiceRecorder.log_event`. This means `events.jsonl` can carry
`learn_lesson_loaded`, `learn_tutor_speak`, `learn_action_observed`, and
`learn_lesson_completed` beside the rest of the app's session events. It does
not make debrief auto-open, and it does not change the booth UI. The debrief
critique builder now consumes cited Learn action/tutor events, and the profile
write-back path receives the structured Learn events through the existing
session event list, so those milestones are no longer passive telemetry.

The latest live desk state is deliberately not marked complete. The physical
DDJ proof and launched Tauri proof are now clear, and the current refreshed
verifier reports `technical_passed=true`, `release_ready=false`, with two
completion blockers: packaged EQ exemplar human ear-pass and Course 3
routed-audio count-in proof. The Course 3 readiness logic was corrected so
Course 3 no longer requires a physical controller by itself; it now requires the
sidecar, Rekordbox, loopback/DJ audio visibility, and live/citable deck context.
The current Course 3 artifact therefore fails for the right reasons: BlackHole
2ch is selected from Rekordbox settings, but direct loopback capture is silent,
sampled capture inputs are below the floor, live master audio is not audible,
no Deck A/B/mix attribution exists, no citable `track_id` exists, and
macOS Now Playing still points at a paused WebKit track (`The Nommos - Iboga`)
instead of Rekordbox. The physical proof artifact was also refreshed after the
DDJ was unplugged; it now skips for the current truth (`DDJ-FLX4` absent from
MIDI and USB/controller audio), not for the earlier jog-window miss. The package
verifier now exposes physical operator commands beside Course 3 commands:
`sniff_controller.py --list`, physical readiness, the full L1.07 proof command,
and package verification. The no-controller frontstage behavior is now directly
tested: connect DDJ, disconnect DDJ, remain on `on-screen deck`, keep the
lesson map opt-in, show `screen deck is ready` only in the chooser, and keep
the primary recommended action wired to `ipc.learn.start_lesson`. No
`8765`/`8766` listeners were left running.

The Learn Python quality artifact now includes a dedicated
`learn_model_router_guard` command (`bash
scripts/release/check_no_hardcoded_model.sh`) between curriculum codegen and
the teaching-loop pytest. This makes the backstage tutor/model-router promise a
real package gate: the current artifact proves the router guard, teaching-loop
metadata, and full Learn pytest all pass before the verifier marks the
`teaching_loop_contract` proven. It also includes
`learn_adaptive_coaching_pytest`, which proves the grounded hint/adapt runtime
path as its own package row instead of burying it inside broad Learn pytest. The
top-level perfection-package artifact now mirrors both proofs through
`quality_contract`, while still keeping
`release_ready=false` honest for the remaining human/live rows.

The future-course path is now executable, not only documented.
`vibemix.learn.lesson_flow.build_lesson_flow_from_meta(...)` lets a draft
lesson compile through the same structured-flow machinery before it is merged
into `CURRICULUM`. `vibemix.learn.course_pack.validate_course_pack_draft(...)`
preflights proposed `CourseMeta`, course frame text, `LessonMeta` rows,
transcript metadata, expected actions, three-hint floor, observed
capabilities, id/path collisions, and new progress fields. It also has an
on-disk JSON manifest path now:
`uv run python scripts/validate_learn_course_pack.py <course-pack.json>`. The
CLI resolves transcript fixtures, writes a JSON report, and exits non-zero when
the draft is not merge-ready. The package verifier now records this as
`sections.curriculum.course_pack_contract.draft_validator` and the completion
row `future_course_extension_contract.evidence.draft_validator`. The refreshed
Python quality artifact includes the dedicated `learn_course_pack_pytest`
command, so stale artifacts without that row should be treated as not proven.

The current verifier and all-in-one package artifact also have a compact
release-blocker recipe. Read `release_blocker_recipe` in either
`/tmp/vibemix-live-learn-proof/learn-package-verification-current.json` or
`/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json` before
touching hardware. It contains exactly two rows right now:
`packaged_eq_exemplar_ear_pass` and `course3_live_audio_play_mode`. Each row
carries the current status, the manual operator action, and exact commands to
run next. The Course 3 row includes the BlackHole/Rekordbox route diagnosis and
operator steps; the current fallback action says to stop unrelated system audio,
route Rekordbox master/output to `BlackHole 2ch @ 48000Hz`, load and play a
real Rekordbox library track, raise channel/master faders until loopback capture
has signal, then rerun the proof. That proof command includes
`--say-course3-prompts` so macOS speaks the exact moment it needs external
playback/routing action. The EQ row includes the current bank fingerprint,
approval command, and audible output recommendation (`MacBook Pro Speakers`,
device index `3`). This is the fastest honest entry point for
the next integration session. The package artifact also mirrors
`quality_contract.python_quality.course_pack_preflight=true` when the current
pass included `learn_course_pack_pytest`.

The booth reset seam is now end-to-end instead of stale-until-next-snapshot.
When settings emits `ipc.learn.progress_state { action: "reset" }`, the sidecar
clears in-memory and on-disk progress, then sends `reset_ack` with the emptied
progress snapshot. The Learn window consumes `reset_ack.progress` just like a
snapshot, so the primary booth action immediately returns to `start opening
dialog`, course locks reset, completed lessons stop advertising replay, and the
lesson map stays opt-in. The refreshed frontstage quality artifact proves this
in `tests/learn/test_practice_booth_shell.spec.ts` with 25 tests.

The latest personality/quality slice keeps the same calm practice booth but
adds a small action-reward loop. Matched actions now leave a deterministic
receipt in the tutor dock (`clean touch · 01`, then rotating restrained labels),
and lesson completion leaves the booth with a one-line pulse such as
`clean pass · 1 move` while moving the primary action to the next lesson. This
is intentionally not a badge system or a new page: it makes proof feel noticed
without reintroducing a syllabus wall. The focused UI tests now cover this in
`test_tutor_speak_sr_announcement.spec.ts` and
`test_practice_booth_shell.spec.ts`; the current count for the latter is 25.
The small Course 3 route-doctor packet in `scripts/learn_live_readiness.py` is
also tested now, including `--say-course3-prompts` on the proof command and
operator steps copied into `course3_route_doctor`.

The Course 3 frontstage now consumes the live-lens blockers more intelligently.
The status bar still shows only one booth-sized phrase (`press play on deck`,
`open one channel`, `load a track`, or `keep playing`), but those states now
become active operator actions with deterministic next steps in `aria-label` /
`title`. This keeps the user surface calm while giving QA, screen readers, and
the next operator the actual route/play/deck/cue sequence. The operator-action
aria helper now preserves up to three bounded steps instead of dropping every
step after the first.

The live socket lens now carries those operator actions from the Python runtime,
too. `src/vibemix/runtime/ws_bus.py` derives a bounded `operator_action` from
the same `course3_lens.blockers` it already serialized: missing audio maps to
press play, audible-but-unattributed audio maps to open one channel, an audible
deck without a citable track maps to load a Rekordbox track, and cue-wait maps
to keep playing. It only does this when Course 3 is active or audio is already
audible, so the cold idle lens stays honest. It also avoids naming a specific
BlackHole route; route-specific steps still come from the readiness doctor.
`scripts/live_course3_lens_probe.py` now promotes the observed runtime
`operator_action` into failed proof summaries and
`scripts/validate_learn_live_proof.py` reports it as `course3 operator action:
...` while still failing strict Course 3 validation. Failed proof artifacts now
carry both pieces: why count-in was not proven and the next action the live
lens observed.

The latest Course 3 readiness probe no longer has the previous port-owner
blocker: `127.0.0.1:8765` now answers as the Vibemix Learn websocket. The
remaining blockers are audio-context blockers: macOS output is still
`MacBook Pro Speakers`, Rekordbox settings currently point at `DDJ-FLX4` at
`44100.0`, BlackHole 16ch/2ch captures are silent, live deck context has no
citable track, and Now Playing is paused WebKit media rather than Rekordbox.
`scripts/learn_live_readiness.py` now turns those blockers into the compact
Course 3 route doctor: route macOS/Rekordbox output to BlackHole 16ch, play a
real Rekordbox library track through that route, clear browser/system Now
Playing noise. The spoken Course 3 count-in proof command is attached next to
those steps. It also still names a foreign listener if the shared app socket is
stolen again.

`scripts/verify_learn_package.py` now discovers
`learn-course3-readiness-current.json` and merges its readiness status, blocker
list, diagnosis, auto-master recommendation, and route-doctor operator steps
into the `course3_live_audio_play_mode` release recipe without overclaiming
proof. This makes the quality analysis artifact actionable for the next
operator: the recipe points at the fresh readiness path and carries the exact
three Course 3 steps above.

After the readiness fix, the full package was refreshed again at
`/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json`: Python
quality, frontend quality, desktop quality, and package verifier all passed;
`technical_passed=true`, `release_ready=false`, matrix `20/22`. The two
remaining release rows are still the human EQ ear-pass and the Course 3 routed
audio/count-in proof. The latest package run also caught a global webview build
fixture drift in `tauri/ui/src/pill/index.test.ts`; the fixture now includes the
required `camelot` and `bpm` fields for `NextSuggestionWire`, and
`npm --prefix tauri/ui run build` is green again. The latest full package after
runtime-backed Course 3 operator actions passed all four commands with
`verification_refreshed=true`; the subsequent probe/validator action-surfacing
slice also refreshed the package successfully.

The desktop quality runner now also retries the exact Vite generated-dist
cleanup flake seen during the package pass (`ENOTEMPTY` while removing
`tauri/ui/dist/assets`) after clearing the generated `tauri/ui/dist`
directory. The latest standalone desktop artifact did not need the retry
(`retried_after_dist_cleanup=false`), but the runner is pinned against that
flake in `tests/learn/test_run_learn_desktop_quality.py`.

The packaged EQ exemplar ear-pass is still human-pending, but its release
artifact is now stricter. `audition_learn_exemplars.py` computes a
`bank_fingerprint` for the exact packaged bank: manifest hash plus canonical
track metadata and WAV hashes. New ear-pass approvals write that fingerprint,
and validation rejects missing/mismatched fingerprints as well as stale track
hashes. The current fingerprint is
`34e7aafe568b2e8badecb75fd28e0a8bd710f4fd1b1f2d84e7ff4a78584096e9`
with manifest hash
`8d8ae0dd1e418babb900dc70c3335829eae27629e9f8b5e6591721c435decd58`.
The package verifier now surfaces that fingerprint in the exemplar completion
row and enriches the release-blocker recipe with the current audible output
recommendation (`MacBook Pro Speakers`, device index `3`) plus `--say-prompts`
for spoken band labels and
`/tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json` for the
durable audition summary, while still correctly reporting `release_ready=false`
until a human approval artifact exists.

## Integration session priorities

1. Start from `release_blocker_recipe` in the freshest verifier or perfection
   package artifact. It is the canonical current operator checklist for the
   two non-proven release rows; do not infer a new blocker order from stale
   proof files.
2. Treat the physical DDJ-FLX4 L1.07 proof as cleared unless a new change
   touches controller mirroring, MIDI profiles, or Learn ACK routing. The latest
   standalone `learn-physical-readiness-current.json` is also green after the
   DDJ reload: MIDI sees `DDJ-FLX4`, USB/audio sees the controller, and the
   physical doctor reports `status=ready`. If the proof must be re-proven, use
   the strict app-bus proof with `--say-physical-prompts`.
3. Open the Learn window from the real app, start the recommended path, and
   complete at least one lesson with the physical controller, not only the
   on-screen deck.
4. With Rekordbox open and audio routed, run a short Learn plus cohost pass and
   confirm grounded evidence appears for what the user actually did and heard.
5. Run Course 3 as a real mini set, checking cue-section lookahead, prepared
   pool awareness, session-state gating, and graceful off-pool coaching.
   Before running the proof, play an actual Rekordbox library track through the
   routed master, not browser/system audio; raise the relevant channel fader so
   `audible_deck` resolves to `A`, `B`, or `mix`. On the current desk, the DDJ
   hardware is visible and BlackHole 16ch/2ch pass self-test, but passive
   capture is silent. The fresh Course 3 readiness doctor is more specific than
   the old route warning: Rekordbox is saved to `Aggregate Device`, the sampled
   matching input is `rekordbox Aggregate Device`, and that capture row is at
   44100Hz. First operator step: set that route to 48000Hz in Audio MIDI Setup
   or choose a 48k BlackHole/aggregate route, then play a deck with channel and
   master faders up. The proof harness still correctly refuses silent audio,
   uncited deck identity, and WebKit/system media as Now Playing. Clear the
   WebKit source or make Rekordbox publish the active title before treating deck
   attribution as proven.
6. Ear-pass the packaged EQ exemplar loops. If they feel thin or synthetic,
   replace them with stronger licensed/self-authored examples and update the
   manifest/hash tests. Approval must be generated after listening with
   `uv run python scripts/audition_learn_exemplars.py --approve-ear-pass
   --approved-by <name> --audition
   /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json
   --approval-out
   /tmp/vibemix-live-learn-proof/learn-exemplar-ear-pass-current.json`; stale
   approvals without the current `bank_fingerprint`, or approvals attempted
   before a matching audition artifact exists, will not release.
7. Re-run the focused Learn Python, Learn UI, e2e, and build gates above. The
   Python quality gate must include `learn_model_router_guard`,
   `learn_all_lessons_runtime_pytest`, `learn_adaptive_coaching_pytest`, and
   `learn_auto_master_finder_pytest`, `learn_course3_mix_anchor_pytest`, and
   `learn_course_pack_pytest`;
   the frontend/desktop quality gates must include `learn_tauri_window_vitest`,
   `learn_browser_booth_playwright`, and `learn_cargo_learn_window_test`.
   Stale artifacts without those commands should be treated as not proven.
8. When adding a new course, start from
   `sections.curriculum.course_pack_contract` in
   `/tmp/vibemix-live-learn-proof/learn-package-verification-current.json`.
   Preflight the draft with either
   `uv run python scripts/validate_learn_course_pack.py <course-pack.json>` or
   `vibemix.learn.course_pack.validate_course_pack_draft(...)`, then add Python
   curriculum metadata, declare the course's `frontstage_mode` and
   `capabilities`, add transcript fixtures, run codegen, then run the contract
   commands it lists. If the compiled flow uses a backstage lens or input
   surface that the course did not declare, the audit should fail.
   The current verifier also records
   `sections.curriculum.flow_contract_summary` and
   `sections.curriculum.transcript_inventory`: all 36 beginner flows are
   structurally valid (`total_steps=76`, `min_hint_count=3`,
   `observable_control_count=18`) and every transcript fixture is claimed by
   exactly one `LessonMeta` row (`fixture_count=37`, no duplicates, no missing
   paths, no orphans). It also records
   `sections.curriculum.flow_contract_summary.prompt_contract`; all governed
   beginner frontstage prompts stay under the current caps (`max_chars=150`,
   `max_words=24`, `max_sentences=2`, one line, no inline list shape), with the
   only exempt step being the tone-locked opening dialog line
   `L1.01.beat.3`. Future course packs also emit `validation.prompt_contract`
   and step-level `prompt_metrics`, so reject draft lessons that try to sneak
   a syllabus wall into a practice prompt.
   It also records
   `sections.curriculum.copy_truthfulness_contract`; new courses must not claim
   automatic debrief/profile/session actions that the Learn runtime and
   frontend do not actually perform. New courses must clear those same checks.

## Cautions for the next session

- The worktree is very dirty and includes unrelated user or parallel-agent
  changes. Do not revert broad files.
- FLX4 hardware learning from the live desk: the DDJ-FLX4 is visible via
  `uv run python scripts/sniff_controller.py --list`, and the raw MIDI callback
  path is decisively good. A direct 18 s sniff while the user rotated the left
  jog captured 5,276 frames with `unique_cc=[0, 32, 33, 34]` and
  `unique_notes=[54]`; left-jog CC `33` / `0x21` appeared repeatedly with
  non-neutral values including `62`, `63`, `65`, and `66`. The controller,
  physical motion, and FLX4 JSON mapping are therefore not the current suspect.
- Physical readiness verifier learning: standalone readiness files now feed the
  package verifier through `--physical-readiness` or auto-discovery of
  `learn-physical-readiness-current.json`. The verifier records
  `readiness_status` on the physical live-proof section, but deliberately does
  not downgrade an already-passed physical proof. Use that field for the latest
  DDJ/USB/audio doctor, and use the strict proof artifact for pass/fail.
- Course 3 route-doctor learning: `learn_live_readiness.py` now matches
  Rekordbox's saved `Aggregate Device` route to the CoreAudio capture row named
  `rekordbox Aggregate Device`. Earlier live readiness correctly reported
  `diagnosis_code=rekordbox_saved_route_capture_rate_mismatch`, `status=fix_rate`,
  and the exact first move as the 44100Hz to 48000Hz route fix. Do not collapse
  that class back to generic "route to BlackHole" advice; when it appears, the
  generic route, playback, and Now Playing steps remain secondary.
- Course 3 spoken-prompt learning: `run_learn_live_proof.py
  --say-course3-prompts` now speaks the route doctor's exact next step when a
  readiness artifact contains one, then falls back to the audio diagnosis, then
  the legacy generic prompt. In the earlier fix-rate state the spoken prompt was
  the Aggregate Device 44100Hz-to-48000Hz fix; after the rate fix, the current
  spoken prompt should come from the `start_playback` route doctor. Failed
  Course 3 proof artifacts record `prompt_source`, `diagnosis_code`, `route`,
  and `operator_steps` in the `course3_operator_prompt` stage; use those fields
  when reviewing what the operator actually heard.
- Course 3 rate-fix operator-action learning: the readiness diagnosis now
  carries structured route fields for sample-rate problems. In the earlier
  rate-fix artifact, `current_rekordbox_route=Aggregate Device @ 48000Hz`,
  `current_capture_route=rekordbox Aggregate Device @ 44100Hz`, and
  `route=rekordbox Aggregate Device @ 48000Hz`. The Learn booth compact label
  for this class is `set aggregate route to 48k`; do not regress it to generic
  playback copy such as `play Rekordbox from deck`.
- Course 3 post-rate-fix learning: after the user changed the aggregate route
  to 48k, readiness left `fix_rate` and now reports `start_playback`. The
  current live state is not a port conflict: `127.0.0.1:8765` is owned by
  `/Users/ozai/projects/dj-set-ai/.venv/bin/python3 -m vibemix` and websocket
  handshake succeeds. The remaining external action is real master audio and
  citable Rekordbox metadata: stop unrelated WebKit media, load/play a real
  Rekordbox library track, raise the channel fader/crossfader/trim/master until
  capture has signal, then rerun Course 3 proof. The route doctor now keeps
  structured operator-action steps before generic blocker steps in this state.
- Perfection package artifact learning: `learn-perfection-package-current.json`
  now persists `release_blocker_recipe_ids` beside `release_blocker_recipe`.
  The current IDs are `packaged_eq_exemplar_ear_pass` and
  `course3_live_audio_play_mode`; integration tooling no longer needs to
  recompute them from recipe rows.
- Latest package-quality learning: a fresh run of
  `uv run python scripts/run_learn_perfection_package.py --out
  /tmp/vibemix-live-learn-proof/learn-perfection-package-current.json` passed
  `python_quality`, `frontend_quality`, `desktop_quality`, and
  `package_verifier`. The saved package artifact has `passed=true`,
  `verification_summary.technical_passed=true`, `release_ready=false`, matrix
  `20/22`, objective audit `7/9`, and exactly two blocker IDs:
  `packaged_eq_exemplar_ear_pass` and `course3_live_audio_play_mode`.
- Objective-audit learning: `scripts/verify_learn_package.py` now emits
  `objective_audit`, which maps the original Learn goal into nine concrete
  objective groups. The current package proves seven groups and blocks exactly
  two: `course3_live_play_mode` and `audible_example_quality`. This is the
  fastest current way to tell what part of the broad goal remains unproven
  without reading every completion-matrix row.
- Future-course integration-plan learning: `validate_course_pack_draft(...)`
  now emits `integration_plan` with `merge_ready`, exact target files,
  `COURSE_REGISTRY`/`COURSE_FRAMES`/`CURRICULUM` edit rows, transcript paths,
  progress-field edits for new locked courses, and post-merge commands. The
  curriculum audit and package verifier require that field in
  `future_course_extension_contract`, and the latest package refresh proves it.
  A CLI smoke at `/tmp/vibemix-live-learn-proof/course-pack-integration-plan-smoke.json`
  wrote a two-lesson `course_4_integration_plan_lab` starter pack with
  `validation.integration_plan.merge_ready=true`.
- Lesson-choice/replay learning: the map stays opt-in, but locked visible
  lessons are no longer a dead click. `renderProgressList(...)` exposes
  `onLockedLesson`, and `learn-window.ts` uses it to pulse the existing
  `lock_reason` in the booth without emitting `ipc.learn.start_lesson`.
  Completed locked-course lessons remain replayable with `level="replay"`.
  Latest frontend quality and full package refresh both passed.
- One-clear-prompt contract learning: `frontstage_prompt_metrics(...)` is now
  the shared guardrail for calm practice prompts. The shipped curriculum audit
  records a passing prompt contract with governed observed maxima
  `115 chars / 23 words / 2 sentences`, and future course-pack validation
  rejects prompts over `150 chars`, over `24 words`, over `2 sentences`,
  multiline prompts, and inline bullet/numbered-list shapes. Do not remove the
  `L1.01.beat.3` exemption unless Kaan explicitly ratifies changing the
  verbatim-locked opening dialog and the byte-equality tests are updated in the
  same change.
- The strict live app-bus proof is cleared. The final run loaded L1.07,
  observed the left jog through the live socket as `jog:A=127`, sent the ACK,
  and saw lesson advance. Treat the DDJ-FLX4 controller, CoreMIDI path,
  controller profile, sidecar listener, and Learn ACK bridge as proven for this
  hardware slice.
- If the physical row ever has to be re-proven, use the strict app proof rather
  than another raw mapping exercise:
  `uv run python scripts/run_learn_live_proof.py --start-app --start-timeout 90
  --no-screen --physical --wait-physical-seconds 20 --physical-seconds 90
  --say-physical-prompts --auto-master-input --out
  /tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json`.
  Start it only when the user is ready to keep rotating the left jog after the
  probe says L1.07 is loaded.
- Operator-audio learning: whenever a proof waits for a human to move physical
  hardware, make the Mac speak the moment with `say(1)` when available. The
  operator is usually looking at the deck, not the terminal. Keep it opt-in and
  fail-soft for CI/unattended runs; the current flag is
  `--say-physical-prompts`, which records `operator_prompt_spoken=true` in the
  proof artifact.
- Do not mark the persistent Learn goal complete until live audio evidence and
  the package verifier prove the remaining product promise.
- Do not replace the calm practice-booth surface with a visible 36-row syllabus.
  The map stays opt-in. The default experience is one prompt, one action, one
  grounded response.
- Do not invent Course 3 audio or phrase claims. Keep proactive calls gated on
  live audio, deck confidence, Rekordbox track/playhead evidence, and authored
  cue/section anchors.
- Do not hardcode model names. Tutor routing stays through
  `vibemix.llm.model_router`.
