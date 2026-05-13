# SPDX-License-Identifier: Apache-2.0
"""Hero PNG + demo GIF placeholders for the README.

Generates two committed artifacts:

  1. `docs/assets/hero.png` — 1280x640 amber-gradient banner with a
     "vibemix" wordmark + tagline + small `placeholder` tag in the
     bottom-right corner. Replaced by Kaan/Momo's final artwork
     post-launch; until then, the README renders sanely.

  2. `docs/assets/demo-placeholder.gif` — tiny 320x180 looping GIF
     reading "demo coming soon". Stands in for the 30-45s demo
     video that Kaan + Francesco shoot post-binary-ship.

Palette is hard-coded from `tauri/ui/src/tokens.css` (v5 CDJ Whisper):
  - void-1  #020205 (gradient edges)
  - amber   #ff8a3d (gradient midpoint)
  - silk    #d6cfc7 (text)

Usage::

    python scripts/dist/render_hero_placeholder.py             # writes hero.png
    python scripts/dist/render_hero_placeholder.py --demo-gif  # writes demo-placeholder.gif
    python scripts/dist/render_hero_placeholder.py --all       # both
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# === v5 palette (canonical: tauri/ui/src/tokens.css) =====================

VOID_1 = (2, 2, 5)       # --void-1 #020205
AMBER = (255, 138, 61)   # --amber #ff8a3d
SILK = (214, 207, 199)   # --silk #d6cfc7
SILK_65 = (214, 207, 199, 165)
SILK_22 = (214, 207, 199, 56)

# === Hero PNG ============================================================

HERO_W = 1280
HERO_H = 640


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Linear interpolation between two RGB tuples."""
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )


