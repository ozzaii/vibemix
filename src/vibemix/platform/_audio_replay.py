# SPDX-License-Identifier: Apache-2.0
"""Env-gated replay capture backend for QA runs.

This module is deliberately narrow: it only substitutes the *input capture*
stream when ``VIBEMIX_REPLAY_SESSION`` points at a recorded session directory.
The replay stream feeds the same sounddevice-shaped callback the live CoreAudio
stream would have called, so the normal audio buffers, deck-audio splitter, and
state refresh loop remain the only downstream writers.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import wave
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from vibemix.audio.resample import resample_audio
from vibemix.platform.audio import AudioCallback, AudioStream, Kind
from vibemix.platform.track import NowPlayingSnapshot


def replay_session_from_env(environ: dict[str, str] | None = None) -> Path | None:
    """Return the replay session dir when the hard env gate is enabled."""

    env = os.environ if environ is None else environ
    raw = str(env.get("VIBEMIX_REPLAY_SESSION") or "").strip()
    return Path(raw).expanduser() if raw else None


def maybe_wrap_replay_audio_backend(backend: Any) -> Any:
    """Wrap ``backend`` only when ``VIBEMIX_REPLAY_SESSION`` is set."""

    session_dir = replay_session_from_env()
    if session_dir is None:
        return backend
    return ReplayAudioBackend(backend, session_dir=session_dir)


def maybe_wrap_replay_midi_backend(backend: Any) -> Any:
    """Wrap MIDI input so replay QA never opens the physical controller."""

    session_dir = replay_session_from_env()
    if session_dir is None:
        return backend
    return ReplayMidiBackend(backend, session_dir=session_dir)


def maybe_wrap_replay_track_backend(backend: Any) -> Any:
    """Wrap nowplaying so replay QA never shells out to the host OS surface."""

    session_dir = replay_session_from_env()
    if session_dir is None:
        return backend
    return ReplayTrackBackend(backend, session_dir=session_dir)


class ReplayAudioBackend:
    """Delegate everything except input capture to a real audio backend."""

    _REPLAY_DEVICE_INDEX = -911

    def __init__(self, delegate: Any, *, session_dir: Path) -> None:
        self._delegate = delegate
        self.session_dir = Path(session_dir).expanduser()
        self.input_wav = self.session_dir / "input.wav"
        self._info = _wav_info(self.input_wav)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def find_device(self, name_substring: str, kind: Kind) -> int:
        if kind == "input":
            return self._REPLAY_DEVICE_INDEX
        return self._delegate.find_device(name_substring, kind)

    def describe_capture_input(
        self,
        device_index: int,
        *,
        requested_device: str,
        opened_channels: int,
    ) -> dict[str, object]:
        return {
            "requested_device": requested_device,
            "device_name": f"Replay Session ({self.session_dir.name})",
            "input_channels": int(self._info["channels"]),
            "opened_channels": int(opened_channels),
            "sample_rate": int(self._info["sample_rate"]),
            "replay_session": str(self.session_dir),
            "replay_input_wav": str(self.input_wav),
        }

    def open_capture(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        stream = ReplayCaptureStream(
            self.input_wav,
            sample_rate=sample_rate,
            channels=channels,
            block_size=block_size,
            callback=callback,
        )
        stream.start()
        return stream


class ReplayCaptureStream:
    """AudioStream that feeds ``input.wav`` into the existing capture callback."""

    def __init__(
        self,
        wav_path: Path,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> None:
        self._wav_path = Path(wav_path)
        self._sample_rate = max(1, int(sample_rate))
        self._channels = max(1, int(channels))
        self._block_size = max(1, int(block_size))
        self._callback = callback
        self._closed = threading.Event()
        self._started = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def latency_ms(self) -> float:
        return 0.0

    def start(self) -> None:
        if self._started.is_set():
            return
        self._started.set()
        self._thread = threading.Thread(
            target=self._run,
            name="vibemix-replay-capture",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._closed.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

    def close(self) -> None:
        self.stop()

    def _run(self) -> None:
        audio = _read_wav_float32(
            self._wav_path,
            target_sample_rate=self._sample_rate,
            target_channels=self._channels,
        )
        if audio.size == 0:
            return
        total = int(audio.shape[0])
        for start in range(0, total, self._block_size):
            if self._closed.is_set():
                return
            block = audio[start : start + self._block_size]
            if block.shape[0] < self._block_size:
                pad = np.zeros(
                    (self._block_size - block.shape[0], self._channels),
                    dtype=np.float32,
                )
                block = np.concatenate([block, pad], axis=0)
            self._callback(block, int(block.shape[0]), {}, None)
            time.sleep(block.shape[0] / float(self._sample_rate))


class ReplayMidiBackend:
    """Delegate shape-compatible MIDI backend driven by ``midi.jsonl``."""

    def __init__(self, delegate: Any, *, session_dir: Path) -> None:
        self._delegate = delegate
        self.session_dir = Path(session_dir).expanduser()
        self.midi_jsonl = self.session_dir / "midi.jsonl"
        self.controller_state = delegate.controller_state

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def list_input_ports(self) -> list[str]:
        return [f"Replay Session ({self.session_dir.name})"] if self.midi_jsonl.exists() else []

    def open_input(self, port_name: str) -> Any:
        raise RuntimeError("VIBEMIX_REPLAY_SESSION is active; live MIDI input is disabled")

    def start_listener_thread(self, stop_event: threading.Event) -> threading.Thread:
        thread = threading.Thread(
            target=self._run_tape,
            args=(stop_event,),
            name="midi-replay-listener",
            daemon=True,
        )
        thread.start()
        return thread

    def start_port_watcher(
        self,
        stop_event: asyncio.Event,
        on_change=None,
        *,
        poll_seconds: float = 2.0,
    ) -> asyncio.Task:
        async def _idle_replay_watcher() -> None:
            while not stop_event.is_set():
                await asyncio.sleep(0.1)

        return asyncio.get_event_loop().create_task(_idle_replay_watcher())

    def _run_tape(self, stop_event: threading.Event) -> None:
        events = _load_midi_tape(self.midi_jsonl)
        if not events:
            return
        self.controller_state.mark_connected(f"Replay Session ({self.session_dir.name})")
        start = time.monotonic()
        for ts, msg in events:
            while not stop_event.is_set():
                delay = float(ts) - (time.monotonic() - start)
                if delay <= 0:
                    break
                time.sleep(min(delay, 0.05))
            if stop_event.is_set():
                return
            self.controller_state.handle_msg(msg)


class ReplayTrackBackend:
    """Track backend whose ``track_info`` reads ``nowplaying.jsonl``."""

    def __init__(self, delegate: Any, *, session_dir: Path) -> None:
        self._delegate = delegate
        self.session_dir = Path(session_dir).expanduser()
        self.track_info = ReplayTrackInfo(self.session_dir)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def is_available(self) -> bool:
        return self.track_info.has_script

    def poll(self) -> NowPlayingSnapshot | None:
        self.track_info.poll_once()
        snap = self.track_info.snapshot()
        title = str(snap.get("title") or "").strip()
        if not title:
            return None
        return NowPlayingSnapshot(
            title=title,
            artist=None,
            album=None,
            duration_sec=_float_or_none(snap.get("duration_sec")),
            position_sec=_float_or_none(snap.get("position_sec")),
        )

    async def run_poll_loop(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            self.track_info.poll_once()
            await asyncio.sleep(1.0)


class ReplayTrackInfo:
    """TrackInfo-shaped nowplaying script player."""

    def __init__(self, session_dir: Path) -> None:
        self.session_dir = Path(session_dir).expanduser()
        self.nowplaying_jsonl = self.session_dir / "nowplaying.jsonl"
        self._rows = _load_nowplaying_script(self.nowplaying_jsonl)
        self._started = time.monotonic()
        self._lock = threading.Lock()
        self.title: str = ""
        self.prev_title: str = ""
        self.title_changed_at: float = 0.0
        self.duration_sec: float | None = None
        self.position_sec: float | None = None
        self.position_sampled_at: float | None = None
        self.playback_rate: float = 1.0
        self.client_bundle_id: str | None = None
        self.poll_once()

    @property
    def has_script(self) -> bool:
        return bool(self._rows)

    def poll_once(self) -> None:
        if not self._rows:
            return
        elapsed = time.monotonic() - self._started
        row = self._rows[0]
        for candidate in self._rows:
            if float(candidate.get("ts") or 0.0) <= elapsed:
                row = candidate
            else:
                break
        now = time.time()
        title = _full_nowplaying_title(row)
        duration_sec = _float_or_none(row.get("duration_sec"))
        position_sec = _float_or_none(row.get("position_sec"))
        playback_rate = _float_or_none(row.get("playback_rate"))
        client_bundle_id = str(
            row.get("client_bundle_id") or row.get("bundle_id") or ""
        ).strip()
        with self._lock:
            if title and title != self.title:
                self.prev_title = self.title
                self.title = title
                self.title_changed_at = now
            self.duration_sec = duration_sec
            self.position_sec = position_sec
            self.position_sampled_at = now if position_sec is not None else None
            self.playback_rate = playback_rate if playback_rate is not None else 1.0
            self.client_bundle_id = client_bundle_id or None

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "title": self.title,
                "prev_title": self.prev_title,
                "title_changed_at": self.title_changed_at,
                "duration_sec": self.duration_sec,
                "position_sec": self.position_sec,
                "position_sampled_at": self.position_sampled_at,
                "playback_rate": self.playback_rate,
                "client_bundle_id": self.client_bundle_id,
            }


def _wav_info(path: Path) -> dict[str, int]:
    if not path.exists():
        raise FileNotFoundError(f"VIBEMIX_REPLAY_SESSION missing input.wav: {path}")
    with wave.open(str(path), "rb") as wf:
        return {
            "channels": int(wf.getnchannels()),
            "sample_rate": int(wf.getframerate()),
            "frames": int(wf.getnframes()),
        }


def _read_wav_float32(
    path: Path,
    *,
    target_sample_rate: int,
    target_channels: int,
) -> np.ndarray:
    with wave.open(str(path), "rb") as wf:
        source_sr = int(wf.getframerate())
        source_channels = int(wf.getnchannels())
        sample_width = int(wf.getsampwidth())
        raw = wf.readframes(wf.getnframes())

    if sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sample_width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"unsupported WAV sample width {sample_width} in {path}")

    if source_channels > 1:
        samples = samples.reshape(-1, source_channels)
    else:
        samples = samples.reshape(-1, 1)

    if source_sr != target_sample_rate:
        resampled = [
            resample_audio(
                samples[:, idx],
                source_sr=source_sr,
                target_sr=target_sample_rate,
            ).astype(np.float32, copy=False)
            for idx in range(samples.shape[1])
        ]
        min_len = min((arr.size for arr in resampled), default=0)
        samples = (
            np.stack([arr[:min_len] for arr in resampled], axis=1)
            if min_len > 0
            else np.zeros((0, samples.shape[1]), dtype=np.float32)
        )

    if samples.shape[1] > target_channels:
        samples = samples[:, :target_channels]
    elif samples.shape[1] < target_channels:
        pad = np.zeros(
            (samples.shape[0], target_channels - samples.shape[1]),
            dtype=np.float32,
        )
        samples = np.concatenate([samples, pad], axis=1)
    return np.clip(samples, -1.0, 1.0).astype(np.float32, copy=False)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _load_midi_tape(path: Path) -> list[tuple[float, Any]]:
    events: list[tuple[float, Any]] = []
    for row in _load_jsonl(path):
        if row.get("summary") is True:
            continue
        msg = _midi_message_from_row(row)
        if msg is None:
            continue
        events.append((_float_or_none(row.get("ts")) or 0.0, msg))
    return sorted(events, key=lambda item: item[0])


def _midi_message_from_row(row: dict[str, Any]) -> Any | None:
    kind = str(row.get("type") or "").strip()
    channel = _int_or_none(row.get("channel"))
    if channel is None:
        return None
    if kind in {"cc", "control_change"}:
        control = _int_or_none(row.get("data1", row.get("control")))
        value = _int_or_none(row.get("data2", row.get("value")))
        if control is None or value is None:
            return None
        return SimpleNamespace(
            type="control_change",
            channel=channel,
            control=control,
            value=value,
        )
    if kind in {"note_on", "note_off"}:
        note = _int_or_none(row.get("data1", row.get("note")))
        velocity = _int_or_none(row.get("data2", row.get("velocity")))
        if note is None or velocity is None:
            return None
        return SimpleNamespace(type=kind, channel=channel, note=note, velocity=velocity)
    return None


def _load_nowplaying_script(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in _load_jsonl(path):
        if not _full_nowplaying_title(row):
            continue
        row = dict(row)
        row["ts"] = _float_or_none(row.get("ts")) or 0.0
        rows.append(row)
    return sorted(rows, key=lambda item: float(item.get("ts") or 0.0))


def _full_nowplaying_title(row: dict[str, Any]) -> str:
    explicit = str(row.get("full_title") or "").strip()
    if explicit:
        return explicit
    title = str(row.get("title") or "").strip()
    artist = str(row.get("artist") or "").strip()
    if title and artist:
        return f"{artist} - {title}"
    return title


def _int_or_none(raw: object) -> int | None:
    try:
        return int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _float_or_none(raw: object) -> float | None:
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
