# SPDX-License-Identifier: Apache-2.0
"""Phase 45 / Plan 45-01 — INSTALL-VM matrix runner contract tests.

Pins the `scripts/dist/install_vm_matrix.sh` + `install_vm_matrix.json`
contract for SHIP-04 (matrix runner) and SHIP-05 install-budget gate.

All tests are zero-network: `tart` is never invoked. When `--live` is
exercised it's against a PATH-shimmed `tart` that writes to a marker
file so the test can assert non-invocation (or the expected shim path).

Test layout:
- Tests 1-6  (Task 1): JSON schema + bash header + --help / unknown-flag
                       contract + default dry-run output shape.
- Tests 7-11 (Task 2): full per-row screenshot/timing capture loop +
                       --live exit codes + skip semantics + run.json.
- Tests 12-16 (Task 3): install-budget gate fail/pass/skip/quiet paths.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MATRIX_JSON = REPO_ROOT / "scripts" / "dist" / "install_vm_matrix.json"
MATRIX_SH = REPO_ROOT / "scripts" / "dist" / "install_vm_matrix.sh"

CANONICAL_ROWS = {
    ("macos", "12.3"),
    ("macos", "14"),
    ("macos", "15"),
    ("windows", "10"),
    ("windows", "11"),
}


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


def _run(args, *, env_extra=None, check=False, cwd=REPO_ROOT):
    """Run `install_vm_matrix.sh` with the given args. Returns CompletedProcess."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        ["bash", str(MATRIX_SH), *args],
        capture_output=True,
        text=True,
        check=check,
        env=env,
        cwd=str(cwd),
    )


def _tart_shim_dir(tmp_path: Path, *, marker: Path, exit_code: int = 0) -> Path:
    """Create a `tart` shim on a fresh dir so tests can prepend it to PATH.

    The shim:
      - writes its argv to ``marker`` (one line per invocation, appended)
      - exits with ``exit_code`` (default 0)
    """
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir(parents=True, exist_ok=True)
    shim = shim_dir / "tart"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "$@" >> "{marker}"\n'
        f"exit {exit_code}\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return shim_dir


# =============================================================================
# Task 1 — Tests 1-6: schema + CLI contract
# =============================================================================


def test_1_matrix_json_parses_with_required_fields():
    """Test 1: install_vm_matrix.json exists, valid JSON, has expected top-level keys."""
    assert MATRIX_JSON.exists(), f"missing {MATRIX_JSON}"
    data = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
    assert isinstance(data.get("version"), int), "version must be int"
    assert data["version"] == 1, "expected version=1"
    assert isinstance(data.get("default_max_install_ms"), int)
    assert data["default_max_install_ms"] == 600000
    assert data["install_ms_budget"] == 600000
    assert isinstance(data.get("rows"), list)
    assert len(data["rows"]) == 5, f"expected 5 rows, got {len(data['rows'])}"


def test_2_each_row_has_required_shape():
    """Test 2: every row has the fields needed to prove full first-install smoke."""
    data = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
    required = {"os", "version", "tart_image", "expected_steps", "max_install_ms"}
    for r in data["rows"]:
        missing = required - set(r.keys())
        assert not missing, f"row missing keys: {missing} in {r}"
        assert r["os"] in {"macos", "windows"}, f"unexpected os: {r['os']}"
        assert isinstance(r["expected_steps"], list)
        assert len(r["expected_steps"]) > 0, "expected_steps must be non-empty"
        assert isinstance(r["max_install_ms"], int)
        assert r["max_install_ms"] == 600000


def test_2b_matrix_steps_include_models_library_and_agentic_engine():
    """The VM matrix must exercise the product beyond the old wizard path."""
    data = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
    required_steps = {
        "required-models",
        "viber-setup",
        "library-search",
        "library-chat",
        "build-set",
        "first-reaction",
    }
    for r in data["rows"]:
        steps = set(r["expected_steps"])
        missing = required_steps - steps
        assert not missing, f"{r['os']}-{r['version']} missing steps: {missing}"


def test_3_matrix_rows_match_canonical_os_versions():
    """Test 3: set of (os, version) tuples = CONTEXT §INSTALL-VM canonical 5."""
    data = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
    actual = {(r["os"], r["version"]) for r in data["rows"]}
    assert actual == CANONICAL_ROWS, f"row set diverged: {actual} != {CANONICAL_ROWS}"


