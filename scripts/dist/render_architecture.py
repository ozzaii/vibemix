# SPDX-License-Identifier: Apache-2.0
"""Deterministic vibemix architecture diagram generator.

Emits `docs/assets/architecture.svg` — a CDJ Whisper v5-styled SVG
diagram with 4 horizontal swim-lanes:

  1. User Hardware  — DJ Controller, Master output, Headphones
  2. vibemix Client — Python sidecar, Tauri UI, Local recording
  3. Network        — Bravoh proxy
  4. Gemini         — Gemini 3 Flash, Gemini TTS

Palette is hard-coded from `tauri/ui/src/tokens.css` (v5 CDJ Whisper
direction, 2026-05-12). Output is fully deterministic: same input dict
in -> same byte string out. No timestamps, no random IDs.

Usage::

    python scripts/dist/render_architecture.py
    python scripts/dist/render_architecture.py --output /tmp/out.svg
    python scripts/dist/render_architecture.py --check     # exit 1 on drift
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# === v5 CDJ Whisper palette (canonical: tauri/ui/src/tokens.css) =========

VOID_0 = "#000000"  # --void
VOID_1 = "#020205"  # --void-1
VOID_2 = "#05070b"  # --void-2
VOID_3 = "#0a0c12"  # --void-3
VOID_4 = "#11141c"  # --void-4

AMBER = "#ff8a3d"  # --amber
AMBER_DEEP = "#ff5a1a"  # --amber-deep
AMBER_PALE = "#ffb88a"  # --amber-pale
AMBER_22 = "rgba(255, 138, 61, 0.22)"
AMBER_40 = "rgba(255, 138, 61, 0.40)"
AMBER_65 = "rgba(255, 138, 61, 0.65)"

SILK = "#d6cfc7"  # --silk
SILK_65 = "rgba(214, 207, 199, 0.65)"
SILK_40 = "rgba(214, 207, 199, 0.40)"
SILK_22 = "rgba(214, 207, 199, 0.22)"
SILK_12 = "rgba(214, 207, 199, 0.12)"

GLASS_EDGE = "rgba(255, 255, 255, 0.065)"

# === Canvas geometry =====================================================

CANVAS_W = 1200
CANVAS_H = 720

LANE_LEFT_PAD = 24
LANE_RIGHT_PAD = 24
LANE_HEIGHT = 150
LANE_GAP = 22
LANE_LABEL_HEIGHT = 22

BOX_HEIGHT = 84
BOX_RADIUS = 8
BOX_TITLE_OFFSET = 36
BOX_SUBTITLE_OFFSET = 60

# === Diagram data (pure data — no rendering logic) ======================

SWIM_LANES: list[dict[str, Any]] = [
    {
        "id": "hw",
        "label": "User Hardware",
        "y": 40,
        "tint": VOID_1,
        "boxes": [
            {
                "id": "controller",
                "label": "DJ Controller",
                "subtitle": "DDJ-FLX4 - 10 mapped + generic fallback",
                "x": 80,
                "w": 240,
            },
            {
                "id": "master",
                "label": "Master output",
                "subtitle": "BlackHole 2ch (macOS) / WASAPI loopback (Win)",
                "x": 360,
                "w": 300,
            },
            {
                "id": "headphones",
                "label": "Headphones",
                "subtitle": "sounddevice OutputStream @ 24 kHz",
                "x": 700,
                "w": 260,
            },
        ],
    },
    {
        "id": "client",
        "label": "vibemix Client",
        "y": 212,
        "tint": VOID_2,
        "boxes": [
            {
                "id": "sidecar",
                "label": "Python sidecar",
                "subtitle": "MusicState - EventDetector - AICoach",
                "x": 60,
                "w": 280,
            },
            {
                "id": "ui",
                "label": "Tauri UI",
                "subtitle": "wizard - session - settings - mascot",
                "x": 380,
                "w": 280,
            },
            {
                "id": "recording",
                "label": "Local recording",
                "subtitle": "input.wav - voice.wav - events.jsonl",
                "x": 700,
                "w": 280,
            },
        ],
    },
    {
        "id": "network",
        "label": "Network",
        "y": 384,
        "tint": VOID_3,
        "boxes": [
            {
                "id": "proxy",
                "label": "Bravoh proxy",
                "subtitle": "api.altidus.world - JWT - 60 rpm / 2000 rpd",
                "x": 300,
                "w": 600,
            },
        ],
    },
    {
        "id": "gemini",
        "label": "Gemini",
        "y": 556,
        "tint": VOID_4,
        "glow": True,
        "boxes": [
            {
                "id": "flash",
                "label": "Gemini 3 Flash",
                "subtitle": "multimodal: audio + screen + evidence",
                "x": 160,
                "w": 360,
            },
            {
                "id": "tts",
                "label": "Gemini TTS",
                "subtitle": "streaming PCM chunks",
                "x": 580,
                "w": 360,
            },
        ],
    },
]

# Arrows — declarative, sorted at render-time for determinism.
ARROWS: list[dict[str, Any]] = [
    # Up-flow: controller -> sidecar (MIDI events)
    {"id": "a1", "from": "controller", "to": "sidecar", "label": "MIDI"},
    # Up-flow: master -> sidecar (audio capture)
    {"id": "a2", "from": "master", "to": "sidecar", "label": "audio 48 kHz"},
    # Down-flow: tts -> headphones (return-path PCM)
    {"id": "a3", "from": "tts", "to": "headphones", "label": "PCM 24 kHz"},
    # Out-flow: sidecar -> proxy (HTTPS)
    {"id": "a4", "from": "sidecar", "to": "proxy", "label": "HTTPS / JWT"},
    # Up-flow: proxy -> flash (forward)
    {"id": "a5", "from": "proxy", "to": "flash", "label": ""},
    # Cross-flow: flash -> tts (Gemini-internal handoff)
    {"id": "a6", "from": "flash", "to": "tts", "label": ""},
]


# === Box index ===========================================================


def _box_index(swim_lanes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Flatten boxes into {id: {x, y, w, h, lane_id}} for arrow routing."""
    index: dict[str, dict[str, Any]] = {}
    for lane in swim_lanes:
        lane_y = lane["y"]
        # Boxes are centered vertically inside the lane area below the label.
        box_top = lane_y + LANE_LABEL_HEIGHT + 10
        for box in lane["boxes"]:
            index[box["id"]] = {
                "x": box["x"],
                "y": box_top,
                "w": box["w"],
                "h": BOX_HEIGHT,
                "lane_id": lane["id"],
                "cx": box["x"] + box["w"] / 2,
                "cy": box_top + BOX_HEIGHT / 2,
                "top": box_top,
                "bottom": box_top + BOX_HEIGHT,
            }
    return index


