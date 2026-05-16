"""Tests for `scripts/dayzero/launch_trigger.sh` — Pitfall P78 enforcement.

Asserts:
1. Default mode is dry-run (no --publish flag → every action prefixed `[dry-run]`).
2. --publish without GH_TOKEN OR DISCORD_WEBHOOK_URL → exit 2.
3. All 4 stages present (t-30, t+0, t+5, t+24h).
4. Header mentions P78 timing recommendation (09:00 EST).
"""
from __future__ import annotations

import os
import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dayzero" / "launch_trigger.sh"


def _run(args: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    full_env = dict(os.environ)
    if env is not None:
        full_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=full_env,
        timeout=15,
    )


def test_launch_trigger_script_present():
    assert SCRIPT.is_file()
    assert SCRIPT.stat().st_mode & 0o111, "must be executable"


def test_launch_trigger_default_dry_run():
    result = _run(["--stage", "t+0"])
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    combined = result.stdout + result.stderr
    assert "[dry-run]" in combined
    assert "[publish]" not in combined


def test_launch_trigger_publish_requires_gh_token():
    env = {"GH_TOKEN": "", "DISCORD_WEBHOOK_URL": "https://discord/test"}
    result = _run(["--stage", "t+0", "--publish"], env=env)
    assert result.returncode == 2, f"expected exit 2; got {result.returncode}"
    assert "GH_TOKEN" in result.stderr


def test_launch_trigger_publish_requires_discord_webhook():
    env = {"GH_TOKEN": "tok", "DISCORD_WEBHOOK_URL": ""}
    result = _run(["--stage", "t+0", "--publish"], env=env)
    assert result.returncode == 2
    assert "DISCORD_WEBHOOK_URL" in result.stderr


def test_launch_trigger_all_stages_present():
    text = SCRIPT.read_text()
    for stage in ("t-30)", "t+0)", "t+5)", "t+24h)"):
        assert stage in text, f"missing stage branch: {stage}"


def test_launch_trigger_recommends_p78_window():
    text = SCRIPT.read_text()
    assert "09:00 EST" in text, "P78 timing recommendation absent"
    assert "P78" in text


def test_launch_copy_files_present():
    copy_dir = ROOT / "scripts" / "dayzero" / "launch_copy"
    assert copy_dir.is_dir()
    for platform in ("twitter", "instagram", "linkedin", "reddit"):
        assert (copy_dir / f"{platform}.txt").is_file(), f"missing {platform}.txt"