def render_hero(out_path: Path) -> None:
    """Write the 1280x640 amber-gradient hero PNG to *out_path*.

    Gradient is a 3-stop horizontal lerp: void-1 -> amber -> void-1.
    Encoded deterministically (PIL PNG save with no timestamp chunks).
    """
    img = Image.new("RGB", (HERO_W, HERO_H), VOID_1)
    draw = ImageDraw.Draw(img)

    mid_x = HERO_W // 2
    # Column-wise gradient — cheap, deterministic, no surprises.
    for x in range(HERO_W):
        if x <= mid_x:
            t = x / mid_x  # 0 -> 1
            color = _lerp(VOID_1, AMBER, t)
        else:
            t = (x - mid_x) / (HERO_W - mid_x)  # 0 -> 1
            color = _lerp(AMBER, VOID_1, t)
        draw.line([(x, 0), (x, HERO_H - 1)], fill=color)

    # Add a darker vignette across the top + bottom 20% to settle text.
    overlay = Image.new("RGBA", (HERO_W, HERO_H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    for y in range(int(HERO_H * 0.22)):
        alpha = int(120 * (1 - y / (HERO_H * 0.22)))
        odraw.line([(0, y), (HERO_W, y)], fill=(0, 0, 0, alpha))
    for y in range(int(HERO_H * 0.78), HERO_H):
        alpha = int(120 * ((y - HERO_H * 0.78) / (HERO_H * 0.22)))
        odraw.line([(0, y), (HERO_W, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Re-bind draw to the composited image.
    draw = ImageDraw.Draw(img)

    # Wordmark — Pillow's default font is bitmap and tiny; scale by writing
    # large into a sub-image and resizing for a "displayed" look without
    # needing a vendored font file.
    title_font = ImageFont.load_default()
    title_text = "vibemix"
    # Render title on a transparent layer at 8x scale, then resize down for
    # cleaner edges than the raw bitmap font.
    title_layer = Image.new("RGBA", (HERO_W, 240), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(title_layer)
    title_bbox = tdraw.textbbox((0, 0), title_text, font=title_font)
    tw = title_bbox[2] - title_bbox[0]
    th = title_bbox[3] - title_bbox[1]
    # Scale factor — bitmap font is ~10px tall; we want ~96px display height.
    scale = 12
    # Draw at large scale via the resize path.
    small = Image.new("RGBA", (tw + 8, th + 8), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(small)
    sdraw.text((4, 4), title_text, font=title_font, fill=(*SILK, 255))
    big = small.resize(
        ((tw + 8) * scale, (th + 8) * scale),
        resample=Image.Resampling.LANCZOS,
    )
    bx = (HERO_W - big.width) // 2
    by = HERO_H // 2 - big.height // 2 - 24
    img.paste(big, (bx, by), big)

    # Subtitle — render at 5x scale via the same path for legibility.
    subtitle_text = "AI co-host for your DJ set"
    sub_bbox = tdraw.textbbox((0, 0), subtitle_text, font=title_font)
    sw = sub_bbox[2] - sub_bbox[0]
    sh = sub_bbox[3] - sub_bbox[1]
    sub_scale = 4
    sub_small = Image.new("RGBA", (sw + 8, sh + 8), (0, 0, 0, 0))
    sub_draw = ImageDraw.Draw(sub_small)
    sub_draw.text((4, 4), subtitle_text, font=title_font, fill=(*SILK, 220))
    sub_big = sub_small.resize(
        ((sw + 8) * sub_scale, (sh + 8) * sub_scale),
        resample=Image.Resampling.LANCZOS,
    )
    sbx = (HERO_W - sub_big.width) // 2
    sby = by + big.height + 8
    img.paste(sub_big, (sbx, sby), sub_big)

    # Bottom-right placeholder tag — small, low-contrast, intentional.
    tag_text = "placeholder - final artwork by Bravoh design lead"
    tag_bbox = tdraw.textbbox((0, 0), tag_text, font=title_font)
    tagw = tag_bbox[2] - tag_bbox[0]
    tagh = tag_bbox[3] - tag_bbox[1]
    tag_scale = 2
    tag_small = Image.new("RGBA", (tagw + 8, tagh + 8), (0, 0, 0, 0))
    tag_draw = ImageDraw.Draw(tag_small)
    tag_draw.text((4, 4), tag_text, font=title_font, fill=(*SILK, 110))
    tag_big = tag_small.resize(
        ((tagw + 8) * tag_scale, (tagh + 8) * tag_scale),
        resample=Image.Resampling.LANCZOS,
    )
    img.paste(
        tag_big,
        (HERO_W - tag_big.width - 24, HERO_H - tag_big.height - 16),
        tag_big,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # optimize=True + no pnginfo keeps the file deterministic across runs.
    img.save(out_path, format="PNG", optimize=True)


# === Demo placeholder GIF ================================================

GIF_W = 320
GIF_H = 180


def render_demo_gif(out_path: Path) -> None:
    """Write the small looping demo-placeholder GIF.

    Three frames so the GIF parser confirms it as animated; total file
    size << 50 KB.
    """
    frames: list[Image.Image] = []
    text = "demo coming soon"

    for i in range(3):
        frame = Image.new("P", (GIF_W, GIF_H), 0)
        # Build a small palette (PIL P-mode requires explicit palette setup
        # to keep file size tiny and the result deterministic).
        palette = [
            VOID_1[0], VOID_1[1], VOID_1[2],   # 0 = void
            AMBER[0], AMBER[1], AMBER[2],      # 1 = amber
            SILK[0], SILK[1], SILK[2],         # 2 = silk
        ] + [0] * (768 - 9)
        frame.putpalette(palette)
        draw = ImageDraw.Draw(frame)

        # Pulse the amber underline brightness across the 3 frames.
        underline_color = 1 if i != 1 else 2  # amber / silk / amber
        # Draw the text via the default bitmap font in silk.
        font = ImageFont.load_default()
        tbbox = draw.textbbox((0, 0), text, font=font)
        tw = tbbox[2] - tbbox[0]
        th = tbbox[3] - tbbox[1]

        # Scale-up via a temporary RGBA layer (mirrors hero.png approach)
        small = Image.new("P", (tw + 4, th + 4), 0)
        small.putpalette(palette)
        sdraw = ImageDraw.Draw(small)
        sdraw.text((2, 2), text, font=font, fill=2)  # silk
        scale = 3
        big = small.resize(
            ((tw + 4) * scale, (th + 4) * scale),
            resample=Image.Resampling.NEAREST,
        )
        bx = (GIF_W - big.width) // 2
        by = (GIF_H - big.height) // 2 - 8
        frame.paste(big, (bx, by))

        # Amber underline below the text — pulses across the 3 frames.
        ux1 = bx + 8
        ux2 = bx + big.width - 8
        uy = by + big.height + 4
        draw.line([(ux1, uy), (ux2, uy)], fill=underline_color, width=2)

        frames.append(frame)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        out_path,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=800,
        loop=0,
        optimize=True,
    )


# === CLI =================================================================


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render the vibemix hero PNG + demo GIF placeholders.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for hero.png (default: docs/assets/hero.png).",
    )
    parser.add_argument(
        "--demo-gif",
        action="store_true",
        help="Write the demo-placeholder.gif instead of hero.png.",
    )
    parser.add_argument(
        "--demo-gif-output",
        type=Path,
        default=None,
        help="Output path for demo gif (default: docs/assets/demo-placeholder.gif).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Render BOTH hero.png and demo-placeholder.gif at their defaults.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    default_hero = repo_root / "docs" / "assets" / "hero.png"
    default_gif = repo_root / "docs" / "assets" / "demo-placeholder.gif"

    if args.all:
        hero_out = args.output or default_hero
        gif_out = args.demo_gif_output or default_gif
        render_hero(hero_out)
        print(f"wrote {hero_out} ({hero_out.stat().st_size} bytes)")
        render_demo_gif(gif_out)
        print(f"wrote {gif_out} ({gif_out.stat().st_size} bytes)")
        return 0

    if args.demo_gif:
        gif_out = args.demo_gif_output or args.output or default_gif
        render_demo_gif(gif_out)
        print(f"wrote {gif_out} ({gif_out.stat().st_size} bytes)")
        return 0

    hero_out = args.output or default_hero
    render_hero(hero_out)
    print(f"wrote {hero_out} ({hero_out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
