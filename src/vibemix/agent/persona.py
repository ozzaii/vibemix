# SPDX-License-Identifier: Apache-2.0
"""Backward-compat thin re-export of the Phase 10 prompt-template-matrix
default cell.

``SYSTEM_INSTRUCTION`` resolves to ``HYPE_INTERMEDIATE`` — byte-identical to
the original Phase 4 v4 port (``cohost_v4.py:150-213``). The single source of
truth lives in ``vibemix.prompts.matrix.HYPE_INTERMEDIATE``.

Phase 10 broke the single SYSTEM_INSTRUCTION constant into a 6-cell matrix
under ``vibemix.prompts.matrix`` (3 skill levels x 2 modes). Existing callers
that import ``SYSTEM_INSTRUCTION`` from this module continue to work; new
callers should reach for ``vibemix.prompts.build_system_instruction(skill, mode)``
directly.

Anti-hallucination invariants are load-bearing IP per CLAUDE.md — DO NOT
paraphrase the underlying prompt body.
"""

from __future__ import annotations

from vibemix.prompts.matrix import HYPE_INTERMEDIATE, build_system_instruction

# Backward-compat: SYSTEM_INSTRUCTION === HYPE_INTERMEDIATE === v4 port.
# Plan 18-03 + Plan 20-02 + Plan 41-04: opt out of all three optional
# appends (citation-grammar block, fail-soft IM_LISTENING_FRAGMENT, TTS
# tag DSL block) so SYSTEM_INSTRUCTION stays byte-identical to the v4
# cell constant. All three additions are made at the dispatcher
# boundary (DJCoHostAgent's prompt_body via the default
# include_*=True params), not at this backward-compat re-export — this
# keeps the v4-byte-identity invariant green AND lets the live agent
# get every addition via the dispatcher's default path.
SYSTEM_INSTRUCTION: str = build_system_instruction(
    "intermediate",
    "hype",
    include_citation_grammar=False,
    include_listening_fallback=False,
    include_tag_dsl=False,
)

# Sanity guard at import time — if the matrix dispatcher ever drifts away
# from byte-equality with HYPE_INTERMEDIATE the failure surfaces here, not
# silently downstream.
assert SYSTEM_INSTRUCTION is HYPE_INTERMEDIATE  # nosec B101

__all__ = ["SYSTEM_INSTRUCTION"]
