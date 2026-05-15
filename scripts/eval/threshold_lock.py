# SPDX-License-Identifier: Apache-2.0
"""Phase 27 Plan 04 — eval/THRESHOLD-LOCK.md parser + autonomous-sign helpers.

Parses the markdown-with-frontmatter contract that locks the v2.1 eval
substance bar. Per V5 ASVS: ALWAYS uses ``yaml.safe_load`` (NEVER
``yaml.load``).

Public surface:
    - parse_threshold_lock_frontmatter(path) -> dict
    - is_signed(parsed) -> bool
    - autonomous_sign(path) -> dict
    - DEFAULT_THRESHOLDS: dict (CONTEXT EVAL-06 fallback)
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# CONTEXT EVAL-06 — kept in sync with eval/THRESHOLD-LOCK.md frontmatter.
DEFAULT_THRESHOLDS: dict[str, float] = {
    "f1_min": 0.80,
    "substance_min": 0.65,
    "cited_cosine_min": 0.4,
    "bypass_max": 0.15,
    "per_genre_f1_min": 0.70,
}

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_threshold_lock_frontmatter(path: Path | str) -> dict[str, Any]:
    """Read the THRESHOLD-LOCK markdown file; return its frontmatter dict.

    Uses ``yaml.safe_load`` exclusively (V5 ASVS: never the generic
    ``yaml.load`` — that path can deserialize arbitrary Python objects).
    """
    import yaml

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"threshold-lock not found: {path}")
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"no frontmatter found in {path}")
    front_yaml = match.group(1)
    parsed = yaml.safe_load(front_yaml)
    if not isinstance(parsed, dict):
        raise ValueError(
            f"frontmatter in {path} did not parse to a dict: {type(parsed).__name__}"
        )
    return parsed


def is_signed(parsed: dict[str, Any]) -> bool:
    """Return True iff ``kaan_signed`` is set to a non-false, non-empty string.

    "false" / "" / missing → False. "autonomous_phase27" or any real
    signature string → True.
    """
    signed = parsed.get("kaan_signed", False)
    if isinstance(signed, bool):
        return signed
    if isinstance(signed, str):
        return signed.strip().lower() not in {"", "false", "no"}
    return False


def autonomous_sign(path: Path | str) -> dict[str, Any]:
    """Rewrite the THRESHOLD-LOCK frontmatter to autonomous-signed state.

    Idempotent: if already signed with ``autonomous_phase27``, returns the
    existing parsed dict without modifying the file. Otherwise rewrites the
    frontmatter setting:
        - kaan_signed: autonomous_phase27
        - kaan_signed_at: <now UTC ISO8601>

    Also appends a one-line audit entry to the phase's KAAN-ACTION-LEGAL.md
    when present (suppresses duplicate appends).
    """
    import yaml

    path = Path(path)
    parsed = parse_threshold_lock_frontmatter(path)
    if parsed.get("kaan_signed") == "autonomous_phase27":
        return parsed

    parsed["kaan_signed"] = "autonomous_phase27"
    parsed["kaan_signed_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    text = path.read_text(encoding="utf-8")
    front_match = _FRONTMATTER_RE.match(text)
    if not front_match:
        raise ValueError(f"cannot autonomous-sign — no frontmatter in {path}")
    body = text[front_match.end():]
    new_front = yaml.safe_dump(parsed, sort_keys=False, default_flow_style=False)
    new_text = f"---\n{new_front}---\n{body}"
    path.write_text(new_text, encoding="utf-8")

    # Append audit entry to KAAN-ACTION-LEGAL.md (if present in same phase dir).
    legal_md = path.parent.parent / ".planning" / "phases"
    # Better: walk up to find the phase dir + KAAN-ACTION-LEGAL.md.
    project_root = path.resolve().parent.parent
    for phase_dir in (project_root / ".planning" / "phases").glob(
        "27-*"
    ):
        legal_path = phase_dir / "KAAN-ACTION-LEGAL.md"
        if legal_path.exists():
            legal_text = legal_path.read_text(encoding="utf-8")
            audit_line = (
                f"- {parsed['kaan_signed_at']}: "
                f"THRESHOLD-LOCK autonomous-signed by Phase 27 Plan 04 (autonomous_sign)."
            )
            if audit_line not in legal_text:
                legal_text = legal_text.rstrip() + "\n" + audit_line + "\n"
                legal_path.write_text(legal_text, encoding="utf-8")
            break

    return parsed