def test_4_matrix_sh_is_executable_and_syntax_clean():
    """Test 4: install_vm_matrix.sh exists, executable, `bash -n` clean, has strict header."""
    assert MATRIX_SH.exists()
    # Executable bit
    mode = MATRIX_SH.stat().st_mode
    assert mode & 0o111, f"install_vm_matrix.sh not executable (mode={oct(mode)})"
    # bash -n syntax check
    rc = subprocess.run(["bash", "-n", str(MATRIX_SH)], capture_output=True, text=True)
    assert rc.returncode == 0, f"bash -n failed: {rc.stderr}"
    # Strict-mode header — must be present, and must be the first non-comment,
    # non-blank statement (so it's actually in effect for the whole script).
    text = MATRIX_SH.read_text(encoding="utf-8")
    assert "set -euo pipefail" in text, "missing `set -euo pipefail` header"
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert stripped == "set -euo pipefail", (
            f"first non-comment line is not `set -euo pipefail`, got: {stripped!r}"
        )
        break


def test_4b_matrix_runner_names_current_install_artifacts():
    """Install VM comments must not regress to the old Windows MSI wording."""
    text = MATRIX_SH.read_text(encoding="utf-8")
    assert "DMG / Windows installer EXE" in text
    assert "DMG/MSI" not in text


def test_4c_matrix_runner_latest_run_lookup_is_linux_portable():
    """The GitHub workflow runs on ubuntu-latest, so avoid BSD-only stat flags."""
    text = MATRIX_SH.read_text(encoding="utf-8")
    assert "stat -f" not in text
    assert 'root.glob("*/run.json")' in text


def test_5_help_exits_zero_and_lists_flags():
    """Test 5: --help exits 0 and references each flag."""
    res = _run(["--help"])
    assert res.returncode == 0, f"--help exit={res.returncode}: {res.stderr}"
    out = res.stdout
    for needle in [
        "--check-install-budget",
        "--check-60s",
        "--live",
        "--matrix",
        "--run-id",
        "--quiet",
    ]:
        assert needle in out, f"--help missing reference to {needle!r}\nGOT:\n{out}"


def test_6_default_dry_run_prints_plan_lines_and_no_tart_invocation(tmp_path: Path):
    """Test 6: default invocation → exit 0, [plan] tart {clone,run,stop} lines per row,
    no actual `tart` invocation (PATH-shimmed marker file remains absent)."""
    marker = tmp_path / "tart-invocations.log"
    shim_dir = _tart_shim_dir(tmp_path, marker=marker, exit_code=0)
    env = {"PATH": f"{shim_dir}:{os.environ['PATH']}"}
    res = _run([], env_extra=env)
    assert res.returncode == 0, f"default run exit={res.returncode}: {res.stderr}"
    # NEVER invoked tart in dry-run mode.
    assert not marker.exists(), (
        f"tart was invoked in dry-run mode (marker exists at {marker}):\n"
        f"{marker.read_text() if marker.exists() else ''}"
    )
    # Per-row dry-run plan lines for the full lifecycle.
    data = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
    for r in data["rows"]:
        tag = f"{r['os']}-{r['version']}"
        for verb in ("clone", "run", "stop"):
            needle = f"[plan] tart {verb}"
            assert needle in res.stdout, (
                f"missing dry-run plan line `{needle}` for row {tag}\n"
                f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            )


def test_6b_unknown_flag_exits_2():
    """Test 6 (split): unknown flag → exit 2 (usage error)."""
    res = _run(["--no-such-flag"])
    assert res.returncode == 2, f"expected exit 2, got {res.returncode}: {res.stderr}"


# =============================================================================
# Task 2 — Tests 7-11: dry-run loop + --live + skip semantics + run.json
# =============================================================================


def test_7_dry_run_emits_screenshot_plan_per_step(tmp_path: Path):
    """Test 7: dry-run emits `[plan] tart screenshot --output ...wizard-step-{N}.png`
    for each expected_steps entry per row, plus clone + run + stop; tart never invoked."""
    marker = tmp_path / "tart-invocations.log"
    shim_dir = _tart_shim_dir(tmp_path, marker=marker, exit_code=0)
    env = {"PATH": f"{shim_dir}:{os.environ['PATH']}"}
    run_id = "2026-05-17T00-00-00Z"
    res = _run(["--run-id", run_id], env_extra=env)
    assert res.returncode == 0
    assert not marker.exists(), "tart invoked in dry-run mode"
    data = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
    for r in data["rows"]:
        tag = f"{r['os']}-{r['version']}"
        assert f"[plan] tart clone {r['tart_image']}" in res.stdout
        for verb in ("run", "stop"):
            assert f"[plan] tart {verb}" in res.stdout
        # One screenshot plan line per expected step.
        for i, _step in enumerate(r["expected_steps"], start=1):
            expected_path_frag = (
                f"install-vm-runs/{run_id}/install-vm-{r['os']}-{r['version']}-wizard-step-{i}.png"
            )
            assert (
                "[plan] tart screenshot" in res.stdout
                and expected_path_frag in res.stdout
            ), (
                f"missing screenshot plan for row {tag} step {i}; "
                f"expected fragment: {expected_path_frag}\n"
                f"STDOUT:\n{res.stdout}"
            )


