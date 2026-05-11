# SPDX-License-Identifier: Apache-2.0
"""vibemix.prompts — Phase 10 prompt-template-matrix layer.

Six prompt cells (3 skill levels × 2 modes) + the anti-slop substrate:
negative dictionary regex bans, post-hoc filter, TurnHistory ring,
<silence/> short-circuit, Coach scorecard.

Public API:
    from vibemix.prompts import build_system_instruction
    from vibemix.prompts import filter_for_slop
    from vibemix.prompts import TurnHistory
    from vibemix.prompts import summarize_session
    from vibemix.prompts import NEGATIVE_PHRASES, NEGATIVE_REGEX

Backward compat: ``vibemix.agent.persona.SYSTEM_INSTRUCTION`` is now a thin
re-export of ``build_system_instruction("intermediate", "hype")`` and stays
byte-identical to the v4 port from Phase 4.
"""

from __future__ import annotations

from vibemix.prompts.filter import filter_for_slop
from vibemix.prompts.matrix import (
    COACH_BEGINNER,
    COACH_INTERMEDIATE,
    COACH_PRO,
    HYPE_BEGINNER,
    HYPE_INTERMEDIATE,
    HYPE_PRO,
    build_system_instruction,
)
from vibemix.prompts.negative_dict import NEGATIVE_PHRASES, NEGATIVE_REGEX
from vibemix.prompts.scorecard import summarize_session
from vibemix.prompts.turn_history import TurnHistory

__all__ = [
    "COACH_BEGINNER",
    "COACH_INTERMEDIATE",
    "COACH_PRO",
    "HYPE_BEGINNER",
    "HYPE_INTERMEDIATE",
    "HYPE_PRO",
    "NEGATIVE_PHRASES",
    "NEGATIVE_REGEX",
    "TurnHistory",
    "build_system_instruction",
    "filter_for_slop",
    "summarize_session",
]
