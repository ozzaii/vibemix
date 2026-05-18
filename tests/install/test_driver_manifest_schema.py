"""Validate installer/companion/driver_manifest.json shape.

Phase 49 Plan 01 — driver-fetch manifest schema validation.

Per ROADMAP P49 SUCCESS_CRITERION #4 + INSTALL-04: the companion driver fetch
reads SHA-256 + URL + version + license-ack from a single source-of-truth JSON.
This test asserts the manifest is well-formed and URL allowlisted.

SHA-256 placeholder discharge: until SignPath cert lands (Kaan-action
§INSTALL-COMPANION-SIGN), sha256 values may start with `PLACEHOLDER_`. The
verifier surfaces a WARNING for placeholders but does NOT fail.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

MANIFEST = Path(__file__).resolve().parents[2] / "installer" / "companion" / "driver_manifest.json"
URL_ALLOWLIST = (
    "https://existential.audio/",
    "https://vb-audio.com/",
)
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PLACEHOLDER_PREFIX = "PLACEHOLDER_"


def _load_manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def test_manifest_file_exists():
    assert MANIFEST.exists(), f"Manifest missing at {MANIFEST}"


def test_manifest_is_valid_json():
    _load_manifest()  # raises on invalid JSON


def test_manifest_has_drivers_block():
    d = _load_manifest()
    assert "drivers" in d, "Top-level `drivers` key required"
    assert "blackhole_2ch" in d["drivers"], "blackhole_2ch entry required"
    assert "vb_cable" in d["drivers"], "vb_cable entry required"


def test_driver_urls_in_allowlist():
    d = _load_manifest()
    for name, entry in d["drivers"].items():
        url = entry.get("url", "")
        ok = any(url.startswith(prefix) for prefix in URL_ALLOWLIST)
        assert ok, f"Driver {name} URL {url} not in allowlist {URL_ALLOWLIST}"


def test_sha256_is_64hex_or_placeholder():
    d = _load_manifest()
    for name, entry in d["drivers"].items():
        sha = entry.get("sha256", "")
        ok = SHA256_RE.match(sha) is not None or sha.startswith(PLACEHOLDER_PREFIX)
        assert ok, f"Driver {name} sha256={sha!r} must be 64-hex or PLACEHOLDER_*"


def test_vendor_signed_is_true_bool():
    d = _load_manifest()
    for name, entry in d["drivers"].items():
        assert entry.get("vendor_signed") is True, f"{name}.vendor_signed must be true"


def test_license_ack_text_non_empty():
    d = _load_manifest()
    for name, entry in d["drivers"].items():
        text = entry.get("license_ack_text", "")
        assert len(text) > 20, f"{name}.license_ack_text too short ({text!r})"


def test_required_fields_present():
    """vendor, version, url, sha256, vendor_signed, license, license_ack_text all required."""
    d = _load_manifest()
    required = {"vendor", "version", "url", "sha256", "vendor_signed", "license", "license_ack_text", "platform"}
    for name, entry in d["drivers"].items():
        missing = required - entry.keys()
        assert not missing, f"{name} missing fields: {missing}"


def test_platform_values_valid():
    d = _load_manifest()
    assert d["drivers"]["blackhole_2ch"]["platform"] == "darwin"
    assert d["drivers"]["vb_cable"]["platform"] == "win32"


def test_vb_cable_has_silent_flag():
    d = _load_manifest()
    assert d["drivers"]["vb_cable"].get("silent_flag") == "/S"