def test_8_live_without_tart_exits_3(tmp_path: Path):
    """Test 8: --live without `tart` on PATH → exit 3 + brew hint on stderr."""
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    for tool in (
        "python3",
        "bash",
        "sh",
        "rm",
        "cat",
        "echo",
        "mkdir",
        "mv",
        "date",
        "dirname",
        "sed",
        "grep",
        "awk",
        "find",
        "ls",
        "cp",
        "chmod",
        "true",
        "false",
        "tr",
        "head",
        "tail",
        "sort",
        "uname",
    ):
        src = shutil.which(tool)
        if src:
            (empty_bin / tool).symlink_to(src)
    env = {"PATH": str(empty_bin)}
    res = _run(["--live"], env_extra=env)
    assert res.returncode == 3, (
        f"expected exit 3 when tart absent, got {res.returncode}\n"
        f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    )
    assert "tart" in res.stderr.lower()
    assert "brew install" in res.stderr, "expected brew install hint on stderr"


def test_9_live_with_image_missing_skips_row_records_reason(tmp_path: Path):
    """Test 9: --live with `tart` shimmed to exit 1 (image missing) → all rows
    recorded as status=skipped + skip_reason=tart_image_missing in run.json; exit 0."""
    marker = tmp_path / "tart-invocations.log"
    shim_dir = _tart_shim_dir(tmp_path, marker=marker, exit_code=1)
    env = {"PATH": f"{shim_dir}:{os.environ['PATH']}"}
    run_id = "2026-05-17T00-00-09Z"
    res = _run(["--live", "--run-id", run_id], env_extra=env)
    assert res.returncode == 0, (
        f"expected exit 0 with all-skipped, got {res.returncode}\n"
        f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    )
    run_json = REPO_ROOT / "dist" / "install-vm-runs" / run_id / "run.json"
    try:
        assert run_json.exists(), f"run.json not written at {run_json}"
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert len(data["rows"]) == 5
        for row in data["rows"]:
            assert row["status"] == "skipped"
            assert row["skip_reason"] == "tart_image_missing"
    finally:
        if run_json.parent.exists():
            shutil.rmtree(run_json.parent)


def test_10_run_json_index_has_required_schema(tmp_path: Path):
    """Test 10: run.json index written with expected schema; run_id auto-generated
    when --run-id is absent (UTC YYYY-MM-DDTHH-MM-SSZ format)."""
    marker = tmp_path / "tart-invocations.log"
    shim_dir = _tart_shim_dir(tmp_path, marker=marker, exit_code=1)
    env = {"PATH": f"{shim_dir}:{os.environ['PATH']}"}
    runs_root = REPO_ROOT / "dist" / "install-vm-runs"
    before = set()
    if runs_root.exists():
        before = {p.name for p in runs_root.iterdir() if p.is_dir()}
    created_dirs: list[Path] = []
    res = _run(["--live"], env_extra=env)
    assert res.returncode == 0, f"expected exit 0, got {res.returncode}: {res.stderr}"

    try:
        assert runs_root.exists(), "runs root missing"
        created_dirs = [
            p for p in runs_root.iterdir() if p.is_dir() and p.name not in before
        ]
        assert created_dirs, "no run dirs created"
        latest = max(created_dirs, key=lambda p: p.stat().st_mtime)
        assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z$", latest.name), (
            f"run_id format unexpected: {latest.name}"
        )
        run_json = latest / "run.json"
        assert run_json.exists()
        data = json.loads(run_json.read_text(encoding="utf-8"))
        for k in ("run_id", "started_at", "matrix_version", "rows"):
            assert k in data, f"run.json missing key: {k}"
        for row in data["rows"]:
            for k in (
                "os",
                "version",
                "status",
                "screenshots",
                "timing_dump",
                "total_ms",
                "exceeded_max_ms",
                "skip_reason",
            ):
                assert k in row, f"row missing key: {k}"
    finally:
        for p in created_dirs:
            if p.exists():
                shutil.rmtree(p)


