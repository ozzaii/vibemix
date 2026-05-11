# SPDX-License-Identifier: Apache-2.0
"""Backward-compat thin re-export of the Phase 10 prompt-template-matrix
default cell.

``SYSTEM_INSTRUCTION`` resolves to ``HYPE_INTERMEDIATE`` — byte-identical to
the original Phase 4 v4 port (``cohost_v4.py:150-213``). The single source of
truth lives in ``vibemix.prompts.matrix.HYPE_INTERMEDIATE``.

Phase 10 broke the single SYSTEM_INSTRUCTION constant into a 6-cell matrix
under ``vibemix.prompts.matrix`` (3 skill levels × 2 modes). Existing callers
that import ``SYSTEM_INSTRUCTION`` from this module continue to work; new
callers should reach for ``vibemix.prompts.build_system_instruction(skill, mode)``
directly.

Anti-hallucination invariants are load-bearing IP per CLAUDE.md — DO NOT
paraphrase the underlying prompt body.
"""

from __future__ import annotations

from vibemix.prompts.matrix import HYPE_INTERMEDIATE, build_system_instruction

# Backward-compat: SYSTEM_INSTRUCTION === HYPE_INTERMEDIATE === v4 port.
SYSTEM_INSTRUCTION: str = build_system_instruction("intermediate", "hype")

# Sanity guard at import time — if the matrix dispatcher ever drifts away
# from byte-equality with HYPE_INTERMEDIATE the failure surfaces here, not
# silently downstream.
assert SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE  # nosec B101

__all__ = ["SYSTEM_INSTRUCTION"]
