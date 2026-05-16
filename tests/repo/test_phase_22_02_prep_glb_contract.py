# SPDX-License-Identifier: Apache-2.0
"""Phase 35 Plan 35-05 — Phase 22-02 structural contract for prep_* GLBs.

Phase 22-02 idle-zero lower-body delta invariant: at t=0 after
AnimationUtils.makeClipAdditive, the lower-body bone deltas of every
prep_* clip must be ~0. The actual bone-level validation lives in the
TS test (`tauri/ui/src/mascot/additive-layer.test.ts`) — Python can't
parse GLB bone data without a native loader.

What THIS test enforces (structural):
    1. All 5 prep_* GLB files exist at the canonical paths.
    2. Files are non-empty (catches truncation, not validity).
    3. The TS additive-layer.test.ts references all 5 prep_* state
       names — guards against silent test-coverage drift when real GLBs
       land via Kaan-action ASSETS-PREP-REPLACE.
    4. manifest.json declares all 5 prep_* states.
    5. The PLACEHOLDER_NOTE.md is committed (documents the contract
       for the next person who touches these files).
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANIMATIONS_DIR = REPO_ROOT / "tauri" / "ui" / "assets" / "mascot" / "animations"
ADDITIVE_TEST = REPO_ROOT / "tauri" / "ui" / "src" / "mascot" / "additive-layer.test.ts"
MANIFEST = REPO_ROOT / "tauri" / "ui" / "assets" / "mascot" / "manifest.json"
PLACEHOLDER_NOTE = ANIMATIONS_DIR / "PLACEHOLDER_NOTE.md"

EXPECTED_PREP_STATES = (
    "prep_lean_in_neutral",
    "prep_lean_in_hyped",
    "prep_head_turn_left",
    "prep_head_turn_right",
    "prep_settle",
)


def test_all_5_prep_glb_files_exist() -> None:
    missing = [
        state for state in EXPECTED_PREP_STATES
        if not (ANIMATIONS_DIR / f"{state}.glb").is_file()
    ]
    assert not missing, (
        f"Missing prep_* GLB(s) at {ANIMATIONS_DIR}: {missing}. "
        f"Phase 22-02 anticipation layer requires all 5."
    )


def test_prep_glb_files_non_empty() -> None:
    """> 1 KB — catches truncation/zero-byte drops. Real bone validation
    happens in additive-layer.test.ts."""
    too_small = []
    for state in EXPECTED_PREP_STATES:
        path = ANIMATIONS_DIR / f"{state}.glb"
        if path.is_file() and path.stat().st_size < 1024:
            too_small.append((state, path.stat().st_size))
    assert not too_small, (
        f"prep_* GLB(s) suspiciously small (< 1 KB — likely truncation): "
        f"{too_small}"
    )


def test_additive_layer_test_references_all_5_prep_states() -> None:
    """The TS test file must mention each state name — guards against
    coverage drift when Kaan drops in real GLBs and forgets to extend
    the test list."""
    assert ADDITIVE_TEST.is_file(), f"missing {ADDITIVE_TEST}"
    text = ADDITIVE_TEST.read_text(encoding="utf-8")
    missing = [s for s in EXPECTED_PREP_STATES if s not in text]
    assert not missing, (
        f"additive-layer.test.ts does not reference: {missing}. "
        f"Phase 22-02 contract test must exercise every prep_* clip."
    )


def test_manifest_declares_all_5_prep_states() -> None:
    """manifest.json must map all 5 prep_* state names — drives
    asset-loader's per-clip wiring."""
    import json
    assert MANIFEST.is_file(), f"missing {MANIFEST}"
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    all_states = set()
    for entry in data.get("animations", []):
        for state in entry.get("states", []):
            all_states.add(state)
    missing = [s for s in EXPECTED_PREP_STATES if s not in all_states]
    assert not missing, (
        f"manifest.json missing state declaration(s): {missing}"
    )


def test_placeholder_note_exists_and_documents_contract() -> None:
    """PLACEHOLDER_NOTE.md documents the Phase 22-02 contract + drop-in
    workflow — required reading for the Kaan-action ASSETS-PREP-REPLACE."""
    assert PLACEHOLDER_NOTE.is_file(), f"missing {PLACEHOLDER_NOTE}"
    text = PLACEHOLDER_NOTE.read_text(encoding="utf-8").lower()
    for marker in ("phase 22-02", "idle-zero", "additive"):
        assert marker in text, (
            f"PLACEHOLDER_NOTE.md must mention {marker!r} so the contract "
            f"surface is documented in-place."
        )
