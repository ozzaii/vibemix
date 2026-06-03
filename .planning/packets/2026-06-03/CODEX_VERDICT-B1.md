# CODEX VERDICT - B1 audible practice decks

Item: B1 - audible two-deck beatmatch practice decks.

SHA: `59a7fcb3` (`feat(learn): wire beatmatch practice audio`)

User value: a Pro Learn user on the beatmatch lesson path now has the owned two-deck
practice player wired into the real lesson runtime, using the same MiniDeck that the
grader snapshots and the same Learn headphone output setting as exemplar audio.

What shipped:
- `LessonRuntime.set_beatmatch_practice_player()` installs a lesson-scoped player.
- L2.01/L2.02 start the player only while the lesson is armed.
- The player stops on new lesson load, advancement, completion, replacement, and app
  shutdown.
- Live boot creates `TwoDeckPlayer(output_device, beatmatch_practice_driver.deck, state=state)`
  after resolving the Learn output device.
- Explicit macOS `Multi-Output Device` selections are honored for the AI voice path,
  while stale/default BlackHole and capture aggregates remain rejected.
- Boot logging now prints the actual resolved output device name instead of the
  fallback constant.

By-eye / runtime artifact:
- Fresh source boot with `VIBEMIX_DEV_SIDECAR=1 uv run python -m vibemix` printed:
  `-> AI voice -> Multi-Output Device @ 24000Hz`
  and
  `-> djay passthrough -> Multi-Output Device @ 48000Hz`.
- Tauri dev shell was launched with `VIBEMIX_E2E_EXTERNAL_SIDECAR=1 cargo tauri dev --no-watch`;
  the UI reconnected to the source bus after sidecar restart.
- `ui.log` showed `pill: connection connected`, `rust bridge ws-state {"state":"connected"}`,
  settings state with `output_device_id:"12"` and `learn.headphone_device_index:12`.
- `ws_probe.py --watch ipc.session.snapshot --seconds 3` saw 28 grounded
  `cohost=LISTENING` snapshots from the real bus.
- Sven was muted after verification via `ipc.session.mute {"toggle": true}`; ack returned
  `{"muted": true}` and mascot voice meter decayed to `0.0`.

By-ear caveat:
- The exact B1 kill-criterion "hear two kicks drift then lock" was not driven in this
  pass because the live rig was actively playing and `TwoDeckPlayer.can_play()` must
  refuse practice audio when a live set is active. This is KEEP behavior, not a
  bypassable test condition.
- The remaining B1 proof is to run L2.01/L2.02 with no active live set, hear the
  practice decks, and then continue the fused Q3/B1/B2/B3/Q6 by-ear gate.

Grounding:
- No new co-host utterance text or speak trigger was introduced. The change wires
  lesson audio lifecycle and output routing only, so `vibemix-grounding-review` was
  not required for this slice.

Verification:
- PASS: `uv run pytest -q tests/audio/test_device_select.py tests/learn/test_beatmatch_practice_audio_lifecycle.py tests/learn/test_two_deck_player.py tests/learn/test_beatmatch_practice_driver.py tests/learn/test_observer_boot_wiring.py tests/learn/test_runtime_evidence_grounding.py tests/learn/test_runtime_invariants.py tests/learn/test_no_new_ws_port.py tests/learn/test_course3_no_exemplar_during_live.py` (74 tests).
- PASS: `uv run ruff check src/vibemix/audio/device_select.py tests/audio/test_device_select.py src/vibemix/learn/runtime.py src/vibemix/__main__.py tests/learn/test_beatmatch_practice_audio_lifecycle.py tests/learn/test_observer_boot_wiring.py`.
- PASS: `git diff --check`.
