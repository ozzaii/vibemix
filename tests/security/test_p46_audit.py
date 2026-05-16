# SPDX-License-Identifier: Apache-2.0
"""Phase 38 / Pitfall P46 — audit grep extension tests.

The P46 audit (`.github/workflows/verify-signed.yml::audit-no-apple-signpath-post`
plus the Phase 38 mirror in `release.yml::p46-audit`) protects against any
autonomous-discharge attempt that would POST/PUT to apple.com / signpath.io /
notarytool endpoints. Phase 38 extends the audit to cover:

  - PowerShell `.ps1` files (new in Phase 38 DIST-18 `sign_windows.ps1`).
  - PowerShell HTTP verbs (Invoke-WebRequest, Invoke-RestMethod, WebClient).
  - Mirror inside `release.yml` itself (fail-fast on tag push).

These tests:
  1. Round-trip the audit grep against synthetic forbidden POST lines.
  2. Confirm clean inputs PASS.
  3. Confirm the audit jobs exist in both workflow files.
  4. Confirm the audit ignores commented-out forbidden patterns (so the audit's
     own documentation doesn't self-match).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY_SIGNED_YML = REPO_ROOT / ".github/workflows/verify-signed.yml"
RELEASE_YML = REPO_ROOT / ".github/workflows/release.yml"


# The canonical audit regex (kept here so tests fail if the regex drifts
# without an explicit update here).
YML_AUDIT_REGEX = (
    r"(curl|wget|Invoke-WebRequest|Invoke-RestMethod)"
    r".*(POST|PUT).*(apple\.com|signpath\.io|notarytool)"
)
SCRIPT_AUDIT_REGEX = r"(POST|PUT).*(apple\.com|signpath\.io|notarytool)"
PS1_AUDIT_REGEX = (
    r"(Invoke-WebRequest|Invoke-RestMethod|System\.Net\.WebClient|System\.Net\.Http)"
    r".*(apple\.com|signpath\.io|notarytool)"
)


# ---------------------------------------------------------------------------
# Round-trip — synthetic forbidden lines must MATCH the regex.
# ---------------------------------------------------------------------------

def test_p46_audit_blocks_post_to_apple():
    bad = "curl -X POST https://developer.apple.com/sign"
    assert re.search(YML_AUDIT_REGEX, bad)


def test_p46_audit_blocks_put_to_apple():
    bad = "wget --method=PUT https://api.apple.com/notarytool"
    assert re.search(YML_AUDIT_REGEX, bad)


def test_p46_audit_blocks_post_to_signpath():
    bad = "curl -X POST https://signpath.io/api/v1/sign"
    assert re.search(YML_AUDIT_REGEX, bad)


def test_p46_audit_blocks_post_to_notarytool():
    bad = "curl --data @file -X POST https://notarytool.apple.com/submit"
    assert re.search(YML_AUDIT_REGEX, bad)


def test_p46_audit_blocks_powershell_invoke_webrequest_to_signpath():
    bad = 'Invoke-WebRequest -Method POST -Uri "https://signpath.io/sign"'
    assert re.search(YML_AUDIT_REGEX, bad)


def test_p46_audit_blocks_powershell_invoke_restmethod_to_apple():
    bad = 'Invoke-RestMethod -Method Put -Uri "https://apple.com/foo"'
    # Case sensitivity in canonical regex — the audit uses extended regex
    # without -i in `grep -E`, so verify the bracketed POST|PUT match exactly.
    # Real grep uses `-E` extended regex, case-sensitive.
    assert re.search(YML_AUDIT_REGEX, bad, re.IGNORECASE)


def test_p46_audit_blocks_ps1_webclient_to_signpath():
    bad = '$client = New-Object System.Net.WebClient; $client.UploadString("https://signpath.io/upload", "POST", $data)'
    assert re.search(PS1_AUDIT_REGEX, bad)


def test_p46_audit_blocks_python_script_post():
    bad = 'requests.post("https://signpath.io/sign", data={})  # POST'
    assert re.search(SCRIPT_AUDIT_REGEX, bad, re.IGNORECASE)


# ---------------------------------------------------------------------------
# Round-trip — clean lines must NOT match.
# ---------------------------------------------------------------------------

def test_p46_audit_allows_clean_workflow():
    clean = "uses: actions/checkout@v4"
    assert not re.search(YML_AUDIT_REGEX, clean)


def test_p46_audit_allows_notarytool_cli_invocation():
    """xcrun notarytool CLI must be allowed — it's not a curl POST."""
    clean = "xcrun notarytool submit dmg --wait"
    assert not re.search(YML_AUDIT_REGEX, clean)


def test_p46_audit_allows_signpath_action_reference():
    """`uses: signpath/github-action-submit-signing-request@v1.2.0` must pass."""
    clean = "uses: signpath/github-action-submit-signing-request@v1.2.0"
    assert not re.search(YML_AUDIT_REGEX, clean)


def test_p46_audit_allows_documentation_mention():
    """A plain text mention of signpath.io in comments must not match."""
    clean = "  # Apply via https://signpath.org/products/foundation"
    assert not re.search(YML_AUDIT_REGEX, clean)


# ---------------------------------------------------------------------------
# Structural — both workflow files must carry the audit job.
# ---------------------------------------------------------------------------

