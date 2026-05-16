# SPDX-License-Identifier: Apache-2.0
"""Phase 40 / AUDIO-06 — Tauri updater pubkey rotation gate test.

Dual-mode gate:

- **Pre-discharge mode (engineering pre-stage state):** The 2026-05-13
  dev-key fingerprint sentinel ``94A8F6CE42E6487D`` is present in the
  decoded ``plugins.updater.pubkey`` value. The test asserts: (a) the
  pubkey decodes via base64, (b) the file path exists, (c) the
  ``release.yml::placeholder-pubkey-gate`` job still exists (Pitfall 6
  regression guard).

- **Post-discharge mode (after Kaan rotates):** The dev-key sentinel
  is absent. The test asserts: (a) pubkey is not empty + not the
  literal ``TAURI_UPDATER_PLACEHOLDER`` Phase-18 sentinel, (b)
  base64-decodes successfully, (c) decoded comment starts with the
  minisign convention ``untrusted comment: minisign public key:``,
  (d) ``release.yml::placeholder-pubkey-gate`` job still exists.

- **Partial-discharge failure mode:** Pubkey rotated but the
  ``Plan 40-05 — production key rotation`` comment block in
  ``tauri.conf.json5`` was not updated, or the ``release.yml`` gate
  job was accidentally removed during the rotation — fails with a
  clear message pointing Kaan at the runbook.

See: KAAN-ACTION-LEGAL.md §AUDIO-06.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
TAURI_CONF = REPO_ROOT / "tauri" / "src-tauri" / "tauri.conf.json5"
RELEASE_YML = REPO_ROOT / ".github" / "workflows" / "release.yml"
LEGAL_MD = REPO_ROOT / "KAAN-ACTION-LEGAL.md"

# The dev-key fingerprint (embedded in the base64 comment of the
# 2026-05-13 dev key). Plan 40-05 treats this as the pre-discharge
# sentinel — its presence means Kaan has not yet rotated.
DEV_KEY_FINGERPRINT = "94A8F6CE42E6487D"

# The Phase 18 placeholder sentinel — already gated against by
# release.yml::placeholder-pubkey-gate on tagged pushes.
PHASE_18_PLACEHOLDER = "TAURI_UPDATER_PLACEHOLDER"

# Minisign public key comment convention.
MINISIGN_COMMENT_PREFIX = "untrusted comment: minisign public key:"

PUBKEY_REGEX = re.compile(r'"pubkey"\s*:\s*"([^"]+)"')


@pytest.fixture(scope="module")
def tauri_conf_text() -> str:
    assert TAURI_CONF.exists(), f"Missing: {TAURI_CONF}"
    return TAURI_CONF.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def release_yml_text() -> str:
    return RELEASE_YML.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def legal_md_text() -> str:
    return LEGAL_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pubkey_value(tauri_conf_text: str) -> str:
    match = PUBKEY_REGEX.search(tauri_conf_text)
    assert match, (
        "Could not extract `pubkey` value from "
        f"{TAURI_CONF}. Did the updater config get refactored? "
        "The placeholder-pubkey-gate in release.yml also depends on "
        "this field being string-grep-able."
    )
    return match.group(1)


@pytest.fixture(scope="module")
def pubkey_decoded(pubkey_value: str) -> str:
    """Decode the base64 pubkey and return the human-readable comment line."""
    try:
        decoded = base64.b64decode(pubkey_value).decode("utf-8", errors="replace")
    except Exception as exc:
        pytest.fail(
            f"pubkey value does not base64-decode: {exc}. "
            "The minisign pubkey envelope is always base64-encoded. "
            "Did the rotation copy a raw key instead of the .pub file body?"
        )
    return decoded


@pytest.fixture(scope="module")
def is_pre_discharge(pubkey_decoded: str) -> bool:
    return DEV_KEY_FINGERPRINT in pubkey_decoded


def test_tauri_conf_exists():
    assert TAURI_CONF.exists()


def test_pubkey_field_present(pubkey_value: str):
    """The pubkey field must always be a non-empty string."""
    assert pubkey_value, "plugins.updater.pubkey is empty."


def test_pubkey_is_not_phase_18_placeholder(pubkey_value: str):
    """The Phase 18-04 placeholder sentinel must never reappear."""
    assert PHASE_18_PLACEHOLDER not in pubkey_value, (
        "REGRESSION DETECTED: the Phase 18 TAURI_UPDATER_PLACEHOLDER "
        "sentinel is back in tauri.conf.json5. The "
        "placeholder-pubkey-gate in release.yml would now fail any "
        "tagged release. Restore the 2026-05-13 dev key (pre-discharge) "
        "or paste the prod pubkey (post-discharge). "
        "See KAAN-ACTION-LEGAL.md §AUDIO-06."
    )


def test_plan_40_05_comment_block_present(tauri_conf_text: str):
    """The Plan 40-05 rotation runbook reference must be in the comment block."""
    assert "Plan 40-05" in tauri_conf_text, (
        "tauri.conf.json5 missing the 'Plan 40-05 — production key "
        "rotation' comment block immediately above the pubkey line. "
        "Plan 40-05 scaffolds this block to document the rotation "
        "runbook in-place. See KAAN-ACTION-LEGAL.md §AUDIO-06."
    )


def test_release_yml_placeholder_gate_preserved(release_yml_text: str):
    """RESEARCH Pitfall 6 regression guard — gate job must not disappear."""
    assert "placeholder-pubkey-gate" in release_yml_text, (
        "PITFALL 6 REGRESSION: release.yml no longer has the "
        "placeholder-pubkey-gate job. The Phase 18-05 gate against the "
        "TAURI_UPDATER_PLACEHOLDER sentinel was the only CI-side guard "
        "against shipping an unsigned-updater release. Restore the job. "
        "See .planning/phases/40-anti-slop-audio-port/40-RESEARCH.md "
        "§State of the Art Pitfall 6 prevention."
    )


def test_legal_md_has_audio_06_runbook(legal_md_text: str):
    """KAAN-ACTION-LEGAL.md must document the AUDIO-06 discharge protocol."""
    assert "AUDIO-06" in legal_md_text, (
        "KAAN-ACTION-LEGAL.md missing the '## AUDIO-06' runbook section "
        "(Tauri ed25519 updater key rotation). Plan 40-05 appends it."
    )
    # The discharge commands from RESEARCH §AUDIO-06 Code Examples.
    assert "tauri-apps/cli signer generate" in legal_md_text, (
        "AUDIO-06 runbook missing the `tauri signer generate` step."
    )
    assert "TAURI_UPDATER_PRIVATE_KEY" in legal_md_text, (
        "AUDIO-06 runbook missing the `gh secret set "
        "TAURI_UPDATER_PRIVATE_KEY` step."
    )


def test_pre_discharge_invariants(
    is_pre_discharge: bool,
    pubkey_decoded: str,
    pubkey_value: str,
):
    """Pre-discharge: dev key fingerprint embedded in base64 comment."""
    if not is_pre_discharge:
        pytest.skip("Post-discharge mode — exercised by separate assertions.")
    # The dev-key fingerprint is the engineering pre-stage sentinel.
    assert DEV_KEY_FINGERPRINT in pubkey_decoded
    # The pubkey base64-decodes (sanity).
    assert pubkey_value
    # The decoded body has the minisign comment line.
    assert MINISIGN_COMMENT_PREFIX in pubkey_decoded, (
        "Dev key present but the minisign comment convention is "
        "missing from the decoded body. The 2026-05-13 dev key was "
        "generated with `tauri signer generate` which always emits "
        "this prefix — did someone hand-edit the base64?"
    )


def test_post_discharge_invariants(
    is_pre_discharge: bool,
    pubkey_value: str,
    pubkey_decoded: str,
    tauri_conf_text: str,
):
    """Post-discharge: dev-key sentinel gone; minisign envelope intact."""
    if is_pre_discharge:
        pytest.skip("Pre-discharge mode — exercised by separate assertions.")
    # The pubkey base64-decodes to a minisign comment + key pair.
    assert MINISIGN_COMMENT_PREFIX in pubkey_decoded, (
        "PARTIAL-DISCHARGE DETECTED: dev-key fingerprint gone but the "
        "decoded pubkey does not start with the minisign comment "
        "convention. Did the rotation paste a non-tauri-signer key? "
        "Re-run `npx @tauri-apps/cli signer generate --no-password` "
        "and copy the .pub file body verbatim."
    )
    # The Plan 40-05 comment block must still be present (audit trail).
    # It describes the rotation that just happened.
    assert "Plan 40-05" in tauri_conf_text, (
        "PARTIAL-DISCHARGE DETECTED: pubkey rotated but the "
        "'Plan 40-05 — production key rotation' comment block in "
        "tauri.conf.json5 was deleted. Keep it for audit trail; "
        "update the runbook reference in-line if needed."
    )
