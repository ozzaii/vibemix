# SPDX-License-Identifier: Apache-2.0
"""Phase 40 / AUDIO-05 — PGP key publication gate test.

Dual-mode gate:

- **Pre-discharge mode (engineering pre-stage state):** The slot file
  ``docs/security/pgp-public-key.txt`` contains the placeholder sentinel
  ``PLACEHOLDER-VIBEMIX-AUDIO-05-PGP-NOT-YET-GENERATED``. In this mode the
  test asserts the placeholder scaffolding is internally consistent
  (slot file exists, SECURITY.md references it, the fingerprint
  placeholder is still in the SECURITY.md table, the KAAN-ACTION-LEGAL
  runbook is present).

- **Post-discharge mode (after Kaan runs the runbook):** The placeholder
  sentinel is absent from the slot file. The test then asserts the
  full-discharge invariants: the slot file is a valid ASCII-armored
  OpenPGP public key block; SECURITY.md no longer references the
  ``KAAN-PGP-PLACEHOLDER.asc`` placeholder path or
  ``PLACEHOLDER-FINGERPRINT-NOT-REAL``; the placeholder ``.asc`` file
  has been ``git rm``'d.

- **Partial-discharge failure mode:** Mixed state — slot file updated
  but SECURITY.md not (or vice versa) — fails with a clear message
  pointing Kaan at the runbook.

See: KAAN-ACTION-LEGAL.md §AUDIO-05.
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SLOT_FILE = REPO_ROOT / "docs" / "security" / "pgp-public-key.txt"
SECURITY_MD = REPO_ROOT / "SECURITY.md"
LEGACY_PLACEHOLDER = REPO_ROOT / "KAAN-PGP-PLACEHOLDER.asc"
LEGAL_MD = REPO_ROOT / "KAAN-ACTION-LEGAL.md"

PLACEHOLDER_SENTINEL = "PLACEHOLDER-VIBEMIX-AUDIO-05-PGP-NOT-YET-GENERATED"
FINGERPRINT_SENTINEL = "PLACEHOLDER-FINGERPRINT-NOT-REAL"
LEGACY_ASC_REF = "KAAN-PGP-PLACEHOLDER.asc"
NEW_PATH_REF = "docs/security/pgp-public-key.txt"

OPENPGP_HEADER = "-----BEGIN PGP PUBLIC KEY BLOCK-----"
OPENPGP_FOOTER = "-----END PGP PUBLIC KEY BLOCK-----"


@pytest.fixture(scope="module")
def slot_text() -> str:
    assert SLOT_FILE.exists(), (
        f"Slot file missing: {SLOT_FILE}. "
        "Plan 40-05 scaffolds this file with a placeholder body. "
        "See KAAN-ACTION-LEGAL.md §AUDIO-05."
    )
    return SLOT_FILE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def security_md_text() -> str:
    return SECURITY_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def legal_md_text() -> str:
    return LEGAL_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def is_pre_discharge(slot_text: str) -> bool:
    return PLACEHOLDER_SENTINEL in slot_text


def test_slot_file_exists_and_has_pgp_block_header(slot_text: str):
    """Slot file always has the PGP armor envelope, even pre-discharge."""
    assert OPENPGP_HEADER in slot_text, (
        f"Slot file {SLOT_FILE} does not contain "
        f"'{OPENPGP_HEADER}'. The placeholder body must still be inside "
        "a valid PGP armor envelope so consumers know where to look."
    )
    assert OPENPGP_FOOTER in slot_text, (
        f"Slot file {SLOT_FILE} missing PGP block footer."
    )


def test_security_md_references_new_slot_file(security_md_text: str):
    """SECURITY.md PGP section must hyperlink the new slot path."""
    assert NEW_PATH_REF in security_md_text, (
        f"SECURITY.md does not reference '{NEW_PATH_REF}'. "
        "Plan 40-05 retargets the PGP link from "
        f"'{LEGACY_ASC_REF}' to '{NEW_PATH_REF}'."
    )


def test_legal_md_has_audio_05_runbook(legal_md_text: str):
    """KAAN-ACTION-LEGAL.md must document the AUDIO-05 discharge protocol."""
    assert "AUDIO-05" in legal_md_text, (
        "KAAN-ACTION-LEGAL.md missing the '## AUDIO-05' runbook section "
        "(PGP key generation + publish to keys.openpgp.org). "
        "Plan 40-05 appends this section."
    )
    # The discharge commands from RESEARCH §AUDIO-05 Code Examples.
    assert "gpg --quick-gen-key" in legal_md_text, (
        "AUDIO-05 runbook missing the 'gpg --quick-gen-key' generation step."
    )
    assert "keys.openpgp.org" in legal_md_text, (
        "AUDIO-05 runbook missing the keys.openpgp.org publish step."
    )


def test_pre_discharge_invariants(
    is_pre_discharge: bool,
    slot_text: str,
    security_md_text: str,
):
    """Pre-discharge: placeholder consistent across slot file + SECURITY.md."""
    if not is_pre_discharge:
        pytest.skip("Post-discharge mode — exercised by separate assertions.")
    # The placeholder sentinel is in the slot file...
    assert PLACEHOLDER_SENTINEL in slot_text
    # ...and the SECURITY.md table still has the placeholder fingerprint.
    assert FINGERPRINT_SENTINEL in security_md_text, (
        "PARTIAL-DISCHARGE DETECTED: slot file still has the placeholder "
        "but SECURITY.md fingerprint cell was updated. "
        "Kaan: finish the runbook — either roll back the SECURITY.md edit "
        "or paste the real PGP armor into the slot file. "
        "See KAAN-ACTION-LEGAL.md §AUDIO-05."
    )


def test_post_discharge_invariants(
    is_pre_discharge: bool,
    slot_text: str,
    security_md_text: str,
):
    """Post-discharge: real PGP key in slot; placeholder strings gone."""
    if is_pre_discharge:
        pytest.skip("Pre-discharge mode — exercised by separate assertions.")

    # The slot file must be a structurally-valid PGP public-key block.
    header_idx = slot_text.find(OPENPGP_HEADER)
    footer_idx = slot_text.find(OPENPGP_FOOTER)
    assert header_idx >= 0 and footer_idx > header_idx, (
        "Slot file is missing the PGP armor envelope. Did the export "
        "command include `--armor`? Re-run "
        "`gpg --armor --export security@bravoh.com > "
        f"{NEW_PATH_REF}`."
    )
    body_len = footer_idx - (header_idx + len(OPENPGP_HEADER))
    assert body_len >= 200, (
        f"PGP block body is suspiciously short ({body_len} chars). "
        "A real ed25519 public key armors to ~400+ chars between header "
        "and footer."
    )

    # No PRIVATE block — only the public half ever lives in the repo.
    assert "-----BEGIN PGP PRIVATE KEY BLOCK-----" not in slot_text, (
        "CRITICAL: slot file contains a PRIVATE PGP key block. "
        "Only the PUBLIC half belongs in the repo. Re-generate "
        "via `gpg --armor --export` (NOT `--export-secret-keys`)."
    )

    # SECURITY.md must no longer reference the placeholder asc file
    # or the placeholder fingerprint string.
    assert LEGACY_ASC_REF not in security_md_text, (
        "PARTIAL-DISCHARGE DETECTED: SECURITY.md still references "
        f"'{LEGACY_ASC_REF}' even though the slot file has the real key. "
        f"Replace the reference with '{NEW_PATH_REF}' "
        "and re-render the fingerprint table. "
        "See KAAN-ACTION-LEGAL.md §AUDIO-05 discharge checklist."
    )
    assert FINGERPRINT_SENTINEL not in security_md_text, (
        "PARTIAL-DISCHARGE DETECTED: SECURITY.md still shows "
        f"'{FINGERPRINT_SENTINEL}'. Replace it with the real "
        "fingerprint from `gpg --list-keys security@bravoh.com`."
    )

    # The legacy `.asc` placeholder file should be removed once discharge
    # is complete (it's part of the runbook checklist).
    assert not LEGACY_PLACEHOLDER.exists(), (
        f"PARTIAL-DISCHARGE DETECTED: {LEGACY_PLACEHOLDER} still exists. "
        "Run `git rm KAAN-PGP-PLACEHOLDER.asc` per the AUDIO-05 discharge "
        "checklist in KAAN-ACTION-LEGAL.md."
    )
