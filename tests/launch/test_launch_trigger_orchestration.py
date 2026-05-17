# SPDX-License-Identifier: Apache-2.0
"""Phase 45 / Plan 45-02 — launch_trigger.sh orchestration contract.

REQ-IDs: SHIP-08

Pins the launch_trigger.sh + cadence_index.json contract:

Task 1 (RED):
  1. cadence_index.json schema (version, stages order, channels keys, values).
  2. Every non-null copy_file references an existing scripts/dayzero/launch_copy file.
  3. launch_trigger.sh exists + executable + bash -n clean.
  4. --help exits 0 + references the 5 flags.
  5. Unknown flag → exit 2.
  6. Missing --phase → exit 2 + named blocker. Invalid phase → exit 2 + lists valid set.

Task 2 (GREEN-loop):
  7-10. Per-phase routing: T+0 = 5 [plan] lines, T-30 = 3, T+5h = 2, T+24h = 4.
  11. Zero-network in dry-run (subordinate PATH-shim assertion).
  12. --live without LAUNCH_REAL=1 → exit 2.
  13. check_no_ai_slop pre-publish gate (PATH-shim fail/pass).
  14. JSONL audit log writes one row per [plan] line.

Task 3 (GREEN-live):
  15. --live missing GITHUB_TOKEN → exit 2.
  16. --live missing DISCORD_WEBHOOK_URL → exit 2.
  17. Sign-off footer regex per Plan 44-05 lock (Kaan signature: + Francesco signature:).
  18. --live end-to-end with all env + shimmed subordinates → JSONL records mode: "live".
  19. GH Actions ::error:: annotation lines on failure.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "launch" / "launch_trigger.sh"
CADENCE_INDEX = REPO_ROOT / "scripts" / "dayzero" / "launch_copy" / "cadence_index.json"
LAUNCH_COPY_DIR = REPO_ROOT / "scripts" / "dayzero" / "launch_copy"

EXPECTED_STAGES: list[str] = ["T-30", "T+0", "T+5h", "T+24h"]
EXPECTED_CHANNELS: set[str] = {"twitter", "instagram", "linkedin", "reddit", "discord"}

# Per-stage expected non-null channel sets (= which channels publish at each cadence).
EXPECTED_PUBLISH_SET: dict[str, set[str]] = {
    "T-30":  {"twitter", "instagram", "discord"},
    "T+0":   {"twitter", "instagram", "linkedin", "reddit", "discord"},
    "T+5h":  {"twitter", "discord"},
    "T+24h": {"twitter", "instagram", "linkedin", "discord"},
}


# ---------------------------------------------------------------------------
# Task 1: cadence_index.json + CLI surface
# ---------------------------------------------------------------------------


def test_01_cadence_index_schema() -> None:
    """cadence_index.json: version=1, stages list in canonical order."""
    assert CADENCE_INDEX.exists(), f"cadence_index.json missing at {CADENCE_INDEX}"
    data = json.loads(CADENCE_INDEX.read_text(encoding="utf-8"))
    assert data["version"] == 1, f"version must be 1, got {data.get('version')}"
    assert data["stages"] == EXPECTED_STAGES, (
        f"stages must be {EXPECTED_STAGES} in order, got {data.get('stages')}"
    )


def test_02_cadence_index_channels_shape() -> None:
    """channels has exactly the 5 keys; every value is a dict with all 4 stage keys."""
    data = json.loads(CADENCE_INDEX.read_text(encoding="utf-8"))
    assert set(data["channels"]) == EXPECTED_CHANNELS, (
        f"channels keys must be {EXPECTED_CHANNELS}, got {set(data['channels'])}"
    )
    for channel, row in data["channels"].items():
        assert set(row.keys()) == set(EXPECTED_STAGES), (
            f"channel {channel} must declare all 4 stages, got {set(row.keys())}"
        )
        for stage, value in row.items():
            assert value is None or isinstance(value, str), (
                f"channel {channel} stage {stage} must be str|null, got {type(value)}"
            )


def test_03_cadence_index_references_existing_copy_files() -> None:
    """Every non-null filename in cadence_index.json corresponds to an existing copy file."""
    data = json.loads(CADENCE_INDEX.read_text(encoding="utf-8"))
    for channel, row in data["channels"].items():
        for stage, filename in row.items():
            if filename is None:
                continue
            path = LAUNCH_COPY_DIR / filename
            assert path.exists(), (
                f"cadence_index.json references {filename} for "
                f"{channel}/{stage} but {path} does not exist "
                f"(Plan 44-05 lock)"
            )


def test_04_script_exists_executable_and_syntax_clean() -> None:
    """launch_trigger.sh must exist, be executable, and bash -n clean."""
    assert SCRIPT.exists(), f"launch_trigger.sh missing at {SCRIPT}"
    mode = SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, (
        f"launch_trigger.sh must be executable (got mode 0o{mode & 0o777:o}); "
        f"run `chmod +x {SCRIPT.relative_to(REPO_ROOT)}`"
    )
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"bash -n failed: {result.stderr}"
    )


def test_05_help_exits_zero_lists_all_flags() -> None:
    """--help exits 0 and references the 5 flags."""
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"--help must exit 0, got {result.returncode}; stderr={result.stderr}"
    )
    combined = result.stdout + result.stderr
    for flag in ("--phase", "--live", "--cadence-index", "--copy-dir", "--quiet"):
        assert flag in combined, f"--help output must reference {flag}"


def test_06a_unknown_flag_exits_two() -> None:
    """Unknown flag → exit 2."""
    result = subprocess.run(
        ["bash", str(SCRIPT), "--bogus-flag"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (
        f"unknown flag must exit 2, got {result.returncode}"
    )


def test_06b_missing_phase_exits_two_with_named_blocker() -> None:
    """Missing --phase → exit 2 with stderr naming the valid phase set."""
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (
        f"missing --phase must exit 2, got {result.returncode}"
    )
    assert "--phase required" in result.stderr, (
        f"stderr must name '--phase required'; got: {result.stderr}"
    )
    for phase in EXPECTED_STAGES:
        assert phase in result.stderr, (
            f"stderr must list valid phase {phase}; got: {result.stderr}"
        )


def test_06c_invalid_phase_exits_two_with_valid_list() -> None:
    """Invalid --phase value → exit 2 + stderr lists the valid set."""
    result = subprocess.run(
        ["bash", str(SCRIPT), "--phase", "T-1d"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (
        f"invalid --phase must exit 2, got {result.returncode}"
    )
    for phase in EXPECTED_STAGES:
        assert phase in result.stderr, (
            f"stderr must list valid phase {phase}; got: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# Task 2: dry-run orchestration loop + zero-network pin
# ---------------------------------------------------------------------------


def _make_shim_dir(
    tmp_path: Path,
    *,
    slop_exit: int = 0,
    record: Path | None = None,
) -> Path:
    """Build a PATH-shim dir with stubbed check_no_ai_slop.py /
    publish_social_posts.py / post_discord_launch.py that record their
    argv into ``record`` and exit ``slop_exit`` for the slop check.

    The shim writes records as JSONL: {"name": "<shim>", "argv": [...]}
    Other shims always exit 0 (their job is to record, not actually publish).
    """
    shim_dir = tmp_path / "shim"
    shim_dir.mkdir(parents=True, exist_ok=True)
    record = record or (tmp_path / "shim_record.jsonl")

    py = sys.executable

    # Note: shims live in shim_dir but launch_trigger.sh calls subordinates by
    # absolute path (REPO_ROOT/scripts/launch/<name>). The shim dir gets the
    # tests in by overriding the PATH used inside the bash script — see
    # _run() below which passes --shim-dir as an override.
    for name in ("check_no_ai_slop.py", "publish_social_posts.py", "post_discord_launch.py"):
        target = shim_dir / name
        exit_code = slop_exit if name == "check_no_ai_slop.py" else 0
        target.write_text(textwrap.dedent(f"""\
            #!{py}
            import json, sys
            from pathlib import Path
            rec = Path({str(record)!r})
            rec.parent.mkdir(parents=True, exist_ok=True)
            with open(rec, 'a') as f:
                f.write(json.dumps({{"name": {name!r}, "argv": sys.argv[1:]}}) + chr(10))
            sys.exit({exit_code})
        """))
        target.chmod(0o755)
    return shim_dir


def _read_shim_records(record: Path) -> list[dict]:
    if not record.exists():
        return []
    return [json.loads(line) for line in record.read_text().splitlines() if line.strip()]


def _run(
    *args: str,
    env: dict | None = None,
    cwd: Path | None = None,
    shim_dir: Path | None = None,
) -> subprocess.CompletedProcess:
    """Run launch_trigger.sh with optional env + shim-dir override.

    When ``shim_dir`` is provided, sets ``VIBEMIX_LAUNCH_SHIM_DIR`` env so
    launch_trigger.sh routes subordinate calls through the shim instead of
    the real scripts/launch/*.py. This is the contract the script honors
    for testability (Task 2 implements it).
    """
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    if shim_dir is not None:
        full_env["VIBEMIX_LAUNCH_SHIM_DIR"] = str(shim_dir)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(cwd or REPO_ROOT),
    )


@pytest.mark.parametrize("phase,expected", list(EXPECTED_PUBLISH_SET.items()))
def test_07_to_10_per_phase_plan_lines(
    tmp_path: Path,
    phase: str,
    expected: set[str],
) -> None:
    """For each phase, dry-run produces a [plan] line per expected channel."""
    shim = _make_shim_dir(tmp_path)
    result = _run(
        "--phase", phase,
        env={"VIBEMIX_LAUNCH_RUN_DIR": str(tmp_path / "launch-runs")},
        shim_dir=shim,
    )
    assert result.returncode == 0, (
        f"dry-run --phase {phase} must exit 0; stderr={result.stderr}"
    )
    found: set[str] = set()
    for line in result.stdout.splitlines():
        if line.startswith("[plan]"):
            for channel in EXPECTED_CHANNELS:
                if f"channel={channel}" in line or f" {channel} " in line or line.endswith(channel):
                    found.add(channel)
    assert found == expected, (
        f"--phase {phase}: expected [plan] channels {expected}, got {found}; "
        f"stdout={result.stdout!r}"
    )


def test_11_zero_network_in_dry_run(tmp_path: Path) -> None:
    """Dry-run does NOT attempt network — proven by unreachable http_proxy."""
    shim = _make_shim_dir(tmp_path)
    result = _run(
        "--phase", "T+0",
        env={
            "http_proxy": "http://127.0.0.1:1",
            "https_proxy": "http://127.0.0.1:1",
            "VIBEMIX_LAUNCH_RUN_DIR": str(tmp_path / "launch-runs"),
        },
        shim_dir=shim,
    )
    assert result.returncode == 0, (
        f"dry-run with unreachable proxy must still exit 0; stderr={result.stderr}"
    )
    # Subordinates were invoked with --dry-run, never --real.
    records = _read_shim_records(tmp_path / "shim_record.jsonl")
    publish_records = [r for r in records if r["name"] == "publish_social_posts.py"]
    discord_records = [r for r in records if r["name"] == "post_discord_launch.py"]
    assert publish_records, "publish_social_posts shim never invoked"
    assert discord_records, "post_discord_launch shim never invoked"
    for r in publish_records + discord_records:
        assert "--dry-run" in r["argv"], (
            f"subordinate {r['name']} must be invoked with --dry-run in dry-run mode; "
            f"argv={r['argv']}"
        )
        assert "--real" not in r["argv"], (
            f"subordinate {r['name']} must NOT receive --real in dry-run; "
            f"argv={r['argv']}"
        )


def test_12_live_without_launch_real_exits_two(tmp_path: Path) -> None:
    """--live without LAUNCH_REAL=1 → exit 2 + named stderr."""
    # Strip LAUNCH_REAL from env if it's set in the test runner.
    env = {k: v for k, v in os.environ.items() if k != "LAUNCH_REAL"}
    env["VIBEMIX_LAUNCH_RUN_DIR"] = str(tmp_path / "launch-runs")
    shim = _make_shim_dir(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--phase", "T+0", "--live"],
        capture_output=True,
        text=True,
        env={**env, "VIBEMIX_LAUNCH_SHIM_DIR": str(shim)},
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2, (
        f"--live without LAUNCH_REAL must exit 2, got {result.returncode}; "
        f"stderr={result.stderr}"
    )
    assert "LAUNCH_REAL" in result.stderr, (
        f"stderr must reference LAUNCH_REAL; got: {result.stderr}"
    )


def test_13a_slop_check_failure_aborts(tmp_path: Path) -> None:
    """If check_no_ai_slop shim exits non-zero, launch_trigger aborts with 2."""
    shim = _make_shim_dir(tmp_path, slop_exit=1)
    result = _run(
        "--phase", "T+0",
        env={"VIBEMIX_LAUNCH_RUN_DIR": str(tmp_path / "launch-runs")},
        shim_dir=shim,
    )
    assert result.returncode == 2, (
        f"slop fail must abort with exit 2, got {result.returncode}; "
        f"stderr={result.stderr}"
    )
    assert "slop" in result.stderr.lower() or "AI-slop" in result.stderr, (
        f"stderr must reference slop gate; got: {result.stderr}"
    )


def test_13b_slop_check_pass_proceeds(tmp_path: Path) -> None:
    """If check_no_ai_slop shim exits 0, the loop runs."""
    shim = _make_shim_dir(tmp_path, slop_exit=0)
    result = _run(
        "--phase", "T+0",
        env={"VIBEMIX_LAUNCH_RUN_DIR": str(tmp_path / "launch-runs")},
        shim_dir=shim,
    )
    assert result.returncode == 0, (
        f"slop pass must exit 0; stderr={result.stderr}"
    )
    plan_lines = [ln for ln in result.stdout.splitlines() if ln.startswith("[plan]")]
    assert len(plan_lines) == 5, (
        f"--phase T+0 must emit 5 [plan] lines, got {len(plan_lines)}: {plan_lines}"
    )


def test_14_jsonl_audit_log_one_row_per_plan_line(tmp_path: Path) -> None:
    """Each [plan] line appends a row to dist/launch-runs/<UTC>.jsonl matching the shape."""
    run_dir = tmp_path / "launch-runs"
    shim = _make_shim_dir(tmp_path)
    result = _run(
        "--phase", "T+0",
        env={"VIBEMIX_LAUNCH_RUN_DIR": str(run_dir)},
        shim_dir=shim,
    )
    assert result.returncode == 0, f"dry-run exited {result.returncode}: {result.stderr}"
    assert run_dir.exists(), "VIBEMIX_LAUNCH_RUN_DIR must be created"
    jsonl_files = list(run_dir.glob("*.jsonl"))
    assert len(jsonl_files) == 1, (
        f"expected exactly 1 jsonl audit file under {run_dir}; got {jsonl_files}"
    )
    rows = [
        json.loads(line)
        for line in jsonl_files[0].read_text().splitlines()
        if line.strip()
    ]
    assert len(rows) == 5, (
        f"T+0 must write 5 audit rows, got {len(rows)}: {rows}"
    )
    expected_channels = EXPECTED_PUBLISH_SET["T+0"]
    seen_channels: set[str] = set()
    for row in rows:
        assert set(row.keys()) >= {"ts", "stage", "channel", "mode", "copy_file", "status"}, (
            f"audit row missing required keys; got {row}"
        )
        assert row["stage"] == "T+0", f"row stage must be T+0; got {row['stage']}"
        assert row["mode"] == "dry-run", f"dry-run mode must record 'dry-run'; got {row['mode']}"
        assert row["channel"] in expected_channels, (
            f"unexpected channel {row['channel']}; valid={expected_channels}"
        )
        seen_channels.add(row["channel"])
    assert seen_channels == expected_channels, (
        f"audit rows must cover all 5 channels; missing={expected_channels - seen_channels}"
    )


# ---------------------------------------------------------------------------
# Task 3: --live discharge contract + sign-off footer gate
# ---------------------------------------------------------------------------


def test_15_live_missing_github_token_exits_two(tmp_path: Path) -> None:
    """--live with LAUNCH_REAL=1 but no GITHUB_TOKEN → exit 2."""
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_TOKEN",)}
    env.update({
        "LAUNCH_REAL": "1",
        "DISCORD_WEBHOOK_URL": "https://example.invalid/webhook",
        "VIBEMIX_LAUNCH_RUN_DIR": str(tmp_path / "launch-runs"),
    })
    shim = _make_shim_dir(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--phase", "T+0", "--live"],
        capture_output=True,
        text=True,
        env={**env, "VIBEMIX_LAUNCH_SHIM_DIR": str(shim)},
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2, (
        f"--live without GITHUB_TOKEN must exit 2, got {result.returncode}; "
        f"stderr={result.stderr}"
    )
    assert "GITHUB_TOKEN" in result.stderr, (
        f"stderr must name GITHUB_TOKEN; got: {result.stderr}"
    )


def test_16_live_missing_discord_webhook_exits_two(tmp_path: Path) -> None:
    """--live with LAUNCH_REAL=1 + GITHUB_TOKEN but no DISCORD_WEBHOOK_URL → exit 2."""
    env = {k: v for k, v in os.environ.items() if k not in ("DISCORD_WEBHOOK_URL",)}
    env.update({
        "LAUNCH_REAL": "1",
        "GITHUB_TOKEN": "gh_fake_token_for_test",
        "VIBEMIX_LAUNCH_RUN_DIR": str(tmp_path / "launch-runs"),
    })
    shim = _make_shim_dir(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--phase", "T+0", "--live"],
        capture_output=True,
        text=True,
        env={**env, "VIBEMIX_LAUNCH_SHIM_DIR": str(shim)},
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2, (
        f"--live without DISCORD_WEBHOOK_URL must exit 2, got {result.returncode}; "
        f"stderr={result.stderr}"
    )
    assert "DISCORD_WEBHOOK_URL" in result.stderr, (
        f"stderr must name DISCORD_WEBHOOK_URL; got: {result.stderr}"
    )


def test_17_signoff_footer_gate_per_plan_44_05_lock(tmp_path: Path) -> None:
    """Each copy file under --copy-dir must contain BOTH 'Kaan signature:' and
    'Francesco signature:' markers; missing on any file → exit 2 (Plan 44-05 lock)."""
    # Build a copy-dir where 1 file is missing the Francesco marker.
    copy_dir = tmp_path / "bad-copy"
    copy_dir.mkdir()
    good = "body\n\n---\nKaan signature: ____\nFrancesco signature: ____\n"
    bad = "body\n\n---\nKaan signature: ____\n"  # missing Francesco
    (copy_dir / "twitter.txt").write_text(good)
    (copy_dir / "instagram.txt").write_text(good)
    (copy_dir / "linkedin.txt").write_text(good)
    (copy_dir / "reddit.txt").write_text(good)
    (copy_dir / "discord.txt").write_text(bad)

    # Need a cadence_index.json pointing at this dir for the resolve step to work.
    cadence = tmp_path / "cadence_index.json"
    cadence.write_text(json.dumps({
        "version": 1,
        "stages": EXPECTED_STAGES,
        "channels": {
            "twitter":   {"T-30": "twitter.txt", "T+0": "twitter.txt",   "T+5h": "twitter.txt",   "T+24h": "twitter.txt"},
            "instagram": {"T-30": "instagram.txt", "T+0": "instagram.txt", "T+5h": None,         "T+24h": "instagram.txt"},
            "linkedin":  {"T-30": None,           "T+0": "linkedin.txt",  "T+5h": None,           "T+24h": "linkedin.txt"},
            "reddit":    {"T-30": None,           "T+0": "reddit.txt",    "T+5h": None,           "T+24h": None},
            "discord":   {"T-30": "discord.txt",  "T+0": "discord.txt",   "T+5h": "discord.txt",  "T+24h": "discord.txt"},
        },
    }))

    # Use a shim that passes the slop gate so the only failure surface is the
    # sign-off footer check.
    shim = _make_shim_dir(tmp_path)
    result = _run(
        "--phase", "T+0",
        "--cadence-index", str(cadence),
        "--copy-dir", str(copy_dir),
        env={"VIBEMIX_LAUNCH_RUN_DIR": str(tmp_path / "launch-runs")},
        shim_dir=shim,
    )
    assert result.returncode == 2, (
        f"missing Francesco signature must exit 2, got {result.returncode}; "
        f"stderr={result.stderr}"
    )
    assert "sign-off" in result.stderr.lower() or "signature" in result.stderr.lower(), (
        f"stderr must reference sign-off/signature gate; got: {result.stderr}"
    )
    assert "discord.txt" in result.stderr, (
        f"stderr must name the offending file; got: {result.stderr}"
    )


def test_18_live_end_to_end_records_mode_live(tmp_path: Path) -> None:
    """--live with all preconditions met → subordinates invoked with --real;
    JSONL audit records mode: 'live'."""
    env = os.environ.copy()
    env.update({
        "LAUNCH_REAL": "1",
        "GITHUB_TOKEN": "gh_fake_test_token",
        "DISCORD_WEBHOOK_URL": "https://example.invalid/webhook",
        "VIBEMIX_LAUNCH_RUN_DIR": str(tmp_path / "launch-runs"),
    })
    shim = _make_shim_dir(tmp_path)
    env["VIBEMIX_LAUNCH_SHIM_DIR"] = str(shim)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--phase", "T+0", "--live"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"--live end-to-end must exit 0; stderr={result.stderr}"
    )

    # Subordinates received --real, not --dry-run.
    records = _read_shim_records(tmp_path / "shim_record.jsonl")
    publish_records = [r for r in records if r["name"] == "publish_social_posts.py"]
    discord_records = [r for r in records if r["name"] == "post_discord_launch.py"]
    assert publish_records, "publish_social_posts shim never invoked in --live"
    assert discord_records, "post_discord_launch shim never invoked in --live"
    for r in publish_records + discord_records:
        assert "--real" in r["argv"], (
            f"--live must invoke subordinate {r['name']} with --real; argv={r['argv']}"
        )

    # JSONL audit records mode: "live".
    run_dir = tmp_path / "launch-runs"
    jsonl_files = list(run_dir.glob("*.jsonl"))
    assert jsonl_files, f"no audit jsonl under {run_dir}"
    rows = [
        json.loads(line)
        for line in jsonl_files[0].read_text().splitlines()
        if line.strip()
    ]
    assert rows, "audit jsonl was empty"
    for row in rows:
        assert row["mode"] == "live", (
            f"--live must record mode='live'; got {row['mode']} in {row}"
        )


def test_19_gh_actions_error_annotation_on_failure(tmp_path: Path) -> None:
    """When GITHUB_ACTIONS=true, failure paths emit ::error:: annotation on stdout."""
    env = {k: v for k, v in os.environ.items() if k != "LAUNCH_REAL"}
    env.update({
        "GITHUB_ACTIONS": "true",
        "VIBEMIX_LAUNCH_RUN_DIR": str(tmp_path / "launch-runs"),
    })
    shim = _make_shim_dir(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPT), "--phase", "T+0", "--live"],
        capture_output=True,
        text=True,
        env={**env, "VIBEMIX_LAUNCH_SHIM_DIR": str(shim)},
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2, (
        f"--live without LAUNCH_REAL must exit 2 under GH Actions too; "
        f"got {result.returncode}; stderr={result.stderr}"
    )
    assert "::error::" in result.stdout, (
        "GITHUB_ACTIONS=true must emit ::error:: annotation on failure; "
        f"got stdout={result.stdout!r}"
    )
