# SPDX-License-Identifier: Apache-2.0
"""DeckVisionReader — the SEPARATE structured-output Gemini deck-read (Plan 59-05, DECK-02).

The UNIVERSAL cross-app fallback leg of the source ladder (Serato / djay /
Traktor / Engine — zero per-app parsers). This is the single biggest
hallucination risk in Phase 59: ``dj_cohost.py`` sets ``screen_jpeg = None`` as
a deliberate v4 anti-hallucination killswitch ("Screen + MIDI metadata caused
hallucination"). Re-introducing vision is NOT a one-line flip of that line — it
is a constrained, structured, low-frequency, eval-gated call that lives OUTSIDE
the reaction path entirely.

What makes this safe (vs the screen Part v4 removed):

  ① SEPARATE call — NOT the reaction turn. The reaction prompt stays de-screened
     (``dj_cohost.py:screen_jpeg = None`` is UNTOUCHED — grep-asserted by the
     plan). This reader issues its own dedicated, non-streaming Gemini call.
  ② STRUCTURED output — ``response_mime_type="application/json"`` +
     ``response_schema`` for ``{"decks":[{"side","title","key","bpm"}]}`` with an
     explicit "if a field is not clearly visible, return null" instruction. The
     constrained schema is what closes the free-text hallucination class that
     killed the original screen Part.
  ③ NULL-DEFENSIVE parse — any null / missing field → ``None`` → confidence=0 /
     unknown. No free-text guess ever reaches deck-state.
  ④ LOWER confidence than XML — a misread badge is a silent error, the SAME
     hallucination class as a wrong library tag, so ``VISION_CONF`` sits BELOW
     the XML floor (``deck_poller.XML_CONF_FLOOR``). Vision can never out-cite a
     pre-analyzed tag.
  ⑤ CADENCE-BOUNDED — a debounce gate refuses reads more often than the
     configured interval (~5-10s, track/screen-change only), and the audio-only
     tier skips the read entirely. Never per-10Hz-tick (cost bound).
  ⑥ GRACEFUL — every exception is swallowed (mirrors ``TrackInfo.poll_once`` /
     ``DeckPoller.poll_once`` discipline); the reader returns an empty/unknown
     map, never raising into the poller.

The returned key is normalized via ``harmonics.to_camelot`` (vision may emit
Camelot, musical, or open-key notation). ``DeckTrack.key`` keeps the raw read;
``DeckTrack.camelot`` carries the normalized code (Pitfall 1 discipline).

GATING: this leg stays GATED OUT of ``DeckPoller`` live consumption until the
real-screenshot accuracy eval (``eval/deck_vision/run_eval.py``) clears the
documented floor on Kaan's rig corpus (the KAAN-ACTION checkpoint, Task 3). Vision
must NOT feed deck-state before that — the conservative-by-default state is "off".

Gemini-only (no other AI provider) per the project constraint.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any

from vibemix.state.deck_state import DeckTrack
from vibemix.state.harmonics import to_camelot

# ---------------------------------------------------------------------- #
# Vision confidence + cadence                                             #
# ---------------------------------------------------------------------- #

# Vision-sourced confidence. MUST stay BELOW deck_poller.XML_CONF_FLOOR (0.6) so
# a runtime badge misread can never out-cite a pre-analyzed XML tag. A misread
# key badge is a silent error of the SAME hallucination class as a wrong library
# tag (RESEARCH A3). Set conservatively until the eval (Task 3) measures the real
# achievable accuracy and the gate is signed off per app.
VISION_CONF: float = 0.5

# Default debounce interval (seconds). The reader refuses a second read sooner
# than this — vision is a track-change / screen-change signal, never per-tick
# (RESEARCH A2, ~5-10s band; cost bound + DoS mitigation T-59-05-03).
DEFAULT_VISION_INTERVAL_S: float = 7.0

# The JSON schema for the structured deck-read. Kept as a plain dict so the call
# works with both ``types.GenerateContentConfig(response_schema=...)`` and the
# dict-config form, and so the schema is trivially inspectable in tests.
_DECK_READ_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "decks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "side": {"type": "string", "nullable": True},
                    "title": {"type": "string", "nullable": True},
                    "key": {"type": "string", "nullable": True},
                    "bpm": {"type": "number", "nullable": True},
                },
            },
        }
    },
}

_DECK_READ_PROMPT = (
    "You are reading a DJ software screenshot to extract per-deck track state. "
    "Look at the deck panels (typically left=A, right=B; some apps show 4 decks "
    "A/B/C/D). For each deck whose badge you can read, return the deck side, the "
    "loaded track title, the musical key (Camelot like '8A', or musical like "
    "'Am' — whatever the badge shows), and the BPM.\n\n"
    "CRITICAL: if a field is NOT clearly visible / legible, return null for that "
    "field. Do NOT guess, infer, or hallucinate. A null is correct and safe; a "
    "wrong value is a silent error. Only report what you can actually read on the "
    "screen. Return JSON matching the schema: "
    '{"decks":[{"side","title","key","bpm"}]}.'
)


class DeckVisionReader:
    """Separate structured-output Gemini deck-vision read (cadence-bounded).

    Dependency-injected Gemini client (no globals) so the default test suite can
    pass a mock and make NO live call:

        DeckVisionReader(client=genai_client, model=VISION_MODEL)

    ``read(jpeg_bytes)`` returns a ``dict[str, DeckTrack]`` keyed by deck side.
    The map is empty on any failure / skip / debounce-with-no-prior — an honest
    unknown, never a raise.
    """

    def __init__(
        self,
        *,
        client: Any,
        model: str,
        interval: float = DEFAULT_VISION_INTERVAL_S,
    ) -> None:
        self._client = client
        self._model = model
        self._interval = max(0.0, float(interval))
        self._last_read_at: float = 0.0
        # Last successful resolved map — returned on a debounced read so the
        # poller keeps last-known state instead of flickering to empty.
        self._last_decks: dict[str, DeckTrack] = {}

    # ------------------------------------------------------------------ #
    # Public read                                                         #
    # ------------------------------------------------------------------ #

    def read(self, jpeg_bytes: bytes, *, audio_only: bool = False) -> dict[str, DeckTrack]:
        """Issue a structured deck-vision read and return resolved decks.

        * ``audio_only=True`` → skip entirely (no decks visible — never call the
          model). Returns ``{}``.
        * within the debounce interval since the last read → return last-known
          decks WITHOUT a new Gemini call (cost bound).
        * otherwise → one non-streaming structured Gemini call; parse defensively.

        NEVER raises: any failure degrades to the last-known / empty map.
        """
        if audio_only:
            return {}

        now = time.time()
        if self._interval > 0.0 and (now - self._last_read_at) < self._interval:
            # Debounced — too soon. Return last-known without a new call.
            return dict(self._last_decks)

        self._last_read_at = now
        try:
            raw = self._call_gemini(jpeg_bytes)
        except Exception as e:  # noqa: BLE001 — graceful degrade (TrackInfo discipline)
            print(f"[deck vision err] {e}", file=sys.stderr)
            return {}

        decks = self._parse(raw, now=now)
        if decks:
            self._last_decks = decks
        return decks

    # ------------------------------------------------------------------ #
    # Gemini call (separate, structured, non-streaming) — Gemini-only     #
    # ------------------------------------------------------------------ #

    def _call_gemini(self, jpeg_bytes: bytes) -> str:
        """Issue the dedicated structured deck-read call. Returns response text.

        Reuses the established ``client.models.generate_content`` (non-streaming —
        deliberately NOT the streaming reaction path) +
        ``types.Part.from_bytes(..., mime_type="image/jpeg")`` inline-image pattern.
        The screenshot is attached to THIS call only — the reaction-path
        ``screen_jpeg = None`` killswitch is untouched.
        """
        from google.genai import types  # local import — keeps module light, matches dj_cohost

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_DECK_READ_SCHEMA,
            temperature=0.0,  # deterministic read — we want the badge, not creativity
        )
        contents = [
            _DECK_READ_PROMPT,
            types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
        ]
        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
            config=config,
        )
        return _extract_text(response)

    # ------------------------------------------------------------------ #
    # Null-defensive parse → DeckTrack map                                #
    # ------------------------------------------------------------------ #

    def _parse(self, raw: str, *, now: float) -> dict[str, DeckTrack]:
        """Parse the structured JSON into a ``{side: DeckTrack}`` map.

        Null/missing fields → ``None`` → confidence=0 / unknown (no guess). A junk
        key normalizes to ``None`` via ``to_camelot`` (never fabricated). Any
        structural surprise (not-a-dict, decks-not-a-list) degrades to ``{}``.
        """
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        if not isinstance(data, dict):
            return {}
        deck_list = data.get("decks")
        if not isinstance(deck_list, list):
            return {}

        decks: dict[str, DeckTrack] = {}
        for item in deck_list:
            if not isinstance(item, dict):
                continue
            side = item.get("side")
            if not isinstance(side, str) or side.strip().upper() not in ("A", "B", "C", "D"):
                continue
            side = side.strip().upper()

            title = item.get("title")
            title = title if isinstance(title, str) and title.strip() else None

            raw_key = item.get("key")
            raw_key = raw_key if isinstance(raw_key, str) and raw_key.strip() else None
            camelot = to_camelot(raw_key)  # musical/open-key/Camelot → Camelot, junk → None

            bpm_val = item.get("bpm")
            try:
                bpm = float(bpm_val) if bpm_val is not None else 0.0
            except (ValueError, TypeError):
                bpm = 0.0

            # A deck with NOTHING legible (no title AND no key) is honest-unknown:
            # confidence=0. A deck with at least a readable title carries the
            # (below-XML) vision confidence.
            resolved = title is not None or camelot is not None
            confidence = VISION_CONF if resolved else 0.0

            decks[side] = DeckTrack(
                title=title,
                track_id=None,  # vision reads a badge, not a library id
                bpm=bpm,
                key=raw_key,  # RAW read kept; camelot is the normalized citation field
                camelot=camelot,
                open_key=None,
                energy=None,
                loaded_at=now,
                confidence=confidence,
                source="screen_vision",
            )
        return decks


# ---------------------------------------------------------------------- #
# Response-text extraction (mirrors debrief/tldr._extract_text)           #
# ---------------------------------------------------------------------- #


def _extract_text(response: Any) -> str:
    """Pull text out of a Gemini response object.

    Handles both the ``.text`` shortcut and the explicit
    ``.candidates[0].content.parts[0].text`` shape. Returns ``""`` on any
    surprise (→ graceful unknown).
    """
    text = getattr(response, "text", None)
    if isinstance(text, str) and text:
        return text
    try:
        return response.candidates[0].content.parts[0].text  # type: ignore[no-any-return]
    except (AttributeError, IndexError, TypeError):
        return ""
