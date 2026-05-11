# SPDX-License-Identifier: Apache-2.0
"""GenreProfile dataclass + JSON loader + active-profile singleton.

Phase 6 Wave 1 — the genre profile data layer. Read by:
- Wave 2: ``validate_bpm`` (profile.bpm_range), ``VocalDetector`` (optional)
- Wave 3: ``classify_phase_percentile`` (every threshold field), ``state_refresh_loop``
- Wave 4: ``__main__.apply_genre_env`` (active-profile singleton)

Locked schema (06-CONTEXT.md §Genre Profile Shape):

    {
      "name": "techno",
      "label": "Techno / Hard Tek / Acidcore",
      "bpm_range": [125, 175],
      "absolute_thresholds": {
        "silent_rms": 0.012, "low_rms": 0.040, "peak_rms": 0.110
      },
      "expected_crest_factor": [3.5, 6.5],
      "band_signature": {
        "sub": [0.25, 0.45], "low": [0.20, 0.35],
        "mid": [0.10, 0.25], "high": [0.05, 0.15]
      },
      "vocal_likelihood": "rare",
      "build_climb_threshold": 0.025,
      "breakdown_ratio": 0.4,
      "drop_jump_threshold": 0.060
    }

Schema validator is hand-written (no pydantic — Critical Constraint 6: no new
heavy deps). Validator raises ``ValueError`` on missing or malformed fields —
silent defaults would defeat the locked-schema contract (CONTEXT scope_reduction
prohibition).

Active-profile singleton:
- Module-level mutable ``_ACTIVE_PROFILE``.
- ``set_active_profile(None)`` is a valid call that disables genre mode and
  flips ``state_refresh_loop`` back to the Phase 3 absolute-threshold path
  (Critical Constraint 8).
"""

from __future__ import annotations

import importlib.resources
import json
from dataclasses import dataclass

_PROFILES_PKG = "vibemix.state.genre.profiles"
_VOCAL_LIKELIHOODS = frozenset({"rare", "occasional", "frequent", "very_frequent"})

# Module-level mutable singleton. Phase 6 Wave 4 ``__main__.apply_genre_env``
# sets this once at startup; Phase 12 Settings UI re-sets it mid-session.
_ACTIVE_PROFILE: GenreProfile | None = None


@dataclass(frozen=True)
class GenreProfile:
    """Frozen, value-typed genre profile. Mirrors the locked JSON schema 1:1."""

    name: str
    label: str
    bpm_range: tuple[float, float]
    silent_rms: float
    low_rms: float
    peak_rms: float
    expected_crest_factor: tuple[float, float]
    band_signature: dict[str, tuple[float, float]]
    vocal_likelihood: str
    build_climb_threshold: float
    breakdown_ratio: float
    drop_jump_threshold: float


def _pair(value, *, field: str, profile_name: str) -> tuple[float, float]:
    """Validate a list-of-2 numeric pair, return as (float, float) tuple."""
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(
            f"profile {profile_name}: field {field!r} must be a 2-element list, got {value!r}"
        )
    lo, hi = value
    if not isinstance(lo, (int, float)) or not isinstance(hi, (int, float)):
        raise ValueError(
            f"profile {profile_name}: field {field!r} must contain numbers, got {value!r}"
        )
    return (float(lo), float(hi))


