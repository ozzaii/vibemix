<!--
SPDX-License-Identifier: Apache-2.0
Phase 43 / VIS-09 — Demo-mode configuration spec for the hero-demo capture day.
-->

# vibemix hero demo — Demo-mode config

**Phase 43 / VIS-09.** `vibemix.demo_mode` replaces the live audio + MIDI input pipeline with a deterministic 30-event sequence so capture-day takes are bit-identically repeatable.

## Purpose

The mascot reacts, the AI lines fire, the EvidenceRegistry chips render — all at the same timestamps every take. Same kick swap at 2:33 every time. Same layer drop at 4:50 every time. Same track end at 6:00 every time. Francesco shoots take after take until the visual reads right; the audio + AI behaviour is locked.

This is also the deterministic surface against which the **anti-hallucination grounding gate** (vibemix's `Hallucination grounding` constraint in CLAUDE.md) can be smoke-tested before shoot day.

## CLI

```bash
# Reset the sequence cursor to step 0 (call between takes)
vibemix --demo-mode reset

# Start vibemix with demo-mode active — replaces live input with DEMO_SEQUENCE
vibemix --demo-mode start

# Stop demo-mode (return to live input)
vibemix --demo-mode stop
```

Alternative env-var form (CI / scripted runs):

```bash
VIBEMIX_DEMO_MODE=1 vibemix
```

## Deterministic 30-event sequence

Defined in [`src/vibemix/runtime/demo_mode.py`](../../src/vibemix/runtime/demo_mode.py) as the module constant `DEMO_SEQUENCE`. Total runtime 0:00 → 6:00 (360s).

### Anchor events (load-bearing — pinned by pytest)

| Time | Event | Mascot reaction | Storyboard cut |
|------|-------|-----------------|----------------|
| 0:00 | `track_start` (Track A) | mascot enters idle pose | Cut 1, 2 |
| 2:33 (153.0s) | **`kick_swap`** | mascot celebrate trigger (Hype-man) | Cut 5 caption + Cut 7 animation |
| 4:50 (290.0s) | **`layer_drop`** | mascot teacher line trigger (Teacher mood) | Cut 7 mid-track moment |
| 6:00 (360.0s) | `track_end` (Track A) | mascot fade to idle | Cut 8 transition |

These four anchors are enforced by `tests/runtime/test_demo_mode_sequence.py`. Any reorder fails CI.

### Filler events (texture)

26 filler events distributed across the gaps — 8 pre-kick-swap, 9 post-kick-swap, 9 post-layer-drop. Event kinds:

| Kind | Purpose |
|------|---------|
| `controller_move` | MIDI knob/fader/cue activity (filter sweeps, EQ shifts, fader rides) |
| `bpm_shift` | BPM nudge / transition between tracks |
| `mood_tick` | Persona heartbeat (Hype-man / Teacher / Coach mood pulse) |

Filler timestamps are **not** pinned (they're texture, not anchors). Filler order is monotonic but exact times can be tuned without breaking the demo.

## Public API surface

```python
from vibemix.runtime.demo_mode import (
    DEMO_SEQUENCE,   # frozen tuple[DemoEvent, ...] of length 30
    DemoEvent,       # @dataclass(frozen=True): timestamp_s, kind, payload
    DemoState,       # cursor state (step_index)
    load_sequence,   # reset + return DemoState
    step,            # return current event + advance; None when exhausted
    reset,           # cursor back to step 0
)
```

## Take repeatability workflow

Because the sequence is deterministic and the demo-mode resets cleanly:

1. Run take 1; review playback.
2. `vibemix --demo-mode reset` → cursor back to step 0.
3. Run take 2 with identical timing; pick the better visual.
4. Repeat until cut 7 (mascot Hype-man celebrate) feels like a Pioneer-CDJ headbob — not a VTuber dance. Kaan's judgment, not Francesco's, on the aesthetic gate.

## AV spec

- **Video:** 1080p+ resolution, 60fps+ frame rate.
- **Audio:** 48kHz sample rate (matches vibemix's `session.wav` for bit-identical alignment).
- **Bit depth:** 24-bit WAV across all 3 capture tracks.

(Full spec table in [`AUDIO-CAPTURE.md`](./AUDIO-CAPTURE.md).)

## Threat model (Plan 43-09)

- **Tampering (T-43-09-01):** anchor timestamps locked by both module-level invariant asserts in `demo_mode.py` AND pytest pins. Any reorder fails import + fails CI.
- **DoS / accidental enablement (T-43-09-02):** module is inert until `load_sequence()` / `step()` is invoked. Default vibemix behaviour is live input. Demo-mode requires an explicit `--demo-mode` flag or `VIBEMIX_DEMO_MODE=1` env var.
- **Repudiation (T-43-09-04):** Francesco + Kaan dual sign-off block in `KAAN-ACTION-LEGAL.md §VIS-09`; AV-spec check via `ffprobe` post-shoot.

## Cross-references

- Sequencer source (the 30 events + invariant asserts): [`src/vibemix/runtime/demo_mode.py`](../../src/vibemix/runtime/demo_mode.py)
- Sequencer pytest pins: [`tests/runtime/test_demo_mode_sequence.py`](../../tests/runtime/test_demo_mode_sequence.py)
- Shot list (8 cuts): [`SHOT-LIST.md`](./SHOT-LIST.md)
- Audio capture plan (3-track + clapboard sync): [`AUDIO-CAPTURE.md`](./AUDIO-CAPTURE.md)
- Francesco discharge runbook: [`KAAN-ACTION-LEGAL.md §VIS-09`](../../KAAN-ACTION-LEGAL.md)
