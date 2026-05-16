# SPDX-License-Identifier: Apache-2.0
"""Phase 31 Plan 04 — Emote-tag parser.

Gemini response text may contain inline ``[emote:NAME]`` markers that
fire the priority-80 mascot reaction layer. Example:

    "Loving that bassline [emote:fist_pump] — keep it rolling [emote:nod]"

We extract the whitelisted intents and strip the tags from the
playback text so they never get sent to TTS.

Whitelist (load-bearing — Pitfall P47 anti-slop; matches
``MASCOT_REACTIONS`` in ``tauri/ui/src/mascot/types.ts``):

- ``wave``
- ``point_left``
- ``point_right``
- ``fist_pump``
- ``nod``
- ``headbang``
- ``surprised``

Unknown tags are silently dropped from the intent list but ALSO stripped
from the output text (so an LLM hallucination like ``[emote:wink]``
doesn't reach TTS literal-readout). The caller is expected to log
unknown tags via Hermes/events.jsonl for prompt-tuning.
"""

from __future__ import annotations

import re
from typing import Final, Literal

MascotReaction = Literal[
    "wave",
    "point_left",
    "point_right",
    "fist_pump",
    "nod",
    "headbang",
    "surprised",
]

# Frozen whitelist — mirrors MASCOT_REACTIONS on the TS side.
REACTION_WHITELIST: Final[frozenset[str]] = frozenset(
    {
        "wave",
        "point_left",
        "point_right",
        "fist_pump",
        "nod",
        "headbang",
        "surprised",
    }
)

# Match `[emote:<lowercase_or_underscore>]`. Case-sensitive on purpose —
# we don't want `[Emote:Wave]` to slip through; the LLM prompt template
# pins the exact form.
_EMOTE_TAG_RE: Final[re.Pattern[str]] = re.compile(
    r"\[emote:([a-z_]+)\]"
)


def parse_emote_tags(text: str) -> list[str]:
    """Return the ordered list of WHITELISTED emote intents in ``text``.

    Unknown tag names are dropped silently. Order matches first-seen
    appearance in the source text; duplicates are preserved (a user may
    legitimately want two fist-pumps in a row).
    """
    intents: list[str] = []
    for m in _EMOTE_TAG_RE.finditer(text):
        name = m.group(1)
        if name in REACTION_WHITELIST:
            intents.append(name)
    return intents


def strip_emote_tags(text: str) -> tuple[str, list[str]]:
    """Strip ALL ``[emote:*]`` tags from ``text`` AND return whitelisted intents.

    Unknown tags are still stripped from the returned text (so the LLM
    can't smuggle them into TTS) but they DON'T appear in the intent
    list. Whitespace around removed tags is normalized — runs of spaces
    collapse to a single space, and leading/trailing whitespace trims.
    """
    intents = parse_emote_tags(text)
    cleaned = _EMOTE_TAG_RE.sub("", text)
    # Collapse runs of whitespace and trim — without this, the stripped
    # text reads "Loving that bassline  — keep it rolling " with a
    # double-space gap where the tag used to be.
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, intents
