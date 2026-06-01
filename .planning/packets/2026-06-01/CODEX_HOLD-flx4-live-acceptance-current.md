# CODEX_HOLD: FLX4 Live Acceptance Current Attempt

Date: 2026-06-01
Verifier: Codex
Related lanes:

- Package 1D - FLX4 Live Context Release Gate
- Hold Lane - FLX4 Live Context Proof Artifacts
- Hold Lane - Cohost/Viber Eval Run Archives

Decision: HOLD final live acceptance. The latest signed package boots and serves
live context, and the DDJ-FLX4 is visible, but the required physical proof legs
were not captured.

## Artifact Under Test

Latest signed/notarized DMG:

```text
dist/fresh-20260601-latest/vibemix-0.0.1.dmg
119957189 bytes
mtime 2026-06-01 08:32:00 +0300
sha256 a5b56658595bbdae11e5558cdac35f266244192c5b37a51ff6361587e4566b29
```

Copied-DMG app launched for the proof:

```text
/tmp/vibemix-signed-install.Tp4lk7/vibemix.app
app PID 57519 -> bundled sidecar PID 57523
sidecar listener: TCP 127.0.0.1:8765
```

The app was quit after the proof and left no sidecar/listener behind.

## Command

First pass:

```text
COHOST_VIBER_FLX4_OUT_DIR=.planning/eval-runs/flx4-live-context-codex-latest-signed COHOST_VIBER_FLX4_WAIT_READY_S=5 COHOST_VIBER_FLX4_TIMEOUT_S=3 COHOST_VIBER_FLX4_FRAMES=180 bash scripts/release/check_flx4_live_context.sh
```

Second pass with direct OS MIDI motion probe:

```text
COHOST_VIBER_FLX4_OUT_DIR=.planning/eval-runs/flx4-live-context-codex-latest-signed COHOST_VIBER_FLX4_WAIT_READY_S=5 COHOST_VIBER_FLX4_TIMEOUT_S=3 COHOST_VIBER_FLX4_FRAMES=180 COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S=3 bash scripts/release/check_flx4_live_context.sh
```

Result:

```text
FAIL check_flx4_live_context: midi_port=DDJ-FLX4 audio_device=True live_ok=True live_ready=False diagnosis=missing_physical_proof frames=115 controller_connected=True recent_moves=False audio_observed=False blockers=20 direct_midi=False direct_midi_frames=0 midi_motion_diag=no_direct_midi_motion_observed listener_read_canary=skipped audio_causality_rejected=skipped audio_source_detail_rejected=skipped action_hint=play_audible_deck_audio_and_move_a_fader_or_knob_within_the_proof_window first_blocker='direct OS MIDI probe saw no controller frames during the probe window' next_action='Collect the missing live proof legs shown in blockers, then rerun `vibemix library live-context --require-proof`.' proof=.planning/eval-runs/flx4-live-context-codex-latest-signed/live_context_proof.json
```

## What Passed

- `DDJ-FLX4` appears in MIDI enumeration.
- `DDJ-FLX4` appears as an audio device.
- The copied signed-DMG app served websocket frames on `127.0.0.1:8765`.
- Live context schema v2 and required capabilities were present.
- `deck_mixer.connected=true`.
- Library cache was visible with `library_tracks=1547`.
- The proof produced bounded artifacts under:
  `.planning/eval-runs/flx4-live-context-codex-latest-signed/`.

## What Blocked Acceptance

From
`.planning/eval-runs/flx4-live-context-codex-latest-signed/flx4_live_context_summary.json`:

```text
ok=false
live_ok=true
live_ready=false
diagnosis=missing_physical_proof
controller_connected=true
recent_moves_seen=false
audio_observed=false
deck_state_resolved=false
deck_state_pair_resolved=false
deck_pair_capture_configured=false
deck_audio_capture_both_active=false
direct_midi_probe.ran=true
direct_midi_probe.motion_observed=false
direct_midi_probe.frames=0
proof_legs_passed=3
proof_legs_total=8
```

Top blockers:

```text
direct OS MIDI probe saw no controller frames during the probe window
no recent controller moves were observed
live master audio was not observed above the audible floor
deck_state had no resolved deck row
deck identity source: no deck Now Playing title was observed
screen vision is not currently resolving the independent second deck
deck_state had no citable track_id at confidence floor
deck_state did not resolve both deck A and deck B
```

## Classification

HOLD:

- Final live acceptance cannot be claimed from this attempt.
- The failure is not a packaged-app boot/signing failure. It is a missing
  physical proof failure: no FLX4 motion frames and no audible deck audio crossed
  the proof window.
- Listener-read and anti-causality canaries were skipped because the prerequisite
  live proof was not ready.

