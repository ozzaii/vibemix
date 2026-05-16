# SPDX-License-Identifier: Apache-2.0
"""Phase 38 / DIST-18 — sign_windows.ps1 local-rehearsal script tests.

The script wraps SignPathClient.exe for Kaan's local rehearsal of the
Windows signing flow. P46 compliance is enforced via grep — no
Invoke-WebRequest / Invoke-RestMethod / WebClient / direct curl|wget to
signpath/apple/notarytool endpoints.

Syntax validation: when pwsh is available we use the PowerShell parser
(`[System.Management.Automation.PSParser]::Tokenize`). When it isn't
(CI sometimes runs on Linux without pwsh), we fall back to a Python-side
balance check (brackets, braces, parens, single-quote pairing).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
PS1 = REPO_ROOT / "scripts/dist/sign_windows.ps1"


@pytest.fixture(scope="module")
def ps1_text() -> str:
    return PS1.read_text(encoding="utf-8")


def test_sign_windows_ps1_exists():
    assert PS1.exists(), f"Missing required script: {PS1}"


def test_sign_windows_ps1_has_param_block(ps1_text: str):
    """The script must declare param() block with required SignPath inputs."""
    # CmdletBinding + param block.
    assert "[CmdletBinding()]" in ps1_text
    assert re.search(r"\bparam\s*\(", ps1_text)
    # Required parameters per the Plan.
    for name in ("MsiPath", "ApiToken", "OrganizationId", "ProjectSlug",
                 "PolicySlug", "ArtifactConfigSlug", "OutputDir"):
        assert f"${name}" in ps1_text, f"Missing param: ${name}"


def test_sign_windows_ps1_no_forbidden_posts(ps1_text: str):
    """Strict P46: no PowerShell HTTP verbs, no direct curl/wget POST/PUT."""
    forbidden_verbs = [
        "Invoke-WebRequest",
        "Invoke-RestMethod",
        "System.Net.WebClient",
        "System.Net.Http",
        "New-Object Net.WebClient",
    ]
    for verb in forbidden_verbs:
        # Allow appearance in comments (lines starting with # after whitespace).
        for line in ps1_text.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            assert verb not in line, f"Forbidden HTTP verb in non-comment line: {verb!r} in {line!r}"

    # Pair-pattern grep: any POST|PUT paired with apple|signpath|notarytool.
    body_lines = [
        line for line in ps1_text.splitlines()
        if not line.lstrip().startswith("#")
    ]
    body = "\n".join(body_lines)
    bad_pattern = re.compile(
        r"(curl|wget|Invoke-WebRequest|Invoke-RestMethod).*"
        r"(POST|PUT).*(apple\.com|signpath\.io|notarytool)",
        re.IGNORECASE,
    )
    matches = bad_pattern.findall(body)
    assert not matches, f"Forbidden POST/PUT to apple/signpath/notarytool: {matches!r}"


def test_sign_windows_ps1_invokes_signpath_cli(ps1_text: str):
    """Must invoke SignPathClient.exe (the official vendor-signed CLI)."""
    assert "SignPathClient.exe" in ps1_text
    assert "Get-Command" in ps1_text


def test_sign_windows_ps1_documents_p46(ps1_text: str):
    """Header comment must reference Pitfall P46 + KAAN-ACTION-LEGAL.md."""
    head = ps1_text[:2000]
    assert "P46" in head
    assert "KAAN-ACTION-LEGAL.md" in head


def test_sign_windows_ps1_emits_kaan_action_pointer(ps1_text: str):
    """If SignPathClient.exe is missing the script must point operator at docs."""
    assert "signpath.io/documentation" in ps1_text or "about.signpath.io" in ps1_text


def _python_side_balance_check(text: str) -> tuple[bool, str]:
    """Lightweight syntax sanity: brackets/braces/parens balanced.

    Strips line/block comments AND single/double-quoted strings so we don't
    count brackets that appear inside those.
    """
    # Strip block comments first.
    text = re.sub(r"<#.*?#>", "", text, flags=re.DOTALL)
    cleaned: list[str] = []
    for line in text.splitlines():
        # Drop line comments (# ...).
        if "#" in line:
            # Naive but sufficient: keep substring before the FIRST `#`.
            line = line.split("#", 1)[0]
        # Drop double-quoted string contents.
        line = re.sub(r'"(?:[^"\\]|\\.)*"', "", line)
        # Drop single-quoted string contents.
        line = re.sub(r"'(?:[^'\\]|\\.)*'", "", line)
        cleaned.append(line)
    body = "\n".join(cleaned)
    pairs = [("(", ")"), ("[", "]"), ("{", "}")]
    for openc, closec in pairs:
        if body.count(openc) != body.count(closec):
            return False, f"Unbalanced {openc}{closec}: open={body.count(openc)} close={body.count(closec)}"
    return True, "balanced"


def test_sign_windows_ps1_syntax_valid(ps1_text: str):
    """Phase 38 hard gate: PowerShell syntax must parse.

    Uses `pwsh` if available; otherwise falls back to a Python-side balance check.
    """
    pwsh = shutil.which("pwsh")
    if pwsh:
        # Use PSParser to tokenize WITHOUT executing.
        cmd = [
            pwsh,
            "-NoProfile",
            "-Command",
            f"$tokens = $null; $errors = $null; "
            f"[void][System.Management.Automation.PSParser]::Tokenize("
            f"(Get-Content -Raw '{PS1.as_posix()}'), [ref]$errors); "
            f"if ($errors -and $errors.Count -gt 0) {{ "
            f"  $errors | ForEach-Object {{ Write-Error $_.Message }}; exit 1 }} "
            f"else {{ exit 0 }}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, (
            f"PowerShell parser errors:\n{result.stdout}\n{result.stderr}"
        )
    else:
        ok, msg = _python_side_balance_check(ps1_text)
        assert ok, f"Python-side syntax sanity failed: {msg}"


def test_sign_windows_ps1_python_balance_check_passes(ps1_text: str):
    """Belt-and-braces: the Python-side balance check itself must pass.

    Guarantees the fallback path used on Linux CI catches regressions.
    """
    ok, msg = _python_side_balance_check(ps1_text)
    assert ok, msg


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
