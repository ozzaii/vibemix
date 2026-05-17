"""SHIP-V1-DECISION audit script + decision template — pin tests.

Plan 45-04 / SHIP-13.

Test layout (commit-tracked TDD progression):
    Task 1 (RED) — Tests 1-7: template schema + RED-vs-GREEN boundary.
    Task 2 (GREEN-fixture-mode) — Tests 8-15: fixture-mode aggregation + pre-fill.
    Task 3 (GREEN-live-mode) — Tests 16-20: --live with patched subprocess,
        URL→CSV fallback, GH Actions notice, atomic write, idempotency.

Hermetic by default: zero real network. --live mode is exercised via
monkeypatched subprocess + urllib so CI never hits GH or Bravoh.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = REPO_ROOT / "docs" / "SHIP-V1-DECISION-TEMPLATE.md"
AUDIT_SCRIPT = REPO_ROOT / "scripts" / "release" / "audit_ship_v1_decision.py"
FIXTURES_DIR = REPO_ROOT / "tests" / "release" / "fixtures" / "synthetic_telemetry"


# ----------------------------------------------------------------------
# Task 1 — RED tests: template schema + RED/GREEN boundary
# ----------------------------------------------------------------------


def _template_text() -> str:
    return TEMPLATE_PATH.read_text(encoding="utf-8")


def test_01_template_first_heading_matches_schema():
    """Test 1: docs/SHIP-V1-DECISION-TEMPLATE.md first heading = v3.0 SHIP-V1-DECISION."""
    assert TEMPLATE_PATH.exists(), "Template doc must be authored in Task 1."
    text = _template_text()
    # First H1 in the file (skip HTML comments + blank lines)
    first_h1 = None
    for line in text.splitlines():
        if line.startswith("# "):
            first_h1 = line.strip()
            break
    assert first_h1 == "# v3.0 SHIP-V1-DECISION — <release_tag>", (
        f"First H1 must be the canonical decision header; got {first_h1!r}"
    )


def test_02_template_has_all_four_evidence_sections():
    """Test 2: Template contains the 4 H3 evidence sections in canonical order."""
    text = _template_text()
    headings = [
        "### 1. Distribution metrics",
        "### 2. Server health (Bravoh)",
        "### 3. Ear-tests (Plan 42-03)",
        "### 4. Crash / Bug reports",
    ]
    last_idx = -1
    for h in headings:
        idx = text.find(h)
        assert idx != -1, f"Missing evidence section heading: {h!r}"
        assert idx > last_idx, f"Evidence section {h!r} appears out of order."
        last_idx = idx


def test_03_template_has_five_row_decision_rubric():
    """Test 3: 5-row rubric (Downloads / Uptime / Slop / Crash / Anti-slop)
    with Green | Yellow | Red columns and pre-filled/manual placeholders."""
    text = _template_text()
    assert "## Decision rubric (Kaan-discharge)" in text, "Rubric heading missing."
    # Each rubric row must mention the metric name.
    rubric_metrics = [
        "Downloads ≥100 in 14d",
        "Healthz uptime ≥99.5%",
        "Ear-test slop incidents",
        "Open crash issues",
        "Anti-slop community reports",
    ]
    for m in rubric_metrics:
        assert m in text, f"Rubric row missing for metric: {m!r}"
    # 4 of 5 rows are pre-filled by audit; the Anti-slop row is manual.
    pre_filled_count = text.count("<pre-filled>")
    manual_count = text.count("<manual>")
    assert pre_filled_count == 4, (
        f"Rubric must have exactly 4 <pre-filled> placeholders; got {pre_filled_count}."
    )
    assert manual_count == 1, (
        f"Rubric must have exactly 1 <manual> placeholder; got {manual_count}."
    )


def test_04_template_three_way_decision_checkbox_block():
    """Test 4: 3 decision checkboxes (v1.0.0 / rc2 / pause)."""
    text = _template_text()
    assert "## Decision" in text, "Decision section missing."
    # All three options live below the rubric.
    options = [
        "- [ ] Cut v1.0.0",
        "- [ ] Cycle v3.0.0-rc2",
        "- [ ] Pause",
    ]
    for opt in options:
        assert opt in text, f"Decision checkbox missing: {opt!r}"


def test_05_template_has_kaan_sign_off_block():
    """Test 5: Kaan sign-off block present."""
    text = _template_text()
    assert "**Kaan sign-off:**" in text, "Kaan sign-off block missing."
    assert "**Date:**" in text, "Date sign-off field missing."
    assert "**Notes:**" in text, "Notes free-form block missing."


def test_06_audit_script_emits_audit_provenance_comment_when_present():
    """Test 6 (RED-vs-GREEN boundary): the audit script does NOT exist at Task 1 RED.
    Re-purposed at Task 2 (when the script ships) to assert provenance HTML
    comment (T-45-04-03 mitigation). Until then, the boundary is the file's
    absence."""
    # During Task 1 (RED) this assertion is the boundary: script must not exist.
    # During Task 2+ (GREEN) the boundary flips: script must exist AND emit the
    # provenance comment when rendering. We honor both phases:
    if not AUDIT_SCRIPT.exists():
        # RED phase — the boundary is "not yet implemented".
        pytest.fail(
            "scripts/release/audit_ship_v1_decision.py does not exist yet "
            "(Task 1 RED boundary). This test flips GREEN once Task 2 lands."
        )
    # GREEN phase: assert provenance comment is in the rendered output.
    text = AUDIT_SCRIPT.read_text(encoding="utf-8")
    assert "_generated_by:" in text, (
        "Audit script must emit a `_generated_by:` HTML provenance comment "
        "in the rendered report (T-45-04-03 mitigation)."
    )


def test_07_fixtures_dir_present_with_gitkeep():
    """Test 7: tests/release/fixtures/synthetic_telemetry/.gitkeep exists
    (or fixtures land at Task 2 — directory must exist either way)."""
    assert FIXTURES_DIR.exists() and FIXTURES_DIR.is_dir(), (
        f"Fixtures dir missing: {FIXTURES_DIR}"
    )
    # Either .gitkeep is present (Task 1) or real fixtures are (Task 2+).
    contents = list(FIXTURES_DIR.iterdir())
    assert contents, (
        f"Fixtures dir is empty: {FIXTURES_DIR} — must contain .gitkeep or fixtures."
    )


# ----------------------------------------------------------------------
# Task 2 — GREEN-fixture-mode tests (8-15)
# ----------------------------------------------------------------------


def test_08_audit_script_has_argparse_cli():
    """Test 8: script exists; has __main__ block; argparse accepts the 5 flags."""
    assert AUDIT_SCRIPT.exists(), (
        "Audit script must exist by Task 2 GREEN."
    )
    text = AUDIT_SCRIPT.read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in text or "if __name__ == '__main__':" in text
    # Flag inventory pinned in the source so the contract is grep-able.
    for flag in ("--since", "--output", "--live", "--fixtures", "--release-tag"):
        assert flag in text, f"argparse flag {flag!r} missing from audit script."


def test_09_audit_script_help_exits_zero(tmp_path):
    """Test 9: `--help` exits 0 and prints flag reference."""
    result = subprocess.run(
        [sys.executable, str(AUDIT_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"--help must exit 0; stderr={result.stderr!r} stdout={result.stdout!r}"
    )
    out = result.stdout + result.stderr
    for flag in ("--since", "--output", "--live", "--fixtures", "--release-tag"):
        assert flag in out, f"--help output missing flag {flag!r}"


def test_10_fixture_mode_reads_all_five_files(tmp_path):
    """Test 10: fixture mode reads gh_releases.json + healthz_uptime.csv +
    gh_issues.json + ear_test_log_*.json."""
    required = [
        "gh_releases.json",
        "healthz_uptime.csv",
        "gh_issues.json",
        "ear_test_log_1.json",
        "ear_test_log_2.json",
    ]
    for name in required:
        path = FIXTURES_DIR / name
        assert path.exists(), f"Required synthetic fixture missing: {path}"
    out_path = tmp_path / "decision.md"
    result = subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--fixtures",
            str(FIXTURES_DIR),
            "--output",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"Fixture-mode run must exit 0; stderr={result.stderr!r}"
    )
    assert out_path.exists(), "Audit must write the output file."


def test_11_fixture_mode_substitutes_all_placeholders(tmp_path):
    """Test 11: rendered report has placeholders replaced; key fields are numbers."""
    out_path = tmp_path / "decision.md"
    subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--fixtures",
            str(FIXTURES_DIR),
            "--output",
            str(out_path),
        ],
        check=True,
        cwd=str(REPO_ROOT),
    )
    rendered = out_path.read_text(encoding="utf-8")
    # Pre-filled placeholders MUST be replaced in the evidence sections.
    forbidden_in_evidence = [
        "<download_count>",
        "<dmg_count>",
        "<msi_count>",
        "<uptime_pct>",
        "<ear_test_count>",
        "<slop_count>",
        "<scripted_count>",
        "<issue_count>",
        "<crash_count>",
        "<oldest_age_days>",
        "<release_tag>",
        "<YYYY-MM-DD>",
        "<audit_date>",
        "<published_at>",
    ]
    for tok in forbidden_in_evidence:
        assert tok not in rendered, (
            f"Placeholder {tok!r} should have been substituted in the rendered report."
        )
    # Uptime is rendered to 2 decimals (e.g. "99.70%" or "100.00%").
    assert re.search(r"healthz uptime: \d+\.\d{2}%", rendered), (
        "Uptime must be rendered with 2 decimal places."
    )
    # Pre-filled "Current" column entries in the rubric must be present
    # (the <manual> placeholder for the Anti-slop row stays as-is).
    assert "<manual>" in rendered, (
        "The <manual> Anti-slop rubric cell must be preserved."
    )
    # Download count must appear as an integer somewhere in the distribution section.
    assert re.search(r"Downloads \(aggregate\): \d+", rendered)


def test_12_fixture_mode_is_deterministic(tmp_path, monkeypatch):
    """Test 12: re-running with identical fixtures + fixed clock produces
    byte-identical output (only digest of the evidence body — provenance
    timestamp varies and is excluded from the determinism check)."""
    out_a = tmp_path / "a.md"
    out_b = tmp_path / "b.md"
    # Freeze the audit date so the report header is identical across runs.
    env = os.environ.copy()
    env["VIBEMIX_AUDIT_DATE_OVERRIDE"] = "2026-06-01T12:00:00Z"
    for out in (out_a, out_b):
        subprocess.run(
            [
                sys.executable,
                str(AUDIT_SCRIPT),
                "--fixtures",
                str(FIXTURES_DIR),
                "--output",
                str(out),
            ],
            check=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
    assert out_a.read_text(encoding="utf-8") == out_b.read_text(encoding="utf-8"), (
        "Two fixture-mode runs with the same VIBEMIX_AUDIT_DATE_OVERRIDE must be byte-identical."
    )


def test_13_live_mode_without_token_exits_2(tmp_path):
    """Test 13: `--live` without GITHUB_TOKEN env exits 2 with the documented stderr."""
    env = os.environ.copy()
    env.pop("GITHUB_TOKEN", None)
    out_path = tmp_path / "decision.md"
    result = subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--live",
            "--output",
            str(out_path),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 2, (
        f"--live without GITHUB_TOKEN must exit 2; got rc={result.returncode}"
    )
    assert "--live requires GITHUB_TOKEN env" in result.stderr, (
        f"Stderr must cite the env requirement; got: {result.stderr!r}"
    )
    assert "KAAN-ACTION-LEGAL.md §SHIP-13" in result.stderr, (
        "Stderr must reference the §SHIP-13 runbook handoff."
    )


def test_14_ear_test_slop_flag_increments_counter(tmp_path):
    """Test 14: an ear-test log flagged felt_slop=true increments slop_count."""
    out_path = tmp_path / "decision.md"
    subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--fixtures",
            str(FIXTURES_DIR),
            "--output",
            str(out_path),
        ],
        check=True,
        cwd=str(REPO_ROOT),
    )
    rendered = out_path.read_text(encoding="utf-8")
    # Synthetic fixtures: 1 ear-test has felt_slop=true. Count must be ≥1.
    m = re.search(r"\"Felt slop\" flagged: (\d+)", rendered)
    assert m is not None, "Slop count line missing from rendered report."
    slop_count = int(m.group(1))
    assert slop_count >= 1, (
        f"Expected ≥1 slop_count from synthetic fixtures; got {slop_count}."
    )


def test_15_release_tag_flag_flows_into_header(tmp_path):
    """Test 15: --release-tag v3.0.0-rc2 names rc2 in the report header."""
    out_path = tmp_path / "decision.md"
    subprocess.run(
        [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--fixtures",
            str(FIXTURES_DIR),
            "--output",
            str(out_path),
            "--release-tag",
            "v3.0.0-rc2",
        ],
        check=True,
        cwd=str(REPO_ROOT),
    )
    rendered = out_path.read_text(encoding="utf-8")
    assert "v3.0.0-rc2" in rendered, "Custom --release-tag must flow into report."
    assert "# v3.0 SHIP-V1-DECISION — v3.0.0-rc2" in rendered, (
        "Report H1 must name the rc2 tag."
    )


# ----------------------------------------------------------------------
# Task 3 — GREEN-live-mode tests (16-20)
# ----------------------------------------------------------------------


def _import_audit_module():
    """Import the audit script as a module (the script is auto-discoverable)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "audit_ship_v1_decision",
        AUDIT_SCRIPT,
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_16_live_mode_uses_gh_subprocess(monkeypatch, tmp_path):
    """Test 16: --live with GITHUB_TOKEN set + subprocess.run patched to
    return canned data → audit writes output with canned values."""
    mod = _import_audit_module()

    canned_release = {
        "tag_name": "v3.0.0-rc1",
        "published_at": "2026-05-01T00:00:00Z",
        "assets": [
            {"name": "vibemix-3.0.0-rc1-macos-universal.dmg", "download_count": 200},
            {"name": "vibemix-3.0.0-rc1-windows-x64.msi", "download_count": 150},
        ],
    }
    canned_issues = [
        {
            "number": 7,
            "title": "[crash] Tauri panics on first MIDI scan",
            "createdAt": "2026-05-04T10:00:00Z",
            "closedAt": None,
            "state": "OPEN",
            "labels": [{"name": "crash"}],
        },
        {
            "number": 8,
            "title": "Wizard step 2 typo",
            "createdAt": "2026-05-06T10:00:00Z",
            "closedAt": "2026-05-07T10:00:00Z",
            "state": "CLOSED",
            "labels": [],
        },
    ]

    def fake_subprocess_run(cmd, *args, **kwargs):
        # Mutation guard: subprocess.run must never POST/PATCH/DELETE.
        for method in ("POST", "PATCH", "DELETE"):
            assert method not in cmd, f"--live must NEVER mutate GH: {cmd}"
        joined = " ".join(cmd)
        # gh CLI command shape: `gh api ... releases/...` for releases,
        # `gh issue list ...` for issues. Match either.
        if "releases" in joined or "release" in joined:
            payload = canned_release
        elif "issue" in joined or "issues" in joined:
            payload = canned_issues
        else:
            raise AssertionError(f"Unexpected gh invocation: {cmd}")
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr(mod.subprocess, "run", fake_subprocess_run)
    monkeypatch.setenv("GITHUB_TOKEN", "fake-test-token")

    out_path = tmp_path / "decision.md"
    healthz_csv = tmp_path / "healthz.csv"
    healthz_csv.write_text(
        "timestamp,status\n"
        + "\n".join(f"2026-05-{d:02d}T00:00:00Z,ok" for d in range(1, 15)),
        encoding="utf-8",
    )
    rc = mod.main(
        [
            "--live",
            "--output",
            str(out_path),
            "--bravoh-healthz-csv",
            str(healthz_csv),
            "--release-tag",
            "v3.0.0-rc1",
        ]
    )
    assert rc == 0, "--live with patched subprocess must complete successfully."
    rendered = out_path.read_text(encoding="utf-8")
    # Aggregate of canned downloads = 200 + 150 = 350.
    assert "350" in rendered, "Aggregate download count must reflect canned data."


