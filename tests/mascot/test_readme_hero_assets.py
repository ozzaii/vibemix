"""MASCOT-07 smoke test — assert README hero assets ship at correct
paths and within size guards. Pure static-file test; does not invoke
Three.js / ffmpeg."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PNG = REPO_ROOT / "docs" / "assets" / "readme-hero.png"
WEBM = REPO_ROOT / "docs" / "assets" / "readme-hero.webm"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "readme-hero-sync.yml"


def test_png_exists():
    assert PNG.is_file()


def test_webm_exists():
    assert WEBM.is_file()


def test_png_under_50kb():
    assert PNG.stat().st_size <= 50 * 1024, (
        f"readme-hero.png is {PNG.stat().st_size} bytes (> 50 KB target)"
    )


def test_webm_under_100kb():
    assert WEBM.stat().st_size <= 100 * 1024, (
        f"readme-hero.webm is {WEBM.stat().st_size} bytes (> 100 KB target)"
    )


def test_png_valid_magic():
    sig = PNG.read_bytes()[:8]
    assert sig == b"\x89PNG\r\n\x1a\n", "PNG signature missing"


def test_webm_valid_magic():
    sig = WEBM.read_bytes()[:4]
    # WebM is an EBML container; magic is 0x1A45DFA3
    assert sig == b"\x1a\x45\xdf\xa3", "WebM/EBML signature missing"


def test_workflow_asserts_hero_assets():
    if not WORKFLOW.is_file():
        return  # workflow optional in some clones
    src = WORKFLOW.read_text()
    assert "docs/assets/readme-hero.png" in src
    assert "docs/assets/readme-hero.webm" in src
