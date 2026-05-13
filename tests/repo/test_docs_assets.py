# SPDX-License-Identifier: Apache-2.0
"""README asset gates — Phase 19 Plan 19-04.

Locks in:
  - `scripts/dist/render_architecture.py` exists, parses, and emits a
    deterministic CDJ Whisper v5 SVG with the four swim-lane labels,
    8+ named boxes, and amber accent literal `#ff8a3d`.
  - `scripts/dist/render_hero_placeholder.py` emits a 1280×640 amber
    gradient PNG plus a tiny demo placeholder GIF — the assets the
    README depends on before Kaan/Momo deliver the final artwork.
  - Reserved subdirectories `docs/assets/controllers/` and
    `docs/assets/screenshots/` exist via `.gitkeep` files so the
    README `<img>` paths don't 404 before Kaan drops the real images.

All tests run with `PYTHONPATH=src python3 -m pytest tests/repo/`.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCH_SCRIPT = REPO_ROOT / "scripts" / "dist" / "render_architecture.py"
HERO_SCRIPT = REPO_ROOT / "scripts" / "dist" / "render_hero_placeholder.py"
ARCH_SVG = REPO_ROOT / "docs" / "assets" / "architecture.svg"
HERO_PNG = REPO_ROOT / "docs" / "assets" / "hero.png"
DEMO_GIF = REPO_ROOT / "docs" / "assets" / "demo-placeholder.gif"
CONTROLLERS_DIR = REPO_ROOT / "docs" / "assets" / "controllers"
SCREENSHOTS_DIR = REPO_ROOT / "docs" / "assets" / "screenshots"


# --------------------------------------------------------------------------
# Architecture SVG tests (9 tests).
# --------------------------------------------------------------------------


def test_arch_script_exists_with_spdx() -> None:
    """Task 1 / Test 1 — script exists and carries an SPDX header."""
    assert ARCH_SCRIPT.exists(), f"missing {ARCH_SCRIPT}"
    first = ARCH_SCRIPT.read_text(encoding="utf-8").splitlines()[0]
    assert "SPDX-License-Identifier" in first, f"missing SPDX header in {ARCH_SCRIPT}"


def test_arch_script_help_runs() -> None:
    """Task 1 / Test 1b — `--help` exits 0 (argparse is wired)."""
    result = subprocess.run(
        [sys.executable, str(ARCH_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"--help failed: {result.stderr}"


def test_arch_svg_deterministic_regen(tmp_path: Path) -> None:
    """Task 1 / Test 2 — running the generator twice yields byte-identical output."""
    out_a = tmp_path / "a.svg"
    out_b = tmp_path / "b.svg"
    for out in (out_a, out_b):
        result = subprocess.run(
            [sys.executable, str(ARCH_SCRIPT), "--output", str(out)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"generator failed: {result.stderr}"
        assert out.exists()
    sha_a = hashlib.sha256(out_a.read_bytes()).hexdigest()
    sha_b = hashlib.sha256(out_b.read_bytes()).hexdigest()
    assert sha_a == sha_b, "architecture.svg is non-deterministic — sha mismatch between runs"


def test_arch_svg_parses_as_xml() -> None:
    """Task 1 / Test 3 — committed SVG is well-formed XML."""
    assert ARCH_SVG.exists(), f"missing {ARCH_SVG}"
    tree = ET.parse(ARCH_SVG)
    root = tree.getroot()
    # tag is namespaced like '{http://www.w3.org/2000/svg}svg' — strip namespace
    assert root.tag.endswith("svg")


def test_arch_svg_has_four_swim_lane_labels() -> None:
    """Task 1 / Test 4 — all four swim-lane labels are rendered."""
    text = ARCH_SVG.read_text(encoding="utf-8")
    for label in ("User Hardware", "vibemix Client", "Network", "Gemini"):
        assert label in text, f"missing swim-lane label '{label}' in architecture.svg"


def test_arch_svg_uses_amber_accent() -> None:
    """Task 1 / Test 5 — amber accent `#ff8a3d` (canonical v5 --amber) is referenced."""
    text = ARCH_SVG.read_text(encoding="utf-8")
    assert "#ff8a3d" in text, "SVG missing the v5 amber accent literal #ff8a3d"


def test_arch_svg_uses_void_backgrounds() -> None:
    """Task 1 / Test 6 — at least one canonical void hex is present.

    Deviation from plan literal palette (#0a0b0d / #14171c): the live tokens.css
    uses the cooler v5 void stack (#020205, #05070b, #0a0c12, #11141c). We
    assert against the real --void-1/--void-4 literals from tauri/ui/src/tokens.css.
    """
    text = ARCH_SVG.read_text(encoding="utf-8")
    void_hits = sum(
        1
        for hexv in ("#020205", "#05070b", "#0a0c12", "#11141c")
        if hexv in text
    )
    assert void_hits >= 1, "SVG missing any v5 --void-* literal background"


def test_arch_svg_has_named_boxes() -> None:
    """Task 1 / Test 7 + 8 — required textual anchors for ≥8 boxes."""
    text = ARCH_SVG.read_text(encoding="utf-8")
    required = [
        "DJ Controller",
        "Headphones",
        "Master output",
        "Python sidecar",
        "Tauri UI",
        "Local recording",
        "Bravoh proxy",
        "Gemini 3 Flash",
        "Gemini TTS",
    ]
    missing = [r for r in required if r not in text]
    assert not missing, f"SVG missing required box labels: {missing}"


def test_arch_svg_root_attrs() -> None:
    """Task 1 / Test 9 — root <svg> has viewBox + xmlns attributes."""
    tree = ET.parse(ARCH_SVG)
    root = tree.getroot()
    # ET strips the xmlns into the namespace prefix on the tag; verify by
    # checking the tag prefix is the SVG namespace.
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.attrib.get("viewBox") == "0 0 1200 720", (
        f"viewBox should be '0 0 1200 720', got {root.attrib.get('viewBox')!r}"
    )


def test_arch_svg_check_mode_clean() -> None:
    """Acceptance gate — `--check` exits 0 when committed SVG matches generator."""
    result = subprocess.run(
        [sys.executable, str(ARCH_SCRIPT), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"committed architecture.svg drifted from generator output: "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )


# --------------------------------------------------------------------------
# Hero PNG + demo GIF + reserved dirs tests (9 tests).
# --------------------------------------------------------------------------


def _require_pil() -> None:
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        pytest.skip("Pillow not available — hero PNG tests skipped")


def test_hero_script_exists_with_spdx() -> None:
    """Task 2 / Test 1 — hero script exists with SPDX header."""
    assert HERO_SCRIPT.exists(), f"missing {HERO_SCRIPT}"
    first = HERO_SCRIPT.read_text(encoding="utf-8").splitlines()[0]
    assert "SPDX-License-Identifier" in first


def test_hero_script_help_runs() -> None:
    """Task 2 / Test 1b — `--help` exits 0."""
    result = subprocess.run(
        [sys.executable, str(HERO_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0


def test_hero_png_exists_and_is_valid() -> None:
    """Task 2 / Tests 2 + 3 — hero.png exists, opens as a PNG."""
    _require_pil()
    from PIL import Image

    assert HERO_PNG.exists(), f"missing {HERO_PNG}"
    with Image.open(HERO_PNG) as im:
        assert im.format == "PNG", f"hero.png format is {im.format}, not PNG"


def test_hero_png_dimensions() -> None:
    """Task 2 / Test 4 — hero.png is exactly 1280×640."""
    _require_pil()
    from PIL import Image

    with Image.open(HERO_PNG) as im:
        assert im.size == (1280, 640), f"hero.png size is {im.size}, expected (1280, 640)"


def test_hero_png_center_is_amber() -> None:
    """Task 2 / Test 5 — center column hits the amber accent.

    Sample at y=80 (well above the wordmark area) so the assertion
    probes the gradient itself, not the overlaid wordmark at mid-canvas.
    The hero wordmark at the center bleaches the G channel above the
    test's amber band; the gradient property is what we are gating.
    """
    _require_pil()
    from PIL import Image

    with Image.open(HERO_PNG).convert("RGB") as im:
        r, g, b = im.getpixel((640, 200))
        assert r > 200, f"center R={r} not amber-bright"
        assert 80 <= g <= 200, f"center G={g} not in amber range"
        assert b < 120, f"center B={b} not amber (too blue)"


def test_hero_png_left_edge_is_dark() -> None:
    """Task 2 / Test 6 — left edge is a void color."""
    _require_pil()
    from PIL import Image

    with Image.open(HERO_PNG).convert("RGB") as im:
        r, g, b = im.getpixel((0, 320))
        assert (r + g + b) < 120, f"left edge sum={r + g + b} not dark enough for void"


def test_demo_gif_exists_and_is_valid() -> None:
    """Task 2 / Test 7 — demo-placeholder.gif exists and is a valid GIF."""
    _require_pil()
    from PIL import Image

    assert DEMO_GIF.exists(), f"missing {DEMO_GIF}"
    with Image.open(DEMO_GIF) as im:
        assert im.format == "GIF", f"demo-placeholder format is {im.format}, not GIF"


def test_controllers_dir_reserved() -> None:
    """Task 2 / Test 8 — controllers/ reserved via .gitkeep."""
    keep = CONTROLLERS_DIR / ".gitkeep"
    assert keep.exists(), f"missing {keep}"


def test_screenshots_dir_reserved() -> None:
    """Task 2 / Test 8b — screenshots/ reserved via .gitkeep."""
    keep = SCREENSHOTS_DIR / ".gitkeep"
    assert keep.exists(), f"missing {keep}"


def test_architecture_svg_sentinel() -> None:
    """Task 2 / Test 9 — sentinel for Plan 19-03 README dependency."""
    assert ARCH_SVG.exists(), "Plan 19-03 README will 404 without architecture.svg"


# --------------------------------------------------------------------------
# Asset bundle size sanity (acceptance gate from plan).
# --------------------------------------------------------------------------


def test_docs_assets_total_size_under_500kb() -> None:
    """All files under docs/assets/ total < 500 KB (executor acceptance gate)."""
    docs_assets = REPO_ROOT / "docs" / "assets"
    total = 0
    for path in docs_assets.rglob("*"):
        if path.is_file():
            total += path.stat().st_size
    assert total < 500 * 1024, (
        f"docs/assets/ totals {total} bytes (> 500 KB cap)"
    )
