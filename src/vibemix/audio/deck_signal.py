# SPDX-License-Identifier: Apache-2.0
"""Adapter: DeckAudioCapture (live rings) -> LiveSignalFrame (the Judge's input).

A pure translation between two layers, kept OUT of DeckAudioCapture so the
capture class stays focused on audio-thread plumbing and the Judge's contract
stays decoupled. The caller resolves per-lane camelot / source-trust / track-id
from already-live state and passes them in `lane_meta` — the adapter never
resolves now-playing rows itself (single-writer invariant respected). Per-lane
bands come from each lane's PCM ring via band_energy_ratios (None when silent).
"""
from __future__ import annotations

from vibemix.audio.band_features import band_energy_ratios
from vibemix.audio.constants import INPUT_SR_TARGET
from vibemix.audio.deck_capture import _DECK_ACTIVE_RMS, _DECK_SIDES, DeckAudioCapture
from vibemix.state.live_signal import LaneObservation, LiveSignalFrame

# ~1s of per-lane audio for the band estimate (matches the _SPEC_WIN window).
_BAND_SAMPLES = INPUT_SR_TARGET


def signal_frame_from_capture(
    capture: DeckAudioCapture,
    *,
    t_session: float,
    policy: str,
    lane_meta: dict[str, dict[str, object]],
) -> LiveSignalFrame:
    """Assemble the Judge's typed input from the live capture rings.

    `lane_meta[side]` carries the caller-resolved {camelot, source_trusted,
    track_id}. `routing_enabled` mirrors the capture's routing — False on the
    common master-only rig, which makes the executed-mix signals honest-null.
    """
    routing_enabled = capture.routing.enabled
    lanes: dict[str, LaneObservation] = {}
    for side in _DECK_SIDES:
        meta = lane_meta.get(side, {})
        buf = capture.buffers.get(side) if routing_enabled else None
        bands = None
        rms = float(capture.last_rms.get(side, 0.0))
        if buf is not None:
            pcm = buf.snapshot(_BAND_SAMPLES)
            bands = band_energy_ratios(pcm, INPUT_SR_TARGET)
        lanes[side] = LaneObservation(
            active=rms >= _DECK_ACTIVE_RMS,
            source_trusted=bool(meta.get("source_trusted", False)),
            camelot=meta.get("camelot"),  # type: ignore[arg-type]
            bands=bands,
            rms=rms,
            track_id=meta.get("track_id"),  # type: ignore[arg-type]
        )
    return LiveSignalFrame(
        t_session=t_session,
        policy=policy,
        routing_enabled=routing_enabled,
        lanes=lanes,
    )