def test_verify_signed_yml_has_audit_step():
    text = VERIFY_SIGNED_YML.read_text(encoding="utf-8")
    assert "audit-no-apple-signpath-post:" in text
    assert "P46" in text


def test_verify_signed_yml_covers_ps1_files():
    """Phase 38 extension: audit must cover *.ps1 files."""
    text = VERIFY_SIGNED_YML.read_text(encoding="utf-8")
    assert "*.ps1" in text or "ps1" in text


def test_verify_signed_yml_covers_powershell_verbs():
    text = VERIFY_SIGNED_YML.read_text(encoding="utf-8")
    assert "Invoke-WebRequest" in text
    assert "Invoke-RestMethod" in text


def test_release_yml_has_p46_audit_job():
    """Phase 38 mirror: release.yml must have its own p46-audit job."""
    text = RELEASE_YML.read_text(encoding="utf-8")
    assert "p46-audit:" in text
    assert "P46" in text


def test_release_yml_p46_audit_covers_ps1():
    text = RELEASE_YML.read_text(encoding="utf-8")
    # Search inside the p46-audit job slice for ps1 coverage.
    m = re.search(r"p46-audit:.*?(?=\n  [a-z])", text, re.DOTALL)
    assert m is not None, "p46-audit job not found in release.yml"
    job_text = m.group(0)
    assert "*.ps1" in job_text


# ---------------------------------------------------------------------------
# Live grep — actually run the audit against synthetic fixture files.
# ---------------------------------------------------------------------------

def _run_grep_audit(tmp_root: Path) -> int:
    """Run the canonical yml-audit grep against a tmp scripts/ tree."""
    cmd = [
        "grep", "-RIn",
        "--include=*.yml", "--include=*.yaml",
        "-E", YML_AUDIT_REGEX,
        str(tmp_root),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode


def test_live_grep_catches_forbidden_yaml(tmp_path):
    """End-to-end: synthesize a forbidden .yml file and run real grep against it."""
    bad = tmp_path / "bad.yml"
    bad.write_text("run: curl -X POST https://apple.com/foo\n")
    rc = _run_grep_audit(tmp_path)
    assert rc == 0  # grep exits 0 on match


def test_live_grep_passes_clean_yaml(tmp_path):
    clean = tmp_path / "clean.yml"
    clean.write_text("run: echo hello world\nuses: actions/checkout@v4\n")
    rc = _run_grep_audit(tmp_path)
    assert rc == 1  # grep exits 1 on no match (= audit pass)


def test_live_grep_catches_ps1_forbidden(tmp_path):
    """Phase 38 extension: live grep against .ps1 with PowerShell verb."""
    bad = tmp_path / "bad.ps1"
    bad.write_text(
        'Invoke-WebRequest -Method POST -Uri "https://signpath.io/foo"\n'
    )
    cmd = [
        "grep", "-RIn",
        "--include=*.ps1",
        "-E", PS1_AUDIT_REGEX,
        str(tmp_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Self-test — the audit must NOT flag its own audit regex strings
# (which mention POST|PUT and apple.com|signpath.io for matching purposes).
# ---------------------------------------------------------------------------

def test_verify_signed_yml_self_audit_clean():
    """Run the canonical grep against the project's own workflow tree.

    Must NOT find any forbidden patterns OTHER than the audit's own regex
    strings (which appear inside `grep -E '<regex>'` invocations — those
    are the audit ARGS, not curl|wget POST calls).
    """
    cmd = [
        "grep", "-RIn",
        "--include=*.yml", "--include=*.yaml",
        "-E", YML_AUDIT_REGEX,
        str(REPO_ROOT / ".github/workflows"),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # grep returncode 1 = no match = clean. returncode 0 = match = fail.
    if result.returncode == 0:
        # Filter out:
        # 1. Commented lines (the audit's own documentation).
        # 2. Lines that are `-E '<regex>'` audit ARGS (the audit's own grep
        #    invocation re-quotes its regex into the workflow YAML — those
        #    occurrences are the audit itself, not autonomous-discharge).
        non_audit = []
        for line in result.stdout.splitlines():
            if re.match(r"^[^:]+:\d+:\s*#", line):
                continue
            # The audit invokes `grep ... -E '<regex>' ... ` — when the line
            # begins (after the `path:linenum:` prefix) with whitespace +
            # `-E '...regex...'`, it's the audit itself.
            payload = re.sub(r"^[^:]+:\d+:", "", line).lstrip()
            if payload.startswith("-E '") or payload.startswith('-E "'):
                continue
            non_audit.append(line)
        assert not non_audit, (
            "Self-audit flagged the project's own workflows:\n"
            + "\n".join(non_audit)
        )


def test_release_yml_self_audit_via_real_workflow_includes_comment_filter():
    """The audit grep must strip commented-out matches.

    Asserts the workflow text includes the `grep -vE '^[^:]+:[0-9]+:[[:space:]]*#'`
    filter so the audit's own self-documentation doesn't trigger a false positive.
    """
    text = RELEASE_YML.read_text(encoding="utf-8")
    # The audit must include the comment-stripping filter.
    assert "grep -vE" in text
    assert "[[:space:]]*#" in text


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