# === Rendering ===========================================================


def _esc(s: str) -> str:
    """Minimal XML escaping for text content + attribute values."""
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _arrow_path(src: dict[str, Any], dst: dict[str, Any]) -> str:
    """Cubic Bezier connecting two boxes vertically.

    Choose endpoints based on relative position. Deterministic — pure
    function of the (rounded) coordinates.
    """
    if dst["cy"] > src["cy"]:
        # downward: src bottom -> dst top
        x1, y1 = src["cx"], src["bottom"]
        x2, y2 = dst["cx"], dst["top"]
    else:
        # upward: src top -> dst bottom
        x1, y1 = src["cx"], src["top"]
        x2, y2 = dst["cx"], dst["bottom"]
    # Control points pull toward the midpoint, biased vertically.
    midy = (y1 + y2) / 2
    cx1, cy1 = x1, midy
    cx2, cy2 = x2, midy
    return (
        f"M {x1:.1f} {y1:.1f} "
        f"C {cx1:.1f} {cy1:.1f} {cx2:.1f} {cy2:.1f} {x2:.1f} {y2:.1f}"
    )


def render(swim_lanes: list[dict[str, Any]] | None = None) -> str:
    """Render the architecture SVG as a deterministic string.

    The output is byte-identical across runs for the same input
    (no timestamps, no random IDs, sorted child ordering inside
    <defs>). Returns the full XML document including the <?xml?>
    declaration.
    """
    lanes = swim_lanes if swim_lanes is not None else SWIM_LANES
    idx = _box_index(lanes)

    out: list[str] = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {CANVAS_W} {CANVAS_H}" '
        f'width="{CANVAS_W}" height="{CANVAS_H}" '
        f'role="img" aria-label="vibemix architecture diagram">'
    )

    # --- <defs> — children emitted in fixed, sorted order ---------------
    out.append("  <defs>")
    # Arrow head marker
    out.append(
        '    <marker id="arrow-end" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
    )
    out.append(f'      <path d="M 0 0 L 10 5 L 0 10 z" fill="{AMBER}"/>')
    out.append("    </marker>")
    # Gemini glow filter
    out.append('    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">')
    out.append('      <feGaussianBlur stdDeviation="6" result="blur"/>')
    out.append('      <feMerge>')
    out.append('        <feMergeNode in="blur"/>')
    out.append('        <feMergeNode in="SourceGraphic"/>')
    out.append('      </feMerge>')
    out.append("    </filter>")
    # Lane gradient
    out.append(
        '    <linearGradient id="lane-bg" x1="0" y1="0" x2="0" y2="1">'
    )
    out.append(f'      <stop offset="0" stop-color="{VOID_1}" stop-opacity="1"/>')
    out.append(f'      <stop offset="1" stop-color="{VOID_2}" stop-opacity="1"/>')
    out.append("    </linearGradient>")
    out.append("  </defs>")

    # --- Background -----------------------------------------------------
    out.append(
        f'  <rect x="0" y="0" width="{CANVAS_W}" height="{CANVAS_H}" '
        f'fill="{VOID_0}"/>'
    )

    # --- Title (top) ----------------------------------------------------
    out.append(
        f'  <text x="{CANVAS_W / 2:.0f}" y="24" text-anchor="middle" '
        f'font-family="Saira, system-ui, sans-serif" font-size="14" '
        f'fill="{SILK_65}" letter-spacing="3" '
        f'style="text-transform:uppercase">vibemix architecture</text>'
    )

    # --- Swim lanes -----------------------------------------------------
    for lane in lanes:
        lane_y = lane["y"]
        lane_label = lane["label"]
        lane_top = lane_y + LANE_LABEL_HEIGHT
        lane_inner_h = LANE_HEIGHT - LANE_LABEL_HEIGHT
        glow_attr = ' filter="url(#glow)"' if lane.get("glow") else ""
        # Lane label (uppercase letterspaced — CDJ Whisper register)
        out.append(
            f'  <text x="{LANE_LEFT_PAD}" y="{lane_y + 14}" '
            f'font-family="Saira, system-ui, sans-serif" font-size="11" '
            f'fill="{SILK_40}" letter-spacing="3" '
            f'style="text-transform:uppercase">{_esc(lane_label)}</text>'
        )
        # Lane body (rounded rect, glass-edge stroke)
        out.append(
            f'  <rect x="{LANE_LEFT_PAD}" y="{lane_top}" '
            f'width="{CANVAS_W - LANE_LEFT_PAD - LANE_RIGHT_PAD}" '
            f'height="{lane_inner_h}" rx="10" ry="10" '
            f'fill="url(#lane-bg)" stroke="{GLASS_EDGE}" '
            f'stroke-width="1"{glow_attr}/>'
        )
        # Boxes inside the lane
        for box in lane["boxes"]:
            b = idx[box["id"]]
            box_stroke = AMBER_40 if lane.get("glow") else SILK_22
            out.append(
                f'  <rect x="{b["x"]}" y="{b["top"]}" '
                f'width="{b["w"]}" height="{b["h"]}" rx="{BOX_RADIUS}" '
                f'ry="{BOX_RADIUS}" fill="{VOID_3}" stroke="{box_stroke}" '
                f'stroke-width="1"/>'
            )
            # Title
            out.append(
                f'  <text x="{b["x"] + b["w"] / 2:.0f}" '
                f'y="{b["top"] + BOX_TITLE_OFFSET}" text-anchor="middle" '
                f'font-family="Saira, system-ui, sans-serif" font-size="15" '
                f'font-weight="600" fill="{SILK}">'
                f'{_esc(box["label"])}</text>'
            )
            # Subtitle
            out.append(
                f'  <text x="{b["x"] + b["w"] / 2:.0f}" '
                f'y="{b["top"] + BOX_SUBTITLE_OFFSET}" text-anchor="middle" '
                f'font-family="Saira, system-ui, sans-serif" font-size="11" '
                f'fill="{SILK_65}">'
                f'{_esc(box["subtitle"])}</text>'
            )

    # --- Arrows (sorted by id for determinism) --------------------------
    for arrow in sorted(ARROWS, key=lambda a: a["id"]):
        src = idx[arrow["from"]]
        dst = idx[arrow["to"]]
        path_d = _arrow_path(src, dst)
        out.append(
            f'  <path d="{path_d}" fill="none" stroke="{AMBER}" '
            f'stroke-width="1.8" stroke-opacity="0.78" '
            f'marker-end="url(#arrow-end)"/>'
        )
        if arrow.get("label"):
            mid_x = (src["cx"] + dst["cx"]) / 2
            mid_y = (src["cy"] + dst["cy"]) / 2
            out.append(
                f'  <text x="{mid_x:.0f}" y="{mid_y:.0f}" '
                f'text-anchor="middle" font-family="JetBrains Mono, ui-monospace, monospace" '
                f'font-size="10" fill="{AMBER_PALE}" '
                f'style="paint-order:stroke;stroke:{VOID_0};stroke-width:3px">'
                f'{_esc(arrow["label"])}</text>'
            )

    # --- Footer ---------------------------------------------------------
    out.append(
        f'  <text x="{CANVAS_W / 2:.0f}" y="{CANVAS_H - 16}" '
        f'text-anchor="middle" font-family="JetBrains Mono, ui-monospace, monospace" '
        f'font-size="10" fill="{SILK_40}" letter-spacing="1">'
        f'open source - Apache 2.0 - github.com/bravoh/vibemix</text>'
    )

    out.append("</svg>")
    return "\n".join(out) + "\n"


# === CLI =================================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render the vibemix architecture SVG (CDJ Whisper v5).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: docs/assets/architecture.svg in repo).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 0 if the committed SVG matches generator output, 1 on drift.",
    )
    args = parser.parse_args(argv)

    # Default output is repo-relative, computed from this script's location
    # so the tool works regardless of cwd.
    repo_root = Path(__file__).resolve().parents[2]
    default_out = repo_root / "docs" / "assets" / "architecture.svg"
    out_path = args.output if args.output is not None else default_out

    rendered = render()

    if args.check:
        if not out_path.exists():
            print(f"architecture.svg missing at {out_path}", file=sys.stderr)
            return 1
        committed = out_path.read_text(encoding="utf-8")
        if committed != rendered:
            print(
                f"architecture.svg drift detected at {out_path}\n"
                f"  expected (generator): {len(rendered)} bytes\n"
                f"  committed:            {len(committed)} bytes\n"
                f"Re-run `python scripts/dist/render_architecture.py` to refresh.",
                file=sys.stderr,
            )
            return 1
        print("architecture.svg is current.")
        return 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    print(f"wrote {out_path} ({len(rendered)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
