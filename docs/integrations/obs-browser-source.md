# OBS Studio — vibemix mascot browser-source integration

Pipe vibemix's VTuber-style mascot directly into an OBS Studio scene as a transparent overlay. The mascot reacts to your audio cues in real time and renders inside OBS without any extra runtime hops.

> **Status:** Production. Lands in v3.1 per ADR `.planning/decisions/DEP-OPP-01-obs-browser-source.md`.

## What you get

- A live mascot canvas composited on top of your camera or screen capture.
- Alpha-channel support — the mascot's background is transparent.
- Real-time reactions driven by the same mascot bus the standalone app uses.

## Prerequisites

- vibemix installed per the README quick-start.
- OBS Studio 28 or newer (the browser-source plugin is built in).
- vibemix and OBS running on the same machine.

## Setup steps

1. **Launch vibemix.** Start a live session as usual. The mascot surface starts serving once the app is running.

2. **Note the mascot route.** vibemix exposes the mascot canvas at `http://127.0.0.1:8765/mascot` (the local mascot bus + webview route). Both vibemix and OBS must run on the same host.

3. **Add a Browser source in OBS.**
   - In OBS, click `+` under Sources and pick `Browser`.
   - Name the source (e.g. `vibemix mascot`).
   - URL: `http://127.0.0.1:8765/mascot`
   - Width: 1280, Height: 720 (these match the mascot canvas aspect; adjust to fit your scene)
   - Check `Refresh browser when scene becomes active`.

4. **Set a transparent background.** Under the Browser source properties, the mascot canvas is alpha-aware — leave the default CSS field empty. If you see a black background, tick `Use custom CSS` and clear any imported defaults.

5. **Resize and position.** Drag the source in the OBS canvas to your preferred corner (lower-right is a common streamer choice). The mascot scales without aliasing.

6. **Confirm it reacts.** Start playing audio into vibemix. The mascot in OBS should respond to track changes, phase shifts, and mix moves at the same cadence as the standalone vibemix surface.

## Troubleshooting

| Symptom | Fix |
|---|---|
| OBS shows a blank source. | Check vibemix is running; the mascot route only serves while the app is live. |
| The background is opaque black. | Set the Browser source's custom CSS field to empty; OBS sometimes injects a default body background. |
| The mascot is frozen. | The mascot bus may have stopped emitting — restart vibemix. Reactions resume on the next event. |
| Aspect ratio looks squashed. | Match the OBS Browser source resolution to the mascot canvas aspect (16:9 by default). |
| Frame rate drops in OBS. | Reduce the Browser source FPS cap to 30 in OBS source properties — the mascot does not need 60 fps inside a scene composite. |

## Privacy + network notes

- The mascot WS bus binds to `127.0.0.1` only. The OBS integration does NOT expose vibemix to the network.
- OBS Studio must run on the same machine as vibemix. Remote-host setups would require firewall rules vibemix does not configure on your behalf.
- No audio is sent to OBS via this integration — the Browser source captures the visual canvas only. Audio routing remains your existing BlackHole / VB-CABLE chain.

## Limitations

- This integration is canvas-only. There is no two-way control (OBS scene change does not toggle vibemix state, and vice versa).
- Multi-monitor screen captures inside OBS may conflict with the mascot's compositing on macOS Sonoma+; if you see flicker, isolate the mascot to a dedicated OBS scene.
- If you run an extreme multi-PC setup with OBS on a separate capture box, you need a different integration (NDI, Spout) that vibemix does not ship.

## References

- ADR: `.planning/decisions/DEP-OPP-01-obs-browser-source.md`
- Scan row: `docs/dep-opportunities/2026-05-scan.md` § DEP-OPP-01
- Memory: `project_mascot_as_vtuber_personality_surface`
