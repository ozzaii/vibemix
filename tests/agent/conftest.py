# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for tests/agent/."""

from __future__ import annotations

import ast
from pathlib import Path


def v4_persona_string() -> str:
    """Return the canonical SYSTEM_INSTRUCTION body extracted from cohost_v4.py
    via AST so we're insensitive to which line numbers the triple-quotes
    land on. The v4 file is READ-ONLY (Kaan runs it live) — extraction must
    not modify it."""
    v4_src = Path("cohost_v4.py").read_text()
    tree = ast.parse(v4_src)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "SYSTEM_INSTRUCTION" for t in node.targets
        ):
            return node.value.value
    raise RuntimeError("SYSTEM_INSTRUCTION not found in cohost_v4.py")