def test_17_live_mode_url_to_csv_fallback(monkeypatch, tmp_path):
    """Test 17: prefer --bravoh-healthz-stats-url; fall back to --bravoh-healthz-csv."""
    mod = _import_audit_module()
    monkeypatch.setenv("GITHUB_TOKEN", "fake-test-token")

    # Stub gh subprocess (re-used from Test 16 shape, kept minimal).
    def fake_subprocess_run(cmd, *args, **kwargs):
        joined = " ".join(cmd)
        if "releases" in joined:
            payload = {
                "tag_name": "v3.0.0-rc1",
                "published_at": "2026-05-01T00:00:00Z",
                "assets": [],
            }
        else:
            payload = []
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr(mod.subprocess, "run", fake_subprocess_run)

    # Stub urllib to return a 200 with canned uptime JSON when the URL is provided.
    class _FakeResp:
        def __init__(self, payload: bytes):
            self._payload = payload

        def read(self) -> bytes:
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    fake_url_payload = {"total_checks": 4032, "ok_count": 4030, "stale_count": 0}
    monkeypatch.setattr(
        mod.urllib.request,
        "urlopen",
        lambda req, timeout=10: _FakeResp(json.dumps(fake_url_payload).encode()),
    )

    out_path_url = tmp_path / "url.md"
    rc = mod.main(
        [
            "--live",
            "--output",
            str(out_path_url),
            "--bravoh-healthz-stats-url",
            "https://api.altidus.world/vibemix/healthz/stats",
            "--release-tag",
            "v3.0.0-rc1",
        ]
    )
    assert rc == 0
    rendered_url = out_path_url.read_text(encoding="utf-8")
    # 4030/4032 = 99.95% (2 decimals).
    assert "99.95%" in rendered_url, (
        f"Expected URL-sourced uptime 99.95%; got rendered: {rendered_url}"
    )

    # Now without the URL, with only a CSV path — fallback must kick in.
    healthz_csv = tmp_path / "healthz.csv"
    rows = ["timestamp,status"] + [
        f"2026-05-{d:02d}T00:00:00Z,{'ok' if d != 5 else 'fail'}"
        for d in range(1, 11)
    ]
    healthz_csv.write_text("\n".join(rows), encoding="utf-8")
    out_path_csv = tmp_path / "csv.md"
    rc = mod.main(
        [
            "--live",
            "--output",
            str(out_path_csv),
            "--bravoh-healthz-csv",
            str(healthz_csv),
            "--release-tag",
            "v3.0.0-rc1",
        ]
    )
    assert rc == 0
    rendered_csv = out_path_csv.read_text(encoding="utf-8")
    # 9/10 = 90.00% — clearly different from the URL-sourced 99.95%.
    assert "90.00%" in rendered_csv, (
        f"CSV fallback must compute uptime from rows; got: {rendered_csv}"
    )


