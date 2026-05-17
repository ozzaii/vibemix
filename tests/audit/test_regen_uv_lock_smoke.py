"""DEPS-01 smoke test — assert scripts/audit/regen_uv_lock.sh keeps the
hermetic invariants. This test does NOT invoke docker — it reads the
script source and asserts the literal constants are present."""

from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "audit" / "regen_uv_lock.sh"


def test_script_exists():
    assert SCRIPT.is_file(), f"missing {SCRIPT}"


def test_image_pin_is_literal_python_3_12_slim_bookworm():
    src = SCRIPT.read_text()
    assert 'IMAGE="python:3.12-slim-bookworm"' in src, \
        "DEPS-01: image pin must be literal `python:3.12-slim-bookworm`"


def test_uv_version_pin_is_literal_0_11_14():
    src = SCRIPT.read_text()
    assert 'UV_VERSION="0.11.14"' in src, \
        "DEPS-01: uv version pin must be literal `0.11.14`"


def test_strict_bash_settings():
    src = SCRIPT.read_text()
    assert "set -euo pipefail" in src, \
        "DEPS-01: script must use strict bash settings"


def test_no_pip_freeze_in_executable_lines():
    # Pitfall 1: `pip freeze` from `.venv` is REJECTED — the whole point
    # of this script is to avoid that path. Comments may explain WHY pip
    # freeze is banned (the header explicitly cites Pitfall 1), but no
    # executable line may invoke it.
    src = SCRIPT.read_text()
    for lineno, line in enumerate(src.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert "pip freeze" not in stripped, \
            f"DEPS-01: `pip freeze` invocation forbidden at line {lineno}: {stripped}"


def test_docker_run_uses_workspace_bind_mount():
    src = SCRIPT.read_text()
    assert 'docker run' in src and '-v "$PWD":/work' in src and '-w /work' in src, \
        "DEPS-01: docker invocation must bind-mount the workspace at /work"