def test_11_timing_dump_merged_into_run_json(tmp_path: Path):
    """Test 11: per-row timing JSON merged into run.json `total_ms` when present
    at the expected VM-output path; missing dump → total_ms: null, exceeded_max_ms: false."""
    marker = tmp_path / "tart-invocations.log"
    shim_dir = _tart_shim_dir(tmp_path, marker=marker, exit_code=1)
    env = {"PATH": f"{shim_dir}:{os.environ['PATH']}"}
    run_id = "2026-05-17T00-00-11Z"
    runs_root = REPO_ROOT / "dist" / "install-vm-runs"
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "macos-14-install-vm-timing.json").write_text(
        json.dumps({"totalMs": 412000, "steps": []}),
        encoding="utf-8",
    )
    try:
        res = _run(["--live", "--run-id", run_id], env_extra=env)
        assert res.returncode == 0, f"unexpected exit: {res.returncode}: {res.stderr}"
        run_json = run_dir / "run.json"
        data = json.loads(run_json.read_text(encoding="utf-8"))
        rows_by_tag = {(r["os"], r["version"]): r for r in data["rows"]}
        macos14 = rows_by_tag[("macos", "14")]
        assert macos14["total_ms"] == 412000
        assert macos14["exceeded_max_ms"] is False
        win11 = rows_by_tag[("windows", "11")]
        assert win11["total_ms"] is None
        assert win11["exceeded_max_ms"] is False
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)


# =============================================================================
# Task 3 — Tests 12-16: install-budget gate
# =============================================================================


