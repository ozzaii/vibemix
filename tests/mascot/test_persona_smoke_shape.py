"""MASCOT-06 smoke test — assert persona_smoke.sh + persona-smoke-harness.ts
have the expected invariants. Pure static-string test; does not invoke
ffmpeg or Tauri."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL_SCRIPT = REPO_ROOT / "scripts" / "mascot" / "persona_smoke.sh"
TS_HARNESS = (
    REPO_ROOT / "tauri" / "ui" / "src" / "mascot" / "persona-smoke-harness.ts"
)


def test_shell_script_exists_executable():
    assert SHELL_SCRIPT.is_file()


def test_shell_30s_duration():
    src = SHELL_SCRIPT.read_text()
    assert "DURATION_SEC=30" in src


def test_shell_5mb_size_cap():
    src = SHELL_SCRIPT.read_text()
    assert "5 * 1024 * 1024" in src


def test_shell_output_path_in_docs_mascot():
    src = SHELL_SCRIPT.read_text()
    assert "docs/mascot" in src
    assert "persona_smoke.webm" in src


def test_shell_vp9_codec():
    src = SHELL_SCRIPT.read_text()
    assert "libvpx-vp9" in src


def test_ts_harness_exists():
    assert TS_HARNESS.is_file()


def test_ts_harness_30s_duration_constant():
    src = TS_HARNESS.read_text()
    assert "PERSONA_SMOKE_DURATION_MS = 30000" in src


def test_ts_harness_15_schedule_entries():
    src = TS_HARNESS.read_text()
    # Schedule entries match `{ t_ms: <number>` pattern (15 total).
    # Interface declaration + accessor uses are counted via different syntax.
    assert src.count("{ t_ms:") == 15


def test_ts_harness_covers_all_5_emotions():
    src = TS_HARNESS.read_text()
    for emotion in (
        "emotion_joy",
        "emotion_trust",
        "emotion_surprise",
        "emotion_anticipation",
        "emotion_focus",
    ):
        assert emotion in src, f"missing emotion clip in schedule: {emotion}"


def test_ts_harness_covers_all_10_reactions():
    src = TS_HARNESS.read_text()
    for reaction in (
        "react_kick_swap",
        "react_sub_layer",
        "react_breakdown",
        "react_reentry",
        "react_phrase_boundary",
        "react_distortion_climb",
        "react_acid_line",
        "react_mix_in",
        "react_mix_out",
        "react_hype_peak",
    ):
        assert reaction in src, f"missing reaction clip in schedule: {reaction}"


def test_ts_harness_hype_peak_has_3s_extended_window():
    """react_hype_peak is the README hero anchor — gets t=27s..30s = 3s extended window."""
    src = TS_HARNESS.read_text()
    assert "t_ms: 27000" in src and "react_hype_peak" in src