def _parse_profile(payload: dict) -> GenreProfile:
    """Validate JSON payload, return a frozen GenreProfile. Raises ValueError
    on missing/malformed fields — silent defaults are explicitly prohibited
    (CONTEXT scope_reduction)."""
    if not isinstance(payload, dict):
        raise ValueError(f"profile payload must be a dict, got {type(payload).__name__}")

    name = payload.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("profile: field 'name' is required and must be a non-empty str")

    label = payload.get("label")
    if not isinstance(label, str) or not label:
        raise ValueError(f"profile {name}: field 'label' is required and must be a non-empty str")

    if "bpm_range" not in payload:
        raise ValueError(f"profile {name}: field 'bpm_range' is required")
    bpm_range = _pair(payload["bpm_range"], field="bpm_range", profile_name=name)

    abs_thr = payload.get("absolute_thresholds")
    if not isinstance(abs_thr, dict):
        raise ValueError(
            f"profile {name}: field 'absolute_thresholds' is required and must be a dict"
        )
    for key in ("silent_rms", "low_rms", "peak_rms"):
        if key not in abs_thr:
            raise ValueError(f"profile {name}: 'absolute_thresholds.{key}' is required")
        if not isinstance(abs_thr[key], (int, float)):
            raise ValueError(
                f"profile {name}: 'absolute_thresholds.{key}' must be a number, "
                f"got {abs_thr[key]!r}"
            )
        if abs_thr[key] < 0:
            raise ValueError(
                f"profile {name}: 'absolute_thresholds.{key}' must be non-negative, "
                f"got {abs_thr[key]!r}"
            )

    silent_rms = float(abs_thr["silent_rms"])
    low_rms = float(abs_thr["low_rms"])
    peak_rms = float(abs_thr["peak_rms"])

    if "expected_crest_factor" not in payload:
        raise ValueError(f"profile {name}: field 'expected_crest_factor' is required")
    expected_crest = _pair(
        payload["expected_crest_factor"], field="expected_crest_factor", profile_name=name
    )

    band_sig_raw = payload.get("band_signature")
    if not isinstance(band_sig_raw, dict):
        raise ValueError(f"profile {name}: field 'band_signature' is required and must be a dict")
    band_signature: dict[str, tuple[float, float]] = {}
    for band_key in ("sub", "low", "mid", "high"):
        if band_key not in band_sig_raw:
            raise ValueError(f"profile {name}: 'band_signature.{band_key}' is required")
        band_signature[band_key] = _pair(
            band_sig_raw[band_key],
            field=f"band_signature.{band_key}",
            profile_name=name,
        )

    vocal_likelihood = payload.get("vocal_likelihood")
    if vocal_likelihood not in _VOCAL_LIKELIHOODS:
        raise ValueError(
            f"profile {name}: 'vocal_likelihood' must be one of {sorted(_VOCAL_LIKELIHOODS)}, "
            f"got {vocal_likelihood!r}"
        )

    for scalar in ("build_climb_threshold", "breakdown_ratio", "drop_jump_threshold"):
        if scalar not in payload:
            raise ValueError(f"profile {name}: field {scalar!r} is required")
        if not isinstance(payload[scalar], (int, float)):
            raise ValueError(
                f"profile {name}: field {scalar!r} must be a number, got {payload[scalar]!r}"
            )

    return GenreProfile(
        name=name,
        label=label,
        bpm_range=bpm_range,
        silent_rms=silent_rms,
        low_rms=low_rms,
        peak_rms=peak_rms,
        expected_crest_factor=expected_crest,
        band_signature=band_signature,
        vocal_likelihood=vocal_likelihood,
        build_climb_threshold=float(payload["build_climb_threshold"]),
        breakdown_ratio=float(payload["breakdown_ratio"]),
        drop_jump_threshold=float(payload["drop_jump_threshold"]),
    )


def list_profiles() -> list[str]:
    """Return sorted list of profile stems (e.g. ['disco','drum_and_bass','house','pop','techno'])."""
    pkg = importlib.resources.files(_PROFILES_PKG)
    names: list[str] = []
    for entry in pkg.iterdir():
        # entry is a Traversable (may be a file or subdir).
        try:
            if not entry.is_file():
                continue
        except Exception:
            continue
        n = entry.name
        if not n.endswith(".json"):
            continue
        names.append(n[: -len(".json")])
    return sorted(names)


def load_profile(name: str) -> GenreProfile | None:
    """Load a profile by name. Returns None if not present; raises ValueError
    on schema drift."""
    if not isinstance(name, str) or not name:
        return None
    resource = importlib.resources.files(_PROFILES_PKG).joinpath(f"{name}.json")
    try:
        if not resource.is_file():
            return None
    except Exception:
        return None
    with resource.open("rb") as f:
        payload = json.load(f)
    return _parse_profile(payload)


def set_active_profile(name: str | None) -> None:
    """Set the module-level active profile. ``name=None`` disables genre mode
    and flips ``state_refresh_loop`` back to the Phase 3 absolute-threshold
    path (Critical Constraint 8). Raises ValueError on unknown name."""
    global _ACTIVE_PROFILE
    if name is None:
        _ACTIVE_PROFILE = None
        return
    prof = load_profile(name)
    if prof is None:
        raise ValueError(f"unknown profile: {name!r}")
    _ACTIVE_PROFILE = prof


def get_active_profile() -> GenreProfile | None:
    """Return the currently-active profile or None (genre mode disabled)."""
    return _ACTIVE_PROFILE
