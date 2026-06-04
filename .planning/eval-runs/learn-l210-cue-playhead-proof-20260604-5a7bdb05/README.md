# L2.10 Cue Placement Playhead Proof

Date: 2026-06-04
HEAD: `5a7bdb05`
Source note: captured from `5a7bdb05` plus the Learn runtime/test diff committed with this artifact.
Sidecar: `VIBEMIX_DEV_SIDECAR=1`, throwaway progress `/tmp/vibemix-learn-l210-proof-progress.json` with `course_2_unlocked=true`.

## Result

- L2.10 loaded: `True`
- Waveform frames: `1`
- Playhead ticks: `59`
- Hot-cue ack sent: `True`
- Cue-grade tutor speaks after press: `1`
- Cue-grade tutor speaks before press: `0`

The press was gated by live deck B `playhead_tick` data, targeting `7.500s` / `330750.0` frames. The outbound ack is the existing `ipc.learn.ack` envelope with `control_id=hotcue:B`.

## Trigger Tick

```json
{
  "recv_monotonic": 26408.147765333,
  "b_position_s": 7.486156462585034,
  "b_frame": 330139.5,
  "target_s": 7.5,
  "target_frame": 330750.0,
  "error_s_at_tick": -0.013843537414966356,
  "error_frames_at_tick": -610.5
}
```

## Voice Evidence

```json
[
  {
    "monotonic": 26408.283407083,
    "type": "ipc.learn.tutor_speak",
    "ts": "2026-06-04T11:34:53.190785+00:00",
    "payload": {
      "text": "nice - that hot cue landed on the drop.",
      "tts_marker": "L2.10.cue_grade",
      "citations": [
        "[ev:CUE_PLACEMENT_GRADED@65.840]"
      ],
      "data_state": "hint"
    }
  }
]
```

Raw bus capture: `l210_cue_playhead_bus.json`.

Session events excerpt: `l210_events_excerpt.json` from `/Users/ozai/Library/Application Support/vibemix/recordings/20260604-143346/events.jsonl` (7 relevant rows).
