# SPDX-License-Identifier: Apache-2.0
"""Robust, OS-agnostic audio device selection.

Pure-Python ranking over a CoreAudio / WASAPI device list (a list of
``{"name", "max_input_channels", "max_output_channels"}`` dicts as returned by
``sounddevice.query_devices()``). No OS imports — the platform backend hands us
the already-queried list, we return the chosen index.

Why this exists (release-blocking bug, 2026-05-24)
--------------------------------------------------
The co-host MUST listen to the DJ's MASTER output, captured on macOS via the
``BlackHole 2ch`` virtual device. The old selection was a naive first-match
case-insensitive substring scan: ``needle in name and max_input_channels > 0``.

On a real rig the device list also contains the DJ controller's built-in
soundcard (Pioneer DDJ-FLX4), the laptop mic, and several aggregate devices
(``rekordbox Aggregate Device``, ``AIDJ``, ``AI Capture``, ``Multi-Output
Device``). A bare substring scan has:

  * no exact-match preference (any device merely *containing* the needle wins),
  * no ranking (it returns whichever input-capable device CoreAudio enumerates
    first — order is not stable), and
  * no exclusion of the controller soundcard or the microphone.

Result: the co-host grabbed the controller's input instead of BlackHole and
"listened to the controller", never the master. This module fixes that by
*ranking* candidates and *excluding* the controller and mic from the
music-capture selection, with a strong exact match on ``BlackHole 2ch``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

# Substrings (lowercased) that identify a DJ controller's built-in soundcard.
# These devices appear as both input AND output because the controller carries
# its own audio interface — they must NEVER be chosen as the music-capture
# source. Extend conservatively: only well-known controller-vendor / model
# tokens, so we don't accidentally exclude a legitimately-named loopback.
_CONTROLLER_NAME_TOKENS: tuple[str, ...] = (
    "ddj",  # Pioneer DDJ-FLX4 / DDJ-* family (the founder's controller)
    "flx",  # DDJ-FLX4 short form some drivers expose
    "pioneer",
    "rekordbox",  # rekordbox Aggregate Device (wraps the FLX4 soundcard)
    "traktor",
    "kontrol",  # NI Traktor Kontrol
    "serato",
    "denon",
    "numark",
    "rane",
    "hercules",
    "reloop",
    "mixtrack",
    "controller",
)

# Substrings (lowercased) that identify a microphone — never a master-capture
# source. The mic is captured on a SEPARATE stream (MIC_DEVICE); for the music
# input we must exclude it so we don't analyze the DJ's voice as "the music".
_MIC_NAME_TOKENS: tuple[str, ...] = (
    "microphone",
    "mic",
    "airpods",  # AirPods expose a mic input that must not be the music source
    "headset",
    "webcam",
    "facetime",
    "iphone microphone",
)

# The canonical master-capture device, in strict preference order. Exact name
# first (``BlackHole 2ch`` is what the install wizard provisions), then other
# BlackHole channel variants as a fallback so a 16ch/64ch-only machine still
# captures rather than failing.
_BLACKHOLE_EXACT = "blackhole 2ch"
_BLACKHOLE_PREFIX = "blackhole"

# Output devices that are virtual routing surfaces rather than stable "play the
# AI voice here" endpoints. Positional ``output_device_id`` values are fragile
# across plug/unplug, and stale indexes onto these devices have caused boot to
# hang inside CoreAudio before the websocket can bind.
_UNSTABLE_OUTPUT_TOKENS: tuple[str, ...] = (
    "aggregate device",
    "multi-output",
    "ai capture",
)


def _is_input(info: dict[str, Any]) -> bool:
    try:
        return int(info.get("max_input_channels", 0)) > 0
    except (TypeError, ValueError):
        return False


def _name_of(info: dict[str, Any]) -> str:
    name = info.get("name")
    return name if isinstance(name, str) else ""


def is_controller_device(name: str) -> bool:
    """True if ``name`` looks like a DJ-controller soundcard (excluded from capture)."""
    low = name.lower()
    return any(tok in low for tok in _CONTROLLER_NAME_TOKENS)


def is_mic_device(name: str) -> bool:
    """True if ``name`` looks like a microphone (excluded from music capture)."""
    low = name.lower()
    return any(tok in low for tok in _MIC_NAME_TOKENS)


def is_unstable_output_device(name: str) -> bool:
    """True for virtual aggregate outputs that should not win stale-index selection."""
    low = name.lower()
    return _BLACKHOLE_PREFIX in low or any(tok in low for tok in _UNSTABLE_OUTPUT_TOKENS)


def is_explicit_multi_output_device(name: str) -> bool:
    """True for macOS' deliberate fan-out output, not a capture aggregate."""
    return "multi-output" in name.lower()


