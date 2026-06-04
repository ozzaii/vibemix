# Learn Course-1 HEAD Bus Proof - 2026-06-04

Latest source head when consolidated: `7cdc4b7a442cac5468b4e1eb9856f10f4467e595`. Current head when staged: `6a43240cf6e10502468f040c4497384e5e268abf`. No Learn/audio files changed from the first capture through that staged head.

Raw captures:

- `course1_part_a_bus.json` - L1.03 EQ-audible bus leg and L1.14 EQ-as-tutor exemplar leg.
- `l113_waveform_bus.json` - L1.13 waveform/playhead/breakdown leg.
- `l201_grade_auto_advance_bus.json` - L2.01 cited grade-to-advance leg.
- `summary.json` - aggregate checks.

The captures span short fresh sidecar runs because the L1.14 observer path played all three exemplar bands but did not complete cleanly when driven at automation speed. The proof condition for L1.14 here is EQ-audible bus evidence: three real `ipc.learn.exemplar_play` envelopes plus band tutor lines. `git diff --name-only ff5015e5..7cdc4b7a` shows no Learn/audio files changed between the first and latest capture.

## Result

Passed: `True`

Checks:

- L1.03 EQ-audio bus: `True`
- L1.14 three EQ exemplars: `True`
- L1.13 waveform with breakdown cue: `True`
- L2.01 cited grade auto-advance: `True`
- Learn/audio unchanged between captures: `True`
- Learn/audio unchanged through staged head: `True`

## Evidence Excerpts

### L1.03 Channel Strip

- Tutor markers: `['L103.beat0', 'L103.beat1']`
- Waveform decks: `['A', 'B']`
- Playhead ticks: `6`
- Advance: `{'lesson_id': 'L1.03', 'reason': 'action_matched'}`
- Complete: `{'lesson_id': 'L1.03', 'reason': 'completed'}`

### L1.14 EQ As Tutor

- Exemplar track ids: `['_packaged:low:vibemix_internal_low_bass_gate', '_packaged:mid:vibemix_internal_mid_chord_body', '_packaged:high:vibemix_internal_high_hat_air']`
- Tutor markers: `['L114.beat0', 'L114.beat1', 'L114.beat2', 'L114.band_low', 'L114.band_mid', 'L114.band_high']`
- Observer advance count before high band: `2`

### L1.13 Spot Breakdown By Eye

- Tutor markers: `['L113.beat0', 'L113.beat1']`
- Waveform decks: `['A', 'B']`
- Cue labels A: `['intro', 'drop', 'breakdown', 'outro']`
- Playhead ticks: `6`
- Advance count: `2`
- Complete: `{'lesson_id': 'L1.13', 'reason': 'completed'}`

### L2.01 Grade To Advance

- Locked grade: `{'citation': '[ev:BEATMATCH_GRADED@36.069]', 'phase_error_beats': 0.0007256235827663993, 'score': 0.9964, 'verdict': 'locked'}`
- Grade voice: `{'citations': ['[ev:BEATMATCH_GRADED@36.069]'], 'data_state': 'hint', 'text': "nice — that's matched.", 'tts_marker': 'L2.01.grade'}`
- Advance: `{'lesson_id': 'L2.01', 'reason': 'action_matched'}`
- Complete: `{'lesson_id': 'L2.01', 'reason': 'completed'}`
- Next lesson loaded: `{'controller_id': 'pioneer_ddj_flx4', 'course_id': 'course_2_transitions', 'lesson_id': 'L2.02', 'progress_dots': [{'lesson_id': 'L2.01', 'status': 'completed'}, {'lesson_id': 'L2.02', 'status': 'current'}, {'lesson_id': 'L2.03', 'status': 'pending'}, {'lesson_id': 'L2.04', 'status': 'pending'}, {'lesson_id': 'L2.05', 'status': 'pending'}, {'lesson_id': 'L2.06', 'status': 'pending'}, {'lesson_id': 'L2.07', 'status': 'pending'}, {'lesson_id': 'L2.08', 'status': 'pending'}, {'lesson_id': 'L2.09', 'status': 'pending'}, {'lesson_id': 'L2.10', 'status': 'pending'}, {'lesson_id': 'L2.11', 'status': 'pending'}, {'lesson_id': 'L2.12', 'status': 'pending'}, {'lesson_id': 'L2.13', 'status': 'pending'}, {'lesson_id': 'L2.14', 'status': 'pending'}], 'title': 'beatmatching with sync'}`

## Launch Notes

Each run launched a clean tracked-source snapshot with `VIBEMIX_DEV_SIDECAR=1` and a throwaway `VIBEMIX_LEARN_PROGRESS_PATH`. The throwaway progress file set `course_2_unlocked=true` so L2.01 could start through the normal Learn IPC gate. Launch logs routed `djay passthrough` and `AI voice` to MacBook Pro Speakers.

This is by-bus proof. It records the live websocket envelopes that prove the player, waveform, tutor, grade, completion, and auto-advance paths fired; it does not claim human ear confirmation.
