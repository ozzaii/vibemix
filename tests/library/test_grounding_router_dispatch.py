# SPDX-License-Identifier: Apache-2.0
"""Plan 41-01 / Task 2 — library/grounding.py routes via ModelRouter.

The grounding pipeline used to inline ``model="gemini-embedding-2"`` at
the ``embed_content`` call site. Post-migration the literal is replaced
with the router-derived constant from ``library.embed``. This test
locks the contract that no model literal remains in ``grounding.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

import vibemix.library.grounding as grounding_mod
from vibemix.library.embed import GEMINI_EMBEDDING_MODEL
from vibemix.llm.model_router import resolve

# Patterns the CI grep gate also checks — kept in sync intentionally.
_MODEL_LITERAL_RE = re.compile(
    r"gemini-3-flash|gemini-3-pro|gemini-embedding-|gemini-3\.1-flash|"
    r"gemini-2\.5-flash"
)


def test_library_grounding_module_loads() -> None:
    """Module imports cleanly post-migration."""
    assert grounding_mod is not None


def test_library_grounding_uses_router_derived_constant() -> None:
    """No inline model literal remains in grounding.py source.

    The pre-migration code carried ``model="gemini-embedding-2"`` inline
    at line 122. Post-migration that string must come from the router
    (either via ``GEMINI_EMBEDDING_MODEL`` re-export or a direct
    ``resolve("embedding")[0]`` call).
    """
    src_path = Path(grounding_mod.__file__)
    src = src_path.read_text(encoding="utf-8")
    # Strip the module docstring + comments — those are allowed to mention
    # model names by name. We only check executable code lines.
    code_lines = [
        line
        for line in src.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    code_text = "\n".join(code_lines)
    # The actual call should use GEMINI_EMBEDDING_MODEL (or similar
    # router-derived name). No raw literal in code.
    # Strip string-literal occurrences inside docstrings — find every
    # triple-quoted block and remove it.
    code_no_docstrings = re.sub(
        r'"""[\s\S]*?"""', "", code_text, flags=re.MULTILINE
    )
    code_no_docstrings = re.sub(
        r"'''[\s\S]*?'''", "", code_no_docstrings, flags=re.MULTILINE
    )
    matches = _MODEL_LITERAL_RE.findall(code_no_docstrings)
    assert not matches, (
        f"grounding.py still carries inline model literal(s): {matches}. "
        "Migrate to router-derived constant."
    )


def test_grounding_embedding_constant_matches_router() -> None:
    """Sanity: the constant the grounding module consumes resolves
    correctly via the router."""
    assert GEMINI_EMBEDDING_MODEL == resolve("embedding")[0]
