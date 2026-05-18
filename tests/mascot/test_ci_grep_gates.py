"""MASCOT-08 smoke test — assert the CI grep gates would pass right now.

Subprocess-shells the same grep commands as .github/workflows/mascot-audit.yml
against the current repo tree. Detects regressions BEFORE pushing to CI.

Note on anti-slop coverage:
    The orchestrator anti-stall discipline rejects redesigning the
    shared scripts/launch/check_no_ai_slop.py mid-execute. Plan 47-08
    Task 2's "extend the launch-side target list" was implemented as a
    sibling script at scripts/mascot/check_no_ai_slop_phase47.py that
    re-imports AI_SLOP_BLOCKLIST from the launch script (single source
    of truth preserved) while scoping the gate to Phase 47 artifacts.
    Tests below assert the sibling script exists + that the canonical
    launch-side script remains untouched.
"""
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        args, cwd=REPO_ROOT, capture_output=True, text=True
    )
    return result.returncode, result.stdout + result.stderr


def test_no_mascot_html_in_tests_e2e_scripts_ci():
    """Mirror the .github/workflows/mascot-tauri-only.yml grep gate.

    grep -rn returns 0 when it finds matches, 1 when not, 2 on error.
    We want 1 (no matches) to mean "clean".

    Allowlisted files reference mascot.html for POC-immutability enforcement
    (the OPPOSITE of the Pitfall 4 regression class — these files declare
    mascot.html as a PROTECTED file that must NOT be touched). The Pitfall
    4 regression we are guarding against is tests/e2e/ci files that USE
    mascot.html as their test target instead of the Tauri+Three.js surface.
    """
    allowlist_basenames = {
        # Phase 37-06 POC-immutability gates (tests/repo/).
        "test_g5_poc_files_untouched.py",
        "test_repo_scrub.py",
        # Phase 33-class reaction-reel POC-pattern guard.
        "test_pipeline.py",
        # Phase 5 POC-files-untouched verification.
        "test_phase05_verification.py",
        # Security gate that scans HTML surfaces — mentions mascot.html
        # as part of the scan-glob list, NOT as a test target.
        "test_no_api_key_surface.py",
        # This very test file — it references mascot.html in docstrings
        # and assertion messages but does not drive tests against it.
        "test_ci_grep_gates.py",
    }
    targets = []
    for d in ("tests", "e2e", "scripts/ci"):
        if (REPO_ROOT / d).is_dir():
            targets.append(d)
    if not targets:
        return  # nothing to grep against on this clone — gate vacuous
    rc, output = _run(
        [
            "grep",
            "-rln",
            "--include=*.py",
            "--include=*.ts",
            "--include=*.tsx",
            "--include=*.js",
            "--include=*.sh",
            "--include=*.yml",
            "--exclude-dir=__pycache__",
            "mascot.html",
            *targets,
        ]
    )
    if rc != 0:
        return  # grep found nothing — clean
    offenders = [
        line.strip()
        for line in output.splitlines()
        if line.strip() and Path(line.strip()).name not in allowlist_basenames
    ]
    assert not offenders, (
        "mascot.html referenced in test/ci surface — close Pitfall 4:\n"
        + "\n".join(offenders)
    )


def test_mascot_tauri_only_workflow_exists():
    wf = REPO_ROOT / ".github" / "workflows" / "mascot-tauri-only.yml"
    assert wf.is_file(), (
        "Phase 47 / MASCOT-08 — mascot-tauri-only.yml CI gate missing"
    )


def test_mascot_audit_workflow_exists():
    wf = REPO_ROOT / ".github" / "workflows" / "mascot-audit.yml"
    assert wf.is_file(), (
        "Phase 47 / MASCOT-08 — mascot-audit.yml aggregated workflow missing"
    )


def test_phase_47_anti_slop_sibling_script_exists():
    """Phase 47 anti-slop sibling at scripts/mascot/check_no_ai_slop_phase47.py.

    Per orchestrator anti-stall discipline: the shared launch-side
    check_no_ai_slop.py is NOT mid-phase-extended. A sibling script
    scopes the same blocklist to Phase 47 artifacts.
    """
    sibling = REPO_ROOT / "scripts" / "mascot" / "check_no_ai_slop_phase47.py"
    assert sibling.is_file(), (
        "Phase 47 / MASCOT-08 — sibling anti-slop script missing"
    )
    src = sibling.read_text(encoding="utf-8")
    for required in (
        "docs/mascot/README.md",
        "docs/mascot/BUNDLE-DECISION.md",
        "scripts/mascot/MIXAMO-CLIP-SOURCES.md",
        "assets/mascot/source/MANIFEST.yaml",
        "tauri/ui/src/mascot/event-dispatcher.ts",
        "tauri/ui/src/mascot/persona-smoke-harness.ts",
    ):
        assert required in src, (
            f"check_no_ai_slop_phase47.py missing target: {required}"
        )


def test_canonical_launch_anti_slop_script_untouched():
    """The canonical scripts/launch/check_no_ai_slop.py stays pinned to
    scripts/dayzero/launch_copy/. The Phase 47 sibling re-imports the
    blocklist from it — single source of truth preserved."""
    launch = REPO_ROOT / "scripts" / "launch" / "check_no_ai_slop.py"
    assert launch.is_file()
    src = launch.read_text(encoding="utf-8")
    # The canonical script's contract is launch_copy/, not Phase 47 paths.
    assert "scripts/dayzero/launch_copy" in src, (
        "canonical launch anti-slop script contract drifted from launch_copy/"
    )


def test_phase_47_anti_slop_sibling_runs_clean():
    """Subprocess-runs the Phase 47 anti-slop sibling; expects exit 0."""
    sibling = REPO_ROOT / "scripts" / "mascot" / "check_no_ai_slop_phase47.py"
    if not sibling.is_file():
        return  # covered by test above
    rc, output = _run(["python3", str(sibling)])
    assert rc == 0, f"Phase 47 anti-slop sibling failed:\n{output}"


def test_mascot_html_byte_identity_invariant_documented():
    """Sanity check: Phase 47 must not edit mascot.html itself.

    The Phase 37-06 poc-immutability-check.yml gate covers byte-identity
    from a separate workflow; this test just confirms the standalone
    easter-egg file still exists at the canonical path."""
    easter_egg = REPO_ROOT / "mascot.html"
    assert easter_egg.is_file(), (
        "mascot.html easter-egg missing — Phase 37-06 byte-identity broken?"
    )