def _write_fixture_run(runs_root: Path, run_id: str, rows: list) -> Path:
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "started_at": f"{run_id[:10]}T{run_id[11:13]}:{run_id[14:16]}:{run_id[17:19]}Z",
        "matrix_version": 1,
        "rows": rows,
    }
    (run_dir / "run.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return run_dir


def _ok_row(os_name: str, ver: str, total_ms: int) -> dict:
    return {
        "os": os_name,
        "version": ver,
        "status": "ok",
        "screenshots": [],
        "timing_dump": f"{os_name}-{ver}-install-vm-timing.json",
        "total_ms": total_ms,
        "install_ms": total_ms,
        "onboarding_ms": total_ms,
        "max_install_ms": 600000,
        "max_onboarding_ms": 600000,
        "exceeded_max_ms": total_ms > 600000,
        "skip_reason": None,
    }


def _skipped_row(os_name: str, ver: str) -> dict:
    return {
        "os": os_name,
        "version": ver,
        "status": "skipped",
        "screenshots": [],
        "timing_dump": None,
        "total_ms": None,
        "install_ms": None,
        "onboarding_ms": None,
        "max_install_ms": 600000,
        "max_onboarding_ms": 600000,
        "exceeded_max_ms": False,
        "skip_reason": "tart_image_missing",
    }


def test_12_check_60s_with_no_runs_exits_1():
    """Test 12: budget check with no dist/install-vm-runs/ → exit 1 + clear stderr."""
    runs_root = REPO_ROOT / "dist" / "install-vm-runs"
    backup = None
    if runs_root.exists():
        backup = runs_root.parent / "install-vm-runs.test12.bak"
        shutil.move(str(runs_root), str(backup))
    try:
        res = _run(["--check-install-budget"])
        assert res.returncode == 1, (
            f"expected exit 1 when no runs, got {res.returncode}\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
        assert "no runs" in res.stderr.lower()
        assert "--live" in res.stderr
    finally:
        if backup is not None and backup.exists():
            if runs_root.exists():
                shutil.rmtree(runs_root)
            shutil.move(str(backup), str(runs_root))


def test_13_check_60s_all_pass_exits_0():
    """Test 13: all rows total_ms <= max → exit 0 + OK summary on stdout."""
    runs_root = REPO_ROOT / "dist" / "install-vm-runs"
    run_id = "2026-05-17T00-00-13Z"
    rows = [
        _ok_row("macos", "12.3", 400000),
        _ok_row("macos", "14", 412000),
        _ok_row("macos", "15", 380000),
        _ok_row("windows", "10", 490000),
        _ok_row("windows", "11", 550000),
    ]
    run_dir = _write_fixture_run(runs_root, run_id, rows)
    try:
        res = _run(["--check-install-budget"])
        assert res.returncode == 0, (
            f"expected exit 0 for all-pass, got {res.returncode}\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
        assert "OK" in res.stdout
        assert "5/5" in res.stdout
        assert "600000" in res.stdout
    finally:
        shutil.rmtree(run_dir)


def test_14_check_60s_one_exceeds_exits_1():
    """Test 14: one row > max_install_ms → exit 1 + BLOCKED line on stderr."""
    runs_root = REPO_ROOT / "dist" / "install-vm-runs"
    run_id = "2026-05-17T00-00-14Z"
    rows = [
        _ok_row("macos", "12.3", 400000),
        _ok_row("macos", "14", 412000),
        _ok_row("macos", "15", 380000),
        _ok_row("windows", "10", 490000),
        _ok_row("windows", "11", 780000),
    ]
    run_dir = _write_fixture_run(runs_root, run_id, rows)
    try:
        res = _run(["--check-install-budget"])
        assert res.returncode == 1, (
            f"expected exit 1, got {res.returncode}\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
        assert "BLOCKED" in res.stderr
        assert "windows-11" in res.stderr
        assert "780000" in res.stderr
        assert "600000" in res.stderr
    finally:
        shutil.rmtree(run_dir)


def test_15_check_60s_all_skipped_exits_0_with_warn():
    """Test 15: all rows skipped (zero VMs present) → exit 0 + autonomous-degraded WARN."""
    runs_root = REPO_ROOT / "dist" / "install-vm-runs"
    run_id = "2026-05-17T00-00-15Z"
    rows = [
        _skipped_row("macos", "12.3"),
        _skipped_row("macos", "14"),
        _skipped_row("macos", "15"),
        _skipped_row("windows", "10"),
        _skipped_row("windows", "11"),
    ]
    run_dir = _write_fixture_run(runs_root, run_id, rows)
    try:
        res = _run(["--check-install-budget"])
        assert res.returncode == 0, (
            f"expected exit 0 (autonomous-degraded), got {res.returncode}\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
        full = res.stdout + res.stderr
        assert "WARN" in full
        assert "skipped" in full.lower()
        assert "SHIP-04" in full
    finally:
        shutil.rmtree(run_dir)


def test_16_check_60s_quiet_suppresses_stdout_but_keeps_stderr():
    """Test 16: budget check --quiet → stdout suppressed on OK path; stderr kept on failure path."""
    runs_root = REPO_ROOT / "dist" / "install-vm-runs"
    run_id = "2026-05-17T00-00-16Z"
    rows = [
        _ok_row("macos", "12.3", 400000),
        _ok_row("macos", "14", 412000),
        _ok_row("macos", "15", 380000),
        _ok_row("windows", "10", 490000),
        _ok_row("windows", "11", 550000),
    ]
    run_dir = _write_fixture_run(runs_root, run_id, rows)
    try:
        res = _run(["--check-install-budget", "--quiet"])
        assert res.returncode == 0
        assert res.stdout.strip() == "", (
            f"expected empty stdout under --quiet, got: {res.stdout!r}"
        )
    finally:
        shutil.rmtree(run_dir)

    run_id2 = "2026-05-17T00-00-16Z-fail"
    rows_fail = [
        _ok_row("macos", "12.3", 400000),
        _ok_row("macos", "14", 412000),
        _ok_row("macos", "15", 380000),
        _ok_row("windows", "10", 490000),
        _ok_row("windows", "11", 780000),
    ]
    run_dir2 = _write_fixture_run(runs_root, run_id2, rows_fail)
    try:
        res = _run(["--check-install-budget", "--quiet"])
        assert res.returncode == 1
        assert "BLOCKED" in res.stderr, (
            f"expected BLOCKED on stderr under --quiet failure, got stderr:\n{res.stderr}"
        )
    finally:
        shutil.rmtree(run_dir2)


def test_17_simulate_writes_install_budget_run_shape():
    """--simulate must write a concrete run.json consumed by the budget gate."""
    runs_root = REPO_ROOT / "dist" / "install-vm-runs"
    run_id = "2026-05-17T00-00-17Z-sim"
    run_dir = runs_root / run_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    try:
        res = _run(["--simulate", "--check-install-budget", "--run-id", run_id, "--quiet"])
        assert res.returncode == 0, (
            f"expected simulated budget check to pass, got {res.returncode}\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
        run_json = run_dir / "run.json"
        assert run_json.exists(), f"missing simulated run.json at {run_json}"
        data = json.loads(run_json.read_text(encoding="utf-8"))
        assert data["run_id"] == run_id
        assert data["install_ms_budget"] == 600000
        assert data["onboarding_ms_budget"] == 600000
        assert len(data["rows"]) == 5
        for row in data["rows"]:
            assert row["status"] == "ok"
            assert row["simulated"] is True
            assert row["install_ms"] == row["total_ms"]
            assert row["onboarding_ms"] == row["total_ms"]
            assert row["max_install_ms"] == 600000
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)
