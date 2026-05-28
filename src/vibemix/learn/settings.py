# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 03 — EXEMPLAR-04 ``learn`` settings reader.

REQ-ID: EXEMPLAR-04 — reader helper for the persisted headphone output
device index used by :class:`vibemix.learn.audio_cue.ExemplarPlayer`.

The setter side rides on the existing ``ipc.settings.set`` envelope
dispatch (see :func:`vibemix.runtime.settings.SettingsApplier._apply_learn_headphone_device_index`).
That handler validates ``int >= 0`` OR ``None`` and persists into
:attr:`vibemix.runtime.config_store.ConfigStore.extra` under
``"learn.headphone_device_index"`` (mirrors the mood / skill / lens /
click_through pattern — no config-store schema bump).

This module is read-only and import-light: it only pulls
:mod:`vibemix.runtime.config_store` (stdlib + dataclasses) so the
exemplar code path stays free of the LiveKit / agent stack the live
co-host carries.
"""
from __future__ import annotations


def read_learn_headphone_device_index() -> int | None:
    """Read the headphone output device index for tutor exemplar playback.

    Returns:
        * ``int >= 0`` — explicit ``sounddevice`` device index the user
          picked via the P97 wizard (or via direct ``ipc.settings.set``).
        * ``None`` — system default (the user did NOT pick a device, or
          the persisted value is missing / invalid). Callers should
          interpret ``None`` as "fall through to ``sd.default.device[1]``"
          rather than passing ``None`` to ``sd.OutputStream(device=...)``
          (which would raise).

    The reader never raises — corrupt persisted values silently return
    ``None`` so the boot path stays bulletproof.
    """
    try:
        from vibemix.runtime.config_store import load_config
        cfg = load_config()
    except Exception:  # pragma: no cover — defensive boot path
        return None
    if cfg is None:
        return None
    val = cfg.extra.get("learn.headphone_device_index")
    if val is None:
        return None
    # Reject bool — Python's bool is a subclass of int and a corrupted
    # disk value of ``true`` / ``false`` would otherwise map to device
    # 0 / 1 (a latent footgun for an audio surface).
    if isinstance(val, bool):
        return None
    try:
        idx = int(val)
    except (TypeError, ValueError):
        return None
    return idx if idx >= 0 else None


__all__ = ["read_learn_headphone_device_index"]
