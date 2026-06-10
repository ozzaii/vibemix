// SPDX-License-Identifier: Apache-2.0
// Wire-shape guard for the live 30Hz mascot frame.
//
// ws_bus.py's `mascot_frame` is a FLAT dict — it carries the Levels meter
// keys (music/voice/mic) plus readout fields, and NO `type` key. The
// emit-boundary guard (BRINGUP-04, ws_bus.py) refuses to send a frame
// missing any of the three meter keys, so their presence IS the frame's
// identity on the wire. The `type: "snapshot"` shape is kept for fixtures
// and the dev mock harness, which have always used the typed form.

export function isSnapshotFrame(
  message: unknown,
): message is Record<string, unknown> {
  if (!message || typeof message !== "object") return false;
  const m = message as Record<string, unknown>;
  if (m.type === "snapshot") return true;
  return (
    m.type === undefined &&
    typeof m.music === "number" &&
    typeof m.voice === "number" &&
    typeof m.mic === "number"
  );
}