class MasterCaptureNotFoundError(RuntimeError):
    """Raised when no BlackHole master-capture input can be selected.

    Carries the candidate device list so the caller can render an actionable
    "install BlackHole 2ch" message instead of silently grabbing the wrong
    device (the bug this module fixes).
    """


def select_master_input(devices: Sequence[dict[str, Any]]) -> int:
    """Choose the music-capture (master-output) INPUT device index.

    Ranking (highest priority first), over input-capable devices only:

      1. Exact ``BlackHole 2ch`` (case-insensitive) — the canonical target.
      2. Any other ``BlackHole`` variant (16ch / 64ch) — degraded but correct.

    Devices whose names look like a DJ controller soundcard or a microphone are
    NEVER selected here, even on a tie — they are the two wrong sources the
    founder hit. If no BlackHole input exists, raise
    ``MasterCaptureNotFoundError`` rather than falling back to *any* input
    (which is exactly how the co-host ended up on the controller).

    Args:
        devices: ``sounddevice.query_devices()``-shaped list.

    Returns:
        Index into ``devices`` of the chosen master-capture input.

    Raises:
        MasterCaptureNotFoundError: no BlackHole input device present.
    """
    exact_match: int | None = None
    variant_match: int | None = None

    for idx, info in enumerate(devices):
        if not _is_input(info):
            continue
        name = _name_of(info)
        if not name:
            continue
        # Hard exclusions: never let the controller or a mic win the music
        # capture, regardless of how its name might otherwise match.
        if is_controller_device(name) or is_mic_device(name):
            continue
        low = name.lower()
        if low == _BLACKHOLE_EXACT and exact_match is None:
            exact_match = idx
        elif _BLACKHOLE_PREFIX in low and variant_match is None:
            variant_match = idx

    if exact_match is not None:
        return exact_match
    if variant_match is not None:
        return variant_match

    available = [_name_of(d) for d in devices if _is_input(d) and _name_of(d)]
    raise MasterCaptureNotFoundError(
        "No BlackHole master-capture input found. vibemix listens to your DJ "
        "software's MASTER output via BlackHole 2ch — it will not fall back to "
        "the controller soundcard or microphone. Install BlackHole 2ch via "
        "`brew install blackhole-2ch` or https://existential.audio/blackhole/ "
        f"and route your DJ app's master into it. Available input devices: {available}"
    )


def find_device_index(
    devices: Sequence[dict[str, Any]], name_substring: str, kind: str
) -> int:
    """Generic case-insensitive substring lookup, kind-filtered.

    Used for the OUTPUT and MIC paths where a plain substring match is correct
    (the caller passes an explicit, unambiguous device name). The music-capture
    INPUT path must use :func:`select_master_input` instead — see this module's
    docstring for why a bare substring match is unsafe for master capture.

    Returns the index of the first input/output-capable device whose name
    contains ``name_substring`` (case-insensitive). Raises ``RuntimeError``
    with the candidate list on a miss.
    """
    field = "max_input_channels" if kind == "input" else "max_output_channels"
    needle = name_substring.lower()
    for idx, info in enumerate(devices):
        name = _name_of(info)
        try:
            chans = int(info.get(field, 0))
        except (TypeError, ValueError):
            chans = 0
        if needle in name.lower() and chans > 0:
            return idx
    available = [_name_of(d) for d in devices if int(d.get(field, 0) or 0) > 0]
    raise RuntimeError(
        f"No {kind} device matching {name_substring!r}. Available {kind} devices: {available}"
    )


