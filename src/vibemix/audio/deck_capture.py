# SPDX-License-Identifier: Apache-2.0
"""Optional multichannel deck-audio capture routing.

The default Vibemix capture is still a cheap 2-channel global mix. This module
only activates when the operator explicitly maps input channels to decks. It is
pure numpy/ring-buffer plumbing: no sounddevice imports, no model calls.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from vibemix.audio.buffers import AudioBuffer
from vibemix.audio.constants import INPUT_SR_TARGET
from vibemix.audio.resample import resample_audio

_DECK_SIDES = ("A", "B")
_MAX_CAPTURE_CHANNELS = 32
_DECK_ACTIVE_RMS = 0.003
_DELTA_FLOOR = 0.10
_WINDOW_HISTORY_S = 7.0
_WINDOW_PRE_START_S = -6.0
_WINDOW_PRE_END_S = -1.0
_WINDOW_CURRENT_START_S = -1.0
_WINDOW_CURRENT_END_S = 0.0


@dataclass(frozen=True, slots=True)
class DeckAudioRouting:
    """Validated channel map for optional isolated deck capture.

    Channel indices are zero-based CoreAudio/PortAudio input indices. This keeps
    the runtime aligned with rekordbox settings such as ``OutputChannel_Deck0_L=0``.
    """

    opened_channels: int
    master_channels: tuple[int, ...]
    deck_channels: dict[str, tuple[int, ...]]
    enabled: bool
    required_opened_channels: int = 0
    reason: str = "disabled"
    source: str = "env"
    hint: dict[str, object] | None = None

    def context(self) -> dict[str, object]:
        context: dict[str, object] = {
            "opened_channels": self.opened_channels,
            "master_channels": ",".join(str(ch) for ch in self.master_channels),
            "deck_channels": {
                side: ",".join(str(ch) for ch in channels)
                for side, channels in sorted(self.deck_channels.items())
            },
            "deck_audio_capture_enabled": self.enabled,
            "deck_audio_capture_reason": self.reason,
            "deck_audio_required_opened_channels": self.required_opened_channels,
            "deck_audio_routing_source": self.source,
        }
        if self.hint:
            hint = _routing_hint_context(self.hint)
            if hint:
                context["deck_audio_routing_hint"] = hint
        return context


@dataclass(slots=True)
class DeckAudioFrame:
    """Audio-thread result from one multichannel callback frame."""

    master_mono: np.ndarray
    passthrough_stereo: np.ndarray
    deck_rms: dict[str, float]
    deck_features: dict[str, dict[str, object]]
    deck_deltas: dict[str, list[str]]


class DeckAudioCapture:
    """Maintains optional per-deck rings from a multichannel capture stream."""

    def __init__(self, routing: DeckAudioRouting, *, seconds: float = 12.0) -> None:
        self.routing = routing
        self.buffers: dict[str, AudioBuffer] = {
            side: AudioBuffer(seconds=seconds, sr=INPUT_SR_TARGET)
            for side in routing.deck_channels
            if routing.enabled
        }
        self._active_sides_seen: set[str] = set()
        self._clock_s: float = 0.0
        self._feature_history: list[tuple[float, dict[str, dict[str, object]]]] = []
        self.last_rms: dict[str, float] = {}
        self.last_features: dict[str, dict[str, object]] = {}
        self.last_deltas: dict[str, list[str]] = {}

    def process(self, indata: np.ndarray, *, source_sr: int) -> DeckAudioFrame:
        """Return master/passthrough audio and update deck rings.

        ``indata`` is float32 ``(frames, channels)`` from PortAudio. The master
        path uses configured master channels when valid; otherwise it averages
        every opened channel, which is the honest fallback for deck-pair-only
        captures.
        """
        if indata.ndim != 2 or indata.shape[1] == 0:
            empty = np.zeros(0, dtype=np.float32)
            return DeckAudioFrame(empty, np.zeros((0, 2), dtype=np.float32), {}, {}, {})

        master_channels = _valid_channels(self.routing.master_channels, indata.shape[1])
        if not master_channels:
            master_channels = tuple(range(indata.shape[1]))
        master_view = indata[:, master_channels]
        master_mono = master_view.mean(axis=1).astype(np.float32)
        passthrough = np.repeat(master_mono[:, None], 2, axis=1).astype(np.float32)

        deck_rms: dict[str, float] = {}
        deck_features: dict[str, dict[str, object]] = {}
        deck_deltas: dict[str, list[str]] = {}
        if self.routing.enabled:
            for side, channels in self.routing.deck_channels.items():
                valid = _valid_channels(channels, indata.shape[1])
                if not valid:
                    continue
                deck_mono = indata[:, valid].mean(axis=1).astype(np.float32)
                deck_rms[side] = float(np.sqrt(np.mean(deck_mono * deck_mono)))
                if deck_rms[side] >= _DECK_ACTIVE_RMS:
                    self._active_sides_seen.add(side)
                deck_features[side] = _deck_frame_features(deck_mono, deck_rms[side])
                delta = _feature_delta_tokens(deck_features[side], self.last_features.get(side))
                if delta:
                    deck_deltas[side] = delta
                try:
                    deck16f = resample_audio(
                        deck_mono,
                        source_sr=source_sr,
                        target_sr=INPUT_SR_TARGET,
                    )
                    deck_pcm = np.clip(deck16f * 32767.0, -32768, 32767).astype(np.int16)
                    self.buffers[side].push(deck_pcm)
                except Exception:
                    continue
        self._record_feature_history(deck_features, frames=indata.shape[0], source_sr=source_sr)
        self.last_rms = deck_rms
        self.last_features = deck_features
        self.last_deltas = deck_deltas
        return DeckAudioFrame(master_mono, passthrough, deck_rms, deck_features, deck_deltas)

    def effective_enabled(self) -> bool:
        """Return whether deck-pair isolation is verified enough to consume.

        Rekordbox settings are a useful hint, not live proof. In the common
        internal-mixer BlackHole setup, channels 0/1 carry the whole master mix
        and 2/3 stay silent; treating that as A/B isolated decks makes Deck 2
        look dead. Manual env maps remain operator-trusted, while auto-detected
        Rekordbox maps must show activity on both configured deck pairs at
        least once before downstream code consumes them as isolated lanes.
        """
        if not self.routing.enabled:
            return False
        if self.routing.source != "rekordbox_settings":
            return True
        return all(side in self._active_sides_seen for side in _DECK_SIDES)

    def context(self) -> dict[str, object]:
        ctx = self.routing.context()
        if self.routing.enabled:
            effective_enabled = self.effective_enabled()
            ctx["deck_audio_capture_configured"] = True
            ctx["deck_audio_capture_enabled"] = effective_enabled
            ctx["deck_audio_capture_verified"] = effective_enabled
            ctx["deck_audio_active_sides_seen"] = (
                ",".join(side for side in _DECK_SIDES if side in self._active_sides_seen)
                or "none"
            )
            if not effective_enabled:
                ctx["deck_audio_capture_reason"] = "deck_pair_capture_unverified"
        if self.last_rms:
            ctx["deck_audio_rms"] = {
                side: round(value, 6) for side, value in sorted(self.last_rms.items())
            }
        if self.last_features:
            ctx["deck_audio_features"] = {
                side: dict(values) for side, values in sorted(self.last_features.items())
            }
        if self.last_deltas:
            ctx["deck_audio_deltas"] = {
                side: list(values) for side, values in sorted(self.last_deltas.items())
            }
        windows = self._window_context()
        if windows:
            ctx["deck_audio_windows"] = windows
        return ctx

    def _record_feature_history(
        self,
        deck_features: dict[str, dict[str, object]],
        *,
        frames: int,
        source_sr: int,
    ) -> None:
        try:
            duration_s = float(frames) / float(source_sr)
        except (TypeError, ValueError, ZeroDivisionError):
            duration_s = 0.0
        if duration_s > 0.0 and duration_s == duration_s:
            self._clock_s += min(duration_s, 1.0)
        if not deck_features:
            return
        self._feature_history.append(
            (self._clock_s, {side: dict(row) for side, row in deck_features.items()})
        )
        cutoff = self._clock_s - _WINDOW_HISTORY_S
        while self._feature_history and self._feature_history[0][0] < cutoff:
            self._feature_history.pop(0)

    def _window_context(self) -> dict[str, object]:
        if not self.routing.enabled or not self._feature_history:
            return {}
        out: dict[str, object] = {
            "pre_s": [_WINDOW_PRE_START_S, _WINDOW_PRE_END_S],
            "current_s": [_WINDOW_CURRENT_START_S, _WINDOW_CURRENT_END_S],
        }
        for side in _DECK_SIDES:
            pre = self._aggregate_window(
                side,
                start_s=self._clock_s + _WINDOW_PRE_START_S,
                end_s=self._clock_s + _WINDOW_PRE_END_S,
            )
            current = self._aggregate_window(
                side,
                start_s=self._clock_s + _WINDOW_CURRENT_START_S,
                end_s=self._clock_s + _WINDOW_CURRENT_END_S,
            )
            if not pre and not current:
                continue
            row: dict[str, object] = {}
            if pre:
                row["pre"] = pre
            if current:
                row["current"] = current
            if pre and current:
                delta = _feature_delta_tokens(current, pre)
                if delta:
                    row["delta"] = delta
            if row:
                out[side] = row
        return out if any(side in out for side in _DECK_SIDES) else {}

    def _aggregate_window(self, side: str, *, start_s: float, end_s: float) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        for at_s, features in self._feature_history:
            if start_s < at_s <= end_s:
                row = features.get(side)
                if isinstance(row, dict):
                    rows.append(row)
        if not rows:
            return {}
        out: dict[str, object] = {}
        for key in ("rms", "peak", "zcr", "flux", "crest"):
            values = [
                value
                for row in rows
                for value in [_feature_number(row.get(key))]
                if value is not None
            ]
            if values:
                out[key] = round(sum(values) / len(values), 6)
        rms = _feature_number(out.get("rms")) or 0.0
        out["activity"] = "active" if rms >= _DECK_ACTIVE_RMS else "silent"
        out["frames"] = len(rows)
        return out


def _deck_frame_features(deck_mono: np.ndarray, rms: float) -> dict[str, object]:
    """Cheap per-callback descriptors for Viber/Gemini deck-lane context."""
    if deck_mono.size == 0:
        return {
            "activity": "silent",
            "rms": 0.0,
            "peak": 0.0,
            "zcr": 0.0,
            "flux": 0.0,
            "crest": 0.0,
        }
    peak = float(np.max(np.abs(deck_mono)))
    if deck_mono.size > 1:
        signs = np.signbit(deck_mono)
        zcr = float(np.mean(signs[1:] != signs[:-1]))
        diff = np.diff(deck_mono.astype(np.float32))
        flux = float(np.sqrt(np.mean(diff * diff))) if diff.size else 0.0
    else:
        zcr = 0.0
        flux = 0.0
    crest = peak / rms if rms > 1e-9 else 0.0
    return {
        "activity": "active" if rms >= _DECK_ACTIVE_RMS else "silent",
        "rms": round(min(max(rms, 0.0), 9.999), 6),
        "peak": round(min(max(peak, 0.0), 9.999), 6),
        "zcr": round(min(max(zcr, 0.0), 1.0), 4),
        "flux": round(min(max(flux, 0.0), 9.999), 6),
        "crest": round(min(max(crest, 0.0), 99.9), 2),
    }


def _feature_delta_tokens(
    current: dict[str, object], previous: dict[str, object] | None
) -> list[str]:
    """Return compact feature-change tokens for one deck lane."""
    if not isinstance(previous, dict):
        return []
    out: list[str] = []
    for key in ("rms", "peak", "flux", "zcr", "crest"):
        cur = _feature_number(current.get(key))
        prev = _feature_number(previous.get(key))
        if cur is None or prev is None or prev <= 0.0:
            continue
        rel = (cur - prev) / abs(prev)
        if abs(rel) < _DELTA_FLOOR:
            continue
        direction = "rose" if rel > 0 else "fell"
        pct = min(999, round(abs(rel) * 100))
        out.append(f"{key}_{direction}_{pct}pct_{_delta_confidence(rel)}")
        if len(out) >= 4:
            break
    return out


def _feature_number(raw: object) -> float | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    if value != value or value < 0.0:
        return None
    return value


def _delta_confidence(rel: float) -> str:
    mag = abs(rel)
    if mag >= 0.40:
        return "strong"
    if mag >= 0.18:
        return "clear"
    return "slight"


def deck_audio_routing_from_env(
    *,
    input_channels: int | None,
    default_opened_channels: int = 2,
    capture_device_name: str | None = None,
    rekordbox_settings_paths: tuple[Path, ...] | None = None,
) -> DeckAudioRouting:
    """Parse optional deck capture env and return a safe routing plan."""
    max_in = _bounded_channel_count(input_channels)
    requested_opened = _bounded_channel_count(os.environ.get("VIBEMIX_INPUT_CHANNELS"))
    raw_deck_channels = os.environ.get("VIBEMIX_DECK_AUDIO_CHANNELS")
    _raw = str(raw_deck_channels or "").strip()
    auto_requested_env = _raw.lower() in {"auto", "rekordbox"}
    hint = rekordbox_deck_output_routing_hint(
        settings_paths=rekordbox_settings_paths,
        capture_device_name=capture_device_name,
        input_channels=max_in,
    )
    # Global default (Kaan 2026-05-30: "it should be global — nobody will set
    # this [env var]"). With NO env override, a high-confidence rekordbox
    # external-mixer hint — both decks mapped AND fitting the capture device —
    # auto-enables per-deck grounding so the Judge + live grounding stack work
    # out of the box instead of staying dark for every real user. Abstain-first
    # downstream is the backstop if the routed audio isn't actually present. Any
    # explicit value (a manual A=..;B=.. map, or "off"/"master") takes its own
    # branch below and overrides this default.
    _hint_external_both_decks = bool(
        hint
        and hint.get("mixer_mode") == "external"
        and isinstance(hint.get("deck_channels"), dict)
        and all(side in (hint.get("deck_channels") or {}) for side in _DECK_SIDES)
    )
    # Fire the global default when the external-mixer map either fits the capture
    # device NOW, or when a concrete capture device is named that __main__ can
    # upgrade to a wider sibling (BlackHole 2ch -> 16ch). The live rig (2026-05-30)
    # taught us the default device boots as 2ch: requiring fits_input_channels on
    # THAT device left per-deck dark forever. With a named device but no fit, the
    # routing falls through to `capture_device_too_few_channels` below — the swap
    # signal __main__ keys on. capture_device_name=None (a plain stereo user, no
    # rig) keeps the stereo master-only default untouched.
    _hint_high_confidence = _hint_external_both_decks and (
        hint.get("fits_input_channels") is True or bool(capture_device_name)
    )
    auto_requested = auto_requested_env or (_raw == "" and _hint_high_confidence)
    if auto_requested and hint:
        deck_channels = {
            side: tuple(channels)
            for side, channels in (hint.get("deck_channels") or {}).items()
            if side in _DECK_SIDES and isinstance(channels, tuple)
        }
        map_reason = "rekordbox_settings_auto"
        source = "rekordbox_settings"
    elif auto_requested:
        deck_channels = {}
        map_reason = "rekordbox_settings_unavailable"
        source = "rekordbox_settings"
    else:
        deck_channels, map_reason = _parse_deck_channels(raw_deck_channels)
        source = "env"

    needed = max((ch for channels in deck_channels.values() for ch in channels), default=-1) + 1
    required_opened = max(0, needed)
    if requested_opened is None:
        requested_opened = max(default_opened_channels, needed)
    if requested_opened is None or requested_opened <= 0:
        requested_opened = default_opened_channels
    if max_in is not None and requested_opened > max_in:
        requested_opened = max_in
    requested_opened = max(1, min(requested_opened, _MAX_CAPTURE_CHANNELS))

    master_channels = _parse_channel_list(os.environ.get("VIBEMIX_MASTER_AUDIO_CHANNELS"))
    if not master_channels:
        if deck_channels:
            master_channels = tuple(
                sorted({ch for channels in deck_channels.values() for ch in channels})
            )
        else:
            master_channels = tuple(range(min(2, requested_opened)))

    valid_decks = {
        side: channels
        for side, channels in deck_channels.items()
        if channels and max(channels) < requested_opened
    }
    enabled = all(side in valid_decks for side in _DECK_SIDES)
    if enabled:
        reason = map_reason if auto_requested else "configured"
    elif deck_channels and max_in is not None and needed > max_in:
        reason = "capture_device_too_few_channels"
    elif deck_channels and needed > requested_opened:
        reason = "opened_channels_too_few"
    elif deck_channels:
        reason = "invalid_channel_map"
    else:
        reason = map_reason

    return DeckAudioRouting(
        opened_channels=requested_opened,
        master_channels=master_channels,
        deck_channels=valid_decks if enabled else {},
        enabled=enabled,
        required_opened_channels=required_opened,
        reason=reason,
        source=source,
        hint=hint,
    )


def _parse_deck_channels(raw: str | None) -> tuple[dict[str, tuple[int, ...]], str]:
    text = str(raw or "").strip()
    if not text:
        return {}, "disabled"
    out: dict[str, tuple[int, ...]] = {}
    for chunk in text.replace("|", ";").split(";"):
        if not chunk.strip():
            continue
        if "=" in chunk:
            side_raw, channels_raw = chunk.split("=", 1)
        elif ":" in chunk:
            side_raw, channels_raw = chunk.split(":", 1)
        else:
            return {}, "parse_error"
        side = side_raw.strip().upper()
        if side not in _DECK_SIDES:
            continue
        channels = _parse_channel_list(channels_raw)
        if channels:
            out[side] = channels
    return out, "configured" if out else "parse_error"


def rekordbox_deck_output_routing_hint(
    *,
    settings_paths: tuple[Path, ...] | None = None,
    capture_device_name: str | None = None,
    input_channels: int | None = None,
) -> dict[str, object] | None:
    """Return the best bounded deck-output routing hint from rekordbox settings.

    rekordbox stores Audio preferences as XML ``DEVICESETUP`` rows. In external
    mixer mode those rows can map track decks to separate output channel pairs.
    That is routing evidence only: it proves how rekordbox was configured to
    output decks, not that Vibemix is currently receiving audio on those input
    channels.
    """
    max_in = _bounded_channel_count(input_channels)
    fallback_candidates: list[dict[str, object]] = []
    candidates: list[dict[str, object]] | None = None
    for path in settings_paths or _default_rekordbox_settings_paths():
        settings_path = Path(path)
        path_candidates = _rekordbox_settings_candidates(settings_path, max_input_channels=max_in)
        current_output_tokens = _rekordbox_current_output_tokens(settings_path)
        if current_output_tokens:
            candidates = [
                candidate
                for candidate in path_candidates
                if _device_token(candidate.get("output_device")) in current_output_tokens
            ]
            break
        fallback_candidates.extend(path_candidates)
    if candidates is None:
        candidates = fallback_candidates
    if not candidates:
        return None

    capture_norm = _device_token(capture_device_name)

    def _score(candidate: dict[str, object]) -> tuple[int, float]:
        score = 0
        if candidate.get("mixer_mode") == "external":
            score += 40
        output_norm = _device_token(candidate.get("output_device"))
        if capture_norm and output_norm == capture_norm:
            score += 30
        elif capture_norm and output_norm and (
            output_norm in capture_norm or capture_norm in output_norm
        ):
            score += 15
        if "aggregate" in output_norm or "blackhole" in output_norm:
            score += 10
        if candidate.get("fits_input_channels"):
            score += 10
        return score, float(candidate.get("date") or 0.0)

    best = max(candidates, key=_score)
    return best if best.get("deck_channels") else None


def _rekordbox_current_output_tokens(path: Path) -> set[str]:
    """Return current rekordbox output device tokens from the top-level setup row."""
    if not path.exists() or not path.is_file():
        return set()
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return set()

    tokens: set[str] = set()
    for value_node in root.iter("VALUE"):
        if str(value_node.attrib.get("name") or "") != "audioDeviceManager":
            continue
        setup = value_node.find("DEVICESETUP")
        if setup is None:
            continue
        token = _device_token(setup.attrib.get("audioOutputDeviceName"))
        if token:
            tokens.add(token)
    return tokens


def _default_rekordbox_settings_paths() -> tuple[Path, ...]:
    home = Path.home()
    return (
        home / "Library/Application Support/Pioneer/rekordbox6/rekordbox3.settings",
        home / "Library/Application Support/Pioneer/rekordbox/rekordbox3.settings",
    )


def _rekordbox_settings_candidates(
    path: Path,
    *,
    max_input_channels: int | None,
) -> list[dict[str, object]]:
    if not path.exists() or not path.is_file():
        return []
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError):
        return []

    candidates: list[dict[str, object]] = []
    for value_node in root.iter("VALUE"):
        setup = value_node.find("DEVICESETUP")
        if setup is None:
            continue
        attrs = setup.attrib
        deck_channels = _deck_output_pairs_from_attrs(attrs)
        if not all(side in deck_channels for side in _DECK_SIDES):
            continue
        highest_channel = max(ch for channels in deck_channels.values() for ch in channels)
        fits = max_input_channels is None or highest_channel < max_input_channels
        name = str(value_node.attrib.get("name") or "")
        candidates.append(
            {
                "source": "rekordbox_settings",
                "settings_file": _settings_file_label(path),
                "settings_entry": _evidence_safe(name, max_len=80),
                "output_device": _evidence_safe(attrs.get("audioOutputDeviceName"), max_len=80),
                "input_device": _evidence_safe(attrs.get("audioInputDeviceName"), max_len=80),
                "mixer_mode": (
                    "external" if str(attrs.get("MixerMode_Is_Internal")) == "0" else "internal"
                ),
                "date": _float_attr(attrs.get("Date")),
                "deck_channels": deck_channels,
                "fits_input_channels": fits,
                "rule": "rekordbox_output_routing_hint_not_live_audio_proof",
            }
        )
    return candidates


def _deck_output_pairs_from_attrs(attrs: dict[str, str]) -> dict[str, tuple[int, int]]:
    out: dict[str, tuple[int, int]] = {}
    for deck_index, side in enumerate(_DECK_SIDES):
        left = _int_attr(attrs.get(f"OutputChannel_Deck{deck_index}_L"))
        right = _int_attr(attrs.get(f"OutputChannel_Deck{deck_index}_R"))
        if left is None or right is None or left < 0 or right < 0:
            continue
        if left >= _MAX_CAPTURE_CHANNELS or right >= _MAX_CAPTURE_CHANNELS:
            continue
        out[side] = (left, right)
    return out


def _routing_hint_context(hint: dict[str, object]) -> str:
    deck_channels = hint.get("deck_channels")
    if not isinstance(deck_channels, dict):
        return ""
    pairs = []
    for side in _DECK_SIDES:
        channels = deck_channels.get(side)
        if isinstance(channels, tuple) and len(channels) >= 2:
            pairs.append(f"{side}:{channels[0]},{channels[1]}")
    if not pairs:
        return ""
    fields = [
        "source=rekordbox_settings",
        f"file={_evidence_safe(hint.get('settings_file'), max_len=60)}",
        f"entry={_evidence_safe(hint.get('settings_entry'), max_len=80)}",
        f"output_device={_evidence_safe(hint.get('output_device'), max_len=80)}",
        f"mixer_mode={_evidence_safe(hint.get('mixer_mode'), max_len=24)}",
        "deck_outputs=" + "+".join(pairs),
        f"fits_input_channels={str(bool(hint.get('fits_input_channels'))).lower()}",
        "rule=rekordbox_output_routing_hint_not_live_audio_proof",
    ]
    return "rekordbox_deck_routing_hint[" + " ".join(fields) + "]"


def _parse_channel_list(raw: str | None) -> tuple[int, ...]:
    if raw is None:
        return ()
    channels: list[int] = []
    for token in str(raw).replace("+", ",").split(","):
        token = token.strip()
        if not token:
            continue
        try:
            value = int(token)
        except ValueError:
            return ()
        if value < 0 or value >= _MAX_CAPTURE_CHANNELS:
            return ()
        channels.append(value)
    return tuple(dict.fromkeys(channels))


def _settings_file_label(path: Path) -> str:
    parts = path.parts
    for marker in ("rekordbox6", "rekordbox"):
        if marker in parts:
            idx = parts.index(marker)
            return "/".join(parts[idx:])
    return path.name


def _evidence_safe(raw: object, *, max_len: int) -> str:
    text = "_".join(str(raw or "unknown").strip().split())
    keep = []
    for ch in text:
        keep.append(ch if ch.isalnum() or ch in "._:+,-" else "_")
    return "".join(keep)[:max_len] or "unknown"


def _device_token(raw: object) -> str:
    text = str(raw or "").strip().lower()
    return "".join(ch for ch in text if ch.isalnum())


def _int_attr(raw: object) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return int(float(str(raw)))
    except (TypeError, ValueError, OverflowError):
        return None


def _float_attr(raw: object) -> float:
    if raw is None or isinstance(raw, bool):
        return 0.0
    try:
        value = float(str(raw))
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return value if value == value else 0.0


def _bounded_channel_count(raw: object) -> int | None:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = int(float(str(raw)))
    except (TypeError, ValueError, OverflowError):
        return None
    if value <= 0:
        return None
    return min(value, _MAX_CAPTURE_CHANNELS)


def _valid_channels(channels: tuple[int, ...], available: int) -> tuple[int, ...]:
    return tuple(ch for ch in channels if 0 <= ch < available)
