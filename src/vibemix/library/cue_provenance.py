# SPDX-License-Identifier: Apache-2.0
"""Cue provenance stamping shared by every cue carrier.

Rekordbox POSITION_MARK and Serato Markers2 do not carry an explicit
``source`` field. The only portable, visible provenance bit is the cue name, so
machine-authored cues get a stable ``VM `` prefix. DJ-authored cues are kept
byte-for-byte unless they already start with that reserved prefix, in which
case the caller must reject the mark so a hand cue cannot masquerade as a
vibemix-authored cue.
"""

from __future__ import annotations

from typing import Any

VM_CUE_PREFIX = "VM "

__all__ = [
    "VM_CUE_PREFIX",
    "is_machine_cue_source",
    "is_vm_cue_name",
    "provenance_stamped_cue_name",
]


def _normalize_source(source: Any) -> str:
    return str(source or "dj").strip().lower() or "dj"


def is_machine_cue_source(source: Any) -> bool:
    """Return true for every explicit non-DJ cue source.

    The current product sources are ``auto`` and ``anlz``; the cue-land design
    also names ``fallback``. Treat future explicit values as machine-authored
    rather than accidentally presenting them as DJ cues.
    """
    return _normalize_source(source) != "dj"


def is_vm_cue_name(name: Any) -> bool:
    return str(name or "").casefold().startswith(VM_CUE_PREFIX.casefold())


def provenance_stamped_cue_name(name: Any, source: Any) -> str | None:
    """Return the carrier-visible cue name, or ``None`` when it is rejected.

    ``None`` is only returned for DJ-authored cues whose name starts with the
    reserved ``VM `` prefix. Machine-authored cues are idempotently stamped:
    ``INTRO`` -> ``VM INTRO`` and ``VM INTRO`` stays ``VM INTRO``.
    """
    raw = str(name or "").strip() or "CUE"
    if not is_machine_cue_source(source):
        if is_vm_cue_name(raw):
            return None
        return raw

    if is_vm_cue_name(raw):
        return VM_CUE_PREFIX + raw[len(VM_CUE_PREFIX) :].lstrip()
    return f"{VM_CUE_PREFIX}{raw}"