## Promotion Gate

To promote this lane, rerun the same script while:

1. A deck is audibly playing through the configured capture route.
2. A FLX4 fader, EQ, filter, transport, or jog control is moved during the probe
   window.
3. Track/deck identity is resolvable enough to cite rather than guess.
4. The summary reports `ok=true`, `live_ready=true`, `recent_moves_seen=true`,
   `audio_observed=true`, and listener/causality canaries pass.

Then update this packet or replace it with a `CODEX_READY-*` live acceptance
packet.

---

## Current-source controller-weighted proof update

Later current-source proof was run against the dirty controller-weighted deck
audio lane, not the signed DMG above. The app was launched from source with
`VIBEMIX_INPUT_DEVICE='BlackHole 16ch'`,
`VIBEMIX_DECK_AUDIO_CHANNELS='A=0,1;B=2,3'`, and `VIBEMIX_LOCAL_TTS=0` so no
cloud or MOSS voice could mask the evidence. Live session id:
`20260601-171701`.

Best combined run:

```text
COHOST_VIBER_FLX4_OUT_DIR=.planning/eval-runs/flx4-live-context-controller-weighted-current-8 \
COHOST_VIBER_FLX4_WAIT_READY_S=1 \
COHOST_VIBER_FLX4_TIMEOUT_S=6 \
COHOST_VIBER_FLX4_FRAMES=360 \
COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S=30 \
COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_MODE=callback \
bash scripts/release/check_flx4_live_context.sh
```

Result:

```text
FAIL check_flx4_live_context: midi_port=DDJ-FLX4 audio_device=True live_ok=True live_ready=False diagnosis=missing_physical_proof frames=253 controller_connected=True recent_moves=True audio_observed=True blockers=9 direct_midi=True direct_midi_frames=358 midi_motion_diag=direct_midi_motion_observed listener_read_canary=skipped audio_causality_rejected=skipped audio_source_detail_rejected=skipped action_hint=collect_remaining_blockers first_blocker='deck_state had no resolved deck row' next_action='Collect the missing live proof legs shown in blockers, then rerun `vibemix library live-context --require-proof`.' proof=.planning/eval-runs/flx4-live-context-controller-weighted-current-8/live_context_proof.json
```

This is materially stronger than the signed-DMG attempt:

```text
live_socket_frames=pass
live_context_schema=pass
controller_connected=pass
recent_controller_move=pass
audible_audio=pass
direct_midi_probe.motion_observed=true
direct_midi_probe.frames=358
```

But final acceptance still stays **HOLD** because the remaining proof legs are
the important anti-slop legs, not operator timing:

```text
deck_state_resolved=false
deck_state_pair_resolved=false
deck_audio_capture_both_active=false
```

Top current blockers:

```text
deck_state had no resolved deck row
deck identity source: Now Playing is owned by a non-DJ app
screen vision is not currently resolving the independent second deck
deck_state had no citable track_id at confidence floor
deck_state did not resolve both deck A and deck B
deck_audio_capture did not show active audio on both deck lanes
```

Evidence details from the best frame:

```text
deck_source_status.nowplaying_owner=com.apple.webkit.gpu
deck_source_status.resolution=no_single_attributable_deck
deck_source_status.screen_vision=disabled
deck_audio_separation_context=... mode=deck_pair_capture_configured ... deck_audio_activity=A_active+B_silent
live_evidence=midi:A_jog_nudge_back + mix:deck_audio_capture=A_active+B_silent
```

Interpretation:

- The FLX4 control feed is proven live. A standalone callback sniff in the same
  session captured 3,579 frames in 10s, and the combined proof captured 358
  direct MIDI frames while the app also saw a recent move.
- The BlackHole 16ch deck-pair route is configured, but this Rekordbox/Multi
  Output setup is not feeding active audio to both declared deck lanes. The
  guard is correctly refusing to treat configured capture as separated-deck
  proof.
- Deck identity is still not citable. Rekordbox is not publishing trustworthy
  Now Playing ownership; `nowplaying-cli` reports a WebKit GPU owner, and the
  screen-vision leg is deliberately disabled/dormant. The app must keep saying
  "unknown deck" until a real identity source lands.

Promotion gate remains:

1. Prove both deck lanes active as `deck_audio_capture=A_active+B_active` on the
   configured route, or explicitly downgrade the package claim to single-lane
   controller-weighted master context.
2. Land a real independent deck-identity source (for example a verified
   screen-vision path or a Rekordbox live source) before allowing citable Deck
   A/B track claims.
3. Rerun `check_flx4_live_context.sh` and require `ok=true`, `live_ready=true`,
   recent moves, audible audio, deck identity, both-lane audio, and canaries.
