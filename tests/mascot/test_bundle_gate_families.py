"""MASCOT-03 smoke test — assert check_bundle_size.sh routes prefixes to
correct family bands. Pure static-string test; does not invoke the bash
script against real GLBs."""
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "mascot" / "check_bundle_size.sh"


def test_script_exists():
    assert SCRIPT.is_file()


def test_band_for_prefix_function_present():
    src = SCRIPT.read_text()
    assert "band_for_prefix()" in src


def test_base_band_is_200_600():
    src = SCRIPT.read_text()
    assert 'base) echo "200 600"' in src


def test_emotion_band_is_300_900():
    src = SCRIPT.read_text()
    assert 'emotion) echo "300 900"' in src


def test_prep_band_is_400_1200():
    src = SCRIPT.read_text()
    assert 'prep) echo "400 1200"' in src


def test_react_band_is_400_1200():
    src = SCRIPT.read_text()
    assert 'react) echo "400 1200"' in src


def test_for_loop_iterates_all_four_prefixes():
    src = SCRIPT.read_text()
    for pattern in ("base_*.glb", "emotion_*.glb", "prep_*.glb", "react_*.glb"):
        assert pattern in src, f"missing prefix scan: {pattern}"


def test_tier1_delegate_preserved():
    src = SCRIPT.read_text()
    assert "scripts/check_mascot_glb_size.sh" in src


def test_strict_bash_settings():
    src = SCRIPT.read_text()
    assert "set -euo pipefail" in src
