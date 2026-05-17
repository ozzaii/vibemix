"""DEPS-08 — assert the dep-cull pass surface is documented:
  - For deps with zero direct imports under src/vibemix/, dep is removed from
    pyproject.toml OR documented as retained-as-transitive in AUDIT.md § Decisions
  - For deps with direct imports (e.g., livekit-plugins-openai used by
    src/vibemix/agent/tts_chain.py), the cull is BLOCKED and documented as
    such in AUDIT.md § Decisions
  - docs/AUDIT.md § Decisions documents each cull decision
"""

import subprocess
import tomllib
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]


def _rg_has_match(pattern: str, *paths: str) -> bool:
    r = subprocess.run(
        ["rg", "-q", pattern, *paths],
        cwd=REPO, capture_output=True, text=True,
    )
    return r.returncode == 0


def test_no_direct_imports_of_google_cloud_speech_or_tts():
    """google-cloud-speech and google-cloud-texttospeech are pure transitives;
    direct imports under src/vibemix/ would invalidate the cull-defer."""
    for pattern in (
        r"from google\.cloud\.speech",
        r"from google\.cloud\.texttospeech",
    ):
        assert not _rg_has_match(pattern, "src/"), \
            f"direct import of cull target: {pattern}"


def test_pyproject_either_culls_or_documents_each_cull_target():
    """For each of the three Phase 46 cull targets, either:
      (a) the dep is NOT in pyproject.toml [project.dependencies], OR
      (b) AUDIT.md § Decisions documents why it's retained.
    """
    with (REPO / "pyproject.toml").open("rb") as f:
        data = tomllib.load(f)
    deps = data["project"]["dependencies"]
    declared = set()
    for d in deps:
        name = (
            d.split("[")[0]
            .split(">=")[0].split("==")[0].split("<")[0].split(">")[0].split("~=")[0]
            .split(";")[0]
            .strip()
        )
        declared.add(name)
    audit_text = (REPO / "docs" / "AUDIT.md").read_text()

    cull_targets_and_markers = {
        "livekit-plugins-openai": "cull-blocked-livekit-plugins-openai",
        "google-cloud-speech": "defer-google-cloud-speech",
        "google-cloud-texttospeech": "defer-google-cloud-texttospeech",
    }
    for dep, marker in cull_targets_and_markers.items():
        if dep in declared:
            # Still declared — must be documented as cull-blocked or deferred.
            assert marker in audit_text, \
                f"{dep} still declared in pyproject.toml but AUDIT.md missing decision marker: {marker}"
        else:
            # Removed — also documented.
            assert marker in audit_text, \
                f"{dep} removed from pyproject.toml but AUDIT.md missing decision marker: {marker}"


def test_audit_md_documents_cull_decisions():
    text = (REPO / "docs" / "AUDIT.md").read_text()
    for marker in (
        "cull-blocked-livekit-plugins-openai",
        "defer-google-cloud-speech",
        "defer-google-cloud-texttospeech",
    ):
        assert marker in text, f"AUDIT.md missing decision marker: {marker}"


def test_dep_ratings_decisions_block_matches():
    with (REPO / "scripts" / "audit" / "dep_ratings.yaml").open() as f:
        data = yaml.safe_load(f)
    decisions = data.get("decisions", [])
    ids = {d["id"] for d in decisions}
    assert ids >= {
        "cull-blocked-livekit-plugins-openai",
        "defer-google-cloud-speech",
        "defer-google-cloud-texttospeech",
    }, f"decisions block missing IDs: {ids}"