def _is_output(info: dict[str, Any]) -> bool:
    try:
        return int(info.get("max_output_channels", 0)) > 0
    except (TypeError, ValueError):
        return False


def select_output_device(
    devices: Sequence[dict[str, Any]],
    *,
    preferred_index: int | None = None,
    fallback_name: str | None = None,
    default_index: int | None = None,
) -> int:
    """Resolve the AI-voice / passthrough OUTPUT device index, degrading
    gracefully instead of crashing when the configured/hardcoded name is absent.

    Why this exists (first-launch crash, 2026-05-29): the live runtime hardcoded
    ``OUTPUT_DEVICE = "MacBook Pro Speakers"`` and resolved it with a strict
    :func:`find_device_index` substring match. A brand-new user on a Mac mini /
    Mac Studio / iMac, with external speakers or headphones selected, a renamed
    output, or a non-English macOS (localized device names) has no such device,
    so the substring missed → ``RuntimeError`` → the process exited with the
    BlackHole-input sentinel and a *misleading* "install BlackHole" banner. The
    app must still boot to SOME working output.

    Preference order (first that resolves to an output-capable device wins):

      1. ``preferred_index`` — the wizard-persisted ``output_device_id`` (an index
         into this same ``query_devices()`` list). The user's explicit choice.
      2. ``fallback_name`` — case-insensitive substring (the ``OUTPUT_DEVICE``
         constant). Preserves the legacy happy path byte-for-byte when the device
         exists.
      3. ``default_index`` — the OS default output (``sd.default.device[1]``).
      4. first output-capable device that is NOT a BlackHole / controller
         loopback — never route the AI voice into the capture device (it would
         feed straight back into the master capture).
      5. first output-capable device at all (last resort).

    Raises:
        RuntimeError (carrying the candidate list) only when the machine has NO
        output-capable device whatsoever — a genuinely unusable state, distinct
        from a missing BlackHole input.
    """

    def _resolvable(idx: int | None, *, allow_multi_output: bool = False) -> bool:
        # output_device_id is a POSITIONAL query_devices() index, which reorders
        # on plug/unplug/reboot. A stale index that lands on a BlackHole output
        # variant would route the AI voice INTO the master-capture device — the
        # co-host would then hear itself (a feedback loop + an anti-slop hazard).
        # So the persisted-index (step 1) and OS-default (step 3) paths reject
        # loopback/aggregate virtual devices; only the explicit last-resort
        # (step 5) may use one.
        # Controllers are NOT excluded here — a stale index onto a controller is
        # merely wrong-output, not a capture loop, and a user may legitimately
        # route the voice to a controller's headphone out.
        if not (isinstance(idx, int) and 0 <= idx < len(devices) and _is_output(devices[idx])):
            return False
        name = _name_of(devices[idx])
        if allow_multi_output and is_explicit_multi_output_device(name):
            return True
        return not is_unstable_output_device(name)

    # 1. Explicit wizard-persisted choice.
    if _resolvable(preferred_index, allow_multi_output=True):
        return preferred_index  # type: ignore[return-value]
    # 2. Legacy substring name (happy-path parity).
    if fallback_name:
        try:
            return find_device_index(devices, fallback_name, "output")
        except RuntimeError:
            pass
    # 3. OS default output.
    if _resolvable(default_index):
        return default_index  # type: ignore[return-value]
    # 4. First real (non-loopback, non-controller) output.
    for idx, info in enumerate(devices):
        if not _is_output(info):
            continue
        low = _name_of(info).lower()
        if not low or is_unstable_output_device(low) or is_controller_device(low):
            continue
        return idx
    # 5. Last resort: any output-capable device.
    for idx, info in enumerate(devices):
        if _is_output(info):
            return idx
    available = [_name_of(d) for d in devices]
    raise RuntimeError(
        "No output-capable audio device found. vibemix needs an audio output "
        f"for the AI voice. Available devices: {available}"
    )
