# SPDX-License-Identifier: Apache-2.0
"""Phase 27-01 — Corpus diversity + integrity validator (referenced by Plan 03).

The eval corpus must satisfy CONTEXT EVAL-03 + Pitfall P43:
    - ≥ 6 sessions total
    - ≥ 3 distinct genres
    - Hard Tek share ≤ 70% (no single-genre overfit)

Manifest schema (eval/corpus/manifest.json — produced by Plan 03):

    {
        "version": "1",
        "sessions": [
            {"id": "hard_tek_01", "genre": "hard_tek", "duration_s": 1800, "source": "..."},
            ...
        ],
        "hard_tek_pct": 0.34,            # computed; validator re-derives + asserts
        "genre_distribution": {           # computed; validator re-derives + asserts
            "hard_tek": 2, "techno": 2, "house": 2
        },
        "sessions_min": 6
    }

The validator is invoked by Plan 04 CI gate AND by ``replay_harness --corpus``
during session glob.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MAX_HARD_TEK_PCT = 0.70
MIN_DISTINCT_GENRES = 3
MIN_SESSIONS = 6


def _canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_manifest(manifest_path: Path | str) -> dict[str, Any]:
    """Validate the corpus manifest at ``manifest_path``.

    Returns
    -------
    {
        "valid": bool,
        "errors": list[str],   # empty when valid
        "manifest_hash": str,  # 12-char SHA-256 prefix of canonical JSON
    }
    """
    path = Path(manifest_path)
    errors: list[str] = []

    if not path.exists():
        return {
            "valid": False,
            "errors": [f"manifest not found: {path}"],
            "manifest_hash": "",
        }

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "errors": [f"manifest is not valid JSON: {e}"],
            "manifest_hash": "",
        }

    sessions = manifest.get("sessions", [])
    if not isinstance(sessions, list):
        errors.append("'sessions' must be a list")
        sessions = []

    declared_min = manifest.get("sessions_min", MIN_SESSIONS)
    if len(sessions) < max(declared_min, MIN_SESSIONS):
        errors.append(
            f"sessions count {len(sessions)} below minimum "
            f"{max(declared_min, MIN_SESSIONS)} (CONTEXT EVAL-03)"
        )

    genres = [s.get("genre", "") for s in sessions]
    distinct = sorted({g for g in genres if g})
    if len(distinct) < MIN_DISTINCT_GENRES:
        errors.append(
            f"distinct genre count {len(distinct)} below minimum "
            f"{MIN_DISTINCT_GENRES} (CONTEXT EVAL-03)"
        )

    hard_tek_count = sum(1 for g in genres if g == "hard_tek")
    if sessions:
        derived_hard_tek_pct = hard_tek_count / len(sessions)
    else:
        derived_hard_tek_pct = 0.0

    if derived_hard_tek_pct > MAX_HARD_TEK_PCT:
        errors.append(
            f"hard_tek_pct {derived_hard_tek_pct:.2%} exceeds "
            f"{MAX_HARD_TEK_PCT:.0%} cap (Pitfall P43)"
        )

    declared_pct = manifest.get("hard_tek_pct")
    if declared_pct is not None:
        if abs(declared_pct - derived_hard_tek_pct) > 0.001:
            errors.append(
                f"declared hard_tek_pct {declared_pct} != derived "
                f"{round(derived_hard_tek_pct, 3)}"
            )

    declared_dist = manifest.get("genre_distribution")
    if declared_dist is not None:
        derived_dist: dict[str, int] = {}
        for g in genres:
            derived_dist[g] = derived_dist.get(g, 0) + 1
        if declared_dist != derived_dist:
            errors.append(
                f"declared genre_distribution {declared_dist} != "
                f"derived {derived_dist}"
            )

    manifest_hash = hashlib.sha256(_canonical_json_bytes(manifest)).hexdigest()[:12]

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "manifest_hash": manifest_hash,
    }