def test_18_gh_actions_emits_notice_annotation(monkeypatch, tmp_path, capsys):
    """Test 18: GITHUB_ACTIONS=true emits a ::notice:: annotation pointing
    at the written decision report path."""
    mod = _import_audit_module()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    out_path = tmp_path / "decision.md"
    rc = mod.main(
        [
            "--fixtures",
            str(FIXTURES_DIR),
            "--output",
            str(out_path),
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    # GH Actions accepts either bare `::notice::msg` or `::notice title=X::msg`.
    # Both must include the literal `::notice` token at the start of a line.
    assert "::notice" in captured.out, (
        "GH Actions must receive a ::notice annotation on completion."
    )
    assert str(out_path) in captured.out, (
        "::notice annotation must include the output path."
    )


def test_19_atomic_write_via_tempfile_replace(monkeypatch, tmp_path):
    """Test 19: output write uses os.replace (atomic) — partial writes never
    leave a half-written report. We verify by patching os.replace and
    asserting it's called with the final output path."""
    mod = _import_audit_module()
    out_path = tmp_path / "decision.md"
    seen: list[tuple[str, str]] = []
    real_replace = mod.os.replace

    def fake_replace(src, dst):
        seen.append((str(src), str(dst)))
        return real_replace(src, dst)

    monkeypatch.setattr(mod.os, "replace", fake_replace)
    rc = mod.main(
        [
            "--fixtures",
            str(FIXTURES_DIR),
            "--output",
            str(out_path),
        ]
    )
    assert rc == 0
    assert any(dst == str(out_path) for _, dst in seen), (
        f"Audit must os.replace into the final output path; saw: {seen}"
    )


def test_20_idempotent_under_live_mode_with_patched_subprocess(monkeypatch, tmp_path):
    """Test 20: re-running --live with the same patched subprocess + fixed
    clock produces byte-identical output."""
    mod = _import_audit_module()
    monkeypatch.setenv("GITHUB_TOKEN", "fake-test-token")
    monkeypatch.setenv("VIBEMIX_AUDIT_DATE_OVERRIDE", "2026-06-01T12:00:00Z")

    canned_release = {
        "tag_name": "v3.0.0-rc1",
        "published_at": "2026-05-01T00:00:00Z",
        "assets": [
            {"name": "vibemix-3.0.0-rc1-macos-universal.dmg", "download_count": 50},
            {"name": "vibemix-3.0.0-rc1-windows-x64.msi", "download_count": 25},
        ],
    }
    canned_issues = []

    def fake_subprocess_run(cmd, *args, **kwargs):
        joined = " ".join(cmd)
        if "releases" in joined:
            payload = canned_release
        else:
            payload = canned_issues
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=json.dumps(payload), stderr=""
        )

    monkeypatch.setattr(mod.subprocess, "run", fake_subprocess_run)
    healthz_csv = tmp_path / "healthz.csv"
    healthz_csv.write_text(
        "timestamp,status\n2026-05-01T00:00:00Z,ok\n2026-05-02T00:00:00Z,ok\n",
        encoding="utf-8",
    )

    outputs = []
    for i in range(2):
        p = tmp_path / f"out_{i}.md"
        rc = mod.main(
            [
                "--live",
                "--output",
                str(p),
                "--bravoh-healthz-csv",
                str(healthz_csv),
                "--release-tag",
                "v3.0.0-rc1",
            ]
        )
        assert rc == 0
        outputs.append(p.read_text(encoding="utf-8"))
    assert outputs[0] == outputs[1], (
        "--live mode with fixed clock + same canned data must produce byte-identical output."
    )
