# SPDX-License-Identifier: Apache-2.0
"""Grep gate: profile MUST NEVER appear in the per-turn prompt path (P60).

Pitfall P60: the long-term DJ profile lives in the GeminiContextCache body,
NOT in any per-turn prompt prefix. This test enforces the invariant by
scanning the agent's hot-path source for the substring "profile" — a single
slip-up that adds ``self._profile`` to ``llm_node`` would invalidate the
1024-token cache floor + 4-min refresh contract.

Allowed sites for the substring:
- :mod:`vibemix.agent.cache` — owns the cache section.
- :mod:`vibemix.agent.dj_cohost` — stores _profile in __init__ but never
  reads it in llm_node. We allow the substring inside __init__ + docstring;
  test fails if it appears inside the def llm_node body.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_profile_substring_absent_from_dj_cohost_llm_node() -> None:
    """Walk dj_cohost.py AST. Find the DJCoHostAgent.llm_node function. Assert
    its source body does NOT contain ``profile`` (case-insensitive)."""
    src = _read(PROJECT_ROOT / "src" / "vibemix" / "agent" / "dj_cohost.py")
    tree = ast.parse(src)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == "llm_node":
            found = True
            body_src = ast.unparse(node)
            # Strip docstring (first statement if str literal).
            docstring = ast.get_docstring(node) or ""
            stripped = body_src.replace(docstring, "")
            assert "profile" not in stripped.lower(), (
                "Pitfall P60 violation: 'profile' appears inside DJCoHostAgent.llm_node. "
                "Profile MUST live in GeminiContextCache only, NEVER per-turn."
            )
    assert found, "DJCoHostAgent.llm_node not found — adjust this test"


def test_profile_substring_absent_from_ai_coach_build_prompt() -> None:
    """AICoach.build_prompt is the second per-turn path (it builds the
    evidence packet). Same gate applies."""
    coach_src_path = PROJECT_ROOT / "src" / "vibemix" / "state" / "ai_coach.py"
    if not coach_src_path.exists():
        # Project layout may differ; fall back to a broad search.
        candidates = list((PROJECT_ROOT / "src" / "vibemix").rglob("ai_coach*.py"))
        if not candidates:
            return  # No AICoach module in source tree — phase-pre-existence path.
        coach_src_path = candidates[0]
    src = _read(coach_src_path)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_prompt":
            body_src = ast.unparse(node)
            docstring = ast.get_docstring(node) or ""
            stripped = body_src.replace(docstring, "")
            assert "profile" not in stripped.lower(), (
                f"P60 violation: 'profile' appears inside {coach_src_path.name} "
                "AICoach.build_prompt. Profile lives in the cache, not per-turn."
            )


def test_profile_substring_only_in_allowed_per_turn_locations() -> None:
    """Broad grep across the per-turn hot path. Allowed locations: cache.py +
    dj_cohost.py __init__ + storage path tokens. Anywhere else inside the
    agent or state modules is a P60 violation candidate.

    This is intentionally strict: any new "profile" reference inside the
    agent hot-path requires updating this allowlist consciously.
    """
    hot_path = PROJECT_ROOT / "src" / "vibemix" / "agent"
    allowed_files = {"cache.py", "dj_cohost.py", "__init__.py"}
    pattern = re.compile(r"profile", re.IGNORECASE)
    for py in hot_path.rglob("*.py"):
        if py.name in allowed_files:
            continue
        if "__pycache__" in py.parts:
            continue
        content = _read(py)
        # Strip comments + docstrings (cheap heuristic: skip whole lines that
        # are entirely comments to reduce false positives from explanatory text).
        non_comment = "\n".join(
            line for line in content.splitlines() if not line.strip().startswith("#")
        )
        if pattern.search(non_comment):
            raise AssertionError(
                f"P60 violation: 'profile' appears in {py.relative_to(PROJECT_ROOT)}. "
                "Only cache.py + dj_cohost.py may reference profile in the agent layer."
            )
