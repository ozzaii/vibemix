#!/usr/bin/env python3
"""
Phase 13 Plan 02 — generate 4 monochrome 16x16 tray icons.

macOS NSStatusItem template-image convention: monochrome (black) PNG with
alpha. macOS auto-tints based on menu-bar appearance (light/dark mode);
Windows shows the raw image (we draw white-on-transparent for legibility
on both light and dark Windows taskbar themes by rendering with full
alpha + black ink, then macOS template flag handles the recolor).

Reference: 13-CONTEXT Area 5 — 4 icon states:
  - tray-idle.png      : outline-only square mask (no session)
  - tray-live.png      : outline + filled accent dot (top-right) — session active
  - tray-thinking.png  : outline + small pulse dot — Gemini generating
  - tray-error.png     : outline + filled X cross — error state

Run:
    python3 scripts/gen_tray_icons.py

Writes 4 PNGs into ../icons/ (relative to this script's parent dir).
Idempotent — overwrites existing icons.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.stderr.write(
        "ERROR: Pillow not installed. Install with `python3 -m pip install Pillow`.\n"
    )
    sys.exit(1)

# 16x16 is the macOS NSStatusItem standard. We render @ 2x (32x32) and
# downscale with Lanczos so the antialiasing looks crisp on Retina menu
# bars while staying point-perfect on standard displays.
SCALE = 2
SIZE = 16
RENDER = SIZE * SCALE

# Ink colour: pure black with full alpha. macOS template-image rendering
# replaces black with the appropriate menu-bar foreground at runtime.
INK = (0, 0, 0, 255)
DOT = (0, 0, 0, 255)


def base() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (RENDER, RENDER), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    return img, draw


def square_outline(draw: ImageDraw.ImageDraw) -> None:
    # Outline a rounded square at the centre — 12px (24 @2x) inside a 16
    # canvas leaves 2px padding all round so it doesn't crowd the bar.
    pad = 4 * SCALE
    size = RENDER - 2 * pad
    draw.rounded_rectangle(
        (pad, pad, pad + size, pad + size),
        radius=2 * SCALE,
        outline=INK,
        width=2 * SCALE,
    )


def make_idle() -> Image.Image:
    img, draw = base()
    square_outline(draw)
    return img


def make_live() -> Image.Image:
    img, draw = base()
    square_outline(draw)
    # Filled accent dot at the top-right corner.
    dot_r = 3 * SCALE
    cx = RENDER - dot_r - 1
    cy = dot_r + 1
    draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=DOT)
    return img


def make_thinking() -> Image.Image:
    img, draw = base()
    square_outline(draw)
    # Smaller dot in the centre (suggests "pulse"); state-swap in tray.rs
    # alternates idle/thinking icons to fake the animation.
    dot_r = 2 * SCALE
    cx = RENDER // 2
    cy = RENDER // 2
    draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=DOT)
    return img


def make_error() -> Image.Image:
    img, draw = base()
    square_outline(draw)
    # X cross across the inner area to signal error.
    pad = 6 * SCALE
    w = 2 * SCALE
    draw.line((pad, pad, RENDER - pad, RENDER - pad), fill=INK, width=w)
    draw.line((pad, RENDER - pad, RENDER - pad, pad), fill=INK, width=w)
    return img


def downscale(img: Image.Image) -> Image.Image:
    return img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main() -> int:
    out_dir = Path(__file__).resolve().parent.parent / "icons"
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = {
        "tray-idle.png": make_idle(),
        "tray-live.png": make_live(),
        "tray-thinking.png": make_thinking(),
        "tray-error.png": make_error(),
    }
    for name, img in targets.items():
        out = downscale(img)
        path = out_dir / name
        out.save(path, "PNG", optimize=True)
        print(f"-> wrote {path} ({path.stat().st_size} bytes)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
