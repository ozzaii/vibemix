# SPDX-License-Identifier: Apache-2.0
"""Phase 70 Plan 70P01 — schema-pin for docs/assets/MANIFEST.yaml (GH-04).

The asset-reproducibility manifest is the single source of truth for which
docs/assets/ files scripts/regenerate_assets.sh owns. A silent malform here
(a typo'd key, a non-hex sha, a stale opt_out path) would either weaken the
asset-bitrot CI gate or make it fail spuriously. These tests pin the exact
shape so future edits can't drift it.

Run with: PYTHONPATH=src python3 -m pytest tests/repo/test_asset_manifest_shape.py -q
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "docs" / "assets" / "MANIFEST.yaml"

_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_ASSET_KEYS = {"path", "source", "sha256", "generator"}


def _load() -> dict:
    assert MANIFEST.exists(), (
        f"Missing required manifest at {MANIFEST.relative_to(REPO_ROOT)}. "
        "GH-04 requires this file. See Plan 70P01 Task 1."
    )
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(data, dict), (
        f"MANIFEST.yaml must parse to a mapping, got {type(data).__name__}."
    )
    return data


def test_manifest_parses() -> None:
    """Test 1 — MANIFEST.yaml exists and yaml.safe_load parses without error."""
    _load()


def test_top_level_keys_exact() -> None:
    """Test 2 — top-level keys are EXACTLY {assets, opt_out}.

    Set-equality so an extra or typo'd top-level key trips the gate.
    """
    data = _load()
    assert set(data) == {"assets", "opt_out"}, (
        f"MANIFEST.yaml top-level keys must be exactly "
        f"{{'assets', 'opt_out'}}, got {sorted(data)}."
    )


def test_assets_entries_have_exact_keys() -> None:
    """Test 3 — `assets` is a list; every entry is a dict with EXACTLY
    {path, source, sha256, generator}."""
    data = _load()
    assets = data["assets"]
    assert isinstance(assets, list), (
        f"MANIFEST.yaml `assets` must be a list, got {type(assets).__name__}."
    )
    for i, entry in enumerate(assets):
        assert isinstance(entry, dict), (
            f"assets[{i}] must be a mapping, got {type(entry).__name__}."
        )
        assert set(entry) == _ASSET_KEYS, (
            f"assets[{i}] keys must be exactly {sorted(_ASSET_KEYS)}, "
            f"got {sorted(entry)}."
        )


def test_assets_sha256_format() -> None:
    """Test 4 — every assets[].sha256 is the literal PENDING or 64-hex lower."""
    data = _load()
    for i, entry in enumerate(data["assets"]):
        sha = entry["sha256"]
        assert sha == "PENDING" or _SHA256_RE.fullmatch(str(sha)), (
            f"assets[{i}].sha256 must be 'PENDING' or a 64-char lowercase "
            f"hex string, got {sha!r}."
        )


def test_opt_out_paths_exist() -> None:
    """Test 5 — `opt_out` is a list of strings; every path points at an
    existing file under REPO_ROOT (catches a stale opt_out entry)."""
    data = _load()
    opt_out = data["opt_out"]
    assert isinstance(opt_out, list), (
        f"MANIFEST.yaml `opt_out` must be a list, got {type(opt_out).__name__}."
    )
    for p in opt_out:
        assert isinstance(p, str), (
            f"opt_out entries must be strings, got {type(p).__name__}: {p!r}."
        )
        target = REPO_ROOT / p
        assert target.is_file(), (
            f"opt_out path {p!r} does not point at an existing file "
            f"(resolved {target}). Remove the stale entry or fix the path."
        )


def test_no_path_in_both_assets_and_opt_out() -> None:
    """Test 6 — no path appears in BOTH `assets` and `opt_out`.

    A path is either source-generated (assets) or bespoke (opt_out), never both.
    """
    data = _load()
    asset_paths = {entry["path"] for entry in data["assets"]}
    opt_out_paths = set(data["opt_out"])
    overlap = asset_paths & opt_out_paths
    assert not overlap, (
        f"These paths appear in BOTH `assets` and `opt_out`: {sorted(overlap)}. "
        "A path is either source-generated or bespoke, never both."
    )
